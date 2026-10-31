"""Real viewport clicks and drags select/move representation owners."""
import sys,traceback,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector,Quaternion
from bpy_extras.view3d_utils import location_3d_to_region_2d
wavelength.register()
from wavelength.source.entity import icons,interaction
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
if '--source' in sys.argv:c.scene.wavelength.engine='source_hl2_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
rv=a.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=7;rv.view_location=(0,0,0)
entities=[]
for name,x in [('Sprite',-1),('Model',1)]:
 e=bpy.data.objects.new(name,None);c.collection.objects.link(e);e['wl_role']='ENTITY';e['wl_pairs']=json.dumps([('classname','light')]);e.location=(x,0,0);entities.append(e)
 if name=='Sprite':assert icons.attach_reference(e)
 else:
  bpy.ops.mesh.primitive_cube_add(size=.4)
  model=c.object;model.parent=e;model.location=(0,0,0);model['wl_model_reference']=True;model['wl_exclude']=True
bpy.ops.object.select_all(action='DESELECT');c.view_layer.update()
steps=[];state={}
def event(kind,value='PRESS',dx=0):
 def run():
  p=state['pixel'];c.window.event_simulate(type=kind,value=value,x=int(r.x+p.x+dx),y=int(r.y+p.y))
 steps.append(run)
for e in entities:
 def setup(entity=e):
  bpy.ops.object.select_all(action='DESELECT');c.view_layer.update();rv.update()
  state['pixel']=location_3d_to_region_2d(r,rv,entity.matrix_world.translation)
  state['start']=entity.matrix_world.translation.copy();state['visual']=entity.children[0].matrix_basis.copy()
  assert interaction.hit(c,state['pixel'])==entity,entity.name
 steps.append(setup)
 event('LEFTMOUSE');event('LEFTMOUSE','RELEASE')
 def selected(entity=e):assert c.object==entity and entity.select_get(),entity.name
 steps.append(selected)
 event('LEFTMOUSE');event('MOUSEMOVE','NOTHING',10);event('MOUSEMOVE','NOTHING',90);event('LEFTMOUSE','RELEASE',90)
 def moved(entity=e):
  assert (entity.matrix_world.translation-state['start']).length>.01,entity.name+' did not move'
  assert entity.children[0].matrix_basis==state['visual'],'Visual local offset changed'
  assert (entity.children[0].matrix_world.translation-entity.matrix_world.translation).length<1e-5
  entity.location.y+=.5;c.view_layer.update()
  assert (entity.children[0].matrix_world.translation-entity.matrix_world.translation).length<1e-5,'Moving owner must move visual'
  entity.select_set(False);ref=entity.children[0];ref.hide_select=False;ref.select_set(True);c.view_layer.objects.active=ref
  interaction.sync_selection()
  assert c.object==entity and entity.select_get() and not ref.select_get(),'Visual selection must promote owner'
  print('PASS click/drag '+entity.name+' moves owning entity and visual together',flush=True)
 steps.append(moved)
def finish():print('PASS ENTITY VISUAL INTERACTION',flush=True);bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
 try:
  with c.temp_override(area=a,region=r):
   if steps:steps.pop(0)();return .3
 except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
