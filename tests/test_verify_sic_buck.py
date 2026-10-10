"""Tests for the two-board V2 verification and freeze tooling (pure logic on temporary trees)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from automation.scripts import verify_sic_buck as v


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, (dict, list)):
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        path.write_bytes(data if isinstance(data, bytes) else str(data).encode("utf-8"))


class VerifySicBuckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = mock.patch.object(v, "EXAMPLE", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _run(self, kind, stamp, name, status="passed", findings=0, source_bytes=b"x", deps=None):
        cad = self.root / "kicad" / v.BOARDS["power"]["dir"]
        source = cad / (name + (".kicad_sch" if kind == "erc" else ".kicad_pcb"))
        _write(source, source_bytes)
        deps = deps or {}
        for rel, content in deps.items():
            _write(cad / rel, content)
        _write(self.root / "verification" / kind / f"{stamp}-{kind}-abcd1234" / "run.json", {
            "source": str(source), "status": status, "finding_count": findings, "tool_exit_code": 0,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "dependency_sha256": {rel: hashlib.sha256(c.encode() if isinstance(c, str) else c).hexdigest() for rel, c in deps.items()},
        })

    def test_latest_run_selects_newest_manifest_for_the_named_source(self):
        self._run("erc", "20260101T000000Z", "AIPE_SiC_Buck_Power", findings=3)
        self._run("erc", "20260102T000000Z", "AIPE_SiC_Buck_Power", findings=0)
        manifest, data = v.latest_run("erc", "AIPE_SiC_Buck_Power")
        self.assertIn("20260102", manifest.parent.name)
        self.assertEqual(data["finding_count"], 0)
        with self.assertRaises(FileNotFoundError):
            v.latest_run("drc", "AIPE_SiC_Buck_Power")

    def test_check_run_detects_changed_source_and_dependency(self):
        self._run("erc", "20260101T000000Z", "AIPE_SiC_Buck_Power", deps={"libraries/AIPE.kicad_sym": "lib"})
        problems = []
        record = v.check_run("erc", "power", problems)
        self.assertEqual(problems, [])
        self.assertTrue(record["hashes_valid"])
        (self.root / "kicad/power_board/libraries/AIPE.kicad_sym").write_text("changed", encoding="utf-8")
        problems = []
        v.check_run("erc", "power", problems)
        self.assertTrue(any("dependency changed" in p for p in problems))

    def test_check_run_rejects_findings_and_missing_runs(self):
        self._run("drc", "20260101T000000Z", "AIPE_SiC_Buck_Power", findings=2)
        problems = []
        v.check_run("drc", "power", problems)
        self.assertTrue(any("zero findings" in p for p in problems))
        problems = []
        self.assertEqual(v.check_run("erc", "control", problems)["status"], "missing")
        self.assertTrue(problems)

    def test_check_exports_validates_manifest_and_artifacts(self):
        out = self.root / "manufacturing/power_board"
        _write(out / "gerber/a.gbr", b"gerber")
        _write(out / "logs/step.log", "ok")
        _write(out / "export-manifest.json", {"status": "passed", "commands": [{}] * 11, "input_sha256": {},
                                             "artifacts": {"gerber/a.gbr": {"bytes": 6, "sha256": hashlib.sha256(b"gerber").hexdigest()}}})
        problems = []
        record = v.check_exports("power", problems)
        self.assertEqual(problems, [])
        self.assertEqual(record["commands"], 11)
        self.assertTrue(record["step_models_complete"])
        (out / "gerber/a.gbr").write_bytes(b"tampered")
        problems = []
        v.check_exports("power", problems)
        self.assertTrue(any("artifact changed" in p for p in problems))

    def test_check_netlist_and_metrics(self):
        problems = []
        self.assertEqual(v.check_netlist("power", problems)["status"], "missing")
        _write(self.root / "verification/netlist_check_power.json", {"exact_match": True})
        problems = []
        self.assertEqual(v.check_netlist("power", problems)["status"], "passed")
        self.assertEqual(problems, [])
        board = self.root / "kicad/power_board/AIPE_SiC_Buck_Power.kicad_pcb"
        _write(board, b"board")
        _write(self.root / "verification/engineering_checks/layout_metrics_power.json", {"board_sha256": hashlib.sha256(b"board").hexdigest()})
        problems = []
        record = v.check_metrics("power", problems)
        self.assertTrue(record["board_hash_matches"])
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
