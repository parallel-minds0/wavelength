"""Fit a procedural straight stair to two world-space landing connections."""
import json
from dataclasses import replace
from math import isfinite

import bpy
from mathutils import Matrix, Vector

from . import primitive_ui, procedural, workspace


def _proposal(root):
    obj = root.get('wl_landing_preview')
    return obj if obj and obj.parent == root and obj.get('wl_landing_proposal') else None


def discard(root):
    obj = _proposal(root)
    if obj:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    if 'wl_landing_preview' in root:
        del root['wl_landing_preview']


def _straight_root(context):
    root = primitive_ui.root_for(context.object)
    if (root and root.get('wl_primitive') == 'STAIRS' and root.get('wl_definition')
            and procedural.state(root) == 'PROCEDURAL'):
        definition = procedural.Definition.loads(root['wl_definition'])
        if not definition.parameters.get('curved'):
            return root
    return None


def _fit(root, context):
    settings = root.wl_landing_stair
    points = []
    for anchor in (settings.lower, settings.upper):
        if not anchor or context.scene.objects.get(anchor.name) != anchor:
            raise ValueError('Choose lower and upper connection objects in this scene')
        ancestor = anchor
        while ancestor:
            if ancestor == root:
                raise ValueError('Landing connections must be independent of the stair')
            ancestor = ancestor.parent
        points.append(anchor.matrix_world.translation.copy())
    start, end = points
    delta = end - start
    horizontal = Vector((delta.x, delta.y, 0))
    if not all(isfinite(value) for value in delta) or delta.z <= 0 or horizontal.length <= 1e-6:
        raise ValueError('The upper connection must be higher and horizontally separated')
    for part in primitive_ui.parts_for(root):
        local = part.matrix_parent_inverse @ part.matrix_basis
        if any(abs(local[i][j] - (i == j)) > 1e-6 for i in range(4) for j in range(4)):
            raise ValueError('Reset individual stair part transforms before fitting landings')
    original = procedural.Definition.loads(root['wl_definition'])
    values = dict(original.parameters)
    unit = original.unit_meters
    rise = delta.z / settings.steps / unit
    run = horizontal.length / settings.steps / unit
    if ((settings.max_rise and rise > settings.max_rise)
            or (settings.min_tread and run < settings.min_tread)):
        raise ValueError(f'{settings.steps} steps give {rise:.4g} rise and {run:.4g} tread in profile units')
    values.update(steps=settings.steps, rise=rise, run=run, landing=0., direction=0.)
    definition = replace(original, parameters=values, grid_step=None)
    forward = horizontal.normalized()
    side = Vector((forward.y, -forward.x, 0))
    basis = Matrix((side, forward, Vector((0, 0, 1)))).transposed().to_4x4()
    basis.translation = start
    stamp = json.dumps([root['wl_definition'], list(start), list(end), settings.steps,
                        settings.max_rise, settings.min_tread,
                        [list(row) for row in root.matrix_world]])
    return definition, basis, stamp


def _preview(root, definition, basis, stamp):
    parts = procedural.validate(definition, procedural.evaluate(definition))
    vertices, faces = [], []
    for points, polygons in parts:
        offset = len(vertices)
        vertices.extend(basis @ (Vector(point) * definition.unit_meters) for point in points)
        faces.extend(tuple(offset + index for index in face) for face in polygons)
    mesh = bpy.data.meshes.new('Landing stair preview')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    discard(root)
    obj = bpy.data.objects.new('Landing stair preview', mesh)
    root.users_collection[0].objects.link(obj)
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted_safe()
    obj['wl_landing_proposal'] = stamp
    obj['wl_exclude'] = True
    obj.hide_select = True
    obj.hide_render = True
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    root['wl_landing_preview'] = obj


class WL_PG_landing_stair(bpy.types.PropertyGroup):
    lower: bpy.props.PointerProperty(name='Lower Connection', type=bpy.types.Object)
    upper: bpy.props.PointerProperty(name='Upper Connection', type=bpy.types.Object)
    steps: bpy.props.IntProperty(name='Steps', default=8, min=1, max=64)
    max_rise: bpy.props.FloatProperty(name='Max Rise', description='Profile units. Zero disables the limit', min=0)
    min_tread: bpy.props.FloatProperty(name='Min Tread', description='Profile units. Zero disables the limit', min=0)


class WL_OT_landing_stair(bpy.types.Operator):
    bl_idname = 'wavelength.landing_stair'
    bl_label = 'Fit Stair to Landings'
    bl_options = {'UNDO'}

    action: bpy.props.EnumProperty(items=[
        ('PREVIEW', 'Preview', ''), ('APPLY', 'Apply', ''), ('DISCARD', 'Discard', ''),
    ])

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and workspace.active(context) and _straight_root(context) is not None

    def execute(self, context):
        root = _straight_root(context)
        try:
            if self.action == 'DISCARD':
                discard(root)
                return {'FINISHED'}
            definition, basis, stamp = _fit(root, context)
            if self.action == 'PREVIEW':
                _preview(root, definition, basis, stamp)
                return {'FINISHED'}
            proposal = _proposal(root)
            if not proposal or proposal['wl_landing_proposal'] != stamp:
                raise ValueError('Preview the current connections and settings before applying')
            previous = root.matrix_world.copy()
            root.matrix_world = basis
            try:
                primitive_ui.rebuild(root, 'STAIRS', definition.parameters, context, exact_dimensions=True)
            except (ValueError, RuntimeError):
                root.matrix_world = previous
                raise
            discard(root)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class WL_PT_landing_stair(bpy.types.Panel):
    bl_idname = 'WL_PT_landing_stair'
    bl_label = 'Fit Stair to Landings'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_order = -10

    @classmethod
    def poll(cls, context):
        return workspace.active(context) and _straight_root(context) is not None

    def draw(self, context):
        root = _straight_root(context)
        layout = self.layout
        layout.enabled = context.mode == 'OBJECT'
        settings = root.wl_landing_stair
        for field in ('lower', 'upper', 'steps', 'max_rise', 'min_tread'):
            layout.prop(settings, field)
        row = layout.row(align=True)
        for action in ('PREVIEW', 'APPLY', 'DISCARD'):
            row.operator(WL_OT_landing_stair.bl_idname, text=action.title()).action = action


def register():
    bpy.utils.register_class(WL_PG_landing_stair)
    bpy.types.Object.wl_landing_stair = bpy.props.PointerProperty(type=WL_PG_landing_stair)
    bpy.utils.register_class(WL_OT_landing_stair)
    bpy.utils.register_class(WL_PT_landing_stair)


def unregister():
    bpy.utils.unregister_class(WL_PT_landing_stair)
    bpy.utils.unregister_class(WL_OT_landing_stair)
    del bpy.types.Object.wl_landing_stair
    bpy.utils.unregister_class(WL_PG_landing_stair)
