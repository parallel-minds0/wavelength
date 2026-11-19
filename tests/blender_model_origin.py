"""Model pivot movement preserves authored geometry and linked placements."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_create.py').read_text(),__file__,'exec'))
from mathutils import Vector
import json
import uuid
def world_points(obj):
    return [obj.matrix_world@vertex.co for vertex in obj.data.vertices]
def close(first,second):
    return max((a-b).length for a,b in zip(first,second))<1e-4
before_points=world_points(mesh)
ctx.scene.cursor.location=(12,7,3)
assert bpy.ops.wavelength.model_origin()=={'FINISHED'}
ctx.view_layer.update()
assert close(world_points(mesh),before_points)
assert (asset.wavelength_model.origin.matrix_world.translation-ctx.scene.cursor.location).length<1e-5
def entity(name,location,rotation):
    obj=bpy.data.objects.new(name,None)
    ctx.collection.objects.link(obj)
    obj['wl_role']='ENTITY'
    obj['wl_id']=uuid.uuid4().hex
    obj['wl_unit_meters']=.0254
    obj['wl_owner_profile']=s.engine
    obj['wl_pairs']=json.dumps([['classname','prop_static']])
    obj.location=location
    obj.rotation_euler=rotation
    ctx.view_layer.update()
    return obj
first=entity('Pivot A',(3,2,1),(.1,.2,.4))
second=entity('Pivot B',(-4,6,2),(.3,-.2,1.2))
life.attach(ctx,asset,first)
life.attach(ctx,asset,second)
ctx.view_layer.update()
reference=next(obj for obj in second.children if obj.get('wl_model_linked_asset')==asset)
first_points=world_points(mesh)
second_points=[reference.matrix_world@point for point in first_points]
ctx.view_layer.objects.active=second
ctx.scene.cursor.location=(5,8,4)
assert bpy.ops.wavelength.model_origin()=={'FINISHED'}
ctx.view_layer.update()
assert close(world_points(mesh),first_points)
assert close([reference.matrix_world@point for point in world_points(mesh)],second_points)
assert (second.matrix_world.translation-ctx.scene.cursor.location).length<1e-4
assert first['wl_custom_model']==asset and second['wl_custom_model']==asset
assert ctx.object==second
print('PASS standalone and rotated linked-instance pivot relocation preserves world geometry')
