import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import profiles

class MeshProfileTests(unittest.TestCase):
 def test_persisted_enum_numbers_do_not_move(self):
  previous=('blender','quake','goldsrc','goldsrc_windows','goldsrc_linux','goldsrc_linux_steam','source_hl2_linux','source_hl2_windows','source_gmod_windows')
  self.assertEqual(tuple(row[0] for row in profiles.PROFILE_ITEMS[:9]),previous)
  self.assertEqual([row[3] for row in profiles.PROFILE_ITEMS[:9]],list(range(9)))
 def test_mesh_profiles_have_no_bsp_or_entity_pipeline(self):
  for engine in ('godot4','source2_cs2_windows'):
   self.assertTrue(profiles.is_mesh_export(engine));self.assertFalse(profiles.requires_convex_brushes(engine))
   self.assertFalse(profiles.get(engine)['entities']);self.assertEqual(profiles.get(engine)['stages'],[])
   self.assertFalse(profiles.is_source(engine));self.assertFalse(profiles.is_goldsrc(engine))
 def test_godot_grid_falls_back_to_metric(self):
  settings=SimpleNamespace(engine='godot4',grid_mode='ENGINE',metric_grid_step=.5,grid_subdivisions=0)
  self.assertEqual(profiles.display_grid(settings),(.5,10));self.assertIsNone(profiles.active_grid_step_meters(settings))
 def test_cs2_grid_uses_physical_source_units(self):
  settings=SimpleNamespace(engine='source2_cs2_windows',grid_mode='ENGINE',grid_step='16',unit_scale=.0254,grid_subdivisions=0)
  spacing,count=profiles.display_grid(settings)
  self.assertAlmostEqual(spacing,.4064);self.assertEqual(count,8)
if __name__=='__main__':unittest.main()
