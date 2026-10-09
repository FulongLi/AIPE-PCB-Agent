"""Tests for the Engineering Knowledge System V0.

These tests run without network access and without the raw reference cache.
Checks that need cached manufacturer files report "skipped" in that case and
the tests assert that they never turn into a pass.
"""

import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from automation.knowledge import acquire, allegro_netlist, check_evidence, inspect_sources, odb_netlist, query, validate
from automation.knowledge.common import CACHE, KNOWLEDGE, ROOT, load_json, sha256_file
from automation.knowledge.schema_check import SchemaError, Validator

BUCK_RELEASE = ROOT / "examples" / "buck-48v-24v-1kw" / "releases" / "v1"


class SchemaValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        (self.dir / "common.schema.json").write_text(json.dumps({"$defs": {"id": {"type": "string", "pattern": "^X-\\d+$"}}}))
        (self.dir / "thing.schema.json").write_text(json.dumps({
            "type": "object", "additionalProperties": False, "required": ["id", "tags"],
            "properties": {"id": {"$ref": "common.schema.json#/$defs/id"},
                           "tags": {"type": "array", "minItems": 1, "items": {"enum": ["a", "b"]}},
                           "value": {"anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]}}}))
        self.validator = Validator(self.dir)

    def test_valid_instance(self):
        self.assertEqual(self.validator.validate({"id": "X-1", "tags": ["a"], "value": None}, "thing.schema.json"), [])

    def test_each_constraint_is_enforced(self):
        cases = {
            "missing required": {"id": "X-1"},
            "cross-file pattern": {"id": "Y-1", "tags": ["a"]},
            "enum": {"id": "X-1", "tags": ["c"]},
            "minItems": {"id": "X-1", "tags": []},
            "additionalProperties": {"id": "X-1", "tags": ["a"], "extra": 1},
            "anyOf": {"id": "X-1", "tags": ["a"], "value": -1},
        }
        for label, instance in cases.items():
            with self.subTest(label):
                self.assertTrue(self.validator.validate(instance, "thing.schema.json"))

    def test_unsupported_keyword_is_an_error_not_ignored(self):
        (self.dir / "bad.schema.json").write_text(json.dumps({"type": "string", "format": "email"}))
        with self.assertRaises(SchemaError):
            self.validator.validate("x", "bad.schema.json")

    def test_cross_check_with_jsonschema_when_installed(self):
        try:
            import jsonschema
            from referencing import Registry, Resource
        except ImportError:
            self.skipTest("optional jsonschema/referencing not installed")
        schema_dir = KNOWLEDGE / "schemas"
        registry = Registry().with_resources(
            (p.name, Resource.from_contents(load_json(p))) for p in schema_dir.glob("*.json"))
        pairs = [("reference.schema.json", KNOWLEDGE.glob("references/*/*/reference.json")),
                 ("skill.schema.json", KNOWLEDGE.glob("skills/*/SKILL-*.json")),
                 ("circuit_block.schema.json", KNOWLEDGE.glob("circuit_blocks/*/CB-*.json")),
                 ("component.schema.json", KNOWLEDGE.glob("components/*/CMP-*.json")),
                 ("engineering_rules.schema.json", [KNOWLEDGE / "rules" / "engineering_rules.json"])]
        for schema_name, paths in pairs:
            checker = jsonschema.Draft202012Validator(load_json(schema_dir / schema_name), registry=registry)
            for path in paths:
                with self.subTest(path=path.name):
                    self.assertEqual([e.message for e in checker.iter_errors(load_json(path))], [])


class KnowledgeBaseValidationTests(unittest.TestCase):
    def test_committed_knowledge_validates(self):
        report = validate.validate()
        self.assertEqual(report["errors"], [])
        counts = report["info"]["counts"]
        self.assertEqual(counts["references"], 4)
        self.assertEqual(counts["skills"], 6)
        self.assertGreaterEqual(counts["blocks"], 10)
        self.assertGreaterEqual(counts["components"], 15)
        self.assertGreaterEqual(counts["rules"], 30)

    def test_part_numbers_confirmed_or_explicitly_skipped(self):
        report = validate.validate()
        numbers = report["info"]["part_numbers"]
        self.assertEqual(numbers["not_found"], 0)
        self.assertEqual(numbers["confirmed"] + numbers["skipped"], report["info"]["counts"]["components"])
        if CACHE.exists():
            self.assertEqual(numbers["skipped"], 0)

    def test_every_reference_document_is_traceable(self):
        for path in KNOWLEDGE.glob("references/*/*/reference.json"):
            for document in load_json(path)["documents"]:
                with self.subTest(document=document["id"]):
                    self.assertTrue(document["source_url"].startswith("https://"))
                    acquisition = document["acquisition"]
                    self.assertIn(acquisition["status"], ("downloaded", "failed"))
                    if acquisition["status"] == "downloaded":
                        self.assertRegex(acquisition["sha256"], "^[0-9a-f]{64}$")
                        self.assertRegex(acquisition["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
                    self.assertNotEqual(document["revision"], "")

    def test_cached_files_match_recorded_checksums(self):
        checked = 0
        for path in KNOWLEDGE.glob("references/*/*/reference.json"):
            for document in load_json(path)["documents"]:
                local = ROOT / document["acquisition"].get("cache_path", "missing")
                if document["acquisition"]["status"] == "downloaded" and local.exists():
                    self.assertEqual(sha256_file(local), document["acquisition"]["sha256"], local.name)
                    checked += 1
        if not checked:
            self.skipTest("reference cache not present; run automation.knowledge.acquire")

    def mutated_copy(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "knowledge"
        shutil.copytree(KNOWLEDGE, root)
        return root

    def edit_rule(self, root, rule_id, change):
        path = root / "rules" / "engineering_rules.json"
        data = load_json(path)
        for rule in data["rules"]:
            if rule["id"] == rule_id:
                change(rule)
        path.write_text(json.dumps(data))

    def test_single_reference_observation_cannot_be_hard_constraint(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-CAP-003", lambda r: r.update(category="hard-constraint"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("single-reference observation cannot be a hard constraint" in e for e in errors))

    def test_multi_source_claim_needs_two_references(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-SN-003", lambda r: r.update(generality="multi-source-consistent"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("KR-SN-003: multi-source-consistent" in e for e in errors))

    def test_analytically_checked_requires_a_cited_check(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-GD-012", lambda r: r.update(validation_status="analytically-checked"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("KR-GD-012: analytically-checked without any cited evidence check" in e for e in errors))

    def test_hardware_validation_cannot_be_claimed_in_v0(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-GD-001", lambda r: r.update(validation_status="hardware-validated"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("hardware-validated claimed" in e for e in errors))

    def test_unknown_evidence_source_is_rejected(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-GD-001", lambda r: r["evidence"][0].update(source="REF-XX-MADE-UP"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("unknown evidence source REF-XX-MADE-UP" in e for e in errors))

    def test_hard_constraint_limit_needs_non_instance_basis(self):
        root = self.mutated_copy()
        self.edit_rule(root, "KR-CAP-001", lambda r: r["numerical_limits"][0].update(basis_type="reference-design-instance"))
        errors = validate.validate(root, cache=root / "no-cache")["errors"]
        self.assertTrue(any("rests on a design instance" in e for e in errors))

    def test_skill_documents_contain_required_sections(self):
        for path in KNOWLEDGE.glob("skills/*/SKILL-*.md"):
            text = path.read_text(encoding="utf-8")
            for section in validate.SKILL_SECTIONS:
                with self.subTest(skill=path.name, section=section):
                    self.assertIn(f"## {section}", text)

    def test_conflicts_are_preserved(self):
        rules = {r["id"]: r for r in load_json(KNOWLEDGE / "rules" / "engineering_rules.json")["rules"]}
        self.assertGreaterEqual(len(rules["KR-GD-004"]["conflicts"]), 2)  # 1 us vs ~46 ns blanking
        self.assertTrue(rules["KR-IS-001"]["conflicts"])  # TI factor-2 gate power expression
        self.assertTrue(rules["KR-GD-005"]["conflicts"])  # 0 V turn-off acceptable after evaluation


class EvidenceCheckTests(unittest.TestCase):
    def test_calculations_pass_and_netlist_checks_never_fail(self):
        report = check_evidence.run_all()
        for entry in report["checks"]:
            with self.subTest(check=entry["id"]):
                if entry["kind"] == "calculation":
                    self.assertIn(entry["status"], ("pass", "computed"))
                else:
                    self.assertIn(entry["status"], ("pass", "skipped"))

    def test_stored_results_reproduce(self):
        stored = {c["id"]: c for c in load_json(check_evidence.RESULTS)["checks"]}
        for entry in check_evidence.run_all()["checks"]:
            with self.subTest(check=entry["id"]):
                if entry["status"] == "skipped":
                    self.assertEqual(stored[entry["id"]]["status"], "pass", "stored netlist result must come from a real run")
                else:
                    self.assertEqual(entry, stored[entry["id"]])

    def test_desat_values_match_wolfspeed(self):
        self.assertAlmostEqual(check_evidence.desat_trip()["computed"], 6.7, places=6)
        self.assertAlmostEqual(check_evidence.desat_blanking()["computed"], 45.9, delta=0.1)


class ParserTests(unittest.TestCase):
    def test_allegro_netlist(self):
        text = ("FILE_TYPE = EXPANDEDNETLIST;\nNET_NAME\n'GATE'\n '@X':\n C_SIGNAL='@x',\n NET_SPACING_TYPE='LOW-SIDE';\n"
                "NODE_NAME\tR1 2\n '@R':\n '2':;\nNODE_NAME\tU1 4\n '@U':\n 'OUTH':;\n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pstxnet.dat"
            path.write_text(text)
            nets = allegro_netlist.parse(path)
        self.assertTrue(allegro_netlist.connected(nets, ("R1", "2"), ("U1", "4")))
        self.assertEqual(allegro_netlist.spacing_classes(nets), {"LOW-SIDE": 1})

    def test_odb_connectivity(self):
        eda = "PKG P0 0 0 0 0 0\nPIN 1 S 0 0 0 U U\nPIN 2 S 0 0 0 U U\nNET A\nSNT TOP T 0 0\nNET B\nSNT TOP T 0 1\nSNT TOP T 1 0\n"
        top = "CMP 0 0 0 0 N D1 diode\nCMP 0 0 0 0 N R1 res\n"
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "odb.tgz"
            with tarfile.open(archive, "w:gz") as bundle:
                for name, body in (("odb/steps/pcb/eda/data", eda), ("odb/steps/pcb/layers/comp_+_top/components", top)):
                    info = tarfile.TarInfo(name)
                    info.size = len(body)
                    bundle.addfile(info, io.BytesIO(body.encode()))
            nets = odb_netlist.connectivity(archive)
        self.assertEqual(odb_netlist.nets_of(nets, "D1"), {"1": "A", "2": "B"})
        self.assertEqual(odb_netlist.nets_of(nets, "R1"), {"1": "B"})


class AcquisitionTests(unittest.TestCase):
    def test_html_error_page_is_not_accepted_as_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "doc.pdf"

            def fake_download(url, path, timeout=120):
                path.write_bytes(b"<!DOCTYPE html><html>login</html>")
                return url
            with patch.object(acquire, "download", side_effect=fake_download):
                record = acquire.acquire_file("https://example.com/doc.pdf", target, "pdf", {}, True, "2026-10-09")
        self.assertEqual(record["status"], "failed")
        self.assertIn("not a pdf", record["error"])
        self.assertFalse(target.exists())

    def test_network_error_on_refresh_keeps_cached_copy(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "doc.pdf"
            target.write_bytes(b"%PDF-1.7 cached")
            previous = {"status": "downloaded", "retrieved": "2026-10-01", "sha256": "0" * 64}
            with patch.object(acquire, "download", side_effect=urllib.error.URLError("offline")):
                record = acquire.acquire_file("https://example.com/doc.pdf", target, "pdf", previous, True, "2026-10-09")
            self.assertEqual(record["status"], "failed")
            self.assertTrue(target.exists())
            self.assertIn("previous successful acquisition", record["note"])

    def test_zip_member_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "evil.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../escape.txt", "x")
            with self.assertRaises(ValueError):
                inspect_sources.safe_extract(archive, Path(folder) / "out")
            self.assertFalse((Path(folder) / "escape.txt").exists())

    def test_member_classification(self):
        self.assertEqual(inspect_sources.classify("Gerber/BOARD.GTL"), "gerber")
        self.assertEqual(inspect_sources.classify("NC Drill/BOARD-RoundHoles.TXT"), "drill")
        self.assertEqual(inspect_sources.classify("CAD/board.PcbDoc"), "altium-project")
        self.assertEqual(inspect_sources.classify("allegro/pstxnet.dat"), "allegro-netlist")


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = query.KnowledgeBase.load()

    def ids(self, question, limit=6, types=None):
        return [hit["id"] for hit in self.kb.search(question, limit=limit, types=types)]

    def test_layout_question(self):
        ids = self.ids("What are the recommended layout practices for an isolated SiC gate driver?")
        self.assertEqual(ids[0], "SKILL-002")
        self.assertTrue(any(i.startswith("KR-PCB") for i in ids))

    def test_dc_link_question(self):
        ids = self.ids("What should be considered when selecting DC-link capacitors?")
        self.assertEqual(ids[0], "SKILL-003")
        self.assertIn("KR-CAP-001", ids)

    def test_current_sensing_question(self):
        ids = self.ids("What reusable current-sensing circuits are available for a high-voltage converter?", types={"block"})
        self.assertEqual(ids[0], "CB-SN-003")
        self.assertIn("CB-SN-004", ids)

    def test_hits_carry_traceability(self):
        hit = self.kb.search("DESAT blanking time", limit=1)[0]
        for key in ("id", "type", "path", "sources", "validation_status", "snippet"):
            self.assertIn(key, hit)
        self.assertTrue(hit["sources"])

    def test_get_and_related(self):
        self.assertEqual(self.kb.get("CB-SN-003")["type"], "block")
        self.assertIn("SKILL-005", self.kb.related("CB-SN-003")["skills"])
        self.assertIsNone(self.kb.get("CB-XX-999"))

    def test_demo_file_is_current(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "demo.md"
            query.write_demo(self.kb, target)
            self.assertEqual(target.read_text(encoding="utf-8"),
                             (KNOWLEDGE / "examples" / "retrieval-demo.md").read_text(encoding="utf-8"))


class RepositoryBoundaryTests(unittest.TestCase):
    def git(self, *args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            self.skipTest(f"git unavailable: {error}")

    def test_frozen_buck_v1_matches_its_manifest(self):
        manifest = load_json(BUCK_RELEASE / "SHA256SUMS.json")
        self.assertGreater(len(manifest["files"]), 100)
        for name, expected in manifest["files"].items():
            with self.subTest(file=name):
                path = BUCK_RELEASE / name
                self.assertEqual(path.stat().st_size, expected["bytes"])
                self.assertEqual(sha256_file(path), expected["sha256"])

    def test_buck_example_unchanged_against_main(self):
        if "main" not in self.git("branch", "--list", "main"):
            self.skipTest("no local main branch")
        changed = self.git("diff", "--name-only", "main", "--", "examples/buck-48v-24v-1kw")
        self.assertEqual(changed.strip(), "")

    def test_no_raw_third_party_files_are_tracked(self):
        tracked = self.git("ls-files", "knowledge").split()
        raw = [p for p in tracked if Path(p).suffix.lower() in
               {".pdf", ".zip", ".xlsx", ".step", ".dsn", ".brd", ".pcbdoc", ".schdoc", ".gbr", ".dat", ".t_g_z"}]
        self.assertEqual(raw, [])

    def test_reference_cache_is_git_ignored(self):
        result = subprocess.run(["git", "check-ignore", ".cache/references/REF-TI-TIDA-010054/tidues0.pdf"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
