"""Insulation-coordination table -> net classes, KiCad design rules and router pair clearances (DAB-V1).

The working-voltage model of a power board is explicit: every hazardous net belongs to a domain whose potential is
``a*BUS + b*SW_A + c*SW_B`` plus a local excursion envelope (requirements/design_constraints.yaml, power_domains);
the switch nodes take the values {0, BUS} independently.  The pair-wise working-voltage difference is the maximum
over those states plus both envelopes, and the functional spacing comes from the reference table of the same file.
SELV nets (everything that is not in a hazardous domain) are separated from every hazardous net by the reinforced
value on every copper layer.  The values are IEC 60664-1 table values used as reference inputs; nothing here
asserts compliance.  Package-limited lead fields (TO-247-4 drain/source, 2220 capacitors) get an explicit,
documented relaxation to the package geometry when the table asks for more than the package provides.
"""
from __future__ import annotations

import fnmatch
import re
from itertools import product

ISLAND_TAGS = ('AH', 'AL', 'BL', 'BH')
ISLAND_PREFIXES = ('G_', 'KS_', 'OUTH_', 'OUTL_', 'VDD_', 'VEE_', 'DESAT_', 'OC_', 'NTC_', 'NTCR_', 'VEEA_', 'RLIM_', 'RDR_',
                   'FBVDD_', 'FBVEE_')
SENSE_ISO_NETS = ('S_16V', 'S_5V', 'S_VEEA', 'S_RLIM', 'S_FBVDD', 'S_FBVEE', 'VADC_IN', 'VMOD_IN')
PACKAGE_LEAD_GAPS = {  # footprint -> minimum pad-edge gap (mm) between electrodes of different potential
    'Package_TO_SOT_THT:TO-247-4_Vertical': 3.175,
    'Capacitor_SMD:C_2220_5750Metric': 3.3,
}


def domain_of(net: str, ladder_nodes: dict) -> tuple | None:
    """(domain name, coefficient triple, envelope) of a hazardous net; None for SELV nets."""
    if net in ladder_nodes:
        fraction = ladder_nodes[net]
        return (f'ladder_{fraction:.3f}', (fraction, 0.0, 0.0), 0.0)
    fixed = {'BUS_P': ('bus_p', (1, 0, 0), 0), 'PGND': ('bus_n', (0, 0, 0), 0), 'SW_A': ('sw_a', (0, 1, 0), 0),
             'SW_B': ('sw_b', (0, 0, 1), 0), 'XF_B': ('ac_b', (0, 0, 1), 60), 'AC_B': ('ac_b', (0, 0, 1), 60)}
    if net in fixed:
        return fixed[net]
    if net in SENSE_ISO_NETS:
        return ('sense_iso', (0, 0, 0), 20)
    for tag in ISLAND_TAGS:
        if net.endswith('_' + tag) and any(net.startswith(p) for p in ISLAND_PREFIXES):
            coeff = {'AH': (0, 1, 0), 'AL': (0, 0, 0), 'BL': (0, 0, 0), 'BH': (0, 0, 1)}[tag]
            return (f'island_{tag.lower()}', coeff, 25)
    return None


def ladder_fractions(parts: list) -> dict:
    """Fraction of BUS carried by every resistor-ladder / bleeder node, from the chain structure of the model."""
    fractions = {}
    chains = {}
    for p in parts:
        for net in p['nets'].values():
            if net and re.fullmatch(r'(VDIV|MDIV|BLD)\d+', net):
                chains.setdefault(re.match(r'[A-Z]+', net).group(0), set()).add(net)
    for prefix, nets in chains.items():
        count = len(nets) + 1  # n nodes -> n+1 resistors between BUS_P and the bottom
        for net in nets:
            index = int(net[len(prefix):])
            fractions[net] = round((count - index) / count, 4)
    return fractions


def power_domains(parts: list) -> dict:
    """net -> (domain, coefficients, envelope_V) for every hazardous net of a power-board model."""
    ladder = ladder_fractions(parts)
    nets = {n for p in parts for n in p['nets'].values() if n}
    return {n: d for n in sorted(nets) if (d := domain_of(n, ladder)) is not None}


