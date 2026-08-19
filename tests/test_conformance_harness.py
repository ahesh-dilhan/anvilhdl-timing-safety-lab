from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import anvil_conformance  # noqa: E402


class ConformanceHarnessTests(unittest.TestCase):
    def test_parser_finds_json_after_non_json_output(self) -> None:
        result = anvil_conformance.parse_json_output(
            'debug line\n{"success":true,"errors":[],"output":""}\n'
        )
        self.assertTrue(result["success"])

    def test_parser_rejects_json_without_success_boolean(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not contain"):
            anvil_conformance.parse_json_output('{"success":"false"}')

    def test_diagnostic_text_flattens_text_fragments(self) -> None:
        result = {
            "errors": [
                {
                    "description": [
                        {"kind": "text", "text": "first"},
                        {"kind": "codespan", "text": None},
                        {"kind": "text", "text": "second"},
                    ]
                }
            ]
        }
        self.assertEqual(anvil_conformance.diagnostic_text(result), "first\nsecond")

    def test_json_success_field_overrides_zero_process_exit(self) -> None:
        payload = {
            "success": False,
            "errors": [
                {
                    "type": "error",
                    "path": None,
                    "description": [
                        {
                            "kind": "text",
                            "text": "Attempted assignment to a borrowed register!",
                        }
                    ],
                }
            ],
            "output": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake_anvil.py"
            fake.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n"
                "raise SystemExit(0)\n",
                encoding="utf-8",
            )
            case = {
                "path": "anvil/unsafe/mutate_while_loaned.anvil",
                "expect": "fail",
                "concept": "borrow check",
                "diagnostic_any": ["borrowed register"],
            }
            passed, detail = anvil_conformance.run_case(
                [sys.executable, str(fake)], case
            )

        self.assertTrue(passed, detail)
        self.assertIn("process exit=0", detail)

    def test_expected_pass_requires_zero_process_exit(self) -> None:
        payload = {"success": True, "errors": [], "output": "module ok;"}
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake_anvil.py"
            fake.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n"
                "raise SystemExit(17)\n",
                encoding="utf-8",
            )
            case = {
                "path": "anvil/safe/fixed_lifetime_spacing.anvil",
                "expect": "pass",
                "concept": "accepted program",
            }
            passed, detail = anvil_conformance.run_case(
                [sys.executable, str(fake)], case
            )

        self.assertFalse(passed)
        self.assertIn("reported success", detail)
        self.assertIn("exit=17", detail)

    def test_expectation_mismatch_includes_compiler_diagnostic(self) -> None:
        payload = {
            "success": False,
            "errors": [
                {
                    "description": [
                        {"kind": "text", "text": "precise type error"}
                    ]
                }
            ],
            "output": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake_anvil.py"
            fake.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n"
                "raise SystemExit(0)\n",
                encoding="utf-8",
            )
            case = {
                "path": "anvil/safe/fixed_lifetime_spacing.anvil",
                "expect": "pass",
                "concept": "accepted program",
            }
            passed, detail = anvil_conformance.run_case(
                [sys.executable, str(fake)], case
            )

        self.assertFalse(passed)
        self.assertIn("precise type error", detail)

    def test_expected_rejection_rejects_abnormal_process_exit(self) -> None:
        payload = {
            "success": False,
            "errors": [
                {
                    "description": [
                        {"kind": "text", "text": "borrowed register"}
                    ]
                }
            ],
            "output": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake_anvil.py"
            fake.write_text(
                "import json\n"
                f"print(json.dumps({payload!r}))\n"
                "raise SystemExit(17)\n",
                encoding="utf-8",
            )
            case = {
                "path": "anvil/unsafe/mutate_while_loaned.anvil",
                "expect": "fail",
                "concept": "borrow check",
                "diagnostic_any": ["borrowed register"],
            }
            passed, detail = anvil_conformance.run_case(
                [sys.executable, str(fake)], case
            )

        self.assertFalse(passed)
        self.assertIn("source rejection", detail)
        self.assertIn("exit=17", detail)

    def test_configured_compiler_command_is_shell_split(self) -> None:
        with patch.dict(
            os.environ,
            {"ANVIL_COMMAND": f"{sys.executable} -I"},
            clear=False,
        ):
            self.assertEqual(
                anvil_conformance.compiler_command(), [sys.executable, "-I"]
            )

    def test_empty_configured_compiler_command_is_rejected(self) -> None:
        with patch.dict(os.environ, {"ANVIL_COMMAND": "   "}, clear=False):
            with self.assertRaisesRegex(FileNotFoundError, "is empty"):
                anvil_conformance.compiler_command()


if __name__ == "__main__":
    unittest.main()
