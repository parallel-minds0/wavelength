"""Deferred browser placement loads fixed world models in a normal UI session."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_source_entity_representations.py').read_text(),__file__,'exec'))
import traceback
obj=bpy.data.objects.new('Dropped Crowbar',None);ctx.collection.objects.link(obj)
obj['wl_entity_browser_template']='weapon_crowbar';obj['wl_entity_browser_profile']=s.engine
assert browser._finalize_drop(ctx.scene,obj)
def verify():
    try:
        check(obj,'models/weapons/w_crowbar.mdl')
        assert ctx.view_layer.objects.active==obj
        print('PASS deferred entity browser drop attaches the real crowbar world mesh; selected entity remains weapon_crowbar',flush=True)
    except Exception:traceback.print_exc();print('FAIL SOURCE ENTITY REPRESENTATION DROP',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(verify,first_interval=2)
