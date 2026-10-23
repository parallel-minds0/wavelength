"""Real native toolbar/keyboard routing and workspace restoration, no keymap edits."""
import sys,traceback,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import transform_bridge as bridge,profiles
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='source_hl2_windows';ctx.scene.wavelength.grid_mode='ENGINE';ctx.scene.tool_settings.use_snap=False
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');window=ctx.window
obj=ctx.object;obj.location=(0,0,0)
import bmesh
from mathutils import Quaternion
from wavelength.source import primitive_ui,tool_snap
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=7
steps=[];state={}
ts=ctx.scene.tool_settings;ts.snap_elements={'INCREMENT'};ts.use_snap=False
ctx.workspace['wl_snapping']=False
step=profiles.active_grid_step_meters(ctx.scene.wavelength)
def aligned(values):return all(abs(v/step-round(v/step))<1e-4 for v in values)
def setup():
    assert bridge.available(ctx),'Legacy map switch must not give ownership back to Blender'
    bpy.ops.wavelength.workspace_toggle(feature='snapping');assert ts.use_snap
    assert bridge.available(ctx)
    obj.location=(.13,.57,.71);ctx.view_layer.update()
    bpy.ops.view3d.snap_selected_to_grid();assert aligned(obj.location),obj.location[:]
    ctx.scene.cursor.location=(.13,.57,.71);bpy.ops.view3d.snap_cursor_to_grid();assert aligned(ctx.scene.cursor.location),ctx.scene.cursor.location[:]
    print('PASS native Shift+S object/cursor grid commands use profile spacing',flush=True)
    # Native command must move an assembly once, without snapping child origins.
    root=bpy.data.objects.new('Snap assembly',None);ctx.collection.objects.link(root)
    primitive_ui.rebuild(root,'STAIRS',primitive_ui.DEFAULTS,ctx);root.location=(.13,.57,.71)
    bpy.ops.object.select_all(action='DESELECT');primitive_ui.select_assembly(root,ctx,True)
    parts=primitive_ui.parts_for(root);before=[p.matrix_local.copy() for p in parts]
    bpy.ops.view3d.snap_selected_to_grid();assert aligned(root.location)
    assert all(a==p.matrix_local for a,p in zip(before,parts))
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
    obj.location=(0,0,0);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.view3d.snap_selected_to_grid()
    mesh=bmesh.from_edit_mesh(obj.data);assert aligned([c for v in mesh.verts for c in obj.matrix_world@v.co])
    state['vertices']=[tuple(v.co) for v in mesh.verts]
    print('PASS procedural assembly ownership and native Edit Mode grid command',flush=True)
    rv.update()
steps.append(setup)
def event(kind,value='PRESS',dx=0):
    def run():window.event_simulate(type=kind,value=value,x=region.x+region.width//2+dx,y=region.y+region.height//2)
    steps.append(run)
event('G');event('G','RELEASE');event('X');event('X','RELEASE');event('MOUSEMOVE','NOTHING',117);event('LEFTMOUSE','PRESS',117);event('LEFTMOUSE','RELEASE',117)
def check():
    mesh=bmesh.from_edit_mesh(obj.data);assert aligned([c for v in mesh.verts for c in obj.matrix_world@v.co]),[tuple(v.co) for v in mesh.verts]
    assert state['vertices']!=[tuple(v.co) for v in mesh.verts], 'Mouse move did not change geometry'
    print('PASS live native vertex move snaps to profile grid',flush=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.wavelength.workspace_toggle(feature='snapping');assert not ts.use_snap and bridge.available(ctx)
    bpy.ops.wavelength.workspace_toggle(feature='snapping');assert ts.use_snap
    ctx.workspace['wl_workspace']=False;bridge.sync()
    ctx.scene.cursor.location=(.13,.57,.71);bpy.ops.view3d.snap_cursor_to_grid()
    assert not aligned(ctx.scene.cursor.location),ctx.scene.cursor.location[:]
    assert ts.snap_elements=={'INCREMENT'}
    print('PASS unified snap toggle preserves backend; outside workspace restores native grid',flush=True)
    print('PASS PROFILE SNAP MAPPING',flush=True);bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .35
    except Exception:traceback.print_exc();print('FAIL PROFILE SNAP MAPPING',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
