"""Always-on scene geometry targeting shared by brushes and pencil creation."""
import sys,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils as view
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import cutter_snap,brush_create,pencil
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='source_hl2_windows';ctx.scene.wavelength.grid_mode='ENGINE'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(-2,0,.3));first=ctx.object
bpy.ops.mesh.primitive_cube_add(location=(2,0,.7));second=ctx.object
second.select_set(False);first.select_set(True);ctx.view_layer.objects.active=first
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=9;rv.view_location=(0,0,0)
def check():
 try:
  with ctx.temp_override(area=area,region=region):
   ctx.view_layer.update();rv.update();ts=ctx.scene.tool_settings;ts.use_snap=False;ts.snap_elements={'INCREMENT'}
   targets=cutter_snap.Targets(ctx,first,scene_targets=True,always_geometry=True)
   def event(point,offset=(0,0),ctrl=False):
    xy=view.location_3d_to_region_2d(region,rv,Vector(point))+Vector(offset)
    return SimpleNamespace(mouse_region_x=xy.x,mouse_region_y=xy.y,ctrl=ctrl)
   def resolve(point,offset=(0,0),ctrl=False,cache=None,locked=False):
    return (cache or targets).resolve(ctx,event(point,offset,ctrl),Vector((0,0,1.7)),Vector((0,0,1)),Vector(),lock_plane=locked)
   result=resolve((3,1,1.7),(4,3));assert result[2]=='VERTEX' and (result[0]-Vector((3,1,1.7))).length<1e-5,result
   result=resolve((3,1,1.7),(4,3),True);assert result[2]=='VERTEX','Ctrl disabled always-on geometry'
   result=resolve((3,.13,1.7),(3,0));assert result[2]=='EDGE',result
   result=resolve((2.13,.19,1.7));assert result[2]=='FACE' and abs(result[0].z-1.7)<1e-5,result
   assert abs(result[0].x-2.13)<1e-4,'Surface point quantized while grid off'
   ts.use_snap=True
   result=resolve((3,1,1.7),(4,3));assert result[2]=='VERTEX' and abs(result[0].x-3)<1e-6,'Grid overrode off-grid vertex'
   result=resolve((2.13,.19,1.7));assert result[2]=='GRID' and abs(result[0].z-1.7)<1e-5,result
   result=resolve((-1,1,1.3),locked=True);assert abs(result[0].z-1.7)<1e-5,'Locked plane jumped to another surface'
   second.hide_set(True);hidden=cutter_snap.Targets(ctx,first,scene_targets=True,always_geometry=True)
   assert len(hidden.vertices)==8,'Hidden object is still a target'
   second.hide_set(False);second['wl_exclude']=True
   assert len(cutter_snap.Targets(ctx,None,scene_targets=True).vertices)==8,'Excluded helper still a target'
   del second['wl_exclude']
   tool=SimpleNamespace(_plane_point=None,_targets=targets)
   brush_create.WL_OT_cube_brush_create._update_hover(tool,ctx,event((3,1,1.7),(4,3)),True)
   assert (tool._hover-Vector((3,1,1.7))).length<1e-5,'Brush first point missed unselected vertex'
   tool._start=Vector((2,0,1.7));tool._initial_drag=Vector((3.01,1.01,1.7));tool._start_mouse_2d=(98,100);tool._virt_mouse=(100,100);tool._step_value=.4064
   with patch.object(view,'region_2d_to_location_3d',return_value=Vector()):
    end=brush_create.WL_OT_cube_brush_create._footprint_drag_from_mouse(tool,ctx)
   assert (end-Vector((3,1,1.7))).length<1e-5,'Brush endpoint did not prioritize geometry'
   assert brush_create._creation_step(tool)==0,'Generator will round the vertex back onto grid'
   vertices,_=brush_create._radial_geometry(ctx.scene.wavelength,tool._start,end,tool._u,tool._v,tool._n,brush_create._creation_step(tool))
   assert abs((vertices[0]-tool._start).length-(end-tool._start).length)<1e-5,'Radial brush lost exact geometry radius'
   stroke=SimpleNamespace(_points=[],_pending=None,_plane=Vector(),_normal=Vector((0,0,1)),_targets=targets,_value='')
   pencil.WL_OT_draw_path._update(stroke,ctx,event((3,1,1.7),(4,3)))
   assert (stroke._hover-Vector((3,1,1.7))).length<1e-5
   assert abs(stroke._plane.z-1.7)<1e-5,'Pencil first vertex did not establish the surface plane'
   rv.view_rotation=Vector((5,-8,5)).to_track_quat('Z','Y');rv.update()
   height_tool=SimpleNamespace(_start=Vector((3,1,0)),_height_mouse_start=(0,0),_virt_mouse=(0,0),_n=Vector((0,0,1)),_height_start_m=1.69,_plane_point=Vector(),_step_value=.4064,_targets=targets)
   brush_create.WL_OT_cube_brush_create._update_height_from_mouse(height_tool,ctx)
   assert abs(height_tool._height_m-1.7)<1e-5,('Brush height missed nearby geometry',height_tool._height_m)
   rv.view_rotation=Quaternion((1,0,0,0));rv.update()
   # Live Edit Mode coordinates, never the stale object mesh datablock.
   second.select_set(True);ctx.view_layer.objects.active=second;bpy.ops.object.mode_set(mode='EDIT')
   import bmesh
   bm=bmesh.from_edit_mesh(second.data);v=next(v for v in bm.verts if v.co==Vector((1,1,1)));v.co.x=.8
   live=cutter_snap.Targets(ctx,None,scene_targets=True,always_geometry=True)
   result=resolve((2.8,1,1.7),(3,2),cache=live);assert result[2]=='VERTEX' and abs(result[0].x-2.8)<1e-5,result
   bpy.ops.object.mode_set(mode='OBJECT')
   print('PASS CREATION SMART SNAP: unselected meshes, grid off/on, Ctrl, edge/face, exact off-grid vertex, hidden/helpers, locked planes, brush hover/endpoint, pencil first point, live edit meshes',flush=True)
 except Exception:
  traceback.print_exc();print('FAIL CREATION SMART SNAP',flush=True)
 finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=2)
