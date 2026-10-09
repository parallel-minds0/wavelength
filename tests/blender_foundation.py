"""Run with Blender --background --factory-startup --python-exit-code 1 --python."""
import sys,json,tempfile
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import scene,primitives,primitive_ui,identity,editor,asset_browser,workspace,grid
wavelength.register();settings=bpy.context.scene.wavelength;settings.engine='source_hl2_linux'
assert not bpy.app.timers.is_registered(__import__('wavelength.source.transform_sync',fromlist=['tick']).tick)
for kind in ('STAIRS','ARCH','SPHERE'):
 assert bpy.ops.wavelength.primitive(kind=kind)=={'FINISHED'}
 root=bpy.context.object
 assert root['wl_primitive']==kind
 children=list(root.children);assert children
 for obj in children:assert scene.brush_from_object(obj,settings.engine)
 values=json.loads(root['wl_parameters']);values['radius']=160;values['steps']=10
 ids=[o['wl_id'] for o in children]
 primitive_ui.rebuild(root,kind,values,bpy.context)
 assert [o['wl_id'] for o in list(root.children)[:len(ids)]]==ids
 for obj in root.children:assert scene.brush_from_object(obj,settings.engine)
 if kind=='STAIRS':
  assert len(root.children)==10
 obj=root.children[0];original=obj['wl_id'];identity.update_ids();copy=obj.copy();copy.data=obj.data.copy();bpy.context.collection.objects.link(copy);identity.update_ids()
 assert copy['wl_id']!=original and obj['wl_id']==original
 before=[obj.matrix_world@v.co for v in obj.data.vertices];obj.location.x+=.0254*16;bpy.context.view_layer.update()
 after=[obj.matrix_world@v.co for v in obj.data.vertices]
 assert all(abs((b-a).x-.0254*16)<1e-5 for a,b in zip(before,after))
# Native material assets and reusable previews, no custom gallery required.
mat=bpy.data.materials.new('test native');mat['wl_texture']='dev/test';mat.use_nodes=True
from wavelength.source.asset_index import record
asset_browser.metadata(mat,record(settings.engine,'dev/test','MATERIAL'))
assert mat.asset_data and mat['wl_asset_id']
from wavelength.source.entity import browser
assert browser.rebuild(bpy.context)>0
assert len({o['wl_entity_browser_template'] for o in bpy.data.objects if o.get('wl_entity_browser_template')})>10
wavelength.unregister();print('PASS FOUNDATION: registration, convex primitives, persistent regeneration, IDs, geometry translation, native material/entity assets')
