import sys,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import cutter_snap
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/cutter';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder)
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='blender'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.mesh.primitive_cube_add()
obj=ctx.object
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=8;rv.view_location=(0,0,0)

def test():
    try:
        with ctx.temp_override(area=area,region=region):
            rv.update();ts=ctx.scene.tool_settings;ts.use_snap=True;ts.snap_elements={'VERTEX','EDGE','INCREMENT'}
            cache=cutter_snap.Targets(ctx,obj)
            def resolve(p,offset=(0,0),ctrl=False):
                xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector(p))+Vector(offset)
                event=SimpleNamespace(mouse_region_x=xy.x,mouse_region_y=xy.y,ctrl=ctrl)
                return cache.resolve(ctx,event,Vector((0,0,1)),Vector((0,0,1)),Vector((0,0,1)))
            result=resolve((1,1,1),(4,3));assert result[2]=='VERTEX' and (result[0]-Vector((1,1,1))).length<1e-6,result
            result=resolve((1,.13,1),(3,0));assert result[2]=='EDGE' and abs(result[0].x-1)<1e-6,result
            result=resolve((.13,.19,1));assert result[2]=='GRID' and abs(result[0].x)<1e-6,result
            result=resolve((.13,.19,1),ctrl=True);assert result[2]=='FACE' and abs(result[0].x-.13)<1e-3,result
            assert not result[3], 'Face hover must not highlight face boundaries'
            ts.snap_elements={'INCREMENT'}
            result=resolve((1,1,1),(4,3));assert result[2]=='VERTEX' and result[0]==Vector((1,1,1)),result
            result=resolve((1,.13,1),(3,0));assert result[2]=='EDGE',result
            result=resolve((.13,.19,1));assert result[2]=='GRID' and not result[3],result
            ts.use_snap=False
            result=resolve((1,1,1),(-4,-3));assert result[2]=='VERTEX' and (result[0]-Vector((1,1,1))).length<1e-6,result
            result=resolve((1,1,1),(-4,-3),ctrl=True);assert result[2]!='VERTEX',result
            ts.use_snap=True
            bpy.ops.wavelength.activate_cutter()
            assert ctx.mode=='EDIT_MESH'
            assert ctx.workspace.tools.from_space_view3d_mode('EDIT_MESH').idname=='wavelength.pencil_edit_tool'
            import bmesh
            live=bmesh.from_edit_mesh(obj.data)
            vertex=next(v for v in live.verts if (v.co-Vector((1,1,1))).length<1e-6)
            vertex.co.x=.8
            cache=cutter_snap.Targets(ctx,obj)
            result=resolve((.8,1,1),(4,3))
            assert result[2]=='VERTEX' and (result[0]-Vector((.8,1,1))).length<1e-6,result
            assert region.x or region.y, 'Test needs an offset viewport'
            xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector((.8,1,1)))
            result=cutter_snap.hover_result(ctx,(region.x+xy.x+4,region.y+xy.y+3))
            assert result[2]=='VERTEX' and (result[0]-Vector((.8,1,1))).length<1e-6,result
            assert not __import__('wavelength.source.pencil',fromlist=['_drawing'])._drawing
            print('PASS pre-click hover snaps using window-to-region coordinates',flush=True)
            print('PASS automatic Edit Mode and live edit-mesh vertex snapping',flush=True)
            print('PASS vertex/edge priority, silhouette snapping, grid fallback, Ctrl inversion',flush=True)
            bpy.ops.wavelength.activate_cutter()
            xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector((1,.13,1)))
            ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=int(region.x+xy.x),y=int(region.y+xy.y))
        bpy.app.timers.register(capture,first_interval=.5)
    except Exception:traceback.print_exc();print('FAIL SNAP',flush=True);bpy.ops.wm.quit_blender()
def capture():
    bpy.ops.screen.screenshot(filepath=str(folder/'cursor-snap.png'));print('PASS SNAP CURSOR',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=2)
