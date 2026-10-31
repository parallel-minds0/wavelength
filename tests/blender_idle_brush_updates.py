"""Idle maps do not poll every brush; dirty native objects still update UVs."""
import sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import editor,scene,identity,object_index
c=bpy.context;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
s=c.scene.wavelength;s.engine='blender';s.live_texture_reproject=True;c.scene.tool_settings.use_snap=False
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
objects=[]
for i in range(100):
 bpy.ops.mesh.primitive_cube_add(location=(i*3,0,0));obj=c.object;scene.mark_brush(obj);editor.apply_uv(obj,'blender');objects.append(obj)
c.view_layer.update();editor._live_tick();c.view_layer.update();editor._live_tick()
with patch.object(editor,'_brush_state',wraps=editor._brush_state) as state:
 for i in range(10):editor._live_tick()
 assert state.call_count==0,('Idle full-map scanning',state.call_count)
obj=objects[12];before=[tuple(v.uv) for v in obj.data.uv_layers['wavelength'].data]
obj.location.x+=.25;c.view_layer.update()
with patch.object(editor,'_brush_state',wraps=editor._brush_state) as state:
 editor._live_tick();assert state.call_count==1,state.call_count
assert before!=[tuple(v.uv) for v in obj.data.uv_layers['wavelength'].data]
identity.update_ids();oldid=obj['wl_id']
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);c.view_layer.objects.active=obj
bpy.ops.object.duplicate();duplicate=c.object;c.view_layer.update()
assert duplicate['wl_id']!=oldid
one=object_index.matching('test',c.scene,lambda o:o.get('wl_role')=='BRUSH',force=True)
assert len(one)==101
bpy.data.objects.remove(duplicate,do_unlink=True)
two=object_index.matching('test',c.scene,lambda o:o.get('wl_role')=='BRUSH')
assert len(two)==100
print('PASS idle brush polling eliminated; one dirty object reprojects; native duplication and role indexes remain correct',flush=True)
