import unittest
from types import SimpleNamespace
from addon.wavelength.source import profiles

class GridProfileTests(unittest.TestCase):
    def settings(self,**kw):
        return SimpleNamespace(**dict({'engine':'source_hl2_linux','grid_mode':'ENGINE','grid_step':'32','unit_scale':.0254,'grid_subdivisions':0,'metric_grid_step':1.0},**kw))
    def test_engine_subdivision_tracks_parent(self):
        for step in (1,16,32,256):
            parent,count=profiles.display_grid(self.settings(grid_step=str(step)))
            self.assertAlmostEqual(parent/count,step*.0254/8)
    def test_blender_profile_uses_meter_not_engine_scale(self):
        self.assertEqual(profiles.display_grid(self.settings(engine='blender')),(1.0,10))
    def test_metric_mode_and_custom_subdivisions(self):
        self.assertEqual(profiles.display_grid(self.settings(grid_mode='BLENDER',metric_grid_step=.5,grid_subdivisions=5)),(.5,5))
    def test_custom_engine_units(self):
        self.assertEqual(profiles.display_grid(self.settings(unit_scale=.01,grid_subdivisions=4)),(.32,4))
