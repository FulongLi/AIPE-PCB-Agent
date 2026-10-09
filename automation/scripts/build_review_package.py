"""Assemble the review entry point from verified exports and measured geometry."""
import csv
import json
import shutil
from automation.kicad_tools.buck_model import build,EXAMPLE
from automation.verification.verify_buck import verify


def main():
    verify()
    root=EXAMPLE;review=root/'review';review.mkdir(exist_ok=True)
    for file in (root/'manufacturing/review').iterdir():shutil.copyfile(file,review/file.name)
    for file in ('bom.csv','component_selection.csv'):shutil.copyfile(root/'components'/file,review/file)
    for file in ('ERC_report.json','DRC_report.json','known_issues.md','verification-summary.json'):
        shutil.copyfile(root/'verification'/file,review/file)
    shutil.copyfile(root/'components/bom.csv',root/'manufacturing/bom/purchasing_bom.csv')
    geometry=json.loads((root/'design/board_geometry.json').read_text())
    with (review/'test_points.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['Reference','Net','X_mm','Y_mm','Reference ground'])
        for p in build().parts:
            if p['kind']=='TP':writer.writerow([p['ref'],p['value'],*geometry[p['ref']]['position'],'GND / TP3'])
    m=json.loads((root/'verification/power-layout-metrics.json').read_text())
    lines=['# V1 power-electronics PCB rule review','',
      'Separate review of the final routed CAD. **Human review required.**',
      'Geometry measurements below are automated; their electrical acceptability is not.','',
      '| Rule / review question | Evidence and finding | Method / disposition |',
      '|---|---|---|',
      '| PE-PCB-001: Driver distance, gate loop and return | Driver-pad to gate-pad distances '+str(m['driver_to_gate_pin_distance_mm'])+' mm. HO/LO total branched tracks 32.00/59.75 mm. Individual gate resistors exist; high-side return is SW and low-side return GND. Return geometry is not a controlled Kelvin pair. | Semi-automated; ringing, current sharing and propagation review required (V1-01). |',
      '| PE-PCB-002: Are HF capacitors close enough? | Eight 1210 ceramics surround the bridge. Nearest capacitor-to-drain pad distances are 11 mm for Q1/Q2 and 16 mm for Q3/Q4. These distances are long relative to an optimized commutation cell. | Semi-automated; no unconditional acceptance (V1-01). |',
      '| PE-PCB-003: Is commutation loop too large? | Input ceramics, parallel TO-220 devices and copper form a spread-out loop. Native DRC verifies continuity, not loop area or inductance. Source and drain current pass through plated device pins and multiple power layers. | Human review; requires current-loop overlay and field/waveform analysis. |',
      '| PE-PCB-004: Is sensing correctly Kelvin routed? | R9 has four separate nets and no force/sense PCB shorts. ISENSE_P/N track sums are 36.893/45.893 mm; filtered branches are 21.236/21.736 mm. Both 10 ohm input resistors and differential 1 nF capacitor are present. | Automated topology plus human coupling review; not length matched (V1-08). |',
      '| PE-PCB-005: Feedback and switch-node exposure | Main sensing/buffer/ADC routing occupies the right/lower partitions. TEMP_RAW intentionally begins next to the power stage. Extended SW has ground-plane windows; local SW area is about 508/606/546 mm2 on F/In3/B. SW is functional but large. | Semi-automated net bounds; human EMI/return review required. |',
      '| PE-PCB-006: 42 A copper, vias and thermal spreading | Outer 70 um force/output pours; VIN on F/In2; SW on F/In3/B. Each shunt side has 32 x 1.0/0.5 mm vias. Main inductor and MOSFET PTH pads connect multiple layers. Actual shunt-pad necks are narrower than the illustrative 25 mm conductor in calculations. | Geometric inventory; do not apply the 25 mm budget as a whole-board ampacity result. Vendor DFM and thermal analysis required. |',
      '| PE-PCB-007: DSP separation and ground returns | DSP center (181,173) mm versus bridge around (123,49) mm. One common GND net uses In1/In4 and outer pours; no analog/digital split beneath the control area. High-current and signal returns still share impedance. | Semi-automated partition check; reviewer must assess return-current paths. |',
      '| PE-PCB-008: Decoupling placement | 26 dedicated DSP 100 nF bypass capacitors; maximum supply-pin to capacitor-pad distance '+str(max(x['distance_mm'] for x in m['dsp_bypass']))+' mm. AUX12/bootstrap capacitors are in the driver region. | Semi-automated; longer DSP supply escapes need impedance/settling review. |',
      '| Mechanical: Connectors, inductor and cooling | Four M5 terminals, bolt-down fuse, heavy upright magnetic, eight support holes. Custom power pads reference manufacturer drawings. Heatsink/clamp/cable assembly is not modeled or validated. | Human review required before fabrication (V1-03/09). |','',
      '## Conclusion and corrections','',
      'The final board has no native DRC errors, warnings, missing connections or schematic-parity findings. '
      'A dedicated third SW layer repaired the disconnected power copper; this is a real geometric change, '
      'not a DRC waiver. Thermal-via arrays, boot-jumper wiring, package geometry and connector silk were also corrected. '
      'The design is suitable for a V1 CAD review, but power-layout, thermal and protection adequacy remain open engineering questions.','',
      'Raw measurements: [power-layout-metrics.json](power-layout-metrics.json). '
      'Thresholds have not been invented to turn these engineering questions into automatic passes.','']
    (root/'verification/pcb_rule_review.md').write_text('\n'.join(lines),encoding='utf8')
    shutil.copyfile(root/'verification/pcb_rule_review.md',review/'pcb_rule_review.md')


if __name__=='__main__':main()
