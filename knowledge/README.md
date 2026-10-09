# AIPE Engineering Knowledge System — V0

> **Reference-derived engineering knowledge — human review required.** Nothing
> here has been simulated or hardware-validated by AIPE. Status labels say
> exactly how far each item has been checked.

This directory holds reusable power-electronics knowledge extracted from
manufacturer reference designs, in a form both engineers and AIPE agents can
use: Markdown for reasoning, JSON for machine use, and evidence pointers for
every claim. The workflow that produces and checks it is described in
[docs/knowledge-system.md](../docs/knowledge-system.md).

## Contents (V0)

| Area | Location | Count |
|---|---|---|
| Reference records, inventories and analyses | [`references/`](references) | 4 references, 25 documents |
| Engineering Skills (Markdown + JSON index) | [`skills/`](skills) | 6 |
| Circuit building blocks | [`circuit_blocks/`](circuit_blocks) | 13 |
| Component knowledge | [`components/`](components) | 19 |
| Engineering rules | [`rules/engineering_rules.json`](rules/engineering_rules.json) | 43 |
| Evidence checks (recomputed calculations, netlist facts) | [`verification/evidence-checks.json`](verification/evidence-checks.json) | 26 |
| JSON schemas | [`schemas/`](schemas) | 6 |
| Retrieval demonstration | [`examples/retrieval-demo.md`](examples/retrieval-demo.md) | 3 questions |

References: TI [TIDA-010054](references/ti/tida-010054/analysis.md) 10 kW DAB ·
Wolfspeed [CGD15SG00D2](references/wolfspeed/cgd15sg00d2/analysis.md) ·
[CGD1700HB2M-UNA](references/wolfspeed/cgd1700hb2m-una/analysis.md) (with PRD-09301) ·
[PRD-04814](references/wolfspeed/prd-04814/analysis.md) gate-bias options.

Skills: [SKILL-001 SiC gate driver](skills/gate_drivers/SKILL-001-sic-gate-driver-design.md) ·
[SKILL-002 gate-driver layout](skills/pcb_layout/SKILL-002-gate-driver-pcb-layout.md) ·
[SKILL-003 DC-link capacitors](skills/capacitors/SKILL-003-dc-link-capacitors.md) ·
[SKILL-004 isolated gate bias](skills/power_electronics/SKILL-004-isolated-gate-bias-supply.md) ·
[SKILL-005 sensing](skills/sensing/SKILL-005-current-voltage-sensing.md) ·
[SKILL-006 thermal placement](skills/thermal/SKILL-006-thermal-placement.md).

## Layout

```text
knowledge/
  references/<vendor>/<design>/
      reference.json    curated record: documents, URLs, revisions, checksums, licence, limitations
      inventory.json    generated metadata of downloaded files (names, sizes, hashes, formats)
      analysis.md       original AIPE analysis of each design decision
  skills/<domain>/SKILL-NNN-*.md|.json
  circuit_blocks/<category>/CB-XX-NNN.json
  components/<category>/CMP-<part>.json
  rules/engineering_rules.json
  verification/evidence-checks.json
  schemas/*.schema.json
  examples/retrieval-demo.md
```

Raw manufacturer files are downloaded to `.cache/references/` (Git-ignored) and
are never committed.

## Vocabulary

**Validation status** (weakest → strongest). V0 contains only the first two.

| Status | Meaning |
|---|---|
| `reference-derived` | Taken from a manufacturer design or document. An implementation exists; it is not independently verified. |
| `analytically-checked` | The cited arithmetic or connectivity was recomputed by `check_evidence` and agrees with the source. |
| `simulation-verified` | Reproduced in AIPE simulation (none yet). |
| `hardware-validated` | Measured on AIPE hardware (none yet). |

**Evidence kinds:** `stated` (written in the source), `observed` (seen in a
BOM, schematic or layout image), `netlist` (confirmed against CAD netlist data),
`calculated` (recomputed), `inferred` (AIPE interpretation the source does not
state — always flagged).

**Rule categories:** `hard-constraint`, `optimization-objective`,
`engineering-recommendation`, `human-review-requirement`. Rule **generality**:
`single-reference-observation`, `multi-source-consistent`,
`manufacturer-guidance`, `physics-derived`. Policies enforced by the validator:

- a single-reference observation is never a hard constraint;
- `multi-source-consistent` needs evidence from at least two references;
- a hard-constraint numerical limit cannot rest on a design-instance value;
- `analytically-checked` requires at least one cited, passing evidence check;
- conflicting approaches are kept in `conflicts`/`alternatives`, not resolved silently.

## Using the knowledge (agents and engineers)

```text
python -m automation.knowledge.query "recommended layout practices for an isolated SiC gate driver"
python -m automation.knowledge.query "DC-link capacitor selection" --type rule --json
python -m automation.knowledge.query --get CB-GD-001
```

Python API for the future AIPE Orchestrator:

```python
from automation.knowledge.query import KnowledgeBase
kb = KnowledgeBase.load()
hits = kb.search("isolated current sensing for an 800 V bus", types={"block"}, limit=5)
block = kb.get(hits[0]["id"])["record"]        # full JSON record
links = kb.related(hits[0]["id"])              # skills, rules, components, referenced_by
```

Each hit carries `id`, `type`, `validation_status`, `path`, `sources` and a
snippet. Agents should cite ids and evidence locations, respect
`applicability` and `exclusions`, and surface `human-review-requirement` rules
to the reviewer instead of deciding them.

## Extending: adding a new reference design

1. Create `references/<vendor>/<design>/reference.json` with document entries
   (official URL, kind, file name/type, `redistribution: not-verified`).
   Use only manufacturer URLs; never construct or guess links.
2. `python -m automation.knowledge.acquire --reference REF-…` — downloads,
   checks file type, records date, size, SHA-256 and resolved URL.
3. `python -m automation.knowledge.inspect_sources` — inventories archives and
   extracts text/CSV into the cache.
4. Read the material; record revision, licence terms, limitations and source
   discrepancies; write `analysis.md` (seven questions per decision).
5. Add or update skills, blocks, components and rules with evidence pointing to
   document ids and locations. Prefer extending existing items over duplicates.
6. Add evidence checks for any calculation or connectivity you rely on
   (`automation/knowledge/check_evidence.py`), then run it.
7. `python -m automation.knowledge.validate` and
   `python -m unittest discover -s tests`; regenerate the retrieval demo with
   `python -m automation.knowledge.query --demo` if rankings change.

## Known limitations of V0

- Four references; sensing and DC-link knowledge rest mainly on TIDA-010054.
- TI Altium sources were not parsed; TI layout knowledge is visual observation.
- Several capacitor and module datasheets could not be retrieved automatically
  (recorded per component as `unverified` or `not-located`).
- Retrieval is lexical BM25 with a small synonym table, adequate for routing an
  agent to the right items but not semantic search.
- No AIPE simulation or hardware validation; Buck V1 is unaffected.
