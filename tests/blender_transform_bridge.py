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
steps=[];state={}
def add(fn):steps.append(fn)
def send(key,unicode=None,ctrl=False,shift=False):
    def run():
        kw=dict(type=key,value='PRESS',ctrl=ctrl,shift=shift,x=region.x+region.width//2,y=region.y+region.height//2)
        if unicode is not None:kw['unicode']=unicode
        window.event_simulate(**kw)
        window.event_simulate(type=key,value='RELEASE',x=kw['x'],y=kw['y'])
    add(run)
def digits(value):
    for char in value:send({'1':'ONE','2':'TWO','6':'SIX','9':'NINE','0':'ZERO'}[char],char)
def setup():
    assert bridge.available(ctx)
    state['native']=[(km.name,item.id,item.idname,item.active) for km in ctx.window_manager.keyconfigs.user.keymaps for item in km.keymap_items if item.idname in {'transform.translate','transform.rotate','transform.resize'}]
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as Tools
    for name in bridge.NATIVE:
        with ctx.temp_override(area=area,region=region):
            bpy.ops.wm.tool_set_by_id(name=name)
            tool=ctx.workspace.tools.from_space_view3d_mode('OBJECT')
            assert tool.idname==name and Tools._tool_get_by_id(ctx,name)[0].widget=='WL_GGT_native_transform',name
    flat=list(Tools._tools_flatten(Tools.tools_from_context(ctx)))
    assert not any(t and t.idname in bridge.LEGACY for t in flat)
    print('PASS native toolbar identities use profile controllers; no duplicate transform tools',flush=True)
add(setup)
send('G');send('X');digits('16');send('RET')
def check_move():
    assert abs(obj.location.x-profiles.engine_to_world(ctx.scene.wavelength,16))<1e-5,obj.location[:]
    print('PASS G X 16 uses engine units exactly once',flush=True)
add(check_move)
send('R');send('Z');digits('90');send('RET')
def check_rotate():
    assert abs(obj.rotation_euler.z-math.pi/2)<1e-5,obj.rotation_euler[:]
    print('PASS R Z 90 routes to engine rotation',flush=True)
add(check_rotate)
send('S');send('X');digits('2');send('RET')
def check_scale():
    assert max(obj.scale)>1.99,obj.scale[:]
    state['matrix']=obj.matrix_world.copy()
    print('PASS S X 2 routes to engine scale',flush=True)
add(check_scale)
send('Z',ctrl=True)
def check_undo():
    global obj
    obj=bpy.data.objects['Cube']
    assert max(obj.scale)<1.01,obj.scale[:]
    print('PASS engine scale native undo',flush=True)
add(check_undo)
send('Z',ctrl=True,shift=True)
def check_redo():
    global obj
    obj=bpy.data.objects['Cube']
    assert max(obj.scale)>1.99,obj.scale[:]
    print('PASS engine scale native redo',flush=True)
add(check_redo)
send('G');send('X');digits('16');send('ESC')
def check_cancel():
    assert all(abs(a-b)<1e-5 for ra,rb in zip(obj.matrix_world,state['matrix']) for a,b in zip(ra,rb))
    ctx.workspace['wl_workspace']=False;bridge.sync()
    tool=ctx.workspace.tools.from_space_view3d_mode('OBJECT');assert bridge._states[(ctx.workspace.as_pointer(),'OBJECT')][1]=='VIEW3D_GGT_xform_gizmo'
    obj.location=(0,0,0)
    print('PASS cancel restores transform; leaving workspace restores native widget',flush=True)
add(check_cancel)
send('G');send('X');digits('2');send('RET')
def check_outside():
    assert abs(obj.location.x-2)<1e-5,obj.location[:]
    ctx.workspace['wl_workspace']=True;ctx.scene.wavelength_context.mode='SUSPENDED';bridge.sync();obj.location=(0,0,0)
    print('PASS ordinary Blender G X 2 outside wavelength',flush=True)
add(check_outside)
send('G');send('X');digits('2');send('RET')
def finish():
    assert abs(obj.location.x-2)<1e-5,obj.location[:]
    current=[(km.name,item.id,item.idname,item.active) for km in ctx.window_manager.keyconfigs.user.keymaps for item in km.keymap_items if item.idname in {'transform.translate','transform.rotate','transform.resize'}]
    assert current==state['native'],'Native keymap bindings or active flags changed'
    ctx.scene.wavelength_context.mode='EDIT';bridge.sync()
    assert bridge._states[(ctx.workspace.as_pointer(),'OBJECT')][1]=='WL_GGT_native_transform'
    addon_utils.disable('wavelength',default_set=False)
    assert __import__('bl_ui.space_toolsystem_toolbar',fromlist=['VIEW3D_PT_tools_active']).VIEW3D_PT_tools_active._tool_get_by_id(ctx,'builtin.transform')[0].widget=='VIEW3D_GGT_xform_gizmo'
    print('PASS suspension uses native transforms; keymaps untouched; disable restores tool runtime',flush=True)
    print('PASS TRANSFORM BRIDGE',flush=True);bpy.ops.wm.quit_blender()
add(finish)
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .22
    except Exception:traceback.print_exc();print('FAIL TRANSFORM BRIDGE',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
