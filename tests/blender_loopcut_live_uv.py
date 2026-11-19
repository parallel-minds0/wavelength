"""Actual Ctrl+R preview/edge-slide with live observers enabled."""
import sys,math,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import scene,editor,edit_safety,primitive_ui,transform_bridge,geometry_debug
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
s=c.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_hl2_windows';s.grid_mode='ENGINE';s.live_texture_reproject=True
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
obj=c.object;scene.mark_brush(obj);editor.apply_uv(obj,s.engine)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_mode(type='EDGE');bpy.ops.mesh.select_all(action='DESELECT')
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
rv=a.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0),math.pi/2);rv.view_distance=7;rv.view_perspective='ORTHO';rv.view_location=(0,0,0)
c.scene.tool_settings.use_snap=True;c.scene.tool_settings.snap_elements={'GRID'}
steps=[];state={'deferred':0,'updates':0};original=editor.apply_edit_uv
def tracked(obj):
 assert not edit_safety.topology_modal_active(c),'UV writer ran during native topology modal'
 state['updates']+=1;return original(obj)
editor.apply_edit_uv=tracked
def pos():
 rv.update();p=view3d_utils.location_3d_to_region_2d(r,rv,Vector((0,-1,1)))
 state['x']=int(r.x+p.x);state['y']=int(r.y+p.y)
steps.append(pos)
def event(kind,value='PRESS',dx=0,dy=0):
 steps.append(lambda:c.window.event_simulate(type=kind,value=value,x=state['x']+dx,y=state['y']+dy))
def held():
 names=[op.bl_idname for op in c.window.modal_operators]
 assert edit_safety.topology_modal_active(c),names
 before=state['updates']
 for _ in range(3):
  editor._live_tick();primitive_ui.sync_assemblies();transform_bridge.sync();geometry_debug.tick()
 assert state['updates']==before
 state['deferred']+=1;print('PASS safely deferred',names,flush=True)
for iteration in range(4):
 event('MOUSEMOVE','NOTHING')
 steps.append(lambda:bpy.ops.mesh.loopcut_slide('INVOKE_DEFAULT'))
 steps.append(held)
 event('ESC');event('ESC','RELEASE')
 def cut():
  result=bpy.ops.mesh.loopcut_slide('EXEC_DEFAULT',MESH_OT_loopcut={'number_cuts':1,'object_index':0,'edge_index':0},TRANSFORM_OT_edge_slide={'value':0})
  assert result=={'FINISHED'},result
  print('SLIDE INVOKE',bpy.ops.transform.edge_slide('INVOKE_DEFAULT'),flush=True)
 steps.append(cut)
 event('MOUSEMOVE','NOTHING',35,-22);steps.append(held)
 event('MOUSEMOVE','NOTHING',-25,16);steps.append(held)
 event('LEFTMOUSE','PRESS',-25,16);event('LEFTMOUSE','RELEASE',-25,16)
 def after():
  assert not edit_safety.topology_modal_active(c),[op.bl_idname for op in c.window.modal_operators]
  editor._live_tick()
 steps.append(after)
def finish():
 assert state['deferred']>=12 and state['updates']>0,state
 bpy.ops.object.mode_set(mode='OBJECT')
 assert len(obj.data.vertices)>8,(len(obj.data.vertices),len(obj.data.polygons))
 print('PASS repeated Ctrl+R cut/slide, live observers deferred, projection resumes, mode exit; topology',len(obj.data.vertices),len(obj.data.polygons),flush=True)
 bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
 try:
  with c.temp_override(area=a,region=r):
   if steps:steps.pop(0)();return .24
 except Exception:
  traceback.print_exc();print('FAIL loopcut live UV',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
