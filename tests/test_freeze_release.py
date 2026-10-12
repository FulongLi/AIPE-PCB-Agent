"""Tests for the generalised release freeze (pure logic on a temporary example tree; verification and git mocked)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from automation.scripts import freeze_release as fr


def _tree(root: Path) -> None:
    for folder in fr.FOLDERS:
        (root / folder).mkdir(parents=True)
        (root / folder / f"{folder}.txt").write_text(folder, encoding="utf-8")
    (root / "kicad" / "board.kicad_prl").write_text("user state", encoding="utf-8")
    (root / "simulation" / "results" / "run").mkdir(parents=True)
    (root / "simulation" / "results" / "run" / "summary.json").write_text("{}", encoding="utf-8")
    (root / "simulation" / "results" / "run" / "waveforms.csv").write_text("t,v\n", encoding="utf-8")


class FreezeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _tree(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_readme_carries_version_label_and_notes(self):
        text = fr.readme("v2.1")
        self.assertIn("AI-GENERATED ENGINEERING PROTOTYPE V2.1 - HUMAN REVIEW REQUIRED", text)
        self.assertIn("review/v2_v21_comparison.md", text)
        self.assertIn("must not be overwritten", text)
        self.assertNotIn("V2.1", fr.readme("v2").splitlines()[0])

    def test_freeze_copies_manifest_and_archive_and_refuses_twice(self):
        with mock.patch.object(fr.verify_sic_buck, "verify", return_value={"status": "passed", "problems": []}), \
                mock.patch.object(fr.subprocess, "check_output", return_value="abc123\n"):
            summary = fr.freeze("v2.1", example=self.root)
            target = self.root / "releases" / "v2.1"
            manifest = json.loads((target / "SHA256SUMS.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["release"], "v2.1")
            self.assertEqual(manifest["source_commit"], "abc123")
            self.assertEqual(summary["frozen_files"], len(manifest["files"]))
            self.assertIn("README.md", manifest["files"])
            self.assertNotIn("kicad/board.kicad_prl", manifest["files"])
            self.assertNotIn("simulation/results/run/waveforms.csv", manifest["files"])
            self.assertIn("simulation/results/run/summary.json", manifest["files"])
            with zipfile.ZipFile(summary["archive"]) as archive:
                self.assertIn("SHA256SUMS.json", archive.namelist())
            with self.assertRaises(FileExistsError):
                fr.freeze("v2.1", example=self.root)

    def test_freeze_refuses_failed_verification_and_unknown_version(self):
        with mock.patch.object(fr.verify_sic_buck, "verify", return_value={"status": "failed", "problems": ["x"]}):
            with self.assertRaises(SystemExit):
                fr.freeze("v2.1", example=self.root)
        with self.assertRaises(SystemExit):
            fr.freeze("v9", example=self.root)
        self.assertFalse((self.root / "releases").exists())


if __name__ == "__main__":
    unittest.main()
