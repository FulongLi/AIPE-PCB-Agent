"""Source provenance of the DAB-V1 component selections: fetch every manufacturer URL named in the requirement files,
record the retrieval date, HTTP status, content type, size and SHA-256 in requirements/source_manifest.json.

Files are cached under the Git-ignored .cache/dab-datasheets; nothing is redistributed.  A recorded hash says that a
document with that content was retrieved from that URL on that date - it does not say that its content was read or
that the design agrees with it; the verification level of each pin table is in automation/dab_v1/parts.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from automation.dab_v1 import parts, requirements as rq

CACHE = rq.ROOT / '.cache' / 'dab-datasheets'
URL = re.compile(r'https?://[^\s"\'<>]+')


def collect(req) -> list[dict]:
    """(id, url, context) for every URL in components.yaml / interfaces.yaml plus the IC tables of parts.py."""
    seen = {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f'{path}/{k}')
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f'{path}[{i}]')
        elif isinstance(node, str):
            for url in URL.findall(node):
                url = url.rstrip('.,;)')
                seen.setdefault(url, path)
    walk(req.components, 'components')
    walk(req.interfaces, 'interfaces')
    for mpn, (_, _, source, _) in parts.EXTRA_IC.items():
        seen.setdefault(source, f'parts.EXTRA_IC/{mpn}')
    for mpn, row in parts.VERIFIED_IC.items():
        seen.setdefault(row[2], f'sic_buck_control_model.IC/{mpn}')
    for key, row in {**parts.EXTRA_CAPS}.items():
        seen.setdefault(row['source'], f'parts.EXTRA_CAPS/{key}')
    records = []
    for url, context in sorted(seen.items()):
        ident = re.sub(r'[^A-Za-z0-9]+', '-', url.split('://', 1)[1])[:90].strip('-')
        records.append(dict(id=ident, url=url, context=context))
    return records


def fetch(record: dict, timeout: float = 40.0) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = dict(record, retrieved=date.today().isoformat())
    try:
        with urlopen(Request(record['url'], headers={'User-Agent': 'AIPE engineering reference review'}), timeout=timeout) as response:
            data = response.read()
            out.update(http_status=response.status, resolved=response.url, content_type=response.headers.get('Content-Type', ''))
    except HTTPError as exc:
        out.update(status='http-error', http_status=exc.code)
        return out
    except (URLError, TimeoutError, OSError) as exc:
        out.update(status='unreachable', error=str(exc)[:200])
        return out
    kind = 'pdf' if data.startswith(b'%PDF') else 'html' if b'<html' in data[:4000].lower() else 'other'
    suffix = '.pdf' if kind == 'pdf' else '.html' if kind == 'html' else '.bin'
    path = CACHE / (record['id'] + suffix)
    path.write_bytes(data)
    out.update(status='downloaded', kind=kind, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), cache=str(path.relative_to(rq.ROOT)).replace('\\', '/'))
    return out


def build(req, *, refresh: bool = True) -> dict:
    manifest_path = rq.REQUIREMENTS / 'source_manifest.json'
    previous = {}
    if manifest_path.exists():
        previous = {r['url']: r for r in json.loads(manifest_path.read_text(encoding='utf-8'))['sources']}
    records = []
    for record in collect(req):
        if not refresh and record['url'] in previous:
            records.append(previous[record['url']])
            continue
        records.append(fetch(record))
        print(records[-1]['status'], record['url'], flush=True)
    manifest = dict(schema=1, generation=rq.GENERATION, generated=date.today().isoformat(),
                    scope='Manufacturer URLs named by the requirement files and the part tables; cached under .cache/dab-datasheets (ignored). '
                          'A hash records what was retrieved, not that it was read; pin-table verification levels are in automation/dab_v1/parts.py.',
                    pinout_verification=parts.PINOUT_SOURCES, sources=records,
                    counts=dict(total=len(records), downloaded=sum(r.get('status') == 'downloaded' for r in records),
                                pdf=sum(r.get('kind') == 'pdf' for r in records), html=sum(r.get('kind') == 'html' for r in records),
                                failed=sum(r.get('status') in ('http-error', 'unreachable') for r in records)))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--no-refresh', action='store_true', help='keep previously recorded entries, fetch only new URLs')
    args = parser.parse_args(argv)
    manifest = build(rq.load(), refresh=not args.no_refresh)
    print(json.dumps(manifest['counts']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
