"""Offline regression checks; fixtures contain no device data."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_dump.py"
CONTENT = bytes(range(256)) * 300  # Cross the streaming read boundary.


class VerifyDumpTests(unittest.TestCase):
    def run_check(self, contents, expected=None, duplicate=False):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for index, data in enumerate(contents):
                path = Path(folder) / f"read{index}.bin"
                path.write_bytes(data)
                paths.append(path)
            if duplicate:
                paths.append(paths[0])
            command = [sys.executable, str(SCRIPT)]
            if expected is not None:
                command.extend(["--expected-size", str(expected)])
            return subprocess.run(
                command + [str(path) for path in paths],
                capture_output=True, text=True, timeout=10,
            )

    def test_three_matching_reads(self):
        result = self.run_check([CONTENT] * 3, expected=len(CONTENT))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("content validity remain unverified", result.stdout)

    def test_legacy_two_file_comparison_warns_about_size(self):
        result = self.run_check([CONTENT] * 2)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Expected chip size was not checked", result.stdout)

    def test_every_input_is_compared(self):
        result = self.run_check([CONTENT, CONTENT, CONTENT[:-1] + b"x"])
        self.assertEqual(result.returncode, 1)

    def test_different_sizes_fail(self):
        self.assertEqual(self.run_check([CONTENT, CONTENT[:-1]]).returncode, 1)

    def test_identical_wrong_size_fails(self):
        self.assertEqual(self.run_check([CONTENT] * 3, expected=2097152).returncode, 1)

    def test_empty_and_blank_reads_fail(self):
        for data in (b"", bytes(80000), b"\xff" * 80000):
            with self.subTest(value=data[:1]):
                self.assertEqual(self.run_check([data] * 3).returncode, 1)

    def test_duplicate_input_fails(self):
        self.assertEqual(self.run_check([CONTENT], duplicate=True).returncode, 1)

    def test_missing_files_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [str(Path(folder) / f"missing{i}.bin") for i in range(2)]
            result = subprocess.run(
                [sys.executable, str(SCRIPT)] + paths,
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)

    def test_invalid_arguments_fail(self):
        self.assertEqual(self.run_check([CONTENT]).returncode, 2)
        self.assertEqual(self.run_check([CONTENT] * 2, expected=0).returncode, 2)


if __name__ == "__main__":
    unittest.main()
