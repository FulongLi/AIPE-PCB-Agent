"""Compare the V1 (48 V -> 24 V / 1 kW Si buck) and V2 (400 V -> 200 V / 5 kW SiC buck) generations.

Collects machine-readable metrics from the repository files of both example projects and writes
examples/sic-buck-400v-200v-5kw/review/v1_v2_comparison.json and v1_v2_comparison.md. The comparison
separates three things that are easy to confuse:

1. differences forced by the electrical specification (voltage, power, current, isolation class,
   semiconductor technology) - these explain metric differences and are NOT improvements;
2. process metrics that are comparable across generations (workflow completeness, knowledge
   utilisation, verification coverage, documentation volume, automated tests);
3. layout and architecture metrics (board outlines, layers, critical-loop proxies, density, specific
   power) - reported with the explicit caveat that raw PCB area or density never proves superiority.

Every V2 metric whose source file does not exist yet (the PCB phase runs concurrently: boards, placement
candidates, DRC runs, layout metrics, export manifests, release) is marked "not yet available" so the
script can be re-run later to complete the tables. Missing files never raise; they are listed in the
report. Standard library only; run from the repository root:

    python -m automation.scripts.compare_v1_v2 [--root DIR] [--output DIR] [--quiet]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V1_REL = "examples/buck-48v-24v-1kw"
V2_REL = "examples/sic-buck-400v-200v-5kw"
BANNER = "**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**"
STATUS = "AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED"
NOT_AVAILABLE = "not yet available"
PENDING_NOTE = "PCB phase running - re-run after the V2 boards are placed, routed and checked"

# Assembly heights used for the volumetric specific power (task definition): board thickness plus the
# tallest documented part for V1; the documented total stack height for V2 (standoffs + board + heatsink).
V1_TALLEST_PART_MM = 55.0          # design/pcb_stackup.md: upright inductor envelope "about 55 mm tall"
V2_ASSEMBLY_HEIGHT_MM = 67.0       # design_decisions.json architecture.mechanical: "15 + 2 + 50 = 67 mm"

V2_BOARDS = {"power": "AIPE_SiC_Buck_Power", "control": "AIPE_SiC_Buck_Control"}
WORKFLOW_STEPS = [
    ("requirements_assumptions", "Requirements capture and assumptions register"),
    ("knowledge_retrieval", "Knowledge retrieval with traceable citations"),
    ("calculations_script", "Reproducible calculations script"),
    ("component_records", "Component records with stress, margin and verification level"),
    ("schematic_erc", "Schematic complete and ERC clean"),
    ("simulation", "Behavioural simulation campaign"),
    ("placement_candidates", "Placement candidates evaluated"),
    ("routing", "Board routed"),
    ("drc", "Native DRC (with parity and unrouted checks) clean"),
    ("layout_metrics", "Power-layout metrics measured against the engineering rules"),
    ("independent_review", "Independent review / verification records"),
    ("release", "Frozen release with hash manifest"),
]


# --- metric containers --------------------------------------------------------------------------------------

def metric(value, source=None, basis="counted", unit=None, note=None, kind=None) -> dict:
    """A reported quantity: value, unit, the file it came from, how it was obtained and how to print a list
    value (kind 'dims' -> 'a x b', 'range' -> 'a-b', default -> 'a / b')."""
    item = {"value": value, "unit": unit, "source": source, "basis": basis, "note": note}
    if kind:
        item["kind"] = kind
    return item


def pair(*values, basis="counted", source=None, unit=None, note=None) -> dict:
    """Several counts reported in one cell ('a / b')."""
    return metric(list(values), source, basis, unit, note)


def clip(text, limit: int) -> str | None:
    """Shorten a quoted sentence at the last clause boundary before `limit` characters."""
    if text is None:
        return None
    text = str(text).strip()
    if len(text) <= limit:
        return text or None
    head = text[:limit]
    cut = max(head.rfind("; "), head.rfind(", "), head.rfind(". "), head.rfind(" ("))
    if cut < limit // 2:
        cut = head.rfind(" ")
    return (head[:cut] if cut > 0 else head).rstrip(" ,;.(") + " ..."


def pending(source=None, note=PENDING_NOTE) -> dict:
    """A V2 quantity whose source file does not exist yet."""
    return {"value": None, "unit": None, "source": source, "basis": NOT_AVAILABLE, "note": note}


def is_pending(item) -> bool:
    return isinstance(item, dict) and item.get("basis") == NOT_AVAILABLE


def value_of(item, default=None):
    if isinstance(item, dict) and "basis" in item:
        return default if item.get("value") is None else item.get("value")
    return default if item is None else item


# --- pure helpers (unit-tested) ------------------------------------------------------------------------------

def _strip_yaml_comment(line: str) -> str:
    if line.lstrip().startswith("#"):
        return ""
    cut = line.find(" #")
    return line if cut < 0 else line[:cut]


def yaml_scalar(text: str):
    """Coerce a YAML scalar: quotes, null, booleans, numbers, inline lists."""
    text = text.strip()
    if text == "" or text in ("null", "~"):
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [yaml_scalar(part) for part in inner.split(",")] if inner else []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_simple_yaml(text: str) -> dict:
    """Minimal YAML reader for the requirement files: nested mappings, scalars and plain lists only."""
    root: dict = {}
    stack: list = [[-1, root, None, None]]  # indent, container, parent, key
    for raw in text.splitlines():
        line = _strip_yaml_comment(raw.replace("\t", "  ")).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        is_item = content.startswith("- ") or content == "-"
        while len(stack) > 1:
            top_indent, top_container, parent, _ = stack[-1]
            if indent > top_indent:
                break
            if indent == top_indent and is_item and parent is not None and (isinstance(top_container, list) or top_container == {}):
                break
            stack.pop()
        entry = stack[-1]
        container = entry[1]
        if is_item:
            if isinstance(container, dict) and container == {} and entry[2] is not None:
                container = []
                entry[2][entry[3]] = container
                entry[1] = container
            if isinstance(container, list):
                container.append(yaml_scalar(content[1:].strip()))
            continue
        if ":" not in content or isinstance(container, list):
            continue
        key, _, rest = content.partition(":")
        key = key.strip().strip("\"'")
        if rest.strip() == "":
            child: dict = {}
            container[key] = child
            stack.append([indent, child, container, key])
        else:
            container[key] = yaml_scalar(rest)
    return root


def dig(data, *keys, default=None):
    """Nested lookup that tolerates missing keys, non-dict intermediates and list indices."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                return default
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and -len(current) <= key < len(current):
            current = current[key]
        else:
            return default
    return current


def csv_summary(path: Path, distinct_columns=()) -> dict | None:
    """Row count (excluding the header), column count and distinct non-empty values per named column."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            columns = reader.fieldnames or []
    except (OSError, UnicodeDecodeError, csv.Error):
        return None
    summary = {"rows": len(rows), "columns": len(columns), "column_names": list(columns), "distinct": {}}
    for column in distinct_columns:
        match = next((c for c in columns if c.lower() == column.lower()), None)
        values = {(r.get(match) or "").strip() for r in rows} if match else set()
        values.discard("")
        summary["distinct"][column] = len(values)
    return summary


def count_markdown_table_rows(text: str, id_pattern: str = r"^\|\s*[A-Z][A-Z0-9]*-\d+\s*\|") -> int:
    """Rows of a Markdown table whose first cell is an identifier such as V1-01 or A-12."""
    return sum(1 for line in text.splitlines() if re.match(id_pattern, line))


def word_count(text: str) -> int:
    return len(text.split())


def count_test_functions(paths) -> dict:
    """{module stem: number of 'def test_' functions} for the given Python files."""
    counts = {}
    for path in sorted(paths):
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        counts[Path(path).stem] = len(re.findall(r"^\s*def test_\w+", text, flags=re.MULTILINE))
    return counts


def latest_runs(directory: Path, kind: str) -> dict:
    """Latest run.json per source stem under <directory>/*-<kind>-*/run.json (directory names start with a timestamp)."""
    latest: dict = {}
    if not directory.is_dir():
        return latest
    for manifest in sorted(directory.glob(f"*-{kind}-*/run.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        stem = Path(str(data.get("source", manifest.parent.name))).stem
        latest[stem] = {"run_dir": manifest.parent.name, "status": data.get("status"),
                        "finding_count": data.get("finding_count"), "tool_exit_code": data.get("tool_exit_code")}
    return latest


def board_key_for_stem(stem: str) -> str:
    lowered = stem.lower()
    for key, name in V2_BOARDS.items():
        if stem == name or key in lowered:
            return key
    return stem


def specific_power_W_per_dm2(power_W, area_mm2):
    if not power_W or not area_mm2:
        return None
    return power_W / (area_mm2 / 1e4)


def volumetric_power_W_per_L(power_W, area_mm2, height_mm):
    """Power per litre of (summed board area x assembly height); not an enclosure volume."""
    if not power_W or not area_mm2 or not height_mm:
        return None
    return power_W / (area_mm2 * height_mm / 1e6)


def components_per_dm2(count, area_mm2):
    if count is None or not area_mm2:
        return None
    return count / (area_mm2 / 1e4)


def cost_index_layer_dm2(boards) -> float | None:
    """Sum over boards of copper layers x area in dm2 (a relative fabrication-cost proxy, not a quotation)."""
    total = 0.0
    seen = False
    for layers, area_mm2 in boards:
        if layers is None or not area_mm2:
            continue
        total += layers * area_mm2 / 1e4
        seen = True
    return total if seen else None


def coerce_board_mm(obj):
    """[width, height] from a list, a dict with outline/board/size keys or a '240 x 180' string."""
    if isinstance(obj, (list, tuple)) and len(obj) >= 2:
        try:
            return [float(obj[0]), float(obj[1])]
        except (TypeError, ValueError):
            return None
    if isinstance(obj, dict):
        for key in ("board_mm", "outline_mm", "size_mm", "board", "outline", "size"):
            if key in obj:
                found = coerce_board_mm(obj[key])
                if found:
                    return found
        if "width_mm" in obj and "height_mm" in obj:
            return coerce_board_mm([obj["width_mm"], obj["height_mm"]])
        return None
    if isinstance(obj, str):
        match = re.search(r"(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)", obj)
        if match:
            return [float(match.group(1)), float(match.group(2))]
    return None


def board_area_mm2(board_mm) -> float | None:
    dims = coerce_board_mm(board_mm)
    return dims[0] * dims[1] if dims else None


def parse_height_mm(text: str) -> float | None:
    """The stack height from a sentence such as 'total height 15 + 2 + 50 = 67 mm'."""
    if not isinstance(text, str):
        return None
    match = re.search(r"height[^=]*=\s*(\d+(?:\.\d+)?)\s*mm", text)
    if match:
        return float(match.group(1))
    match = re.search(r"height\s*(\d+(?:\.\d+)?)\s*mm", text)
    return float(match.group(1)) if match else None


def bucket_verification_level(level) -> str:
    """Coarse class of a free-text component verification level."""
    text = str(level or "").strip().lower()
    if not text:
        return "unstated"
    if text.startswith("fetched-datasheet") or text.startswith("analytical"):
        return "fetched-datasheet"
    if text.startswith("manufacturer-page"):
        return "manufacturer-page"
    if text.startswith("search-snippet"):
        return "search-snippet"
    if text.startswith("unverified"):
        return "unverified"
    return "other"


def min_max(values):
    cleaned = [float(v) for v in values if isinstance(v, (int, float))]
    return (min(cleaned), max(cleaned)) if cleaned else None


def fmt(value, nd: int = 1, kind=None) -> str:
    """Compact Markdown rendering for numbers, ranges, dimensions, lists, dicts and pending markers."""
    if isinstance(value, dict) and "basis" in value:
        if value.get("basis") == NOT_AVAILABLE:
            return f"{NOT_AVAILABLE} ({value.get('note') or PENDING_NOTE})"
        text = fmt(value.get("value"), nd, value.get("kind"))
        if value.get("unit"):
            text += f" {value['unit']}"
        if value.get("basis") == "planned":
            text += " (planned)"
        return text
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e6:
            return str(int(value))
        return f"{value:.{nd}f}" if abs(value) >= 1 else f"{value:.{nd + 2}f}"
    if isinstance(value, (list, tuple)):
        numeric_pair = len(value) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
        if numeric_pair and kind == "dims":
            return f"{fmt(value[0], nd)} x {fmt(value[1], nd)}"
        if numeric_pair and kind == "range":
            return fmt(value[0], nd) if value[0] == value[1] else f"{fmt(value[0], nd)}-{fmt(value[1], nd)}"
        return " / ".join(fmt(v, nd, kind) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k} {fmt(v, nd, 'dims' if kind is None else kind)}" for k, v in value.items())
    return str(value)


def fmt_range(pair, unit="", nd=1) -> str:
    if not pair:
        return "n/a"
    low, high = pair
    body = fmt(low, nd) if low == high else f"{fmt(low, nd)}-{fmt(high, nd)}"
    return f"{body} {unit}".strip()


# --- file access with provenance -----------------------------------------------------------------------------

class Sources:
    """Reads files relative to a root and records what was found and what is missing."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.read: list = []
        self.missing: list = []

    def rel(self, path: Path) -> str:
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return Path(path).as_posix()

    def _record(self, path: Path, ok: bool):
        target = self.read if ok else self.missing
        rel = self.rel(path)
        if rel not in target:
            target.append(rel)

    def json(self, path: Path):
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            self._record(path, False)
            return None
        self._record(path, True)
        return data

    def text(self, path: Path):
        path = Path(path)
        try:
            data = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            self._record(path, False)
            return None
        self._record(path, True)
        return data

    def csv(self, path: Path, distinct_columns=()):
        path = Path(path)
        summary = csv_summary(path, distinct_columns) if path.is_file() else None
        self._record(path, summary is not None)
        return summary

    def glob(self, pattern: str, base: Path | None = None) -> list:
        base = Path(base) if base else self.root
        return sorted(base.glob(pattern)) if base.is_dir() else []


