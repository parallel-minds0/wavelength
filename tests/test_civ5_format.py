import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import civ5_format as fmt
class Civ5Tests(unittest.TestCase):
 def fixture(self,version=12):
  blocks=[b'TERRAIN_GRASS\0TERRAIN_DESERT\0',b'FEATURE_FOREST\0',b'',b'RESOURCE_IRON\0',b'opaque-mod\0',b'Test\0',b'Description\0']
  header=struct.pack('<BIIBI7I',version|128,2,1,2,4,*map(len,blocks))+b''.join(blocks)
  if version>=11:header+=struct.pack('<I',12)+b'WORLDSIZE_1\0'
  return header+bytes([0,255,255,192,0,1,255,0])*2+b'unknown scenario data\x00\xff'
 def test_lossless_versions(self):
  for version in (7,9,10,11,12):
   raw=self.fixture(version);m=fmt.parse(raw);self.assertEqual(m.write({0:m.tile(0),1:m.tile(1)}),raw)
 def test_cell_only_patch_preserves_scenario_and_header(self):
  raw=self.fixture();m=fmt.parse(raw);tile=list(m.tile(1));tile[0]=1;tile[4]=2;out=m.write({1:tile})
  self.assertEqual([i for i,(a,b) in enumerate(zip(raw,out)) if a!=b],[m.offset+8,m.offset+12])
 def test_bad_indices_and_truncation(self):
  raw=self.fixture();m=fmt.parse(raw)
  with self.assertRaises(ValueError):m.write({2:m.tile(0)})
  tile=list(m.tile(0));tile[0]=200
  with self.assertRaises(ValueError):m.write({0:tile})
  with self.assertRaises(ValueError):fmt.parse(raw[:m.offset+8])
  with self.assertRaises(ValueError):fmt.parse(b'SQLite format 3\0')

