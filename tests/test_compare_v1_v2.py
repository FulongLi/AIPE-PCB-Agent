"""Tests for automation.scripts.compare_v1_v2 (V1 versus V2 comparison report).

The metric helpers are pure Python and are tested directly. The smoke tests build the report against a
temporary repository skeleton that has only the design-phase V2 files (no boards, DRC, placement, exports
or release) and against an empty tree, and assert that nothing raises and that every absent V2 source is
reported as "not yet available". A final test runs the collector against this checkout when the example
directories exist, writing into a temporary directory so the committed review files are not touched.
"""

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from automation.scripts import compare_v1_v2 as cmp


class YamlParserTests(unittest.TestCase):
    def test_nested_mappings_scalars_lists_and_comments(self):
        text = textwrap.dedent("""\
            schema_version: 1
            label: AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED
            # a full-line comment
            converter:
              topology: synchronous_buck
              input_voltage_nominal_V: 400.0
              output_power_W: 5000
              enabled: true
            pcb:
              architecture: ai_selected   # decided elsewhere
              preferred_layer_counts:
                power_board: 2-4 where technically feasible
                control_board: 4 preferred
            knowledge:
              mandatory_outputs:
                - design/knowledge_application.md
                - review/knowledge_utilisation_report.md
            unresolved:
              input_range_V: null
              quoted: "a: b"
            inline: [1, 2.5, x]
            """)
        data = cmp.parse_simple_yaml(text)
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["label"], "AI-GENERATED ENGINEERING PROTOTYPE V2 - HUMAN REVIEW REQUIRED")
        self.assertEqual(data["converter"]["topology"], "synchronous_buck")
        self.assertEqual(data["converter"]["input_voltage_nominal_V"], 400.0)
        self.assertEqual(data["converter"]["output_power_W"], 5000)
        self.assertIs(data["converter"]["enabled"], True)
        self.assertEqual(data["pcb"]["architecture"], "ai_selected")
        self.assertEqual(data["pcb"]["preferred_layer_counts"]["control_board"], "4 preferred")
        self.assertEqual(data["knowledge"]["mandatory_outputs"], ["design/knowledge_application.md", "review/knowledge_utilisation_report.md"])
        self.assertIsNone(data["unresolved"]["input_range_V"])
        self.assertEqual(data["unresolved"]["quoted"], "a: b")
        self.assertEqual(data["inline"], [1, 2.5, "x"])

    def test_list_at_the_same_indent_as_its_key(self):
        data = cmp.parse_simple_yaml("items:\n- a\n- b\nnext: 3\n")
        self.assertEqual(data, {"items": ["a", "b"], "next": 3})

    def test_scalar_coercion(self):
        self.assertIsNone(cmp.yaml_scalar("~"))
        self.assertEqual(cmp.yaml_scalar("'quoted'"), "quoted")
        self.assertEqual(cmp.yaml_scalar("41.6666666667"), 41.6666666667)
        self.assertIs(cmp.yaml_scalar("false"), False)
        self.assertEqual(cmp.yaml_scalar("[]"), [])


