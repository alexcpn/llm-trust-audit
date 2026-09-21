"""Run untrusted generated code against hidden tests in an isolated sandbox.

Isolation, strongest first:
  bwrap    read-only system, empty home, project folder invisible, no network, no environment variables
  unshare  no network and a clean environment, but the filesystem is visible (warned)
Without either, execution is refused unless --unsafe-exec is passed.
"""
import hashlib
import json
import os
import re
import resource
import shutil
import site
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "sandbox_runner.py")
RUNNER_VERSION = hashlib.sha256(open(RUNNER, "rb").read()).hexdigest()[:12]
CODE_BLOCK = re.compile(r"```([\w+.-]*)[^\n]*\n(.*?)```", re.S)


def extract_solution(text, required_names):
    """Pick the Python code needed to define all required functions.

    Prefers one block defining everything; otherwise joins all Python-looking blocks in order."""
    blocks = [body for lang, body in CODE_BLOCK.findall(text or "") if lang.lower() in ("", "python", "py", "python3")]
    defines = lambda b: all(re.search(rf"^\s*(async\s+)?def\s+{n}\s*\(", b, re.M) for n in required_names)
    for b in blocks:
        if defines(b):
            return b
    joined = "\n\n".join(blocks)
    return joined if blocks and defines(joined) else None


def detect_mode():
    if shutil.which("bwrap"):
        return "bwrap"
    if shutil.which("unshare"):
        return "unshare"
    return None


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 ** 2, 50 * 1024 ** 2))


def _command(mode, workdir, task, argv=None):
    """Build the sandbox command. argv overrides what runs inside, for the startup probe."""
    py = os.path.realpath(sys.executable)
    user_site = site.getusersitepackages()
    pypath = ":".join(p for p in [user_site] + [p for p in sys.path if "dist-packages" in p or "site-packages" in p] if os.path.isdir(p))
    if mode == "bwrap":
        cmd = ["bwrap", "--ro-bind", "/usr", "/usr"]
        for link in ("lib", "lib64", "bin", "sbin"):
            if os.path.islink(f"/{link}"):
                cmd += ["--symlink", os.readlink(f"/{link}"), f"/{link}"]
            elif os.path.isdir(f"/{link}"):
                cmd += ["--ro-bind", f"/{link}", f"/{link}"]
        for etc in ("/etc/ssl", "/etc/alternatives", "/etc/localtime"):
            if os.path.exists(etc):
                cmd += ["--ro-bind", etc, etc]
        cmd += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--tmpfs", "/home"]
        for p in pypath.split(":"):
            if p and not p.startswith("/usr"):
                cmd += ["--ro-bind", p, p]
        cmd += ["--ro-bind", RUNNER, "/work/sandbox_runner.py", "--bind", workdir, "/work/out",
                "--chdir", "/work/out", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
                "--setenv", "HOME", "/tmp", "--setenv", "PATH", "/usr/bin", "--setenv", "PYTHONPATH", pypath + ":/work/out",
                "--setenv", "PYTHONDONTWRITEBYTECODE", "1", py]
        cmd += argv if argv is not None else ["-W", "ignore", "/work/sandbox_runner.py", task]
        return cmd, None
    if mode == "unshare":
        env = {"HOME": workdir, "PATH": "/usr/bin:/bin", "PYTHONPATH": pypath + ":" + workdir, "PYTHONDONTWRITEBYTECODE": "1"}
        shutil.copy(RUNNER, os.path.join(workdir, "sandbox_runner.py"))
        return ["unshare", "-rn", py] + (argv if argv is not None else ["-W", "ignore", "sandbox_runner.py", task]), env
    env = {"HOME": workdir, "PATH": "/usr/bin:/bin", "PYTHONPATH": pypath + ":" + workdir}
    shutil.copy(RUNNER, os.path.join(workdir, "sandbox_runner.py"))
    return [py] + (argv if argv is not None else ["-W", "ignore", "sandbox_runner.py", task]), env


# The launcher's own failures (namespaces prohibited, a missing bind path, no permission) are
# printed by bwrap or unshare before Python starts. They say nothing about the model's code.
LAUNCHER_ERROR = re.compile(r"^(bwrap|unshare):", re.M)
PROBE_OK = "sandbox-probe-ok"


class SandboxUnavailable(RuntimeError):
    """The sandbox itself could not run. Never a property of the code under test."""


def preflight(mode):
    """Prove the sandbox starts before any answer is scored.

    A launcher failure would otherwise be recorded as an import failure, marking correct code
    broken and caching that verdict, which silently contaminates the reliability numbers.
    """
    workdir = tempfile.mkdtemp(prefix="codeaudit-probe-")
    try:
        cmd, env = _command(mode, workdir, None, argv=["-c", f"print('{PROBE_OK}')"])
        try:
            proc = subprocess.run(cmd, cwd=workdir, env=env if env is not None else {},
                                  capture_output=True, timeout=60)
        except (subprocess.TimeoutExpired, OSError) as e:
            raise SandboxUnavailable(f"{mode}: probe did not run ({type(e).__name__}: {e})")
        if PROBE_OK not in proc.stdout.decode(errors="replace"):
            detail = (proc.stderr.decode(errors="replace").strip() or "no output")[-300:]
            raise SandboxUnavailable(f"{mode}: probe exited {proc.returncode}: {detail}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


class ExecCache:
    def __init__(self, path):
        self.path, self.lock, self.rows = path, threading.Lock(), {}
        self.dropped = 0
        if os.path.exists(path):
            for line in open(path):
                if line.strip():
                    r = json.loads(line)
                    if LAUNCHER_ERROR.search(r["result"].get("stderr") or ""):
                        # Written by an older version that scored launcher failures as broken code.
                        self.dropped += 1
                        self.rows.pop(r["key"], None)
                        continue
                    self.rows[r["key"]] = r["result"]

    def get(self, key):
        return self.rows.get(key)

    def put(self, key, result):
        with self.lock:
            self.rows[key] = result
            with open(self.path, "a") as fh:
                fh.write(json.dumps({"key": key, "result": result}) + "\n")


def run_tests(code, task, mode, cache=None, timeout=90):
    key = hashlib.sha256(f"{RUNNER_VERSION}|{task}|{code}".encode()).hexdigest()[:32]
    if cache is not None and cache.get(key) is not None:
        return cache.get(key)
    workdir = tempfile.mkdtemp(prefix="codeaudit-")
    try:
        with open(os.path.join(workdir, "solution.py"), "w") as fh:
            fh.write(code)
        cmd, env = _command(mode, workdir, task)
        try:
            proc = subprocess.run(cmd, cwd=workdir, env=env if env is not None else {}, capture_output=True,
                                  timeout=timeout, preexec_fn=_limits)
            stderr = proc.stderr.decode(errors="replace")[-600:]
        except subprocess.TimeoutExpired:
            result = {"timeout": True, "import_ok": False, "functional": {}, "security": {}, "net_attempts": [], "errors": {}}
        else:
            path = os.path.join(workdir, "result.json")
            if os.path.exists(path):
                result = json.load(open(path))
            elif LAUNCHER_ERROR.search(stderr):
                # The sandbox never started, so nothing was learned about this code. Do not
                # score it and do not cache it; the caller stops the stage instead.
                raise SandboxUnavailable(f"{mode}: {stderr.strip()[-300:]}")
            else:
                result = {"crashed": True, "stderr": stderr, "import_ok": False, "functional": {}, "security": {},
                          "net_attempts": [], "errors": {}}
        result["sandbox"] = mode
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if cache is not None:
        cache.put(key, result)
    return result
