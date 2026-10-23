import sys,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_browser
from wavelength.source.ui import _spawn_point_entity
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False;ctx.workspace['wl_workspace']=True
folder=root/'build/entity-model-browser';folder.mkdir(exist_ok=True);ctx.preferences.filepaths.temporary_directory=str(folder)
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path='';s.project_dir=str(folder)
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
prop=None;browser=None
def begin():
    global prop,browser
    prop=_spawn_point_entity(ctx,'prop_physics');model_browser.tick()
    assert bpy.ops.wavelength.entity_browser(section='MODELS')=={'FINISHED'}
    browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
    bpy.app.timers.register(choose,first_interval=1)
def choose():
    path='models/props_c17/oildrum001.mdl'
    choice=next((o for o in bpy.data.objects if o.get('wl_model_choice') and o.get('wl_source_model')==path and o.asset_data),None)
    if not choice:return .2
    params=browser.spaces.active.params
    assert params.asset_library_reference=='LOCAL' and params.filter_asset_id.filter_object and not params.filter_asset_id.filter_material
    assert params.catalog_id==model_browser.CATALOG and params.asset_catalog_visibility=='CATALOG'
    params.filter_search='oildrum001.mdl'
    bpy.app.timers.register(activate,first_interval=1)
def activate():
    choice=next(o for o in bpy.data.objects if o.get('wl_source_model')=='models/props_c17/oildrum001.mdl' and o.get('wl_model_choice'))
    region=next(r for r in browser.regions if r.type=='WINDOW')
    with ctx.temp_override(area=browser,region=region):
        browser.spaces.active.activate_asset_by_id(choice)
        bpy.ops.file.select_all(action='SELECT')
    ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=browser.x+440,y=region.y+region.height-75)
    ctx.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=browser.x+440,y=region.y+region.height-75)
    ctx.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=browser.x+440,y=region.y+region.height-75)
    bpy.app.timers.register(apply,first_interval=1)
def apply():
    bpy.ops.screen.screenshot(filepath=str(folder/'context-before-assign.png'))
    with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
        print('CONTEXT',ctx.area.type,ctx.space_data.type,ctx.region.type,'ACTIVE ASSET',ctx.asset,'SELECTED',list(ctx.selected_assets or []),flush=True)
        assert ctx.asset and ctx.asset.local_id.get('wl_model_choice')
        assert bpy.ops.wavelength.use_asset()=={'FINISHED'}
    assert ctx.view_layer.objects.active==prop
    assert len([c for c in prop.children if c.get('wl_model_reference')])==1
    print('PASS native model catalog, object-only filter and Use Asset update the selected physics entity',flush=True)
    bpy.app.timers.register(finish,first_interval=1)
def finish():
    bpy.ops.screen.screenshot(filepath=str(folder/'contextual-models.png'));bpy.ops.wm.quit_blender()
def safe(fn):
    def call():
        try:return fn()
        except Exception:traceback.print_exc();print('FAIL contextual model browser UI',flush=True);bpy.ops.wm.quit_blender()
    return call
begin=safe(begin);choose=safe(choose);activate=safe(activate);apply=safe(apply);finish=safe(finish)
bpy.app.timers.register(begin,first_interval=1.5)
