"""Imported native displacement geometry and metadata survive an untouched export."""
from pathlib import Path
import sys,copy,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import vmf,scene,displacement,source_displacement as sd,formats
c=bpy.context;s=c.scene.wavelength;s.engine='source_hl2_windows'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_displacement import fixture
doc,face_index=fixture(3)
brush=doc.entities[0].brushes[0]
small=formats.Map([formats.Entity([('classname','worldspawn')],[brush])])
collection=scene.import_map(c.scene,small)
surfaces=[o for o in collection.objects if o.get(sd.KEY)]
assert surfaces
for obj in surfaces:
 original=sd.info(obj)['data'];points,alpha,tags=sd.read_surface(obj)
 data=sd.export_surface(obj,copy.deepcopy(brush[sd.info(obj)['face_id']-1])).vmf['dispinfo']
 assert displacement.pairs(data)==displacement.pairs(original),(data['startposition'],original['startposition'])
 assert obj.data.uv_layers.get('wavelength')
 assert all(p.use_smooth for p in obj.data.polygons)
 # Native edits modify a grid vertex and preserve both sideways and height changes.
 obj.data.vertices[6].co+=Vector((.1,.2,.3))*obj['wl_unit_meters'];obj.data.update();c.view_layer.update()
 face=copy.deepcopy(brush[sd.info(obj)['face_id']-1]);data=sd.export_surface(obj,face).vmf['dispinfo']
 _,_,quad=sd.source_face(obj)
 result=displacement.grid(data,quad,face.plane()[0])
 current,_,_=sd.read_surface(obj)
 assert max((Vector(a)-b).length for a,b in zip(result,current))<.002
 obj.data.attributes[sd.BLEND].data[0].value=.5;obj.data.attributes[sd.TAGS].data[0].value=0;obj.data.update();c.view_layer.update()
 data=sd.export_surface(obj,copy.deepcopy(brush[sd.info(obj)['face_id']-1])).vmf['dispinfo']
 assert abs(data['alphas'][0][0]-127.5)<.001 and data['triangle_tags'][0][0]==0
exported=scene.export_map(c.scene)
assert len(exported.entities[0].brushes)==1,'Original backing brush must not be split or replaced'
assert len(vmf.parse(vmf.write(exported)).entities[0].brushes)==1
print('PASS native displacement: original backing, untouched metadata, native 3D edits, alpha/tags, Source units, UVs and scene/VMF export',flush=True)
