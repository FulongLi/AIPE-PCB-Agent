"""Failure-mode tests; these do NOT replace a real KiCad smoke test."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.kicad_tools.run_check import run_check
from automation.setup.detect_kicad import find_kicad_cli


class DetectionTests(unittest.TestCase):
    def test_invalid_explicit_path_does_not_fall_back_to_other_kicad(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"AIPE_KICAD_CLI": str(Path(folder) / "absent.exe")}):
                with self.assertRaises(FileNotFoundError):
                    find_kicad_cli({})

    def test_explicit_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="aipe path ") as folder:
            exe = Path(folder) / "kicad-cli.exe"
            exe.touch()
            with patch.dict(os.environ, {"AIPE_KICAD_CLI": str(exe)}):
                self.assertEqual(find_kicad_cli({}), exe.resolve())


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aipe check ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "test.kicad_pcb"
        self.source.write_text("test fixture", encoding="utf-8")
        self.cli = self.root / "kicad-cli.exe"

    def fake_process(self, returncode, produce_report=True):
        def execute(command, **kwargs):
            if produce_report:
                report = Path(command[command.index("--output") + 1])
                report.write_text(json.dumps({"violations": []}), encoding="utf-8")
            return subprocess.CompletedProcess(command, returncode, "simulated", "")
        return execute

    def test_violations_remain_failure(self):
        with patch("subprocess.run", side_effect=self.fake_process(5)):
            code, manifest = run_check("drc", self.source, self.root / "out", self.cli)
        data = json.loads(manifest.read_text())
        self.assertEqual(code, 5)
        self.assertEqual(data["status"], "failed")
        self.assertIn("--severity-all", data["command"])
        self.assertIn("--schematic-parity", data["command"])

    def test_exit_zero_without_report_cannot_pass(self):
        with patch("subprocess.run", side_effect=self.fake_process(0, False)):
            code, manifest = run_check("erc", self.source, self.root / "out", self.cli)
        self.assertNotEqual(code, 0)
        self.assertEqual(json.loads(manifest.read_text())["status"], "failed")

    def test_old_success_cannot_mask_a_failed_second_run(self):
        with patch("subprocess.run", side_effect=self.fake_process(0)):
            first_code, first = run_check("erc", self.source, self.root / "out", self.cli)
        with patch("subprocess.run", side_effect=self.fake_process(0, False)):
            second_code, second = run_check("erc", self.source, self.root / "out", self.cli)
        self.assertEqual(first_code, 0)
        self.assertNotEqual(second_code, 0)
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first.read_text())["status"], "passed")


if __name__ == "__main__":
    unittest.main()
