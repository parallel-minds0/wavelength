import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import primitives,profile_store,geometry,formats,vmf,asset_index
P=dict(radius=128,thickness=32,depth=64,angle=180,segments=8,rings=6,steps=8,rise=16,run=32,width=128,landing=64,direction=0)
class FoundationTests(unittest.TestCase):
 def test_primitives_convex_and_closed(self):
  for kind in ('ARCH','STAIRS','SPHERE'):
   for angle in (45,90,180,270,360):
    for v,f in primitives.generate(kind,{**P,'angle':angle}):geometry.validate(v,[list(x) for x in f])
 def test_stairs_dimensions(self):
  parts=primitives.generate('STAIRS',P);self.assertEqual(len(parts),9)
  v=parts[-1][0];self.assertEqual(max(x[2] for x in v),128);self.assertEqual(max(x[1] for x in v),320)
 def test_invalid_primitives(self):
  for kind,change in [('ARCH',{'thickness':129}),('SPHERE',{'subdivisions':2}),('STAIRS',{'rise':0})]:
   with self.assertRaises(ValueError):primitives.generate(kind,{**P,**change})
 def test_profiles_persist_rename_stable_id(self):
  with tempfile.TemporaryDirectory() as d:
   store=profile_store.Store(d);row=store.save({'name':'My game','settings':{'engine':'quake'}});identity=row['id'];row['name']='Renamed';store.save(row)
   self.assertEqual(profile_store.Store(d).get(identity)['name'],'Renamed');self.assertEqual(len(store.all()),1);store.remove(identity);self.assertEqual(store.all(),[])
 def test_legacy_project_migration(self):
  value=profile_store.validate({'schema_version':1,'engine':'quake','grid_step':'16'})
  self.assertEqual(value['schema'],1);self.assertEqual(value['settings']['engine'],'quake')
 def test_profile_invalid(self):
  for settings in ({'engine':'nope'},{'engine':'quake','unit_scale':float('nan')},{'engine':'quake','wrapper':'{}'}):
   with self.assertRaises(ValueError):profile_store.validate({'name':'X','settings':settings})
 def test_asset_identity_and_cache(self):
  self.assertEqual(asset_index.identity('quake','MATERIAL','STONE'),asset_index.identity('quake','MATERIAL','stone'))
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'cache.json';rows=[asset_index.record('quake','foo','MATERIAL')]
   self.assertTrue(asset_index.write_index(p,rows));self.assertFalse(asset_index.write_index(p,rows))
