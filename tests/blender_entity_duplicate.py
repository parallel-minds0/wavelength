"""Native entity duplication retains independently parented visual references."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import identity
for kind in ('MESH','CURVE','INSTANCE'):
 data=(bpy.data.meshes.new('visual mesh') if kind=='MESH' else bpy.data.curves.new('icon','CURVE') if kind=='CURVE' else None)
 source=bpy.data.objects.new('Entity '+kind,None);bpy.context.collection.objects.link(source)
 source['wl_role']='ENTITY';source['wl_id']='source-'+kind
 visual=bpy.data.objects.new('Visual '+kind,data);bpy.context.collection.objects.link(visual);visual.parent=source
 visual['wl_entity_icon_reference' if kind=='CURVE' else 'wl_model_reference']=True
 visual['wl_exclude']=True;visual['wl_role']='MODEL_REFERENCE';visual.hide_select=True;visual.location=(.1,.2,.3)
 if kind=='INSTANCE':
  visual.instance_type='COLLECTION';visual.instance_collection=bpy.data.collections.new('Cached model')
 identity.update_ids();source_id=source['wl_id']
 for linked in (False,True):
  bpy.ops.object.select_all(action='DESELECT');source.select_set(True);bpy.context.view_layer.objects.active=source
  bpy.ops.object.duplicate(linked=linked)
  duplicate=bpy.context.object
  identity.update_ids();bpy.context.view_layer.update()
  assert duplicate!=source
  assert len(duplicate.children)==1,(kind,linked,list(duplicate.children))
  ref=duplicate.children[0]
  assert ref!=visual and ref.parent==duplicate
  assert ref.data==visual.data
  assert ref.matrix_basis==visual.matrix_basis
  assert ref.hide_select==visual.hide_select and ref['wl_exclude']
  assert duplicate['wl_id']!=source_id and source['wl_id']==source_id
  original=visual.matrix_world.copy();duplicate.location.x+=3;bpy.context.view_layer.update()
  assert visual.matrix_world==original
  identity.update_ids();assert len(duplicate.children)==1
  if kind=='INSTANCE':assert ref.instance_collection==visual.instance_collection
 # Selecting entity and visual together must not create a second representation.
 bpy.ops.object.select_all(action='DESELECT');visual.hide_select=False;source.select_set(True);visual.select_set(True);bpy.context.view_layer.objects.active=source
 bpy.ops.object.duplicate();identity.update_ids()
 duplicate=next(o for o in bpy.context.selected_objects if o.get('wl_role')=='ENTITY')
 assert len(duplicate.children)==1,(kind,len(duplicate.children))
print('PASS native entity duplication: mesh, SVG curve, collection instance; Shift+D/Alt+D; independent parents, shared assets, stable source IDs, no duplicate visuals',flush=True)
