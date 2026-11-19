"""Run with Blender in background. Pass -- --compile for the local HL2 check."""
import json
from pathlib import Path
import subprocess
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'addon'))
import wavelength
from wavelength.source import displacement, formats, primitives, scene, source_displacement, terrain_surface, vmf

wavelength.register()
context = bpy.context
engine = 'source_hl2_windows'
context.scene.wavelength.engine = engine
unit = .03125
bindings = []
brushes = []
for index, (left, right) in enumerate(((0, 0), (0, 64), (64, 64))):
    bpy.ops.mesh.primitive_cube_add(size=2, location=((index * 128 + 64) * unit, 0, 0))
    host = context.object
    for vertex in host.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x * 64 * unit, y * 64 * unit,
                     ((left if x < 0 else right) if z > 0 else -64) * unit)
    host.data.update()
    scene.mark_brush(host)
    host['wl_unit_meters'] = unit
    polygon = max(host.data.polygons, key=lambda p: p.normal.z)
    face_id = host.data.attributes['wl_face_id'].data[polygon.index].value
    solid = scene.brush_from_object(host, engine)
    for side in solid:
        side.texture = 'tools/toolsnodraw'
    face = solid[polygon.index]
    corners = [scene.world_point(host, host.data.vertices[i].co, unit) for i in polygon.vertices]
    quad = source_displacement._export_quad(host, face_id, corners)
    face.texture = 'nature/dirtfloor001a'
    brushes.append(solid)
    bindings.append((host, face_id, quad, face))

mesh = terrain_surface.cage('Three-brush terrain', [[Vector(p) * unit for p in quad] for _, _, quad, _ in bindings])
terrain = bpy.data.objects.new(mesh.name, mesh)
context.collection.objects.link(terrain)
terrain['wl_terrain_prototype_bindings'] = json.dumps([
    {'brush': host['wl_id'], 'face': face_id} for host, face_id, _, _ in bindings
])
assert len(mesh.vertices) == 8
power = 3
size = 2 ** power + 1
modifier = terrain.modifiers.new('Native subdivision', 'SUBSURF')
modifier.levels = 3
modifier.uv_smooth = 'NONE'

def world_samples():
    context.view_layer.update()
    return terrain_surface.sample(terrain, context.evaluated_depsgraph_get(), len(bindings), power)

def seam(grids, x, left, right):
    base = [sorted((point for point in grid if abs(point.x - x * unit) < 1e-5), key=lambda p:p.y)
            for grid in (grids[left], grids[right])]
    assert len(base[0]) == len(base[1]) == size
    assert all((a-b).length < 1e-5 for a,b in zip(*base))

modifier.subdivision_type = 'SIMPLE'
flat = world_samples()
seam(flat, 128, 0, 1)
seam(flat, 256, 1, 2)
modifier.subdivision_type = 'CATMULL_CLARK'
rounded = world_samples()
assert any((a-b).length > .001 for a,b in zip(flat[0],rounded[0]))
seam(rounded, 128, 0, 1)
seam(rounded, 256, 1, 2)
# A topology-preserving height edit on the authored cage.
max(mesh.vertices, key=lambda vertex: vertex.co.x).co.z += .15
mesh.update()
sampled = world_samples()
assert any((a-b).length > .001 for a,b in zip(sampled[2], rounded[2]))
for (_, _, quad, face), points in zip(bindings, sampled, strict=True):
    face.vmf = dict(face.vmf or {}, dispinfo=terrain_surface.source_grid(points, quad, power, unit))

def add_box(bounds):
    vertices, polygons = primitives.box(*bounds)
    solid = []
    for polygon in polygons:
        face = formats.Face([list(vertices[i]) for i in (polygon[0],polygon[2],polygon[1])],
                            'tools/toolsnodraw', [0,0,0,1,1])
        face.axes = formats.quake_axes(face.plane()[0],face.projection)
        solid.append(face)
    brushes.append(solid)

