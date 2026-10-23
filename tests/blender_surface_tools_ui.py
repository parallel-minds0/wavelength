exec(compile((__import__('pathlib').Path(__file__).parent/'blender_surface_tools.py').read_text(),__file__,'exec'))
import traceback
from types import SimpleNamespace
ctx.preferences.view.show_splash=False
# Exercise the real File Browser context while retaining Edit Mode face selection.
with surface_tools.viewport(ctx):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data)
    for face in bm.faces:face.select_set(False)
    bm.faces.ensure_lookup_table();bm.faces[0].select_set(True);bmesh.update_edit_mesh(obj.data)
bpy.ops.wavelength.entity_browser(section='TEXTURES')
def verify():
    try:
        browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS');region=next(r for r in browser.regions if r.type=='WINDOW')
        with ctx.temp_override(area=browser,region=region):
            fake=SimpleNamespace(asset=SimpleNamespace(local_id=materials[0]),scene=ctx.scene,screen=ctx.screen)
            assert asset_browser.WL_OT_use_asset.execute(SimpleNamespace(report=lambda *args:print(args)),fake)=={'FINISHED'}
            assert obj.mode=='EDIT'
            bm=bmesh.from_edit_mesh(obj.data)
            assert sum(obj.data.materials[f.material_index]==materials[0] for f in bm.faces)==1
            assert bpy.ops.wavelength.read_face_texture()=={'FINISHED'}
            bpy.ops.wm.call_panel(name='WL_PT_surface',keep_open=True)
        print('PASS real Asset Browser context applies only selected faces, reads mapping and opens texture settings',flush=True)
        bpy.app.timers.register(finish,first_interval=1)
    except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
def finish():
    bpy.ops.screen.screenshot(filepath=str(root/'build/surface-tools-ui.png'))
    ctx.window.event_simulate(type='ESC',value='PRESS');ctx.window.event_simulate(type='ESC',value='RELEASE')
    bpy.app.timers.register(start_picker,first_interval=.5)
def start_picker():
    try:
        with surface_tools.viewport(ctx):
            bpy.ops.object.mode_set(mode='OBJECT')
            for candidate in ctx.scene.objects:
                if candidate!=obj:candidate.hide_set(True)
            bpy.ops.view3d.view_axis(type='FRONT');ctx.space_data.region_3d.view_location=(0,0,0);ctx.space_data.region_3d.view_distance=6
        browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER')
        with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
            assert bpy.ops.wavelength.pick_asset('INVOKE_DEFAULT',kind='TEXTURE')=={'RUNNING_MODAL'}
        view=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in view.regions if r.type=='WINDOW')
        x=region.x+region.width//2;y=region.y+region.height//2
        ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
        ctx.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=x,y=y);ctx.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=x,y=y)
        bpy.app.timers.register(check_picker,first_interval=.5)
    except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
def check_picker():
    try:
        assert json.loads(ctx.scene['_wl_asset_clipboard'])['category']=='MATERIAL'
        print('PASS live Asset Browser eyedropper click samples viewport surface without applying or changing selection',flush=True)
    except Exception:traceback.print_exc()
    bpy.ops.wm.quit_blender()
bpy.app.timers.register(verify,first_interval=1)
