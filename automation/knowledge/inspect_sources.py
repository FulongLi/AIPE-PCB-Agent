"""Inspect acquired reference documents and record a committed inventory.

Usage (repository root, after ``acquire``):

    python -m automation.knowledge.inspect_sources

For each downloaded document this stage:

* safely extracts ZIP archives into the cache (no path traversal, skips
  ``__MACOSX`` resource forks) and classifies members by engineering format;
* extracts PDF text into the cache when a text backend exists (``pypdf`` if
  importable, otherwise macOS PDFKit through ``osascript``); otherwise the
  document is marked for manual reading rather than silently skipped;
* converts XLSX worksheets to CSV in the cache using only the standard library.

The committed ``inventory.json`` holds metadata only (member names, sizes,
hashes, formats, page counts and extraction outcomes), never document content.
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

from automation.knowledge.common import cache_dir, load_json, reference_files, rel, sha256_file, write_json

FORMATS = {
    "gerber": {".gtl", ".gbl", ".gto", ".gbo", ".gts", ".gbs", ".gtp", ".gbp", ".g1", ".g2", ".gm",
               ".gm1", ".gm2", ".gm9", ".gm10", ".gm12", ".gd1", ".gg1", ".art", ".apr", ".apr_lib"},
    "drill": {".drl", ".drr", ".ldp", ".rou", ".txt_drill"},
    "altium-project": {".prjpcb", ".pcbdoc", ".schdoc", ".pcblib", ".schlib", ".outjob",
                       ".prjpcbstructure", ".prjpcbvariants"},
    "orcad-capture": {".dsn", ".opj", ".dbk"},
    "allegro-board": {".brd"},
    "allegro-netlist": {".dat"},
    "odb++": {".t_g_z", ".tgz"},
    "step-3d": {".step", ".stp"},
    "pdf": {".pdf"},
    "spreadsheet": {".xlsx", ".xls"},
    "pick-and-place": {".csv"},
    "text": {".txt", ".rep", ".extrep", ".rul", ".htm"},
}
PDF_HELPER = """ObjC.import('PDFKit');
function run(argv){var d=$.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[0]));
if(!d||d.isNil()) throw new Error('unreadable PDF'); var out=[];
for(var i=0;i<d.pageCount;i++){var s=d.pageAtIndex(i).string; out.push('\\f=== page '+(i+1)+' ===\\n'+(s.isNil()?'':ObjC.unwrap(s)));}
return out.join('\\n');}"""


def classify(name: str) -> str:
    lowered = name.lower()
    suffix = PurePosixPath(lowered).suffix
    if "drill" in lowered and suffix == ".txt":
        return "drill"
    if "pick" in lowered or "centroid" in lowered or "placement" in lowered:
        return "pick-and-place"
    for kind, suffixes in FORMATS.items():
        if suffix in suffixes:
            return kind
    return "other"


def safe_extract(archive: Path, destination: Path) -> list[dict]:
    """Extract regular members; reject absolute or parent-relative paths."""
    members = []
    if destination.exists():
        shutil.rmtree(destination)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if info.is_dir() or "__MACOSX" in parts or parts[-1] in (".DS_Store",):
                continue
            if name.startswith("/") or ".." in parts:
                raise ValueError(f"unsafe archive member {name!r} in {archive.name}")
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            members.append({"path": name, "bytes": info.file_size, "format": classify(name),
                            "sha256": sha256_file(target), "_local": target})
    return members


def pdf_text(path: Path) -> tuple[str | None, str]:
    """Return (text, backend). text is None when no backend can read it."""
    try:
        import pypdf  # optional; not required by the repository
        import logging
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        reader = pypdf.PdfReader(str(path))
        pages = [f"\f=== page {i + 1} ===\n" + (page.extract_text() or "") for i, page in enumerate(reader.pages)]
        return "\n".join(pages), "pypdf"
    except ImportError:
        pass
    if sys.platform == "darwin" and shutil.which("osascript"):
        result = subprocess.run(["osascript", "-l", "JavaScript", "-e", PDF_HELPER, str(path)],
                                capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return result.stdout, "macos-pdfkit"
        return None, f"macos-pdfkit failed: {result.stderr.strip()[:200]}"
    return None, "no PDF text backend available; read manually"


def xlsx_to_csv(path: Path, out_dir: Path) -> list[str]:
    """Minimal XLSX reader: shared strings + inline values, one CSV per sheet."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    written = []
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")) for si in root.findall("m:si", ns)]
        for sheet in sorted(n for n in book.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)):
            rows = []
            for row in ET.fromstring(book.read(sheet)).iter(f"{{{ns['m']}}}row"):
                values = {}
                for cell in row.findall("m:c", ns):
                    column = re.match(r"[A-Z]+", cell.get("r", "A")).group(0)
                    index = 0
                    for char in column:
                        index = index * 26 + ord(char) - 64
                    value = cell.find("m:v", ns)
                    text = value.text if value is not None else "".join(t.text or "" for t in cell.iter(f"{{{ns['m']}}}t"))
                    if cell.get("t") == "s" and text is not None:
                        text = shared[int(text)]
                    values[index] = text or ""
                if values:
                    rows.append([values.get(i, "") for i in range(1, max(values) + 1)])
            target = out_dir / f"{path.stem}.{PurePosixPath(sheet).stem}.csv"
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)
            written.append(target.name)
    return written


