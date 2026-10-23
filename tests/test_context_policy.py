import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import context_policy as p

class Object(dict):
    type='MESH';wavelength_context_role='AUTO';data=None

class ContextPolicyTests(unittest.TestCase):
    def test_capabilities_are_independent_and_render_scoped(self):
        self.assertIn('PREPARE',p.capabilities(editing=False))
        self.assertNotIn('EDIT',p.capabilities(editing=False))
        self.assertIn('GRID',p.capabilities(editing=False))
        self.assertNotIn('HANDLES',p.capabilities(editing=False))
        self.assertNotIn('GRID',p.capabilities(overlays=False))
        self.assertIn('EDIT',p.capabilities(overlays=False))
        for caps in [p.capabilities(mode='CLEAN'),p.capabilities(mode='SUSPENDED'),p.capabilities(workspace_enabled=False),p.capabilities(rendering=True)]:
            self.assertEqual(caps,{'INSPECT','EXPORT','RENDER'})
    def test_export_exclusion_does_not_mean_editor_helper(self):
        self.assertEqual(p.role(Object(wl_exclude=True,wl_model_reference=True)),'CONTENT')
        light=Object(wl_exclude=True,wl_sun_preview=True);light.type='LIGHT'
        self.assertEqual(p.role(light),'CONTENT')
        self.assertEqual(p.role(Object(wl_entity_icon_reference=True)),'HELPER')
        self.assertEqual(p.role(Object(wl_cutter_guide=True)),'HELPER')
        self.assertEqual(p.role(Object(wl_asset_template=True)),'LIBRARY')
    def test_trigger_and_utility_volumes_and_mixed_materials(self):
        self.assertEqual(p.role(Object(wl_role='BRUSH',wl_entity_pairs='[["classname","trigger_multiple"]]'),'source_hl2_windows'),'HELPER')
        brush=Object(wl_role='BRUSH');brush.data=SimpleNamespace(materials=[{'wl_texture':'tools/toolsclip'}])
        self.assertEqual(p.role(brush,'source_hl2_windows'),'HELPER')
        brush.data.materials.append({'wl_texture':'brick/wall'})
        self.assertEqual(p.role(brush,'source_hl2_windows'),'CONTENT')
        brush.wavelength_context_role='HELPER';self.assertEqual(p.role(brush),'HELPER')
