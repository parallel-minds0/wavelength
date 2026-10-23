"""Separate capped objects and inherit used texture slots/UVs on new cut faces."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_cutter_solid.py').read_text().split('ctx.scene.wavelength_draw.separate_objects=False')[0],__file__,'exec'))
from unittest.mock import patch
ctx.scene.wavelength_draw.separate_objects=True
used=[bpy.data.materials.new('Used Texture '+str(i)) for i in range(2)]
unused=bpy.data.materials.new('Unused Slot')
def cut(keep,multi=False,separate=True):
    target=cube();target.name='Textured Split';original=target.data
    target.data.materials.append(None);target.data.materials.append(used[0])
    target.data.materials.append(used[1]);target.data.materials.append(unused)
    for face in target.data.polygons:face.material_index=1+(face.index%2 if multi else 0)
    uv=target.data.uv_layers.active
    before=[tuple(value.uv) for value in uv.data]
    root=pencil.create_guide(ctx,[pencil.point(p) for p in [(-2,0,1),(2,0,1)]],(0,0,1),False,target)
    st=root.wavelength_cutter;st.operation='SPLIT';st.keep=keep;st.separate_objects=separate
    def pick(values):
        assert set(values)==set(used if multi else used[:1]),values
        return used[1] if multi else used[0]
    with patch('wavelength.source.cutter_solid.random.choice',side_effect=pick):pieces=pencil.apply_cut(ctx,root)
    expected=used[1] if multi else used[0]
    outputs=[target]+pieces
    assert len(outputs)==(2 if keep=='BOTH' and separate else 1)
    assert len(ctx.selected_objects)==len(outputs)
    assert abs(sum(volume(obj) for obj in outputs)-(8 if keep=='BOTH' else 4))<1e-4
    for obj in outputs:
        assert obj.data.uv_layers
        caps=[face for face in obj.data.polygons if all(abs(obj.data.vertices[i].co.y)<1e-5 for i in face.vertices)]
        assert caps,'Expected a capped cutting plane'
        for face in caps:
            assert obj.data.materials[face.material_index]==expected
            coords=[tuple(obj.data.uv_layers.active.data[i].uv) for i in face.loop_indices]
            assert len(set(coords))>=3,('Cap UVs collapsed',coords)
        for face in obj.data.polygons:
            assert obj.data.materials[face.material_index] in used,(obj.name,face.index,face.material_index,[m.name if m else None for m in obj.data.materials],[(tuple(obj.data.vertices[i].co)) for i in face.vertices])
    assert target.data!=original
    if pieces:assert pieces[0].data!=target.data and pieces[0].matrix_world==target.matrix_world
    print('PASS capped materials/UV and output objects',keep,multi,separate,flush=True)
for keep in ('BOTH','OUTSIDE','INSIDE'):
    for multi in (False,True):cut(keep,multi)
cut('BOTH',True,False)
print('PASS SEPARATE OBJECTS AND CAP TEXTURES',flush=True)
