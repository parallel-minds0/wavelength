"""Exercise real native modal scale input, profile-size snapping and routing."""
import sys,traceback,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import transform_bridge as bridge,profiles,primitive_ui
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
s=c.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_hl2_windows';s.grid_mode='ENGINE';s.grid_step='16'
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=8;rv.view_location=(0,0,0)
ts=c.scene.tool_settings;ts.snap_elements={'GRID'};ts.use_snap_scale=True
obj=c.object;steps=[];state={};results={}
def event(kind,value='PRESS',key='start'):
 def run():
  p=state[key];c.window.event_simulate(type=kind,value=value,x=int(region.x+p.x),y=int(region.y+p.y))
 steps.append(run)
def setup(axis,snap,active=True,procedural=False):
 def run():
  global obj
  if obj.mode=='EDIT':bpy.ops.object.mode_set(mode='OBJECT')
  bpy.ops.object.select_all(action='DESELECT')
  if procedural:
   obj=bpy.data.objects.new('Native scale assembly',None);c.collection.objects.link(obj)
   primitive_ui.rebuild(obj,'CUBE',primitive_ui.DEFAULTS,c);primitive_ui.select_assembly(obj,c,True)
  else:
   obj=bpy.data.objects.get('Cube');obj.select_set(True);c.view_layer.objects.active=obj
  obj.location=(0,0,0);obj.scale=(1,1,1);c.view_layer.update()
  c.workspace['wl_workspace']=active;ts.use_snap=snap;bridge.sync_grid_policy()
  rv.view_rotation=Quaternion((1,0,0,0)) if axis!='Z' else Quaternion((1,0,0),math.pi/2)
  rv.update()
  origin=view3d_utils.location_3d_to_region_2d(region,rv,Vector((0,0,0)))
  unit=Vector((1,0,0)) if axis=='FREE' else Vector(tuple(float(a==axis) for a in 'XYZ'))
  end=view3d_utils.location_3d_to_region_2d(region,rv,unit)
  direction=(end-origin).normalized();state['start']=origin+direction*160
  state['in']=origin+direction*95;state['out']=origin+direction*225
  if procedural:
   points=[p.matrix_world@Vector(v) for p in primitive_ui.parts_for(obj) for v in p.bound_box]
   dims=Vector(tuple(max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)))
  else:dims=obj.dimensions.copy()
  state.update(axis=axis,snap=snap,active=active,original=obj.matrix_world.copy(),dims=dims)
 steps.append(run)
def invoke():
 if state['active']:bpy.ops.wavelength.transform_route('INVOKE_DEFAULT',kind='SCALE')
 else:bpy.ops.transform.resize('INVOKE_DEFAULT')
def check(direction):
 def run():
  axis=state['axis'];i=0 if axis=='FREE' else 'XYZ'.index(axis);factor=obj.scale[i]
  assert (0<factor<1 if direction=='in' else factor>1),(state,factor)
  if state['snap']:
   size=state['dims'][i]*factor;step=profiles.active_grid_step_meters(s)
   assert abs(size/step-round(size/step))<1e-4,(axis,size,step)
  results[(axis,state['snap'],state['active'],direction)]=factor
  print('PASS live native scale',axis,state['snap'],state['active'],direction,factor,flush=True)
 steps.append(run)
for active,snap,axis,procedural in [(False,False,'FREE',False),(True,False,'FREE',False),(True,True,'FREE',False),(True,True,'X',False),(True,True,'Y',False),(True,True,'Z',False),(True,True,'X',True)]:
 setup(axis,snap,active,procedural);event('MOUSEMOVE','NOTHING');steps.append(invoke)
 if axis!='FREE':event(axis);event(axis,'RELEASE')
 event('MOUSEMOVE','NOTHING','in');check('in')
 event('MOUSEMOVE','NOTHING','out');check('out')
 event('ESC');event('ESC','RELEASE')
 def cancelled():
  assert max(abs(a-b) for ra,rb in zip(obj.matrix_world,state['original']) for a,b in zip(ra,rb))<1e-5
 steps.append(cancelled)
def finish():
 for direction in ('in','out'):
  assert abs(results[('FREE',False,False,direction)]-results[('FREE',False,True,direction)])<.02
 from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as Tools
 item=Tools._tool_get_by_id(c,'builtin.scale')[0]
 assert item.widget!='WL_GGT_native_transform' and item.operator!='wavelength.transform_route'
 print('PASS native scale parity, live profile grid, XYZ, procedural assembly, cancellation and native Scale toolbar',flush=True)
 bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
 try:
  with c.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .18
 except Exception:
  traceback.print_exc();print('FAIL native scale',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
