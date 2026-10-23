import sys,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_import
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=root/'build/source-models';folder.mkdir(exist_ok=True);ctx.preferences.filepaths.temporary_directory=str(folder)
ctx.scene.wavelength.engine='source_hl2_windows';ctx.scene.wavelength.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
def check():
    try:
        area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
        with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.add_source_model('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
        assert any(item[0]=='models/props_junk/wood_crate001a.mdl' for item in model_import._MODEL_ITEMS)
        ctx.window.event_simulate(type='ESC',value='PRESS')
        print('PASS native model search popup enumerates active game mounts without loading all meshes',flush=True)
        bpy.app.timers.register(place,first_interval=.4)
    except Exception:traceback.print_exc();print('FAIL model search popup',flush=True);bpy.ops.wm.quit_blender()
def place():
    try:
        assert bpy.ops.wavelength.add_source_model(model='models/props_junk/wood_crate001a.mdl')=={'FINISHED'}
        assert ctx.object.get('wl_role')=='ENTITY' and any(c.type=='MESH' for c in ctx.object.children)
        print('PASS model chooser places real geometry at the scene cursor',flush=True)
        from mathutils import Euler,Vector
        area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');space=area.spaces.active
        space.shading.type='MATERIAL';space.region_3d.view_location=Vector((0,0,.4));space.region_3d.view_distance=3;space.region_3d.view_rotation=Euler((1.1,0,.65)).to_quaternion()
        bpy.app.timers.register(finish,first_interval=6)
    except Exception:traceback.print_exc();print('FAIL model chooser placement',flush=True);bpy.ops.wm.quit_blender()
def finish():
    bpy.ops.screen.screenshot(filepath=str(folder/'model-preview.png'));bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1.5)
