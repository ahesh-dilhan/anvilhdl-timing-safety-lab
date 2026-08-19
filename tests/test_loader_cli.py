from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from anvil_lab.cli import main
from anvil_lab.loader import ScenarioFormatError, load_scenario, scenario_from_dict


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"


def minimal_data() -> dict[str, object]:
    return {
        "name": "minimal",
        "description": "one fixed event",
        "expected": "safe",
        "events": [{"id": "tick", "delay": {"fixed": 0}}],
    }


class LoaderTests(unittest.TestCase):
    def test_minimal_scenario_loads_from_dict(self) -> None:
        scenario = scenario_from_dict(minimal_data())
        self.assertEqual(scenario.name, "minimal")
        self.assertEqual(scenario.dag.schedule_count, 1)
        self.assertTrue(scenario.expected_safe)

    def test_event_point_string_and_object_forms_load(self) -> None:
        data = minimal_data()
        data["lifetimes"] = [
            {
                "id": "life",
                "resource": "x",
                "interval": {
                    "start": "tick",
                    "end": {"event": "tick", "offset": 1},
                },
            }
        ]
        scenario = scenario_from_dict(data)
        self.assertEqual(scenario.lifetimes[0].interval.end.offset, 1)

    def test_missing_required_field_has_context(self) -> None:
        with self.assertRaisesRegex(ScenarioFormatError, "missing required field 'name'"):
            scenario_from_dict({"events": []})

    def test_invalid_delay_is_reported_as_scenario_format_error(self) -> None:
        data = minimal_data()
        data["events"] = [{"id": "tick", "delay": {"min": 3, "max": 1}}]
        with self.assertRaisesRegex(ScenarioFormatError, "delay maximum"):
            scenario_from_dict(data)

    def test_unknown_root_field_is_rejected(self) -> None:
        data = minimal_data()
        data["loan"] = []
        with self.assertRaisesRegex(ScenarioFormatError, "unknown field: 'loan'"):
            scenario_from_dict(data)

    def test_unknown_event_field_is_rejected(self) -> None:
        data = minimal_data()
        data["events"] = [{"id": "tick", "delai": 2}]
        with self.assertRaisesRegex(ScenarioFormatError, "unknown field: 'delai'"):
            scenario_from_dict(data)

    def test_unknown_nested_interval_field_is_rejected(self) -> None:
        data = minimal_data()
        data["lifetimes"] = [
            {
                "id": "life",
                "resource": "x",
                "interval": {"start": "tick", "end": "tick", "inclusive": True},
            }
        ]
        with self.assertRaisesRegex(ScenarioFormatError, "unknown field: 'inclusive'"):
            scenario_from_dict(data)

    def test_use_without_lifetime_is_rejected(self) -> None:
        data = minimal_data()
        data["uses"] = [
            {
                "id": "read",
                "resource": "unknown",
                "interval": {"start": "tick", "end": "tick"},
            }
        ]
        with self.assertRaisesRegex(ScenarioFormatError, "without a lifetime"):
            scenario_from_dict(data)

    def test_promise_resource_is_optional_and_loaded_when_present(self) -> None:
        data = minimal_data()
        data["lifetimes"] = [
            {
                "id": "life",
                "resource": "payload",
                "interval": {
                    "start": "tick",
                    "end": {"event": "tick", "offset": 1},
                },
            }
        ]
        data["promises"] = [
            {
                "id": "send",
                "message": "stream.out",
                "resource": "payload",
                "interval": {
                    "start": "tick",
                    "end": {"event": "tick", "offset": 1},
                },
            },
            {
                "id": "barrier",
                "message": "stream.control",
                "interval": {"start": "tick", "end": "tick"},
            },
        ]
        scenario = scenario_from_dict(data)
        self.assertEqual(scenario.promises[0].resource, "payload")
        self.assertIsNone(scenario.promises[1].resource)

    def test_promise_resource_without_lifetime_is_rejected(self) -> None:
        data = minimal_data()
        data["promises"] = [
            {
                "id": "send",
                "message": "stream.out",
                "resource": "missing",
                "interval": {"start": "tick", "end": "tick"},
            }
        ]
        with self.assertRaisesRegex(ScenarioFormatError, "without a lifetime"):
            scenario_from_dict(data)

    def test_invalid_json_reports_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"name":', encoding="utf-8")
            with self.assertRaisesRegex(ScenarioFormatError, "line 1"):
                load_scenario(path)

    def test_all_bundled_experiments_match_expectations(self) -> None:
        from anvil_lab.oracle import analyze

        paths = sorted(EXPERIMENTS.glob("*.json"))
        self.assertEqual(len(paths), 5)
        results = [analyze(load_scenario(path)) for path in paths]
        self.assertEqual(
            [result.safe for result in results], [True, False, False, False, False]
        )
        self.assertTrue(all(result.expectation_matches for result in results))
        self.assertEqual(
            [result.schedules_checked for result in results], [3, 3, 2, 2, 1]
        )
        self.assertEqual(
            [len(result.violations) for result in results], [0, 2, 2, 1, 1]
        )

    def test_bundled_counterexample_boundaries_are_stable(self) -> None:
        from anvil_lab.oracle import analyze

        early = analyze(
            load_scenario(EXPERIMENTS / "02_early_address_mutation.json")
        )
        early_delays = {
            violation.schedule.delays["lookup_done"]
            for violation in early.violations
            if violation.kind == "register_mutation_loan"
        }
        self.assertEqual(early_delays, {2, 3})

        overlap = analyze(load_scenario(EXPERIMENTS / "04_overlapping_send.json"))
        overlap_delays = {
            violation.schedule.delays["send_b_start"]
            for violation in overlap.violations
            if violation.kind == "message_promise_overlap"
        }
        self.assertEqual(overlap_delays, {2})


