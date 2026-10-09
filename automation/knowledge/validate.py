"""Validate the engineering knowledge base.

Usage (repository root):

    python -m automation.knowledge.validate            # human-readable report
    python -m automation.knowledge.validate --json     # machine-readable report

Checks, in order:

1. every record passes its JSON schema (``knowledge/schemas``);
2. identifiers are unique and every cross-reference resolves (evidence sources
   and documents, related skills/blocks/components/rules, existing project
   rules PE-PCB-xxx, evidence-check ids, Markdown documents);
3. traceability: every reference document records an acquisition outcome with
   URL, date, size and SHA-256 (or an explicit failure), and every component
   datasheet marked ``verified-pdf`` was actually downloaded as a PDF;
4. policy: single-reference observations are never hard constraints; status
   ``analytically-checked`` requires at least one cited evidence check and all
   cited checks must have passed; skills contain the required sections;
5. part numbers: each component part number (or orderable variant) appears in
   the cited manufacturer files when the local cache is present; otherwise the
   check is reported as skipped rather than passed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

from automation.knowledge.common import CACHE, KNOWLEDGE, ROOT, load_json, rel
from automation.knowledge.schema_check import Validator

SKILL_SECTIONS = ("Purpose", "Applicable conditions", "Not applicable", "Engineering principles",
                  "Design procedure", "Component selection considerations", "PCB constraints",
                  "Verification methods", "Known limitations", "Source references")
STATUS_ORDER = ["reference-derived", "analytically-checked", "simulation-verified", "hardware-validated"]


def records(root: Path = KNOWLEDGE) -> dict[str, list[tuple[Path, dict]]]:
    def load(paths: Iterable[Path]) -> list[tuple[Path, dict]]:
        return [(p, load_json(p)) for p in sorted(paths)]
    return {
        "reference": load(root.glob("references/*/*/reference.json")),
        "skill": load(root.glob("skills/*/SKILL-*.json")),
        "block": load(root.glob("circuit_blocks/*/CB-*.json")),
        "component": load(root.glob("components/*/CMP-*.json")),
        "rules": load([root / "rules" / "engineering_rules.json"]),
    }


SCHEMA_FOR = {"reference": "reference.schema.json", "skill": "skill.schema.json",
              "block": "circuit_block.schema.json", "component": "component.schema.json",
              "rules": "engineering_rules.schema.json"}


def project_rule_ids() -> set[str]:
    text = (ROOT / "docs" / "pcb-design-rules.md").read_text(encoding="utf-8")
    return set(re.findall(r"PE-PCB-\d{3}", text))


def walk_evidence(node, path="$"):
    """Yield (json path, evidence dict) for every evidence-shaped object."""
    if isinstance(node, dict):
        if {"source", "location", "kind"} <= node.keys():
            yield path, node
        for key, value in node.items():
            yield from walk_evidence(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_evidence(value, f"{path}[{index}]")


def walk_related(node, path="$"):
    if isinstance(node, dict):
        if "related" in node and isinstance(node["related"], dict):
            yield path + ".related", node["related"]
        for key, value in node.items():
            if key != "related":
                yield from walk_related(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_related(value, f"{path}[{index}]")


def normalise(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def cached_text(reference_id: str, cache: Path = CACHE) -> str | None:
    """All extracted text/CSV/netlist content for a reference, normalised."""
    base = cache / reference_id
    if not base.exists():
        return None
    chunks = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".txt", ".csv", ".dat"}:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return normalise("\n".join(chunks)) if chunks else None


def validate(root: Path = KNOWLEDGE, cache: Path = CACHE) -> dict:
    """Validate the knowledge base under ``root``; ``cache`` holds raw source files."""
    errors: list[str] = []
    warnings: list[str] = []
    info: dict = {}
    data = records(root)
    validator = Validator(root / "schemas")

    # 1. schemas -----------------------------------------------------------
    for kind, items in data.items():
        for path, record in items:
            for problem in validator.validate(record, SCHEMA_FOR[kind]):
                errors.append(f"schema {rel(path)}: {problem}")

    references = {r["id"]: (p, r) for p, r in data["reference"]}
    documents = {rid: {d["id"] for d in r["documents"]} for rid, (_, r) in references.items()}
    skills = {r["id"]: p for p, r in data["skill"]}
    blocks = {r["id"]: p for p, r in data["block"]}
    components = {r["id"]: p for p, r in data["component"]}
    rules_doc = data["rules"][0][1] if data["rules"] else {"rules": []}
    rules = {r["id"]: r for r in rules_doc.get("rules", [])}
    checks_path = root / "verification" / "evidence-checks.json"
    checks = {c["id"]: c for c in load_json(checks_path)["checks"]} if checks_path.exists() else {}
    project_rules = project_rule_ids()
    info["counts"] = {"references": len(references), "skills": len(skills), "blocks": len(blocks),
                      "components": len(components), "rules": len(rules), "evidence_checks": len(checks)}

    # 2. identifiers and cross-references ----------------------------------
    for kind, ids in (("skill", [r["id"] for _, r in data["skill"]]), ("block", [r["id"] for _, r in data["block"]]),
                      ("component", [r["id"] for _, r in data["component"]]), ("rule", [r["id"] for r in rules_doc.get("rules", [])])):
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            errors.append(f"duplicate {kind} ids: {sorted(duplicates)}")
    for path, record in data["component"]:
        if path.stem != record["id"] or path.parent.name != record["category"]:
            errors.append(f"{rel(path)}: file name/folder must match id and category")
    for path, record in data["block"]:
        if path.stem != record["id"]:
            errors.append(f"{rel(path)}: file name must match id")

    known = {"skills": skills, "blocks": blocks, "components": components, "rules": rules}
    for kind, items in data.items():
        for path, record in items:
            for where, evidence in walk_evidence(record):
                source = evidence["source"]
                if source not in references:
                    errors.append(f"{rel(path)} {where}: unknown evidence source {source}")
                elif "document" in evidence and evidence["document"] not in documents[source]:
                    errors.append(f"{rel(path)} {where}: document {evidence['document']} not in {source}")
                if "check" in evidence:
                    check = checks.get(evidence["check"])
                    if check is None:
                        errors.append(f"{rel(path)} {where}: unknown evidence check {evidence['check']}")
                    elif check["reference"] != source:
                        errors.append(f"{rel(path)} {where}: check {evidence['check']} belongs to {check['reference']}")
            for where, related in walk_related(record):
                for key, ids in related.items():
                    for item in ids:
                        if key == "project_rules":
                            if item not in project_rules:
                                errors.append(f"{rel(path)} {where}: unknown project rule {item}")
                        elif item not in known[key]:
                            errors.append(f"{rel(path)} {where}: unknown {key[:-1]} {item}")
    for path, record in data["block"]:
        for calc in record["design_calculations"]:
            if "check" in calc and calc["check"] not in checks:
                errors.append(f"{rel(path)}: unknown calculation check {calc['check']}")
        for item in record["required_components"]:
            if "component" in item and item["component"] not in components:
                errors.append(f"{rel(path)}: unknown component {item['component']}")
    for path, record in data["reference"]:
        if not (path.parent / record["analysis"]).exists():
            errors.append(f"{rel(path)}: analysis document {record['analysis']} missing")
        if not (path.parent / "inventory.json").exists():
            warnings.append(f"{rel(path)}: no inventory.json (run inspect_sources)")

    # 3. traceability -------------------------------------------------------
    for path, record in data["reference"]:
        for document in record["documents"]:
            acquisition = document["acquisition"]
            label = f"{record['id']}/{document['id']}"
            if acquisition["status"] == "downloaded":
                missing = [k for k in ("retrieved", "bytes", "sha256", "cache_path") if k not in acquisition]
                if missing:
                    errors.append(f"{label}: downloaded but missing {missing}")
            elif acquisition["status"] == "failed":
                if not acquisition.get("error"):
                    errors.append(f"{label}: failed acquisition without error text")
                warnings.append(f"{label}: acquisition failed ({acquisition.get('error')})")
            else:
                errors.append(f"{label}: acquisition not attempted")
            if document["extraction"]["status"] == "not-inspected":
                warnings.append(f"{label}: not inspected")
    for path, record in data["component"]:
        sheet = record["datasheet"]
        status = sheet.get("acquisition", {}).get("status", "not-attempted")
        if sheet["url_status"] == "verified-pdf" and status != "downloaded":
            errors.append(f"{rel(path)}: datasheet marked verified-pdf but acquisition is {status}")
        if sheet["url_status"] == "not-located" and sheet["url"] is not None:
            errors.append(f"{rel(path)}: not-located datasheet must have url null")
        if sheet["url_status"] != "not-located" and not sheet["url"]:
            errors.append(f"{rel(path)}: {sheet['url_status']} datasheet needs a url")

    # 4. policy -------------------------------------------------------------
    for rule in rules.values():
        sources = {e["source"] for e in rule["evidence"]}
        if rule["category"] == "hard-constraint" and rule["generality"] == "single-reference-observation":
            errors.append(f"{rule['id']}: a single-reference observation cannot be a hard constraint")
        if rule["generality"] == "multi-source-consistent" and len(sources) < 2:
            errors.append(f"{rule['id']}: multi-source-consistent needs evidence from at least two references")
        if rule["category"] == "hard-constraint" and rule.get("numerical_limits") is not None:
            for limit in rule["numerical_limits"]:
                if limit["basis_type"] == "reference-design-instance":
                    errors.append(f"{rule['id']}: hard-constraint limit '{limit['parameter']}' rests on a design instance")
    status_items = ([(rel(p), r) for p, r in data["skill"]] + [(rel(p), r) for p, r in data["block"]]
                    + [(f"rule {r['id']}", r) for r in rules.values()])
    for label, record in status_items:
        cited = {e["check"] for _, e in walk_evidence(record) if "check" in e}
        cited |= {c["check"] for c in record.get("design_calculations", []) if "check" in c}
        if record["validation_status"] == "analytically-checked":
            if not cited:
                errors.append(f"{label}: analytically-checked without any cited evidence check")
            bad = [c for c in cited if checks.get(c, {}).get("status") not in ("pass", "computed")]
            if bad:
                errors.append(f"{label}: analytically-checked but checks not passing: {sorted(bad)}")
        if STATUS_ORDER.index(record["validation_status"]) > 1:
            errors.append(f"{label}: {record['validation_status']} claimed but V0 contains no simulation or hardware evidence")
    for path, record in data["skill"]:
        document = path.parent / record["document"]
        if not document.exists():
            errors.append(f"{rel(path)}: skill document missing")
            continue
        headings = re.findall(r"^## (.+)$", document.read_text(encoding="utf-8"), re.M)
        for section in SKILL_SECTIONS:
            if not any(h.startswith(section) for h in headings):
                errors.append(f"{rel(document)}: missing section '{section}'")
        if record["validation_status"] not in document.read_text(encoding="utf-8").split("\n", 3)[2]:
            warnings.append(f"{rel(document)}: status line does not mention {record['validation_status']}")

    # 5. part numbers in manufacturer files ----------------------------------
    part_checks = {"confirmed": [], "not_found": [], "skipped": []}
    text_cache: dict[str, str | None] = {}
    for path, record in data["component"]:
        candidates = [record["part_number"], *record.get("orderable_variants", [])]
        found = False
        cache_seen = False
        for usage in record["reference_usage"]:
            ref = usage["reference"]
            if ref not in text_cache:
                text_cache[ref] = cached_text(ref, cache)
            text = text_cache[ref]
            if text is None:
                continue
            cache_seen = True
            if any(normalise(c) in text for c in candidates):
                found = True
        if found:
            part_checks["confirmed"].append(record["id"])
        elif cache_seen:
            part_checks["not_found"].append(record["id"])
            errors.append(f"{rel(path)}: none of {candidates} found in cited manufacturer files")
        else:
            part_checks["skipped"].append(record["id"])
    info["part_numbers"] = {k: len(v) for k, v in part_checks.items()}
    info["part_numbers_skipped"] = part_checks["skipped"]
    if part_checks["skipped"]:
        warnings.append(f"part-number check skipped for {len(part_checks['skipped'])} components (reference cache absent)")
    return {"errors": errors, "warnings": warnings, "info": info, "ok": not errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = validate()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("counts:", report["info"]["counts"])
        print("part numbers:", report["info"]["part_numbers"])
        for warning in report["warnings"]:
            print("WARNING", warning)
        for error in report["errors"]:
            print("ERROR", error)
        print("RESULT:", "PASS" if report["ok"] else f"FAIL ({len(report['errors'])} errors)")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
