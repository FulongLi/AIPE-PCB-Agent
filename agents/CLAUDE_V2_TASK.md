# V2 execution contract

The user authorised execution of [task09102026.txt](../task09102026.txt) on
2026-10-10 with the instruction "执行这个task" (execute this task). The V2
run is performed by Claude Code (Claude Fable 5.1) independently of the Codex
V1 run, as the task requires.

Constraints carried over from V1 and from the task:

- Work in `FulongLi/AIPE-PCB-Agent` on branch `feat/sic-buck-5kw-v2`, created
  from `upstream/main` (commit 6ec5977, which already contains the merged V1 and
  the Engineering Knowledge System V0).
- The authenticated account (MrCoconut616) has read access to the upstream
  repository and administers the fork `MrCoconut616/AIPE-PCB-Agent`, from which
  the V1 pull request (#1) was merged. The task permits "an authorised fork and
  create a PR" when direct push is unavailable, so V2 is pushed to the fork and
  submitted as a pull request against upstream `main`. Nothing is merged.
- Nothing under `examples/buck-48v-24v-1kw/` is modified; the frozen V1 release
  and its manifest stay byte-identical (guarded by `tests/test_knowledge.py`).
- No software is installed or upgraded. KiCad 10.0.7 at
  `D:\EngineeringTools\KiCad\10.0`, its bundled Python/pcbnew/ngspice shared
  library, host Python 3.10 with its already-present numpy/scipy, Git and the
  GitHub CLI are the only tools used. Existing configurations are not changed.
- The knowledge system is used through its existing interface
  (`automation/knowledge/query.py`) and is not rewritten; new automation is added
  as new modules beside the V1 tools, which remain unchanged for reproducibility.
- Real KiCad ERC/DRC/exports are the only accepted CAD evidence. No check is
  disabled or waived to obtain a clean report; unresolved issues are documented.
- No fabrication, purchasing, firmware commissioning or energisation. The run
  ends with a frozen V2 engineering review package and a pull request.

Progress and blockers are recorded in the example's `review/design_report.md`
and `verification/known_issues.md`.
