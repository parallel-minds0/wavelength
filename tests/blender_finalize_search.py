"""Exercise normal menu search without Search All Operators enabled."""
import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.preferences.view.show_developer_ui=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
steps=[];state={}
def setup():
 assert bpy.ops.wavelength.primitive(kind='CUBE')=={'FINISHED'}
 from wavelength.source import primitive_ui
 state['root']=primitive_ui.root_for(ctx.object)
 assert bpy.ops.wavelength.finalize_primitive.poll()
steps.append(setup)
def send(key,text=None):
 def event():
  kw=dict(type=key,value='PRESS',x=region.x+region.width//2,y=region.y+region.height//2)
  if text:kw['unicode']=text
  ctx.window.event_simulate(**kw)
  ctx.window.event_simulate(type=key,value='RELEASE',x=kw['x'],y=kw['y'])
 steps.append(event)
send('F3')
for char in 'final':send(char.upper(),char)
def capture():bpy.ops.screen.screenshot(filepath=str(Path(__file__).resolve().parents[1]/'build/finalize-search.png'))
steps.append(capture);send('RET')
def verify():
 assert state['root'].get('wl_procedural_state')=='FINALIZED'
 print('PASS normal F3 search finds and executes Finalize Geometry',flush=True)
 bpy.ops.wm.quit_blender()
steps.append(verify)
def tick():
 try:
  with ctx.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .35
 except Exception:traceback.print_exc();print('FAIL FINALIZE SEARCH',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
