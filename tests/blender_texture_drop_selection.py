"""Selected-face drops preserve neighboring materials, UVs and export metadata."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_asset_placement.py').read_text(),__file__,'exec'))
ctx.view_layer.objects.active=obj;obj.select_set(True)
placement.paint(ctx,obj,0,materials[0],'OBJECT')
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
for face in bm.faces:face.select_set(False)
bm.faces[0].select_set(True);bm.faces[2].select_set(True)
ids=bm.faces.layers.int['wl_face_id'];uv=bm.loops.layers.uv['wavelength']
before={str(face[ids]):dict(selected=face.select,uv=[tuple(loop[uv].uv) for loop in face.loops]) for face in bm.faces}
records=json.loads(obj.data['wl_faces'])
placement.paint_drop(ctx,obj,4,materials[1],'SURFACE')
bm=bmesh.from_edit_mesh(obj.data)
after=json.loads(obj.data['wl_faces'])
for face in bm.faces:
    key=str(face[ids]);selected=before[key]['selected']
    assert face.select==selected
    assert obj.data.materials[face.material_index]==materials[1 if selected else 0]
    if selected:assert after[key]['texture']==materials[1]['wl_texture'],(after[key]['texture'],materials[1]['wl_texture'],names[1])
    else:
        assert records[key]==after[key]
        assert before[key]['uv']==[tuple(loop[uv].uv) for loop in face.loops]
for face in bm.faces:face.select_set(False)
placement.paint_drop(ctx,obj,4,materials[1],'SURFACE')
bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
assert obj.data.materials[bm.faces[4].material_index]==materials[1]
assert sum(obj.data.materials[face.material_index]==materials[1] for face in bm.faces)==3
assert not any(face.select for face in bm.faces)
print('PASS selected-face drops: exact face set, preserved neighboring UVs/export metadata, selection unchanged; no-selection drop paints hit face',flush=True)