for bounds in [(-128,-256,-144,512,256,-128),(-128,-256,256,512,256,272),
               (-128,-256,-128,-112,256,256),(496,-256,-128,512,256,256),
               (-112,-256,-128,496,-240,256),(-112,240,-128,496,256,256)]:
    add_box(bounds)
document = formats.Map([
    formats.Entity([('classname','worldspawn'),('skyname','sky_day01_01')], brushes),
    formats.Entity([('classname','info_player_start'),('origin','0 0 100')], [])
])
serialized = vmf.write(document)
parsed = vmf.parse(serialized)
records = [face for solid in parsed.entities[0].brushes for face in solid if (face.vmf or {}).get('dispinfo')]
assert len(records) == 3
preview_vertices, preview_faces = [], []
for face, (_, _, quad, _), points in zip(records, bindings, sampled, strict=True):
    preview = displacement.grid(face.vmf['dispinfo'], quad, face.plane()[0])
    assert all((Vector(p) * unit - q).length < 1e-5 for p, q in zip(preview, points, strict=True))

    start = len(preview_vertices)
    preview_vertices.extend(Vector(point) * unit for point in preview)
    preview_faces.extend(tuple(start + i for i in tri) for tri in displacement.triangles(size))

if '--compile' in sys.argv:
    output = ROOT / 'build/continuous-terrain'
    output.mkdir(parents=True, exist_ok=True)
    preview_mesh = bpy.data.meshes.new('Source sampled triangles')
    preview_mesh.from_pydata(preview_vertices, [], preview_faces)
    preview_mesh.update()
    preview_obj = bpy.data.objects.new('Source Preview · 3 patches', preview_mesh)
    context.collection.objects.link(preview_obj)
    preview_obj.hide_set(True)
    for obj in context.scene.objects:
        obj.select_set(False)
        if obj not in (terrain, preview_obj):
            obj.hide_set(True)
    context.view_layer.objects.active = terrain
    terrain.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'continuous_terrain.blend'))

# Losing the domain must fail explicitly instead of silently exporting a flat brush.
mesh.uv_layers.remove(mesh.uv_layers[terrain_surface.DOMAIN])
mesh.update()
terrain.update_tag()
try:
    world_samples()
except ValueError as exc:
    assert 'sampling domain' in str(exc)
else:
    raise AssertionError('Expected missing-domain diagnostic')
print('PASS continuous terrain subdivision, welded seams, native cage edit and three-patch VMF round trip')


from wavelength.source import terrain_output
context.workspace['wl_workspace'] = True
material = bpy.data.materials.new('Source terrain fixture')
material['wl_texture'] = 'nature/dirtfloor001a'
for host, _, _, _ in bindings:
    host.data.materials.append(material)
selection = {host: [max(host.data.polygons, key=lambda p: p.normal.z).index]
             for host, _, _, _ in bindings}
continuous, = terrain_surface.create_selected(context, selection)
continuous.data.vertices[0].co.z += .125
continuous.data.update()
assert bpy.ops.wavelength.terrain_game_preview() == {'FINISHED'}
preview = continuous['wl_terrain_preview']
assert len(preview.data.vertices) == 3 * size ** 2 and preview.hide_render
preview_points = [v.co.copy() for v in preview.data.vertices]
assert bpy.ops.wavelength.terrain_game_preview(mode='BASE') == {'FINISHED'}
assert len(preview.data.vertices) == 8
assert bpy.ops.wavelength.terrain_game_preview(mode='EVALUATED') == {'FINISHED'}
assert len(preview.data.vertices) > 8
assert bpy.ops.wavelength.terrain_game_preview() == {'FINISHED'}
assert all((v.co - p).length < 1e-6 for v,p in zip(preview.data.vertices, preview_points, strict=True))
doc = scene.export_map(context.scene)
assert sum(bool((face.vmf or {}).get('dispinfo'))
           for solid in doc.entities[0].brushes for face in solid) == 3
