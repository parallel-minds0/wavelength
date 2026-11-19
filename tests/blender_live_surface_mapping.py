"""Live UI property writes change UVs and the exported brush mapping."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy
import bmesh
import wavelength
from wavelength.source import scene

wavelength.register()
ctx=bpy.context
ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength
s.auto_prepare_assets=False
s.engine='source_hl2_windows'
s.game_dir=''
s.texture='dev/dev_measuregeneric01b'
obj=ctx.object
scene.mark_brush(obj)
material=bpy.data.materials.new('Live mapping')
material['wl_texture']=s.texture
material['wl_width']=128
material['wl_height']=64
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
assert obj.data.uv_layers.active.name=='wavelength'
assert obj.data.uv_layers['wavelength'].active_render
assert s.live_mapping_adjustment
bpy.ops.object.mode_set(mode='EDIT')
ctx.scene.tool_settings.mesh_select_mode=(False,False,True)
bm=bmesh.from_edit_mesh(obj.data)
for face in bm.faces:face.select_set(False)
face=next(iter(bm.faces))
face.select_set(True)
bm.faces.active=face
bmesh.update_edit_mesh(obj.data)
ids=bm.faces.layers.int['wl_face_id']
selected=str(face[ids])

def snapshot():
    layer=bm.loops.layers.uv['wavelength']
    return {str(f[ids]):[tuple(loop[layer].uv) for loop in f.loops] for f in bm.faces}

original=snapshot()
records=json.loads(obj.data['wl_faces'])
for shift in (8,24,40):
    s.adjust_shift_u=shift
    uv=snapshot()
    assert all(abs(a[0]-b[0]-shift/128)<1e-6 and a[1]==b[1]
               for a,b in zip(uv[selected],original[selected]))
    assert all(uv[key]==original[key] for key in uv if key!=selected)
assert ctx.mode=='EDIT_MESH' and face.select
changed=json.loads(obj.data['wl_faces'])
assert changed[selected]['axes'][0][3]==40
assert all(changed[key]==records[key] for key in records if key!=selected)
s.adjust_texture_rotation=30
s.adjust_texture_scale_v=2
assert snapshot()[selected]!=uv[selected]
s.adjust_texture_scale_v=0
assert s.texture_scale_v==2
assert all(snapshot()[key]==original[key] for key in uv if key!=selected)
bpy.ops.object.mode_set(mode='OBJECT')
assert any(face.axes[0][3]==40 for face in scene.brush_from_object(obj,s.engine))
s.adjust_shift_v=12
assert all(face.axes[1][3]==12 for face in scene.brush_from_object(obj,s.engine))
s.live_mapping_adjustment=False
s.adjust_shift_u=100
assert any(face.axes[0][3]==40 for face in scene.brush_from_object(obj,s.engine))
s.live_mapping_adjustment=True
s.shift_u=0
assert any(face.axes[0][3]==40 for face in scene.brush_from_object(obj,s.engine))
s.texture=''
s.shift_u=17
s.shift_v=29
obj.data.uv_layers.active=obj.data.uv_layers['UVMap']
assert bpy.ops.wavelength.apply_texture(mapping_only=True)=={'FINISHED'}
assert obj.data.uv_layers.active.name=='wavelength'
assert all(face.axes[0][3]==17 and face.axes[1][3]==29 and face.texture==material['wl_texture']
           for face in scene.brush_from_object(obj,s.engine))
# Edit Mode paint can leave a material slot without a serialized face record.
obj.data['wl_faces']='{}'
bpy.ops.object.mode_set(mode='EDIT')
s.adjust_shift_u=25
assert any(record['projection'][0]==8 for record in json.loads(obj.data['wl_faces']).values())
bpy.ops.object.mode_set(mode='OBJECT')

s.engine='source2_cs2_windows'
bpy.ops.mesh.primitive_cube_add()
mesh=ctx.object.data
ordinary=mesh.uv_layers.active
layer=mesh.uv_layers.new(name='wavelength',do_init=True)
mesh.uv_layers.active=ordinary
original_ordinary=[tuple(loop.uv) for loop in ordinary.data]
before=[tuple(loop.uv) for loop in layer.data]
area=next(area for area in ctx.screen.areas if area.type=='DOPESHEET_EDITOR')
area.type='FILE_BROWSER'
with ctx.temp_override(area=area):
    s.adjust_shift_u=41
    s.adjust_shift_v=37
assert mesh.uv_layers.active.name=='wavelength' and layer.active_render
assert [tuple(loop.uv) for loop in ordinary.data]==original_ordinary
assert all(abs(loop.uv.x-u-.25)<1e-6 and abs(loop.uv.y-v+.125)<1e-6
           for loop,(u,v) in zip(layer.data,before))
s.live_mapping_adjustment=False
s.adjust_shift_u=0
s.adjust_shift_v=0
assert bpy.ops.wavelength.apply_texture(mapping_only=True)=={'FINISHED'}
native_before=[tuple(loop.uv) for loop in layer.data]
s.adjust_shift_u=16
s.adjust_shift_v=8
assert bpy.ops.wavelength.apply_texture(mapping_only=True)=={'FINISHED'}
assert all(abs(loop.uv.x-u-.25)<1e-6 and abs(loop.uv.y-v+.125)<1e-6
           for loop,(u,v) in zip(layer.data,native_before))
print('PASS live field writes update selected brush faces and exported axes, whole objects, and native UVs',flush=True)
