"""Blender editor integration: editing in context, setup in a small menu."""
import bpy
from . import workspace, profiles, grid, primitive_ui


def editing(context):
    return workspace.active(context)


def engine_editing(context):
    return editing(context) and context.scene.wavelength.engine != 'blender'


class WL_PT_grid(bpy.types.Panel):
    bl_idname = 'WL_PT_grid'
    bl_label = 'Map Grid & Snapping'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    @classmethod
    def poll(cls, context):
        return editing(context)

    def draw(self, context):
        s = context.scene.wavelength
        l = self.layout
        l.use_property_split = True
        l.prop(s, 'grid_mode', expand=True)
        row = l.row(align=True)
        row.operator('wavelength.grid_step', text='−').direction = -1
        row.prop(s, 'grid_step' if grid.engine_enabled(s) else 'metric_grid_step', text='Spacing')
        row.operator('wavelength.grid_step', text='+').direction = 1
        l.prop(s, 'grid_subdivisions')
        if s.engine == 'blender':
            l.prop(s, 'snap_to_grid')
        for feature, label in (('grid', 'Map Grid'), ('snapping', 'Map Snapping')):
            op = l.operator('wavelength.workspace_toggle', text=label,
                            depress=context.workspace.get('wl_' + feature, True))
            op.feature = feature
        l.operator('wavelength.snap_grid', text='Snap Selection to Grid')
        if not grid.native_available(context.space_data):
            l.label(text='Native grid patch missing: repair installation', icon='ERROR')


class WL_OT_inspect(bpy.types.Operator):
    bl_idname = 'wavelength.inspect'
    bl_label = 'Inspect Wavelength Object'
    bl_description = 'Show the selected object in Object Properties'

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.spaces.active.context = 'OBJECT'
                area.tag_redraw()
                return {'FINISHED'}
        self.report({'INFO'}, 'Open a Properties editor and choose Object Properties')
        return {'FINISHED'}


class WL_OT_map_settings(bpy.types.Operator):
    bl_idname = 'wavelength.map_settings'
    bl_label = 'Map and Project Settings'

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                area.spaces.active.context = 'SCENE'
                area.tag_redraw()
                return {'FINISHED'}
        self.report({'INFO'}, 'Open Scene Properties for map and project settings')
        return {'FINISHED'}


class WL_PT_selection(bpy.types.Panel):
    bl_idname = 'WL_PT_selection'
    bl_label = 'Map Object'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'

    @classmethod
    def poll(cls, context):
        obj = context.object
        return engine_editing(context) and obj is not None and bool(
            obj.get('wl_role') or primitive_ui.root_for(obj))

    def draw(self, context):
        from . import ui
        obj = context.object
        _, pairs, _ = ui._entity_property_target(obj)
        label = dict(pairs).get('classname', '') if pairs else ''
        self.layout.label(text=label or obj.get('wl_role', 'Assembly').title())
        self.layout.operator('wavelength.inspect', text='Object Properties', icon='PROPERTIES')


class WL_PT_object(bpy.types.Panel):
    bl_idname = 'WL_PT_object'
    bl_label = 'Wavelength Object'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        return engine_editing(context) and context.object is not None

    def draw(self, context):
        from . import ui
        obj = ui._resolve_brush_object(context.object)
        l = self.layout
        role = obj.get('wl_role', 'Unassigned')
        l.label(text='Export role: ' + role.title())
        if 'wl_exclude' in obj:
            l.prop(obj, '["wl_exclude"]', text='Exclude from Export')
        if role != 'BRUSH':
            if obj.type == 'MESH':
                l.operator('wavelength.mark_brush', text='Use Mesh as Brush')
            return
        if obj.get('wl_entity_id'):
            count = len(ui._brush_entity_members(context.scene, obj['wl_entity_id']))
            l.label(text=f'Brush entity: {count} solids')
            row = l.row(align=True)
            row.operator('wavelength.brush_entity_add', text='Add Selected')
            row.operator('wavelength.brush_entity_remove', text='Remove Selected')
            l.operator('wavelength.brush_entity_to_world', text='Convert Entity to World')
        else:
            l.prop(context.scene.wavelength, 'entity_choice', text='Entity Class')
            l.operator('wavelength.brush_entity', text='Make Brush Entity')


