"""Prototype parameter-domain sampling for continuous terrain."""
import math

import bpy
from mathutils import Vector

from . import displacement, terrain_revision, workspace

DOMAIN = "wavelength_terrain_domain"
PATCH = "wavelength_terrain_patch"
CORNERS = ((0, 0), (1, 0), (1, 1), (0, 1))


def cage(name, quads):
    """Build an unlinked cage from ordered world-space quads with exact shared edges."""
    vertices, faces, indices = [], [], {}
    for quad in quads:
        face = []
        for point in quad:
            key = tuple(point)
            if key not in indices:
                indices[key] = len(vertices)
                vertices.append(key)
            face.append(indices[key])
        if len(set(face)) != 4:
            raise ValueError("Terrain footprints require four distinct corners")
        faces.append(face)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    patch = mesh.attributes.new(PATCH, 'INT', 'FACE')
    domain = mesh.uv_layers.new(name=DOMAIN)
    for polygon in mesh.polygons:
        patch.data[polygon.index].value = polygon.index + 1
        for loop, uv in zip(polygon.loop_indices, CORNERS, strict=True):
            domain.uv[loop].vector = uv
    return mesh


def sample(obj, depsgraph, count, power, *, blend=False):
    """Sample evaluated geometry in the original patch domain, independent of vertex IDs."""
    if power not in (2, 3, 4):
        raise ValueError("Source displacement power must be 2, 3 or 4")
    segments = 2 ** power
    size = segments + 1
    grids = [[None] * (size * size) for _ in range(count)]
    weights = [[0.0] * (size * size) for _ in grids] if blend else None
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    try:
        domain = mesh.uv_layers.get(DOMAIN)
        patch = mesh.attributes.get(PATCH)
        if not domain or not patch or patch.domain != 'FACE' or patch.data_type != 'INT':
            raise ValueError("Terrain modifiers removed the patch sampling domain")
        mesh.calc_loop_triangles()
        points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        vertex_weights = None
        group = evaluated.vertex_groups.get(terrain_revision.BLEND_GROUP) if blend else None
        if group is not None:
            vertex_weights = [next((weight.weight for weight in vertex.groups if weight.group == group.index), 0.0)
                              for vertex in mesh.vertices]
        for triangle in mesh.loop_triangles:
            index = patch.data[triangle.polygon_index].value
            if not 1 <= index <= count:
                raise ValueError(f"Invalid terrain patch reference {index}")
            uv = [domain.uv[loop].vector * segments for loop in triangle.loops]
            a, b, c = uv
            ab, ac = b - a, c - a
            determinant = ab.x * ac.y - ab.y * ac.x
            if abs(determinant) < 1e-10:
                raise ValueError(f"Terrain patch {index} has a collapsed sampling triangle")
            x0, y0 = (max(0, math.ceil(min(p[k] for p in uv) - 1e-5)) for k in (0, 1))
            x1, y1 = (min(segments, math.floor(max(p[k] for p in uv) + 1e-5)) for k in (0, 1))
            p, q, r = (points[i] for i in triangle.vertices)
            grid = grids[index - 1]
            if vertex_weights is not None:
                wp, wq, wr = (vertex_weights[i] for i in triangle.vertices)
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    dx, dy = x - a.x, y - a.y
                    u = (dx * ac.y - dy * ac.x) / determinant
                    v = (ab.x * dy - ab.y * dx) / determinant
                    if min(u, v, 1 - u - v) < -1e-5:
                        continue
                    point = p + (q - p) * u + (r - p) * v
                    slot = y * size + x
                    if grid[slot] is not None and (grid[slot] - point).length > 1e-5:
                        raise ValueError(f"Terrain patch {index} has overlapping samples at {x}, {y}")
                    grid[slot] = point
                    if vertex_weights is not None:
                        weight = wp + (wq - wp) * u + (wr - wp) * v
                        weights[index - 1][slot] = min(1.0, max(0.0, weight))
        for index, grid in enumerate(grids, 1):
            if any(point is None for point in grid):
                raise ValueError(f"Terrain patch {index} has incomplete sample coverage")
        return (grids, weights) if blend else grids
    finally:
        evaluated.to_mesh_clear()