def markdown_volume(paths) -> dict:
    files, words = 0, 0
    for path in paths:
        try:
            words += word_count(Path(path).read_text(encoding="utf-8", errors="replace"))
            files += 1
        except OSError:
            continue
    return {"files": files, "words": words}


# --- V1 collection -------------------------------------------------------------------------------------------

def collect_v1(root: Path, repo_root: Path | None = None) -> dict:
    """Metrics of the frozen V1 example (read-only)."""
    root = Path(root)
    repo_root = Path(repo_root) if repo_root else root.parents[1]
    src = Sources(repo_root)
    m: dict = {"generation": "V1", "name": "48 V -> 24 V / 1 kW Si synchronous buck, integrated board"}

    req_text = src.text(root / "input/requirements.yaml")
    req = parse_simple_yaml(req_text) if req_text else {}
    conv = req.get("converter", {}) if isinstance(req, dict) else {}
    m["vin_nominal_V"] = metric(conv.get("input_voltage_nominal_V"), "input/requirements.yaml", "documented", "V")
    m["vout_V"] = metric(conv.get("output_voltage_V"), "input/requirements.yaml", "documented", "V")
    m["pout_W"] = metric(conv.get("output_power_W"), "input/requirements.yaml", "documented", "W")
    m["iout_A"] = metric(conv.get("output_current_nominal_A"), "input/requirements.yaml", "documented", "A")
    m["board_count"] = metric(dig(req, "pcb", "board_count"), "input/requirements.yaml", "documented")
    m["architecture"] = metric(dig(req, "pcb", "architecture"), "input/requirements.yaml", "documented")

    calc = src.json(root / "design/calculations.json") or {}
    m["fsw_Hz"] = metric(calc.get("frequency_Hz"), "design/calculations.json", "documented", "Hz")
    m["vin_range_V"] = metric(min_max(c.get("vin_V") for c in calc.get("cases", []) if isinstance(c, dict)), "design/calculations.json", "documented", "V",
                              "input cases evaluated (design/assumptions.md: 36-54 V continuous)", kind="range")
    m["inductance_uH"] = metric((calc.get("inductance_H") or 0) * 1e6 or None, "design/calculations.json", "documented", "uH")
    m["operating_points"] = metric(len(calc.get("cases", [])), "design/calculations.json")
    m["loss_items"] = metric(len(calc.get("losses_W", {})), "design/calculations.json")
    m["total_loss_W"] = metric(calc.get("total_loss_W"), "design/calculations.json", "documented", "W")
    m["efficiency_estimate"] = metric(calc.get("efficiency_estimate"), "design/calculations.json", "documented")
    m["efficiency_sensitivity"] = metric(calc.get("efficiency_if_loss_doubles"), "design/calculations.json", "documented",
                                         note="efficiency if the assumed loss doubles")
    m["calculation_invariants"] = metric(0, "design/calculations.json", "counted", note="no machine-checked invariants in the V1 record")
    m["calculation_inputs_register"] = metric(0, "design/calculations.json", "counted", note="inputs are embedded in the generator script, not registered")

    placement = src.json(root / "design/placement.json") or {}
    board_mm = coerce_board_mm(placement.get("board_mm"))
    m["board_outline_mm"] = metric(board_mm, "design/placement.json", "documented", "mm", kind="dims")
    m["board_outlines"] = metric({"integrated": board_mm} if board_mm else None, "design/placement.json", "documented", "mm", kind="dims")
    m["total_board_area_mm2"] = metric(board_area_mm2(board_mm), "design/placement.json", "derived", "mm2")
    m["placement_candidates"] = metric(1 if placement else 0, "design/placement.json", note="single placement; no alternatives recorded")

    assumptions = src.text(root / "design/assumptions.md") or ""
    m["assumption_rows"] = metric(sum(1 for l in assumptions.splitlines() if l.startswith("| ") and not l.startswith("| Topic") and not l.startswith("|---")),
                                  "design/assumptions.md", note="rows of the single assumptions table")

    bom = src.csv(root / "components/bom.csv", ("Manufacturer", "MPN"))
    m["bom_rows"] = metric(bom["rows"] if bom else None, "components/bom.csv")
    m["bom_distinct_mpn"] = metric(bom["distinct"]["MPN"] if bom else None, "components/bom.csv")
    m["bom_distinct_manufacturers"] = metric(bom["distinct"]["Manufacturer"] if bom else None, "components/bom.csv")
    sel = src.csv(root / "components/component_selection.csv", ("manufacturer", "part_number"))
    m["component_records"] = metric(sel["rows"] if sel else None, "components/component_selection.csv", note="one row per reference designator")
    m["component_record_fields"] = metric(sel["columns"] if sel else None, "components/component_selection.csv")
    m["component_record_types"] = metric(sel["distinct"]["part_number"] if sel else None, "components/component_selection.csv", note="distinct part numbers")
    m["component_verification_levels"] = metric({"not recorded": sel["rows"]} if sel else None, "components/component_selection.csv", "documented",
                                                note="a uniform 'verification_limit' sentence; no per-part datasheet-fetch level")
    sel_rows = []
    try:
        with (root / "components/component_selection.csv").open(encoding="utf-8-sig", newline="") as handle:
            sel_rows = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        pass
    q_rows = [r for r in sel_rows if re.match(r"Q\d+$", r.get("reference", ""))]
    power_q = [r for r in q_rows if q_rows and r.get("part_number") == q_rows[0].get("part_number")]  # the paralleled power devices share Q1's part
    m["mosfet"] = metric({"part": power_q[0].get("part_number"), "manufacturer": power_q[0].get("manufacturer"), "qty": len(power_q),
                          "package": clip(power_q[0].get("package"), 60), "voltage_rating": clip(power_q[0].get("voltage_rating"), 40)} if power_q else None,
                         "components/component_selection.csv", "documented")
    drivers = [r for r in sel_rows if "UCC27211" in (r.get("part_number") or "")]
    sensors = [r for r in sel_rows if "INA240" in (r.get("part_number") or "")]
    m["gate_driver"] = metric({"part": drivers[0].get("part_number"), "isolation": "none (bootstrap half-bridge driver)"} if drivers else None,
                              "components/component_selection.csv", "documented")
    m["current_sensing"] = metric({"part": sensors[0].get("part_number"), "method": "2 mohm shunt + INA240 (non-isolated Kelvin shunt)"} if sensors else None,
                                  "components/component_selection.csv", "documented")
    m["isolation_concept"] = metric("48 V SELV-class system on one board; no reinforced isolation barrier, no isolated gate bias, no isolated sensing",
                                    "design/architecture.md", "documented")

    summary = src.json(root / "verification/verification-summary.json") or {}
    m["erc_findings"] = metric(dig(summary, "erc", "findings"), "verification/verification-summary.json", "measured")
    m["drc_findings"] = metric(dig(summary, "drc", "findings"), "verification/verification-summary.json", "measured")
    m["verification_status"] = metric(summary.get("status"), "verification/verification-summary.json", "measured")
    m["footprints"] = metric(summary.get("components"), "verification/verification-summary.json", "measured")
    m["purchased_components"] = metric(summary.get("purchased_components"), "verification/verification-summary.json", "measured")
    m["named_nets"] = metric(summary.get("named_nets"), "verification/verification-summary.json", "measured")
    m["mapped_pins"] = metric(summary.get("mapped_pins"), "verification/verification-summary.json", "measured")
    m["export_commands"] = metric(summary.get("export_commands"), "verification/verification-summary.json", "measured")
    m["export_files"] = metric(summary.get("export_files"), "verification/verification-summary.json", "measured")
    m["erc_runs_recorded"] = metric(len(src.glob("*-erc-*/run.json", root / "verification")), "verification/")
    m["drc_runs_recorded"] = metric(len(src.glob("*-drc-*/run.json", root / "verification")), "verification/")

    lm = src.json(root / "verification/power-layout-metrics.json") or {}
    m["tracks"] = metric(lm.get("tracks"), "verification/power-layout-metrics.json", "measured")
    m["vias"] = metric(lm.get("vias"), "verification/power-layout-metrics.json", "measured")
    m["copper_layers"] = metric(lm.get("copper_layers"), "verification/power-layout-metrics.json", "measured")
    m["board_thickness_mm"] = metric(lm.get("thickness_mm"), "verification/power-layout-metrics.json", "measured", "mm")
    m["copper_um"] = metric("70 outer/In2/In3, 35 In1/In4", "design/assumptions.md", "documented", "um")
    m["critical_topology_checks"] = metric(lm.get("critical_topology_checks"), "verification/power-layout-metrics.json", "measured")
    hf = [d.get("pad_center_distance_mm") for d in lm.get("hf_capacitor_distances", [])]
    m["hf_capacitor_to_device_mm"] = metric(min_max(hf), "verification/power-layout-metrics.json", "measured", "mm", "MOSFET pad centre to nearest HF ceramic pad centre", kind="range")
    gate = lm.get("driver_to_gate_pin_distance_mm") or {}
    m["driver_to_gate_pin_mm"] = metric(min_max(gate.values()), "verification/power-layout-metrics.json", "measured", "mm", kind="range")
    dsp = [d.get("distance_mm") for d in lm.get("dsp_bypass", [])]
    m["dsp_bypass_max_mm"] = metric(max(d for d in dsp if isinstance(d, (int, float))) if dsp else None, "verification/power-layout-metrics.json", "measured", "mm")
    sw_zones = {z.get("layer"): z.get("area_mm2") for z in lm.get("zones", []) if z.get("net") == "SW"}
    m["sw_copper_mm2"] = metric(sw_zones or None, "verification/power-layout-metrics.json", "measured", "mm2")
    m["sw_copper_total_mm2"] = metric(sum(v for v in sw_zones.values() if isinstance(v, (int, float))) if sw_zones else None,
                                      "verification/power-layout-metrics.json", "measured", "mm2")
    m["copper_zones"] = metric(len(lm.get("zones", [])), "verification/power-layout-metrics.json", "measured")
    m["isolation_min_distance_mm"] = metric(None, "verification/power-layout-metrics.json", "documented",
                                            note="not applicable: no isolation barrier on a 48 V board")
    m["barrier_parts"] = metric(0, "design/architecture.md", "documented", note="no barrier parts")

    issues = src.text(root / "verification/known_issues.md") or ""
    m["documented_open_issues"] = metric(count_markdown_table_rows(issues), "verification/known_issues.md")
    report = src.text(root / "review/design_report.md") or ""
    m["design_report_words"] = metric(word_count(report), "review/design_report.md")
    m["schematic_sheets"] = metric(len(src.glob("*.kicad_sch", root / "kicad")), "kicad/")
    m["board_files"] = metric(len(src.glob("*.kicad_pcb", root / "kicad")), "kicad/", "counted")
    m["custom_footprints"] = metric(len(src.glob("libraries/AIPE*.pretty/*.kicad_mod", root / "kicad")), "kicad/libraries/")

    manifest = src.json(root / "manufacturing/export-manifest.json") or {}
    m["export_manifest_commands"] = metric(len(manifest.get("commands", [])), "manufacturing/export-manifest.json", "measured")
    m["export_manifest_artifacts"] = metric(len(manifest.get("artifacts", {})), "manufacturing/export-manifest.json", "measured")
    m["export_manifest_status"] = metric(manifest.get("status"), "manufacturing/export-manifest.json", "measured")
    m["release_frozen"] = metric((root / "releases/v1/SHA256SUMS.json").is_file(), "releases/v1/SHA256SUMS.json")
    m["release_files"] = metric(len(src.json(root / "releases/v1/SHA256SUMS.json") or {}), "releases/v1/SHA256SUMS.json")

    m["independent_review_records"] = metric(sum(1 for p in ("verification/visual-review.json", "verification/pcb_rule_review.md") if (root / p).is_file()),
                                             "verification/", note="AI visual review and PCB rule review of the final CAD; no separate verifier lenses")
    m["review_lenses"] = metric(["visual-review", "pcb_rule_review"], "verification/", "counted")

    # Knowledge and simulation: V1 predates the knowledge system and had no simulation.
    knowledge_status = src.text(repo_root / "docs/knowledge-status.md") or ""
    status_doc = src.text(repo_root / "docs/status.md") or ""
    no_sim_source = "docs/knowledge-status.md" if "No simulation" in knowledge_status else ("docs/status.md" if "simulation" in status_doc.lower() else "docs/")
    m["knowledge_items_used"] = metric({"skills": 0, "rules": 0, "blocks": 0, "components": 0, "references": 0, "project_rules": 8},
                                       "docs/pcb-design-rules.md", "documented",
                                       note="no knowledge system existed for V1; only the eight project PCB rules were applied in review")
    m["knowledge_applicability"] = metric({"direct": 0, "adapted": 0, "not-applicable": 0, "human-review": 0}, None, "documented")
    m["knowledge_queries"] = metric(0, None, "documented", note="no retrieval interface existed")
    m["simulation_runs"] = metric(0, no_sim_source, "documented",
                                  note="'No simulation or hardware validation' (docs/knowledge-status.md); docs/status.md lists no simulation milestone")
    m["simulation_models"] = metric(0, no_sim_source, "documented")
    m["parasitic_studies"] = metric(0, no_sim_source, "documented")
    test_counts = count_test_functions([repo_root / "tests/test_setup.py"]) if (repo_root / "tests/test_setup.py").is_file() else {}
    m["test_modules"] = metric(len(test_counts), "tests/test_setup.py", note="V1-era module; docs/status.md: 'Six automation tests pass'")
    m["test_functions"] = metric(sum(test_counts.values()), "tests/test_setup.py", note="docs/status.md: 'Six automation tests pass'")

    docs = markdown_volume(src.glob("design/*.md", root) + src.glob("review/*.md", root) + src.glob("verification/*.md", root))
    m["documentation_files"] = metric(docs["files"], "design/, review/, verification/ (*.md)")
    m["documentation_words"] = metric(docs["words"], "design/, review/, verification/ (*.md)")

    thermal = src.text(root / "design/thermal_estimate.md") or ""
    m["thermal_document_words"] = metric(word_count(thermal), "design/thermal_estimate.md")
    m["thermal_corners"] = metric(1, "design/thermal_estimate.md", "documented", note="one illustrative 95 C junction estimate at 50 C ambient")
    m["thermal_heatsink"] = metric("external sink <= 1.5 C/W, part not selected", "design/thermal_estimate.md", "documented")
    m["thermal_interface"] = metric("0.5 C/W per isolated TO-220 interface, material not selected", "design/thermal_estimate.md", "documented")
    m["thermal_fan_failure"] = metric(False, "design/thermal_estimate.md", "documented", note="no cooling-failure analysis")
    m["thermal_sensor_mapping"] = metric("LM61 measures power-area PCB temperature, not junction", "design/architecture.md", "documented")

    m["tallest_part_mm"] = metric(V1_TALLEST_PART_MM, "design/pcb_stackup.md", "documented", "mm", "upright inductor envelope")
    thickness = value_of(m["board_thickness_mm"], 2.0)
    m["assembly_height_mm"] = metric(thickness + V1_TALLEST_PART_MM, "design/pcb_stackup.md", "derived", "mm", "board thickness + tallest part")
    m["sources"] = {"read": src.read, "missing": src.missing}
    return m


