import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector,Matrix
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_face,terrain_sew,terrain_paint,primitives,scene,vmf
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True;ctx.scene.wavelength.engine='source_hl2_windows'
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
material=bpy.data.materials.new('Dirt');material['wl_texture']='nature/dirtfloor001a'
def brush(name):
    vertices,faces=primitives.box(-128,-128,-128,128,128,128);mesh=bpy.data.meshes.new(name);mesh.from_pydata([[c*.0254 for c in p] for p in vertices],[],faces);mesh.update();mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);ctx.collection.objects.link(obj);scene.mark_brush(obj)
    obj.matrix_world=Matrix.Translation(Vector((10,20,3)))@Matrix.Rotation(.6,4,'Z')@Matrix.Diagonal(Vector((1.5,.75,2.,1.)))
    return obj
def select_faces(obj,all_faces=False):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj;bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data)
    for face in bm.faces:face.select_set(all_faces)
    if not all_faces:max(bm.faces,key=lambda f:f.normal.z).select_set(True)
    bmesh.update_edit_mesh(obj.data)
source=brush('Consumed cube');name=source.name;original=[source.matrix_world@v.co for v in source.data.vertices];select_faces(source,True)
assert bpy.ops.wavelength.displacement_from_face()=={'FINISHED'}
assert name not in ctx.scene.objects
surfaces=[o for o in ctx.scene.objects if o.get('wl_terrain')];assert len(surfaces)==6
assert all(o.parent is None and o.wavelength_terrain.surface_source is None and o.get('wl_terrain_detached') for o in surfaces)
assert all(min((o.matrix_world@p-q).length for q in original)<1e-5 for o in surfaces for p in terrain_face.corners(o))
assert terrain_sew.sew(surfaces)==12
assert len(scene.export_map(ctx.scene).entities[0].brushes)==6
base=terrain_sew.frames(surfaces);point=terrain_sew.positions(surfaces[0],base[surfaces[0]])[0]
terrain_paint.network_stroke(surfaces,base,point,Vector((0,0,1)),'RAISE',1,.05,.2);terrain_sew.validate_export(surfaces[0])
print('PASS six selected cube faces become independent, paintable, sewable surfaces; backing brush removed',flush=True)
folder=Path(__file__).resolve().parents[1]/'build/terrain-detach';folder.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'independent.blend'));bpy.ops.wm.open_mainfile(filepath=str(folder/'independent.blend'))
assert len(scene.export_map(bpy.context.scene).entities[0].brushes)==6
print('PASS saved independent geometry and neighbour links need no source objects',flush=True)
ctx=bpy.context;material=bpy.data.materials['Dirt'];source=brush('Legacy orphan');select_faces(source)
orphan=terrain_face.create(ctx,independent=False)
terrain_paint.stroke(orphan,Vector(), 'RAISE',2,.2,.5)
bpy.data.objects.remove(source,do_unlink=True);ctx.view_layer.update()
terrain_face.validate_attachment(orphan)
assert orphan.get('wl_terrain_detached') and orphan.parent is None
assert len(terrain.patches(orphan))==1
terrain_paint.stroke(orphan,Vector(),'RAISE',2,.2,.5)
assert len(scene.export_map(ctx.scene).entities[0].brushes)==7
print('PASS legacy surface recovers after backing brush deletion and retains editable paint',flush=True)
