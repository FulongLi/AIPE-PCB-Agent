# Engineering Knowledge System — architecture and workflow

The knowledge system turns manufacturer reference designs into traceable,
reusable design knowledge for AIPE agents. It sits beside the existing CAD
automation and does not change it:

```text
Requirements ──► calculations ──► schematic/PCB generation ──► KiCad checks ──► review
                       ▲                     ▲                       ▲
                       └──── knowledge/ (skills, blocks, components, rules) ──┘
                                   ▲
              automation/knowledge (acquire → inspect → extract → check → store)
```

## Reference-learning pipeline

```text
Reference discovery      manufacturer product pages → curated reference.json
        ↓
Download                 acquire.py: official URLs only, type check, SHA-256, date, resolved URL
        ↓
Document / CAD inspection inspect_sources.py: safe unzip, format inventory, PDF text, XLSX→CSV;
                         allegro_netlist.py / odb_netlist.py for CAD connectivity
        ↓
Engineering extraction   analysis.md per reference (what/why/problem/applicability/evidence/reuse/verification)
        ↓
Skill / rule / component skills/, circuit_blocks/, components/, rules/ with evidence pointers
extraction
        ↓
Evidence validation      check_evidence.py (recompute calculations, confirm netlist facts)
                         validate.py (schemas, cross-refs, traceability, policies, part numbers)
        ↓
Knowledge storage        Git: original analysis + metadata; .cache/references: raw files (ignored)
        ↓
Retrieval                query.py: BM25 search, get, related; JSON for agents
```

| Stage | Command | Output | Committed? |
|---|---|---|---|
| Download | `python -m automation.knowledge.acquire` | `.cache/references/<ref>/…`, acquisition block per document and datasheet | metadata only |
| Inspect | `python -m automation.knowledge.inspect_sources` | `inventory.json`; cache `extracted/`, `text/` | inventory only |
| Check | `python -m automation.knowledge.check_evidence` | `knowledge/verification/evidence-checks.json` | yes |
| Validate | `python -m automation.knowledge.validate` | report (exit 1 on any error) | no |
| Retrieve | `python -m automation.knowledge.query …` | ranked hits / JSON | demo file only |

Every reference document records: source URL, document revision and the basis
for that revision, download date, file type, download status, size and
SHA-256, extraction status and method, redistribution status and limitations.
A failed download is recorded as `failed` with the error; it is never shown as
acquired. Checks that need cached files report `skipped` when the cache is
missing — never `pass`.

## Licensing and redistribution

TI design files are bundled with TI's Important Notice, which permits use only
for developing applications with the TI products and prohibits other
reproduction. Wolfspeed documents are "All rights reserved" without a
redistribution licence. Therefore only original AIPE analysis, derived
knowledge, file inventories, checksums and links are committed. The tests
fail if PDF, ZIP, XLSX, STEP or CAD source files appear under `knowledge/`.

## Environment

Standard-library Python (tested here with Python 3.9.6 on macOS; the existing
automation targets 3.10+). Optional, used only when present: `pypdf` for PDF
text, otherwise macOS PDFKit through `osascript`, otherwise documents are marked
for manual reading. `jsonschema` is used only by a cross-check test. No package
was installed for this work.

## Integration points

- **AIPE Orchestrator (future):** `KnowledgeBase.load()`, `.search()`, `.get()`,
  `.related()` in `automation/knowledge/query.py`; or the CLI with `--json`.
  The Orchestrator is not implemented in V0.
- **Existing PCB review rules:** knowledge rules link to `PE-PCB-001…008`
  (`docs/pcb-design-rules.md`) through `related.project_rules`; the validator
  rejects unknown project rule ids. Several rules carry an `aipe_hook` naming
  the automated check they could become (e.g. net-class clearances, Kelvin-net
  separation).
- **Component databases:** component records are design knowledge, not a
  parametric catalogue. `external_refs.aipe_component_db` and
  `external_refs.aipe_transistor_db` are the join keys for the existing AIPE
  databases (null until linked). Power semiconductors (e.g. C3M0075120K) are
  deliberately not duplicated; they appear only as reference usage.

## Validation status of this V0

See [knowledge-status.md](knowledge-status.md) for the recorded results.
