"""Cutter boundaries: profile depth units, transforms and live modifiers."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_cutter_solid.py').read_text().split('for closed,op,through')[0],__file__,'exec'))
from mathutils import Vector
from wavelength.source import profiles

for engine in ('blender','source_hl2_windows','goldsrc_windows'):
    ctx.scene.wavelength.engine=engine
    target=cube();target.location=(3,-2,4);target.scale=(2,.5,1.5);target.rotation_euler=(.2,.3,.4)
    ctx.view_layer.update();matrix=target.matrix_world.copy()
    coords=[matrix@Vector(p) for p in [(-.5,-.5,1),(.5,-.5,1),(.5,.5,1),(-.5,.5,1)]]
    normal=(matrix.to_3x3().inverted().transposed()@Vector((0,0,1))).normalized()
    root=pencil.create_guide(ctx,[pencil.point(p) for p in coords],normal,True,target)
    st=root.wavelength_cutter;st.operation='SUBTRACT';st.through=False
    st.depth=.5/profiles.engine_to_world(ctx.scene.wavelength,1)
    pencil.apply_cut(ctx,root)
    world_volume=volume(target)*abs(matrix.determinant())
    assert abs(world_volume-11.5)<1e-4,(engine,world_volume)
    print('PASS transformed finite depth in profile',engine,flush=True)

target=cube();modifier=target.modifiers.new('Live array','ARRAY');modifier.count=2
root=pencil.create_guide(ctx,[pencil.point(p) for p in [(-2,0,1),(2,0,1)]],(0,0,1),False,target)
root.wavelength_cutter.operation='SPLIT';original=target.data
try:pencil.apply_cut(ctx,root)
except ValueError as exc:assert 'finaliz' in str(exc).lower(),str(exc)
else:raise AssertionError('Live modifiers were silently cut using the unmodified base mesh')
assert target.data==original and target.modifiers.get('Live array')
print('PASS procedural/modifier target rejection preserves source',flush=True)
