import sys,json,traceback
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
from bpy_extras import view3d_utils
wavelength.register()
from wavelength.source import workspace,scene,vmf,asset_browser,asset_placement as ap,external_library
root=Path(__file__).resolve().parents[3]
mat=None;obj=None
bpy.context.preferences.use_preferences_save=False
# A real, small VMF with Source brush textures and real HL2 asset decoding.
def setup():
 global mat,obj
 try:
  c=bpy.context;c.workspace['wl_workspace']=True
  s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
  s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
  scene.import_map(c.scene,vmf.parse((root/'maps/source1-fixed/level.vmf').read_text()),defer_assets=False)
  obj=next(o for o in c.scene.objects if o.get('wl_role')=='BRUSH')
  mat=asset_browser.publish_material_fast(s,'brick/brickwall001a')
  from wavelength.source.entity import browser
  window,screen,area=browser.ensure_browser_layout(c,'TEXTURES')
  def select():
   p=area.spaces.active.params
   if p is None:return .1
   p.asset_library_reference='LOCAL';p.filter_search='';p.catalog_id=''
   area.spaces.active.activate_asset_by_id(mat,deferred=False)
   bpy.app.timers.register(test,first_interval=2)
  bpy.app.timers.register(select,first_interval=1)
 except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
def test():
 try:
  c=bpy.context;browser=next(a for a in c.screen.areas if a.type=='FILE_BROWSER')
  with c.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
   print('MAT',mat.name,mat.asset_data,'FILTER',browser.spaces.active.params.filter_search,flush=True);browser.spaces.active.activate_asset_by_id(mat,deferred=False)
   print('BROWSER',c.asset,'LIB',browser.spaces.active.params.asset_library_reference,'ACTIVE',ap._active,'STATUS',c.scene.wavelength.status,flush=True)
   print('PAYLOAD',ap.payload(c),flush=True)
   if not ap._active:print('INVOKE',bpy.ops.wavelength.click_place('INVOKE_DEFAULT'),flush=True)
  area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
  target=obj.matrix_world@sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
  rv.view_location=target;rv.view_distance=12;rv.view_perspective='PERSP'
  pos=view3d_utils.location_3d_to_region_2d(region,rv,target)
  event=SimpleNamespace(type='LEFTMOUSE',value='PRESS',mouse_x=region.x+pos.x,mouse_y=region.y+pos.y,shift=False,ctrl=False,alt=False)
  print('CLICK',ap._active.modal(c,event),'STATUS',c.scene.wavelength.status,flush=True)
  assert any(o.data.materials[p.material_index].get('wl_texture')=='brick/brickwall001a' for o in c.scene.objects if o.type=='MESH' and o.data.materials for p in o.data.polygons)
  # Exercise the drag-release route through the same modal handler.
  ap._active.dragging=True
  ap._active.drag_start=(browser.x+20,browser.y+40)
  event.value='RELEASE'
  print('DROP',ap._active.modal(c,event),'STATUS',c.scene.wavelength.status,flush=True)
  assert c.scene.wavelength.status.startswith('Placed ')
  session=ap._active
  session.finish(c,dismiss=True)
  assert ap._dismissed is not None
  with c.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
   assert bpy.ops.wavelength.arm_asset('INVOKE_DEFAULT')=={'PASS_THROUGH'}
  assert ap._dismissed is None
  # Recovering an invalidated modal session must not suppress this asset.
  session.closed=False;session.finish(c)
  assert ap._dismissed is None
  print('PASS VMF Source material interactive click',flush=True)
 except Exception:traceback.print_exc()
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(setup,first_interval=2)




