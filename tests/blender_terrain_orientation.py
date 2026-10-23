"""Regression for inward mesh winding versus Source's outward brush planes."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_face,terrain_sew as sew,terrain_paint as paint,scene,primitives,formats,vmf
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True;ctx.scene.wavelength.engine='source_hl2_windows';unit=.0254
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
material=bpy.data.materials.new('Concrete');material['wl_texture']='concrete/concretefloor001a'
def make(name,x0,x1):
    vertices,faces=primitives.box(x0,-128,-32,x1,128,0);mesh=bpy.data.meshes.new(name);mesh.from_pydata([[c*unit for c in p] for p in vertices],[],[tuple(reversed(f)) for f in faces]);mesh.update();mesh.materials.append(material)
    source=bpy.data.objects.new(name,mesh);ctx.collection.objects.link(source);scene.mark_brush(source);bpy.ops.object.select_all(action='DESELECT');source.select_set(True);ctx.view_layer.objects.active=source;bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(mesh)
    for f in bm.faces:f.select_set(False)
    face=max(bm.faces,key=lambda f:f.calc_center_median().z);assert face.normal.z<0;face.select_set(True);bmesh.update_edit_mesh(mesh)
    return terrain_face.create(ctx,independent=False)
a=make('Reversed left',-256,0);b=make('Reversed right',0,256);a.wavelength_terrain.power='2';b.wavelength_terrain.power='3';a.wavelength_terrain.amplitude=8;b.wavelength_terrain.amplitude=5
sew.sew([a,b]);base=sew.frames([a,b]);paint.network_stroke([a,b],base,Vector((0,unit*48,0)),Vector((0,0,-1)),'RAISE',2,.4,.5)
folder=Path(__file__).resolve().parents[1]/'build/terrain-orientation';folder.mkdir(exist_ok=True)
expected=[]
for obj in (a,b):
    assert obj.get('wl_terrain_reverse_facing')
    vertices,_,info=terrain.patches(obj)[0];vertices,info=terrain.export_facing(obj,vertices,info)
    expected.append(dict(name=obj.name,base=[list(obj.matrix_world@Vector(p)/unit) for p in info['base_corners']],positions=[list(obj.matrix_world@Vector(p)/unit) for p in vertices],normal=[0,0,1]))
(folder/'expected.json').write_text(json.dumps(expected),encoding='utf-8')
doc=scene.export_map(ctx.scene);assert len(doc.entities[0].brushes)==2
assert all(brush[0].plane()[0][2]>.99 for brush in doc.entities[0].brushes)
before=[a.matrix_world@v.co for v in a.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices]
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);ctx.view_layer.objects.active=a
assert bpy.ops.wavelength.terrain_flip_facing()=={'FINISHED'}
after=[obj.matrix_world@v.co for obj in [a] for v in obj.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices]
assert max((p-q).length for p,q in zip(before,after))<1e-6
sew.validate_export(a)
assert bpy.ops.wavelength.terrain_flip_facing()=={'FINISHED'}
print('PASS flip facing preserves sculpted positions and sewn joins',flush=True)
for bounds in [(-800,-800,-272,800,800,-256),(-800,-800,512,800,800,528),(-800,-800,-256,-784,800,512),(784,-800,-256,800,800,512),(-784,-800,-256,784,-784,512),(-784,784,-256,784,800,512)]:
    vertices,faces=primitives.box(*bounds);wall=[]
    for face in faces:
        f=formats.Face([list(vertices[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);wall.append(f)
    doc.entities[0].brushes.append(wall)
doc.entities[0].pairs.append(('skyname','sky_day01_01'));doc.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
(folder/'reversed-winding.vmf').write_text(vmf.write(doc),encoding='utf-8')
print('PASS reversed mesh winding exports independent surface frames instead of transposing displacement grids',flush=True)
