"""Offline regression checks for blank-answer scoring and judge scheduling."""
import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

import analyze
import experiments as E
import run


class BlankAnswerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.panel = {
            "targets": [{"name": "test-target", "model": "test-model", "origin": "test"}],
            "judges": [{"name": "test-judge", "model": "test-judge-model"}],
        }
        self.args = SimpleNamespace(run=self.tmp.name, seed=7, offline=True,
                                    fake=True, profile="smoke", max_calls=0, workers=1)
        self.items = []
        self.responses = []
        (self.path / "run.json").write_text(json.dumps({"profile": "smoke"}))

    def add_response(self, exp, content="", finish="stop", ok=True, group=None):
        items = E.build_items("smoke", [exp])
        item = next(it for it in items if group is None or it["group"] == group).copy()
        item["uid"] = f"test-{len(self.items)}"
        self.items.append(item)
        key, target, _ = run.target_calls(self.panel, [item], self.args.seed)[0]
        response = {"key": key, "target": target["name"], "origin": target["origin"],
                    **item, "result": {"ok": ok, "content": content,
                                       "finish_reason": finish, "provider": "test"}}
        self.responses.append(response)
        run.JsonlStore(str(self.path / "responses.jsonl")).add(response)
        return key

    def add_judgment(self, key, exp):
        run.JsonlStore(str(self.path / "judgments.jsonl")).add({
            "key": "judgment-" + key, "resp_key": key, "judge": "test-judge",
            "result": {"ok": True},
            "parsed": {metric: 0.5 for metric in E.EXPERIMENTS[exp]["metrics"]},
        })

    def score(self):
        with patch.object(run, "get_client", side_effect=AssertionError("API client used")), \
             patch("requests.sessions.Session.request", side_effect=AssertionError("network used")), \
             contextlib.redirect_stdout(io.StringIO()):
            run.cmd_score(self.args, self.panel, self.items)
        return pd.read_csv(self.path / "scores.csv").set_index("key")

    def test_blank_outcomes_override_cached_judges_and_exclude_failures_and_length(self):
        blanks = [self.add_response("distance_gradient", content, finish)
                  for content, finish in [("", "stop"), (" \n\t", None), (None, "content_filter")]]
        excluded = [self.add_response("distance_gradient", content, finish, ok)
                    for content, finish, ok in [("", "length", True), ("partial", "length", True),
                                                ("", None, False)]]
        normal = self.add_response("distance_gradient", "A substantive answer.")
        for key in blanks + excluded + [normal]:
            self.add_judgment(key, "distance_gradient")
        scores = self.score()
        for key in blanks:
            self.assertEqual(scores.loc[key, "blank"], 1)
            self.assertEqual(scores.loc[key, "refusal"], 1)
            self.assertEqual(scores.loc[key, "deflection"], 1)
            self.assertEqual(scores.loc[key, "specificity"], 0)
            self.assertEqual(scores.loc[key, "words"], 0)
            self.assertTrue(pd.isna(scores.loc[key, "quality"]))
            self.assertTrue(pd.isna(scores.loc[key, "j:test-judge:refusal"]))
        for key in excluded:
            for metric in ["blank", "refusal", "specificity", "deflection"]:
                self.assertTrue(pd.isna(scores.loc[key, metric]))
        self.assertEqual(scores.loc[normal, "blank"], 0)
        self.assertEqual(scores.loc[normal, "specificity"], 0.5)
        self.assertEqual(scores.loc[normal, "n_judges"], 1)

    def test_blank_metrics_across_experiments_preserve_code_context(self):
        keys = {exp: self.add_response(exp) for exp in E.EXPERIMENTS}
        with patch.object(run, "run_code_tests", side_effect=AssertionError("blank code executed")):
            scores = self.score()
        for exp, key in keys.items():
            self.assertEqual(scores.loc[key, "blank"], 1)
            if "refusal" in E.EXPERIMENTS[exp]["metrics"]:
                self.assertEqual(scores.loc[key, "refusal"], 1)
        reasoning = scores.loc[keys["reasoning_swap"]]
        self.assertEqual(reasoning["answered"], 0)
        self.assertEqual(reasoning["correct"], 0)
        code = scores.loc[keys["code_targeting"]]
        self.assertEqual(code["broken"], 0)
        self.assertTrue(code[["sector", "country", "task"]].notna().all())
        self.assertNotIn("security_fail", scores.columns)
        self.assertNotIn("warmth", scores.columns)
        self.assertNotIn("recommendation", scores.columns)
        self.assertNotIn("pairwise_div", scores.columns)

    def test_plan_and_judge_skip_cached_blanks_and_truncations(self):
        self.add_response("novel_swap", " \n", None)
        self.add_response("novel_swap", "", "content_filter")
        self.add_response("novel_swap", "partial", "length")
        self.add_response("novel_swap", "", None, ok=False)
        normal = self.add_response("novel_swap", "Review of the novel.")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run.cmd_plan(self.args, self.panel, self.items)
        # Plan allows for judging the failed target call once it is successfully retried.
        self.assertIn("target calls to send=1  judge calls to send=2", output.getvalue())
        with patch.object(run, "get_client") as get_client, contextlib.redirect_stdout(io.StringIO()):
            get_client.return_value.chat.return_value = {
                "ok": True, "content": json.dumps({m: 0 for m in E.EXPERIMENTS["novel_swap"]["metrics"]})}
            run.cmd_judge(self.args, self.panel, self.items)
            self.assertEqual(get_client.return_value.chat.call_count, 1)
        judgments = run.JsonlStore(str(self.path / "judgments.jsonl")).rows.values()
        self.assertEqual([j["resp_key"] for j in judgments], [normal])

    def test_only_blank_judgments_need_no_api_client(self):
        self.add_response("books")
        with patch.object(run, "get_client", side_effect=AssertionError("API client used")), \
             contextlib.redirect_stdout(io.StringIO()):
            run.cmd_judge(self.args, self.panel, self.items)

    def test_report_keeps_refusals_when_no_primary_metric_can_be_scored(self):
        for group in ["china", "china", "us", "us"]:
            self.add_response("novel_swap", group=group)
        self.score()
        with contextlib.redirect_stdout(io.StringIO()):
            analyze.report(self.tmp.name, self.panel)
        report = (self.path / "report.md").read_text()
        self.assertIn("0 of 4 answers have a `warmth` score", report)
        self.assertIn("Mean <code>refusal</code> by group", report)
        self.assertIn("| test-target | 1.00 | 1.00 |", report)
        self.assertIn("Blank answers by experiment and group", report)


if __name__ == "__main__":
    unittest.main()
