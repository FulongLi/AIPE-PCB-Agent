"""Shared paths and deterministic JSON helpers for the knowledge pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = ROOT / "knowledge"
REFERENCES = KNOWLEDGE / "references"
SCHEMAS = KNOWLEDGE / "schemas"
# Raw manufacturer material; .cache/ is Git-ignored. Never commit its contents.
CACHE = ROOT / ".cache" / "references"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def reference_files() -> Iterator[Path]:
    """Every curated reference record, in a stable order."""
    return iter(sorted(REFERENCES.glob("*/*/reference.json")))


def cache_dir(reference_id: str) -> Path:
    return CACHE / reference_id


def rel(path: Path) -> str:
    """Repository-relative POSIX path (absolute path for files outside the repository)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()
