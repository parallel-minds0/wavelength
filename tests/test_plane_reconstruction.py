"""Numerical reconstruction must preserve thin edges and shared cone apices."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import formats,geometry


class PlaneReconstructionTests(unittest.TestCase):
    def test_thin_wedge_keeps_distinct_vertices(self):
        points=[
            [(3278,2487,-9768),(3330,2559,-9768),(3466,2453,-9768)],
            [(3466,2453,-9816),(3330,2559,-9816),(3278,2487,-9768)],
            [(3330,2559,-9816),(3466,2453,-9816),(3466,2453,-9768)],
            [(3330,2559,-9768),(3278,2487,-9768),(3330,2559,-9816)],
            [(3466,2453,-9816),(3278.01,2487,-9768),(3466,2453,-9768)],
        ]
        faces=[formats.Face(p,'test',[0,0,0,1,1]) for p in points]
        planes=[f.plane() for f in faces];before=list(planes)
        vertices,polygons=geometry.from_planes(planes)
        self.assertEqual(planes,before)
        self.assertEqual(len(vertices),6)
        self.assertEqual(len(polygons),5)
        geometry.validate(vertices,polygons)
        nearest=min(geometry.length(geometry.sub(a,b)) for i,a in enumerate(vertices) for b in vertices[i+1:])
        self.assertLess(nearest,.002)

    def test_many_faces_share_one_apex(self):
        apex=(12768,13536,-6144)
        ring=[(12768+round(224*math.cos(-i*math.tau/24)),13536+round(224*math.sin(-i*math.tau/24)),-6384) for i in range(24)]
        faces=[formats.Face([ring[2],ring[1],ring[0]],'test',[0,0,0,1,1])]
        faces.extend(formats.Face([apex,ring[i],ring[(i+1)%24]],'test',[0,0,0,1,1]) for i in range(24))
        vertices,polygons=formats.brush_mesh(faces)
        self.assertEqual(len(vertices),25)
        self.assertEqual(len(polygons),25)
        self.assertEqual(sum(geometry.length(geometry.sub(v,apex))<geometry.TOLERANCE for v in vertices),1)
        geometry.validate(vertices,polygons)

    def test_unbounded_input_still_rejected(self):
        with self.assertRaises(geometry.BrushError):
            geometry.from_planes([((1,0,0),1),((-1,0,0),1),((0,1,0),1),((0,-1,0),1)])


if __name__=='__main__':unittest.main()
