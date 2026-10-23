"""Native edit-mesh coordinates update projection without leaving Edit Mode."""
import sys,json,traceback
from pathlib import Path
from dataclasses import asdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import editor,scene
ctx=bpy.context;ctx.preferences.use_preferences_save=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength_context.preparation=False
s=ctx.scene.wavelength;s.engine='blender';s.live_texture_reproject=True
ctx.scene.tool_settings.use_snap=False
if ctx.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add();obj=ctx.object;scene.mark_brush(obj)
material=bpy.data.materials.new('Projection fixture');material['wl_width']=128;material['wl_height']=64
obj.data.materials.append(material)
editor.apply_uv(obj,'blender')
bpy.ops.object.mode_set(mode='EDIT')
assert not editor.apply_edit_uv(obj),'Entering Edit Mode must preserve default face-axis projection'
bpy.ops.object.mode_set(mode='OBJECT')
records={str(i):asdict(face) for i,face in zip(sorted(d.value for d in obj.data.attributes['wl_face_id'].data),scene.brush_from_object(obj,'blender'))}
for record in records.values():record['axes']=[[1,0,0,7],[0,1,0,-3]];record['projection']=[0,0,0,2,.5]
obj.data['wl_faces']=json.dumps(records);saved_records=obj.data['wl_faces']
editor.apply_uv(obj,'blender')
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(obj.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
for vertex in bm.verts:vertex.select_set(False)
bm.verts[0].select_set(True);bmesh.update_edit_mesh(obj.data)
selection=[v.select for v in bm.verts];editor._live_tick()
uv=bm.loops.layers.uv['wavelength'];old={(face.index,i):tuple(loop[uv].uv) for face in bm.faces for i,loop in enumerate(face.loops)}
bm.verts[0].co+=Vector((.37,.23,.19));bmesh.update_edit_mesh(obj.data)
editor._live_tick()
bm=bmesh.from_edit_mesh(obj.data)
assert ctx.mode=='EDIT_MESH' and [v.select for v in bm.verts]==selection
assert obj.data['wl_faces']==saved_records
changed=0
for face in bm.faces:
    for i,loop in enumerate(face.loops):
        p=obj.matrix_world@loop.vert.co/obj.get('wl_unit_meters',1.)
        expected=((p.x/2+7)/128,1-(p.y/.5-3)/64)
        assert all(abs(loop[uv].uv[j]-expected[j])<1e-6 for j in (0,1))
        changed+=tuple(loop[uv].uv)!=old[face.index,i]
assert changed>0
s.live_texture_reproject=False;editor._live_tick()
old=[tuple(loop[uv].uv) for face in bm.faces for loop in face.loops]
bm.verts[0].co.x+=.2;bmesh.update_edit_mesh(obj.data);editor._live_tick()
assert old==[tuple(loop[uv].uv) for face in bm.faces for loop in face.loops]
s.live_texture_reproject=True;editor._live_tick()
assert old!=[tuple(loop[uv].uv) for face in bm.faces for loop in face.loops]
assert not editor.apply_edit_uv(obj),'Unchanged geometry must not repeatedly dirty UVs'
print('PASS live BMesh projection, transient non-planar faces, preserved selection/records, disable/reenable and feedback guard',flush=True)

if not bpy.app.background:
    area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
    def native_move():
        try:
            with ctx.temp_override(area=area,region=region):
                bpy.ops.ed.undo_push(message='Before native vertex transform')
                bpy.ops.transform.translate(value=(.41,.17,0),orient_type='GLOBAL')
            bpy.app.timers.register(check_timer,first_interval=.4)
        except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
    def check_timer():
        try:
            mesh=bmesh.from_edit_mesh(obj.data);layer=mesh.loops.layers.uv['wavelength']
            for face in mesh.faces:
                for loop in face.loops:
                    p=obj.matrix_world@loop.vert.co/obj.get('wl_unit_meters',1.)
                    assert abs(loop[layer].uv.x-(p.x/2+7)/128)<1e-6
                    assert abs(loop[layer].uv.y-(1-(p.y/.5-3)/64))<1e-6
            assert ctx.mode=='EDIT_MESH' and obj.data['wl_faces']==saved_records
            print('PASS real native transform and automatic live timer projection while remaining in Edit Mode',flush=True)
        except Exception:traceback.print_exc()
        finally:bpy.ops.wm.quit_blender()
    bpy.app.timers.register(native_move,first_interval=.4)
