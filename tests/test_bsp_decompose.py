import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source.bsp_decompose import decompose,volume
from wavelength.source.geometry import validate

def voxels(cells):
    vertices=[];faces=[];lookup={}
    corners=[(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
    sides=[((0,0,-1),[0,3,2,1]),((0,0,1),[4,5,6,7]),((0,-1,0),[0,1,5,4]),((1,0,0),[1,2,6,5]),((0,1,0),[2,3,7,6]),((-1,0,0),[3,0,4,7])]
    for cell in sorted(cells):
        for delta,face in sides:
            if tuple(a+b for a,b in zip(cell,delta)) in cells:continue
            ids=[]
            for index in face:
                p=tuple(a+b for a,b in zip(cell,corners[index]))
                if p not in lookup:lookup[p]=len(vertices);vertices.append(p)
                ids.append(lookup[p])
            faces.extend([[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]])
    return vertices,faces

class BSPDecomposeTests(unittest.TestCase):
    def check_cells(self,cells,transform=lambda p:p):
        v,f=voxels(cells);v=[transform(p) for p in v]
        parts=decompose(v,f,[[v[i] for i in face] for face in f])
        for vs,fs in parts:validate(vs,fs)
        self.assertAlmostEqual(sum(volume(vs,fs) for vs,fs in parts),len(cells),places=5)
        return parts
    def test_concave_corner(self):self.assertEqual(len(self.check_cells({(0,0,0),(1,0,0),(0,1,0)})),3)
    def test_through_hole(self):self.assertEqual(len(self.check_cells({(x,y,0) for x in range(3) for y in range(3) if (x,y)!=(1,1)})),8)
    def test_disconnected_solids(self):self.assertEqual(len(self.check_cells({(0,0,0),(2,0,0)})),2)
    def test_oblique_far_from_origin(self):
        import math
        a=.43;c=math.cos(a);s=math.sin(a)
        self.check_cells({(0,0,0),(1,0,0),(0,1,0)},lambda p:(c*p[0]-s*p[1]+10000,s*p[0]+c*p[1]-20000,p[2]+30000))
    def test_complexity_failure(self):
        v,f=voxels({(0,0,0),(1,0,0),(0,1,0)})
        with self.assertRaisesRegex(ValueError,'cells'):decompose(v,f,[[v[i] for i in face] for face in f],max_cells=1)
    def test_reversed_winding(self):
        v,f=voxels({(0,0,0),(1,0,0),(0,1,0)});f=[face[::-1] for face in f]
        parts=decompose(v,f,[[v[i] for i in face] for face in f])
        self.assertAlmostEqual(sum(volume(vs,fs) for vs,fs in parts),3)
if __name__=='__main__':unittest.main()
