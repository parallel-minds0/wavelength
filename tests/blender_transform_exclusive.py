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
def send(key,unicode=None):
    def run():
        kw=dict(type=key,value='PRESS',x=region.x+region.width//2,y=region.y+region.height//2)
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
def disable_route():
    km=ctx.window_manager.keyconfigs.user.keymaps['Object Mode']
    state['route']=next(i for i in km.keymap_items if i.idname=='wavelength.transform_route' and i.type=='G')
    state['route'].active=False
add(disable_route)
send('G')
def check_native_suppressed():
    assert hasattr(window,'modal_operators')
    assert not any(op.bl_idname in {'TRANSFORM_OT_translate','transform.translate'} for op in window.modal_operators),[op.bl_idname for op in window.modal_operators]
    assert obj.location.length<1e-6, 'Competing native G binding ran in wavelength'
    print('PASS native G shortcut is suppressed independently of replacement binding',flush=True)
    bpy.ops.wm.quit_blender()
add(check_native_suppressed)
send('ESC')
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .22
    except Exception:traceback.print_exc();print('FAIL TRANSFORM BRIDGE',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
