"""Real event regression: Blender --enable-event-simulate --factory-startup --python."""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,scene
wavelength.register();bpy.context.preferences.view.show_splash=False
stage=0;point=(0,0);before=None
def key(type,unicode='',ctrl=False):
 w=bpy.context.window
 w.event_simulate(type=type,value='PRESS',unicode=unicode,x=point[0],y=point[1],ctrl=ctrl)
 w.event_simulate(type=type,value='RELEASE',x=point[0],y=point[1],ctrl=ctrl)
def tick():
 global stage,point,before
 try:
  if stage==0:bpy.context.window.workspace=workspace.ensure(bpy.context)
  elif stage==1:
   s=bpy.context.scene.wavelength;s.engine='source_hl2_linux';s.grid_mode='ENGINE'
   obj=bpy.data.objects['Cube'];scene.mark_brush(obj);bpy.context.view_layer.objects.active=obj
   before=(obj.matrix_world@obj.data.vertices[0].co).copy()
   bpy.context.scene.tool_settings.use_transform_data_origin=True
   area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');r=next(r for r in area.regions if r.type=='WINDOW');point=(r.x+r.width//2,r.y+r.height//2)
   bpy.context.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=point[0],y=point[1])
  elif stage==2:key('G')
  elif stage==3:key('X')
  elif stage==4:key('ONE','1');key('SIX','6')
  elif stage==5:key('RET')
  elif stage==6:
   obj=bpy.data.objects['Cube'];assert abs(obj.location.x-.4064)<1e-5,obj.location[:]
   world=obj.matrix_world@obj.data.vertices[0].co;assert abs(world.x-(before.x+.4064))<1e-5,world
   key('Z',ctrl=True)
  elif stage==7:
   assert abs(bpy.data.objects['Cube'].location.x)<1e-5,bpy.data.objects['Cube'].location[:]
   key('G')
  elif stage==8:key('X');key('THREE','3');key('TWO','2')
  elif stage==9:key('ESC')
  else:
   assert abs(bpy.data.objects['Cube'].location.x)<1e-5
   print('PASS MOVE: simulated G/X/16, geometry moves with origin-only setting, Undo, Escape rollback',flush=True);bpy.ops.wm.quit_blender();return
  stage+=1;return .6
 except Exception:
  import traceback;traceback.print_exc();print('FAIL MOVE',stage,flush=True);bpy.ops.wm.quit_blender();return
bpy.app.timers.register(tick,first_interval=3)