class WL_MT_setup(bpy.types.Menu):
    bl_idname = 'WL_MT_setup'
    bl_label = 'Wavelength'

    def draw(self, context):
        l = self.layout
        l.popover(panel='WL_PT_profiles', text='Manage Profiles', icon='PRESET')
        l.operator('wavelength.map_settings', text='Map and Project Settings', icon='PREFERENCES')
        l.operator('wavelength.save_project')
        l.operator('wavelength.load_project')
        l.separator()
        l.operator('wavelength.workspace', text='Reset Workspace Layout', icon='WORKSPACE').reset = True
        l.menu('WL_MT_features', text='Workspace Features')
        l.separator()
        l.operator('wavelength.view_log', text='View Diagnostics Log', icon='TEXT')
        l.operator('wavelength.export_log', text='Export Diagnostics Log')
        l.operator('wavelength.asset_report', text='Asset Dependency Report')
        from .. import bl_info
        l.label(text='Wavelength ' + '.'.join(map(str, bl_info['version'])))


class WL_MT_features(bpy.types.Menu):
    bl_idname = 'WL_MT_features'
    bl_label = 'Workspace Features'

    def draw(self, context):
        for feature, label in (('enabled', 'Editing'), ('grid', 'Map Grid'),
                               ('snapping', 'Map Snapping'), ('gizmos', 'Handles'),
                               ('textures', 'Live UV')):
            enabled = context.workspace.get('wl_' + feature, True)
            self.layout.operator('wavelength.workspace_toggle', text=label,
                                 icon='CHECKBOX_HLT' if enabled else 'CHECKBOX_DEHLT').feature = feature


class WL_MT_face_mapping(bpy.types.Menu):
    bl_idname = 'WL_MT_face_mapping'
    bl_label = 'Face Mapping'

    def draw(self, context):
        l = self.layout
        l.operator('wavelength.read_face_texture', text='Read Selected Face')
        l.operator('wavelength.apply_texture', text='Apply Mapping')
        l.separator()
        l.operator('wavelength.texture_copy', text='Copy Mapping')
        l.operator('wavelength.texture_paste', text='Paste Mapping')
        l.separator()
        for action, label in (('RESET', 'Reset Mapping'), ('ROT90', 'Rotate 90°'),
                              ('FLIP_U', 'Flip U'), ('FLIP_V', 'Flip V')):
            l.operator('wavelength.texture_nudge', text=label).action = action


def draw_header(self, context):
    ws = context.workspace
    if not ws or not ws.get(workspace.MARKER, ws.name == 'wavelength'):
        return
    s = context.scene.wavelength
    l = self.layout
    l.separator()
    l.menu('WL_MT_setup', text='Wavelength')
    if not editing(context):
        return
    l.popover(panel='WL_PT_profiles', text='', icon='PRESET')
    l.popover(panel='WL_PT_grid', text=str(profiles.grid_step_units(s)) if grid.engine_enabled(s) else 'Grid', icon='GRID')
    if engine_editing(context):
        from . import ui
        row = l.row(align=True)
        row.operator('wavelength.validate_alpha', text='', icon='CHECKMARK')
        build = row.row(align=True)
        build.enabled = ui._JOB is None
        if s.build_output:
            build.operator_context = 'EXEC_DEFAULT'
        op = build.operator('wavelength.build', text='Build', icon='MOD_BUILD')
        op.filepath = s.build_output
        row.operator('wavelength.launch', text='', icon='PLAY')
        if ui._JOB:
            row.operator('wavelength.cancel_build', text='', icon='CANCEL')


def draw_grid(self, context):
    if editing(context):
        self.layout.separator()
        self.layout.popover(panel='WL_PT_grid', text='Map Grid & Snapping', icon='GRID')


