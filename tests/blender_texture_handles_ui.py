"""Drive the face gizmos with real Blender viewport events."""
from pathlib import Path
import traceback

fixture=Path(__file__).with_name('blender_texture_layout.py')
exec(compile(fixture.read_text().split('reference=')[0],str(fixture),'exec'))
from mathutils import Quaternion

context.preferences.use_preferences_save=False
context.preferences.view.show_splash=False
context.workspace['wl_layout_ready']=True
context.workspace['wl_system_tree_layout_v1']=True
destination.select_set(False)
bm.faces.active=source
bmesh.update_edit_mesh(obj.data)
context.scene.wl_show_texture_handles=True
window=context.window
area=next(area for area in context.screen.areas if area.type=='VIEW_3D')
region=next(region for region in area.regions if region.type=='WINDOW')
view=area.spaces.active.region_3d
view.view_rotation=Quaternion((1,0,0,0))
view.view_perspective='ORTHO'
view.view_distance=6
view.view_location=(0,0,0)
original=[loop[layer].uv.copy() for loop in source.loops]
original_records=obj.data['wl_faces']
with context.temp_override(area=area,region=region):
    bpy.ops.ed.undo_push(message='Before texture gizmo')


def send(kind,value,distance=0,handle=0,**modifiers):
    with context.temp_override(area=area,region=region):
        center,(u,v)=texture_layout.screen_axes(bpy.context,obj,source,layer)
    axis=u if handle==0 else v
    xy=center+axis*(38+distance)
    window.event_simulate(type=kind,value=value,x=round(region.x+xy.x),
                          y=round(region.y+xy.y),**modifiers)


def check_changed():
    live=bmesh.from_edit_mesh(obj.data)
    uv_layer=live.loops.layers.uv['wavelength']
    assert any(loop[uv_layer].uv!=uv for loop,uv in zip(live.faces.active.loops,original))


def check_cancel():
    assert all(loop[layer].uv==uv for loop,uv in zip(source.loops,original))
    assert obj.data['wl_faces']==original_records


def check_commit():
    check_changed()
    assert obj.data['wl_faces']!=original_records
    global committed_records
    committed_records=obj.data['wl_faces']
    print('PASS texture gizmo mouse drag, Escape rollback and release commit',flush=True)
    with context.temp_override(area=area,region=region):
        assert bpy.ops.ed.undo()=={'FINISHED'}


def check_undo():
    active=context.edit_object
    assert active.data['wl_faces']==original_records
    restored=bmesh.from_edit_mesh(active.data)
    uv=restored.loops.layers.uv['wavelength']
    assert all(loop[uv].uv==value for loop,value in zip(restored.faces.active.loops,original))
    print('PASS texture gizmo undo restores UVs and Source face records',flush=True)
    with context.temp_override(area=area,region=region):
        assert bpy.ops.ed.redo()=={'FINISHED'}


def check_redo():
    assert context.edit_object.data['wl_faces']==committed_records
    print('PASS texture gizmo redo restores Source face records',flush=True)
    bpy.ops.wm.quit_blender()


steps=iter([
    lambda:send('MOUSEMOVE','NOTHING'),
    lambda:send('LEFTMOUSE','PRESS'),
    lambda:send('MOUSEMOVE','NOTHING',22,ctrl=True),
    check_changed,
    lambda:send('ESC','PRESS',22),
    lambda:send('LEFTMOUSE','RELEASE',22),
    check_cancel,
    lambda:send('MOUSEMOVE','NOTHING',handle=1),
    lambda:send('LEFTMOUSE','PRESS',handle=1),
    lambda:send('MOUSEMOVE','NOTHING',22,handle=1),
    lambda:send('LEFTMOUSE','RELEASE',22,handle=1),
    check_commit,
    check_undo,
    check_redo,
])


def tick():
    try:
        next(steps)()
        return .35
    except StopIteration:
        return None
    except Exception:
        traceback.print_exc()
        print('FAIL texture gizmo mouse events',flush=True)
        bpy.ops.wm.quit_blender()
        return None


bpy.app.timers.register(tick,first_interval=3)
