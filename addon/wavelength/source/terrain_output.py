"""Shared Source conversion and inspection for continuous terrain regions."""

import copy

import bpy
from mathutils import Vector

from . import displacement, formats, terrain_surface


def source_patches(obj, depsgraph, brushes):
    """Return exported face indices, displacement records and preview grids."""
    from .scene import world_point

    bindings = obj['wl_continuous_terrain']
    power = obj.wavelength_terrain_power
    points, weights = terrain_surface.sample(obj, depsgraph, len(bindings), power, blend=True)
    size = 2 ** power + 1
    borders = {}
    result = []
    for index, grid in enumerate(points):
        binding = bindings[str(index + 1)]
        host = binding.get('host')
        face_id = binding.get('face_id')
        if host is None or host.get('wl_role') != 'BRUSH' or host.get('wl_entity_id') or host not in brushes:
            raise ValueError(f'{obj.name}, patch {index + 1}: include its original Source world brush in export')
        ids = host.data.attributes.get('wl_face_id')
        matches = [p for p in host.data.polygons if ids and ids.data[p.index].value == face_id]
        if len(matches) != 1 or not face_id or len(matches[0].vertices) != 4:
            raise ValueError(f'{obj.name}, patch {index + 1}: backing face is missing or changed')
        polygon = matches[0]
        indices = list(binding.get('corners', polygon.vertices))
        if len(indices) != 4 or set(indices) != set(polygon.vertices):
            raise ValueError(f'{obj.name}, patch {index + 1}: backing corners changed')
        unit = host.get('wl_unit_meters', 1.0)
        solid = brushes[host]
        face_index = sorted(d.value for d in ids.data).index(face_id)
        face = solid[face_index]
        original = binding.get('native')
        baseline = None
        if original is not None:
            from . import source_displacement
            if original not in source_displacement.surfaces(host) or source_displacement.info(original)['face_id'] != face_id:
                raise ValueError(f'{obj.name}, patch {index + 1}: migrated displacement lost its source binding')
            face = source_displacement.export_surface(original, copy.deepcopy(face))
            baseline = face.vmf['dispinfo']
            if baseline['power'] != power:
                raise ValueError(f'{obj.name}, patch {index + 1}: keep the original Source power to preserve metadata')
        vertices, polygons = formats.brush_mesh(solid)
        corners = [vertices[i] for i in polygons[face_index]]
        if len(corners) != 4:
            raise ValueError(f'{obj.name}, patch {index + 1}: exported backing face is not a quad')
        quad = []
        for vertex in indices:
            point = Vector(world_point(host, host.data.vertices[vertex].co, unit))
            quad.append(min(corners, key=lambda corner: (Vector(corner) - point).length_squared))
        if len({tuple(point) for point in quad}) != 4:
            raise ValueError(f'{obj.name}, patch {index + 1}: backing quad could not be matched')

        for edge, slots in enumerate((range(size), range(size - 1, size * size, size),
                                      range(size * size - 1, size * (size - 1) - 1, -1),
                                      range(size * (size - 1), -1, -size))):
            a, b = [tuple(round(value * unit, 6) for value in quad[i]) for i in (edge, (edge + 1) % 4)]
            edge_samples = [grid[slot] for slot in slots]
            if a > b:
                edge_samples.reverse()
            key = tuple(sorted((a, b)))
            if key in borders and any((p - q).length > 1e-5 for p, q in zip(edge_samples, borders[key], strict=True)):
                raise ValueError(f'{obj.name}, patch {index + 1}: sampled edge does not match its neighbor')
            borders[key] = edge_samples

        if baseline is None and any(weight > 1e-5 for weight in weights[index]):
            from . import source_assets
            settings = bpy.context.scene.wavelength
            material = host.material_slots[polygon.material_index].material if polygon.material_index < len(host.material_slots) else None
            if material and material.get('wl_texture') == face.texture and material.get('wl_source_blend'):
                shader = 'worldvertextransition'
            else:
                assets = source_assets.library(bpy.path.abspath(settings.game_dir))
                shader = assets.material(face.texture).get('_wl_shader', '')
            if not shader.lower().startswith('worldvertextransition'):
                raise ValueError(f'{obj.name}, patch {index + 1}: assign a Source blend material to the backing face')
        # The reconstructed brush determines Source row winding.
        ordered = displacement.quad(vertices, polygons[face_index], quad[0])
        if tuple(quad[1]) != ordered[1]:
            if tuple(quad[3]) != ordered[1]:
                raise ValueError(f'{obj.name}, patch {index + 1}: backing quad winding changed')
            slots = [x * size + y for y in range(size) for x in range(size)]
            grid = [grid[slot] for slot in slots]
            weights[index] = [weights[index][slot] for slot in slots]
        data = terrain_surface.source_grid(grid, ordered, power, unit, weights[index])
        if baseline is not None:
            # Use the native face's existing row orientation and preserve its
            # projection, collision flags, triangle tags and extension blocks.
            normal = Vector(face.plane()[0])
            native_order = displacement.quad(vertices, polygons[face_index], baseline['startposition'])
            if (Vector(native_order[1]) - Vector(native_order[0])).cross(
                    Vector(native_order[3]) - Vector(native_order[0])).dot(normal) < 0:
                native_order = [native_order[i] for i in (0, 3, 2, 1)]
            by_corner = {tuple(point): uv for point, uv in zip(ordered, ((0,0), (1,0), (1,1), (0,1)), strict=True)}
            a, b, _, d = [by_corner[tuple(point)] for point in native_order]
            slots = []
            for y in range(size):
                for x in range(size):
                    u = a[0] * (size - 1) + (b[0] - a[0]) * x + (d[0] - a[0]) * y
                    v = a[1] * (size - 1) + (b[1] - a[1]) * x + (d[1] - a[1]) * y
                    slots.append(v * size + u)
            native_points = [grid[slot] for slot in slots]
            adjusted = []
            for i, point in enumerate(native_points):
                y, x = divmod(i, size)
                offset = Vector(baseline['offsets'][y][3*x:3*x+3]) if baseline.get('offsets') else Vector((0,0,0))
                adjusted.append(point - unit * (offset + normal * baseline.get('elevation', 0)))
            sampled = terrain_surface.source_grid(adjusted, native_order, power, unit,
                                                  [weights[index][slot] for slot in slots])
            for key in ('normals', 'distances', 'alphas'):
                baseline[key] = sampled[key]
            source_displacement._ensure_raw(baseline, 'alphas')
            data, ordered = baseline, native_order
        preview = [Vector(point) * unit for point in displacement.grid(data, ordered, face.plane()[0])]
        result.append((host, face_index, data, preview))
    return result


