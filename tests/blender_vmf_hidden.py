"""Hidden world solids, brush entities and point entities survive interchange."""
import copy
import json
import sys
import tempfile
from pathlib import Path

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import wavelength
wavelength.register()
from wavelength.source import formats, scene, vmf

root = Path(__file__).resolve().parents[1]
base = vmf.parse((root / 'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
brush = copy.deepcopy(base.entities[0].brushes[0])
for face in brush:
    face.vmf['hidden'] = True
document = formats.Map([
    formats.Entity([('classname', 'worldspawn')], [brush]),
    formats.Entity([('classname', 'func_detail')], [copy.deepcopy(brush)], vmf_hidden=True),
    formats.Entity([('classname', 'info_target'), ('origin', '128 64 32'),
                    (vmf.OUTPUT + 'OnUser1', 'target\x1bUse\x1b\x1b0\x1b-1')], vmf_hidden=True),
])
document.vmf_visgroups = [('visgroups', [('visgroup', [
    ('name', 'Architecture'), ('visgroupid', '8'), ('color', '50 80 110'),
    ('visgroup', [('name', 'Trim'), ('visgroupid', '9'), ('color', '70 80 90')]),
])])]
document.entities[0].brushes[0][0].vmf['visgroup'] = [('visgroupid', '8'), ('visgroupid', '9'), ('color', '42 102 203')]
document.entities[1].vmf_visgroup = [('visgroupid', '8'), ('visgroupshown', '0'), ('color', '91 202 33')]
document.entities[2].vmf_visgroup = [('visgroupid', '9'), ('visgroupautoshown', '1'), ('color', '255 93 42')]


document.entities[0].brushes[0][0].vmf.update(contents='1', flags='128')
document.vmf_cameras = [('cameras', [
    ('activecamera', '1'),
    ('camera', [('position', '[128.25 -64 32]'), ('look', '[256 0 64]')]),
    ('camera', [('position', '[-20 40 80]'), ('look', '[0 0 0]')]),
])]

document.entities[0].pairs.append(('mapversion', '42'))
document.vmf_view_metadata = [
    ('versioninfo', [('editorversion', '400'), ('editorbuild', '9999'), ('mapversion', '43')]),
    ('viewsettings', [('bSnapToGrid', '1'), ('nGridSpacing', '32')]),
    ('cordon', [('mins', '(-64 -64 -64)'), ('maxs', '(64 64 64)'), ('active', '0')]),
    ('cordons', [('active', '0'), ('cordon', [
        ('name', 'Courtyard'), ('active', '1'),
        ('box', [('mins', '(-128 -64 0)'), ('maxs', '(128 64 256)')]),
    ])]),
]

# Hammer++ metadata is opaque. Keys that resemble object-group references
# inside these blocks belong to the extension and must remain unchanged.
for root_name in ('palette_plus', 'colorcorrection_plus', 'light_plus', 'postprocess_plus', 'bgimages_plus'):
    document.vmf_view_metadata.append((root_name, [
        ('entry', [('name', 'First'), ('groupid', '2')]),
        ('entry', [('name', 'Second'), ('groupid', '7')]),
    ]))

# Object groups have their own ID space on input. The writer allocates IDs
# alongside entities, solids and sides and remaps group-to-group membership.
world = document.entities[0]
world.vmf_groups = [[('id', '1')], [('id', '2'), ('editor', [('groupid', '1')])]]
world.brushes[0][0].vmf['visgroup'].append(('groupid', '2'))
document.entities[-1].vmf_visgroup.append(('groupid', '1'))
grouped = vmf.parse(vmf.write(document))
outer, inner = grouped.entities[0].vmf_groups
outer_id, inner_id = dict(outer)['id'], dict(inner)['id']
assert outer_id != '1' and inner_id != '2'
assert dict(dict(inner)['editor'])['groupid'] == outer_id
assert dict(grouped.entities[0].brushes[0][0].vmf['visgroup'])['groupid'] == inner_id
assert dict(grouped.entities[-1].vmf_visgroup)['groupid'] == outer_id
assert not vmf.parse(vmf.write(document, editor_metadata=False)).entities[0].vmf_groups



def visgroups(doc):
    return json.dumps([doc.vmf_visgroups, [
        [entity.vmf_visgroup, [(brush[0].vmf or {}).get('visgroup', []) for brush in entity.brushes]]
        for entity in doc.entities
    ]])


def signature(doc):
    return [(e.vmf_hidden, [any((f.vmf or {}).get('hidden') for f in b) for b in e.brushes]) for e in doc.entities]

decoded = vmf.parse(vmf.write(document))
assert signature(decoded) == signature(document)
assert dict(decoded.entities[-1].pairs)[vmf.OUTPUT + 'OnUser1'] == 'target,Use,,0,-1'
c = bpy.context
c.scene.wavelength.engine = 'source_hl2_windows'
c.scene.wavelength.auto_prepare_assets = False
from wavelength.source import map_import
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory) / 'visgroups.vmf'
    fixture.write_text(vmf.write(document), encoding='utf-8')
    session = map_import.Session(c, fixture)
    try:
        import time
        while not session.advance():
            assert time.monotonic() - session.started < 60
            time.sleep(.02)
        collection = c.scene.collection.children['wavelength Map']
    finally:
        session.close()
        from wavelength.source import render_support
        render_support.loaded()
assert all(obj.hide_get() for obj in collection.objects if obj.get('wl_role') in {'BRUSH', 'ENTITY'})
exported = vmf.parse(vmf.write(scene.export_map(c.scene)))
assert signature(exported) == signature(document), signature(exported)
assert visgroups(exported) == visgroups(grouped)
assert json.dumps(exported.entities[0].vmf_groups) == json.dumps(grouped.entities[0].vmf_groups)
compiler_document = vmf.parse(vmf.write(scene.export_map(c.scene), editor_metadata=False))
assert json.dumps(exported.vmf_cameras) == json.dumps(document.vmf_cameras)
assert json.dumps(exported.vmf_view_metadata) == json.dumps(document.vmf_view_metadata)
assert dict(exported.entities[0].pairs)['mapversion'] == '42'
assert 'mapversion' not in dict(compiler_document.entities[0].pairs)
assert [name for name, _ in compiler_document.vmf_view_metadata] == ['versioninfo']
assert dict(compiler_document.vmf_view_metadata[0][1])['mapversion'] == '1'
assert not compiler_document.vmf_cameras
for kind in ('cordon', 'cordons'):
    try:
        vmf.parse(f'{kind} {{ "active" "1" }} world {{ "classname" "worldspawn" }}')
    except ValueError as exc:
        assert 'Disable the active Hammer cordon' in str(exc)
    else:
        raise AssertionError('Active cordon accepted')
assert not compiler_document.vmf_visgroups
assert all(not entity.vmf_visgroup for entity in compiler_document.entities)
assert all('visgroup' not in brush[0].vmf for entity in compiler_document.entities for brush in entity.brushes)
assert signature(compiler_document) == signature(document)
for result in (exported, compiler_document):
    faces = result.entities[0].brushes[0]
    assert faces[0].vmf['contents'] == '1'
    assert faces[0].vmf['flags'] == '128'
    assert all('contents' not in face.vmf and 'flags' not in face.vmf for face in faces[1:])


# Edit a single Source face and leave its texture projection and neighbors intact.
c.workspace['wl_workspace'] = True
brush_obj = next(obj for obj in collection.objects if obj.get('wl_role') == 'BRUSH')
for obj in c.selected_objects:
    obj.select_set(False)
brush_obj.hide_set(False)
brush_obj.select_set(True)
c.view_layer.objects.active = brush_obj
c.scene.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.object.mode_set(mode='EDIT')
import bmesh
bm = bmesh.from_edit_mesh(brush_obj.data)
bpy.ops.mesh.select_all(action='DESELECT')
bm.faces.ensure_lookup_table()
bm.faces[0].select_set(True)
fid = str(bm.faces[0][bm.faces.layers.int['wl_face_id']])
before = json.loads(brush_obj.data['wl_faces'])
c.scene.wavelength.texture_lightmap = 48
assert bpy.ops.wavelength.apply_texture(lightmap_only=True) == {'FINISHED'}
assert c.mode == 'EDIT_MESH'
after = json.loads(brush_obj.data['wl_faces'])
expected = copy.deepcopy(before)
expected[fid]['vmf']['lightmapscale'] = '48'
assert after == expected
assert bpy.ops.wavelength.read_face_texture() == {'FINISHED'}
assert c.scene.wavelength.texture_lightmap == 48
c.scene.wavelength.texture_smoothing_groups = '2147483653'
assert bpy.ops.wavelength.apply_texture(smoothing_only=True) == {'FINISHED'}
assert c.mode == 'EDIT_MESH'
expected[fid]['vmf']['smoothing_groups'] = '-2147483643'
assert json.loads(brush_obj.data['wl_faces']) == expected
assert bpy.ops.wavelength.read_face_texture() == {'FINISHED'}
assert c.scene.wavelength.texture_smoothing_groups == '-2147483643'
settings = c.scene.wavelength
settings.texture_contents = '32'
assert bpy.ops.wavelength.apply_texture(face_flag='CONTENTS') == {'FINISHED'}
expected[fid]['vmf']['contents'] = '32'
settings.texture_surface_flags = '16'
assert bpy.ops.wavelength.apply_texture(face_flag='FLAGS') == {'FINISHED'}
expected[fid]['vmf']['flags'] = '16'
assert bpy.ops.wavelength.read_face_texture() == {'FINISHED'}
assert (settings.texture_contents, settings.texture_surface_flags) == ('32', '16')
assert json.loads(brush_obj.data['wl_faces']) == expected
settings.texture_surface_flags = ''
assert bpy.ops.wavelength.apply_texture(face_flag='FLAGS') == {'FINISHED'}
del expected[fid]['vmf']['flags']
assert json.loads(brush_obj.data['wl_faces']) == expected
assert c.mode == 'EDIT_MESH'
bpy.ops.object.mode_set(mode='OBJECT')
edited = vmf.parse(vmf.write(scene.export_map(c.scene)))
assert sum((f.vmf or {}).get('lightmapscale') == '48'
           for e in edited.entities for b in e.brushes for f in b) == 1
assert sum((f.vmf or {}).get('smoothing_groups') == '-2147483643'
           for e in edited.entities for b in e.brushes for f in b) == 1

compiler_faces = [f for e in vmf.parse(vmf.write(scene.export_map(c.scene), editor_metadata=False)).entities
                  for b in e.brushes for f in b]
changed, = [f for f in compiler_faces if f.vmf.get('contents') == '32']
assert 'flags' not in changed.vmf

# Transfer all four settings together, including clearing optional overrides.
bpy.ops.object.mode_set(mode='EDIT')
settings.texture_lightmap = 64
settings.texture_smoothing_groups = '3'
settings.texture_contents = ''
settings.texture_surface_flags = '128'
assert bpy.ops.wavelength.apply_texture(face_flag='ALL') == {'FINISHED'}
assert c.mode == 'EDIT_MESH'
metadata = expected[fid]['vmf']
metadata.update(lightmapscale='64', smoothing_groups='3', flags='128')
del metadata['contents']
assert json.loads(brush_obj.data['wl_faces']) == expected
settings.texture_smoothing_groups = 'invalid'
settings.texture_lightmap = 80
try:
    bpy.ops.wavelength.apply_texture(face_flag='ALL')
except RuntimeError as exc:
    assert 'decimal smoothing group mask' in str(exc)
else:
    raise AssertionError('Invalid mask accepted')
assert json.loads(brush_obj.data['wl_faces']) == expected
bpy.ops.object.mode_set(mode='OBJECT')
compiled = vmf.parse(vmf.write(scene.export_map(c.scene), editor_metadata=False))
face, = [f for e in compiled.entities for b in e.brushes for f in b if f.vmf.get('lightmapscale') == '64']
assert face.vmf['smoothing_groups'] == '3' and face.vmf['flags'] == '128'
assert 'contents' not in face.vmf

# Reject unknown payloads instead of treating hidden as a validation escape.
try:
    vmf.parse('world { "classname" "worldspawn" hidden { unsupported {} } }')
except ValueError as exc:
    assert 'unsupported' in str(exc)
else:
    raise AssertionError('Unknown hidden payload accepted')
print('PASS hidden VMF: world/brush/point containers, Blender visibility, output connections, scene round trip and strict validation', flush=True)

if '--map' in sys.argv:
    path = Path(sys.argv[sys.argv.index('--map') + 1])
    actual = vmf.parse(path.read_text(encoding='utf-8-sig'))
    roundtrip = vmf.parse(vmf.write(actual))
    assert signature(actual) == signature(roundtrip)
    def object_colors(doc):
        return [
            ([v for k, v in e.vmf_visgroup if k == 'color'],
             [[v for k, v in (b[0].vmf or {}).get('visgroup', []) if k == 'color'] for b in e.brushes])
            for e in doc.entities
        ]

    assert object_colors(actual) == object_colors(roundtrip)
    assert actual.vmf_cameras == roundtrip.vmf_cameras
    assert actual.vmf_view_metadata == roundtrip.vmf_view_metadata
    assert dict(actual.entities[0].pairs).get('mapversion') == dict(roundtrip.entities[0].pairs).get('mapversion')
    assert sum(len(e.vmf_groups) for e in actual.entities) == sum(len(e.vmf_groups) for e in roundtrip.entities)
    assert sum(len(b) for e in actual.entities for b in e.brushes) == sum(len(b) for e in roundtrip.entities for b in e.brushes)
    print('PASS actual map:', path, 'entities', len(actual.entities), 'hidden entities', sum(e.vmf_hidden for e in actual.entities), 'hidden brushes', sum(any((f.vmf or {}).get('hidden') for f in b) for e in actual.entities for b in e.brushes), flush=True)
