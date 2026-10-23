exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_auto.py').read_text().split('def begin():')[0],__file__,'exec'))
from wavelength.source.entity import browser as entities
dropped=None
def begin():
    global dropped
    entities.rebuild(ctx)
    template=next(o for o in bpy.data.objects if o.get('wl_entity_browser_template')=='prop_physics')
    dropped=template.copy()
    # Exercise an asset linked both to its source collection and the drop target.
    template.users_collection[0].objects.link(dropped);ctx.collection.objects.link(dropped)
    ctx.view_layer.update()
    bpy.app.timers.register(check,first_interval=2)
def check():
    assert not dropped.get('wl_entity_browser_template') and not dropped.get('wl_exclude')
    assert dropped.asset_data is None and not dropped.hide_select
    assert ctx.view_layer.objects.active==dropped and dropped.select_get()
    assert s.asset_browser_section=='MODELS' and model_browser.target()[0]==dropped
    assert any(o.get('wl_entity_browser_template')=='prop_physics' and o.asset_data for o in bpy.data.objects)
    print('PASS native entity drop finalizes, activates and automatically opens model choices while preserving its browser template',flush=True)
    bpy.ops.wm.quit_blender()
def safe(fn):
    def call():
        try:return fn()
        except Exception:traceback.print_exc();print('FAIL model drop auto',flush=True);bpy.ops.wm.quit_blender()
    return call
begin=safe(begin);check=safe(check)
bpy.app.timers.register(begin,first_interval=1.5)
