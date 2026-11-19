"""Collision preview uses exporter triangles and preserves authored state."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_create.py').read_text(),__file__,'exec'))
from wavelength.source import model_collision_preview as preview
from mathutils import Vector
state=asset.wavelength_model
selected=set(ctx.selected_objects)
active=ctx.object
frame=ctx.scene.frame_current
for mode in ('BOX','CONVEX','OBJECT'):
    state.collision_mode=mode
    state.collision=mesh if mode=='OBJECT' else None
    lines=preview.geometry(ctx,asset)
    assert len(lines)>=24
    for axis in range(3):
        assert abs(min(p[axis] for p in lines)-min(p[axis] for p in before))<1e-4
        assert abs(max(p[axis] for p in lines)-max(p[axis] for p in before))<1e-4
    assert set(ctx.selected_objects)==selected and ctx.object==active
    assert ctx.scene.frame_current==frame
    assert mesh.data==data
state.collision_mode='NONE'
try:
    preview.geometry(ctx,asset)
except ValueError as exc:
    assert 'collision mode' in str(exc)
else:
    raise AssertionError('NONE collision accepted')
assert not any(obj.get('wl_collision_preview') for obj in bpy.data.objects)
print('PASS collision preview bounds match transformed source for BOX, CONVEX and assigned collision')
