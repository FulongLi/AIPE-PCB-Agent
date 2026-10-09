"""Retrieve engineering knowledge for an agent question (standard library only).

Usage (repository root):

    python -m automation.knowledge.query "recommended layout practices for an isolated SiC gate driver"
    python -m automation.knowledge.query "DC-link capacitor selection" --type rule --json
    python -m automation.knowledge.query --get KR-CAP-001
    python -m automation.knowledge.query --demo          # rewrite knowledge/examples/retrieval-demo.md

Python API (intended for the future AIPE Orchestrator)::

    from automation.knowledge.query import KnowledgeBase
    kb = KnowledgeBase.load()
    hits = kb.search("current sensing for a high-voltage converter", types={"block"}, limit=5)
    record = kb.get("CB-SN-003")

Ranking is Okapi BM25 over chunks (skill sections, rule/block/component
fields, reference-analysis decisions) with a small power-electronics synonym
table. Each hit returns its id, type, validation status, file path and source
references so an agent can cite evidence instead of paraphrasing it.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from automation.knowledge.common import KNOWLEDGE, ROOT, load_json, rel

STOPWORDS = set("""a an and are as at be by can do does for from how in is it of on or should the to what when
which with be into this that these those there their them they we you your our its was were will would could
also than then using use used via per any all each other available considered recommended practices""".split())

# Compound phrases are replaced by one token so that context words such as the
# "voltage" in "high-voltage converter" do not match voltage-sensing items.
COMPOUNDS = {
    "silicon carbide": "sic", "high-voltage": "highvoltage", "high voltage": "highvoltage",
    "dc-link": "dclink", "dc link": "dclink", "gate-driver": "gate driver", "gate drive ": "gate driver ",
    "heat-sink": "heatsink", "heat sink": "heatsink", "short-circuit": "shortcircuit", "short circuit": "shortcircuit",
    "delta-sigma": "deltasigma", "kelvin-source": "kelvin", "kelvin source": "kelvin",
    "current-sensing": "current sensing", "current sense ": "current sensing ", "turn-off": "turnoff", "turn-on": "turnon",
}
# Expansions add related vocabulary without removing the original words.
EXPANSIONS = {
    "pcb": "layout", "routing": "layout", "placement": "layout", "layout": "pcb routing placement",
    "creepage": "isolation", "clearance": "isolation", "desaturation": "desat overcurrent",
    "shortcircuit": "desat overcurrent", "shunt": "current", "hall": "current", "bulk capacitor": "dclink",
    "bus capacitor": "dclink", "bias supply": "isolated supply", "isolated amplifier": "sensing",
}
TYPE_WEIGHT = {"skill": 1.0, "rule": 1.0, "block": 1.0, "component": 0.9, "reference": 0.7}


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    for phrase, replacement in COMPOUNDS.items():
        lowered = lowered.replace(phrase, replacement)
    extra = " ".join(add for key, add in EXPANSIONS.items() if key in lowered)
    tokens = []
    for raw in re.findall(r"[a-z0-9]+", lowered + " " + extra):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        for suffix in ("ings", "ing", "ies", "es", "s"):
            if raw.endswith(suffix) and len(raw) - len(suffix) >= 4:
                raw = raw[: -len(suffix)] + ("y" if suffix == "ies" else "")
                break
        tokens.append(raw)
    return tokens


@dataclass
class Chunk:
    item_id: str
    item_type: str
    title: str
    section: str
    text: str
    path: str
    meta: dict = field(default_factory=dict)
    boost_tokens: list = field(default_factory=list)


def _flatten(value) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return str(value) if value is not None else ""


def _sources(record: dict) -> list[str]:
    found = set()
    def walk(node):
        if isinstance(node, dict):
            if "source" in node and isinstance(node["source"], str) and node["source"].startswith("REF-"):
                found.add(node["source"])
            if "reference" in node and isinstance(node["reference"], str) and node["reference"].startswith("REF-"):
                found.add(node["reference"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(record)
    return sorted(found)


def _markdown_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.M)
    return [(p.split("\n", 1)[0].strip(), p.split("\n", 1)[1] if "\n" in p else "") for p in parts[1:]]


class KnowledgeBase:
    def __init__(self, chunks: list[Chunk], records: dict[str, dict]):
        self.chunks = chunks
        self.records = records
        self._tokens = [tokenize(c.title + " " + c.section + " " + c.text) + c.boost_tokens for c in chunks]
        self._df: Counter = Counter()
        for tokens in self._tokens:
            self._df.update(set(tokens))
        self._avg = sum(len(t) for t in self._tokens) / max(len(self._tokens), 1)

    # -- construction -------------------------------------------------------
    @classmethod
    def load(cls, root: Path = KNOWLEDGE) -> "KnowledgeBase":
        chunks: list[Chunk] = []
        records: dict[str, dict] = {}

        for path in sorted(root.glob("skills/*/SKILL-*.json")):
            skill = load_json(path)
            records[skill["id"]] = {"type": "skill", "path": rel(path), "record": skill}
            meta = {"domain": skill["domain"], "status": skill["validation_status"], "sources": _sources(skill)}
            boost = tokenize(skill["title"] + " " + " ".join(skill.get("keywords", []))) * 2
            for key in ("purpose", "applicable_conditions", "principles", "procedure", "pcb_constraints"):
                chunks.append(Chunk(skill["id"], "skill", skill["title"], key, _flatten(skill[key]), rel(path), meta, boost))
            document = path.parent / skill["document"]
            for heading, body in _markdown_sections(document):
                chunks.append(Chunk(skill["id"], "skill", skill["title"], heading, body, rel(document), meta, boost))

        for path in sorted(root.glob("circuit_blocks/*/CB-*.json")):
            block = load_json(path)
            records[block["id"]] = {"type": "block", "path": rel(path), "record": block}
            meta = {"domain": block["category"], "status": block["validation_status"], "sources": _sources(block)}
            boost = tokenize(block["name"] + " " + " ".join(block.get("keywords", []))) * 2
            # Blocks are short: one chunk keeps co-occurring terms (e.g. "current" with a
            # high-voltage port) together. Ports carry the isolation domain of each signal.
            text = " ".join([block["function"], _flatten(block["inputs"]), _flatten(block["outputs"]),
                             _flatten(block["operating_conditions"]), _flatten(block["required_components"]),
                             _flatten(block["design_calculations"]), _flatten(block["interface_requirements"]),
                             _flatten(block["pcb_constraints"])])
            chunks.append(Chunk(block["id"], "block", block["name"], block["category"], text, rel(path), meta, boost))

        for path in sorted(root.glob("components/*/CMP-*.json")):
            component = load_json(path)
            records[component["id"]] = {"type": "component", "path": rel(path), "record": component}
            meta = {"domain": component["category"], "status": None, "sources": _sources(component)}
            title = f"{component['manufacturer']} {component['part_number']}"
            boost = tokenize(title + " " + component["description"] + " " + " ".join(component.get("keywords", [])))
            text = " ".join([component["description"], _flatten(component["application_conditions"]),
                             _flatten(component["design_considerations"]),
                             " ".join(p["name"] for p in component["key_parameters"])])
            chunks.append(Chunk(component["id"], "component", title, component["category"], text, rel(path), meta, boost))

        rules_path = root / "rules" / "engineering_rules.json"
        for rule in load_json(rules_path)["rules"]:
            records[rule["id"]] = {"type": "rule", "path": rel(rules_path), "record": rule}
            meta = {"domain": rule["domain"], "status": rule["validation_status"], "sources": _sources(rule),
                    "category": rule["category"], "priority": rule["priority"]}
            text = " ".join([rule["statement"], rule["rationale"], _flatten(rule["applicability"]),
                             rule["verification"]["procedure"]])
            chunks.append(Chunk(rule["id"], "rule", rule["title"], rule["category"], text, rel(rules_path), meta,
                                tokenize(rule["title"]) * 2))

        for path in sorted(root.glob("references/*/*/reference.json")):
            reference = load_json(path)
            records[reference["id"]] = {"type": "reference", "path": rel(path), "record": reference}
            analysis = path.parent / reference["analysis"]
            for heading, body in _markdown_sections(analysis):
                if heading.startswith("Decision"):
                    chunks.append(Chunk(reference["id"], "reference", reference["title"], heading, body, rel(analysis),
                                        {"domain": None, "status": "reference-derived", "sources": [reference["id"]]},
                                        tokenize(heading) * 2))
        return cls(chunks, records)

    # -- retrieval ----------------------------------------------------------
    def _score(self, query_tokens: list[str], index: int, k1: float = 1.4, b: float = 0.75) -> tuple[float, set]:
        tokens = self._tokens[index]
        counts = Counter(tokens)
        n = len(self.chunks)
        score, matched = 0.0, set()
        for term in set(query_tokens):
            tf = counts.get(term, 0)
            if not tf:
                continue
            matched.add(term)
            idf = math.log(1 + (n - self._df[term] + 0.5) / (self._df[term] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(tokens) / self._avg))
        return score, matched

    def search(self, question: str, limit: int = 8, types: set | None = None, domain: str | None = None) -> list[dict]:
        query_tokens = tokenize(question)
        best: dict[str, dict] = {}
        for index, chunk in enumerate(self.chunks):
            if types and chunk.item_type not in types:
                continue
            if domain and chunk.meta.get("domain") != domain:
                continue
            score, matched = self._score(query_tokens, index)
            if score <= 0:
                continue
            # Reward coverage of distinct query terms so short focused items are not drowned out.
            score *= (0.5 + len(matched) / max(len(set(query_tokens)), 1)) * TYPE_WEIGHT[chunk.item_type]
            current = best.get(chunk.item_id)
            if current is None or score > current["score"]:
                best[chunk.item_id] = {
                    "id": chunk.item_id, "type": chunk.item_type, "title": chunk.title, "section": chunk.section,
                    "score": round(score, 3), "matched_terms": sorted(matched), "path": chunk.path,
                    "validation_status": chunk.meta.get("status"), "sources": chunk.meta.get("sources", []),
                    "snippet": _snippet(chunk.text, matched)}
                for key in ("category", "priority"):
                    if key in chunk.meta:
                        best[chunk.item_id][key] = chunk.meta[key]
        return sorted(best.values(), key=lambda h: (-h["score"], h["id"]))[:limit]

    def get(self, item_id: str) -> dict | None:
        return self.records.get(item_id)

    def related(self, item_id: str) -> dict[str, list[str]]:
        """Items referenced by, and referencing, the given id."""
        out: dict[str, set] = defaultdict(set)
        entry = self.records.get(item_id)
        if entry:
            for key, ids in entry["record"].get("related", {}).items():
                out[key].update(ids)
        for other, data in self.records.items():
            if other != item_id and item_id in json.dumps(data["record"].get("related", {})):
                out["referenced_by"].add(other)
        return {k: sorted(v) for k, v in out.items()}


def _snippet(text: str, matched: set, width: int = 240) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    lowered = flat.lower()
    positions = [lowered.find(term) for term in matched if lowered.find(term) >= 0]
    start = max(min(positions) - 60, 0) if positions else 0
    snippet = flat[start:start + width]
    return ("…" if start else "") + snippet + ("…" if start + width < len(flat) else "")


DEMO_QUESTIONS = [
    ("What are the recommended layout practices for an isolated SiC gate driver?", None),
    ("What should be considered when selecting DC-link capacitors?", None),
    ("What reusable current-sensing circuits are available for a high-voltage converter?", {"block"}),
]


def write_demo(kb: KnowledgeBase, target: Path) -> str:
    lines = ["# Knowledge retrieval demonstration", "",
             "Generated by `python -m automation.knowledge.query --demo`. Deterministic: rerunning on an",
             "unchanged knowledge base reproduces this file. Scores are BM25 relevance, not confidence.", ""]
    for question, types in DEMO_QUESTIONS:
        lines += [f"## {question}", ""]
        if types:
            lines += [f"Filter: types = {sorted(types)}", ""]
        lines += ["| Rank | Id | Type | Title | Status | Score |", "|---|---|---|---|---|---|"]
        for rank, hit in enumerate(kb.search(question, limit=6, types=types), 1):
            lines.append(f"| {rank} | `{hit['id']}` | {hit['type']} | {hit['title']} | {hit['validation_status'] or '-'} | {hit['score']} |")
        lines.append("")
    text = "\n".join(lines)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question", nargs="?")
    parser.add_argument("--type", action="append", choices=["skill", "block", "component", "rule", "reference"])
    parser.add_argument("--domain")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="machine-readable output for agents")
    parser.add_argument("--get", metavar="ID", help="print one record with its related items")
    parser.add_argument("--demo", action="store_true", help="write knowledge/examples/retrieval-demo.md")
    args = parser.parse_args(argv)
    kb = KnowledgeBase.load()
    if args.demo:
        print(write_demo(kb, KNOWLEDGE / "examples" / "retrieval-demo.md"))
        return 0
    if args.get:
        entry = kb.get(args.get)
        if entry is None:
            print(f"unknown id {args.get}", file=sys.stderr)
            return 1
        print(json.dumps({**entry, "related_items": kb.related(args.get)}, indent=2, ensure_ascii=False))
        return 0
    if not args.question:
        parser.error("a question, --get or --demo is required")
    hits = kb.search(args.question, limit=args.limit, types=set(args.type) if args.type else None, domain=args.domain)
    if args.json:
        print(json.dumps({"question": args.question, "hits": hits}, indent=2, ensure_ascii=False))
        return 0
    for rank, hit in enumerate(hits, 1):
        status = hit["validation_status"] or "-"
        print(f"{rank:2}. {hit['id']:22} {hit['type']:9} {status:20} {hit['score']:7}  {hit['title']}")
        print(f"    {hit['path']} :: {hit['section']}")
        print(f"    {hit['snippet']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
