"""Minimal OpenRouter chat client with retries.

Deliberately sends no app-attribution headers (HTTP-Referer, X-Title):
naming the tool would make audit traffic identifiable (paper Section 7).
"""
import os
import random
import time

import requests

API = "https://openrouter.ai/api/v1"
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524}


class OpenRouterClient:
    def __init__(self, api_key=None, timeout=240, max_retries=8):
        self.key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.key:
            raise SystemExit("OPENROUTER_API_KEY is not set. Export it, or use --fake for an offline run.")
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(self, model, messages, provider=None, extra=None, max_tokens=3000, temperature=None):
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "usage": {"include": True}}
        if temperature is not None:
            body["temperature"] = temperature
        if provider:
            body["provider"] = provider
        if extra:
            body.update(extra)
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        last = {"status": None, "error": None}
        waited = False
        for attempt in range(self.max_retries):
            if attempt and not waited:
                time.sleep(min(60, 2 ** attempt) + random.random())
            waited = False
            try:
                r = requests.post(f"{API}/chat/completions", headers=headers, json=body, timeout=self.timeout)
            except requests.RequestException as e:
                last = {"status": None, "error": str(e)}
                continue
            try:
                data = r.json()
            except ValueError:
                data = {"error": {"message": r.text[:500]}}
            if r.status_code in RETRY_STATUS:
                last = {"status": r.status_code, "error": data.get("error")}
                continue
            if r.status_code == 402:
                err = data.get("error") or {}
                reason = (err.get("metadata") or {}).get("reason", "")
                if "in_flight" in reason and attempt < self.max_retries - 1:
                    # credit is reserved by requests still running; wait for them to settle
                    hdrs = (err.get("metadata") or {}).get("headers") or {}
                    wait = float(r.headers.get("Retry-After") or hdrs.get("Retry-After") or 60)
                    time.sleep(min(wait, 180) + random.random() * 5)
                    waited = True
                    last = {"status": 402, "error": err}
                    continue
                return {"ok": False, "status": 402, "error": err, "fatal": "credits"}
            if r.status_code != 200 or "error" in data:
                return {"ok": False, "status": r.status_code, "error": data.get("error")}
            choice = (data.get("choices") or [{}])[0]
            if "error" in choice:
                last = {"status": r.status_code, "error": choice["error"]}
                continue
            msg = choice.get("message") or {}
            return {
                "ok": True,
                "content": msg.get("content") or "",
                "finish_reason": choice.get("finish_reason"),
                "provider": data.get("provider"),
                "model_served": data.get("model"),
                "usage": data.get("usage"),
                "id": data.get("id"),
            }
        return {"ok": False, **last}
