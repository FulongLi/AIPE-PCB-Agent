# Installation proposal

Status: **awaiting user confirmation**. Prepared 2026-10-09, Asia/Shanghai.

| Tool | Finding | Proposed action | Proposed location |
| --- | --- | --- | --- |
| Git 2.53.0.windows.2 | Present | Reuse | Existing installation |
| Python 3.10.11 x64 | Present | Reuse for standard-library automation | Existing installation |
| GitHub CLI 2.88.1 | Present and authenticated | Reuse | Existing installation |
| KiCad 10.0.7 x64 | Not found in PATH, default install roots or installed-app records | Install official stable suite, CLI, symbols, footprints and 3D libraries after confirmation | Proposed D:\EngineeringTools\KiCad\10.0 |
| Additional Python packages | Not currently required by bootstrap | No installation proposed yet | Any future environment and packages require confirmation |
| Third-party KiCad MCP / autorouter | Not required for bootstrap | No installation proposed | None |

Alternative KiCad directory offered: `C:\Program Files\KiCad\10.0`.
The selected directory is not yet approved. Installer downloads, if needed, will
be kept in ignored `.cache/downloads/` inside the repository. Standard installer
settings or user configuration may also be written to the Windows user profile.
Do not change the machine-wide PATH unnecessarily; retain an explicit CLI path
in `.aipe/local-tools.json`.

Before running an installer, verify its official origin and Authenticode
signature. If elevation is necessary, report the exact action requiring user
interaction. Do not silently fall back to a different installation directory.

The official download page reports 10.0.7 as the current stable Windows release.
The exact installed executable and automation capabilities must be verified
locally after installation; web documentation alone is not a smoke test.

References (checked 2026-10-09):

- [KiCad Windows downloads](https://www.kicad.org/download/windows/)
- [KiCad CLI manual](https://docs.kicad.org/10.0/en/cli/cli.html)
- [KiCad API and bindings](https://dev-docs.kicad.org/en/apis-and-binding/)

## Approval record

Pending. No software installation approved or performed as of this checkpoint.
