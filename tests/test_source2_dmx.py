import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import source2_dmx as d
from wavelength.source.source2_assets import Assets

class Source2DmxTests(unittest.TestCase):
    def mesh(self,faces=None):
        return d.polygon_mesh([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],faces or [[0,1,2,3]],[[(0,0),(1,0),(1,1),(0,1)]],['materials/test.vmat'],[0])
    def test_open_surface_roundtrip(self):
        mesh=self.mesh();result=d.read_mesh(mesh)
        self.assertEqual(result[1],[[0,1,2,3]]);self.assertEqual(result[2][0],[(0,0),(1,0),(1,1),(0,1)])
        self.assertEqual(mesh.get('edgeOppositeIndices'),[1,0,3,2,5,4,7,6])
        self.assertEqual(sum(v==-1 for v in mesh.get('edgeFaceIndices')),4)
    def test_typed_document_and_escaping(self):
        root=d.element('CMapRootElement',name=('string','mesh "quoted" \\ path'),world=('CDmePolygonMesh',self.mesh()))
        loaded=d.loads(d.dumps(root))
        self.assertEqual(loaded.get('name'),root.get('name'))
        self.assertEqual(d.read_mesh(loaded.get('world')),d.read_mesh(root.get('world')))
    def test_duplicate_or_invalid_vertex_rejected(self):
        for face in ([0,1,1],[0,1,90]):
            with self.assertRaises(ValueError):self.mesh([face])
    def test_bad_loop_rejected(self):
        mesh=self.mesh();mesh.get('edgeNextIndices')[0]=999
        with self.assertRaises(ValueError):d.read_mesh(mesh)
    def test_truncated_document_rejected(self):
        for text in ('"CMapRootElement" {','"CMapRootElement" { "x" "int"','not dmx'):
            with self.assertRaises(ValueError):d.loads(text)
    def test_native_reference_normalization(self):
        assets=object.__new__(Assets)
        self.assertEqual(assets.resolve('brick/wall'),'materials/brick/wall.vmat')
        self.assertEqual(assets.resolve('materials/brick/wall.vmat_c'),'materials/brick/wall.vmat')
        with self.assertRaises(ValueError):assets.resolve('../escape')
if __name__=='__main__':unittest.main()
