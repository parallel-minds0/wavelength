exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_auto.py').read_text().split('def begin():')[0],__file__,'exec'))
from wavelength.source.entity import browser as entities
browser=None
def begin():
    global browser
    assert bpy.ops.wavelength.entity_browser(section='ENTITIES')=={'FINISHED'}
    browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
    bpy.app.timers.register(filter_assets,first_interval=.3)
def filter_assets():
    if browser.spaces.active.params is None:return .2
    browser.spaces.active.params.filter_search='prop_physics'
    bpy.app.timers.register(activate,first_interval=1)
def activate():
    region=next(r for r in browser.regions if r.type=='WINDOW')
    with ctx.temp_override(area=browser,region=region):
        template=next(o for o in bpy.data.objects if o.get('wl_entity_browser_template')=='prop_physics')
        browser.spaces.active.activate_asset_by_id(template)
    ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=browser.x+440,y=region.y+region.height-75)
    ctx.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=browser.x+440,y=region.y+region.height-75)
    ctx.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=browser.x+440,y=region.y+region.height-75)
    bpy.app.timers.register(place,first_interval=.5)
def place():
    with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
        print('ENTITY ASSET',ctx.asset,flush=True)
        assert bpy.ops.wavelength.use_asset()=={'FINISHED'}
    bpy.app.timers.register(check,first_interval=2)
def check():
    print('ACTIVE',ctx.view_layer.objects.active,'TARGET',model_browser.target()[0],'STATUS',s.status,'SECTION',s.asset_browser_section,flush=True)
    assert s.asset_browser_section=='MODELS'
    assert model_browser.target()[0]
    print('PASS entity placed from native asset browser automatically enters model context',flush=True)
    bpy.ops.wm.quit_blender()
def safe(fn):
    def call():
        try:return fn()
        except Exception:traceback.print_exc();print('FAIL model asset auto',flush=True);bpy.ops.wm.quit_blender()
    return call
begin=safe(begin);filter_assets=safe(filter_assets);activate=safe(activate);place=safe(place);check=safe(check)
bpy.app.timers.register(begin,first_interval=1.5)