def source_grid(points, quad, power, unit, weights=None):
    """Encode the sampled surface using Source normal and distance rows."""
    size = 2 ** power + 1
    normals, distances = [], []
    for y in range(size):
        normal_row, distance_row = [], []
        for x in range(size):
            base = displacement.base(quad, x / (size - 1), y / (size - 1))
            delta = points[y * size + x] / unit - Vector(base)
            distance_row.append(delta.length)
            normal_row.extend(delta.normalized() if delta.length_squared else (0, 0, 1))
        normals.append(normal_row)
        distances.append(distance_row)
    result = dict(power=power, startposition=quad[0], normals=normals, distances=distances)
    if weights is not None:
        result['alphas'] = [[255 * value for value in weights[y:y + size]]
                            for y in range(0, size * size, size)]
    return result

def connected_regions(quads):
    """Partition by full edges and reject ambiguous or inconsistently wound joins."""
    edges = {}
    neighbors = [set() for _ in quads]
    for index, quad in enumerate(quads):
        for a, b in zip(quad, quad[1:] + quad[:1], strict=True):
            edge = edges.setdefault(tuple(sorted((a, b))), [])
            if len(edge) == 2:
                raise ValueError(f"More than two terrain faces share the edge {a} to {b}")
            if edge:
                other, start = edge[0]
                if start == a:
                    raise ValueError(f"Terrain faces have inconsistent winding at {a} to {b}")
                neighbors[index].add(other)
                neighbors[other].add(index)
            edge.append((index, a))

    seen = set()
    for seed in range(len(quads)):
        if seed in seen:
            continue
        region, pending = [], [seed]
        seen.add(seed)
        while pending:
            index = pending.pop()
            region.append(index)
            for neighbor in neighbors[index] - seen:
                seen.add(neighbor)
                pending.append(neighbor)
        yield sorted(region)


def edit_faces(context):
    import bmesh

    for host in sorted(context.objects_in_mode, key=lambda obj: obj.name):
        if host.type != 'MESH':
            continue
        edit = bmesh.from_edit_mesh(host.data)
        edit.faces.index_update()
        edit.verts.index_update()
        ids = edit.faces.layers.int.get('wl_face_id')
        for face in edit.faces:
            if face.select and not face.hide:
                yield host, face.index, [vertex.co for vertex in face.verts], face[ids] if ids else 0, face.material_index, [vertex.index for vertex in face.verts]


def object_faces(selection):
    for host, indices in selection.items():
        ids = host.data.attributes.get('wl_face_id')
        for index in sorted(indices):
            face = host.data.polygons[index]
            coordinates = [host.data.vertices[i].co for i in face.vertices]
            yield host, index, coordinates, ids.data[index].value if ids else 0, face.material_index, list(face.vertices)


def collect_faces(faces):
    footprints, bindings, materials = [], [], []
    for host, index, coordinates, face_id, slot, corners in faces:
        label = f"{host.name}, face {index}"
        if host.get('wl_continuous_terrain') or host.get('wl_terrain') or host.get('wl_source_displacement'):
            raise ValueError(f"{label}: select the original brush or mesh")
        if host.modifiers:
            raise ValueError(f"{label}: use a mesh or brush with finalized geometry")
        quad = [host.matrix_world @ point for point in coordinates]
        if len(quad) != 4:
            raise ValueError(f"{label}: select planar convex quads")
        normal = (quad[1] - quad[0]).cross(quad[2] - quad[1]).normalized()
        edges = [quad[(i + 1) % 4] - quad[i] for i in range(4)]
        if (abs((quad[3] - quad[0]).dot(normal)) > 1e-6 or
                any(edge.cross(edges[(i + 1) % 4]).dot(normal) <= 1e-10
                    for i, edge in enumerate(edges))):
            raise ValueError(f"{label}: select planar convex quads")
        footprints.append([tuple(point) for point in quad])
        bindings.append({"host": host, "face_index": index,
                         "face_id": face_id, "corners": corners})
        materials.append(host.material_slots[slot].material if slot < len(host.material_slots) else None)
    return footprints, bindings, materials