# --- V2 collection -------------------------------------------------------------------------------------------

def _research_summary(src: Sources, research_dir: Path) -> dict:
    research = [p for p in src.glob("*.json", research_dir) if not p.name.startswith("verify_")]
    verifies = src.glob("verify_*.json", research_dir)
    verdicts, item_status, agrees, required, misuse, lenses = Counter(), Counter(), Counter(), 0, 0, Counter()
    for path in verifies:
        data = src.json(path) or {}
        verdicts[str(data.get("verdict"))] += 1
        lenses[str(data.get("lens"))] += 1
        for item in data.get("checked_items", []) or []:
            item_status[str(item.get("status"))] += 1
        for item in data.get("recomputed", []) or []:
            agrees["agrees" if item.get("agrees") else "disagrees"] += 1
        required += len(data.get("required_changes", []) or [])
        misuse += len(data.get("knowledge_misuse", []) or [])
    for path in research:
        src.json(path)
    return {"research_records": len(research), "verification_records": len(verifies), "verdicts": dict(verdicts),
            "lenses": dict(lenses), "checked_item_status": dict(item_status), "recomputed": dict(agrees),
            "required_changes": required, "knowledge_misuse_items": misuse}


def _circuit_summary(parts) -> dict | None:
    if not isinstance(parts, list):
        return None
    nets = {n for p in parts for n in (p.get("nets") or {}).values() if n}
    custom = {p.get("footprint") for p in parts if str(p.get("footprint", "")).split(":")[0].upper().startswith("AIPE")}
    return {"parts": len(parts), "dnp": sum(1 for p in parts if p.get("dnp")), "nets": len(nets),
            "pages": len({p.get("page") for p in parts}), "custom_footprints": len(custom),
            "distinct_mpn": len({p.get("mpn") for p in parts if p.get("mpn")}),
            "distinct_makers": len({p.get("maker") for p in parts if p.get("maker")}),
            "purchased": sum(1 for p in parts if p.get("kind") not in ("TP", "H", "HS") and not p.get("dnp"))}


def _layout_metrics_summary(lm: dict) -> dict:
    """Headline numbers from a check_sic_layout.py layout_metrics_<board>.json document."""
    board = lm.get("board", {}) or {}
    com = lm.get("commutation", {}) or {}
    hf = []
    for mosfet in com.get("mosfets", []) or []:
        for entry in (mosfet.get("pins") or {}).values():
            if isinstance(entry, dict) and isinstance(entry.get("nearest_same_net_mm"), (int, float)):
                hf.append(entry["nearest_same_net_mm"])
    gate = [g.get("driver_output_to_gate_pad_mm") for g in (lm.get("gate_loops", {}) or {}).get("loops", []) or []]
    sw = {layer: v.get("total_mm2") for layer, v in (com.get("sw_copper_mm2") or {}).items() if isinstance(v, dict)}
    iso = lm.get("isolation", {}) or {}
    pair_min = []
    for pair in iso.get("pairs", []) or []:
        for layer in (pair.get("per_layer") or {}).values():
            if isinstance(layer, dict) and isinstance(layer.get("distance_mm"), (int, float)):
                pair_min.append(layer["distance_mm"])
    barrier_paths = [b.get("surface_path_mm") for b in iso.get("barrier_parts", []) or []]
    comp = lm.get("compactness", {}) or {}
    dsp = [b.get("distance_mm") for b in (lm.get("control", {}) or {}).get("dsp_bypass", []) or []]
    summary = lm.get("summary", {}) or {}
    return {"outline_mm": coerce_board_mm(board.get("outline_mm")), "area_mm2": board.get("outline_area_mm2"),
            "copper_layers": board.get("copper_layers"), "thickness_mm": board.get("thickness_mm"), "copper_um": board.get("copper_um"),
            "footprints": board.get("footprints"), "tracks": board.get("tracks"), "vias": board.get("vias"), "nets": board.get("nets"),
            "hf_capacitor_to_device_mm": min_max(hf), "driver_to_gate_pin_mm": min_max(gate), "sw_copper_mm2": sw or None,
            "sw_copper_total_mm2": sum(v for v in sw.values() if isinstance(v, (int, float))) if sw else None,
            "isolation_min_distance_mm": min(pair_min) if pair_min else None, "isolation_pairs_within": sum(1 for p in iso.get("pairs", []) or [] if p.get("within_threshold")),
            "isolation_pairs": len(iso.get("pairs", []) or []), "barrier_parts": len(iso.get("barrier_parts", []) or []),
            "barrier_surface_path_min_mm": min(v for v in barrier_paths if isinstance(v, (int, float))) if any(isinstance(v, (int, float)) for v in barrier_paths) else None,
            "dsp_bypass_max_mm": max(d for d in dsp if isinstance(d, (int, float))) if any(isinstance(d, (int, float)) for d in dsp) else None,
            "power_density_W_per_dm2": comp.get("power_density_W_per_dm2"), "power_density_W_per_L": comp.get("power_density_W_per_L"),
            "assembly_height_mm": dig(comp, "assembly_height_mm", "used"), "footprints_per_dm2": comp.get("footprints_per_dm2"),
            "rule_rows": summary.get("rows"), "within_threshold": summary.get("within_threshold"), "exceeding_threshold": summary.get("exceeding_threshold"),
            "not_measured": summary.get("not_measured"), "board_sha256": board.get("sha256")}


def _simulation_summary(cs: dict) -> dict:
    runs = cs.get("runs", {}) or {}
    controllers = Counter(str(r.get("controller")) for r in runs.values())
    steady_pass = steady_total = event_pass = event_total = 0
    ripple, excursions, recoveries, raw_max, failed = [], [], [], [], []
    for name, run in runs.items():
        campaign = run.get("campaign", {}) or {}
        checks = campaign.get("steady_checks", {}) or {}
        steady_total += len(checks)
        steady_pass += sum(1 for v in checks.values() if v)
        for event in campaign.get("events", []) or []:
            event_checks = event.get("checks", {}) or {}
            event_total += len(event_checks)
            event_pass += sum(1 for v in event_checks.values() if v)
            failing = sorted(k for k, v in event_checks.items() if not v)
            if failing:
                failed.append({"run": name, "event": event.get("type"), "failed_checks": failing,
                               "load_step_A": [event.get("i_load_before_A"), event.get("i_load_after_A")]})
            if isinstance(event.get("excursion_cycle_avg_V"), (int, float)):
                excursions.append(abs(event["excursion_cycle_avg_V"]))
            if isinstance(event.get("recovery_time_s"), (int, float)):
                recoveries.append(event["recovery_time_s"] * 1e3)
            if isinstance(event.get("vout_raw_max_V"), (int, float)):
                raw_max.append(event["vout_raw_max_V"])
        value = (run.get("metrics", {}) or {}).get("vout_pkpk")
        if isinstance(value, (int, float)):
            ripple.append(value)
    warnings = sum(len(r.get("warnings", []) or []) for r in runs.values())
    loop = cs.get("loop_gain_analysis")
    return {"runs": len(runs), "controllers": dict(controllers), "steady_checks_passed": steady_pass, "steady_checks_total": steady_total,
            "event_checks_passed": event_pass, "event_checks_total": event_total, "failed_event_checks": failed,
            "events": sum(len((r.get("campaign", {}) or {}).get("events", []) or []) for r in runs.values()),
            "vout_ripple_Vpp": min_max(ripple), "load_step_excursion_V": min_max(excursions), "recovery_ms": min_max(recoveries),
            "vout_raw_max_V": max(raw_max) if raw_max else None, "ngspice_warnings": warnings,
            "parasitic_cases": len(cs.get("parasitic_sweep", []) or []), "total_runtime_s": cs.get("total_runtime_s"),
            "cross_check_vout_mean_pct": dig(cs, "cross_check_max_abs_deviation_pct_open_loop_ccm_runs", "vout_mean"),
            "loop_gain_analysis": bool(loop), "ngspice": cs.get("ngspice"),
            "limits": {k: v for k, v in (cs.get("limits", {}) or {}).items() if isinstance(v, (int, float))}}


