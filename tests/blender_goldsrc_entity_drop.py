exec(compile((__import__('pathlib').Path(__file__).parent/'blender_goldsrc_entity_models.py').read_text(),__file__,'exec'))
import traceback
from wavelength.source.entity import browser
ctx=bpy.context;s=ctx.scene.wavelength
obj=bpy.data.objects.new('Dropped HL1 Crowbar',None);ctx.collection.objects.link(obj)
obj['wl_entity_browser_template']='weapon_crowbar';obj['wl_entity_browser_profile']=s.engine
assert browser._finalize_drop(ctx.scene,obj)
def verify():
    try:
        reference=visual(obj);assert reference['wl_source_model']=='models/w_crowbar.mdl'
        assert ctx.view_layer.objects.active==obj
        print('PASS native GoldSrc browser placement creates actual crowbar geometry outside depsgraph callbacks',flush=True)
    except Exception:traceback.print_exc();print('FAIL HL1 ENTITY DROP',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(verify,first_interval=2)
