"""Named model revisions preserve an editable snapshot and restore an independent variant."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_create.py').read_text(),__file__,'exec'))
from wavelength.source import model_revisions as revisions
selected=set(ctx.selected_objects)
active=ctx.object
original_points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
entry=revisions.save(ctx,asset,'Before bending')
assert set(ctx.selected_objects)==selected and ctx.object==active
assert revisions.records(asset)[0]['name']=='Before bending'
mesh.data.vertices[0].co.z+=3
ctx.view_layer.update()
changed=[mesh.matrix_world@v.co for v in mesh.data.vertices]
variant=revisions.open_variant(ctx,asset,entry['id'])
restored=next(obj for obj in life.sources(variant) if obj.type=='MESH')
assert variant!=asset and restored.data!=mesh.data
assert variant['wl_model_id']!=asset['wl_model_id']
assert 'wl_model_publish_settings' not in variant and not revisions.records(variant)
ctx.view_layer.update()
assert max((expected-restored.matrix_world@vertex.co).length for expected,vertex in zip(original_points,restored.data.vertices))<1e-4
assert max((expected-mesh.matrix_world@vertex.co).length for expected,vertex in zip(changed,mesh.data.vertices))<1e-5
snapshot=Path(entry['path'])
payload=snapshot.read_bytes()
snapshot.write_bytes(payload+b'changed')
collections=set(bpy.data.collections)
try:
    revisions.open_variant(ctx,asset,entry['id'])
except ValueError as exc:
    assert 'has changed' in str(exc)
else:
    raise AssertionError('Modified checkpoint accepted')
assert set(bpy.data.collections)==collections
snapshot.write_bytes(payload)
# Restoring a selected placement preserves the other instance's edited model.
import json
import uuid
def placement(name,location):
    obj=bpy.data.objects.new(name,None)
    ctx.collection.objects.link(obj)
    obj['wl_role']='ENTITY'
    obj['wl_id']=uuid.uuid4().hex
    obj['wl_unit_meters']=.0254
    obj['wl_owner_profile']=s.engine
    obj['wl_pairs']=json.dumps([['classname','prop_static']])
    obj.location=location
    ctx.view_layer.update()
    return obj
first=placement('Restored placement',(8,2,1))
second=placement('Other placement',(-4,6,2))
life.attach(ctx,asset,first)
life.attach(ctx,asset,second)
ctx.view_layer.objects.active=first
pose=first.matrix_world.copy()
old_geometry=[vertex.co.copy() for vertex in mesh.data.vertices]
restored_asset=revisions.restore_placement(ctx,asset,entry['id'])
assert first['wl_custom_model']==restored_asset
assert second['wl_custom_model']==asset
assert first.matrix_world==pose
assert [tuple(vertex.co) for vertex in mesh.data.vertices]==[tuple(point) for point in old_geometry]
history=revisions.records(restored_asset)
assert len(history)==2 and history[-1]['name']=='Before revision restore'
assert Path(history[-1]['path']).is_file()
assert restored_asset['wl_model_revision_source']==entry['id']
name=asset.name
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'revisions.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'revisions.blend'))
assert revisions.records(bpy.data.collections[name])[0]['id']==entry['id']
print('PASS named checkpoint, independent restoration, modified-package rejection and revision list save/reopen')