def collect_v2(root: Path, repo_root: Path | None = None) -> dict:
    """Metrics of the V2 example; PCB-phase files are read defensively and marked pending when absent."""
    root = Path(root)
    repo_root = Path(repo_root) if repo_root else root.parents[1]
    src = Sources(repo_root)
    m: dict = {"generation": "V2", "name": "400 V -> 200 V / 5 kW / 50 kHz SiC synchronous buck, power board + SELV control board"}

    req_text = src.text(root / "input/requirements.yaml")
    req = parse_simple_yaml(req_text) if req_text else {}
    conv = req.get("converter", {}) if isinstance(req, dict) else {}
    dd = src.json(root / "design/design_decisions.json") or {}
    user = dd.get("requirements_user", {}) or {}
    m["vin_nominal_V"] = metric(conv.get("input_voltage_nominal_V", user.get("vin_nominal_V")), "input/requirements.yaml", "documented", "V")
    m["vout_V"] = metric(conv.get("output_voltage_V", user.get("vout_V")), "input/requirements.yaml", "documented", "V")
    m["pout_W"] = metric(conv.get("output_power_W", user.get("pout_W")), "input/requirements.yaml", "documented", "W")
    m["iout_A"] = metric(conv.get("output_current_nominal_A", user.get("iout_A")), "input/requirements.yaml", "documented", "A")
    m["fsw_Hz"] = metric(conv.get("switching_frequency_Hz", user.get("fsw_Hz")), "input/requirements.yaml", "documented", "Hz")
    m["vin_range_V"] = metric(dig(dd, "assumptions_accepted", "vin_operating_range_V"), "design/design_decisions.json", "documented", "V", kind="range")
    arch = dd.get("architecture", {}) or {}
    power = arch.get("power_board", {}) or {}
    control = arch.get("control_board", {}) or {}
    m["board_count"] = metric(2 if power and control else (1 if power or control else None), "design/design_decisions.json", "documented")
    m["architecture"] = metric(clip(arch.get("option"), 90), "design/design_decisions.json", "documented")
    m["architecture_scores"] = metric(arch.get("scores"), "design/design_decisions.json", "documented")
    m["board_outlines_planned"] = metric({"power": coerce_board_mm(power.get("outline_mm")), "control": coerce_board_mm(control.get("outline_mm"))},
                                         "design/design_decisions.json", "planned", "mm", kind="dims")
    m["copper_layers_planned"] = metric({"power": power.get("layers"), "control": control.get("layers")}, "design/design_decisions.json", "planned")
    m["copper_um_planned"] = metric({"power": power.get("copper_um"), "control": control.get("copper_um")}, "design/design_decisions.json", "planned", "um")
    m["board_thickness_planned_mm"] = metric({"power": power.get("thickness_mm"), "control": control.get("thickness_mm")}, "design/design_decisions.json", "planned", "mm")
    m["layout_targets"] = metric(arch.get("target_metrics_after_layout"), "design/design_decisions.json", "planned")
    m["assembly_height_mm"] = metric(parse_height_mm(arch.get("mechanical")) or V2_ASSEMBLY_HEIGHT_MM, "design/design_decisions.json", "documented", "mm",
                                     "standoffs + board + heatsink (architecture.mechanical)")
    m["assumptions_accepted"] = metric(len(dd.get("assumptions_accepted", {}) or {}), "design/design_decisions.json")
    m["conflict_resolutions"] = metric(len(dd.get("conflict_resolutions", []) or []), "design/design_decisions.json")
    m["open_items_for_human_review"] = metric(len(dd.get("open_items_for_human_review", []) or []), "design/design_decisions.json")
    m["operating_points_baseline"] = metric(len(dd.get("operating_points", []) or []), "design/design_decisions.json")
    mosfet = dig(dd, "power_stage", "mosfet") or {}
    m["mosfet"] = metric({"part": mosfet.get("part"), "manufacturer": mosfet.get("manufacturer"), "qty": mosfet.get("qty"), "package": mosfet.get("package"),
                          "voltage_rating": "1200 V class" if mosfet else None} if mosfet else None, "design/design_decisions.json", "documented")
    driver = dig(dd, "power_stage", "gate_driver") or {}
    bias = dig(dd, "power_stage", "bias_supply") or {}
    m["gate_driver"] = metric({"part": driver.get("part"), "isolation": clip(driver.get("isolation"), 70), "bias": f"{clip(bias.get('qty'), 40)} x {bias.get('part')}" if bias else None}
                              if driver else None, "design/design_decisions.json", "documented")
    current = dig(dd, "sensing", "current") or {}
    m["current_sensing"] = metric({"part": current.get("part"), "method": "isolated Hall sensor in the inductor output path"} if current else None,
                                  "design/design_decisions.json", "documented")
    rules = dig(dd, "standards_and_spacing", "kicad_rules_mm") or {}
    m["isolation_concept"] = metric(clip(dig(dd, "assumptions_accepted", "isolation_concept"), 170), "design/design_decisions.json", "documented")
    m["isolation_rules_mm"] = metric({k: v for k, v in rules.items() if isinstance(v, (int, float))} or None, "design/design_decisions.json", "documented", "mm")
    short_rules = {"HV to SELV (all layers)": "HV_or_DRV_or_DESAT_or_SENSE_ISO_to_CTRL_SELV_all_layers", "barrier strip": "ISO_BARRIER_keepout_width",
                   "HV to PE": "HV_to_PE", "HV functional outer/inner": ("HV_functional_outer", "HV_functional_inner")}
    picked = {}
    for label, key in short_rules.items():
        if isinstance(key, tuple):
            values = [rules.get(k) for k in key]
            if all(isinstance(v, (int, float)) for v in values):
                picked[label] = values
        elif isinstance(rules.get(key), (int, float)):
            picked[label] = rules[key]
    m["isolation_rules_headline_mm"] = metric(picked or None, "design/design_decisions.json", "documented", "mm", kind="list")
    thermal = dd.get("thermal", {}) or {}
    m["thermal_heatsink"] = metric(clip(thermal.get("heatsink"), 90), "design/design_decisions.json", "documented")
    m["thermal_interface"] = metric(clip(thermal.get("interface_pad"), 90), "design/design_decisions.json", "documented")
    assumptions = src.text(root / "design/assumptions.md") or ""
    m["assumption_rows"] = metric(count_markdown_table_rows(assumptions, r"^\|\s*(A|U|D|H)-\d+\s*\|"), "design/assumptions.md", note="U-/A- register rows")

    kt = src.json(root / "design/knowledge_trace.json") or {}
    coverage = kt.get("coverage", {}) or {}
    project_ids = dig(coverage, "project_rules", "ids") or []
    aggregate_ids = [i for i in project_ids if not re.fullmatch(r"PE-PCB-\d{3}", str(i))]
    m["knowledge_items_used"] = metric({k: v.get("used") for k, v in coverage.items()} or None, "design/knowledge_trace.json",
                                       note=(f"project_rules counts {len(aggregate_ids)} aggregate citation string(s) such as '{aggregate_ids[0]}' besides the "
                                             f"{len(project_ids) - len(aggregate_ids)} individual rules") if aggregate_ids else None)
    m["knowledge_items_total"] = metric({k: v.get("total") for k, v in coverage.items()} or None, "design/knowledge_trace.json")
    m["knowledge_applicability"] = metric(kt.get("by_applicability"), "design/knowledge_trace.json")
    m["knowledge_citation_rows"] = metric(len(kt.get("rows", []) or []), "design/knowledge_trace.json")
    m["knowledge_distinct_ids"] = metric(len({r.get("id") for r in kt.get("rows", []) or [] if r.get("id")}), "design/knowledge_trace.json")
    m["knowledge_unknown_ids"] = metric(len(kt.get("unknown_ids", []) or []), "design/knowledge_trace.json")
    m["knowledge_queries"] = metric(sum(len(v) for v in (kt.get("queries", {}) or {}).values()), "design/knowledge_trace.json")
    m["knowledge_areas"] = metric(len(kt.get("areas", []) or []), "design/knowledge_trace.json")
    validation = Counter(str(r.get("validation_status")) for r in kt.get("rows", []) or [] if r.get("validation_status"))
    m["knowledge_validation_status"] = metric(dict(validation) or None, "design/knowledge_trace.json")

    research = _research_summary(src, root / "design/research")
    m["research_records"] = metric(research["research_records"], "design/research/*.json")
    m["verification_records"] = metric(research["verification_records"], "design/research/verify_*.json")
    m["verification_verdicts"] = metric(research["verdicts"] or None, "design/research/verify_*.json")
    m["verification_lenses"] = metric(research["lenses"] or None, "design/research/verify_*.json")
    m["verification_checked_items"] = metric(research["checked_item_status"] or None, "design/research/verify_*.json")
    m["verification_recomputed"] = metric(research["recomputed"] or None, "design/research/verify_*.json")
    m["verification_required_changes"] = metric(research["required_changes"], "design/research/verify_*.json")
    m["verification_knowledge_misuse"] = metric(research["knowledge_misuse_items"], "design/research/verify_*.json")
    m["consistency_review"] = metric((root / "design/consistency_review.md").is_file(), "design/consistency_review.md")
    m["independent_review_records"] = metric(research["verification_records"] + (1 if (root / "design/consistency_review.md").is_file() else 0),
                                             "design/research/verify_*.json, design/consistency_review.md",
                                             note="two verifier lenses per research area plus the cross-document consistency review")
    m["review_lenses"] = metric(sorted(research["lenses"]) + (["consistency-review"] if (root / "design/consistency_review.md").is_file() else []),
                                "design/research/", "counted")

    calc = src.json(root / "design/calculations.json") or {}
    m["operating_points"] = metric(len(calc.get("operating_points", []) or []), "design/calculations.json")
    m["calculation_inputs_register"] = metric(len(calc.get("inputs_register", []) or []), "design/calculations.json")
    invariants = calc.get("invariants", []) or []
    m["calculation_invariants"] = metric(len(invariants), "design/calculations.json", note=f"{sum(1 for i in invariants if i.get('status') == 'PASS')} PASS")
    crosscheck = calc.get("baseline_crosscheck", []) or []
    m["baseline_crosscheck"] = metric({"items": len(crosscheck), "agrees": sum(1 for c in crosscheck if c.get("status") == "agrees")} if crosscheck else None,
                                      "design/calculations.json")
    eff = calc.get("efficiency", {}) or {}
    scenarios = {s.get("scenario"): s for s in eff.get("scenarios", []) or [] if isinstance(s, dict)}
    typical = scenarios.get("typical_expected") or (next(iter(scenarios.values())) if scenarios else {})
    m["total_loss_W"] = metric(typical.get("converter_loss_W"), "design/calculations.json", "documented", "W", "typical_expected scenario, converter only")
    m["efficiency_estimate"] = metric(typical.get("eta_converter_only"), "design/calculations.json", "documented", note="typical_expected scenario, converter only")
    m["efficiency_system"] = metric(typical.get("eta_system"), "design/calculations.json", "documented", note="including auxiliary electronics, relay hold and fan")
    m["efficiency_target"] = metric({"target": eff.get("target"), "floor": eff.get("floor")}, "design/calculations.json", "documented")
    m["efficiency_scenarios"] = metric(len(scenarios), "design/calculations.json")
    worst = min((s.get("eta_converter_only") for s in scenarios.values() if isinstance(s.get("eta_converter_only"), (int, float))), default=None)
    m["efficiency_sensitivity"] = metric(worst, "design/calculations.json", "documented", note="lowest converter-only efficiency over the recorded scenarios")
    m["loss_items"] = metric(len(eff.get("items_W", {}) or {}) + sum(1 for k in ("mosfet_pair_W", "inductor_W", "interconnect_W", "ring_W", "bleeders_W") if k in typical),
                             "design/calculations.json")
    m["calculation_limitations"] = metric(len(calc.get("limitations", []) or []), "design/calculations.json")
    m["calculation_open_items"] = metric(len(calc.get("open_items", []) or []), "design/calculations.json")
    th = calc.get("thermal", {}) or {}
    m["thermal_corners"] = metric(len(th.get("corners", []) or []), "design/calculations.json", note="loss/temperature corners (R variants x k_RG)")
    m["thermal_tj_expected_C"] = metric(dig(th, "expected_400V_25A_100C", "T_J_HS_C"), "design/calculations.json", "documented", "C", "HS junction at 400 V / 25 A, typical parts")
    m["thermal_tj_hottest_C"] = metric(dig(th, "hottest_HS_corner", "T_J_HS_C"), "design/calculations.json", "documented", "C",
                                       f"{dig(th, 'hottest_HS_corner', 'corner')} max R, k_RG {dig(th, 'hottest_HS_corner', 'k_RG')}")
    m["thermal_fan_failure"] = metric(bool(th.get("fan_failure")), "design/calculations.json", "documented",
                                      note=f"{len(th.get('fan_failure', []) or [])} natural-convection cases with time-to-trip")
    m["thermal_sensor_mapping"] = metric("heatsink NTC mapped to T_J with a stated offset band" if th.get("ntc_to_TJ_offset_K") else None, "design/calculations.json", "documented")
    thermal_doc = src.text(root / "design/thermal_analysis.md") or ""
    m["thermal_document_words"] = metric(word_count(thermal_doc), "design/thermal_analysis.md")

    circuits = {}
    for board in V2_BOARDS:
        circuits[board] = _circuit_summary(src.json(root / f"design/circuit_{board}.json"))
    present = {b: c for b, c in circuits.items() if c}
    m["circuit_parts"] = metric({b: c["parts"] for b, c in present.items()} or None, "design/circuit_*.json")
    m["footprints"] = metric(sum(c["parts"] for c in present.values()) if present else None, "design/circuit_*.json", note="schematic items on both boards (PCB footprint count follows after layout)")
    m["purchased_components"] = metric(sum(c["purchased"] for c in present.values()) if present else None, "design/circuit_*.json")
    m["dnp_parts"] = metric({b: c["dnp"] for b, c in present.items()} or None, "design/circuit_*.json")
    m["named_nets_per_board"] = metric({b: c["nets"] for b, c in present.items()} or None, "design/circuit_*.json")
    m["named_nets"] = metric(sum(c["nets"] for c in present.values()) if present else None, "design/circuit_*.json", note="sum over both boards")
    m["schematic_pages_model"] = metric({b: c["pages"] for b, c in present.items()} or None, "design/circuit_*.json")
    m["custom_footprints"] = metric(sum(c["custom_footprints"] for c in present.values()) if present else None, "design/circuit_*.json", note="distinct AIPE-library footprints")
    m["circuit_distinct_mpn"] = metric({b: c["distinct_mpn"] for b, c in present.items()} or None, "design/circuit_*.json")

    bom = src.csv(root / "components/bom.csv", ("manufacturer", "mpn"))
    m["bom_rows"] = metric(bom["rows"] if bom else None, "components/bom.csv")
    m["bom_distinct_mpn"] = metric(bom["distinct"]["mpn"] if bom else None, "components/bom.csv")
    m["bom_distinct_manufacturers"] = metric(bom["distinct"]["manufacturer"] if bom else None, "components/bom.csv")
    records = src.json(root / "components/component_records.json")
    records = records.get("records") if isinstance(records, dict) else records
    if isinstance(records, list):
        buckets = Counter(bucket_verification_level(r.get("verification_level")) for r in records if isinstance(r, dict))
        fields = sorted({k for r in records if isinstance(r, dict) for k in r})
        m["component_records"] = metric(len(records), "components/component_records.json", note="one record per part type")
        m["component_record_fields"] = metric(len(fields), "components/component_records.json")
        m["component_record_types"] = metric(len({r.get("mpn") for r in records if isinstance(r, dict)}), "components/component_records.json", note="distinct part numbers")
        m["component_verification_levels"] = metric(dict(buckets), "components/component_records.json")
        m["component_knowledge_refs"] = metric(sum(len(r.get("knowledge_refs", []) or []) for r in records if isinstance(r, dict)), "components/component_records.json")
        m["component_open_issues"] = metric(sum(len(r.get("open_issues", []) or []) for r in records if isinstance(r, dict)), "components/component_records.json")
        m["component_alternatives"] = metric(sum(len(r.get("alternatives", []) or []) for r in records if isinstance(r, dict)), "components/component_records.json")
    else:
        for key in ("component_records", "component_record_fields", "component_record_types", "component_verification_levels",
                    "component_knowledge_refs", "component_open_issues", "component_alternatives"):
            m[key] = pending("components/component_records.json", "component records not found")
    m["magnetic_record"] = metric((root / "components/magnetic_record.json").is_file(), "components/magnetic_record.json")

    # Native checks: latest ERC and DRC per board.
    erc = {board_key_for_stem(stem): rec for stem, rec in latest_runs(root / "verification/erc", "erc").items()}
    for board in V2_BOARDS:
        rec = erc.get(board)
        m[f"erc_findings_{board}"] = metric(rec.get("finding_count"), f"verification/erc/{rec['run_dir']}/run.json", "measured") if rec else pending("verification/erc/", "no ERC run for this board yet")
    m["erc_findings"] = metric(sum(value_of(m[f"erc_findings_{b}"], 0) for b in V2_BOARDS), "verification/erc/*/run.json", "measured", note="sum of the latest run per board") \
        if all(not is_pending(m[f"erc_findings_{b}"]) for b in V2_BOARDS) else pending("verification/erc/", "ERC not recorded for every board yet")
    m["erc_runs_recorded"] = metric(len(src.glob("*-erc-*/run.json", root / "verification/erc")), "verification/erc/")
    drc = {board_key_for_stem(stem): rec for stem, rec in latest_runs(root / "verification/drc", "drc").items()}
    for board in V2_BOARDS:
        rec = drc.get(board)
        m[f"drc_findings_{board}"] = metric(rec.get("finding_count"), f"verification/drc/{rec['run_dir']}/run.json", "measured") if rec else pending("verification/drc/")
    m["drc_findings"] = metric(sum(value_of(m[f"drc_findings_{b}"], 0) for b in V2_BOARDS), "verification/drc/*/run.json", "measured", note="sum of the latest run per board") \
        if all(not is_pending(m[f"drc_findings_{b}"]) for b in V2_BOARDS) else pending("verification/drc/")
    m["drc_runs_recorded"] = metric(len(src.glob("*-drc-*/run.json", root / "verification/drc")), "verification/drc/")
    vsum = src.json(root / "verification/verification-summary.json")
    m["verification_status"] = metric(vsum.get("status"), "verification/verification-summary.json", "measured",
                                      note=f"{len(vsum.get('problems', []) or [])} open problems listed") if vsum else pending("verification/verification-summary.json")
    smoke = src.json(root / "verification/environment/v2-pipeline-smoke.json")
    m["pipeline_smoke"] = metric(smoke.get("status"), "verification/environment/v2-pipeline-smoke.json", "measured",
                                 note="footprints -> schematic -> routing -> DRC -> exports -> ngspice on a disposable half bridge") if smoke else pending("verification/environment/v2-pipeline-smoke.json", "pipeline smoke record not found")

    # Boards, placement candidates, layout metrics, exports, release: PCB phase.
    sheets = {b: len(src.glob("*.kicad_sch", root / "kicad" / f"{b}_board")) for b in V2_BOARDS}
    m["schematic_sheets_per_board"] = metric({b: n for b, n in sheets.items() if n} or None, "kicad/*/")
    m["schematic_sheets"] = metric(sum(sheets.values()) or None, "kicad/*/", note="sum over both boards")
    boards = src.glob("*/*.kicad_pcb", root / "kicad")
    m["board_files"] = metric(len(boards), "kicad/*/", "counted") if boards else pending("kicad/*/*.kicad_pcb")
    placements = src.glob("placement_*.json", root / "design")
    if placements:
        candidates = {}
        for path in placements:
            data = src.json(path) or {}
            candidates[path.stem] = coerce_board_mm(data if isinstance(data, dict) else None)
        m["placement_candidates"] = metric(len(placements), "design/placement_*.json")
        m["placement_board_mm"] = metric(candidates, "design/placement_*.json", "measured", "mm")
    else:
        m["placement_candidates"] = pending("design/placement_*.json")
        m["placement_board_mm"] = pending("design/placement_*.json")
    layout = {}
    for board in V2_BOARDS:
        lm = src.json(root / f"verification/engineering_checks/layout_metrics_{board}.json")
        if lm:
            layout[board] = _layout_metrics_summary(lm)
    m["layout_metrics_boards"] = metric(sorted(layout), "verification/engineering_checks/layout_metrics_*.json", "measured") if layout else pending("verification/engineering_checks/layout_metrics_*.json")
    if layout:
        lsrc = "verification/engineering_checks/layout_metrics_*.json"
        m["board_outlines"] = metric({b: l["outline_mm"] for b, l in layout.items()}, lsrc, "measured", "mm", kind="dims")
        m["total_board_area_mm2"] = metric(sum(l["area_mm2"] for l in layout.values() if l["area_mm2"]) or None, lsrc, "measured", "mm2")
        m["copper_layers"] = metric({b: l["copper_layers"] for b, l in layout.items()}, lsrc, "measured")
        m["board_thickness_mm"] = metric({b: l["thickness_mm"] for b, l in layout.items()}, lsrc, "measured", "mm")
        m["copper_um"] = metric({b: l["copper_um"] for b, l in layout.items()}, lsrc, "measured", "um")
        m["pcb_footprints"] = metric(sum(l["footprints"] or 0 for l in layout.values()), lsrc, "measured")
        m["tracks"] = metric(sum(l["tracks"] or 0 for l in layout.values()), lsrc, "measured")
        m["vias"] = metric(sum(l["vias"] or 0 for l in layout.values()), lsrc, "measured")
        power_l = layout.get("power", {})
        m["hf_capacitor_to_device_mm"] = metric(power_l.get("hf_capacitor_to_device_mm"), lsrc, "measured", "mm", "MOSFET drain/source pad to nearest same-net HF capacitor pad", kind="range")
        m["driver_to_gate_pin_mm"] = metric(power_l.get("driver_to_gate_pin_mm"), lsrc, "measured", "mm", kind="range")
        m["sw_copper_mm2"] = metric(power_l.get("sw_copper_mm2"), lsrc, "measured", "mm2")
        m["sw_copper_total_mm2"] = metric(power_l.get("sw_copper_total_mm2"), lsrc, "measured", "mm2")
        m["isolation_min_distance_mm"] = metric(power_l.get("isolation_min_distance_mm"), lsrc, "measured", "mm",
                                                f"{power_l.get('isolation_pairs_within')}/{power_l.get('isolation_pairs')} class pairs within threshold")
        m["barrier_parts"] = metric(power_l.get("barrier_parts"), lsrc, "measured")
        m["barrier_surface_path_min_mm"] = metric(power_l.get("barrier_surface_path_min_mm"), lsrc, "measured", "mm")
        control_l = layout.get("control", {})
        m["dsp_bypass_max_mm"] = metric(control_l.get("dsp_bypass_max_mm"), lsrc, "measured", "mm")
        m["layout_rule_rows"] = metric({b: {"rows": l["rule_rows"], "within": l["within_threshold"], "exceeding": l["exceeding_threshold"], "not_measured": l["not_measured"]}
                                        for b, l in layout.items()}, lsrc, "measured")
        m["checker_power_density"] = metric({b: {"W_per_dm2": l["power_density_W_per_dm2"], "W_per_L": l["power_density_W_per_L"], "height_mm": l["assembly_height_mm"]}
                                             for b, l in layout.items()}, lsrc, "measured", note="checker figures use the spec assembly height, which may differ from the task height")
    else:
        planned_area = sum(a for a in (board_area_mm2(power.get("outline_mm")), board_area_mm2(control.get("outline_mm"))) if a) or None
        m["board_outlines"] = metric(value_of(m["board_outlines_planned"]), "design/design_decisions.json", "planned", "mm", PENDING_NOTE, kind="dims") if planned_area else pending("design/design_decisions.json")
        m["total_board_area_mm2"] = metric(planned_area, "design/design_decisions.json", "planned", "mm2", PENDING_NOTE) if planned_area else pending("design/design_decisions.json")
        m["copper_layers"] = metric(value_of(m["copper_layers_planned"]), "design/design_decisions.json", "planned", None, PENDING_NOTE) if power else pending()
        m["board_thickness_mm"] = metric(value_of(m["board_thickness_planned_mm"]), "design/design_decisions.json", "planned", "mm", PENDING_NOTE) if power else pending()
        m["copper_um"] = metric(value_of(m["copper_um_planned"]), "design/design_decisions.json", "planned", "um", PENDING_NOTE) if power else pending()
        for key in ("pcb_footprints", "tracks", "vias", "hf_capacitor_to_device_mm", "driver_to_gate_pin_mm", "sw_copper_mm2", "sw_copper_total_mm2",
                    "isolation_min_distance_mm", "barrier_surface_path_min_mm", "dsp_bypass_max_mm", "layout_rule_rows", "checker_power_density"):
            m[key] = pending("verification/engineering_checks/layout_metrics_*.json")
        spec = src.json(root / "verification/engineering_checks/layout_spec_power.json") or {}
        barrier = len(dig(spec, "isolation", "barrier_parts") or [])
        m["barrier_parts"] = metric(barrier, "verification/engineering_checks/layout_spec_power.json", "planned", note="barrier parts listed in the layout spec") if barrier else pending()
    m["layout_specs"] = metric(len(src.glob("layout_spec_*.json", root / "verification/engineering_checks")), "verification/engineering_checks/")
    m["critical_topology_checks"] = metric(sum(l.get("rule_rows") or 0 for l in layout.values()), "verification/engineering_checks/layout_metrics_*.json", "measured") if layout \
        else pending("verification/engineering_checks/layout_metrics_*.json")

    manifests = src.glob("*/export-manifest.json", root / "manufacturing")
    if manifests:
        per_board = {}
        for path in manifests:
            data = src.json(path) or {}
            per_board[path.parent.name] = {"commands": len(data.get("commands", []) or []), "artifacts": len(data.get("artifacts", {}) or {}), "status": data.get("status")}
        m["export_manifests"] = metric(per_board, "manufacturing/*/export-manifest.json", "measured")
        m["export_manifest_commands"] = metric(sum(v["commands"] for v in per_board.values()), "manufacturing/*/export-manifest.json", "measured")
        m["export_manifest_artifacts"] = metric(sum(v["artifacts"] for v in per_board.values()), "manufacturing/*/export-manifest.json", "measured")
    else:
        m["export_manifests"] = pending("manufacturing/*/export-manifest.json")
        m["export_manifest_commands"] = pending("manufacturing/*/export-manifest.json")
        m["export_manifest_artifacts"] = pending("manufacturing/*/export-manifest.json")
    releases = src.glob("*/SHA256SUMS.json", root / "releases")
    m["release_frozen"] = metric(True, releases[0].parent.name, "counted") if releases else pending("releases/")
    m["release_files"] = metric(len(src.json(releases[0]) or {}), "releases/", "counted") if releases else pending("releases/")
    issues_path = next((root / p for p in ("verification/known_issues.md", "review/known_issues.md") if (root / p).is_file()), None)
    m["documented_open_issues"] = metric(count_markdown_table_rows(src.text(issues_path) or ""), src.rel(issues_path)) if issues_path else \
        pending("verification/known_issues.md", "PCB-level known-issues register not written yet; design-level open items are counted separately")
    report_path = next((root / p for p in ("review/design_report.md",) if (root / p).is_file()), None)
    m["design_report_words"] = metric(word_count(src.text(report_path) or ""), "review/design_report.md") if report_path else pending("review/design_report.md")

    cs = src.json(root / "simulation/results/campaign_summary.json")
    if cs:
        sim = _simulation_summary(cs)
        m["simulation_runs"] = metric(sim["runs"], "simulation/results/campaign_summary.json", "measured", note=fmt(sim["controllers"]))
        m["simulation_summary"] = metric(sim, "simulation/results/campaign_summary.json", "measured")
        m["parasitic_studies"] = metric(sim["parasitic_cases"], "simulation/results/campaign_summary.json", "measured")
        m["simulation_steady_checks"] = metric(f"{sim['steady_checks_passed']}/{sim['steady_checks_total']}", "simulation/results/campaign_summary.json", "measured")
        failed_runs = sorted({f"{f['run']} ({f['event']})" for f in sim["failed_event_checks"]})
        m["simulation_event_checks"] = metric(f"{sim['event_checks_passed']}/{sim['event_checks_total']}", "simulation/results/campaign_summary.json", "measured",
                                              note=("failing checks in " + ", ".join(failed_runs) + ": the 12.5 A-step limits (10 V / 5 ms) applied to the 25 A load-dump events, "
                                                    "whose design-basis limit is the 230 V output OVP, plus the deliberately failing single-loop reference case") if failed_runs else "all event checks pass")
        m["simulation_vout_ripple_Vpp"] = metric(sim["vout_ripple_Vpp"], "simulation/results/campaign_summary.json", "measured", "Vpp", kind="range")
        m["simulation_load_step_excursion_V"] = metric(sim["load_step_excursion_V"], "simulation/results/campaign_summary.json", "measured", "V", kind="range")
        m["simulation_recovery_ms"] = metric(sim["recovery_ms"], "simulation/results/campaign_summary.json", "measured", "ms", kind="range")
        m["simulation_vout_raw_max_V"] = metric(sim["vout_raw_max_V"], "simulation/results/campaign_summary.json", "measured", "V", "worst raw output peak over the load-dump events")
    else:
        for key in ("simulation_runs", "simulation_summary", "parasitic_studies", "simulation_steady_checks", "simulation_event_checks",
                    "simulation_vout_ripple_Vpp", "simulation_load_step_excursion_V", "simulation_recovery_ms", "simulation_vout_raw_max_V"):
            m[key] = pending("simulation/results/campaign_summary.json", "simulation campaign summary not found")
    m["simulation_models"] = metric(len([p for p in src.glob("*.json", root / "simulation/models") if p.name != "campaign_manifest.json"]), "simulation/models/")
    m["simulation_report"] = metric((root / "simulation/simulation_report.md").is_file(), "simulation/simulation_report.md")

    tests = count_test_functions(src.glob("test_*.py", repo_root / "tests"))
    m["test_modules"] = metric(len(tests), "tests/", note="all automation test modules in the repository at V2 time")
    m["test_functions"] = metric(sum(tests.values()), "tests/")
    m["test_functions_per_module"] = metric(tests or None, "tests/")
    docs = markdown_volume(src.glob("design/*.md", root) + src.glob("review/*.md", root) + src.glob("simulation/*.md", root) + src.glob("verification/*.md", root))
    m["documentation_files"] = metric(docs["files"], "design/, review/, simulation/, verification/ (*.md)")
    m["documentation_words"] = metric(docs["words"], "design/, review/, simulation/, verification/ (*.md)", note="includes generated tables (knowledge_trace.md, calculations.md)")
    m["sources"] = {"read": src.read, "missing": src.missing}
    return m


