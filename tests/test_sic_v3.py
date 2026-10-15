"""V3 regression checks: analytical bounds, isolation and executable CAD topology."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from automation.sic_v3 import calculations as calc, model, footprints, schematics
from automation.kicad_tools import project_footprints as pf, project_schematic as ps
from automation.kicad_tools.native_schematic import parse, children, pins


class ElectricalTests(unittest.TestCase):
    def test_rated_corners_and_bias_load_envelope(self):
        data=calc.calculate()
        for p in data['corners']:
            self.assertLess(p['ripple_pp_A'],10)
            self.assertAlmostEqual(p['duty']*p['vin_V'],200)
            self.assertGreater(p['rms_A'],p['current_A'])
            self.assertLess(p['junction_h_estimate_C'],125)
        self.assertGreater(data['gate_bias']['source_margin'],1)
        self.assertGreater(data['gate_bias']['sink_margin'],1)
        self.assertLess(data['protection']['peak_after_8us_bound_A'],60)
        self.assertLess(data['protection']['dc_link_discharge_s'],60)
        self.assertLess(data['protection']['output_discharge_s'],60)

    def test_magnetic_rolloff_and_energy_not_constant_L(self):
        low,high=calc.magnetic(25),calc.magnetic(55)
        self.assertLess(high['L_H'],low['L_H'])
        self.assertGreater(high['L_H'],calc.protection()['inductor_min_L_to_60A_H'])
        self.assertGreater(calc.operating_point(440)['ripple_pp_A'],calc.operating_point(360)['ripple_pp_A'])

    def test_all_model_pins_connected_or_explicit_nc(self):
        for circuit in [model.power(),model.control()]:
            report=ps.analyse_connectivity(circuit.parts,schematics.FLAGS[circuit.board])
            for k in ['undriven_power_nets','pin_conflicts','single_pin_nets','no_connect_pins_with_nets']:
                self.assertFalse(report[k],(circuit.board,k,report[k]))
            self.assertEqual(len({p['ref'] for p in circuit.parts}),len(circuit.parts))

    def test_physical_barrier_land_gaps(self):
        for name in ['V3_UCC21710_HV','V3_UCC14141_DWN','V3_AMC1311_DWV']:
            pads=pf.pads_in_text(footprints.custom()[name][0])
            left=max(p['at'][0]+p['size'][0]/2 for p in pads if p['at'][0]<0)
            right=min(p['at'][0]-p['size'][0]/2 for p in pads if p['at'][0]>0)
            self.assertGreaterEqual(right-left,8.0,name)

    def test_hazardous_domain_inventory(self):
        c=model.power();domains=schematics.power_domains(c.parts)
        for n in ['RAW','BUS','PGND','SW','VOUT','KS_H','KS_L','H_VEEA','S_VEEA','BUS_DIV1','BLEED_OUT_3']:
            self.assertIn(n,domains)
        for n in model.HARNESS.values():self.assertNotIn(n,domains)
        classes,rules,evidence=schematics.rules('power',c.parts)
        self.assertIn('(min 8.0)',rules)
        self.assertNotIn('exemption',rules.lower())
        self.assertTrue(all(p['clearance_mm']>=.25 for p in evidence['pairs']))


class PresentationTests(unittest.TestCase):
    def test_conventional_buck_is_wired_and_offboard_choke_not_a_footprint(self):
        c=model.power()
        parts=[p for p in c.parts if c.groups.get(p['ref'])=='half_bridge']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            result=ps.generate_project(dict(name='fixture',title='buck fixture',kicad_dir=root/'cad',design_dir=root/'design',
                pages={'01_stage':'Power flow'},parts=parts,flag_nets=['BUS','PGND','VOUT','KS_H','KS_L'],
                presentation=dict(groups=c.groups,group_templates={'01_stage/half_bridge':dict(type='buck_half_bridge',high_side='Q1',low_side='Q2',inductor='L1',output_net='VOUT')})))
            mapping=json.loads((root/'design/schematic_mapping.json').read_text())
            pos=mapping['placement']
            self.assertEqual(pos['Q1'][0]['x'],pos['Q2'][0]['x'])
            self.assertLess(pos['Q1'][0]['y'],pos['L1'][0]['y'])
            self.assertLess(pos['L1'][0]['y'],pos['Q2'][0]['y'])
            self.assertGreater(pos['L1'][0]['x'],pos['Q1'][0]['x'])
            tree=parse((root/'cad/01_stage.kicad_sch').read_text(encoding='utf-8'))
            choke=next(s for s in children(tree,'symbol') if any(x[1:3]==['Reference','L1'] for x in children(s,'property')))
            self.assertEqual(children(choke,'on_board')[0][1],'no')
            self.assertGreater(len(children(tree,'wire')),25)
        self.assertNotIn('L1',[p['ref'] for p in pf.select_parts(parts)])

    def test_analogue_symbols_preserve_each_pin_once(self):
        for p in model.control().parts:
            if not p.get('amplifier_channels'):continue
            groups=ps.default_unit_grouping(p)
            definition,extents,source=ps.amplifier_symbol(p,groups,'test')
            seen=[pin['number'] for unit in range(1,len(extents)+1) for pin in pins(definition,unit)]
            self.assertCountEqual(seen,p['pins'])
            self.assertEqual(len(seen),len(set(seen)))

if __name__=='__main__':unittest.main()
