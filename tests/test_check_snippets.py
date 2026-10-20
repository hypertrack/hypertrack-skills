"""check_snippets.py must never report success for a failed or skipped compile."""

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock

TOOL = Path(__file__).resolve().parent.parent / "tools/check_snippets.py"
spec = importlib.util.spec_from_file_location("check_snippets", TOOL)
check_snippets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_snippets)


def proc(code, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=["compiler"], returncode=code, stdout=stdout, stderr=stderr)


class FailureTextTest(unittest.TestCase):
    def test_success_is_empty(self):
        self.assertEqual(check_snippets.failure_text(proc(0, stderr="warning: something")), "")

    def test_nonzero_exit_without_diagnostics_still_fails(self):
        text = check_snippets.failure_text(proc(137, stderr="Killed\n"), diagnostics="")
        self.assertEqual(text, "Killed")

    def test_nonzero_exit_without_any_output_fails(self):
        self.assertIn("status 1", check_snippets.failure_text(proc(1)))

    def test_diagnostics_preferred_over_raw_output(self):
        text = check_snippets.failure_text(proc(1, stderr="noise\nx.kt:1: error: boom"), diagnostics="x.kt:1: error: boom")
        self.assertEqual(text, "x.kt:1: error: boom")


class MissingToolchainTest(unittest.TestCase):
    blocks = [(Path("references/a.md"), "code"), (Path("references/b.md"), "code")]

    def setUp(self):
        patcher = mock.patch.object(check_snippets, "log")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_xcode_fails_every_swift_block(self):
        with mock.patch.object(check_snippets, "blocks", return_value=self.blocks), \
                mock.patch.object(check_snippets.shutil, "which", return_value=None):
            self.assertEqual(check_snippets.check_swift(), 2)

    def test_missing_jdk_fails_every_kotlin_block(self):
        with mock.patch.object(check_snippets, "blocks", return_value=self.blocks), \
                mock.patch.object(check_snippets, "java_home", return_value=None), \
                mock.patch.object(check_snippets, "android_jar", return_value=None):
            self.assertEqual(check_snippets.check_kotlin(), 2)

    def test_missing_npm_fails_every_ts_block(self):
        with mock.patch.object(check_snippets, "blocks", return_value=self.blocks), \
                mock.patch.object(check_snippets.shutil, "which", return_value=None):
            self.assertEqual(check_snippets.check_ts(), 2)


if __name__ == "__main__":
    unittest.main()