# --- derived metrics -----------------------------------------------------------------------------------------

def derive(v1: dict, v2: dict) -> dict:
    """Specific power, density and cost proxies for both generations (planned V2 values flagged)."""
    out = {"v1": {}, "v2": {}}
    for key, m in (("v1", v1), ("v2", v2)):
        power = value_of(m.get("pout_W"))
        area_item = m.get("total_board_area_mm2")
        area = value_of(area_item)
        basis = "derived" if not is_pending(area_item) and area_item.get("basis") != "planned" else ("planned" if area else NOT_AVAILABLE)
        height = value_of(m.get("assembly_height_mm"))
        footprints = value_of(m.get("pcb_footprints")) if key == "v2" and not is_pending(m.get("pcb_footprints")) else value_of(m.get("footprints"))
        nets = value_of(m.get("named_nets"))
        boards = value_of(m.get("board_count")) or 1
        layers_item = m.get("copper_layers")
        layers = value_of(layers_item)
        outlines = value_of(m.get("board_outlines")) or {}
        if isinstance(layers, dict) and isinstance(outlines, dict):
            pairs = [(layers.get(b), board_area_mm2(o)) for b, o in outlines.items()]
        else:
            pairs = [(layers if isinstance(layers, (int, float)) else None, area)]
        note = None if basis == "derived" else PENDING_NOTE
        d = out[key]
        d["total_board_area_dm2"] = metric(area / 1e4 if area else None, None, basis, "dm2", note)
        d["specific_power_W_per_dm2"] = metric(specific_power_W_per_dm2(power, area), None, basis, "W/dm2", note)
        d["assembly_height_mm"] = metric(height, None, "documented", "mm")
        d["volume_L"] = metric(area * height / 1e6 if area and height else None, None, basis, "L", "summed board area x assembly height, not an enclosure volume")
        d["volumetric_power_W_per_L"] = metric(volumetric_power_W_per_L(power, area, height), None, basis, "W/L", note)
        d["components_per_dm2"] = metric(components_per_dm2(footprints, area), None, basis, "1/dm2", note)
        d["nets_per_board"] = metric(nets / boards if nets else None, None, "derived", "nets")
        d["cost_index_layer_dm2"] = metric(cost_index_layer_dm2(pairs), None, basis, "layer-dm2", "sum of copper layers x area per board; relative proxy, not a quotation")
        d["mosfet_count"] = metric(dig(value_of(m.get("mosfet")) or {}, "qty"), None, "documented")
        d["power_per_mosfet_W"] = metric(power / dig(value_of(m.get("mosfet")) or {}, "qty") if power and dig(value_of(m.get("mosfet")) or {}, "qty") else None, None, "derived", "W")
        d["bom_rows_per_kW"] = metric(value_of(m.get("bom_rows")) / (power / 1e3) if value_of(m.get("bom_rows")) and power else None, None, "derived", "rows/kW")
    return out