def create_selected(context, selection=None):
    """Create independent terrain cages from selected source faces."""
    faces = edit_faces(context) if selection is None else object_faces(selection)
    footprints, bindings, materials = collect_faces(faces)
    if not footprints:
        raise ValueError("Select at least one face")

    regions = list(connected_regions(footprints))
    created = []
    try:
        for region in regions:
            origin = Vector(footprints[region[0]][0])
            mesh = cage("Terrain", [[Vector(point) - origin for point in footprints[i]] for i in region])
            obj = bpy.data.objects.new("Terrain", mesh)
            created.append(obj)
            obj.location = origin
            obj["wl_continuous_terrain"] = {
                str(patch): bindings[index] for patch, index in enumerate(region, 1)
            }
            slots = {}
            for polygon, index in zip(mesh.polygons, region, strict=True):
                material = materials[index]
                if material not in slots:
                    slots[material] = len(mesh.materials)
                    mesh.materials.append(material)
                polygon.material_index = slots[material]
            modifier = obj.modifiers.new("Terrain Subdivision", 'SUBSURF')
            modifier.subdivision_type = 'SIMPLE'
            modifier.levels = modifier.render_levels = 2
            modifier.uv_smooth = 'NONE'
            context.collection.objects.link(obj)
        if context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        for obj in created:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        raise

    for host in context.selected_objects:
        host.select_set(False)
    for obj in created:
        obj.select_set(True)
    context.view_layer.objects.active = created[0]
    return created


class WL_OT_create_terrain(bpy.types.Operator):
    bl_idname = 'wavelength.create_terrain_from_faces'
    bl_label = 'Create Terrain'
    bl_description = 'Build terrain cages from selected quad faces across meshes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and workspace.active(context)

    def execute(self, context):
        try:
            regions = create_selected(context)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Created {len(regions)} terrain region(s)")
        return {'FINISHED'}


def menu(self, context):
    if WL_OT_create_terrain.poll(context):
        self.layout.operator(WL_OT_create_terrain.bl_idname, icon='MESH_GRID')


class WL_OT_create_terrain_from_meshes(bpy.types.Operator):
    bl_idname = 'wavelength.create_terrain_from_meshes'
    bl_label = 'Create Terrain from Meshes'
    bl_description = 'Use all faces of the selected terrain meshes'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and workspace.active(context) and any(
            obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        selection = {obj: range(len(obj.data.polygons)) for obj in context.selected_objects
                     if obj.type == 'MESH'}
        try:
            regions = create_selected(context, selection)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f"Created {len(regions)} terrain region(s)")
        return {'FINISHED'}


_PICKERS = set()


