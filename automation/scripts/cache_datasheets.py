"""Cache manufacturer references for local inspection; installs nothing."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    **{part: f"https://www.ti.com/lit/ds/symlink/{part}.pdf" for part in (
        "tms320f28335", "csd19536kcs", "ucc27211", "lm5164", "tps54302",
        "tps767d3", "ina240", "lm2903b", "sn74lvc2g08", "sn74lvc1g74",
        "tlv9004", "tps3808", "sn74lvc1g04", "sn74lvc1g08", "sn74lvc1g86", "lm61")},
    "ref3125": "https://www.ti.com/lit/gpn/REF31",
    "asv": "https://abracon.com/Oscillators/ASV.pdf",
    "ihxl2000vz-3a": "https://www.vishay.com/docs/34681/ihxl2000vz-3a.pdf",
    "css4j-4026": "https://www.bourns.com/docs/product-datasheets/css4j-4026.pdf",
    "74651195": "https://www.we-online.com/components/products/datasheet/74651195.pdf",
}


def fetch(item):
    name, url = item
    target = ROOT / ".cache/datasheets" / (name + ".pdf")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(request, timeout=60).read()
        if not data.startswith(b"%PDF-"):
            raise ValueError(f"Not a PDF: {url}")
        target.write_bytes(data)
    return {"id": name, "url": url, "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, SOURCES.items()))
    target = ROOT / "examples/buck-48v-24v-1kw/components/references.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"retrieved": "2026-10-09", "sources": records}, indent=2) + "\n")
    print(f"Cached {len(records)} manufacturer PDFs; reference hashes recorded.")
