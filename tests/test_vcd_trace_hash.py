from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vcd_trace_hash.py"
SPEC = importlib.util.spec_from_file_location("vcd_trace_hash", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VcdTraceHashTests(unittest.TestCase):
    def test_normalization_ignores_date_block_only(self) -> None:
        first = "$date\n today\n$end\n$version\n tool\n$end\n#0\n0!\n"
        second = "$date\n tomorrow\n$end\n$version\n tool\n$end\n#0\n0!\n"
        changed_trace = second.replace("0!", "1!")

        self.assertEqual(MODULE.normalized_vcd(first), MODULE.normalized_vcd(second))
        self.assertNotEqual(
            MODULE.normalized_vcd(first), MODULE.normalized_vcd(changed_trace)
        )

    def test_unterminated_date_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unterminated"):
            MODULE.normalized_vcd("$date\n today\n")


if __name__ == "__main__":
    unittest.main()
