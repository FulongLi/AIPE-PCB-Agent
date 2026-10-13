"""Shared contract for the SiC buck electrical models (power board and control board; V2 design, V2.1 generation).

This module is the single place where the two board models agree on names: project
basenames, the mezzanine pin-to-net assignment taken from design/design_decisions.json,
the shared part-list helper class and a starter table of generic passives with real
manufacturer part numbers. The board models (sic_buck_power_model.py and
sic_buck_control_model.py) import it; they must not modify it. Everything here is
deterministic data; electrical correctness is established by KiCad ERC/DRC and human
review, not by this file.
"""
from __future__ import annotations

from contextlib import contextmanager

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/sic-buck-400v-200v-5kw"
DECISIONS = EXAMPLE / "design/design_decisions.json"
POWER_NAME = "AIPE_SiC_Buck_Power"
CONTROL_NAME = "AIPE_SiC_Buck_Control"
POWER_DIR = EXAMPLE / "kicad/power_board"
CONTROL_DIR = EXAMPLE / "kicad/control_board"
# Generation label of everything the current generators write (title blocks, silkscreen, models, page notes, evidence
# writers). The frozen V2 generation lives in releases/v2 and keeps its own label; V1 tooling has its own string.
GENERATION = "V2.2"
BANNER = f"AI-GENERATED ENGINEERING PROTOTYPE - {GENERATION} - HUMAN REVIEW REQUIRED"
BASIS = "400 V (360-440 V) to 200 V / 25 A / 5 kW / 50 kHz synchronous buck; Wolfspeed C4MS025120K; TMS320F28335 control board on a stacked SELV mezzanine"


def decisions() -> dict:
    """Load the orchestrator-resolved design baseline."""
    return json.loads(DECISIONS.read_text(encoding="utf-8"))


def mezzanine_nets() -> dict[str, str]:
    """Mezzanine pin number -> net name, from the baseline (identical on both boards)."""
    return {str(k): v for k, v in decisions()["interconnect"]["pin_assignment"].items()}


# Nets that cross the mezzanine must use exactly these names on both boards.
MEZZANINE_NET_ALIASES = {
    "+12V_PROT": "12V_PROT",
    "+3V3_PWRBOARD": "3V3",
}


def mezzanine_net(pin: str) -> str:
    """Canonical KiCad net name for a mezzanine pin (aliases applied)."""
    name = mezzanine_nets()[str(pin)]
    return MEZZANINE_NET_ALIASES.get(name, name)


def pin_defs(text: str) -> dict:
    """Parse 'number:name:type ...' into the shared pins dictionary (KiCad pin types)."""
    return {n: dict(name=name, type=kind) for n, name, kind in (s.split(":") for s in text.split())}


class Circuit:
    """Ordered part list in the shared model format (see automation/kicad_tools/buck_model.py).

    Each part carries an explicit pad-number -> net mapping and explicit pin names/types so
    ERC semantics are meaningful. The 'board' key selects the KiCad project.
    """

    def __init__(self, board: str):
        self.board = board
        self.parts: list[dict] = []
        self.counters: dict[str, int] = {}
        # Presentation metadata (V2.1): functional block of each reference, kept out of the part dicts so the
        # electrical model (design/circuit_<board>.json) is byte-identical with or without block annotations.
        self.groups: dict[str, str] = {}
        self.block_titles: dict[str, str] = {}
        self._blocks: list[str] = []

    @contextmanager
    def block(self, name: str, title: str | None = None):
        """Functional block for the schematic presentation: every add() inside is grouped under `name`.

        Nested blocks join with '/'. The group id is '<page>/<name>' on the sheet of the part's page; a title is
        shown as the group heading (default: the name with underscores as spaces).
        """
        self._blocks.append(name)
        full = "/".join(self._blocks)
        if title:
            self.block_titles[full] = title
        try:
            yield full
        finally:
            self._blocks.pop()

    def add(self, prefix, value, footprint, nets, *, page, kind="passive", mpn="", maker="", source="",
            definitions=None, ref=None, note="", dnp=False):
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        ref = ref or prefix + str(self.counters[prefix])
        assert not any(p["ref"] == ref for p in self.parts), ref
        if self._blocks:
            self.groups[ref] = "/".join(self._blocks)
        nets = {str(k): v for k, v in nets.items()}
        definitions = definitions or {n: dict(name=n, type="passive") for n in nets}
        assert set(definitions) == set(nets), (ref, set(definitions) ^ set(nets))
        part = dict(ref=ref, value=value, footprint=footprint, nets=nets, page=page, kind=kind, mpn=mpn,
                    maker=maker, source=source, pins=definitions, note=note, xy=None, board=self.board, dnp=dnp)
        self.parts.append(part)
        return part

    def resistor(self, value, a, b, page, *, package="0603", note="", mpn=None, maker=None, source=None, dnp=False, ref=None):
        """Generic thick-film resistor; HV/pulse parts must pass an explicit mpn."""
        spec = RESISTOR_PACKAGES[package]
        return self.add("R", value, spec["footprint"], {1: a, 2: b}, page=page, kind="R",
                        mpn=mpn or spec["mpn"](value), maker=maker or spec["maker"], source=source or spec["source"], note=note, dnp=dnp, ref=ref)

    def cap(self, key, a, b, page, *, note="", dnp=False, ref=None):
        """Capacitor from the shared PASSIVE_CAPS table (key like '100n/50V/0603')."""
        spec = PASSIVE_CAPS[key]
        return self.add("C", key.rsplit("/", 1)[0], spec["footprint"], {1: a, 2: b}, page=page, kind="C",
                        mpn=spec["mpn"], maker=spec["maker"], source=spec["source"], note=note, dnp=dnp, ref=ref)

    def header(self, count, nets, page, *, note="", rows=1, mpn=None, maker="Samtec", source="https://www.samtec.com/products/tsw"):
        label = f"{rows}x{count // rows:02}"
        return self.add("J", note or label, f"Connector_PinHeader_2.54mm:PinHeader_{label}_P2.54mm_Vertical", nets, page=page, kind="J",
                        mpn=mpn or f"TSW-{count // rows:03}-07-G-{'S' if rows == 1 else 'D'}", maker=maker, source=source, note=note)


