"""Exercise Create Terrain through its multi-object Edit Mode entry point."""
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import wavelength
from wavelength.source import scene, terrain_surface

wavelength.register()
context = bpy.context
context.workspace['wl_workspace'] = True
context.scene.wavelength.engine = 'blender'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
hosts = []
for x, y in ((0, 0), (2, 0), (4, 0), (8, 2), (10, 4)):
    bpy.ops.mesh.primitive_plane_add(size=2, location=(x, y, 0))
    hosts.append(context.object)
scene.mark_brush(hosts[0])
material = bpy.data.materials.new('Terrain test')
hosts[0].data.materials.append(material)
for host in hosts:
    host.select_set(True)
context.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
assert bpy.ops.wavelength.create_terrain_from_faces() == {'FINISHED'}
assert context.mode == 'OBJECT'
regions = sorted(context.selected_objects, key=lambda obj: len(obj.data.polygons))
assert [len(obj.data.polygons) for obj in regions] == [1, 1, 3]
assert all(len(host.data.polygons) == 1 for host in hosts)
joined = regions[-1]
assert len(joined.data.vertices) == 8
bindings = joined['wl_continuous_terrain']
assert {entry['host'] for entry in bindings.values()} == set(hosts[:3])
assert any(entry['host'] == hosts[0] and entry['face_id'] > 0 for entry in bindings.values())
assert material in list(joined.data.materials)
context.view_layer.update()
assert len(terrain_surface.sample(joined, context.evaluated_depsgraph_get(), 3, 3)) == 3

quad = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
try:
    list(terrain_surface.connected_regions([quad, quad]))
except ValueError as exc:
    assert 'winding' in str(exc)
else:
    raise AssertionError('Duplicate footprint should fail')

print('PASS Create Terrain joins full edges, separates point contacts, retains brush bindings and samples native subdivision')

bpy.ops.object.select_all(action='DESELECT')
for host in hosts[:3]:
    host.select_set(True)
context.view_layer.objects.active = hosts[0]
assert bpy.ops.wavelength.create_terrain_from_meshes() == {'FINISHED'}
assert len(context.selected_objects) == 1
assert len(context.object.data.vertices) == 8
assert 'pick_terrain_faces' in dir(bpy.ops.wavelength)
print('PASS whole-mesh terrain creation and viewport picker registration')

from wavelength.source import displacement, terrain_revision

authored = context.object
assert bpy.ops.wavelength.paint_terrain_blend() == {'FINISHED'}
assert context.mode == 'PAINT_WEIGHT'
bpy.ops.object.mode_set(mode='OBJECT')
group = authored.vertex_groups.active
assert group.name == terrain_revision.BLEND_GROUP
# Assign a continuous painted stripe to the welded seam vertices.
seam = [vertex.index for vertex in authored.data.vertices
        if abs((authored.matrix_world @ vertex.co).x - 1) < 1e-6]
assert len(seam) == 2
group.add(seam, .75, 'REPLACE')
authored.modifiers[0].subdivision_type = 'CATMULL_CLARK'
assert bpy.ops.wavelength.save_terrain_revision(name='Painted slope') == {'FINISHED'}
snapshot = authored[terrain_revision.REVISIONS]['Painted slope']
assert snapshot.data != authored.data and not snapshot.users_collection

def samples(obj):
    context.view_layer.update()
    return terrain_surface.sample(obj, context.evaluated_depsgraph_get(), 3, 3, blend=True)

geometry, weights = samples(authored)
left = sorted(weight for point, weight in zip(geometry[0], weights[0]) if abs(point.x - 1) < 1e-5)
right = sorted(weight for point, weight in zip(geometry[1], weights[1]) if abs(point.x - 1) < 1e-5)
assert len(left) == len(right) == 9
assert all(abs(a-b) < 1e-5 for a,b in zip(left,right)) and max(left) > .5
record = terrain_surface.source_grid(geometry[0], [(0,0,0)]*4, 3, 1, weights[0])
assert max(max(row) for row in displacement.parse(displacement.pairs(record))['alphas']) > 127

group.remove(seam)
authored.data.vertices[0].co.z += .5
authored.data.update()
authored.modifiers[0].subdivision_type = 'SIMPLE'
assert bpy.ops.wavelength.restore_terrain_revision(name='Painted slope') == {'FINISHED'}
restored = context.object
assert restored != authored and restored.data != snapshot.data
assert restored.modifiers[0].subdivision_type == 'CATMULL_CLARK'
restored_geometry, restored_weights = samples(restored)
assert restored_weights == weights
assert all((a-b).length < 1e-6 for grid_a, grid_b in zip(geometry, restored_geometry)
           for a, b in zip(grid_a, grid_b))
assert restored['wl_continuous_terrain']['1']['host'] == snapshot['wl_continuous_terrain']['1']['host']
print('PASS native weight paint entry, shared seam alpha, Source encoding and independent revision restore')

assert bpy.ops.wavelength.add_terrain_detail() == {'FINISHED'}
detail = restored.modifiers[-1]
inputs = {socket.name: socket.identifier for socket in detail.node_group.interface.items_tree
          if socket.item_type == 'SOCKET' and socket.in_out == 'INPUT'}

def detail_value(name, value):
    key = inputs[name]
    if hasattr(detail, 'properties'):
        getattr(detail.properties.inputs, key).value = value
    else:
        detail[key] = value
    restored.update_tag()

detail_value('Noise Height', .6)
noisy, noisy_weights = samples(restored)
assert any((a-b).length > .01 for a,b in zip(noisy[0], geometry[0]))
assert noisy_weights == weights
image = bpy.data.images.new('White heightmap', width=2, height=2)
image.pixels = [1.0] * 16
detail_value('Noise Height', 0.0)
detail_value('Heightmap', image)
detail_value('Image Height', .4)
raised, _ = samples(restored)
assert all(abs(a.z - b.z - .2) < 1e-5 for a,b in zip(raised[0], geometry[0]))
print('PASS live Geometry Nodes noise and image displacement preserve patch sampling')

from tempfile import TemporaryDirectory

authored_name = authored.name
with TemporaryDirectory(prefix='wavelength-revision-') as directory:
    filename = str(Path(directory) / 'revision.blend')
    bpy.ops.wm.save_as_mainfile(filepath=filename)
    bpy.ops.wm.open_mainfile(filepath=filename)
    authored = bpy.data.objects[authored_name]
    snapshot = authored[terrain_revision.REVISIONS]['Painted slope']
    assert snapshot and not snapshot.users_collection
    assert snapshot.modifiers[0].subdivision_type == 'CATMULL_CLARK'
    assert snapshot.vertex_groups[terrain_revision.BLEND_GROUP].weight(seam[0]) == .75
    assert snapshot['wl_continuous_terrain']['1']['host'] in bpy.context.scene.objects.values()
print('PASS revision mesh, stack, paint and host references survive reopening the blend file')
