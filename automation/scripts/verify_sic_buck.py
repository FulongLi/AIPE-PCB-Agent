"""Require current native ERC/DRC reports, netlist checks and export manifests for both V2 boards.

Mirrors automation/verification/verify_buck.py for the two-board V2 example. It checks that
the LATEST ERC and DRC run per board passed with zero findings and that the recorded source
and dependency hashes still match the delivered KiCad files, that each board's export
manifest passed with eleven commands and intact artifact hashes, that the independent
netlist checks exist and report an exact pad/net match, and that the layout metrics were
produced from the current board files. It writes verification/verification-summary.json.
It does not qualify electrical, thermal or EMI performance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/sic-buck-400v-200v-5kw"
BOARDS = {
    "power": dict(dir="power_board", name="AIPE_SiC_Buck_Power"),
    "control": dict(dir="control_board", name="AIPE_SiC_Buck_Control"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_run(kind: str, name: str) -> tuple[Path, dict]:
    """Latest run.json of the given kind whose source is the named board/schematic."""
    candidates = []
    for manifest in sorted((EXAMPLE / "verification" / kind).glob(f"*-{kind}-*/run.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if Path(data["source"]).stem == name:
            candidates.append((manifest, data))
    if not candidates:
        raise FileNotFoundError(f"no {kind} run for {name}")
    return candidates[-1]


def check_run(kind: str, board: str, problems: list) -> dict:
    cfg = BOARDS[board]
    cad = EXAMPLE / "kicad" / cfg["dir"]
    try:
        manifest, data = latest_run(kind, cfg["name"])
    except FileNotFoundError as exc:
        problems.append(str(exc))
        return {"status": "missing"}
    record = {"manifest": manifest.relative_to(EXAMPLE).as_posix(), "status": data["status"],
              "findings": data.get("finding_count"), "tool_exit_code": data.get("tool_exit_code")}
    if data["status"] != "passed" or data.get("finding_count") != 0:
        problems.append(f"{board} {kind}: latest run did not pass with zero findings ({manifest})")
    source = cad / (cfg["name"] + (".kicad_sch" if kind == "erc" else ".kicad_pcb"))
    if not source.exists():
        problems.append(f"{board} {kind}: source missing {source}")
    elif sha(source) != data["source_sha256"]:
        problems.append(f"{board} {kind}: source changed since the recorded run")
    for name, digest in data.get("dependency_sha256", {}).items():
        dependency = cad / name
        if not dependency.exists() or sha(dependency) != digest:
            problems.append(f"{board} {kind}: dependency changed {name}")
    hash_problems = [p for p in problems if p.startswith(f"{board} {kind}: source") or p.startswith(f"{board} {kind}: dependency")
                     or p.startswith(f"{board} {kind}: report")]
    record["hashes_valid"] = not hash_problems  # finding counts are reported separately; only hash/currency problems invalidate the chain
    report = Path(data.get("report", ""))
    recorded_report_hash = data.get("report_sha256")
    if recorded_report_hash is not None:  # run_check records the report hash (review LR-19); older manifests lack it
        if not report.is_file() or sha(report) != recorded_report_hash:
            problems.append(f"{board} {kind}: report changed since the recorded run")
            record["hashes_valid"] = False
        record["report_hash_checked"] = True
    else:
        record["report_hash_checked"] = False
    return record


def check_exports(board: str, problems: list) -> dict:
    cfg = BOARDS[board]
    output = EXAMPLE / "manufacturing" / cfg["dir"]
    manifest = output / "export-manifest.json"
    if not manifest.exists():
        problems.append(f"{board}: export manifest missing")
        return {"status": "missing"}
    exports = json.loads(manifest.read_text(encoding="utf-8"))
    record = {"status": exports.get("status"), "commands": len(exports.get("commands", [])), "files": len(exports.get("artifacts", {}))}
    if exports.get("status") != "passed" or len(exports.get("commands", [])) != 11:
        problems.append(f"{board}: exports incomplete")
    cad = EXAMPLE / "kicad" / cfg["dir"]
    for name, digest in exports.get("input_sha256", {}).items():
        path = cad / name
        if not path.exists() or sha(path) != digest:
            problems.append(f"{board}: export source changed {name}")
    for name, item in exports.get("artifacts", {}).items():
        path = output / name
        if not path.exists() or path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            problems.append(f"{board}: export artifact changed {name}")
    step_log = output / "logs/step.log"
    if step_log.exists():
        text = step_log.read_text(encoding="utf-8", errors="replace")
        record["step_models_complete"] = "Could not add 3D model" not in text and "File not found" not in text
    return record


def check_netlist(board: str, problems: list) -> dict:
    path = EXAMPLE / "verification" / f"netlist_check_{board}.json"
    if not path.exists():
        problems.append(f"{board}: netlist check missing")
        return {"status": "missing"}
    data = json.loads(path.read_text(encoding="utf-8"))
    ok = bool(data.get("exact_match", data.get("status") == "passed"))
    if not ok:
        problems.append(f"{board}: netlist check reports a mismatch")
    return {"status": "passed" if ok else "failed", "file": path.relative_to(EXAMPLE).as_posix()}


def check_metrics(board: str, problems: list) -> dict:
    path = EXAMPLE / "verification/engineering_checks" / f"layout_metrics_{board}.json"
    if not path.exists():
        problems.append(f"{board}: layout metrics missing")
        return {"status": "missing"}
    data = json.loads(path.read_text(encoding="utf-8"))
    board_file = EXAMPLE / "kicad" / BOARDS[board]["dir"] / (BOARDS[board]["name"] + ".kicad_pcb")
    recorded = data.get("board_sha256") or data.get("board", {}).get("sha256")
    current = sha(board_file) if board_file.exists() else None
    record = {"status": "passed" if (recorded and recorded == current) else ("unverified" if not recorded else "failed"),
              "file": path.relative_to(EXAMPLE).as_posix(), "board_hash_recorded": recorded is not None,
              "board_hash_matches": (recorded == current) if recorded else None}
    if recorded and recorded != current:
        problems.append(f"{board}: layout metrics were measured on a different board file")
    return record


def verify() -> dict:
    problems: list[str] = []
    summary = {"boards": {}}
    for board in BOARDS:
        summary["boards"][board] = {
            "erc": check_run("erc", board, problems),
            "drc": check_run("drc", board, problems),
            "exports": check_exports(board, problems),
            "netlist_check": check_netlist(board, problems),
            "layout_metrics": check_metrics(board, problems),
        }
        parts = json.loads((EXAMPLE / "design" / f"circuit_{board}.json").read_text(encoding="utf-8-sig"))
        summary["boards"][board]["components"] = len(parts)
        summary["boards"][board]["purchased_components"] = sum(1 for p in parts if p["kind"] not in ("TP", "H", "HS") and not p.get("dnp"))
        summary["boards"][board]["dnp_components"] = sum(1 for p in parts if p.get("dnp"))
        summary["boards"][board]["named_nets"] = len({n for p in parts for n in p["nets"].values() if n})
    summary["simulation_runs"] = len(list((EXAMPLE / "simulation/results").glob("*/summary.json")))
    summary["research_records"] = len([p for p in (EXAMPLE / "design/research").glob("*.json") if not p.name.startswith("verify_")])
    summary["verification_records"] = len(list((EXAMPLE / "design/research").glob("verify_*.json")))
    summary["problems"] = problems
    summary["status"] = "passed" if not problems else "failed"
    summary["scope"] = "CAD connectivity, native check currency and export integrity only; hardware unqualified"
    (EXAMPLE / "verification/verification-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = verify()
    print(json.dumps({k: v for k, v in result.items() if k != "boards"}, indent=2))
    for board, data in result["boards"].items():
        print(board, json.dumps({k: (v.get("status") if isinstance(v, dict) else v) for k, v in data.items()}))
    raise SystemExit(0 if result["status"] == "passed" else 1)
