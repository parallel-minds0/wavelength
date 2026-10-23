import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector,Quaternion
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import scene,primitives,terrain,terrain_face
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain-face';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder)
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True;ctx.scene.wavelength.engine='source_gmod_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
vertices,faces=primitives.box(-128,-128,-32,128,128,0)
mesh=bpy.data.meshes.new('Brush');mesh.from_pydata([Vector(v)*.0254 for v in vertices],[],faces);mesh.update()
obj=bpy.data.objects.new('Brush',mesh);ctx.collection.objects.link(obj);scene.mark_brush(obj)
mat=bpy.data.materials.new('Dirt');mat['wl_texture']='nature/dirtfloor001a';mesh.materials.append(mat)
obj.select_set(True);ctx.view_layer.objects.active=obj;bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(mesh)
for f in bm.faces:f.select_set(False)
max(bm.faces,key=lambda f:f.normal.z).select_set(True);bmesh.update_edit_mesh(mesh)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.displacement_from_face()=={'FINISHED'}
terrain_obj=ctx.object;terrain_obj.wavelength_terrain.amplitude=24
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((.86,.36,.14,.33)).normalized();rv.view_location=(0,0,0);rv.view_distance=12
props=next(a for a in ctx.screen.areas if a.type=='PROPERTIES');props.spaces.active.context='OBJECT'
def check():
    try:
        assert terrain_obj.parent is None and terrain_obj.get('wl_terrain_detached') and terrain.WL_PT_terrain.poll(ctx)
        bpy.ops.screen.screenshot(filepath=str(folder/'brush-face-ui.png'))
        print('PASS brush-face creation in viewport and attached terrain properties panel',flush=True)
    except Exception:traceback.print_exc();print('FAIL BRUSH FACE UI',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1.5)
