"""Locators must identify the same geometry rejected by the export validator."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source.geometry_diagnostics import problem
V=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
F=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
class GeometryDiagnosticsTests(unittest.TestCase):
 def test_valid_solid_has_no_problem(self):self.assertIsNone(problem(V,F))
 def test_exact_coincident_group_and_nearby_distinction(self):
  p=problem(V+[V[0],V[0]],F);self.assertEqual(p['code'],'DUPLICATE_VERTEX');self.assertEqual(p['vertices'],[0,8,9])
  p=problem(V+[(-.999999,-1,-1)],F);self.assertEqual(p['code'],'LOOSE_VERTEX');self.assertEqual(p['vertices'],[8])
 def test_boundary_edges_are_localized(self):
  p=problem(V,F[1:]);self.assertEqual(p['code'],'NONMANIFOLD');self.assertEqual(set(map(tuple,p['edges'])),{(0,1),(1,2),(2,3),(0,3)})
 def test_nonplanar_face_is_localized(self):
  v=list(V);v[6]=(1,1,1.3);p=problem(v,F);self.assertEqual(p['code'],'NONPLANAR_FACE');self.assertIn(1,p['faces'])
 def test_invalid_coordinates_remain_identifiable(self):
  v=list(V);v[2]=(float('nan'),1,1);p=problem(v,F);self.assertEqual(p['code'],'NONFINITE_COORDINATE');self.assertEqual(p['vertices'],[2])
if __name__=='__main__':unittest.main()