def pair_voltage(a: tuple, b: tuple, bus: float) -> float:
    """Maximum working-voltage difference between two domain tuples over the switch-node states."""
    (_, ca, ea), (_, cb, eb) = a, b
    worst = 0.0
    for sw_a, sw_b in product((0.0, bus), repeat=2):
        va = ca[0] * bus + ca[1] * sw_a + ca[2] * sw_b
        vb = cb[0] * bus + cb[1] * sw_a + cb[2] * sw_b
        worst = max(worst, abs(va - vb))
    return worst + ea + eb


def class_name(index: int) -> str:
    return f'HV_{index:02d}'


def build_rules(req, board: str, parts: list) -> dict:
    """Net classes, .kicad_dru text and the evidence table for one board."""
    cfg = req.board(board)
    allnets = sorted({n for p in parts for n in p['nets'].values() if n})
    default = dict(clearance=cfg['min_clearance_mm'], track_width=max(cfg['min_track_mm'], 0.25),
                   via_diameter=cfg['via_mm'][0], via_drill=cfg['via_mm'][1])
    classes = [dict(name='Default', nets=[], **default)]
    if cfg['side'] == 'control':
        rails = [n for n in allnets if n in ('12V_IN', '12V_E', '5V0', '3V3', 'GND_CTRL', 'SW5', 'BST5')]
        classes.append(dict(name='CTRL_POWER', nets=rails, clearance=cfg['min_clearance_mm'], track_width=0.5,
                            via_diameter=cfg['via_mm'][0], via_drill=cfg['via_mm'][1]))
        classes.append(dict(name='CTRL_SIGNAL', nets=[n for n in allnets if n not in rails], clearance=cfg['min_clearance_mm'],
                            track_width=0.2, via_diameter=cfg['via_mm'][0], via_drill=cfg['via_mm'][1]))
        dru = ['(version 1)',
               f'(rule "Copper to board edge" (constraint edge_clearance (min {req.constraints["insulation_reference"]["selv_copper_to_board_edge_mm"]}mm)))']
        return dict(classes=classes, dru='\n'.join(dru) + '\n', evidence=dict(board=board, domains={}, pairs=[], relaxations=[],
                    note='Single SELV domain; functional spacing is the board minimum clearance.'))
    bus = float(cfg['bus_working_envelope_V'])
    domains = power_domains(parts)
    by_profile: dict = {}
    for net, (name, coeff, env) in domains.items():
        by_profile.setdefault((name, tuple(coeff), env), []).append(net)
    profiles = {class_name(i): key for i, key in enumerate(sorted(by_profile, key=lambda k: (k[0], k[1], k[2])))}
    for cname, key in profiles.items():
        classes.append(dict(name=cname, nets=sorted(by_profile[key]), clearance=cfg['min_clearance_mm'], track_width=0.3,
                            via_diameter=cfg['via_mm'][0], via_drill=cfg['via_mm'][1], domain=key[0]))
    classes.append(dict(name='CTRL', nets=[n for n in allnets if n not in domains], clearance=cfg['min_clearance_mm'],
                        track_width=0.3, via_diameter=cfg['via_mm'][0], via_drill=cfg['via_mm'][1]))
    iso = req.constraints['insulation_reference']
    reinforced = req.reinforced_gap_mm()
    hv_any_a = ' || '.join(f"A.NetClass == '{c}'" for c in profiles)
    hv_any_b = ' || '.join(f"B.NetClass == '{c}'" for c in profiles)
    dru = ['(version 1)',
           f'(rule "Reinforced HV-to-SELV separation, every copper layer (reference {reinforced} mm, to be reviewed)" '
           f'(condition "(A.NetClass == \'CTRL\' && ({hv_any_b})) || (B.NetClass == \'CTRL\' && ({hv_any_a}))") '
           f'(constraint clearance (min {reinforced}mm)))',
           f'(rule "Hazardous copper to board edge" (condition "A.NetClass != \'CTRL\'") (constraint edge_clearance (min {iso["hv_copper_to_board_edge_mm"]}mm)))',
           f'(rule "SELV copper to board edge" (condition "A.NetClass == \'CTRL\'") (constraint edge_clearance (min {iso["selv_copper_to_board_edge_mm"]}mm)))']
    pairs = []
    names = list(profiles)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            volts = pair_voltage(profiles[a], profiles[b], bus)
            gap = req.functional_gap_mm(volts)
            if gap > cfg['min_clearance_mm']:
                dru.append(f'(rule "Functional {a}-{b} {volts:g} V working envelope" '
                           f'(condition "(A.NetClass == \'{a}\' && B.NetClass == \'{b}\') || (A.NetClass == \'{b}\' && B.NetClass == \'{a}\')") '
                           f'(constraint clearance (min {gap}mm)))')
            pairs.append(dict(a=a, b=b, domain_a=profiles[a][0], domain_b=profiles[b][0], working_voltage_V=round(volts, 1), clearance_mm=gap))
    # package-limited lead fields: documented relaxation to the package geometry, never below the board minimum
    relaxations = []
    class_of = {net: cname for cname, key in profiles.items() for net in by_profile[key]}
    for p in parts:
        gap_pkg = PACKAGE_LEAD_GAPS.get(p['footprint'])
        if gap_pkg is None:
            continue
        nets = sorted({n for n in p['nets'].values() if n in domains})
        for i, x in enumerate(nets):
            for y in nets[i + 1:]:
                volts = pair_voltage(domains[x], domains[y], bus)
                needed = req.functional_gap_mm(volts)
                if needed <= gap_pkg:
                    continue
                ca, cb = class_of[x], class_of[y]
                dru.append(f'(rule "Package lead field {p["ref"]} ({p["footprint"].split(":")[1]}) {x}-{y}: component-limited functional spacing" '
                           f'(condition "A.memberOfFootprint(\'{p["ref"]}\') && B.memberOfFootprint(\'{p["ref"]}\') && '
                           f'((A.NetClass == \'{ca}\' && B.NetClass == \'{cb}\') || (A.NetClass == \'{cb}\' && B.NetClass == \'{ca}\'))") '
                           f'(constraint clearance (min {gap_pkg}mm)))')
                relaxations.append(dict(ref=p['ref'], footprint=p['footprint'], nets=[x, y], table_mm=needed, package_mm=gap_pkg,
                                        working_voltage_V=round(volts, 1),
                                        basis='manufacturer-rated package; functional insulation inside the component lead field'))
    evidence = dict(board=board, bus_working_envelope_V=bus, reinforced_mm=reinforced, reference=iso['standard'],
                    domains={n: dict(domain=d[0], coefficients=list(d[1]), envelope_V=d[2]) for n, d in domains.items()},
                    classes={c: dict(domain=k[0], coefficients=list(k[1]), envelope_V=k[2], nets=sorted(by_profile[k])) for c, k in profiles.items()},
                    pairs=pairs, relaxations=relaxations,
                    note='Functional spacing from the reference table of design_constraints.yaml (creepage PD2 MG I / clearance for the functional '
                         'impulse basis); inner layers use the outer-layer values; same-domain nets keep the board minimum clearance. '
                         'Reference inputs to be reviewed, not a compliance assertion.')
    return dict(classes=classes, dru='\n'.join(dru) + '\n', evidence=evidence, domains=domains, profiles=profiles)


def make_pair_gap(req, board: str, domains: dict):
    """(gap_mm, across_layers) callback for the PairwiseRouter and the placer: reinforced across the barrier, functional
    between hazardous domains, board minimum inside one domain or between SELV nets."""
    cfg = req.board(board)
    bus = float(cfg.get('bus_working_envelope_V', 0))
    reinforced = req.reinforced_gap_mm()
    minimum = float(cfg['min_clearance_mm'])
    cache = {}

    def gap(a: str, b: str):
        if a == b:
            return 0.0, False
        key = (a, b) if a < b else (b, a)
        if key in cache:
            return cache[key]
        da, db = domains.get(a), domains.get(b)
        if (da is None) != (db is None):
            result = (reinforced, True)
        elif da is None:
            result = (minimum, False)
        elif da[0] == db[0] and da[1] == db[1] and da[2] == db[2]:
            result = (minimum, False)
        else:
            result = (max(minimum, req.functional_gap_mm(pair_voltage(da, db, bus))), False)
        cache[key] = result
        return result
    return gap


def net_matches(net: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(net, p) for p in patterns)
