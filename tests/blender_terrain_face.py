import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector,Matrix
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_face,terrain_paint,scene,primitives,formats,vmf
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
ctx.scene.wavelength.engine='source_gmod_windows'
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
unit=.0254
material=bpy.data.materials.new('blend');material['wl_texture']='concrete/blendconcdirt003a'
material['wl_source_blend']=True

def brush(name,transform=None,skew=False):
    vertices,faces=primitives.box(-128,-128,-32,128,128,0)
    if skew:vertices=[(x*(.7 if y>0 else 1),y,z) for x,y,z in vertices]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([Vector(v)*unit for v in vertices],[],faces);mesh.update();mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);ctx.collection.objects.link(obj);scene.mark_brush(obj)
    if transform:obj.matrix_world=transform
    return obj

def attach(obj,axis):
    if ctx.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data)
    for face in bm.faces:face.select_set(False)
    selected=max(bm.faces,key=lambda f:f.normal.dot(Vector(axis)));selected.select_set(True);bmesh.update_edit_mesh(obj.data)
    result=bpy.ops.wavelength.displacement_from_face(independent=False);assert result=={'FINISHED'},result
    return ctx.object

source=brush('floor');data=[v.co.copy() for v in source.data.vertices];faces=[list(p.vertices) for p in source.data.polygons]
obj=attach(source,(0,0,1));assert obj.get('wl_terrain') and obj.parent==source
assert all((a-b.co).length<1e-8 for a,b in zip(data,source.data.vertices));assert faces==[list(p.vertices) for p in source.data.polygons]
ctx.view_layer.update();evaluated=source.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh();assert len(mesh.polygons)==5;evaluated.to_mesh_clear()
terrain_paint.stroke(obj,Vector((0,0,0)),'RAISE',2,.25,1)
terrain_paint.stroke(obj,Vector((0,0,0)),'TEXTURE',2,.25,.8)
obj.wavelength_terrain.flat_preview=True
doc=scene.export_map(ctx.scene);assert len(doc.entities[0].brushes)==1 and len(doc.entities[0].brushes[0])==6
disps=[f for f in doc.entities[0].brushes[0] if f.vmf and f.vmf.get('dispinfo')];assert len(disps)==1
disp=disps[0].vmf['dispinfo'];assert max(x for row in disp['distances'] for x in row)>1
assert max(x for row in disp['alphas'] for x in row)>1
assert abs(disp['startposition'][2])<1e-4,'Base plane must stay on original face while painting'
print('PASS attached displacement preserves brush, hides only viewport face, exports one original solid with paint',flush=True)

# Vertical face on same brush, sloped transformed brush and a tapered convex quad.
vertical=attach(source,(1,0,0));terrain_paint.stroke(vertical,Vector((0,0,0)),'RAISE',1,.05,.5)
slope=brush('slope',Matrix.Translation(Vector((12,0,2)))@Matrix.Rotation(.5,4,'Y'))
sloped=attach(slope,(0,0,1));terrain_paint.stroke(sloped,Vector((0,0,0)),'RAISE',2,.2,.5)
taper=brush('taper',Matrix.Translation(Vector((-12,0,0))),True);tapered=attach(taper,(0,0,1));terrain_paint.stroke(tapered,Vector((0,0,0)),'RAISE',2,.1,.5)
for target in (obj,vertical,sloped,tapered):
    patches=terrain.patches(target);assert len(patches)==1 and len(patches[0][0])==81
    for u,v in ((0,0),(1,0),(1,1),(0,1),(.3,.8)):
        uv=terrain_face.parameters(target,terrain_face.position(target,u,v));assert abs(uv[0]-u)<1e-5 and abs(uv[1]-v)<1e-5
doc=scene.export_map(ctx.scene);assert len(doc.entities[0].brushes)==4
assert sum(bool(f.vmf and f.vmf.get('dispinfo')) for b in doc.entities[0].brushes for f in b)==4
print('PASS multiple attached faces, vertical/sloped surfaces and convex tapered quads',flush=True)

# Finalization keeps the attachment and the original base plane.
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
assert bpy.ops.wavelength.terrain_finalize()=={'FINISHED'}
assert obj['wl_procedural_state']=='FINALIZED';assert len(terrain.patches(obj))==1
source.location.z+=unit*16;ctx.view_layer.update()
doc=scene.export_map(ctx.scene)
assert len(doc.entities[0].brushes)==4
print('PASS finalized displacement attachment and parent movement',flush=True)

folder=Path(__file__).resolve().parents[1]/'build/terrain-face';folder.mkdir(exist_ok=True)
for bounds in [(-1000,-800,-272,1000,800,-256),(-1000,-800,512,1000,800,528),(-1000,-800,-256,-984,800,512),(984,-800,-256,1000,800,512),(-984,-800,-256,984,-784,512),(-984,784,-256,984,800,512)]:
    vertices,faces=primitives.box(*bounds);wall=[]
    for face in faces:
        f=formats.Face([list(vertices[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);wall.append(f)
    doc.entities[0].brushes.append(wall)
doc.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
doc.entities[0].pairs.append(('skyname','sky_day01_01'))
(folder/'brush-face.vmf').write_text(vmf.write(doc),encoding='utf-8')

# Invalid source topology is rejected, and deleting the attachment restores viewport face.
face=next(p for p in taper.data.polygons if taper.data.attributes['wl_face_id'].data[p.index].value==tapered['wl_terrain_face_id'])
taper.data.vertices[face.vertices[0]].co.x+=.1
try:scene.export_map(ctx.scene)
except ValueError as exc:assert 'changed' in str(exc)
else:raise AssertionError('Changed source face accepted')
bpy.data.objects.remove(vertical,do_unlink=True);terrain_face.sync_masks(ctx.scene)
assert sum(d.value for d in source.data.attributes['wl_displacement_surface'].data)==1
print('PASS stale attachment rejected and deleted attachment restores brush face',flush=True)
# Save/reopen verifies the source pointer, face identity and node graphs persist.
taper.data.vertices[face.vertices[0]].co.x-=.1
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'brush-face.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'brush-face.blend'))
ctx=bpy.context
doc=scene.export_map(ctx.scene)
assert len(doc.entities[0].brushes)==3
assert sum(bool(f.vmf and f.vmf.get('dispinfo')) for b in doc.entities[0].brushes for f in b)==3
print('PASS saved brush-face ownership and attachment reload',flush=True)
addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
print('PASS face-displacement addon reload',flush=True)