def draw_context(self, context):
    if not engine_editing(context) or context.object is None:
        return
    from . import ui
    obj = ui._resolve_brush_object(context.object)
    l = self.layout
    l.separator()
    if context.mode == 'EDIT_MESH':
        l.menu('WL_MT_face_mapping', icon='UV')
        return
    if obj.type == 'MESH':
        if obj.get('wl_role') == 'BRUSH':
            l.operator('wavelength.make_hollow')
            l.operator('wavelength.clip')
            if obj.get('wl_entity_id'):
                l.operator('wavelength.brush_entity_add')
                l.operator('wavelength.brush_entity_remove')
                l.operator('wavelength.brush_entity_to_world')
            else:
                l.operator('wavelength.brush_entity')
            if profiles.is_goldsrc(context.scene.wavelength.engine):
                l.operator('wavelength.special_brush')
                l.operator('wavelength.origin_brush')
        else:
            l.operator('wavelength.mark_brush', text='Use Mesh as Brush')
    if ui._entity_property_target(obj)[0] is not None:
        l.operator('wavelength.inspect', text='Entity Properties')
        l.operator('wavelength.select_class')
        l.operator('wavelength.select_target', text='Select Targets').direction = 'TARGET'
        l.operator('wavelength.select_target', text='Select Sources').direction = 'SOURCE'
    if obj.get('wl_role') or primitive_ui.root_for(obj):
        l.operator('wavelength.duplicate_assembly')
        l.operator('wavelength.bake_static')
    if profiles.is_goldsrc(context.scene.wavelength.engine):
        l.operator('wavelength.path_chain')


def draw_add_assets(self, context):
    if engine_editing(context) and profiles.is_goldsrc(context.scene.wavelength.engine):
        for kind, label in (('MODEL', 'Model'), ('SPRITE', 'Sprite'), ('DECAL', 'Decal'), ('SOUND', 'Sound')):
            self.layout.operator('wavelength.asset_entity', text=label).kind = kind


def draw_add_brush(self, context):
    if engine_editing(context):
        for kind in ('CUBE', 'CYLINDER', 'CONE'):
            self.layout.operator('wavelength.add_brush', text=kind.title() + ' Brush').kind = kind


def sync_inspector():
    """Load selection-bound fields outside draw(), only for a visible inspector."""
    from . import ui
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if not engine_editing(bpy.context):
                continue
            for area in window.screen.areas:
                if area.type != 'PROPERTIES' or area.spaces.active.context != 'OBJECT':
                    continue
                with bpy.context.temp_override(area=area):
                    key, _, binding = ui._entity_property_target(bpy.context.object)
                    if key and binding != window.scene.wavelength.entity_editor_binding:
                        bpy.ops.wavelength.entity_properties(apply=False)
                        area.tag_redraw()
    return .2


def draw_import(self, context):
    if editing(context):
        self.layout.operator('wavelength.import_map', text='Wavelength Map (.map / .vmf)')


def draw_export(self, context):
    if engine_editing(context):
        self.layout.operator('wavelength.export_map', text='Wavelength Map (.map / .vmf)')


def draw_status(self, context):
    if not engine_editing(context):
        return
    from . import ui
    s = context.scene.wavelength
    if ui._JOB or s.build_error:
        self.layout.label(text=s.status[:100], icon='ERROR' if s.build_error else 'TIME')


CLASSES = (WL_PT_grid, WL_OT_inspect, WL_OT_map_settings, WL_PT_selection, WL_PT_object, WL_MT_features, WL_MT_setup, WL_MT_face_mapping)
HOOKS = (
    (bpy.types.VIEW3D_HT_tool_header, draw_header),
    (bpy.types.VIEW3D_PT_overlay, draw_grid),
    (bpy.types.VIEW3D_PT_snapping, draw_grid),
    (bpy.types.VIEW3D_MT_object_context_menu, draw_context),
    (bpy.types.VIEW3D_MT_edit_mesh_context_menu, draw_context),
    (bpy.types.VIEW3D_MT_add, draw_add_assets),
    (bpy.types.VIEW3D_MT_mesh_add, draw_add_brush),
    (bpy.types.TOPBAR_MT_file_import, draw_import),
    (bpy.types.TOPBAR_MT_file_export, draw_export),
    (bpy.types.STATUSBAR_HT_header, draw_status),
)
_registered = []
_hooks = []


def register():
    try:
        for cls in CLASSES:
            bpy.utils.register_class(cls)
            _registered.append(cls)
        for owner, draw in HOOKS:
            owner.append(draw)
            _hooks.append((owner, draw))
        if not bpy.app.background:
            bpy.app.timers.register(sync_inspector, first_interval=.2, persistent=True)
    except Exception:
        unregister()
        raise


def unregister():
    if bpy.app.timers.is_registered(sync_inspector):
        bpy.app.timers.unregister(sync_inspector)
    for owner, draw in reversed(_hooks):
        owner.remove(draw)
    _hooks.clear()
    for cls in reversed(_registered):
        bpy.utils.unregister_class(cls)
    _registered.clear()
