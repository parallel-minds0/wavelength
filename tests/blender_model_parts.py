"""Model source membership changes preserve pose and reject broken dependencies."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_create.py').read_text(),__file__,'exec'))
from wavelength.source import model_smd
bpy.ops.mesh.primitive_cube_add(location=(8,2,1))
part=ctx.object
part.rotation_euler=(.3,.1,.4)
part.scale=(.4,2,1)
ctx.view_layer.update()
points=[part.matrix_world@v.co for v in part.data.vertices]
part['wl_source_displacement']=True
mesh.select_set(True)
ctx.view_layer.objects.active=mesh
assert bpy.ops.wavelength.model_part()=={'FINISHED'}
assert part in life.sources(asset) and part.get('wl_model_asset')==asset
assert 'wl_source_displacement' not in part
ctx.view_layer.update()
assert max((p-part.matrix_world@v.co).length for p,v in zip(points,part.data.vertices))<1e-5
counts={}
model_smd.export(asset,ctx.scene,{},triangle_counts=counts)
assert sum(counts.values())==24
assert bpy.ops.wavelength.model_part(source_name=part.name)=={'FINISHED'}
ctx.view_layer.update()
assert part not in life.sources(asset) and part.name in ctx.scene.objects
assert life.asset_for(part) is None and part.get('wl_exclude')
assert max((p-part.matrix_world@v.co).length for p,v in zip(points,part.data.vertices))<1e-5
try:
    life.remove_source(ctx,asset,mesh)
except ValueError as exc:
    assert 'at least one' in str(exc)
else:
    raise AssertionError('Removed the final render mesh')
control=bpy.data.objects.new('Modelling control',None)
ctx.collection.objects.link(control)
mirror=mesh.modifiers.new('Controlled mirror','MIRROR')
mirror.mirror_object=control
life.add_sources(ctx,asset,[control])
try:
    life.remove_source(ctx,asset,control)
except ValueError as exc:
    assert 'required' in str(exc)
else:
    raise AssertionError('Removed a required modelling control')
assert control in life.sources(asset)
print('PASS add/remove source parts, world pose, export triangles and required-control checks')
