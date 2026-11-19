import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import unittest
from types import SimpleNamespace as NS
from wavelength.source.edit_safety import topology_modal_active

class EditSafetyTests(unittest.TestCase):
    def context(self,*names):
        return NS(window_manager=NS(windows=[NS(modal_operators=[NS(bl_idname=n) for n in names])]))
    def test_native_topology_and_slide(self):
        for name in ('MESH_OT_loopcut_slide','MESH_OT_bevel','TRANSFORM_OT_edge_slide','TRANSFORM_OT_vert_slide'):
            self.assertTrue(topology_modal_active(self.context(name)))
    def test_simple_transforms_remain_live(self):
        self.assertFalse(topology_modal_active(self.context('TRANSFORM_OT_translate','TRANSFORM_OT_resize','WAVELENGTH_OT_click_place')))
    def test_all_windows_and_empty_context(self):
        self.assertFalse(topology_modal_active(NS()))
        self.assertTrue(topology_modal_active(NS(window_manager=NS(windows=[NS(modal_operators=[]),NS(modal_operators=[NS(bl_idname='MESH_OT_extrude_region_move')])]))))

if __name__=='__main__':unittest.main()
