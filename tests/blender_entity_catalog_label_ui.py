import bpy,traceback,time
bpy.context.preferences.use_preferences_save=False
placed=bpy.data.objects.new('prop_static',None);bpy.context.collection.objects.link(placed)
asset=bpy.data.objects.new('prop_static',None);asset['wl_entity_browser_template']='prop_static';asset.asset_mark()
assert asset.name!='prop_static'
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');area.type='FILE_BROWSER';area.ui_type='ASSETS'
attempts=0
def check():
 global attempts
 attempts+=1
 try:
  space=area.spaces.active
  if space.params is None:return .2
  if space.params.asset_library_reference!='LOCAL':space.params.asset_library_reference='LOCAL'
  space.activate_asset_by_id(asset,deferred=False)
  with bpy.context.temp_override(area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
   selected=bpy.context.asset
   if selected is None:
    assert attempts<30,'Asset browser did not finish loading'
    return .2
   assert selected.local_id==asset
   assert selected.name=='prop_static',(selected.name,asset.name)
   assert asset.name!='prop_static' and placed.name=='prop_static'
  print('PASS native catalog display: prop_static label with unique template ID, placed object name unchanged',flush=True)
 except Exception:traceback.print_exc()
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1)
