"""Host-side copper plan preparation: union the pour rectangles of each net and layer into polygons (Shapely).

floorplan.py (KiCad Python, no Shapely) records the pours as rectangles; KiCad reports overlapping same-net zones of
equal priority as a DRC error, so the rectangles are merged here into disjoint polygons before routing.  Polygons
with holes are rejected (none are expected from the strip-and-island plan); the merged plan is written back into
pcb/floorplan_<board>.json under plan.zones with plan.zones_merged = true.
"""
from __future__ import annotations

import argparse
import json

from automation.dab_v1 import requirements as rq
from automation.dab_v1.floorplan import PCB_DIR, save_json


def merge_zones(zones: dict) -> dict:
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    merged = {}
    for net, layers in zones.items():
        merged[net] = {}
        for layer, polys in layers.items():
            shape = unary_union([Polygon(p).buffer(0) for p in polys])
            parts = list(shape.geoms) if shape.geom_type == 'MultiPolygon' else [shape]
            out = []
            for part in parts:
                if part.is_empty:
                    continue
                if list(part.interiors):
                    raise ValueError(f'{net}/{layer}: merged pour has a hole; split the rectangles differently')
                ring = [(round(x, 4), round(y, 4)) for x, y in part.exterior.coords[:-1]]
                out.append(ring)
            merged[net][layer] = out
    return merged


def prepare(board: str) -> dict:
    path = PCB_DIR / f'floorplan_{board}.json'
    record = json.loads(path.read_text(encoding='utf-8'))
    plan = record['plan']
    if plan.get('zones_merged'):
        return record
    plan['zones_raw_rectangles'] = plan['zones']
    plan['zones'] = merge_zones(plan['zones'])
    plan['zones_merged'] = True
    save_json(path, record)
    counts = {net: {layer: len(p) for layer, p in layers.items()} for net, layers in plan['zones'].items()}
    print(f'{board}: merged pours -> {counts}', flush=True)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--board', choices=rq.BOARDS, required=True)
    args = parser.parse_args(argv)
    prepare(args.board)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
