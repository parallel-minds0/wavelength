"""Create editable copies of saved terrain while retaining the original objects."""

import bpy
from mathutils import Vector

from . import displacement, source_displacement as native, terrain_face, terrain_revision, terrain_surface, workspace


def native_mesh(objects):
    vertices, triangles, uv_rows, patch_ids, weights = [], [], [], [], []
    materials, material_indices, bindings = [], [], {}
    indices = {}
    powers = {native.info(obj)['data']['power'] for obj in objects}
    if len(powers) != 1:
        raise ValueError('Select native displacement grids of the same Source power')
    power = powers.pop()
    size = 2 ** power + 1
    origin = objects[0].matrix_world.translation.copy()
    for patch_id, obj in enumerate(objects, 1):
        host, record, _ = native.source_face(obj)
        points, alphas, _, uvs = native.read_surface(obj, with_uv=True)
        unit = obj['wl_unit_meters']
        indices_in_patch = []
        for point, alpha in zip(points, alphas, strict=True):
            point = Vector(point) * unit
            key = (*point, alpha)
            if key not in indices:
                indices[key] = len(vertices)
                vertices.append(point - origin)
                weights.append(alpha / 255)
            indices_in_patch.append(indices[key])
        material = native.surface_material(obj)
        if material not in materials:
            materials.append(material)
        for tri in displacement.triangles(size):
            triangles.append(tuple(indices_in_patch[i] for i in tri))
            uv_rows.append([(i % size / (size - 1), i // size / (size - 1), uvs[i]) for i in tri])
            patch_ids.append(patch_id)
            material_indices.append(materials.index(material))
        bindings[str(patch_id)] = {
            'host': host, 'face_id': record['face_id'], 'corners': record['corners'],
            'native': obj,
        }

    mesh = bpy.data.meshes.new('Migrated Source Terrain')
    mesh.from_pydata(vertices, [], triangles)
    mesh.update()
    for material in materials:
        mesh.materials.append(material)
    domain = mesh.uv_layers.new(name=terrain_surface.DOMAIN)
    texture = mesh.uv_layers.new(name='wavelength')
    mesh.uv_layers.active = texture
    attribute = mesh.attributes.new(terrain_surface.PATCH, 'INT', 'FACE')
    attribute.data.foreach_set('value', patch_ids)
    for polygon, row, slot in zip(mesh.polygons, uv_rows, material_indices, strict=True):
        polygon.material_index = slot
        for loop, (u, v, uv) in zip(polygon.loop_indices, row, strict=True):
            domain.uv[loop].vector = (u, v)
            texture.uv[loop].vector = uv
    return mesh, origin, bindings, weights, power


def migrate_native(context, objects):
    mesh, origin, bindings, weights, power = native_mesh(objects)
    obj = bpy.data.objects.new(mesh.name, mesh)
    obj.location = origin
    obj['wl_continuous_terrain'] = bindings
    obj['wl_exclude'] = True
    obj.wavelength_terrain_power = power
    context.collection.objects.link(obj)
    group = obj.vertex_groups.new(name=terrain_revision.BLEND_GROUP)
    buckets = {}
    for index, weight in enumerate(weights):
        if weight:
            buckets.setdefault(weight, []).append(index)
    for weight, indices in buckets.items():
        group.add(indices, weight, 'REPLACE')
    return obj


def migrate_legacy(context, source):
    from . import terrain_paint

    previous = terrain_paint.full_surface(source)
    try:
        depsgraph = context.evaluated_depsgraph_get()
        depsgraph.update()
        mesh = terrain_face.export_mesh(source, depsgraph)
    finally:
        terrain_paint.restore_surface(source, previous)
    obj = bpy.data.objects.new(f'{source.name} · Terrain Mesh', mesh)
    obj.matrix_world = source.matrix_world.copy()
    obj['wl_terrain_migration_source'] = source
    obj['wl_exclude'] = True
    context.collection.objects.link(obj)
    return obj


class WL_OT_migrate_terrain(bpy.types.Operator):
    bl_idname = 'wavelength.migrate_terrain'
    bl_label = 'Migrate Terrain as Copy'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and workspace.active(context)
                and any(obj.get(native.KEY) or obj.get('wl_terrain') for obj in context.selected_objects))

    def execute(self, context):
        selected = list(context.selected_objects)
        native_grids = [obj for obj in selected if obj.get(native.KEY) and not obj.get('wl_custom_model_owner')]
        legacy = [obj for obj in selected if obj.get('wl_terrain') and not obj.get(native.KEY)]
        created = []
        try:
            if native_grids:
                created.append(migrate_native(context, native_grids))
            for source in legacy:
                created.append(migrate_legacy(context, source))
        except (ValueError, RuntimeError) as exc:
            for obj in created:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if not created:
            return {'CANCELLED'}
        for obj in selected:
            obj.select_set(False)
        for obj in created:
            obj.select_set(True)
        context.view_layer.objects.active = created[0]
        self.report({'INFO'}, f'Created {len(created)} terrain copy(s) with export disabled')
        return {'FINISHED'}


class WL_OT_use_migrated_terrain(terrain_revision.TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.use_migrated_terrain'
    bl_label = 'Switch Migrated Terrain Export'
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        bindings = obj['wl_continuous_terrain']
        if not all(binding.get('native') for binding in bindings.values()):
            self.report({'ERROR'}, 'The original Source displacements are required')
            return {'CANCELLED'}
        obj['wl_exclude'] = not obj.get('wl_exclude', False)
        return {'FINISHED'}


def menu(self, context):
    if WL_OT_migrate_terrain.poll(context):
        self.layout.operator(WL_OT_migrate_terrain.bl_idname, icon='MESH_GRID')


def register():
    bpy.utils.register_class(WL_OT_migrate_terrain)
    bpy.utils.register_class(WL_OT_use_migrated_terrain)
    bpy.types.VIEW3D_MT_object.append(menu)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu)
    bpy.utils.unregister_class(WL_OT_use_migrated_terrain)
    bpy.utils.unregister_class(WL_OT_migrate_terrain)
