import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import procedural as p
PARAMS=dict(radius=128,thickness=32,depth=64,angle=180,segments=8,direction=0)
class Boundaries(unittest.TestCase):
    def test_definition_roundtrip_and_input_isolation(self):
        values=dict(PARAMS);d=p.define('ARCH','blender',values,1,profile_id='project-a')
        values['radius']=999
        self.assertEqual(p.Definition.loads(d.dumps()),d)
        self.assertEqual(d.parameters['radius'],128)
        self.assertEqual(d.owner_profile_id,'project-a')
    def test_evaluation_and_validation_are_profile_owned(self):
        for owner,parts in [('blender',1),('source_hl2_windows',8)]:
            d=p.define('ARCH',owner,PARAMS,1)
            self.assertEqual(len(p.validate(d,p.evaluate(d))),parts)
    def test_unknown_generator_rejected_without_replacement(self):
        from dataclasses import replace
        d=replace(p.define('ARCH','blender',PARAMS,1),generator='future.nodes')
        with self.assertRaises(ValueError):p.evaluate(d)
    def test_existing_owner_and_units_survive_active_profile_change(self):
        d=p.define('ARCH','source_hl2_windows',PARAMS,.0254,16,profile_id='source-project')
        root={'wl_definition':d.dumps()}
        new=p.definition_for(root,'ARCH',{**PARAMS,'segments':6},d.owner,1,1)
        self.assertEqual(new.unit_meters,.0254);self.assertEqual(new.grid_step,16);self.assertEqual(new.owner_profile_id,'source-project')
        with self.assertRaises(ValueError):p.definition_for(root,'ARCH',PARAMS,'blender',1,1)
    def test_validation_rejects_corrupt_adapter_output(self):
        d=p.define('ARCH','blender',PARAMS,1)
        with self.assertRaises(ValueError):p.validate(d,[([(0,0,0)],[(0,1,2)])])
