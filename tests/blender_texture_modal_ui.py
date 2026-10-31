import sys,json,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from bpy_extras import view3d_utils
wavelength.register()
from wavelength.source import workspace,asset_browser,asset_placement as ap
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
c.scene.wavelength.engine='source_hl2_windows';c.scene.wavelength.auto_prepare_assets=False
bpy.ops.mesh.primitive_cube_add();obj=c.object
mat=bpy.data.materials.new('Event paint test');mat['wl_texture']='event-test'
asset_browser.metadata(mat,dict(id='event',engine='source_hl2_windows',category='MATERIAL',path='event-test',validation='test'))
# Untextured local native material avoids invoking game decoders.
del mat['wl_texture']
obj.data.materials.append(mat)
from wavelength.source import external_library
external_library.schedule=lambda *a,**k:None
external_library.reference=lambda:'LOCAL'
asset_browser.reveal_texture(c,'event-test',mat)
def test():
 try:
  print('ACTIVE',ap._active,'DISMISSED',ap._dismissed,flush=True)
  browser=next(a for a in c.screen.areas if a.type=='FILE_BROWSER')
  with c.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
   print('ASSET',c.asset,'PAYLOAD',ap.payload(c),flush=True)
   if not ap._active:print('INVOKE',bpy.ops.wavelength.click_place('INVOKE_DEFAULT'),flush=True)
  area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
  pos=view3d_utils.location_3d_to_region_2d(region,area.spaces.active.region_3d,obj.location)
  event=SimpleNamespace(type='LEFTMOUSE',value='PRESS',mouse_x=region.x+pos.x,mouse_y=region.y+pos.y,shift=False,ctrl=False,alt=False)
  print('EVENT',event,'RESULT',ap._active.modal(c,event),'STATUS',c.scene.wavelength.status,flush=True)
  print('MATERIALS',[m.name for m in obj.data.materials],flush=True)
  assert mat in list(obj.data.materials)
  print('PASS browser-to-viewport modal click applies selected material',flush=True)
 except Exception:traceback.print_exc()
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=4)



