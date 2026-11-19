"""Stage fence posts along an open Blender Poly spline."""
from bisect import bisect_right
from math import floor, hypot, isfinite
import json

import bpy

from . import editor, primitives, profiles, scene, workspace


def placement(route):
    splines = route.data.splines
    if (len(splines) != 1 or splines[0].type != 'POLY'
            or splines[0].use_cyclic_u or len(splines[0].points) < 2):
        raise ValueError('Use one open Poly spline with at least two points')
    points = [route.matrix_world @ point.co.to_3d() for point in splines[0].points]
    config = route.wl_fence_route
    spacing, width, height = config.spacing, config.post_width, config.post_height
    gate, gap = config.gate_center, config.gate_width
    if not all(isfinite(value) for value in (spacing, width, height, gate, gap)):
        raise ValueError('Fence dimensions must be finite')
    if min(width, height) <= 0 or spacing < width:
        raise ValueError('Use positive post dimensions and spacing at least as large as the post width')
    lengths = [0.]
    for a, b in zip(points, points[1:]):
        length = (b - a).length
        if not isfinite(length) or length < 1e-6:
            raise ValueError('Route segments must have distinct, finite points')
        lengths.append(lengths[-1] + length)
    total = lengths[-1]
    lower, upper = gate - gap / 2, gate + gap / 2
    if gap and (lower < 0 or upper > total):
        raise ValueError(f'Place the gate opening within the {total:.3g} m route')

    def point_at(distance):
        index = min(len(points) - 2, bisect_right(lengths, distance) - 1)
        fraction = (distance - lengths[index]) / (lengths[index + 1] - lengths[index])
        return points[index].lerp(points[index + 1], fraction)

    opening = []
    if gap:
        opening = [point_at(lower), *(p for d, p in zip(lengths, points) if lower < d < upper),
                   point_at(upper)]
        opening = [point.to_2d() for point in opening]
    radius = hypot(width / 2, width / 2)

    def clears_opening(point):
        xy = point.to_2d()
        for a, b in zip(opening, opening[1:]):
            nearest = a
            if a != b:
                segment = b - a
                fraction = (xy - a).dot(segment) / segment.length_squared
                nearest = a + segment * min(1., max(0., fraction))
            if (xy - nearest).length < radius:
                return False
        return True

    candidates = (point_at(min(index * spacing, total))
                  for index in range(floor(total / spacing + 1e-7) + 1))
    positions = [point for point in candidates if clears_opening(point)]
    return positions, [list(point) for point in points], (spacing, width, height, gate, gap)


def _mesh(positions, width, height):
    vertices, faces = [], []
    half = width / 2
    for x, y, z in positions:
        corners, sides = primitives.box(x - half, y - half, z, x + half, y + half, z + height)
        faces.extend(tuple(len(vertices) + index for index in face) for face in sides)
        vertices.extend(corners)
    mesh = bpy.data.meshes.new('Fence post geometry')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    return mesh


