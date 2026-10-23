import sys,traceback,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import profile_ui
from wavelength.source.profile_store import Store
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
temporary=tempfile.TemporaryDirectory();original=profile_ui.store;registry=Store(temporary.name);profile_ui.store=lambda:registry
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
steps=[]
def setup():
 ctx.scene.wavelength.engine='godot4'
 assert bpy.ops.wavelength.profile(action='REGISTER',name='Studio Godot',parent='godot4')=={'FINISHED'}
 assert ctx.scene.wavelength.profile_id not in profile_ui.TEMPLATES.definitions
 props=next(a for a in ctx.screen.areas if a.type=='PROPERTIES');props.spaces.active.context='SCENE'
steps.append(setup)
def custom():
 bpy.ops.screen.screenshot(filepath=str(Path(__file__).resolve().parents[1]/'build/profile-registry-custom.png'))
 ctx.scene.wavelength.saved_profile='godot4'
steps.append(custom)
def protected():
 bpy.ops.screen.screenshot(filepath=str(Path(__file__).resolve().parents[1]/'build/profile-registry-protected.png'))
 print('PASS registry UI: register operation, protected template and user profile controls',flush=True)
 profile_ui.store=original;temporary.cleanup();bpy.ops.wm.quit_blender()
steps.append(protected)
def tick():
 try:
  with ctx.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .9
 except Exception:
  traceback.print_exc();print('FAIL REGISTRY UI',flush=True)
  profile_ui.store=original;temporary.cleanup();bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
