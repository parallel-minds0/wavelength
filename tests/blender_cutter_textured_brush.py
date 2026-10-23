"""Cut textured GoldSrc brushes and validate cap textures in export face records."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_asset_placement.py').read_text(),__file__,'exec'))
from wavelength.source import pencil
ctx.scene.wavelength_draw.separate_objects=True
for keep in ('OUTSIDE','INSIDE','BOTH'):
    bpy.ops.mesh.primitive_cube_add();target=ctx.object;scene.mark_brush(target)
    placement.paint(ctx,target,0,materials[0],'OBJECT')
    root=pencil.create_guide(ctx,[pencil.point(p) for p in [(-2,0,1),(2,0,1)]],(0,0,1),False,target)
    st=root.wavelength_cutter;st.operation='SPLIT';st.keep=keep
    pieces=pencil.apply_cut(ctx,root)
    for output in [target]+pieces:
        faces=scene.brush_from_object(output,s.engine,require_texture=True)
        assert all(face.texture==materials[0]['wl_texture'] for face in faces)
        assert len(faces)==6
    if pieces:assert pieces[0]['wl_id']!=target['wl_id']
    print('PASS textured brush cap/export and unique brush IDs',keep,flush=True)