# --- workflow status -----------------------------------------------------------------------------------------

def _done(evidence: str) -> dict:
    return {"state": "done", "evidence": evidence}


def _not_done(evidence: str) -> dict:
    return {"state": "not done", "evidence": evidence}


def _pending(evidence: str) -> dict:
    return {"state": NOT_AVAILABLE, "evidence": evidence}


def workflow_status(v1: dict, v2: dict) -> dict:
    """Per workflow step: done / not done / not yet available with the evidence used, for both generations."""
    def v(m, key, default=None):
        return value_of(m.get(key), default)

    steps = {}
    steps["requirements_assumptions"] = {
        "v1": _done(f"input/requirements.yaml; design/assumptions.md ({v(v1, 'assumption_rows', 0)} rows)") if v(v1, "assumption_rows") else _not_done("assumptions register missing"),
        "v2": _done(f"input/requirements.yaml; design/assumptions.md ({v(v2, 'assumption_rows', 0)} register rows); design_decisions.json ({v(v2, 'assumptions_accepted', 0)} accepted assumptions, {v(v2, 'conflict_resolutions', 0)} conflict resolutions)")
        if v(v2, "assumption_rows") or v(v2, "assumptions_accepted") else _pending("assumptions register not found")}
    steps["knowledge_retrieval"] = {
        "v1": _not_done("no knowledge system existed (0 skills/rules retrievable)"),
        "v2": _done(f"knowledge_trace.json: {v(v2, 'knowledge_queries', 0)} logged queries over {v(v2, 'knowledge_areas', 0)} areas, {v(v2, 'knowledge_citation_rows', 0)} citation rows")
        if v(v2, "knowledge_citation_rows") else _pending("knowledge_trace.json not found")}
    steps["calculations_script"] = {
        "v1": _done(f"automation/scripts/calculate_buck.py -> design/calculations.json ({v(v1, 'operating_points', 0)} input cases, {v(v1, 'loss_items', 0)} loss items, no invariants)") if v(v1, "operating_points") else _not_done("calculations.json missing"),
        "v2": _done(f"automation/scripts/calculate_sic_buck.py -> design/calculations.json ({v(v2, 'operating_points', 0)} operating points, {v(v2, 'calculation_inputs_register', 0)} registered inputs, "
                    f"{v(v2, 'calculation_invariants', 0)} invariants, {dig(v(v2, 'baseline_crosscheck') or {}, 'items', default=0)} baseline cross-checks of which {dig(v(v2, 'baseline_crosscheck') or {}, 'agrees', default=0)} agree)")
        if v(v2, "operating_points") else _pending("calculations.json not found")}
    steps["component_records"] = {
        "v1": _done(f"component_selection.csv: {v(v1, 'component_records', 0)} rows x {v(v1, 'component_record_fields', 0)} fields; uniform verification sentence") if v(v1, "component_records") else _not_done("component records missing"),
        "v2": _done(f"component_records.json: {v(v2, 'component_records', 0)} part-type records x {v(v2, 'component_record_fields', 0)} fields with per-part verification levels ({fmt(v(v2, 'component_verification_levels'))})")
        if not is_pending(v2.get("component_records")) and v(v2, "component_records") else _pending("component_records.json not found")}
    steps["schematic_erc"] = {
        "v1": _done(f"{v(v1, 'schematic_sheets', 0)} sheets, latest ERC {v(v1, 'erc_findings')} findings") if v(v1, "erc_findings") is not None else _not_done("no ERC summary"),
        "v2": _done(f"{fmt(v(v2, 'schematic_sheets_per_board'))} sheets; latest ERC findings power {v(v2, 'erc_findings_power')} / control {v(v2, 'erc_findings_control')}")
        if not is_pending(v2.get("erc_findings")) else _pending("ERC not yet recorded for every board")}
    steps["simulation"] = {
        "v1": _not_done("no simulation (docs/knowledge-status.md)"),
        "v2": _done(f"{v(v2, 'simulation_runs', 0)} ngspice transient runs + {v(v2, 'parasitic_studies', 0)} parasitic cases; steady checks {v(v2, 'simulation_steady_checks')}, event checks {v(v2, 'simulation_event_checks')}")
        if not is_pending(v2.get("simulation_runs")) else _pending("campaign_summary.json not found")}
    steps["placement_candidates"] = {
        "v1": _done("design/placement.json: one placement, no alternatives compared") if v(v1, "placement_candidates") else _not_done("no placement record"),
        "v2": _done(f"{v(v2, 'placement_candidates')} placement file(s): {fmt(v(v2, 'placement_board_mm'))}") if not is_pending(v2.get("placement_candidates")) else _pending("design/placement_*.json not found")}
    steps["routing"] = {
        "v1": _done(f"{v(v1, 'tracks', 0)} tracks, {v(v1, 'vias', 0)} vias on {v(v1, 'copper_layers', 0)} layers") if v(v1, "tracks") else _not_done("no routed board metrics"),
        "v2": _done(f"{v(v2, 'board_files')} board file(s); {v(v2, 'tracks')} tracks, {v(v2, 'vias')} vias") if not is_pending(v2.get("board_files")) and not is_pending(v2.get("tracks")) else _pending("no .kicad_pcb / layout metrics yet")}
    steps["drc"] = {
        "v1": _done(f"latest DRC {v(v1, 'drc_findings')} findings ({v(v1, 'drc_runs_recorded', 0)} runs recorded)") if v(v1, "drc_findings") is not None else _not_done("no DRC summary"),
        "v2": _done(f"latest DRC findings power {v(v2, 'drc_findings_power')} / control {v(v2, 'drc_findings_control')}") if not is_pending(v2.get("drc_findings")) else _pending("verification/drc/ empty")}
    steps["layout_metrics"] = {
        "v1": _done(f"power-layout-metrics.json: {v(v1, 'critical_topology_checks', 0)} critical topology checks, rule review in pcb_rule_review.md") if v(v1, "critical_topology_checks") else _not_done("no layout metrics"),
        "v2": _done(f"layout_metrics_*.json for {fmt(v(v2, 'layout_metrics_boards'))}: {fmt(v(v2, 'layout_rule_rows'))}") if not is_pending(v2.get("layout_metrics_boards"))
        else _pending(f"checker and {v(v2, 'layout_specs', 0)} layout specs exist; metrics follow the routed boards")}
    steps["independent_review"] = {
        "v1": _done(f"{v(v1, 'independent_review_records', 0)} review records (AI visual review, PCB rule review); known_issues.md {v(v1, 'documented_open_issues', 0)} rows") if v(v1, "independent_review_records") else _not_done("no review records"),
        "v2": _done(f"{v(v2, 'verification_records', 0)} verify_*.json records ({fmt(v(v2, 'verification_verdicts'))}) + consistency review; PCB-level review {NOT_AVAILABLE}")
        if v(v2, "verification_records") else _pending("no verification records")}
    steps["release"] = {
        "v1": _done(f"releases/v1 frozen with SHA256SUMS.json ({v(v1, 'release_files', 0)} files) and review package zip") if v(v1, "release_frozen") else _not_done("not frozen"),
        "v2": _done(f"frozen release with {v(v2, 'release_files')} hashed files") if not is_pending(v2.get("release_frozen")) else _pending("releases/ empty")}
    return steps


# --- tables --------------------------------------------------------------------------------------------------

def specification_table(v1: dict, v2: dict) -> list:
    """Table 1: specification-driven differences and the metric effects they force."""
    def part(m, key, field):
        return dig(value_of(m.get(key)) or {}, field)

    rows = [
        ("Nominal input voltage", f"{fmt(value_of(v1.get('vin_nominal_V')))} V ({fmt(value_of(v1.get('vin_range_V')), kind='range')} V assumed range)",
         f"{fmt(value_of(v2.get('vin_nominal_V')))} V ({fmt(value_of(v2.get('vin_range_V')), kind='range')} V operating)",
         "8.3x higher voltage forces reinforced isolation, 9 mm HV-to-SELV spacing, copper-free barrier strips and 1200 V-class parts; it enlarges the HV area and lowers the achievable component density"),
        ("Output voltage", f"{fmt(value_of(v1.get('vout_V')))} V", f"{fmt(value_of(v2.get('vout_V')))} V (hazardous, insulated like the input)",
         "the output is a hazardous voltage in V2: isolated output sensing, bleeders and discharge-time requirements appear that V1 did not need"),
        ("Output power", f"{fmt(value_of(v1.get('pout_W')))} W", f"{fmt(value_of(v2.get('pout_W')))} W",
         "5x power raises W/dm2 and W/L arithmetically; the specific-power ratio between generations is therefore mostly specification, not layout skill"),
        ("Output current", f"{fmt(value_of(v1.get('iout_A')), 2)} A", f"{fmt(value_of(v2.get('iout_A')))} A",
         "V1 carries 1.7x more current at low voltage: heavy copper on six layers, 2 mohm shunt and M5 terminals were current-driven; V2 copper is sized for 25 A"),
        ("Switching frequency", f"{fmt((value_of(v1.get('fsw_Hz')) or 0) / 1e3)} kHz", f"{fmt((value_of(v2.get('fsw_Hz')) or 0) / 1e3)} kHz",
         "half the frequency with 8x the volt-seconds: a 27x larger inductance (custom 272 uH choke, 632 g) and film DC-link capacitors replace the 10 uH part and electrolytic bank"),
        ("Semiconductor class", f"{part(v1, 'mosfet', 'qty')} x {part(v1, 'mosfet', 'part')} ({part(v1, 'mosfet', 'voltage_rating')}, {part(v1, 'mosfet', 'package')})",
         f"{part(v2, 'mosfet', 'qty')} x {part(v2, 'mosfet', 'part')} ({part(v2, 'mosfet', 'voltage_rating')}, {part(v2, 'mosfet', 'package')})",
         "SiC allows two devices instead of four paralleled Si parts; fewer power footprints and a shorter commutation cell are a technology effect, not a layout-process result"),
        ("Gate drive", f"{part(v1, 'gate_driver', 'part')}: {part(v1, 'gate_driver', 'isolation')}",
         f"{part(v2, 'gate_driver', 'part')}: isolated ({part(v2, 'gate_driver', 'isolation')}); bias {part(v2, 'gate_driver', 'bias')}",
         "isolated drivers and three isolated bias modules add parts, barrier slots and decoupling islands; part count and BOM rows grow for safety reasons"),
        ("Current sensing", f"{part(v1, 'current_sensing', 'part')}: {part(v1, 'current_sensing', 'method')}", f"{part(v2, 'current_sensing', 'part')}: {part(v2, 'current_sensing', 'method')}",
         "isolated sensing removes the shunt loss and Kelvin-matching issue of V1 but adds an isolated supply and reinforced-isolation footprint"),
        ("Isolation concept", fmt(value_of(v1.get("isolation_concept"))), fmt(value_of(v2.get("isolation_concept"))),
         f"KiCad spacing rules ({fmt(value_of(v2.get('isolation_rules_headline_mm')))} mm) exist only in V2; any V2 clearance or barrier metric has no V1 counterpart"),
        ("Board architecture", f"{fmt(value_of(v1.get('architecture')))} ({fmt(value_of(v1.get('board_count')))} board)",
         f"option {fmt(value_of(v2.get('architecture')))} ({fmt(value_of(v2.get('board_count')))} boards, stacked mezzanine)",
         "the two-board split is an AI architecture decision scored against alternatives (A/B/C), so layer-count and area comparisons mix a process choice with the specification"),
    ]
    return [{"quantity": q, "v1": a, "v2": b, "effect_on_metrics": e} for q, a, b, e in rows]


