# Installation proposal

Status: **installed and smoke-tested**. Prepared 2026-10-09, Asia/Shanghai.

| Tool | Finding | Proposed action | Proposed location |
| --- | --- | --- | --- |
| Git 2.53.0.windows.2 | Present | Reuse | Existing installation |
| Python 3.10.11 x64 | Present | Reuse for standard-library automation | Existing installation |
| GitHub CLI 2.88.1 | Present and authenticated | Reuse | Existing installation |
| KiCad 10.0.7 x64 | Not found in PATH, default install roots or installed-app records | Install official stable suite, CLI, symbols, footprints and 3D libraries after confirmation | Proposed D:\EngineeringTools\KiCad\10.0 |
| Additional Python packages | Not currently required by bootstrap | No installation proposed yet | Any future environment and packages require confirmation |
| Third-party KiCad MCP / autorouter | Not required for bootstrap | No installation proposed | None |

Alternative KiCad directory offered: `C:\Program Files\KiCad\10.0`.
The user approved `D:\EngineeringTools\KiCad\10.0`. Installer downloads will
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

On 2026-10-09 the user replied "可以" to the explicit request to install the
KiCad 10.0.7 x64 suite, CLI and official libraries at
`D:\EngineeringTools\KiCad\10.0`. This approves that software and location.
Additional dependencies still require separate confirmation. Installation is
complete and verified. The installer exited 0 using current-user mode and the
approved directory. CLI reports 10.0.7; bundled Python 3.11.5 imports `pcbnew`
and reports 10.0.7. Symbols, footprints and 3D libraries are present. Existing
system Python remains 3.10.11.

## Installation evidence

- Download: official download page's Tsinghua mirror, `kicad-10.0.7-x86_64.exe`.
- File size: 968953784 bytes.
- SHA-256 (computed locally): `CE3881B6A9188EB34AC1EBAAEC7651149E8A025206410ADDFB11A1A9656ECF95`.
- Windows Authenticode status: Valid; signer KICAD SERVICES CORPORATION.
- Certificate issuer: GlobalSign GCC R45 EV CodeSigning CA 2020.
- Certificate serial: `39DF6B588D969CA15D8D2756`, matching the official page.
- Install mode: `/S /currentuser /D=D:\EngineeringTools\KiCad\10.0`.
- Executable: `D:\EngineeringTools\KiCad\10.0\bin\kicad-cli.exe`.
- Actual smoke evidence: `examples/automation-smoke/verification/smoke-result.json`.
- No additional application or third-party Python package was installed by the
  automation. The official suite supplies its own Python and dependencies.
