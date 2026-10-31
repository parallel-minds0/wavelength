import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import displacement as d,vmf,formats,primitives
from wavelength.source.geometry import validate

def fixture(power=3,axis=2,corner=0):
    vertices,polygons=primitives.box(0,0,-16,128,128,0)
    if axis==0:vertices=[(z,y,-x) for x,y,z in vertices]
    elif axis==1:vertices=[(x,z,-y) for x,y,z in vertices]
    brush=[]
    for triplet,n,distance in validate(vertices,polygons):
        f=formats.Face([list(vertices[i]) for i in triplet[::-1]],'dev/dev_measuregeneric01b',[11,-7,0,.5,.25])
        f.axes=formats.quake_axes(n,f.projection);brush.append(f)
    index=max(range(len(brush)),key=lambda i:brush[i].plane()[0][axis]);face=brush[index]
    verts,polys=formats.brush_mesh(brush);quad=[verts[i] for i in polys[index]];quad=quad[corner:]+quad[:corner]
    size=2**power+1;n=face.plane()[0]
    data={'power':power,'startposition':list(quad[0]),'flags':14,'elevation':7,'subdiv':1,
          'normals':[list(n)*size for _ in range(size)],'distances':[[i+j*3 for i in range(size)] for j in range(size)],
          'offsets':[[c for i in range(size) for c in (i*.2,j*.3,.5)] for j in range(size)],
          'offset_normals':[list(n)*size for _ in range(size)],'alphas':[[i*255/(size-1) for i in range(size)] for _ in range(size)],
          'triangle_tags':[[9 if i%3 else 0 for i in range(2*(size-1))] for _ in range(size-1)],'allowed_verts':[-1]*9+[123]}
    face.vmf={'id':'123','lightmapscale':'32','smoothing_groups':'0','dispinfo':data}
    return formats.Map([formats.Entity([('classname','worldspawn')],[brush])]),index

class DisplacementTests(unittest.TestCase):
    def test_powers_planes_corners_and_metadata(self):
        for power in (2,3,4):
            for axis in (0,1,2):
                for corner in range(4):
                    doc,index=fixture(power,axis,corner);brush=doc.entities[0].brushes[0];face=brush[index];data=face.vmf['dispinfo']
                    verts,polys=formats.brush_mesh(brush);quad=d.quad(verts,polys[index],data['startposition'])
                    points=d.grid(data,quad,face.plane()[0]);size=2**power+1
                    self.assertEqual(len(points),size*size)
                    for j,i in ((0,0),(size-1,0),(0,size-1),(size//2,size//2)):
                        base=d.base(quad,i/(size-1),j/(size-1));n=face.plane()[0]
                        expected=[base[k]+n[k]*(7+i+j*3)+(i*.2,j*.3,.5)[k] for k in range(3)]
                        for a,b in zip(points[j*size+i],expected):self.assertAlmostEqual(a,b,places=6)
                    actual=vmf.parse(vmf.write(doc)).entities[0].brushes[0][index].vmf['dispinfo']
                    self.assertEqual(d.pairs(data),d.pairs(actual))

    def test_optional_fields_and_extensions(self):
        doc,index=fixture(2);rows=d.pairs(doc.entities[0].brushes[0][index].vmf['dispinfo'])
        rows=[(k,[] if k=='triangle_tags' else v) for k,v in rows if k not in {'offsets','offset_normals'}]
        rows.extend([('smoothing_angle','45'),('future_extension',[('do_not_drop','value')])])
        parsed=d.parse(rows);self.assertEqual(parsed['triangle_tags'],[])
        out=d.pairs(parsed);self.assertNotIn('offsets',dict(out));self.assertEqual(dict(out)['future_extension'],[('do_not_drop','value')])
        self.assertEqual(d.pairs(d.parse(out)),out)

    def test_malformed_grids(self):
        doc,index=fixture(2);rows=d.pairs(doc.entities[0].brushes[0][index].vmf['dispinfo'])
        for mutation in ('power','length','nan','missing','start'):
            bad=copy.deepcopy(rows)
            if mutation=='power':bad=[(k,'8' if k=='power' else v) for k,v in bad]
            if mutation=='length':dict(bad)['distances'][0]=('row0','0 0')
            if mutation=='nan':dict(bad)['normals'][0]=('row0','nan '*15)
            if mutation=='missing':bad=[(k,v) for k,v in bad if k!='normals']
            if mutation=='start':bad=[(k,'[0 1]' if k=='startposition' else v) for k,v in bad]
            with self.assertRaises(ValueError,msg=mutation):d.parse(bad)