def layout_rows(v1: dict, v2: dict, derived: dict) -> list:
    """Table 3 rows: (label, v1 metric, v2 metric, comment)."""
    rows = [
        ("Board outline(s) (mm)", v1.get("board_outlines"), v2.get("board_outlines"), "V2 outlines are design targets until the routed boards are measured"),
        ("Total PCB area (mm2)", v1.get("total_board_area_mm2"), v2.get("total_board_area_mm2"), "area alone proves nothing: V2 must host a 9 mm isolation barrier, films and a heatsink"),
        ("Copper layers", v1.get("copper_layers"), v2.get("copper_layers"), "fewer layers per board in V2 follow from moving the fine-pitch DSP off the heavy-copper board"),
        ("Copper weight (um)", v1.get("copper_um"), v2.get("copper_um"), ""),
        ("Board thickness (mm)", v1.get("board_thickness_mm"), v2.get("board_thickness_mm"), ""),
        ("Cost index (layers x dm2)", derived["v1"].get("cost_index_layer_dm2"), derived["v2"].get("cost_index_layer_dm2"), "fabrication proxy only; V2 adds a mezzanine connector pair and non-plated slots"),
        ("Footprints / schematic items", v1.get("footprints"), v2.get("pcb_footprints") if not is_pending(v2.get("pcb_footprints")) else v2.get("footprints"),
         "V2 counts schematic items until the boards exist; includes test points and mounting holes on both generations"),
        ("Components per dm2", derived["v1"].get("components_per_dm2"), derived["v2"].get("components_per_dm2"), "V2 is 5x the power with isolation parts, so a higher density is expected, not earned"),
        ("Named nets (per board)", v1.get("named_nets"), v2.get("named_nets_per_board"), ""),
        ("Nets per board", derived["v1"].get("nets_per_board"), derived["v2"].get("nets_per_board"), ""),
        ("Tracks", v1.get("tracks"), v2.get("tracks"), ""),
        ("Vias", v1.get("vias"), v2.get("vias"), ""),
        ("HF capacitor to MOSFET pad (mm)", v1.get("hf_capacitor_to_device_mm"), v2.get("hf_capacitor_to_device_mm"), "V2 target 5 mm (row 1) / 15 mm (row 2); straight-line proxy, not loop inductance"),
        ("Driver output to gate pad (mm)", v1.get("driver_to_gate_pin_mm"), v2.get("driver_to_gate_pin_mm"), "V2 target <= 15 mm; V1 range was flagged long in known issue V1-01"),
        ("Switch-node copper (mm2)", v1.get("sw_copper_total_mm2"), v2.get("sw_copper_total_mm2"), "sum over layers; V2 SW carries 400 V at 110 V/ns so a smaller area is required, not optional"),
        ("DSP bypass max pad distance (mm)", v1.get("dsp_bypass_max_mm"), v2.get("dsp_bypass_max_mm"), "V1 maximum 6.86 mm was known issue V1-08"),
        ("Isolation min copper distance (mm)", v1.get("isolation_min_distance_mm"), v2.get("isolation_min_distance_mm"), "no V1 counterpart (48 V board); V2 threshold 9.0 mm on all layers"),
        ("Barrier parts (slots required)", v1.get("barrier_parts"), v2.get("barrier_parts"), ""),
        ("Barrier surface path min (mm)", None, v2.get("barrier_surface_path_min_mm"), "2*sqrt((g/2)^2 + e^2) around the slot ends; required >= 9.0 mm"),
        ("Assembly height used (mm)", v1.get("assembly_height_mm"), v2.get("assembly_height_mm"), "V1: 2.0 mm board + 55 mm inductor; V2: 15 mm standoffs + 2 mm board + 50 mm heatsink"),
        ("Specific power (W/dm2)", derived["v1"].get("specific_power_W_per_dm2"), derived["v2"].get("specific_power_W_per_dm2"), "rated power over summed PCB area"),
        ("Volumetric power (W/L)", derived["v1"].get("volumetric_power_W_per_L"), derived["v2"].get("volumetric_power_W_per_L"), "summed PCB area x assembly height; not an enclosure volume"),
        ("Layout rule rows (within / exceeding)", v1.get("critical_topology_checks"), v2.get("layout_rule_rows"), "V1 checker had no thresholds; V2 rows carry spec thresholds where the design defines one"),
    ]
    return [{"metric": label, "v1": a, "v2": b, "comment": c} for label, a, b, c in rows]


def process_rows(v1: dict, v2: dict) -> dict:
    """Table 2 sub-tables: knowledge utilisation, verification coverage, documentation and tests."""
    def v(m, key):
        return value_of(m.get(key))

    def pair_or_pending(m, *keys, basis="counted"):
        """A 'a / b' cell, or the pending marker when any part is not yet available."""
        for key in keys:
            if is_pending(m.get(key)):
                return m.get(key)
        return pair(*[v(m, key) for key in keys], basis=basis)

    knowledge = [
        ("Knowledge items used (skills/rules/blocks/components/references/project rules)", v1.get("knowledge_items_used"), v2.get("knowledge_items_used"),
         f"V2 totals available: {fmt(v(v2, 'knowledge_items_total'))}" + (f"; {v2['knowledge_items_used'].get('note')}" if dig(v2, 'knowledge_items_used', 'note') else "")),
        ("Applicability classes of citations", v1.get("knowledge_applicability"), v2.get("knowledge_applicability"), "direct / adapted / not-applicable / human-review (plus 'see text' rows cited in markdown only)"),
        ("Logged retrieval queries", v1.get("knowledge_queries"), v2.get("knowledge_queries"), ""),
        ("Citation rows / distinct ids", pair(0, 0, basis="documented"), pair_or_pending(v2, "knowledge_citation_rows", "knowledge_distinct_ids"), "V1 column shows 0: no citations existed"),
        ("Validation status of cited items", None, v2.get("knowledge_validation_status"), "nothing in the knowledge base is simulated or hardware-validated"),
        ("Unknown ids flagged by the trace", None, v2.get("knowledge_unknown_ids"), "aggregate citations and external sources that the trace could not resolve"),
    ]
    verification = [
        ("Research records / verification records", pair(0, 0, basis="documented"), pair_or_pending(v2, "research_records", "verification_records"), "two lenses per area in V2: engineering recompute and source fact-check"),
        ("Verification verdicts", None, v2.get("verification_verdicts"), ""),
        ("Checked items by status", None, v2.get("verification_checked_items"), ""),
        ("Recomputed quantities (agrees / disagrees)", None, v2.get("verification_recomputed"), ""),
        ("Required changes raised / knowledge-misuse items", None, pair_or_pending(v2, "verification_required_changes", "verification_knowledge_misuse"), ""),
        ("Calculation invariants / baseline cross-checks", pair(v(v1, "calculation_invariants"), 0), pair(v(v2, "calculation_invariants"), dig(v(v2, "baseline_crosscheck") or {}, "items")), ""),
        ("Independent review records", v1.get("independent_review_records"), v2.get("independent_review_records"), "V2 PCB-level review (rule review, known issues) not yet available"),
        ("ERC findings (latest run)", v1.get("erc_findings"), v2.get("erc_findings"), ""),
        ("DRC findings (latest run)", v1.get("drc_findings"), v2.get("drc_findings"), ""),
        ("ERC / DRC runs recorded", pair(v(v1, "erc_runs_recorded"), v(v1, "drc_runs_recorded")), pair(v(v2, "erc_runs_recorded"), v(v2, "drc_runs_recorded")), "history of native check runs, not a quality score"),
        ("Verification summary status", v1.get("verification_status"), v2.get("verification_status"), "V2 'failed' means missing PCB-phase artefacts, not failing checks"),
        ("Pipeline smoke (all modules on a disposable board)", metric(None, None, "documented", note="V1 smoke covered KiCad checks and exports only"), v2.get("pipeline_smoke"), ""),
        ("Simulation runs / models / parasitic cases", pair(0, 0, 0, basis="documented"), pair_or_pending(v2, "simulation_runs", "simulation_models", "parasitic_studies", basis="measured"), ""),
        ("Simulation checks passed (steady / event)", None,
         v2.get("simulation_steady_checks") if is_pending(v2.get("simulation_steady_checks")) else
         metric(f"steady {v(v2, 'simulation_steady_checks')}; event {v(v2, 'simulation_event_checks')}", None, "measured"), dig(v2, "simulation_event_checks", "note") or ""),
        ("Simulated output ripple (Vpp)", None, v2.get("simulation_vout_ripple_Vpp"), "limit 2.0 Vpp; range over all runs"),
        ("Simulated load-step excursion (V) / recovery (ms)", None,
         v2.get("simulation_load_step_excursion_V") if is_pending(v2.get("simulation_load_step_excursion_V")) else
         metric(f"{fmt(v(v2, 'simulation_load_step_excursion_V'), kind='range')} V / {fmt(v(v2, 'simulation_recovery_ms'), kind='range')} ms", None, "measured"),
         "ranges over all load events including the 25 A dumps and the deliberately failing single-loop reference case; limits for the 12.5 A step are 10 V / 5 ms"),
        ("Documented open issues (PCB-level register)", v1.get("documented_open_issues"), v2.get("documented_open_issues"), f"V2 design-level open items: {fmt(v(v2, 'open_items_for_human_review'))} in design_decisions.json, {fmt(v(v2, 'calculation_open_items'))} in calculations.json"),
    ]
    documentation = [
        ("Design documents (files / words)", pair(v(v1, "documentation_files"), v(v1, "documentation_words")), pair(v(v2, "documentation_files"), v(v2, "documentation_words")), "V2 includes generated tables; volume is not quality"),
        ("Design report words", v1.get("design_report_words"), v2.get("design_report_words"), ""),
        ("Schematic sheets", v1.get("schematic_sheets"), v2.get("schematic_sheets"), ""),
        ("Automation test modules / functions", pair(v(v1, "test_modules"), v(v1, "test_functions")), pair(v(v2, "test_modules"), v(v2, "test_functions")), "V1 figure from the V1-era module and docs/status.md; V2 counts every module in tests/"),
        ("Export manifest commands / artifacts", pair(v(v1, "export_manifest_commands"), v(v1, "export_manifest_artifacts"), basis="measured"), pair_or_pending(v2, "export_manifest_commands", "export_manifest_artifacts", basis="measured"), ""),
        ("Frozen release", v1.get("release_frozen"), v2.get("release_frozen"), ""),
    ]
    to_rows = lambda rows: [{"metric": label, "v1": a, "v2": b, "comment": c} for label, a, b, c in rows]  # noqa: E731
    return {"knowledge_utilisation": to_rows(knowledge), "verification_coverage": to_rows(verification), "documentation_and_tests": to_rows(documentation)}


def component_thermal_rows(v1: dict, v2: dict) -> dict:
    def v(m, key):
        return value_of(m.get(key))

    def pair_or_pending(m, *keys):
        for key in keys:
            if is_pending(m.get(key)):
                return m.get(key)
        return pair(*[v(m, key) for key in keys])

    components = [
        ("Records / fields per record", pair(v(v1, "component_records"), v(v1, "component_record_fields")), pair_or_pending(v2, "component_records", "component_record_fields"),
         "V1: one row per reference designator; V2: one record per part type"),
        ("Distinct part numbers / manufacturers (BOM)", pair(v(v1, "bom_distinct_mpn"), v(v1, "bom_distinct_manufacturers")), pair(v(v2, "bom_distinct_mpn"), v(v2, "bom_distinct_manufacturers")), ""),
        ("BOM rows (incl. DNP in V2)", v1.get("bom_rows"), v2.get("bom_rows"), f"V2 DNP parts {fmt(v(v2, 'dnp_parts'))}"),
        ("Per-part verification level", v1.get("component_verification_levels"), v2.get("component_verification_levels"), "V2 states fetched-datasheet / manufacturer-page / search-snippet / unverified per record"),
        ("Knowledge references inside component records", metric(0, None, "documented"), v2.get("component_knowledge_refs"), ""),
        ("Open sourcing issues / alternatives recorded", None, pair_or_pending(v2, "component_open_issues", "component_alternatives"), ""),
        ("Custom footprints", v1.get("custom_footprints"), v2.get("custom_footprints"), "V2 isolation parts need slotted custom footprints"),
        ("Magnetic design record", metric(False, None, "documented", note="catalogue 10 uH part"), v2.get("magnetic_record"), "V2 output choke is a custom wound part with a Magnetic Database record"),
    ]
    thermal = [
        ("Thermal document words", v1.get("thermal_document_words"), v2.get("thermal_document_words"), ""),
        ("Loss / temperature corners evaluated", v1.get("thermal_corners"), v2.get("thermal_corners"), ""),
        ("Heatsink", v1.get("thermal_heatsink"), v2.get("thermal_heatsink"), ""),
        ("Interface material", v1.get("thermal_interface"), v2.get("thermal_interface"), ""),
        ("Expected / hottest junction temperature (C)", metric("illustrative 95 C", None, "documented"), pair(v(v2, "thermal_tj_expected_C"), v(v2, "thermal_tj_hottest_C"), basis="documented"),
         f"lumped steady-state arithmetic in both generations; nothing simulated or measured; V2 hottest corner: {dig(v2, 'thermal_tj_hottest_C', 'note') or 'n/a'}"),
        ("Cooling-failure analysis", v1.get("thermal_fan_failure"), v2.get("thermal_fan_failure"), ""),
        ("Temperature sensor to junction mapping", v1.get("thermal_sensor_mapping"), v2.get("thermal_sensor_mapping"), ""),
        ("Efficiency estimate (converter)", v1.get("efficiency_estimate"), v2.get("efficiency_estimate"), f"V2 target/floor {fmt(value_of(v2.get('efficiency_target')))}; V1 sensitivity {fmt(value_of(v1.get('efficiency_sensitivity')))} if loss doubles"),
        ("Total loss estimate (W)", v1.get("total_loss_W"), v2.get("total_loss_W"), "different power levels; compare loss fraction, not watts"),
    ]
    manufacturability = [
        ("Boards x layers x copper", metric(f"1 x {fmt(value_of(v1.get('copper_layers')))} layers, {fmt(value_of(v1.get('copper_um')))} um, {fmt(value_of(v1.get('board_thickness_mm')))} mm", None, "documented"),
         metric(f"power {fmt(dig(value_of(v2.get('copper_layers')) or {}, 'power'))} layers / {fmt(dig(value_of(v2.get('copper_um')) or {}, 'power'))} um / {fmt(dig(value_of(v2.get('board_thickness_mm')) or {}, 'power'))} mm; control {fmt(dig(value_of(v2.get('copper_layers')) or {}, 'control'))} layers / {fmt(dig(value_of(v2.get('copper_um')) or {}, 'control'))} um / {fmt(dig(value_of(v2.get('board_thickness_mm')) or {}, 'control'))} mm",
                None, v2.get("copper_layers", {}).get("basis", "planned") if isinstance(v2.get("copper_layers"), dict) else "planned"),
         "V1 combined heavy copper with an LQFP-176 on one board (known issue V1-09); V2 keeps fine pitch off the heavy-copper board"),
        ("Fine-pitch parts on heavy-copper board", metric("yes (LQFP-176, 0.5 mm pitch on 70 um outer copper)", None, "documented"), metric("no (DSP on the 35 um control board)", None, "planned"), ""),
        ("Non-plated barrier slots", metric(0, None, "documented"), v2.get("barrier_parts"), "slots under isolators where the land gap is below 9 mm"),
        ("Custom footprints", v1.get("custom_footprints"), v2.get("custom_footprints"), ""),
        ("Export manifest (commands / artifacts)", pair(v(v1, "export_manifest_commands"), v(v1, "export_manifest_artifacts"), basis="measured"), v2.get("export_manifests"), ""),
        ("Fabrication notes raised", metric("plated slots, exposed-pad vias, fine pitch with heavy copper (V1-09)", None, "documented"), metric("0.20 mm prepreg between two 70 um layers to confirm; 2.0 mm core stack; slot widths >= 1.0 mm after tolerance", None, "documented"), "from the stack-up documents; fabricator DFM feedback is pending in both generations"),
    ]
    to_rows = lambda rows: [{"metric": label, "v1": a, "v2": b, "comment": c} for label, a, b, c in rows]  # noqa: E731
    return {"component_selection": to_rows(components), "thermal_design": to_rows(thermal), "manufacturability": to_rows(manufacturability)}


