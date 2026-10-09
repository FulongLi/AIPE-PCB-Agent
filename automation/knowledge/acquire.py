"""Download reference-design documents listed in curated reference records.

Usage (repository root):

    python -m automation.knowledge.acquire                # all references
    python -m automation.knowledge.acquire --reference REF-TI-TIDA-010054
    python -m automation.knowledge.acquire --refresh      # re-download
    python -m automation.knowledge.acquire --datasheets   # component datasheets only

Files land in ``.cache/references/<reference id>/`` and component datasheets in
``.cache/references/datasheets/`` (both Git-ignored). Each document's
``acquisition`` block (in ``reference.json`` or the component record) is
rewritten with the actual outcome: resolved URL, date, byte count, SHA-256 and
status. A failed download is recorded as failed; it is never reported as
acquired.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.error
import urllib.request
from pathlib import Path

from automation.knowledge.common import CACHE, KNOWLEDGE, cache_dir, load_json, reference_files, rel, sha256_file, write_json

USER_AGENT = "Mozilla/5.0 (AIPE-PCB-Agent knowledge acquisition; engineering reference study)"
# Leading bytes that must match the declared file type; HTML error pages fail.
MAGIC = {"pdf": (b"%PDF-",), "zip": (b"PK\x03\x04", b"PK\x05\x06")}


def check_magic(path: Path, file_type: str) -> None:
    expected = MAGIC.get(file_type)
    if expected is None:
        return
    head = path.read_bytes()[:8]
    if not head.startswith(expected):
        raise ValueError(f"downloaded bytes are not a {file_type} file (starts {head!r})")


def download(url: str, target: Path, timeout: int = 120) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        resolved = response.geturl()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(data)
    partial.replace(target)
    return resolved


def acquire_file(url: str, target: Path, file_type: str, previous: dict, refresh: bool, today: str) -> dict:
    record = {"status": "failed", "retrieved": today, "cache_path": rel(target)}
    try:
        resolved = previous.get("resolved_url")
        if refresh or not target.exists():
            resolved = download(url, target)
        else:
            record["retrieved"] = previous.get("retrieved", today)
        check_magic(target, file_type)
        record.update(status="downloaded", bytes=target.stat().st_size, sha256=sha256_file(target))
        if resolved:
            # Drop TI's per-request timestamp query; keep the revisioned path.
            record["resolved_url"] = resolved.split("?ts=")[0]
        if previous.get("sha256") and previous["sha256"] != record["sha256"]:
            record["note"] = f"content changed since previous acquisition (was {previous['sha256']})"
    except (urllib.error.URLError, OSError, ValueError) as error:
        record["error"] = f"{type(error).__name__}: {error}"
        if target.exists():
            target.unlink()
    return record


def acquire_document(reference_id: str, document: dict, refresh: bool, today: str) -> dict:
    target = cache_dir(reference_id) / document["file_name"]
    return acquire_file(document["source_url"], target, document["file_type"],
                        document.get("acquisition", {}), refresh, today)


def run_datasheets(refresh: bool, today: str) -> int:
    """Download datasheets whose URL is recorded in component records."""
    failures = 0
    for path in sorted(KNOWLEDGE.glob("components/*/CMP-*.json")):
        component = load_json(path)
        sheet = component["datasheet"]
        if not sheet.get("url"):
            continue
        target = CACHE / "datasheets" / f"{component['id']}.pdf"
        sheet["acquisition"] = acquire_file(sheet["url"], target, "pdf", sheet.get("acquisition", {}), refresh, today)
        outcome = sheet["acquisition"]
        # A "verified-pdf" URL that no longer serves a PDF is a real failure;
        # an "unverified" URL failing just confirms its status.
        failures += sheet["url_status"] == "verified-pdf" and outcome["status"] != "downloaded"
        print(f"{component['id']:34} {sheet['url_status']:13} {outcome['status']}"
              + (f"  {outcome.get('error')}" if outcome["status"] != "downloaded" else ""))
        write_json(path, component)
    return failures


def run(selected: str | None = None, refresh: bool = False, datasheets_only: bool = False) -> int:
    today = dt.date.today().isoformat()
    failures = run_datasheets(refresh, today) if selected is None else 0
    if datasheets_only:
        return 1 if failures else 0
    for path in reference_files():
        reference = load_json(path)
        if selected and reference["id"] != selected:
            continue
        for document in reference["documents"]:
            document["acquisition"] = acquire_document(reference["id"], document, refresh, today)
            outcome = document["acquisition"]
            failures += outcome["status"] != "downloaded"
            print(f"{reference['id']:28} {document['file_name']:70} {outcome['status']}"
                  + (f"  {outcome.get('error')}" if outcome["status"] != "downloaded" else ""))
        write_json(path, reference)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reference", help="limit to one reference id")
    parser.add_argument("--refresh", action="store_true", help="re-download cached files")
    parser.add_argument("--datasheets", action="store_true", help="only component datasheets")
    args = parser.parse_args(argv)
    return run(args.reference, args.refresh, args.datasheets)


if __name__ == "__main__":
    sys.exit(main())
