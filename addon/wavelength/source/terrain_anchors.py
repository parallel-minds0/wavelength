"""Explicit terrain cage anchors with a recoverable refresh operation."""

import hashlib

import bpy
from mathutils import Vector

from . import workspace

KEY = 'wl_terrain_anchors'


def topology_signature(count, edges):
    topology = (count, sorted(tuple(sorted(edge)) for edge in edges))
    return hashlib.sha256(repr(topology).encode()).hexdigest()


def bind(obj, follow):
    import bmesh

    mesh = bmesh.from_edit_mesh(obj.data)
    mesh.verts.index_update()
    boundary = {v for edge in mesh.edges if edge.is_boundary for v in edge.verts}
    vertices = [v for v in mesh.verts if v.select and not v.hide]
    if not vertices or any(v not in boundary for v in vertices):
        raise ValueError('Select only terrain cage boundary vertices')
    target = obj.wavelength_terrain_anchor_target if follow else None
    if follow and (target is None or target == obj):
        raise ValueError('Choose another object as the Follow Target')
    signature = topology_signature(len(mesh.verts), ([v.index for v in e.verts] for e in mesh.edges))
    anchors = obj.get(KEY, {})
    indices = {v.index for v in vertices}
    if any(indices.intersection(anchor['vertices']) for anchor in anchors.values()):
        raise ValueError('These vertices already have an anchor')
    record = dict(vertices=sorted(indices), topology=signature, follow=follow,
                  positions={str(v.index): list(obj.matrix_world @ v.co) for v in vertices},
                  falloff=obj.wavelength_terrain_anchor_falloff)
    if target:
        record['target'] = target
        record['origin'] = list(target.matrix_world.translation)
    if KEY not in obj:
        obj[KEY] = {}
    obj[KEY][str(len(anchors))] = record


def refresh(obj, scene):
    anchors = obj.get(KEY, {})
    mesh = obj.data
    signature = topology_signature(len(mesh.vertices), (edge.vertices for edge in mesh.edges))
    if any(anchor['topology'] != signature for anchor in anchors.values()):
        raise ValueError('Terrain cage topology changed. Clear anchors and bind again')
    world = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    inverse = obj.matrix_world.inverted()
    displacements = [Vector((0, 0, 0)) for _ in world]
    pins, updates, broken = {}, [], []
    for name, anchor in anchors.items():
        positions = {int(index): Vector(value) for index, value in anchor['positions'].items()}
        delta = Vector((0, 0, 0))
        if anchor['follow']:
            target = anchor.get('target')
            if target is None or scene.objects.get(target.name) != target:
                broken.append(name)
            else:
                origin = target.matrix_world.translation.copy()
                delta = origin - Vector(anchor['origin'])
                updates.append((anchor, origin, positions, delta))
        pins.update({index: point + delta for index, point in positions.items()})
        falloff = anchor['falloff']
        if falloff > 0 and delta.length_squared:
            for index, point in enumerate(world):
                distance = min((point - pin).length for pin in positions.values())
                t = max(0.0, 1.0 - distance / falloff)
                displacements[index] += delta * (t * t * (3 - 2 * t))
    for vertex in mesh.vertices:
        index = vertex.index
        vertex.co = inverse @ pins.get(index, world[index] + displacements[index])
    for anchor, origin, positions, delta in updates:
        anchor['origin'] = list(origin)
        anchor['positions'] = {str(index): list(point + delta) for index, point in positions.items()}
    mesh.update()
    obj.update_tag()
    return broken


class WL_OT_bind_terrain_anchor(bpy.types.Operator):
    bl_idname = 'wavelength.bind_terrain_anchor'
    bl_label = 'Bind Terrain Boundary'
    bl_options = {'UNDO'}

    follow: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and workspace.active(context) and
                context.object and bool(context.object.get('wl_continuous_terrain')))

    def execute(self, context):
        try:
            bind(context.object, self.follow)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_refresh_terrain_anchors(bpy.types.Operator):
    bl_idname = 'wavelength.refresh_terrain_anchors'
    bl_label = 'Refresh Terrain Anchors'
    bl_options = {'UNDO'}

    clear: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and workspace.active(context) and
                context.object and bool(context.object.get(KEY)))

    def execute(self, context):
        obj = context.object
        if self.clear:
            del obj[KEY]
            return {'FINISHED'}
        try:
            broken = refresh(obj, context.scene)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        if broken:
            self.report({'WARNING'}, f'{len(broken)} missing anchor target(s). Last valid positions retained')
        return {'FINISHED'}


CLASSES = (WL_OT_bind_terrain_anchor, WL_OT_refresh_terrain_anchors)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.wavelength_terrain_anchor_target = bpy.props.PointerProperty(
        name='Follow Target', type=bpy.types.Object)
    bpy.types.Object.wavelength_terrain_anchor_falloff = bpy.props.FloatProperty(
        name='Anchor Falloff', default=2.0, min=0, unit='LENGTH')


def unregister():
    del bpy.types.Object.wavelength_terrain_anchor_falloff
    del bpy.types.Object.wavelength_terrain_anchor_target
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