class WL_OT_pick_terrain_faces(bpy.types.Operator):
    bl_idname = 'wavelength.pick_terrain_faces'
    bl_label = 'Pick Terrain Faces'
    bl_description = 'Pick quad faces across meshes in the viewport'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.area and context.area.type == 'VIEW_3D' and
                context.mode == 'OBJECT' and workspace.active(context))

    def invoke(self, context, event):
        if context.region is None or context.region_data is None or any(picker.area == context.area for picker in _PICKERS):
            self.report({'ERROR'}, 'Use a 3D viewport without an active terrain picker')
            return {'CANCELLED'}
        self.area = context.area
        self.region = context.region
        self.selection = {}
        self.preview = {}
        self.handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_preview, (), 'WINDOW', 'POST_VIEW')
        _PICKERS.add(self)
        self.area.header_text_set('Click faces to toggle · Enter creates terrain · Esc cancels')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def draw_preview(self):
        if bpy.context.region != self.region:
            return
        import gpu
        from gpu_extras.batch import batch_for_shader

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        shader.bind()
        for count, color in ((1, (.2, .7, 1, 1)), (2, (.3, 1, .35, 1)), (3, (1, .3, .2, 1))):
            points = [point for edge, uses in self.preview.items() if min(uses, 3) == count for point in edge]
            if points:
                shader.uniform_float('color', color)
                batch_for_shader(shader, 'LINES', {'pos': points}).draw(shader)

    def finish(self):
        if self in _PICKERS:
            _PICKERS.remove(self)
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
            try:
                self.area.header_text_set(None)
                self.area.tag_redraw()
            except ReferenceError:
                pass

    def cancel(self, context):
        self.finish()

    def modal(self, context, event):
        from bpy_extras import view3d_utils

        if self not in _PICKERS or event.type == 'ESC' or context.mode != 'OBJECT' or not workspace.active(context):
            self.finish()
            return {'CANCELLED'}
        if event.value != 'PRESS':
            return {'PASS_THROUGH'}
        if event.type in {'RET', 'NUMPAD_ENTER'}:
            try:
                regions = create_selected(context, self.selection)
            except (ValueError, RuntimeError, ReferenceError) as exc:
                self.report({'WARNING'}, str(exc))
                return {'RUNNING_MODAL'}
            self.finish()
            self.report({'INFO'}, f"Created {len(regions)} terrain region(s)")
            return {'FINISHED'}
        if event.type != 'LEFTMOUSE' or context.region != self.region or context.region_data is None:
            return {'PASS_THROUGH'}
        cursor = (event.mouse_region_x, event.mouse_region_y)
        origin = view3d_utils.region_2d_to_origin_3d(context.region, context.region_data, cursor)
        direction = view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, cursor)
        hit, _, _, index, host, _ = context.scene.ray_cast(context.evaluated_depsgraph_get(), origin, direction)
        if not hit or host.type != 'MESH' or not 0 <= index < len(host.data.polygons):
            return {'RUNNING_MODAL'}
        try:
            collect_faces(object_faces({host: [index]}))
            indices = self.selection.setdefault(host, set())
            if index in indices:
                indices.remove(index)
            else:
                indices.add(index)
            self.preview.clear()
            quads, _, _ = collect_faces(object_faces(self.selection))
            for quad in quads:
                for a, b in zip(quad, quad[1:] + quad[:1], strict=True):
                    edge = tuple(sorted((a, b)))
                    self.preview[edge] = self.preview.get(edge, 0) + 1
            list(connected_regions(quads))
        except (ValueError, ReferenceError, IndexError) as exc:
            self.report({'WARNING'}, str(exc))
        self.area.tag_redraw()
        return {'RUNNING_MODAL'}


def object_menu(self, context):
    if WL_OT_pick_terrain_faces.poll(context):
        row = self.layout.row()
        row.operator_context = 'INVOKE_REGION_WIN'
        row.operator(WL_OT_pick_terrain_faces.bl_idname, icon='RESTRICT_SELECT_OFF')
    if WL_OT_create_terrain_from_meshes.poll(context):
        self.layout.operator(WL_OT_create_terrain_from_meshes.bl_idname, icon='MESH_GRID')


def register():
    terrain_revision.register()
    from . import environment_layers
    environment_layers.register()
    from . import terrain_migration
    terrain_migration.register()
    bpy.utils.register_class(WL_OT_create_terrain)
    bpy.utils.register_class(WL_OT_create_terrain_from_meshes)
    bpy.utils.register_class(WL_OT_pick_terrain_faces)
    bpy.types.VIEW3D_MT_object.append(object_menu)
    bpy.types.VIEW3D_MT_edit_mesh_faces.append(menu)


def unregister():
    from . import environment_layers
    environment_layers.unregister()
    from . import terrain_migration
    terrain_migration.unregister()
    terrain_revision.unregister()
    for picker in tuple(_PICKERS):
        picker.finish()
    bpy.utils.unregister_class(WL_OT_pick_terrain_faces)
    bpy.types.VIEW3D_MT_object.remove(object_menu)
    bpy.utils.unregister_class(WL_OT_create_terrain_from_meshes)
    bpy.types.VIEW3D_MT_edit_mesh_faces.remove(menu)
    bpy.utils.unregister_class(WL_OT_create_terrain)