def preview_mesh(context, obj, mode):
    from . import profiles, scene, terrain_face

    if mode == 'BASE':
        mesh = obj.data.copy()
        mesh.transform(obj.matrix_world)
        return mesh

    depsgraph = context.evaluated_depsgraph_get()
    engine = context.scene.wavelength.engine
    if mode == 'EVALUATED' or not profiles.is_source(engine):
        if mode != 'EVALUATED' and not profiles.is_mesh_export(engine) and engine != 'blender':
            raise ValueError('Game Preview supports Source 1 and mesh profiles')
        mesh = terrain_face.export_mesh(obj, depsgraph)
        mesh.transform(obj.matrix_world)
        return mesh

    from .export_scope import Scope

    scope = Scope(context.scene)
    hosts = {entry.get('host') for entry in obj['wl_continuous_terrain'].values()}
    brushes = {host: scene.brush_from_object(host, engine, require_texture=True)
               for host in hosts if host is not None and host.get('wl_role') == 'BRUSH'
               and not host.get('wl_exclude') and scope.includes(host)}
    patches = source_patches(obj, depsgraph, brushes)
    vertices, triangles, weights = [], [], []
    size = 2 ** obj.wavelength_terrain_power + 1
    for _, _, data, grid in patches:
        weights.extend(value / 255 for row in data['alphas'] for value in row)
        start = len(vertices)
        vertices.extend(grid)
        triangles.extend(tuple(start + i for i in tri) for tri in displacement.triangles(size))
    mesh = bpy.data.meshes.new('Terrain Game Preview')
    mesh.from_pydata(vertices, [], triangles)
    attribute = mesh.attributes.new('wl_terrain_blend', 'FLOAT', 'POINT')
    attribute.data.foreach_set('value', weights)
    mesh.update()
    return mesh