def inspect_file(path: Path, text_dir: Path) -> dict:
    """Derive text/CSV for one local file; returns metadata only."""
    kind = classify(path.name)
    outcome: dict = {}
    if kind == "pdf":
        text, backend = pdf_text(path)
        outcome["text_backend"] = backend
        if text is not None:
            pages = text.count("\f=== page ")
            target = text_dir / (path.stem + ".txt")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            chars = len(re.sub(r"\f=== page \d+ ===\n", "", text).strip())
            outcome.update(pages=pages, text_chars=chars,
                           text_status="extracted" if chars > 200 else "image-only-or-empty; inspect visually")
        else:
            outcome["text_status"] = "not-extracted"
    elif kind == "spreadsheet" and path.suffix.lower() == ".xlsx":
        outcome["csv_sheets"] = xlsx_to_csv(path, text_dir)
    return outcome


def inspect_reference(path: Path) -> dict:
    reference = load_json(path)
    base = cache_dir(reference["id"])
    documents = []
    for document in reference["documents"]:
        entry = {"id": document["id"], "file_name": document["file_name"]}
        local = base / document["file_name"]
        if document.get("acquisition", {}).get("status") != "downloaded" or not local.exists():
            entry["status"] = "not-available-locally; run acquire first"
            documents.append(entry)
            continue
        text_dir = base / "text" / document["id"]
        if document["file_type"] == "zip":
            members = safe_extract(local, base / "extracted" / document["id"])
            for member in members:
                member.update(inspect_file(member.pop("_local"), text_dir))
            entry["members"] = members
            entry["formats"] = sorted({m["format"] for m in members})
        else:
            entry.update(inspect_file(local, text_dir))
        entry["status"] = "inspected"
        documents.append(entry)
    inventory = {
        "reference_id": reference["id"],
        "generated": dt.date.today().isoformat(),
        "generator": "automation/knowledge/inspect_sources.py",
        "note": "Metadata only. Raw files and derived text stay in the Git-ignored cache.",
        "documents": documents,
    }
    write_json(path.parent / "inventory.json", inventory)
    return inventory


def main() -> int:
    for path in reference_files():
        inventory = inspect_reference(path)
        for document in inventory["documents"]:
            detail = ", ".join(document.get("formats", [])) or document.get("text_status", "")
            print(f"{inventory['reference_id']:28} {document['id']:18} {document['status']:12} {detail}")
        print(f"  -> {rel(path.parent / 'inventory.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
