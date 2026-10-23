import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import primitives,scene
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain-detach';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True;ctx.scene.wavelength.engine='source_hl2_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
vertices,faces=primitives.box(-64,-64,-64,64,64,64);mesh=bpy.data.meshes.new('Undo source');mesh.from_pydata([[c*.0254 for c in p] for p in vertices],[],faces);mesh.update()
source=bpy.data.objects.new('Undo source',mesh);ctx.collection.objects.link(source);scene.mark_brush(source);source.select_set(True);ctx.view_layer.objects.active=source;bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(mesh)
for face in bm.faces:face.select_set(True)
bmesh.update_edit_mesh(mesh)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');steps=[]
def extract():
    bpy.ops.ed.undo_push(message='Original source brush')
    with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.displacement_from_face('EXEC_DEFAULT',True)=={'FINISHED'}
    assert 'Undo source' not in ctx.scene.objects
    assert len([o for o in ctx.scene.objects if o.get('wl_terrain_detached')])==6
    bpy.ops.screen.screenshot(filepath=str(folder/'independent-ui.png'))
    print('PASS viewport extraction creates six selected independent surfaces and consumes the brush',flush=True)
steps.append(extract)
def undo():ctx.window.event_simulate(type='Z',value='PRESS',ctrl=True,x=region.x+200,y=region.y+200)
steps.append(undo)
def check():
    assert 'Undo source' in ctx.scene.objects
    assert not any(o.get('wl_terrain') for o in ctx.scene.objects)
    print('PASS native undo restores the complete brush and removes the generated surfaces',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .4 if steps else None
    except Exception:traceback.print_exc();print('FAIL DETACH UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
