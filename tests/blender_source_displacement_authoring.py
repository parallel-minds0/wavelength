"""Native Source grids: creation, power resampling, painting, seams and duplication."""
import sys,json,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,wavelength
from mathutils import Vector,Matrix
wavelength.register()
from wavelength.source import source_displacement as sd,scene,primitives,formats,displacement,identity
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';unit=s.unit_scale
mat=bpy.data.materials.new('Transition');mat['wl_texture']='concrete/blendconcdirt003a';mat['wl_source_blend']=True;mat['wl_width']=mat['wl_height']=256
area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
def clear():
 if c.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
 for obj in list(c.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
def make(x0,y0,x1,y1,power,rotation=None):
 verts,faces=primitives.box(x0,y0,-16,x1,y1,0)
 mesh=bpy.data.meshes.new('Backing');mesh.from_pydata([Vector(v)*unit for v in verts],[],faces);mesh.update();mesh.materials.append(mat)
 source=bpy.data.objects.new('Backing',mesh);c.collection.objects.link(source);scene.mark_brush(source)
 bpy.ops.object.select_all(action='DESELECT');source.select_set(True);c.view_layer.objects.active=source
 with c.temp_override(area=area,region=region):
  bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(mesh)
  for f in bm.faces:f.select_set(False)
  max(bm.faces,key=lambda f:f.normal.z).select_set(True);bmesh.update_edit_mesh(mesh)
  assert bpy.ops.wavelength.displacement_from_face()=={'FINISHED'}
  result=c.object
  if power!=3:sd.change_power(result,power)
 if rotation:source.matrix_world=rotation
 c.view_layer.update();return result
clear();a=make(0,0,128,128,2);b=make(128,0,256,128,3)
assert len(sd.connections([a,b]))==1
# Offset the shared boundary, then sew differing powers into the same edge curve.
for v in b.data.vertices:v.co.z+=.05
b.data.update();c.view_layer.update();assert sd.sew([a,b])==1;c.view_layer.update()
pa,_,_=sd.read_surface(a);pb,_,_=sd.read_surface(b)
for i in range(9):assert (pb[i*9]-sd.sample(pa,5,1,i/8)).length<.002
old,_,_=sd.read_surface(a);sd.change_power(a,4);c.view_layer.update();new,_,_=sd.read_surface(a)
assert len(a.data.vertices)==289
for j in range(17):
 for i in range(17):assert (new[j*17+i]-sd.sample(old,5,i/16,j/16)).length<.003
sd.change_power(a,2);c.view_layer.update()
# Native raise and layer blending span shared surfaces.
point=Vector((128,64,2))*unit
assert sd.paint_stroke([a,b],point,'RAISE',80*unit,2*unit,.5)>0
sd.sew([a,b]);c.view_layer.update()
assert sd.paint_stroke([a,b],point,'TEXTURE',80*unit,0,.5)>0
assert max(d.value for d in a.data.attributes[sd.BLEND].data)>0 and max(d.value for d in b.data.attributes[sd.BLEND].data)>0
# Collision flags remain orthogonal and preserve other bits.
a.wavelength_displacement_no_physics=True;a.wavelength_displacement_no_ray=True
assert sd.info(a)['data']['flags']==10
# A rotated backing carries both domain and native grid correctly.
a.parent.matrix_world=Matrix.Rotation(.3,4,'X');c.view_layer.update()
face=scene.brush_from_object(a.parent,s.engine)[sd.info(a)['face_id']-1]
export=sd.export_surface(a,face);_,_,quad=sd.source_face(a)
points,_,_=sd.read_surface(a);decoded=displacement.grid(export.vmf['dispinfo'],quad,face.plane()[0])
assert max((p-Vector(q)).length for p,q in zip(points,decoded))<.003
# Duplicate a grid by itself: new backing, no duplicate face claims.
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);c.view_layer.objects.active=a;identity.update_ids();bpy.ops.object.duplicate();duplicate=c.object;identity.update_ids()
assert duplicate.parent!=a.parent and duplicate.data!=a.data and len(sd.surfaces(duplicate.parent))==1
scene.export_map(c.scene)
# Half-edge adjacency, including two smaller neighbors.
clear();a=make(0,0,128,128,2);b=make(128,0,256,64,3);d=make(128,64,256,128,2)
assert len(sd.connections([a,b,d]))==3
sd.sew([a,b,d]);c.view_layer.update();scene.export_map(c.scene)
# Mirrored backing brushes transpose Source rows/columns without changing shape.
a.parent.scale.x=-1;c.view_layer.update()
faces=scene.brush_from_object(a.parent,s.engine);fid=sd.info(a)['face_id']
face=sd.export_surface(a,faces[fid-1]);vs,polys=formats.brush_mesh(faces)
quad=displacement.quad(vs,polys[fid-1],face.vmf['dispinfo']['startposition'])
decoded=[Vector(p) for p in displacement.grid(face.vmf['dispinfo'],quad,face.plane()[0])]
actual,_,_=sd.read_surface(a)
assert max(min((p-q).length for q in actual) for p in decoded)<.003
# Native affine UV edits are captured, and material assignment covers one Source patch.
from wavelength.source import asset_placement
for entry in a.data.uv_layers['wavelength'].data:entry.uv.x+=.25
c.view_layer.update();face=scene.brush_from_object(a.parent,s.engine)[fid-1]
before_axes=copy.deepcopy(face.axes);face=sd.export_surface(a,face)
assert face.axes!=before_axes,'Native UV edits were ignored'
replacement=bpy.data.materials.new('Replacement');replacement['wl_texture']='brick/brickwall001a';replacement['wl_width']=replacement['wl_height']=128
asset_placement.paint(c,a,0,replacement,'SURFACE')
assert {p.material_index for p in a.data.polygons}=={len(a.data.materials)-1}
face=sd.export_surface(a,scene.brush_from_object(a.parent,s.engine)[fid-1]);assert face.texture=='brick/brickwall001a'
# Invalid topology produces an actionable error rather than corrupting a VMF.
b.data.vertices[0].co=b.data.vertices[1].co;b.data.update();c.view_layer.update()
try:sd.read_surface(b);raise AssertionError('Collapsed triangle was accepted')
except ValueError as exc:assert 'collapsed' in str(exc)
from wavelength.source import geometry_debug
problem=geometry_debug.inspect(b,c.scene)
assert problem and problem['code']=='DISPLACEMENT_INVALID'
assert len(problem['vertices'])==3,'Collapsed triangle diagnostics must select its vertices'
assert geometry_debug.inspect(a.parent,c.scene) is None,'Display-only backing mask must not report an invalid solid'
clear()
from wavelength.source import terrain
original=terrain.create(c,paintable_surface=True);original.data.materials.append(mat)
terrain.update(original);c.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');original.select_set(True);c.view_layer.objects.active=original
before_world=c.scene.get('wl_world_pairs')
assert bpy.ops.wavelength.source_displacement(action='CONVERT')=={'FINISHED'}
assert original.get('wl_exclude') and original.hide_get()
assert c.scene.get('wl_world_pairs')==before_world
assert len([o for o in c.scene.objects if o.get(sd.KEY)])==4
scene.export_map(c.scene)
print('PASS Source authoring: quad creation, power 2/3/4 resampling, raise/blend paint, mixed-power/half-edge sewing, rotation, collision flags, duplication, topology diagnostics',flush=True)
wavelength.unregister();wavelength.register();wavelength.unregister();print('PASS Source displacement registration lifecycle',flush=True)
