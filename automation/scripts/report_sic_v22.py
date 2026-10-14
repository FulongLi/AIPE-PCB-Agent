"""Consolidate current native checks, frozen integrity and V2.2 before/after evidence.

Run under KiCad Python after ERC, DRC, exports, netlist checks and layout metrics.
Fails on stale board evidence; it does not convert open physical risks into passes.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from automation.kicad_tools.sic_buck_common import EXAMPLE, BANNER
from automation.scripts.verify_sic_buck import latest_run, verify


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import pcbnew as pcb
    out = EXAMPLE / "review/v22"
    result = dict(generated_utc=datetime.now(timezone.utc).isoformat(), scope="CAD and analytical evidence only; human review required",
                  frozen={}, boards={}, calculations={}, comparison=[])
    for version in ("v2", "v2.1"):
        folder = EXAMPLE / "releases" / version; manifest = folder / "SHA256SUMS.json"
        data = read(manifest)
        errors = [n for n,v in data['files'].items() if not (folder/n).is_file() or sha(folder/n) != v['sha256']]
        assert not errors, (version, errors)
        result['frozen'][version] = dict(files=len(data['files']), manifest_sha256=sha(manifest), errors=errors)
    for label in ("power", "control"):
        name = f"AIPE_SiC_Buck_{label.title()}"
        board_path = EXAMPLE / f"kicad/{label}_board/{name}.kicad_pcb"
        board = pcb.LoadBoard(str(board_path)); digest = sha(board_path)
        manifest_path, drc = latest_run('drc', name)
        assert drc['status'] == 'passed' and drc['source_sha256'] == digest
        metrics = EXAMPLE / f"verification/engineering_checks/layout_metrics_{label}.json"
        measured = read(metrics)
        assert measured['board']['sha256'] == digest
        netlist = read(EXAMPLE / f"verification/netlist_check_{label}.json")
        assert netlist['exact_match']
        stored = read(EXAMPLE / f"verification/engineering_checks/stored_zone_fill_check_{label}.json")
        assert stored['board_sha256'] == digest
        assert stored['tool_exit_code'] == stored['violations'] == stored['unconnected_items'] == 0
        tracks = list(board.GetTracks())
        progress = dict(schema_version=1, status=BANNER, generator="automation.kicad_tools.refine_sic_v22",
                        baseline=f"releases/v2.1/verification/routing_progress_{label}.json",
                        generated_utc=result['generated_utc'], board=str(board_path), board_sha256=digest,
                        stage='routed', unresolved_count=0, footprints=len(list(board.GetFootprints())),
                        tracks=sum(not isinstance(t,pcb.PCB_VIA) for t in tracks), vias=sum(isinstance(t,pcb.PCB_VIA) for t in tracks),
                        zones=len(list(board.Zones())), drc=dict(manifest=str(manifest_path), status=drc['status'],
                        finding_count=drc['finding_count'], **drc['finding_counts']),
                        evidence_note="Counts are read from the final CAD; original router search statistics remain in the frozen release.")
        (EXAMPLE/f'verification/routing_progress_{label}.json').write_text(json.dumps(progress,indent=2)+'\n',encoding='utf-8')
        eco_path = out/f'eco_{label}.json'; eco = read(eco_path)
        eco['output_sha256'] = digest
        eco['native_verification'] = str(manifest_path.relative_to(EXAMPLE))
        eco_path.write_text(json.dumps(eco,indent=2)+'\n',encoding='utf-8')
        (out/'after').mkdir(exist_ok=True)
        for suffix in ('json','md'):
            shutil.copy2(metrics.with_suffix('.'+suffix),out/'after'/metrics.with_suffix('.'+suffix).name)
        before = read(out/f'baseline/layout_metrics_{label}.json')
        for ic in (('U4','U8','U10','U11') if label == 'control' else ()):
            old = next(x for x in before['decoupling']['ics'] if x['ic']==ic)['max_distance_mm']
            new = next(x for x in measured['decoupling']['ics'] if x['ic']==ic)['max_distance_mm']
            result['comparison'].append(dict(metric=f'Control {ic} maximum supply-pad to nearest bypass-pad distance',unit='mm',before=old,after=new,
                                             limitation='Geometric distance, not measured supply-loop inductance'))
        if label == 'power':
            for q in ('Q1','Q2'):
                old = next(x for x in before['gate_loops']['loops'] if x['mosfet']==q)
                new = next(x for x in measured['gate_loops']['loops'] if x['mosfet']==q)
                for key in ('gate_track_mm','gate_vias','gate_track_over_kelvin_pour_fraction'):
                    result['comparison'].append(dict(metric=f'{q} {key}',before=old[key],after=new[key],
                                                     limitation='Summed gate-net geometry/projection; not a closed-loop inductance extraction'))
        result['boards'][label] = dict(sha256=digest, footprints=progress['footprints'], drc=drc['finding_counts'],
                                      schematic_model_board_exact=True, metrics=str(metrics.relative_to(EXAMPLE)),
                                      stored_fill_diagnostic=stored,
                                      drc_manifest=str(manifest_path.relative_to(EXAMPLE)))
    result['calculations'] = dict(
        evidence='Analytical calculations; no hardware measurement',
        current_reference=dict(before_V=3.3/10.09,after_V=2.5*1.01/7.66, fixed_sensor_zero_V=.33,
                               before_supply_5pct_error_A=.05*(3.3/10.09)/.05, new_nominal_reference_error_A=(2.5*1.01/7.66-.33)/.05,
                               reference_load_A=2.5/7660, divider_output_impedance_ohm=6650*1010/7660,
                               caveat='Sensor offset/gain, REF3125 errors, divider tolerance and ADC error require calibration'),
        sense_bias=dict(required_A=2*.0097+.001,typical_Rint_ohm=30, equation9_Rlim_max_ohm=5/.0204-30,
                        old_eq9_capacity_A=5/(1000+30),new_eq9_capacity_A=5/(160+30),
                        stress_capacity_A=4.935/(160*1.01+60),stress_note='60 ohm internal resistance is an engineering assumption, not a datasheet maximum',
                        normal_combined_resistor_switch_loss_W=.0204*10, resistor_rating_W_at_70C=.66,
                        ambient_derated_resistor_rating_W_at_100C=.66*(155-100)/(155-70),
                        caveat='Normal-operation loss bound does not qualify startup pulses, regulator stability or continuous operation'))
    status = verify()
    result['aggregate_verification'] = status
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if status['status'] != 'passed':
        raise RuntimeError('Aggregate verification failed; see validation.json')
    lines=['# V2.1 → V2.2 measured comparison','','All distances and lengths below come from native CAD geometry, not hardware measurements.','',
           '| Metric | V2.1 | V2.2 |','|---|---:|---:|']
    for row in result['comparison']:
        lines.append(f"| {row['metric']} | {row['before']:.4f} | {row['after']:.4f} |")
    lines += ['', 'Pad distance is not route length. Gate-net sums are not loop inductance. A passing DRC does not close the independent review’s insulation, electrothermal or mechanical issues.',
              '', 'See `validation.json` for calculations, source hashes and native-check references.']
    lines += ['', '## Native copper comparisons', '',
              'Equal-scale native KiCad B.Cu / B.Fab / Edge.Cuts plots, viewed through the board without mirroring. '
              'These images show local changes; they do not establish current capability or loop inductance.', '',
              '![Sense-bias resistor before and after](comparison_power_bias.png)', '',
              '![Reset bypass before and after](comparison_control_reset.png)', '',
              '![Fault-logic bypasses before and after](comparison_control_logic.png)']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'boards':result['boards'],'aggregate':status},indent=2))


if __name__ == '__main__':
    main()