class CliTests(unittest.TestCase):
    def run_cli(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(arguments)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_one_file_readable_output(self) -> None:
        path = EXPERIMENTS / "02_early_address_mutation.json"
        status, stdout, stderr = self.run_cli([str(path)])
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("[UNSAFE] early_address_mutation", stdout)
        self.assertIn("register_mutation_loan", stdout)
        self.assertIn("2/3 schedules", stdout)

    def test_safe_readable_output_is_explicitly_bounded(self) -> None:
        path = EXPERIMENTS / "01_safe_dynamic_cache.json"
        status, stdout, stderr = self.run_cli([str(path)])
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertIn("[BOUNDED SAFE] safe_dynamic_cache", stdout)

    def test_all_json_output_is_machine_readable(self) -> None:
        status, stdout, _ = self.run_cli(
            ["--all", "--experiments-dir", str(EXPERIMENTS), "--json"]
        )
        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["summary"]["scenarios"], 5)
        self.assertEqual(payload["summary"]["unsafe"], 4)
        self.assertNotIn("schedules", payload["results"][0])

    def test_show_schedules_in_json(self) -> None:
        path = EXPERIMENTS / "01_safe_dynamic_cache.json"
        status, stdout, _ = self.run_cli([str(path), "--json", "--show-schedules"])
        payload = json.loads(stdout)
        self.assertEqual(status, 0)
        self.assertEqual(len(payload["results"][0]["schedules"]), 3)

    def test_fail_on_unsafe_returns_one(self) -> None:
        path = EXPERIMENTS / "04_overlapping_send.json"
        status, _, _ = self.run_cli([str(path), "--fail-on-unsafe"])
        self.assertEqual(status, 1)

    def test_fail_on_mismatch_accepts_expected_unsafe_scenarios(self) -> None:
        status, _, _ = self.run_cli(
            [
                "--all",
                "--experiments-dir",
                str(EXPERIMENTS),
                "--fail-on-mismatch",
            ]
        )
        self.assertEqual(status, 0)

    def test_fail_on_mismatch_returns_one_for_wrong_expectation(self) -> None:
        data = minimal_data()
        data["expected"] = "unsafe"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mismatch.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            status, _, _ = self.run_cli([str(path), "--fail-on-mismatch"])
        self.assertEqual(status, 1)

    def test_missing_file_returns_usage_error(self) -> None:
        status, _, stderr = self.run_cli(["does-not-exist.json"])
        self.assertEqual(status, 2)
        self.assertIn("cannot read", stderr)

    def test_all_and_explicit_file_are_rejected(self) -> None:
        path = EXPERIMENTS / "01_safe_dynamic_cache.json"
        status, _, stderr = self.run_cli(
            ["--all", "--experiments-dir", str(EXPERIMENTS), str(path)]
        )
        self.assertEqual(status, 2)
        self.assertIn("cannot be combined", stderr)


if __name__ == "__main__":
    unittest.main()
