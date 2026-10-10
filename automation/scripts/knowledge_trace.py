"""Aggregate knowledge citations from V2 design research records into a traceable table.

Reads examples/sic-buck-400v-200v-5kw/design/research/*.json written by the design
agents (and verify_*.json written by the verifiers), checks every cited knowledge id
against the Engineering Knowledge System, and writes design/knowledge_trace.json plus a
Markdown table used by review/knowledge_utilisation_report.md. It records what was
retrieved and how it was applied; it does not judge engineering adequacy.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/sic-buck-400v-200v-5kw"
RESEARCH = EXAMPLE / "design/research"
PROJECT_RULES = {f"PE-PCB-{i:03d}" for i in range(1, 9)}
ID_PATTERN = re.compile(r"\b(SKILL-\d{3}|KR-[A-Z]{2,3}-\d{3}|CB-[A-Z]{2}-\d{3}|CMP-[A-Za-z0-9.\-]+|REF-[A-Z]{2}-[A-Z0-9\-]+|PE-PCB-\d{3}|EC-\d{3})\b")


def load_records() -> tuple[dict, dict]:
    """Return (design records by area, verifier records by file stem)."""
    designs, verifications = {}, defaultdict(list)
    for path in sorted(RESEARCH.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            designs[path.stem] = {"error": str(exc)}
            continue
        if path.stem.startswith("verify_"):
            verifications[path.stem].append(data)
        else:
            designs[path.stem] = data
    return designs, dict(verifications)


def trace() -> dict:
    """Build the citation trace and write knowledge_trace.json / knowledge_trace.md."""
    from automation.knowledge.query import KnowledgeBase
    kb = KnowledgeBase.load()
    designs, verifications = load_records()
    rows, unknown, usage = [], [], defaultdict(set)
    for area, data in designs.items():
        if "error" in data:
            rows.append(dict(area=area, error=data["error"]))
            continue
        declared = set()
        for item in data.get("knowledge_used", []):
            item_id = str(item.get("id", "")).strip()
            declared.add(item_id)
            record = kb.get(item_id)
            exists = record is not None or item_id in PROJECT_RULES
            if not exists:
                unknown.append((area, item_id))
            usage[item_id].add(area)
            rows.append(dict(area=area, id=item_id, exists=exists,
                             type=(record or {}).get("type", "project-rule" if item_id in PROJECT_RULES else item.get("type", "unknown")),
                             validation_status=((record or {}).get("record") or {}).get("validation_status"),
                             applicability=item.get("applicability"), how_applied=item.get("how_applied"),
                             reference_design=item.get("reference_design", "")))
        # Ids cited inside the markdown but not declared in knowledge_used are reported too.
        for cited in sorted(set(ID_PATTERN.findall(data.get("markdown", ""))) - declared):
            usage[cited].add(area)
            rows.append(dict(area=area, id=cited, type="cited-in-text-only", applicability="see text",
                             how_applied="cited in markdown without a knowledge_used entry",
                             exists=kb.get(cited) is not None or cited in PROJECT_RULES or cited.startswith("EC-"),
                             validation_status=None, reference_design=""))
    queries = {area: data.get("knowledge_queries", []) for area, data in designs.items() if "error" not in data}
    verdicts = {name: [v.get("verdict") for v in items] for name, items in verifications.items()}
    kinds = dict(skills="skill", rules="rule", blocks="block", components="component", references="reference")
    prefixes = dict(skills="SKILL", rules="KR-", blocks="CB-", components="CMP-", references="REF-", project_rules="PE-PCB")
    coverage = {}
    for key, prefix in prefixes.items():
        used = sorted(i for i in usage if i.startswith(prefix))
        total = len(PROJECT_RULES) if key == "project_rules" else sum(1 for r in kb.records.values() if r["type"] == kinds[key])
        coverage[key] = dict(used=len(used), total=total, ids=used)
    report = dict(areas=sorted(designs), rows=rows, unknown_ids=unknown, queries=queries, verification_verdicts=verdicts,
                  coverage=coverage,
                  by_applicability={a: sum(1 for r in rows if r.get("applicability") == a) for a in ("direct", "adapted", "not-applicable", "human-review")})
    (EXAMPLE / "design/knowledge_trace.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["| Design area | Knowledge id | Type | Status | Applicability | How it was applied |", "|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['area']} | (unreadable record) | | | | {r['error']} |")
            continue
        how = str(r.get("how_applied") or "").replace("|", "/").replace("\n", " ")
        flag = "" if r["exists"] else " (UNKNOWN ID)"
        lines.append(f"| {r['area']} | {r['id']}{flag} | {r['type']} | {r.get('validation_status') or ''} | {r.get('applicability') or ''} | {how} |")
    (EXAMPLE / "design/knowledge_trace.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = trace()
    print(json.dumps(dict(areas=result["areas"], unknown_ids=result["unknown_ids"],
                          coverage={k: f"{v['used']}/{v['total']}" for k, v in result["coverage"].items()},
                          by_applicability=result["by_applicability"]), indent=2))