def _remove(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if not mesh.users:
        bpy.data.meshes.remove(mesh)


def _proposal(route):
    obj = route.get('wl_fence_preview')
    return obj if obj and obj.get('wl_fence_owner') == route else None


def _discard(route):
    obj = _proposal(route)
    if obj:
        _remove(obj)
    if 'wl_fence_preview' in route:
        del route['wl_fence_preview']


def _preview(route, collection, positions, width, height, stamp):
    obj = bpy.data.objects.new('Fence preview', _mesh(positions, width, height))
    collection.objects.link(obj)
    obj['wl_fence_owner'] = route
    obj['wl_fence_stamp'] = stamp
    obj['wl_exclude'] = True
    obj['wl_editor_helper'] = True
    obj.hide_select = True
    obj.hide_render = True
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    _discard(route)
    route['wl_fence_preview'] = obj


def _apply(context, route, positions, width, height, engine, unit, material):
    settings = context.scene.wavelength
    brushes = profiles.requires_convex_brushes(engine)
    if material and material.get('wl_asset_profile', engine) != engine:
        raise ValueError('Choose a fence material from the active profile')
    if brushes and (not material or not material.get('wl_texture')):
        raise ValueError('Choose an engine texture material for the fence posts')
    collection = route.get('wl_fence_output')
    created_collection = not collection or collection.get('wl_fence_owner') != route
    if created_collection:
        collection = bpy.data.collections.new(route.name + ' · Fence Posts')
        collection['wl_fence_owner'] = route
        route.users_collection[0].children.link(collection)
    previous = [obj for obj in collection.objects if obj.get('wl_fence_owner') == route]
    created = []
    try:
        for point in positions:
            obj = bpy.data.objects.new('Fence post', _mesh([(0., 0., 0.)], width, height))
            created.append(obj)
            collection.objects.link(obj)
            obj.location = point
            obj['wl_fence_owner'] = route
            obj['wl_owner_profile'] = engine
            obj['wl_owner_profile_id'] = settings.profile_id
            if material:
                obj.data.materials.append(material)
            if brushes:
                scene.mark_brush(obj)
                obj['wl_unit_meters'] = unit
        if brushes:
            context.view_layer.update()
            for obj in created:
                editor.apply_uv(obj, engine)
    except Exception:
        for obj in created:
            _remove(obj)
        if created_collection:
            bpy.data.collections.remove(collection)
        raise
    for obj in previous:
        _remove(obj)
    route['wl_fence_output'] = collection
    _discard(route)


class WL_PG_fence_route(bpy.types.PropertyGroup):
    spacing: bpy.props.FloatProperty(name='Post Spacing (m)', default=1., min=.001)
    post_width: bpy.props.FloatProperty(name='Post Width (m)', default=.15, min=.001)
    post_height: bpy.props.FloatProperty(name='Post Height (m)', default=1.1, min=.001)
    gate_center: bpy.props.FloatProperty(name='Gate Distance (m)', default=2., min=0.)
    gate_width: bpy.props.FloatProperty(name='Gate Width (m)', default=0., min=0.,
                                      description='Use zero for a continuous fence')
    material: bpy.props.PointerProperty(name='Post Material', type=bpy.types.Material)


class WL_OT_fence_route(bpy.types.Operator):
    bl_idname = 'wavelength.fence_route'
    bl_label = 'Fence Route'
    bl_options = {'UNDO'}

    action: bpy.props.EnumProperty(items=[
        ('PREVIEW', 'Preview', ''), ('APPLY', 'Apply', ''), ('DISCARD', 'Discard', ''),
    ])

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and workspace.active(context, 'editing')
                and context.object is not None and context.object.type == 'CURVE'
                and context.object.library is None)

    def execute(self, context):
        route = context.object
        if self.action == 'DISCARD':
            _discard(route)
            return {'FINISHED'}
        try:
            positions, points, dimensions = placement(route)
            _, width, height, _, _ = dimensions
            settings = context.scene.wavelength
            engine, unit = settings.engine, profiles.unit_meters(settings)
            material = route.wl_fence_route.material
            stamp = json.dumps([points, dimensions, engine, unit, settings.profile_id,
                                [material.name_full, material.get('wl_texture'),
                                 material.get('wl_asset_profile')] if material else None])
            if self.action == 'PREVIEW':
                _preview(route, route.users_collection[0], positions, width, height, stamp)
            else:
                proposal = _proposal(route)
                if not proposal or proposal.get('wl_fence_stamp') != stamp:
                    raise ValueError('Preview the current fence route before applying')
                _apply(context, route, positions, width, height, engine, unit, material)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        self.report({'INFO'}, f'{len(positions)} fence posts')
        return {'FINISHED'}


class WL_PT_fence_route(bpy.types.Panel):
    bl_idname = 'WL_PT_fence_route'
    bl_label = 'Fence Route'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_order = -10

    @classmethod
    def poll(cls, context):
        return WL_OT_fence_route.poll(context)

    def draw(self, context):
        config = context.object.wl_fence_route
        for field in ('spacing', 'post_width', 'post_height', 'gate_center', 'gate_width', 'material'):
            self.layout.prop(config, field)
        row = self.layout.row(align=True)
        for action in ('PREVIEW', 'APPLY', 'DISCARD'):
            row.operator(WL_OT_fence_route.bl_idname, text=action.title()).action = action


class WL_OT_add_fence_route(bpy.types.Operator):
    bl_idname = 'wavelength.add_fence_route'
    bl_label = 'Add Fence Route'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and workspace.active(context, 'editing')

    def execute(self, context):
        curve = bpy.data.curves.new('Fence Route', 'CURVE')
        curve.dimensions = '3D'
        spline = curve.splines.new('POLY')
        spline.points.add(1)
        spline.points[0].co = (0., 0., 0., 1.)
        spline.points[1].co = (4., 0., 0., 1.)
        route = bpy.data.objects.new('Fence Route', curve)
        context.collection.objects.link(route)
        route.location = context.scene.cursor.location
        for obj in context.selected_objects:
            obj.select_set(False)
        route.select_set(True)
        context.view_layer.objects.active = route
        return {'FINISHED'}


def _draw_add_menu(self, context):
    if WL_OT_add_fence_route.poll(context):
        self.layout.operator(WL_OT_add_fence_route.bl_idname, icon='CURVE_DATA')


def register():
    bpy.utils.register_class(WL_PG_fence_route)
    bpy.types.Object.wl_fence_route = bpy.props.PointerProperty(type=WL_PG_fence_route)
    bpy.utils.register_class(WL_OT_fence_route)
    bpy.utils.register_class(WL_PT_fence_route)
    bpy.utils.register_class(WL_OT_add_fence_route)
    bpy.types.VIEW3D_MT_add.append(_draw_add_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(_draw_add_menu)
    bpy.utils.unregister_class(WL_OT_add_fence_route)
    bpy.utils.unregister_class(WL_PT_fence_route)
    bpy.utils.unregister_class(WL_OT_fence_route)
    del bpy.types.Object.wl_fence_route
    bpy.utils.unregister_class(WL_PG_fence_route)
