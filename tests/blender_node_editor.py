import bpy,runpy,traceback
from pathlib import Path
scope=runpy.run_path(str(Path(__file__).with_name('blender_node_stairs.py')))
obj=scope['obj'];ui=scope['ui'];ctx=bpy.context
ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/node-editor';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');area.type='NODE_EDITOR';area.ui_type='GeometryNodeTree'
space=area.spaces.active;space.node_tree_sub_type='MODIFIER';space.pin=False
ctx.workspace['wl_workspace']=False
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj

def check():
    try:
        assert ctx.view_layer.objects.active==obj
        assert not scope['root'].select_get()
        assert space.node_tree==obj.modifiers[0].node_group,(space.node_tree,obj.modifiers[0].node_group)
        print('PASS native node workspace retains mesh selection and visible graph',flush=True)
        ctx.workspace['wl_workspace']=True
        for _ in range(4):ui.sync_assemblies()
        assert ctx.view_layer.objects.active==obj
        assert space.node_tree==obj.modifiers[0].node_group
        print('PASS Wavelength assembly selection retains active node mesh',flush=True)
    except Exception:traceback.print_exc();print('FAIL NODE EDITOR',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1)

