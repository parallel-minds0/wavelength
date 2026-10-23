import sys,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_browser
from wavelength.source.ui import _spawn_point_entity
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False;ctx.workspace['wl_workspace']=True
folder=root/'build/entity-model-browser';ctx.preferences.filepaths.temporary_directory=str(folder)
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path='';s.project_dir=str(folder)
def begin():
    _spawn_point_entity(ctx,'prop_physics')
    print('TIMER REGISTERED',bpy.app.timers.is_registered(model_browser.tick),'TARGET',model_browser.target()[0],flush=True)
    bpy.app.timers.register(check,first_interval=2)
def check():
    print('SECTION',s.asset_browser_section,'TIMER',bpy.app.timers.is_registered(model_browser.tick),'STATUS',s.status,flush=True)
    assert s.asset_browser_section=='MODELS'
    assert any(a.type=='FILE_BROWSER' and a.ui_type=='ASSETS' for a in ctx.screen.areas)
    print('PASS automatic entity selection without manually calling the watcher',flush=True)
    from wavelength.source import asset_index
    model_browser.assign(ctx,asset_index.record(s.engine,'models/props_c17/oildrum001.mdl'))
    parent=ctx.view_layer.objects.active;child=next(c for c in parent.children if c.get('wl_model_reference'))
    assert not child.hide_select
    parent.select_set(False);child.select_set(True);ctx.view_layer.objects.active=child
    bpy.app.timers.register(check_visual,first_interval=1)
def check_visual():
    assert ctx.view_layer.objects.active.get('wl_role')=='ENTITY' and s.asset_browser_section=='MODELS'
    print('PASS selecting model geometry activates its owning engine entity automatically',flush=True)
    bpy.ops.wm.quit_blender()
def safe(fn):
    def call():
        try:return fn()
        except Exception:traceback.print_exc();print('FAIL model auto',flush=True);bpy.ops.wm.quit_blender()
    return call
begin=safe(begin);check=safe(check);check_visual=safe(check_visual)
bpy.app.timers.register(begin,first_interval=1.5)
