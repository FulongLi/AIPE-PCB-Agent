"""Fill the result sections of docs/dab-10kw/review-report.md from the per-board verification summaries.

Reads verification/summary_<board>.json, the ERC/DRC manifests and reports they point to, the export manifests, the
routing reports and the design records, and replaces the RESULTS-* placeholders of the report with Markdown tables.
Numbers are copied from the evidence files, never typed; the files are hashed in the evidence index.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from automation.dab_v1 import requirements as rq

REPORT = rq.ROOT / 'docs/dab-10kw/review-report.md'


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rel(path) -> str:
    return str(Path(path).resolve().relative_to(rq.ROOT)).replace('\\', '/')


def drc_breakdown(summary: dict) -> tuple[str, list]:
    drc = summary.get('drc') or {}
    counts = drc.get('finding_counts') or {}
    by_type = drc.get('by_type') or {}
    parts = [f"{k.split(':')[1]} ({k.split(':')[2]}) x{v}" for k, v in sorted(by_type.items())]
    return (f"violations {counts.get('violations', '?')}, unconnected {counts.get('unconnected_items', '?')}, parity {counts.get('schematic_parity', '?')}"
            + (f"; {', '.join(parts)}" if parts else ''), [c['key'] for c in drc.get('ignored_checks', [])])


def generated_table(req) -> list[str]:
    rows = ['| Board | Project | Size / stack | Parts (model) | Sheets | Nets | Net classes | DRU rules | Package relaxations |', '|---|---|---|---|---|---|---|---|---|']
    for board in rq.BOARDS:
        cfg = req.board(board)
        parts = read(rq.DESIGN / f'circuit_{board}.json')
        sch = read(rq.DESIGN / f'schematic_summary_{board}.json')
        spacing = read(rq.DESIGN / f'spacing_{board}.json')
        pro = read(rq.EXAMPLE / board / f'{cfg["name"]}.kicad_pro')
        dru = (rq.EXAMPLE / board / f'{cfg["name"]}.kicad_dru').read_text(encoding='utf-8')
        nets = len({n for p in parts for n in p['nets'].values() if n})
        stack = f"{cfg['size_mm'][0]} x {cfg['size_mm'][1]} mm, {cfg['layers']} layers, {cfg['copper_um'][0]} um, {cfg['thickness_mm']} mm"
        rows.append(f"| {board} | `{cfg['name']}` | {stack} | {len(parts)} | {len(sch['sheets'])} | {nets} | {len(pro['net_settings']['classes'])} | "
                    f"{dru.count('(rule ')} | {len(spacing.get('relaxations', []))} |")
    return rows


def erc_drc_table(req, summaries: dict) -> list[str]:
    rows = ['| Board | ERC (`sch erc --severity-all`) | DRC (`pcb drc --schematic-parity --severity-all --refill-zones`) | Checks ignored by KiCad (default, not disabled here) | Router result |', '|---|---|---|---|---|']
    for board in rq.BOARDS:
        s = summaries.get(board)
        if not s:
            rows.append(f'| {board} | not run | not run | - | - |')
            continue
        erc = s.get('erc') or {}
        text, ignored = drc_breakdown(s)
        routing = s.get('routing') or {}
        route = (f"{routing.get('tracks')} tracks, {routing.get('vias')} vias, {routing.get('zones')} zones, {routing.get('unresolved')} unresolved connections, "
                 f"{routing.get('seconds')} s") if routing else '-'
        rows.append(f"| {board} | {erc.get('finding_count', '?')} findings (`{Path(erc.get('manifest', '')).parent.name}`) | {text} (`{Path(s.get('drc', {}).get('manifest', '')).parent.name}`) | "
                    f"{', '.join(ignored) if ignored else '-'} | {route} |")
    return rows


def export_table(summaries: dict) -> list[str]:
    rows = ['| Board | Status | Commands (exit codes) | Artifacts | Manifest |', '|---|---|---|---|---|']
    for board in rq.BOARDS:
        s = summaries.get(board)
        e = (s or {}).get('export') or {}
        if not e:
            rows.append(f'| {board} | not run | - | - | - |')
            continue
        cmds = ', '.join(f'{n}={c}' for n, c in e.get('commands', []))
        rows.append(f"| {board} | {e.get('status')} | {cmds} | {e.get('artifacts')} | `{e.get('manifest')}` |")
    return rows


def remaining(summaries: dict) -> list[str]:
    lines = []
    for board in rq.BOARDS:
        s = summaries.get(board)
        if not s:
            lines.append(f'- **{board}**: pipeline not completed; no routed-board evidence.')
            continue
        drc = s.get('drc') or {}
        counts = drc.get('finding_counts') or {}
        routing = s.get('routing') or {}
        netlist = s.get('netlist') or {}
        islands = s.get('copper_islands') or {}
        quality = (s.get('routing_quality') or {}).get('board_totals') or (s.get('routing_quality') or {}).get('summary') or {}
        layout = (s.get('layout_metrics') or {}).get('summary') or {}
        items = []
        if counts.get('violations'):
            items.append(f"{counts['violations']} DRC violations remain ({', '.join(k.split(':')[1] + ' x' + str(v) for k, v in (drc.get('by_type') or {}).items() if k.startswith('violations'))})")
        if counts.get('unconnected_items'):
            nets = drc.get('unconnected_nets') or {}
            items.append(f"{counts['unconnected_items']} unconnected items remain in {len(nets)} nets (router: {routing.get('unresolved', 'n/a')} open connections); "
                         f"unrouted or partly routed nets: {', '.join(f'{n} ({c})' for n, c in list(nets.items())[:60])}{' ...' if len(nets) > 60 else ''}")
        if counts.get('schematic_parity'):
            items.append(f"{counts['schematic_parity']} schematic-parity differences")
        if not items:
            items.append('native DRC reports 0 violations, 0 unconnected items and 0 parity differences under the recorded rule set')
        items.append(f"model/schematic/board pad-net equality: {'exact' if netlist.get('passed') else 'NOT exact or not run'}"
                     + (f" (schematic mismatches {netlist.get('schematic_mismatches')}, board mismatches {netlist.get('board_mismatches')})" if netlist else ''))
        if islands:
            items.append(f"filled-copper islands per power net: {islands.get('components')} ({'all single' if islands.get('passed') else 'split nets or not analysed'})")
        if quality:
            items.append(f"routing geometry: {quality}")
        if layout:
            items.append(f"layout-metric rows: {layout.get('within_threshold')} within, {layout.get('exceeding_threshold')} exceeding, {layout.get('measured_only')} measured only, "
                         f"{layout.get('not_measured')} not measured (thresholds are the unverified design targets; geometry only)")
        lines.append(f'- **{board}**: ' + '; '.join(items) + '.')
    lines.append('- The router report is a geometric proposal; every remaining DRC item above is a real finding of the generated copper and must be '
                 'resolved or dispositioned by a human before any fabrication decision. Routing quality metrics are geometry, not inductance or EMI.')
    return lines


def evidence_index(summaries: dict) -> list[str]:
    rows = ['| Board | Evidence file | SHA-256 |', '|---|---|---|']
    for board in rq.BOARDS:
        s = summaries.get(board)
        if not s:
            continue
        files = [rq.VERIFICATION / f'summary_{board}.json']
        for key in ('erc', 'drc'):
            if (s.get(key) or {}).get('manifest'):
                files.append(rq.ROOT / s[key]['manifest'])
        if (s.get('export') or {}).get('manifest'):
            files.append(rq.ROOT / s['export']['manifest'])
        for key in ('netlist', 'routing_quality', 'layout_metrics', 'copper_islands', 'routing'):
            f = (s.get(key) or {}).get('file')
            if f:
                files.append(rq.ROOT / f)
        for f in files:
            if Path(f).exists():
                rows.append(f'| {board} | `{rel(f)}` | `{sha(f)[:16]}...` |')
    rows.append(f'| all | `examples/dab-10kw/requirements/source_manifest.json` | `{sha(rq.REQUIREMENTS / "source_manifest.json")[:16]}...` |')
    return rows


def build(req) -> str:
    summaries = {}
    for board in rq.BOARDS:
        path = rq.VERIFICATION / f'summary_{board}.json'
        if path.exists():
            summaries[board] = read(path)
    text = REPORT.read_text(encoding='utf-8')
    sections = {
        'RESULTS-TABLE-GENERATED': '\n'.join(generated_table(req)),
        'RESULTS-ERC-DRC': '\n'.join(erc_drc_table(req, summaries)),
        'RESULTS-EXPORTS': '\n'.join(export_table(summaries)),
        'RESULTS-REMAINING': '\n'.join(remaining(summaries)),
        'RESULTS-EVIDENCE': '\n'.join(evidence_index(summaries)),
    }
    for key, value in sections.items():
        marker = f'<!-- {key} -->'
        if marker in text:
            start = text.index(marker)
            end = text.index(f'<!-- /{key} -->', start) + len(f'<!-- /{key} -->')
            text = text[:start] + f'{marker}\n{value}\n<!-- /{key} -->' + text[end:]
        else:
            text = text.replace(key, f'{marker}\n{value}\n<!-- /{key} -->')
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true', help='only print the rendered sections')
    args = parser.parse_args(argv)
    text = build(rq.load())
    if args.check:
        print(text[:4000])
    else:
        REPORT.write_text(text, encoding='utf-8', newline='\n')
        print(f'updated {REPORT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