class HelperTests(unittest.TestCase):
    def test_dig_tolerates_missing_keys_and_lists(self):
        data = {"a": {"b": [10, {"c": 3}]}}
        self.assertEqual(cmp.dig(data, "a", "b", 1, "c"), 3)
        self.assertEqual(cmp.dig(data, "a", "x", default="d"), "d")
        self.assertIsNone(cmp.dig(data, "a", "b", 5))
        self.assertIsNone(cmp.dig(None, "a"))

    def test_csv_summary_counts_rows_columns_and_distinct_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bom.csv"
            path.write_text("Reference,Value,Manufacturer,MPN\nJ1,VIN,Wurth,74651195\nJ2,VIN,Wurth,74651195\nC1,470u,Chemi-Con,EKY\nC2,10u,,\n", encoding="utf-8")
            summary = cmp.csv_summary(path, ("manufacturer", "MPN"))
        self.assertEqual(summary["rows"], 4)
        self.assertEqual(summary["columns"], 4)
        self.assertEqual(summary["distinct"], {"manufacturer": 2, "MPN": 2})
        self.assertIsNone(cmp.csv_summary(Path(folder) / "absent.csv"))

    def test_markdown_issue_rows_and_word_count(self):
        text = "| ID | Priority |\n|---|---|\n| V1-01 | x |\n| V1-12 | y |\n| note | z |\n"
        self.assertEqual(cmp.count_markdown_table_rows(text), 2)
        self.assertEqual(cmp.count_markdown_table_rows("| A-01 | q |\n| U-03 | r |\n| D-9 | s |", r"^\|\s*(A|U)-\d+\s*\|"), 2)
        self.assertEqual(cmp.word_count("one two  three\nfour"), 4)

    def test_count_test_functions(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / "test_a.py"
            a.write_text("def test_one():\n    pass\n\nclass T:\n    def test_two(self):\n        pass\n    def helper(self):\n        pass\n", encoding="utf-8")
            counts = cmp.count_test_functions([a, Path(folder) / "missing.py"])
        self.assertEqual(counts, {"test_a": 2})

    def test_latest_runs_picks_the_newest_per_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for stamp, source, findings in (("20261010T065851Z-erc-aaaa", "AIPE_SiC_Buck_Power.kicad_sch", 3), ("20261010T070357Z-erc-bbbb", "AIPE_SiC_Buck_Power.kicad_sch", 0),
                                            ("20261010T065853Z-erc-cccc", "AIPE_SiC_Buck_Control.kicad_sch", 0)):
                run = root / stamp
                run.mkdir()
                (run / "run.json").write_text(json.dumps({"source": f"D:/x/{source}", "status": "passed", "finding_count": findings}), encoding="utf-8")
            (root / "20261010T080000Z-erc-dddd").mkdir()
            (root / "20261010T080000Z-erc-dddd" / "run.json").write_text("not json", encoding="utf-8")
            latest = cmp.latest_runs(root, "erc")
        self.assertEqual(latest["AIPE_SiC_Buck_Power"]["finding_count"], 0)
        self.assertEqual(latest["AIPE_SiC_Buck_Power"]["run_dir"], "20261010T070357Z-erc-bbbb")
        self.assertEqual(latest["AIPE_SiC_Buck_Control"]["finding_count"], 0)
        self.assertEqual(cmp.latest_runs(root / "absent", "drc"), {})
        self.assertEqual(cmp.board_key_for_stem("AIPE_SiC_Buck_Power"), "power")
        self.assertEqual(cmp.board_key_for_stem("AIPE_SiC_Buck_Control"), "control")
        self.assertEqual(cmp.board_key_for_stem("Other"), "Other")

    def test_density_and_cost_formulas(self):
        self.assertAlmostEqual(cmp.specific_power_W_per_dm2(1000, 300 * 220), 151.515, places=2)
        self.assertAlmostEqual(cmp.volumetric_power_W_per_L(1000, 66000, 57), 265.78, places=1)
        self.assertAlmostEqual(cmp.volumetric_power_W_per_L(5000, 52800, 67), 1413.4, places=1)
        self.assertAlmostEqual(cmp.components_per_dm2(240, 66000), 36.36, places=2)
        self.assertAlmostEqual(cmp.cost_index_layer_dm2([(6, 66000)]), 39.6)
        self.assertAlmostEqual(cmp.cost_index_layer_dm2([(4, 43200), (4, 9600)]), 21.12)
        self.assertIsNone(cmp.cost_index_layer_dm2([(None, 100), (4, None)]))
        self.assertIsNone(cmp.specific_power_W_per_dm2(None, 10))
        self.assertIsNone(cmp.volumetric_power_W_per_L(10, 10, None))
        self.assertIsNone(cmp.components_per_dm2(None, 10))

    def test_board_geometry_helpers(self):
        self.assertEqual(cmp.coerce_board_mm([300.0, 220.0]), [300.0, 220.0])
        self.assertEqual(cmp.coerce_board_mm({"board_mm": [240, 180]}), [240.0, 180.0])
        self.assertEqual(cmp.coerce_board_mm({"outline": "240 x 180 target"}), [240.0, 180.0])
        self.assertEqual(cmp.coerce_board_mm({"width_mm": 120, "height_mm": 80}), [120.0, 80.0])
        self.assertIsNone(cmp.coerce_board_mm({"nothing": 1}))
        self.assertIsNone(cmp.coerce_board_mm("no size here"))
        self.assertEqual(cmp.board_area_mm2([300, 220]), 66000)
        self.assertEqual(cmp.parse_height_mm("power board on 6 x M4 x 15 mm standoffs; total height 15 + 2 + 50 = 67 mm (72 mm envelope)"), 67.0)
        self.assertEqual(cmp.parse_height_mm("height 48 mm"), 48.0)
        self.assertIsNone(cmp.parse_height_mm(None))

    def test_verification_level_buckets(self):
        self.assertEqual(cmp.bucket_verification_level("fetched-datasheet (Rev. 2, Dec 2025); status manufacturer-page"), "fetched-datasheet")
        self.assertEqual(cmp.bucket_verification_level("analytical; core data fetched-datasheet"), "fetched-datasheet")
        self.assertEqual(cmp.bucket_verification_level("manufacturer-page"), "manufacturer-page")
        self.assertEqual(cmp.bucket_verification_level("search-snippet (TDK page HTTP 403)"), "search-snippet")
        self.assertEqual(cmp.bucket_verification_level("unverified (generic)"), "unverified")
        self.assertEqual(cmp.bucket_verification_level(""), "unstated")
        self.assertEqual(cmp.bucket_verification_level("simulated"), "other")

    def test_formatting_of_metrics_pairs_ranges_and_dimensions(self):
        self.assertEqual(cmp.fmt(cmp.metric([300.0, 220.0], unit="mm", kind="dims")), "300 x 220 mm")
        self.assertEqual(cmp.fmt(cmp.metric((8.735, 16.17), unit="mm", kind="range")), "8.7-16.2 mm")
        self.assertEqual(cmp.fmt(cmp.metric([11.0, 11.0], kind="range")), "11")
        self.assertEqual(cmp.fmt(cmp.pair(10, 20)), "10 / 20")
        self.assertEqual(cmp.fmt(cmp.metric({"power": [240, 180], "control": [120, 80]}, kind="dims")), "power 240 x 180; control 120 x 80")
        self.assertEqual(cmp.fmt(cmp.metric(52800, basis="planned", unit="mm2")), "52800 mm2 (planned)")
        self.assertTrue(cmp.fmt(cmp.pending("x")).startswith(cmp.NOT_AVAILABLE))
        self.assertEqual(cmp.fmt(None), "n/a")
        self.assertEqual(cmp.fmt(True), "yes")
        self.assertEqual(cmp.fmt(0.1530123), "0.153")
        self.assertEqual(cmp.fmt(947.03), "947.0")
        self.assertEqual(cmp.fmt_range((36.0, 54.0), "V"), "36-54 V")
        self.assertEqual(cmp.min_max([3, None, 1.5, "x"]), (1.5, 3.0))
        self.assertIsNone(cmp.min_max([]))

    def test_clip_cuts_at_a_clause_boundary(self):
        text = "control electronics are a SELV domain; the single-point SGND-to-PE bond (PELV) is a proposed deviation that the reviewer must approve"
        clipped = cmp.clip(text, 60)
        self.assertTrue(clipped.endswith(" ..."))
        self.assertLessEqual(len(clipped), 64)
        self.assertEqual(clipped, "control electronics are a SELV domain ...")
        self.assertEqual(cmp.clip("short", 60), "short")
        self.assertIsNone(cmp.clip(None, 10))
        self.assertIsNone(cmp.clip("", 10))

    def test_metric_container_helpers(self):
        item = cmp.metric(5, "a/b.json", "measured", "mm", "note")
        self.assertEqual(cmp.value_of(item), 5)
        self.assertFalse(cmp.is_pending(item))
        self.assertTrue(cmp.is_pending(cmp.pending("x")))
        self.assertEqual(cmp.value_of(cmp.pending("x"), "default"), "default")
        self.assertEqual(cmp.value_of(7), 7)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_v2_design_phase_tree(root: Path):
    """A minimal V2 example with design-phase files only (no boards, placement, DRC, exports, release)."""
    v2 = root / cmp.V2_REL
    (v2 / "input").mkdir(parents=True)
    (v2 / "input/requirements.yaml").write_text("converter:\n  input_voltage_nominal_V: 400.0\n  output_voltage_V: 200.0\n  output_power_W: 5000.0\n"
                                                "  output_current_nominal_A: 25.0\n  switching_frequency_Hz: 50000.0\n", encoding="utf-8")
    write_json(v2 / "design/design_decisions.json", {
        "requirements_user": {"vin_nominal_V": 400, "vout_V": 200, "pout_W": 5000, "iout_A": 25, "fsw_Hz": 50000},
        "assumptions_accepted": {"vin_operating_range_V": [360, 440], "isolation_concept": "control electronics are a SELV domain"},
        "operating_points": [{"vin_V": 360}, {"vin_V": 400}, {"vin_V": 440}],
        "architecture": {"option": "B: separate power PCB and DSP control PCB", "power_board": {"outline_mm": [240, 180], "layers": 4, "copper_um": 70, "thickness_mm": 2.0},
                         "control_board": {"outline_mm": [120, 80], "layers": 4, "copper_um": 35, "thickness_mm": 1.6},
                         "mechanical": "total height 15 + 2 + 50 = 67 mm (72 mm envelope)", "target_metrics_after_layout": {"driver_to_gate_pin_mm_max": 15}},
        "power_stage": {"mosfet": {"part": "C4MS025120K", "manufacturer": "Wolfspeed", "qty": 2, "package": "TO-247-4"},
                        "gate_driver": {"part": "UCC21710QDWRQ1", "isolation": "5.7 kVrms, VIORM 2121 Vpk"}, "bias_supply": {"part": "UCC14141QDWNRQ1", "qty": "3"}},
        "sensing": {"current": {"part": "TMCS1133C2AQDVGR"}},
        "standards_and_spacing": {"kicad_rules_mm": {"HV_or_DRV_or_DESAT_or_SENSE_ISO_to_CTRL_SELV_all_layers": 9.0, "ISO_BARRIER_keepout_width": 10.0, "HV_to_PE": 5.0,
                                                     "HV_functional_outer": 3.0, "HV_functional_inner": 1.0, "to247_pin_field_exception": "text"}},
        "thermal": {"heatsink": "Fischer LAM 5 D K 100 12", "interface_pad": "Sil-Pad TSP A2000"},
        "conflict_resolutions": [{"id": "CR-01"}], "open_items_for_human_review": ["a", "b"]})
    write_json(v2 / "design/knowledge_trace.json", {
        "areas": ["architecture"], "rows": [{"area": "architecture", "id": "KR-PCB-005", "type": "rule", "validation_status": "reference-derived", "applicability": "direct"},
                                            {"area": "architecture", "id": "SKILL-002", "type": "skill", "validation_status": "analytically-checked", "applicability": "adapted"}],
        "unknown_ids": [], "queries": {"architecture": [{"command": "q", "top_hits": []}]},
        "coverage": {"skills": {"used": 1, "total": 6, "ids": ["SKILL-002"]}, "rules": {"used": 1, "total": 43, "ids": ["KR-PCB-005"]},
                     "project_rules": {"used": 2, "total": 8, "ids": ["PE-PCB-001", "PE-PCB-001..008"]}},
        "by_applicability": {"direct": 1, "adapted": 1, "not-applicable": 0, "human-review": 0}})
    write_json(v2 / "design/research/architecture.json", {"knowledge_used": [{"id": "KR-PCB-005"}]})
    write_json(v2 / "design/research/verify_pcb_architecture_selection_engineering.json",
               {"lens": "ENGINEERING", "verdict": "confirmed-with-corrections", "checked_items": [{"status": "verified"}, {"status": "contradicted"}],
                "recomputed": [{"agrees": True}, {"agrees": False}], "required_changes": ["x"], "knowledge_misuse": []})
    write_json(v2 / "design/calculations.json", {
        "operating_points": [{"vin_V": 360}, {"vin_V": 400}], "inputs_register": [{"name": "V_OUT"}], "invariants": [{"status": "PASS"}, {"status": "PASS"}],
        "baseline_crosscheck": [{"status": "agrees"}, {"status": "differs"}],
        "efficiency": {"target": 0.98, "floor": 0.975, "items_W": {"a": 1.0}, "scenarios": [{"scenario": "typical_expected", "converter_loss_W": 65.7, "eta_converter_only": 0.987, "eta_system": 0.984}]},
        "thermal": {"corners": [{}, {}], "expected_400V_25A_100C": {"T_J_HS_C": 105.7}, "hottest_HS_corner": {"T_J_HS_C": 143.1, "corner": "360V/27.5A", "k_RG": 2.0},
                    "fan_failure": [{}], "ntc_to_TJ_offset_K": {"typ": 58}},
        "limitations": ["l1"], "open_items": ["o1", "o2"]})
    write_json(v2 / "design/circuit_power.json", [
        {"ref": "Q1", "kind": "Q", "footprint": "Package_TO_SOT_THT:TO-247-4_Vertical", "nets": {"1": "G_H", "2": "VIN"}, "page": "01", "mpn": "C4MS025120K", "maker": "Wolfspeed", "dnp": False},
        {"ref": "U1", "kind": "IC", "footprint": "AIPE:UCC14141_DWN0036A_Slot", "nets": {"1": "VIN", "2": "SW"}, "page": "02", "mpn": "UCC14141", "maker": "TI", "dnp": False},
        {"ref": "C9", "kind": "C", "footprint": "Capacitor_SMD:C_2512", "nets": {"1": "SW", "2": "PGND"}, "page": "01", "mpn": "x", "maker": "TDK", "dnp": True},
        {"ref": "TP1", "kind": "TP", "footprint": "TestPoint:TestPoint_Pad_D2.0mm", "nets": {"1": "SW"}, "page": "01", "mpn": "", "maker": "", "dnp": False}])
    write_json(v2 / "design/circuit_control.json", [
        {"ref": "U1", "kind": "DSP", "footprint": "Package_QFP:LQFP-176", "nets": {"1": "3V3", "2": "GND_CTRL"}, "page": "03", "mpn": "TMS320F28335PGFA", "maker": "TI", "dnp": False}])
    (v2 / "components").mkdir()
    (v2 / "components/bom.csv").write_text("board,reference,value,manufacturer,mpn,footprint,datasheet,dnp,note\npower,Q1,x,Wolfspeed,C4MS025120K,f,d,no,n\ncontrol,U1,y,TI,TMS320F28335PGFA,f,d,no,n\n", encoding="utf-8")
    write_json(v2 / "components/component_records.json", [
        {"mpn": "C4MS025120K", "verification_level": "fetched-datasheet (Rev. 2)", "knowledge_refs": ["KR-GD-001"], "open_issues": ["stock"], "alternatives": ["C3M0021120K"]},
        {"mpn": "TMS320F28335PGFA", "verification_level": "unverified (V1 cache)", "knowledge_refs": [], "open_issues": [], "alternatives": []}])
    run = v2 / "verification/erc/20261010T065851Z-erc-1c9f84ae"
    write_json(run / "run.json", {"source": "D:/x/AIPE_SiC_Buck_Power.kicad_sch", "status": "passed", "finding_count": 0, "tool_exit_code": 0})
    write_json(v2 / "verification/engineering_checks/layout_spec_power.json", {"isolation": {"barrier_parts": [{"ref": "U1"}, {"ref": "U2"}]}})
    write_json(v2 / "simulation/results/campaign_summary.json", {
        "runs": {"ol_400V": {"controller": "open-loop", "warnings": [], "metrics": {"vout_pkpk": 0.18}, "campaign": {"steady_checks": {"a": True, "b": True}, "events": []}},
                 "cl_400V": {"controller": "cascade", "warnings": [], "metrics": {"vout_pkpk": 0.17},
                             "campaign": {"steady_checks": {"a": True}, "events": [{"type": "load_step_off", "excursion_cycle_avg_V": 7.8, "recovery_time_s": 0.00075, "vout_raw_max_V": 207.9,
                                                                                   "i_load_before_A": 25.0, "i_load_after_A": 12.5, "checks": {"excursion_within_10V": True, "recovery_within_5ms": False}}]}}},
        "parasitic_sweep": [{"L_loop": 2.5e-8}], "limits": {"vout_ripple_max_Vpp": 2.0}, "loop_gain_analysis": "results/loop_gain_analysis.json", "total_runtime_s": 12.0})
    write_json(v2 / "simulation/models/ol_400V.json", {})
    write_json(v2 / "simulation/models/campaign_manifest.json", {})
    (v2 / "kicad/power_board").mkdir(parents=True)
    (v2 / "kicad/power_board/AIPE_SiC_Buck_Power.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
    (v2 / "kicad/power_board/01_power_stage.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests/test_x.py").write_text("def test_a():\n    pass\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs/knowledge-status.md").write_text("- No simulation or hardware validation.\n", encoding="utf-8")
    return v2


class SmokeTests(unittest.TestCase):
    def test_empty_tree_never_raises_and_marks_everything_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = cmp.build_report(root)
            v1, v2 = report["generations"]["v1"], report["generations"]["v2"]
            self.assertEqual(cmp.value_of(v1["erc_findings"]), None)
            self.assertTrue(cmp.is_pending(v2["drc_findings"]))
            self.assertTrue(cmp.is_pending(v2["board_files"]))
            self.assertTrue(cmp.is_pending(v2["simulation_runs"]))
            self.assertTrue(cmp.is_pending(v2["component_records"]))
            self.assertIn("drc_findings", report["pending_v2_metrics"])
            self.assertTrue(v2["sources"]["missing"])
            text = cmp.render_markdown(report)
            self.assertTrue(text.startswith(cmp.BANNER))
            json_path, md_path = cmp.write_outputs(report, root / "out")
            self.assertTrue(json_path.is_file() and md_path.is_file())
            json.loads(json_path.read_text(encoding="utf-8"))

    def test_design_phase_tree_reports_design_metrics_and_pending_pcb_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            make_v2_design_phase_tree(root)
            report = cmp.build_report(root)
            v2 = report["generations"]["v2"]
            self.assertEqual(cmp.value_of(v2["pout_W"]), 5000.0)
            self.assertEqual(cmp.value_of(v2["vin_range_V"]), [360, 440])
            self.assertEqual(cmp.value_of(v2["board_count"]), 2)
            self.assertEqual(cmp.value_of(v2["assembly_height_mm"]), 67.0)
            self.assertEqual(cmp.value_of(v2["total_board_area_mm2"]), 52800)
            self.assertEqual(v2["total_board_area_mm2"]["basis"], "planned")
            self.assertEqual(cmp.value_of(v2["erc_findings_power"]), 0)
            self.assertTrue(cmp.is_pending(v2["erc_findings_control"]))
            self.assertTrue(cmp.is_pending(v2["erc_findings"]))
            self.assertTrue(cmp.is_pending(v2["drc_findings"]))
            self.assertTrue(cmp.is_pending(v2["tracks"]))
            self.assertTrue(cmp.is_pending(v2["placement_candidates"]))
            self.assertTrue(cmp.is_pending(v2["export_manifests"]))
            self.assertTrue(cmp.is_pending(v2["release_frozen"]))
            self.assertEqual(cmp.value_of(v2["barrier_parts"]), 2)
            self.assertEqual(v2["barrier_parts"]["basis"], "planned")
            self.assertEqual(cmp.value_of(v2["circuit_parts"]), {"power": 4, "control": 1})
            self.assertEqual(cmp.value_of(v2["dnp_parts"]), {"power": 1, "control": 0})
            self.assertEqual(cmp.value_of(v2["named_nets"]), 6)
            self.assertEqual(cmp.value_of(v2["custom_footprints"]), 1)
            self.assertEqual(cmp.value_of(v2["purchased_components"]), 3)
            self.assertEqual(cmp.value_of(v2["component_verification_levels"]), {"fetched-datasheet": 1, "unverified": 1})
            self.assertEqual(cmp.value_of(v2["knowledge_items_used"])["project_rules"], 2)
            self.assertIn("aggregate", v2["knowledge_items_used"]["note"])
            self.assertEqual(cmp.value_of(v2["verification_verdicts"]), {"confirmed-with-corrections": 1})
            self.assertEqual(cmp.value_of(v2["verification_recomputed"]), {"agrees": 1, "disagrees": 1})
            self.assertEqual(cmp.value_of(v2["simulation_runs"]), 2)
            self.assertEqual(cmp.value_of(v2["simulation_steady_checks"]), "3/3")
            self.assertEqual(cmp.value_of(v2["simulation_event_checks"]), "1/2")
            self.assertIn("cl_400V", v2["simulation_event_checks"]["note"])
            self.assertEqual(cmp.value_of(v2["simulation_models"]), 1)
            self.assertEqual(cmp.value_of(v2["schematic_sheets"]), 2)
            self.assertEqual(cmp.value_of(v2["test_functions"]), 1)
            self.assertEqual(cmp.value_of(v2["calculation_invariants"]), 2)
            self.assertEqual(cmp.value_of(v2["baseline_crosscheck"]), {"items": 2, "agrees": 1})
            self.assertEqual(cmp.value_of(v2["thermal_tj_hottest_C"]), 143.1)
            derived = report["derived"]["v2"]
            self.assertAlmostEqual(cmp.value_of(derived["specific_power_W_per_dm2"]), 946.97, places=1)
            self.assertEqual(derived["specific_power_W_per_dm2"]["basis"], "planned")
            self.assertAlmostEqual(cmp.value_of(derived["volumetric_power_W_per_L"]), 1413.4, places=1)
            self.assertAlmostEqual(cmp.value_of(derived["cost_index_layer_dm2"]), 21.12)
            self.assertEqual(cmp.value_of(derived["nets_per_board"]), 3)
            self.assertEqual(cmp.value_of(derived["power_per_mosfet_W"]), 2500)
            workflow = report["tables"]["2_process_metrics"]["workflow_completeness"]
            self.assertEqual(workflow["knowledge_retrieval"]["v2"]["state"], "done")
            self.assertEqual(workflow["simulation"]["v2"]["state"], "done")
            self.assertEqual(workflow["schematic_erc"]["v2"]["state"], cmp.NOT_AVAILABLE)
            self.assertEqual(workflow["drc"]["v2"]["state"], cmp.NOT_AVAILABLE)
            self.assertEqual(workflow["release"]["v2"]["state"], cmp.NOT_AVAILABLE)
            self.assertEqual(workflow["knowledge_retrieval"]["v1"]["state"], "not done")
            text = cmp.render_markdown(report)
            self.assertIn("## 1. Specification-driven differences", text)
            self.assertIn("### 2.1 Workflow completeness", text)
            self.assertIn("## 3. Layout and architecture metrics", text)
            self.assertIn("## 6. What this comparison can and cannot show", text)
            self.assertIn("power 240 x 180; control 120 x 80 mm (planned)", text)
            self.assertIn(cmp.NOT_AVAILABLE, text)
            for name in report["pending_v2_metrics"]:
                self.assertIn(name.split(".")[-1], text.replace("`", ""))

    def test_main_writes_both_files_to_the_requested_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            make_v2_design_phase_tree(root)
            out = root / "review-out"
            self.assertEqual(cmp.main(["--root", str(root), "--output", str(out), "--quiet"]), 0)
            report = json.loads((out / "v1_v2_comparison.json").read_text(encoding="utf-8"))
            text = (out / "v1_v2_comparison.md").read_text(encoding="utf-8")
            self.assertEqual(report["status"], cmp.STATUS)
            self.assertEqual(set(report["tables"]), {"1_specification_driven_differences", "2_process_metrics", "3_layout_and_architecture", "4_component_selection_thermal_manufacturability"})
            self.assertEqual(text.splitlines()[0], cmp.BANNER)
            self.assertNotIn("\t", text)


@unittest.skipUnless((cmp.ROOT / cmp.V1_REL / "input/requirements.yaml").is_file() and (cmp.ROOT / cmp.V2_REL / "design/design_decisions.json").is_file(),
                     "example projects not present in this checkout")
class RepositoryTests(unittest.TestCase):
    def test_collects_the_frozen_v1_metrics_from_this_checkout(self):
        v1 = cmp.collect_v1(cmp.ROOT / cmp.V1_REL, cmp.ROOT)
        self.assertEqual(cmp.value_of(v1["pout_W"]), 1000.0)
        self.assertEqual(cmp.value_of(v1["board_outline_mm"]), [300.0, 220.0])
        self.assertEqual(cmp.value_of(v1["copper_layers"]), 6)
        self.assertEqual(cmp.value_of(v1["erc_findings"]), 0)
        self.assertEqual(cmp.value_of(v1["drc_findings"]), 0)
        self.assertEqual(cmp.value_of(v1["schematic_sheets"]), 14)
        self.assertEqual(cmp.value_of(v1["documented_open_issues"]), 12)
        self.assertEqual(cmp.value_of(v1["mosfet"])["qty"], 4)
        self.assertEqual(cmp.value_of(v1["vin_range_V"]), (36.0, 54.0))
        self.assertEqual(cmp.value_of(v1["simulation_runs"]), 0)
        self.assertEqual(cmp.value_of(v1["assembly_height_mm"]), 57.0)
        self.assertEqual(v1["sources"]["missing"], [])

    def test_report_against_this_checkout_writes_to_a_temporary_directory(self):
        report = cmp.build_report(cmp.ROOT)
        v2 = report["generations"]["v2"]
        self.assertEqual(cmp.value_of(v2["pout_W"]), 5000.0)
        self.assertEqual(cmp.value_of(v2["board_count"]), 2)
        self.assertIsNotNone(cmp.value_of(v2["knowledge_items_used"]))
        for item in v2.values():
            if isinstance(item, dict) and item.get("basis") == cmp.NOT_AVAILABLE:
                self.assertTrue(item.get("note"), "every pending metric states why")
        with tempfile.TemporaryDirectory() as folder:
            json_path, md_path = cmp.write_outputs(report, Path(folder))
            text = md_path.read_text(encoding="utf-8")
            self.assertEqual(text.splitlines()[0], cmp.BANNER)
            self.assertIn("## 6. What this comparison can and cannot show", text)
            json.loads(json_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