def _yageo(series, code_voltage):
    def mpn(value):
        return f"{series}FR-07{resistor_code(value)}L"
    return mpn


def resistor_code(value: str) -> str:
    """Yageo-style value code: 4.7k -> 4K7, 10k -> 10K, 0.1 -> 0R1, 100 -> 100R, 1M -> 1M."""
    v = value.strip()
    if v.endswith("M"):
        return v.replace(".", "M") if "." in v else v
    if v.endswith("k"):
        return v[:-1].replace(".", "K") if "." in v else v[:-1] + "K"
    if v.startswith("0."):
        return "0R" + v[2:]
    if "." in v:
        return v.replace(".", "R")
    return v + "R"


RESISTOR_PACKAGES = {
    "0603": dict(footprint="Resistor_SMD:R_0603_1608Metric", mpn=_yageo("RC0603", 75), maker="Yageo", source="https://www.yageo.com/en/Chart/Download/pdf/RC0603"),
    "0805": dict(footprint="Resistor_SMD:R_0805_2012Metric", mpn=_yageo("RC0805", 150), maker="Yageo", source="https://www.yageo.com/en/Chart/Download/pdf/RC0805"),
    "1206": dict(footprint="Resistor_SMD:R_1206_3216Metric", mpn=_yageo("RC1206", 200), maker="Yageo", source="https://www.yageo.com/en/Chart/Download/pdf/RC1206"),
    "2512": dict(footprint="Resistor_SMD:R_2512_6332Metric", mpn=lambda value: f"CRCW2512{resistor_code(value)}FKEG", maker="Vishay", source="https://www.vishay.com/docs/20035/dcrcwe3.pdf"),
}

# Generic capacitors: key = value/voltage/package. Real orderable parts; verification level is
# recorded by the component records, not here.
PASSIVE_CAPS = {
    "100p/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H101JA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H101JA01%23"),
    "330p/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H331JA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H331JA01%23"),
    "470p/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H471JA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H471JA01%23"),
    "680p/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H681JA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H681JA01%23"),
    "1n/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM1885C1H102JA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H102JA01%23"),
    "10n/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM188R71H103KA01D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H103KA01%23"),
    "100n/50V/0603": dict(footprint="Capacitor_SMD:C_0603_1608Metric", mpn="GRM188R71H104KA93D", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM188R71H104KA93%23"),
    "1u/50V/0805": dict(footprint="Capacitor_SMD:C_0805_2012Metric", mpn="GRM21BR71H105KA12L", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM21BR71H105KA12%23"),
    "2.2u/25V/0805": dict(footprint="Capacitor_SMD:C_0805_2012Metric", mpn="GRM21BR71E225KA73L", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM21BR71E225KA73%23"),
    "4.7u/25V/1206": dict(footprint="Capacitor_SMD:C_1206_3216Metric", mpn="C3216X7R1E475K160AC", maker="TDK", source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3216X7R1E475K160AC"),
    "10u/25V/1210": dict(footprint="Capacitor_SMD:C_1210_3225Metric", mpn="GRM32ER71E106KA12L", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM32ER71E106KA12%23"),
    "22u/25V/1210": dict(footprint="Capacitor_SMD:C_1210_3225Metric", mpn="GRM32ER71E226KE15L", maker="Murata", source="https://www.murata.com/en-us/products/productdetail?partno=GRM32ER71E226KE15%23"),
    "0.47u/630V/2220": dict(footprint="Capacitor_SMD:C_2220_5750Metric", mpn="CGA9P1X7T2J474M250KC", maker="TDK", source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=CGA9P1X7T2J474M250KC"),
    "1n/1kV/1812": dict(footprint="Capacitor_SMD:C_1812_4532Metric", mpn="C4532C0G3A102J130KA", maker="TDK", source="https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C4532C0G3A102J130KA"),
    "100u/25V/elec": dict(footprint="Capacitor_SMD:CP_Elec_8x10.5", mpn="EEE-FK1E101P", maker="Panasonic", source="https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFK1E101P"),
}

# Spacing / net-class membership used by both schematic generators and the board scripts.
NET_CLASS_PATTERNS = {
    "HV_VIN": ["VIN_RAW", "VIN", "VIN_PRE"],
    "HV_SW": ["SW"],
    "HV_PGND": ["PGND"],
    "HV_VOUT": ["VOUT", "VOUT_L"],
    "DRV_HS": ["HS_*", "G_H", "KS_H", "DESAT_H*", "VDD_H", "VEE_H"],
    "DRV_LS": ["LS_*", "G_L", "KS_L", "DESAT_L*", "VDD_L", "VEE_L"],
    "SENSE_ISO": ["ISO_*", "5V_ISO", "VIN_DIV*", "VOUT_DIV*"],
    "PE": ["PE"],
}
