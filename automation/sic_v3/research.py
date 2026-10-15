"""Cache explicitly named public manufacturer PDFs and preserve content provenance.

No vendor PDF is redistributed in Git. Run with --id ID --url HTTPS_URL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/sic-buck-400v-200v-5kw-v3'

def fetch(identifier: str, url: str) -> dict:
    import pymupdf
    cache = ROOT / '.cache/v3-datasheets'
    cache.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(url, headers={'User-Agent': 'AIPE engineering reference review'}), timeout=45) as response:
        data, resolved = response.read(), response.url
    if not data.startswith(b'%PDF'):
        raise ValueError(f'{identifier}: response is not a PDF')
    path = cache / (identifier + '.pdf')
    path.write_bytes(data)
    with pymupdf.open(path) as doc:
        pages = len(doc)
        path.with_suffix('.txt').write_text('\n'.join(f'\n=== PAGE {i+1} ===\n{p.get_text()}' for i, p in enumerate(doc)), encoding='utf-8')
    return dict(id=identifier, url=url, resolved=resolved, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), pages=pages,
                retrieved=date.today().isoformat(), cache=str(path.relative_to(ROOT)).replace('\\', '/'), status='downloaded')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    record = fetch(args.id, args.url)
    manifest = EXAMPLE / 'requirements/source_manifest.json'
    data = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    # Initial exploratory download used an object wrapper; retain that format.
    records = data if isinstance(data, list) else data['sources']
    records[:] = [r for r in records if r['id'] != args.id] + [record]
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(record))

if __name__ == '__main__':
    main()