def pending_metrics(v2: dict, derived: dict) -> list:
    names = sorted(k for k, item in v2.items() if is_pending(item))
    names += sorted(f"derived.{k}" for k, item in derived["v2"].items() if is_pending(item) or (isinstance(item, dict) and item.get("basis") == "planned"))
    return names


# --- report assembly -----------------------------------------------------------------------------------------

CAVEATS = [
    "Raw PCB area, component density and specific power do not prove that either generation is better engineered: V2 carries 5x the power at 8x the voltage with an isolation barrier that V1 never needed, so most density ratios are specification effects (table 1).",
    "V2 layout, DRC, placement, export and release metrics are produced by a concurrent PCB phase; every such entry is marked 'not yet available' and the script must be re-run to complete the tables.",
    "Counts of files, rows, words, citations, tests and runs measure process coverage, not engineering correctness; a verified-with-corrections record can still contain a wrong number that both lenses missed.",
    "All thermal and efficiency figures of both generations are lumped analytical estimates; the V2 simulation is a behavioural ngspice model without SiC device physics, switching loss or firmware. Nothing in either generation is measured on hardware.",
    "V1 is frozen and read-only; this comparison never alters it, and its known issues remain the authoritative V1 review state.",
]

CAN_SHOW = [
    "whether each workflow step exists in each generation and which file is the evidence (table 2.1);",
    "how much of the knowledge base was retrieved, how it was classified (direct / adapted / not applicable / human review) and how many citations were checked by independent verifiers (tables 2.2 and 2.3);",
    "which automated checks exist and their recorded results (ERC, DRC, layout rules, simulation checks, calculation invariants, tests);",
    "the planned versus measured V2 board geometry once the layout metrics exist, against the V1 measurements already on record (table 3).",
]

CANNOT_SHOW = [
    "that V2 is a better converter: no efficiency, EMI, thermal rise, insulation or control-loop result is measured in either generation;",
    "that fewer layers, smaller area or higher W/dm2 are achievements: they follow from the specification and the two-board split, and V2 must still prove 9 mm clearances, slot creepage and loop inductance on the routed boards;",
    "that more documents, citations or tests mean higher quality; they show traceability and coverage, which the human reviewer still has to judge;",
    "anything about manufacturability beyond the stack-up statements and export manifests: no fabricator DFM review exists for either generation.",
]


def build_report(root: Path = ROOT) -> dict:
    root = Path(root)
    v1 = collect_v1(root / V1_REL, root)
    v2 = collect_v2(root / V2_REL, root)
    derived = derive(v1, v2)
    report = {
        "schema_version": 1,
        "status": STATUS,
        "title": "V1 (48 V -> 24 V / 1 kW Si buck) versus V2 (400 V -> 200 V / 5 kW SiC buck): process, knowledge, verification and layout comparison",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "python -m automation.scripts.compare_v1_v2",
        "definitions": {
            "specific_power_W_per_dm2": "rated output power divided by the summed PCB area of all boards",
            "volumetric_power_W_per_L": "rated output power divided by (summed PCB area x assembly height); V1 height = board 2.0 mm + 55 mm inductor, V2 height = 67 mm documented stack (15 + 2 + 50)",
            "components_per_dm2": "footprints (V1 measured; V2 schematic items until the boards exist) divided by summed PCB area",
            "cost_index_layer_dm2": "sum over boards of copper layers x board area in dm2; relative fabrication proxy, not a quotation",
            "nets_per_board": "named nets divided by board count",
            "basis": "measured = CAD/simulation tool output; counted = counted from repository files; documented = stated in a design document; planned = design target not yet measured; derived = computed here; not yet available = source file missing",
        },
        "generations": {"v1": v1, "v2": v2},
        "derived": derived,
        "tables": {
            "1_specification_driven_differences": specification_table(v1, v2),
            "2_process_metrics": {"workflow_completeness": workflow_status(v1, v2), **process_rows(v1, v2)},
            "3_layout_and_architecture": layout_rows(v1, v2, derived),
            "4_component_selection_thermal_manufacturability": component_thermal_rows(v1, v2),
        },
        "pending_v2_metrics": pending_metrics(v2, derived),
        "caveats": CAVEATS,
        "can_show": CAN_SHOW,
        "cannot_show": CANNOT_SHOW,
    }
    return report


# --- markdown ------------------------------------------------------------------------------------------------

def md_table(headers, rows) -> list:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in row) + " |")
    return lines


def cell(item) -> str:
    if item is None:
        return "-"
    return fmt(item)


def metric_rows(rows, label_key="metric") -> list:
    return [[r[label_key], cell(r["v1"]), cell(r["v2"]), r.get("comment") or ""] for r in rows]


def render_markdown(report: dict) -> str:
    v1, v2 = report["generations"]["v1"], report["generations"]["v2"]
    tables = report["tables"]
    pending_list = report["pending_v2_metrics"]
    lines = [BANNER, "", f"# {report['title']}", "",
             f"Generated {report['generated_utc']} by `{report['generated_by']}`. Machine-readable twin: `v1_v2_comparison.json`. "
             f"V1 sources are the frozen files under `{V1_REL}/` (read-only); V2 sources are under `{V2_REL}/`. "
             f"{len(pending_list)} V2 metrics are marked '{NOT_AVAILABLE}' because the PCB phase is running; re-run the script after placement, routing, DRC, "
             "layout metrics, exports and release exist to complete the tables.", "",
             "## 0. How to read this comparison", ""]
    lines += [f"- {c}" for c in report["caveats"]]
    lines += ["", f"Basis of every value: {report['definitions']['basis']}.", ""]

    lines += ["## 1. Specification-driven differences (explain metric differences; not improvements)", "",
              "These differences are fixed by the task. They change parts, spacing, copper and board count before any process quality enters. "
              "Read every row of tables 3 and 4 against this table first.", ""]
    lines += md_table(["Quantity", "V1", "V2", "Effect on the metrics below (not an improvement)"],
                      [[r["quantity"], r["v1"], r["v2"], r["effect_on_metrics"]] for r in tables["1_specification_driven_differences"]])

    lines += ["", "## 2. Process metrics comparable across generations", "", "### 2.1 Workflow completeness", "",
              "States: done, not done, or not yet available (V2 PCB phase running). Evidence names the repository file that was read.", ""]
    wf = tables["2_process_metrics"]["workflow_completeness"]
    rows = []
    for key, label in WORKFLOW_STEPS:
        step = wf.get(key, {})
        rows.append([label, f"{step.get('v1', {}).get('state', '-')} - {step.get('v1', {}).get('evidence', '')}",
                     f"{step.get('v2', {}).get('state', '-')} - {step.get('v2', {}).get('evidence', '')}"])
    lines += md_table(["Step", "V1", "V2"], rows)
    done = lambda gen: sum(1 for s in wf.values() if s.get(gen, {}).get("state") == "done")  # noqa: E731
    pend = sum(1 for s in wf.values() if s.get("v2", {}).get("state") == NOT_AVAILABLE)
    lines += ["", f"Steps done: V1 {done('v1')}/{len(WORKFLOW_STEPS)}, V2 {done('v2')}/{len(WORKFLOW_STEPS)} with {pend} steps {NOT_AVAILABLE}. "
              "V1 steps marked 'not done' (knowledge retrieval, simulation) were not part of the V1 workflow; this is the genuine process difference between the generations.", ""]

    lines += ["### 2.2 Knowledge utilisation", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(tables["2_process_metrics"]["knowledge_utilisation"]))
    lines += ["", "### 2.3 Verification coverage and open issues", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(tables["2_process_metrics"]["verification_coverage"]))
    lines += ["", "### 2.4 Documentation volume, automation tests and release", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(tables["2_process_metrics"]["documentation_and_tests"]))

    lines += ["", "## 3. Layout and architecture metrics", "",
              "Caveat: these are straight-line board geometries, counts and ratios. They are not loop inductance, current capacity, creepage per standard or EMI performance, "
              "and raw area or density never proves superiority (section 1). V2 values marked 'planned' are design targets from `design_decisions.json`; "
              f"values marked '{NOT_AVAILABLE}' appear after the routed boards are measured by `automation/verification/check_sic_layout.py`.", ""]
    lines += md_table(["Metric", "V1 (measured, frozen)", "V2", "Comment"], metric_rows(tables["3_layout_and_architecture"]))
    d1, d2 = report["derived"]["v1"], report["derived"]["v2"]
    lines += ["", "### 3.1 Density and power density (derived)", "",
              f"Definitions: {report['definitions']['specific_power_W_per_dm2']}; {report['definitions']['volumetric_power_W_per_L']}; "
              f"{report['definitions']['components_per_dm2']}; {report['definitions']['cost_index_layer_dm2']}.", ""]
    lines += md_table(["Derived metric", "V1", "V2", "Reading"], [
        ["Total PCB area (dm2)", cell(d1["total_board_area_dm2"]), cell(d2["total_board_area_dm2"]), "V2 planned total 5.28 dm2 versus V1 6.6 dm2 - a 20 % smaller area at 5x power and 8x voltage is only meaningful once clearances and loops are measured"],
        ["Specific power (W/dm2)", cell(d1["specific_power_W_per_dm2"]), cell(d2["specific_power_W_per_dm2"]), "dominated by the 5x power specification"],
        ["Volume used (L)", cell(d1["volume_L"]), cell(d2["volume_L"]), "summed board area x assembly height"],
        ["Volumetric power (W/L)", cell(d1["volumetric_power_W_per_L"]), cell(d2["volumetric_power_W_per_L"]), "heights 57 mm (V1) and 67 mm (V2) are documented envelopes, not measured assemblies"],
        ["Components per dm2", cell(d1["components_per_dm2"]), cell(d2["components_per_dm2"]), "V2 counts schematic items until the boards exist"],
        ["Nets per board", cell(d1["nets_per_board"]), cell(d2["nets_per_board"]), ""],
        ["Cost index (layer-dm2)", cell(d1["cost_index_layer_dm2"]), cell(d2["cost_index_layer_dm2"]), "V2 adds a mezzanine pair and slots that the index ignores"],
        ["Power per MOSFET (W)", cell(d1["power_per_mosfet_W"]), cell(d2["power_per_mosfet_W"]), "technology effect (SiC 1200 V versus paralleled Si 100 V)"],
        ["BOM rows per kW", cell(d1["bom_rows_per_kW"]), cell(d2["bom_rows_per_kW"]), "isolation parts raise the V2 count while power lowers rows per kW"],
    ])

    comp = tables["4_component_selection_thermal_manufacturability"]
    lines += ["", "## 4. Component selection rationale, thermal design completeness and manufacturability", "", "### 4.1 Component selection rationale", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(comp["component_selection"]))
    lines += ["", "### 4.2 Thermal design completeness", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(comp["thermal_design"]))
    lines += ["", "### 4.3 Manufacturability", ""]
    lines += md_table(["Metric", "V1", "V2", "Comment"], metric_rows(comp["manufacturability"]))

    lines += ["", "## 5. Genuine process improvements versus specification effects", "",
              "Process improvements (independent of the electrical specification): a knowledge system with logged retrieval and classified citations; research records with two independent "
              "verification lenses per decision area; a calculation record with a registered input list, invariants and baseline cross-checks; per-part verification levels in the component records; "
              "an ngspice simulation campaign with analytical cross-checks; a data-driven layout checker with spec thresholds; and an automation test suite an order of magnitude larger.", "",
              "Specification effects (not improvements): higher W/dm2 and W/L, fewer power devices, a shorter commutation cell, film instead of electrolytic capacitors, "
              "isolated drivers and sensing, barrier slots and the mezzanine interconnect. The two-board architecture sits between the two: it was chosen by a scored comparison "
              "(a process step) but its payoff - fine pitch off the heavy-copper board - is only real once both boards are routed and checked.", ""]

    lines += ["## 6. What this comparison can and cannot show", "", "It can show:", ""]
    lines += [f"- {c}" for c in report["can_show"]]
    lines += ["", "It cannot show:", ""]
    lines += [f"- {c}" for c in report["cannot_show"]]
    lines += ["", f"### 6.1 V2 metrics {NOT_AVAILABLE} ({len(pending_list)})", ""]
    lines += [f"- `{name}`" for name in pending_list] or ["- none"]
    lines += ["", "### 6.2 Sources", "",
              f"V1 files read: {len(v1['sources']['read'])}; missing: {len(v1['sources']['missing'])}" + (f" ({', '.join(v1['sources']['missing'])})" if v1['sources']['missing'] else "") + ".",
              f"V2 files read: {len(v2['sources']['read'])}; missing: {len(v2['sources']['missing'])}" + (f" ({', '.join(v2['sources']['missing'])})" if v2['sources']['missing'] else "") + ".", ""]
    return "\n".join(lines)


def write_outputs(report: dict, output_dir: Path) -> tuple:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "v1_v2_comparison.json"
    md_path = output_dir / "v1_v2_comparison.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--output", type=Path, default=None, help=f"output directory (default: <root>/{V2_REL}/review)")
    parser.add_argument("--quiet", action="store_true", help="suppress the Markdown echo")
    args = parser.parse_args(argv)
    report = build_report(args.root)
    output_dir = args.output or (Path(args.root) / V2_REL / "review")
    json_path, md_path = write_outputs(report, output_dir)
    if not args.quiet:
        sys.stdout.write(render_markdown(report) + "\n")
    sys.stdout.write(f"wrote {json_path}\nwrote {md_path}\npending V2 metrics: {len(report['pending_v2_metrics'])}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
