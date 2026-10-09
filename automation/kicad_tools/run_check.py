"""Run real KiCad ERC/DRC; preserve failures and separate every run's evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from automation.setup.detect_kicad import find_kicad_cli


def run_check(kind: str, source: Path, output_root: Path,
              cli: Path | None = None) -> tuple[int, Path]:
    if kind not in ("erc", "drc"):
        raise ValueError(f"Unsupported check: {kind}")
    source = source.resolve(strict=True)
    cli = cli or find_kicad_cli()
    if not cli:
        raise FileNotFoundError("KiCad CLI is unavailable; installation requires user confirmation.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_root.resolve() / f"{stamp}-{kind}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    report = output / f"{kind}.json"
    command = [str(cli), "sch" if kind == "erc" else "pcb", kind,
               "--format", "json", "--severity-all", "--exit-code-violations",
               "--output", str(report)]
    if kind == "drc":
        command.extend(["--schematic-parity", "--refill-zones"])
    command.append(str(source))
    manifest = {"command": command, "source": str(source), "status": "failed",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "tool_exit_code": None, "wrapper_exit_code": 2, "report": str(report)}
    # Hierarchical schematics, rules and project libraries also affect results.
    # Record their bytes, rather than accepting an unchanged root sheet as proof.
    suffixes={'.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym','.kicad_mod'}
    dependencies=sorted(p for p in source.parent.rglob('*') if p.is_file() and
                        (p.suffix in suffixes or p.name in ('sym-lib-table','fp-lib-table')))
    manifest['dependency_sha256']={p.relative_to(source.parent).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=180)
        (output / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (output / "stderr.log").write_text(result.stderr, encoding="utf-8")
        manifest["tool_exit_code"] = result.returncode
        # Never let an old report from an earlier invocation establish success.
        report_data = json.loads(report.read_text(encoding="utf-8-sig"))
        if not isinstance(report_data, dict) or not report_data:
            raise ValueError("KiCad produced an empty or invalid JSON report")
        if report_data.get("$schema") != f"https://schemas.kicad.org/{kind}.v1.json":
            raise ValueError("Unexpected KiCad report schema; manual inspection required")
        if kind == "erc":
            sheets = report_data.get("sheets")
            if not isinstance(sheets, list) or not sheets:
                raise ValueError("ERC report has no sheets")
            groups = [sheet["violations"] for sheet in sheets]
        else:
            groups = [report_data[key] for key in ("violations", "unconnected_items", "schematic_parity")]
        if not all(isinstance(group, list) for group in groups):
            raise ValueError("Malformed violation lists")
        manifest["finding_count"] = sum(len(group) for group in groups)
        manifest["wrapper_exit_code"] = result.returncode or (5 if manifest["finding_count"] else 0)
        manifest["status"] = "passed" if manifest["wrapper_exit_code"] == 0 else "failed"
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        manifest["error"] = str(exc)
    manifest_path = output / "run.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["wrapper_exit_code"], manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("erc", "drc"))
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".aipe/checks"))
    args = parser.parse_args()
    try:
        code, manifest = run_check(args.kind, args.source, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Unable to run KiCad check: {exc}\n")
    print(manifest)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
