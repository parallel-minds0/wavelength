"""Native weight painting and persistent checkpoints for continuous terrain."""

import bpy
from bpy.props import StringProperty

from . import terrain_anchors, workspace

BLEND_GROUP = "Terrain Blend"
REVISIONS = "wl_terrain_revisions"


def copy_surface(source):
    """Copy authored mesh data and the native stack without sharing edit state."""
    copy = source.copy()
    copy.data = source.data.copy()
    for key in (REVISIONS, 'wl_terrain_preview'):
        if key in copy:
            del copy[key]
    return copy


def save_revision(source, name):
    name = name.strip()
    if not name or name in source.get(REVISIONS, {}):
        raise ValueError("Choose a unique terrain revision name")
    snapshot = copy_surface(source)
    snapshot.name = f"{source.name} · {name}"
    if REVISIONS not in source:
        source[REVISIONS] = {}
    source[REVISIONS][name] = snapshot
    return snapshot


class TerrainAction:
    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and workspace.active(context) and
                context.object is not None and bool(context.object.get("wl_continuous_terrain")))


class WL_OT_add_terrain_detail(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.add_terrain_detail'
    bl_label = 'Add Terrain Detail'
    bl_options = {'UNDO'}

    def execute(self, context):
        from .terrain_detail import detail_group

        obj = context.object
        if any(mod.type == 'NODES' and mod.node_group and mod.node_group.get('wl_terrain_detail')
               for mod in obj.modifiers):
            self.report({'ERROR'}, 'Terrain Detail is already in the modifier stack')
            return {'CANCELLED'}
        group = detail_group()
        modifier = obj.modifiers.new('Terrain Detail', 'NODES')
        modifier.node_group = group
        return {'FINISHED'}


class WL_OT_paint_terrain_blend(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.paint_terrain_blend'
    bl_label = 'Paint Terrain Blend'
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        group = obj.vertex_groups.get(BLEND_GROUP) or obj.vertex_groups.new(name=BLEND_GROUP)
        obj.vertex_groups.active_index = group.index
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        return {'FINISHED'}


class WL_OT_save_terrain_revision(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.save_terrain_revision'
    bl_label = 'Save Terrain Revision'
    bl_options = {'UNDO'}

    name: StringProperty(name='Revision Name', default='Checkpoint', maxlen=48)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            save_revision(context.object, self.name)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_restore_terrain_revision(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.restore_terrain_revision'
    bl_label = 'Restore Terrain Revision as Copy'
    bl_options = {'UNDO'}

    name: StringProperty(options={'HIDDEN'})

    def execute(self, context):
        snapshot = context.object.get(REVISIONS, {}).get(self.name)
        if snapshot is None:
            self.report({'ERROR'}, 'The terrain revision is unavailable')
            return {'CANCELLED'}
        restored = copy_surface(snapshot)
        restored['wl_exclude'] = True
        context.collection.objects.link(restored)
        for obj in context.selected_objects:
            obj.select_set(False)
        restored.select_set(True)
        context.view_layer.objects.active = restored
        return {'FINISHED'}


class WL_OT_terrain_game_preview(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.terrain_game_preview'
    bl_label = 'Refresh Game Preview'
    bl_options = {'UNDO'}

    mode: bpy.props.EnumProperty(items=[
        ('BASE', 'Base Cage', 'Show the unmodified mesh'),
        ('EVALUATED', 'Evaluated Terrain', 'Show the native modifier result'),
        ('GAME', 'Game Preview', 'Show the active profile output'),
    ], default='GAME')

    def execute(self, context):
        from .terrain_output import preview_mesh

        terrain = context.object
        try:
            mesh = preview_mesh(context, terrain, self.mode)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        preview = terrain.get('wl_terrain_preview')
        if preview is None:
            preview = bpy.data.objects.new(f'{terrain.name} · Game Preview', mesh)
            context.collection.objects.link(preview)
            terrain['wl_terrain_preview'] = preview
            preview['wl_exclude'] = True
            preview.hide_render = True
            preview.hide_select = True
            preview.display_type = 'WIRE'
            preview.show_in_front = True
        else:
            old = preview.data
            preview.data = mesh
            if not old.users:
                bpy.data.meshes.remove(old)
        preview.hide_set(False)
        return {'FINISHED'}


class WL_OT_hide_terrain_game_preview(TerrainAction, bpy.types.Operator):
    bl_idname = 'wavelength.hide_terrain_game_preview'
    bl_label = 'Hide Game Preview'
    bl_options = {'UNDO'}

    def execute(self, context):
        preview = context.object.get('wl_terrain_preview')
        if preview:
            preview.hide_set(True)
        return {'FINISHED'}


class WL_PT_continuous_terrain(bpy.types.Panel):
    bl_label = 'Wavelength Terrain'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'modifier'

    @classmethod
    def poll(cls, context):
        return (context.mode in {'OBJECT', 'EDIT_MESH'} and workspace.active(context) and
                context.object and bool(context.object.get('wl_continuous_terrain')))

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.prop(obj, 'wavelength_terrain_anchor_target')
        layout.prop(obj, 'wavelength_terrain_anchor_falloff')
        if context.mode == 'EDIT_MESH':
            layout.operator('wavelength.bind_terrain_anchor', text='Hold Boundary')
            layout.operator('wavelength.bind_terrain_anchor', text='Follow Target Translation').follow = True
            return
        if obj.get(terrain_anchors.KEY):
            row = layout.row(align=True)
            row.operator('wavelength.refresh_terrain_anchors')
            row.operator('wavelength.refresh_terrain_anchors', text='Clear Anchors').clear = True
        from . import profiles
        if any(binding.get('native') for binding in obj['wl_continuous_terrain'].values()):
            layout.operator('wavelength.use_migrated_terrain',
                            text='Use Migrated Terrain in Source Export' if obj.get('wl_exclude') else 'Use Original Source Displacements')
        if profiles.is_source(context.scene.wavelength.engine):
            layout.prop(context.object, 'wavelength_terrain_power')
        row = layout.row(align=True)
        row.operator('wavelength.terrain_game_preview', text='Base Cage').mode = 'BASE'
        row.operator('wavelength.terrain_game_preview', text='Evaluated').mode = 'EVALUATED'
        row.operator('wavelength.terrain_game_preview', text='Game Preview').mode = 'GAME'
        if context.object.get('wl_terrain_preview'):
            row.operator('wavelength.hide_terrain_game_preview', text='', icon='HIDE_ON')
        layout.operator('wavelength.add_terrain_detail')
        layout.operator('wavelength.paint_terrain_blend')
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator('wavelength.save_terrain_revision')
        for name in context.object.get(REVISIONS, {}).keys():
            layout.operator('wavelength.restore_terrain_revision', text=f'Restore Copy · {name}').name = name


CLASSES = (WL_OT_add_terrain_detail, WL_OT_paint_terrain_blend, WL_OT_save_terrain_revision,
           WL_OT_restore_terrain_revision, WL_OT_terrain_game_preview,
           WL_OT_hide_terrain_game_preview, WL_PT_continuous_terrain)


def register():
    terrain_anchors.register()
    bpy.types.Object.wavelength_terrain_power = bpy.props.IntProperty(
        name='Source Patch Power', default=3, min=2, max=4)
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    terrain_anchors.unregister()
    del bpy.types.Object.wavelength_terrain_power
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