serialized_preview = []
for solid in vmf.parse(vmf.write(doc)).entities[0].brushes:
    vertices, polygons = formats.brush_mesh(solid)
    for face, polygon in zip(solid, polygons, strict=True):
        if data := (face.vmf or {}).get('dispinfo'):
            quad = displacement.quad(vertices, polygon, data['startposition'])
            serialized_preview.extend(Vector(point) * unit for point in displacement.grid(data, quad, face.plane()[0]))
assert len(serialized_preview) == len(preview_points)
error = max(min((point - other).length for other in serialized_preview) for point in preview_points)
assert error < 1e-5, error
assert bpy.ops.wavelength.hide_terrain_game_preview() == {'FINISHED'}
assert preview.hide_get()
context.scene.wavelength.engine = 'blender'
mesh_preview = terrain_output.preview_mesh(context, continuous, 'GAME')
assert len(mesh_preview.vertices) > 8
bpy.data.meshes.remove(mesh_preview)
context.scene.wavelength.engine = engine
target = bpy.data.objects.new('Anchor target', None)
context.collection.objects.link(target)
continuous.wavelength_terrain_anchor_target = target
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
continuous.data.vertices[0].select = True
bpy.ops.object.mode_set(mode='EDIT')
assert bpy.ops.wavelength.bind_terrain_anchor(follow=True) == {'FINISHED'}
bpy.ops.object.mode_set(mode='OBJECT')
start = continuous.data.vertices[0].co.copy()
target.location.z += .5
context.view_layer.update()
assert bpy.ops.wavelength.refresh_terrain_anchors() == {'FINISHED'}
assert abs(continuous.data.vertices[0].co.z - start.z - .5) < 1e-6
last = continuous.data.vertices[0].co.copy()
bpy.data.objects.remove(target, do_unlink=True)
assert bpy.ops.wavelength.refresh_terrain_anchors() == {'FINISHED'}
assert (continuous.data.vertices[0].co - last).length < 1e-6
print('PASS normal Source export, Game Preview and terrain anchor refresh')

# Compile the output produced by the normal scene exporter, with the fixture enclosure.
doc.entities[0].brushes.extend(brushes[3:])
doc.entities[0].pairs.append(('skyname','sky_day01_01'))
doc.entities.extend(document.entities[1:])
serialized = vmf.write(doc)
if '--compile' in sys.argv:
    hl2 = Path(r'C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2')
    game = ROOT / 'build/continuous-terrain/game'
    maps = game / 'maps'
    maps.mkdir(parents=True, exist_ok=True)
    (game / 'gameinfo.txt').write_text(
        'GameInfo { game "Terrain test" FileSystem { SteamAppId 220 SearchPaths {\n'
        f'Game "|gameinfo_path|."\nGame "{(hl2 / "hl2").as_posix()}"\n'
        f'Game "{(hl2 / "hl2_complete").as_posix()}"\n' + '} } }', encoding='utf-8')
    path = maps / 'continuous_terrain.vmf'
    path.write_text(serialized, encoding='utf-8')
    result = subprocess.run([str(hl2 / 'bin/vbsp.exe'), '-game', str(game), str(path)],
                            capture_output=True, text=True, errors='replace', timeout=75)
    log = result.stdout + result.stderr
    (game.parent / 'vbsp.log').write_text(log, encoding='utf-8')
    assert result.returncode == 0, log
    assert path.with_suffix('.bsp').read_bytes()[:4] == b'VBSP'
    print('PASS Source VBSP compiled continuous terrain')


from tempfile import TemporaryDirectory
from wavelength.source import mesh_assets

continuous.data.materials.clear()
context.scene.wavelength.engine = 'godot4'
with TemporaryDirectory(prefix='wavelength-terrain-glb-') as directory:
    mesh_assets.export(context, directory, selected=True, name='continuous_terrain')
    glb = Path(directory) / 'continuous_terrain' / 'continuous_terrain.glb'
    assert glb.read_bytes()[:4] == b'glTF'
print('PASS Godot profile exports the same authored terrain to GLB')
