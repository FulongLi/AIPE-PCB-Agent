# V1 execution contract

The user authorised execution of [task071026.txt](../task071026.txt) on
2026-10-09 (Asia/Shanghai), with the following overriding constraint:

> Confirm required software and its installation location with the user before installing.

This includes additional Python packages and automation dependencies. Existing
software may be used. KiCad 10.0.7 x64 and its official libraries are approved for
`D:\EngineeringTools\KiCad\10.0` by the user's subsequent "可以" reply. No other
package installation or dependency upgrade is authorised. Capture approvals in
the installation plan.

Work in `FulongLi/AIPE-PCB-Agent`, branch `codex/v1-buck-1kw`; preserve existing
content. Do not fork or create another repository to bypass missing write access.
The initial remote commit is `c08c1494f5ea9def80efa3f1cbfaac64defdba4a`.

The original task defines scope and outputs. Progress is tracked in
`docs/status.md`. Missing tools and permission failures must be described as
blockers, never reported as successful verification.

Complete a real KiCad smoke test before converter engineering. Do not disable
meaningful ERC/DRC checks. Do not manufacture or energise hardware. Stop the
design sequence after a frozen V1 ready for human review; V2 needs feedback.
