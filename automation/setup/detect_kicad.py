"""Discover an existing KiCad CLI without installing or changing PATH."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_config(path: Path | None = None) -> dict:
    path = path or ROOT / ".aipe" / "local-tools.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Tool configuration must be a JSON object: {path}")
    return data


def version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(number) for number in re.findall(r"\d+", path.name))


def find_kicad_cli(config: dict | None = None) -> Path | None:
    config = read_config() if config is None else config
    explicit = os.environ.get("AIPE_KICAD_CLI") or config.get("kicad_cli")
    if explicit:
        candidate = Path(os.path.expandvars(explicit)).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"Configured KiCad CLI does not exist: {candidate}")
        return candidate.resolve()

    on_path = shutil.which("kicad-cli")
    if on_path:
        return Path(on_path).resolve()

    candidates: list[Path] = []
    system = platform.system()
    if system == "Windows":
        roots = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "KiCad",
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
            / "Programs/KiCad",
            Path("D:/EngineeringTools/KiCad"),
        ]
        for root in roots:
            if root.is_dir():
                versions = sorted((p for p in root.iterdir() if p.is_dir()),
                                  key=version_key, reverse=True)
                candidates.extend(p / "bin/kicad-cli.exe" for p in versions)
                candidates.append(root / "bin/kicad-cli.exe")
    elif system == "Darwin":
        for root in (Path("/Applications"), Path.home() / "Applications"):
            candidates.extend([
                root / "KiCad/KiCad.app/Contents/MacOS/kicad-cli",
                root / "KiCad.app/Contents/MacOS/kicad-cli",
            ])
    else:
        candidates.extend(Path(p) for p in (
            "/usr/bin/kicad-cli", "/usr/local/bin/kicad-cli", "/snap/bin/kicad-cli"
        ))
    return next((p.resolve() for p in candidates if p.is_file()), None)


if __name__ == "__main__":
    found = find_kicad_cli()
    print(found if found else "KiCad CLI not found; installation needs user confirmation.")
    raise SystemExit(0 if found else 2)
