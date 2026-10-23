"""Workspace-scoped engine tool column and undoable grid transforms."""
import math
import bpy
from mathutils import Matrix, Vector
from . import workspace, profiles, tool_snap, axis_guides

_original_draw = None


class WL_OT_engine_transform(bpy.types.Operator):
    bl_idname = 'wavelength.engine_transform'
    bl_label = 'Engine Transform'
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    kind: bpy.props.EnumProperty(items=[('ROTATE', 'Rotate', ''), ('SCALE', 'Scale', '')])
    release_confirm: bpy.props.BoolProperty(default=False)
    axis: bpy.props.EnumProperty(items=[(a, a, '') for a in ('FREE', 'X', 'Y', 'Z')], default='FREE')

    @classmethod
    def poll(cls, context):
        from .precision_move import WL_OT_precision_move
        return bool(WL_OT_precision_move.poll(context))

    def invoke(self, context, event):
        if tool_snap.enabled(context,event,self.kind) and not tool_snap.grid_enabled(context,event,self.kind):
            operator=bpy.ops.transform.rotate if self.kind=='ROTATE' else bpy.ops.transform.resize
            operator('INVOKE_DEFAULT',constraint_axis=tuple(self.axis==a for a in 'XYZ'))
            return {'FINISHED'}
        from . import primitive_ui
        from .precision_move import WL_OT_precision_move
        primitive_ui.sync_assemblies(force=True)
        self._objects = [(o, o.matrix_world.copy()) for o in context.selected_objects
                         if not any(p.select_get() for p in WL_OT_precision_move.parents(o))]
        self._pivot = context.object.matrix_world.translation.copy()
        self._dimensions = context.object.dimensions.copy()
        self._mouse = event.mouse_x
        self._value = ''
        self._step = tool_snap.step(context)
        context.area.header_text_set('Engine ' + self.kind.title() + ': X/Y/Z axis · type degrees / scale factor · Ctrl free · Enter confirm · Esc cancel')
        axis_guides.start(self,context,self._pivot)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self,context):
        axis_guides.finish(self,context)

    def modal(self, context, event):
        if event.type=='TAB' and event.shift:return {'PASS_THROUGH'}
        if event.type in {'ESC', 'RIGHTMOUSE'} or not workspace.active(context, 'snapping'):
            for obj, matrix in self._objects:
                obj.matrix_world = matrix
            axis_guides.finish(self,context)
            return {'CANCELLED'}
        if ((event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS') or
                (event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and getattr(self, 'release_confirm', False))):
            axis_guides.finish(self,context)
            return {'FINISHED'}
        if event.value == 'PRESS':
            if event.type in {'X', 'Y', 'Z'}:
                self.axis = event.type
            elif event.type == 'BACK_SPACE':
                self._value = self._value[:-1]
            elif event.unicode and event.unicode in '0123456789.-':
                self._value += event.unicode
        axis_guides.update(self)
        if event.type == 'MOUSEMOVE' or event.value == 'PRESS':
            try:
                amount = float(self._value) if self._value else None
            except ValueError:
                return {'RUNNING_MODAL'}
            distance = event.mouse_x - self._mouse
            if self.kind == 'ROTATE':
                degrees = amount if amount is not None else distance * .5
                if amount is None and tool_snap.enabled(context,event,'ROTATE'):
                    ts=context.scene.tool_settings
                    key='snap_angle_increment_3d_precision' if event.shift else 'snap_angle_increment_3d'
                    increment=math.degrees(getattr(ts,key,math.radians(5)))
                    if increment>1e-8:degrees=round(degrees/increment)*increment
                axis = self.axis if self.axis != 'FREE' else 'Z'
                change = Matrix.Rotation(math.radians(degrees), 4, axis)
            else:
                factor = amount if amount is not None else 1 + distance / 150
                factors = [factor if self.axis == 'FREE' or self.axis == a else 1 for a in 'XYZ']
                if amount is None and tool_snap.grid_enabled(context,event,'SCALE'):
                    for i in range(3):
                        size = self._dimensions[i]
                        if size > 1e-8 and (self.axis == 'FREE' or self.axis == 'XYZ'[i]):
                            sign = -1 if factors[i] < 0 else 1
                            factors[i] = sign * max(self._step, round(abs(size * factors[i]) / self._step) * self._step) / size
                change = Matrix.Diagonal((*factors, 1))
            change = Matrix.Translation(self._pivot) @ change @ Matrix.Translation(-self._pivot)
            for obj, original in self._objects:
                obj.matrix_world = change @ original
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}


class WL_GGT_engine_transform(bpy.types.GizmoGroup):
    bl_idname = 'WL_GGT_engine_transform'
    bl_label = 'Engine Rotate and Scale'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        if not WL_OT_engine_transform.poll(context) or not workspace.active(context, 'gizmos'):
            return False
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        return bool(tool and tool.idname in {t.bl_idname for t in TOOLS})

    def setup(self, context):
        self.handles = []
        for kind in ('ROTATE', 'SCALE'):
            for i, color in enumerate(((.8, .15, .15), (.15, .8, .15), (.15, .3, .9))):
                g = self.gizmos.new('GIZMO_GT_dial_3d' if kind == 'ROTATE' else 'GIZMO_GT_arrow_3d')
                if kind == 'SCALE':
                    g.draw_style = 'BOX'
                    g.length = .65
                g.color = g.color_highlight = color
                g.alpha = .7
                g.alpha_highlight = 1
                g.scale_basis = .8 if kind == 'ROTATE' else .65
                op = g.target_set_operator('wavelength.engine_transform')
                op.release_confirm = True
                op.kind = kind
                op.axis = 'XYZ'[i]
                self.handles.append((g, kind, i))

    def draw_prepare(self, context):
        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False).idname
        for g, kind, i in self.handles:
            g.hide = tool not in {'builtin.transform','builtin.'+kind.lower(),'wavelength.engine_transform_tool','wavelength.engine_'+kind.lower()+'_tool'}
            direction = Vector(tuple(float(j == i) for j in range(3)))
            matrix = direction.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            matrix.translation = context.object.matrix_world.translation
            g.matrix_basis = matrix


def _tool(name, label, icon, kind=None):
    keymap = () if kind is None else (('wavelength.engine_transform', {'type': 'LEFTMOUSE', 'value': 'PRESS'}, {'properties': [('kind', kind)]}),)
    return type(name, (bpy.types.WorkSpaceTool,), dict(
        bl_space_type='VIEW_3D', bl_context_mode='OBJECT',
        bl_idname='wavelength.engine_' + label.lower() + '_tool',
        bl_label='Engine ' + label, bl_description='Engine ' + label.lower() + ' with axis handles and grid increments',
        bl_icon=icon, bl_widget='WL_GGT_engine_transform', bl_keymap=keymap))


TOOLS = (_tool('WL_Tool_rotate', 'Rotate', 'ops.transform.rotate', 'ROTATE'),
         _tool('WL_Tool_scale', 'Scale', 'ops.transform.resize', 'SCALE'),
         _tool('WL_Tool_transform', 'Transform', 'ops.transform.transform'))


def _draw(self, context):
    if context.mode != 'OBJECT':
        return _original_draw(self, context)
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
    from .brush_create import TOOLS as brushes
    from .precision_move import WL_Tool_move
    # Filter only the drawing iterator. Tool lookup/activation retains Blender's
    # complete registered definitions, including the brush hold-menu group.
    class NativeColumn(ToolSelectPanelHelper):
        _tool_group_active = VIEW3D_PT_tools_active._tool_group_active
        @classmethod
        def tools_from_context(cls, ctx):
            for item in VIEW3D_PT_tools_active.tools_from_context(ctx):
                if type(item) is tuple:
                    item = tuple(t for t in item if t is None or not t.idname.startswith('wavelength.'))
                    if not any(t is not None for t in item):
                        continue
                elif item is not None and item.idname.startswith('wavelength.'):
                    continue
                yield item
    if not workspace.active(context):
        return NativeColumn.draw_cls(self.layout, context)
    context.workspace['wl_toolbar_columns'] = 2
    icon_value = ToolSelectPanelHelper._icon_value_from_icon_handle
    row = self.layout.row(align=False)
    row.alignment = 'EXPAND'
    row.scale_x = 1.925
    native = row.column(align=True)
    native.scale_y = 1.75
    active_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    active_name = active_tool.idname if active_tool else ''
    for item in NativeColumn.tools_from_context(context):
        if item is None:
            native.separator()
            continue
        group = type(item) is tuple
        if group:
            index = next((i for i, t in enumerate(item) if t is not None and t.idname == active_name), None)
            if index is not None:
                VIEW3D_PT_tools_active._tool_group_active[item[0].idname] = index
            item = item[index] if index is not None else item[VIEW3D_PT_tools_active._tool_group_active_get_from_item(item)]
        if group:
            op = native.operator_menu_hold('wm.tool_set_by_id', text='', icon_value=icon_value(item.icon),
                                           depress=item.idname == active_name, menu='WM_MT_toolsystem_submenu')
        else:
            op = native.operator('wm.tool_set_by_id', text='', icon_value=icon_value(item.icon),
                                 depress=item.idname == active_name)
        op.name = item.idname
    row.separator(factor=0.15)
    col = row.column(align=True)
    col.scale_y = 1.75
    active = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    active_id = active.idname if active else ''
    group_state = VIEW3D_PT_tools_active._tool_group_active
    brush_index = next((i for i, t in enumerate(brushes) if t.bl_idname == active_id), None)
    if brush_index is not None:
        group_state[brushes[0].bl_idname] = brush_index
    brush = brushes[min(group_state.get(brushes[0].bl_idname, 0), len(brushes) - 1)]
    icon = icon_value
    col.operator_menu_hold('wm.tool_set_by_id', text='', icon_value=icon(brush.bl_icon),
                          depress=active_id in {t.bl_idname for t in brushes},
                          menu='WM_MT_toolsystem_submenu').name = brush.bl_idname
    from .pencil import WL_Tool_pencil
    col.operator('wavelength.activate_cutter',text='',icon_value=icon(WL_Tool_pencil.bl_icon),depress=active_id==WL_Tool_pencil.bl_idname)
    if context.scene.wavelength.engine=='blender' or profiles.is_source(context.scene.wavelength.engine):
        if context.object and context.object.get('wl_terrain') and context.object.get('wl_procedural_state')=='PROCEDURAL':
            from . import terrain
            if not terrain.paintable(context.object):
                col.operator('wavelength.terrain_enable_paint',text='',icon='MESH_GRID')
            else:
                col.prop(context.object.wavelength_terrain,'flat_preview',text='',icon='MESH_PLANE',toggle=True)
                from .terrain_paint import paint_button
                paint_button(col,context)



def register():
    global _original_draw
    bpy.utils.register_class(WL_OT_engine_transform)
    bpy.utils.register_class(WL_GGT_engine_transform)
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    _original_draw = VIEW3D_PT_tools_active.draw
    VIEW3D_PT_tools_active.draw = _draw


def _clear_workspace_flags():
    for ws in bpy.data.workspaces:
        if 'wl_toolbar_columns' in ws:del ws['wl_toolbar_columns']
    return None


def unregister():
    global _original_draw
    axis_guides.clear()
    # Unregistration can also run under Blender's restricted addon context.
    if not bpy.app.timers.is_registered(_clear_workspace_flags):
        bpy.app.timers.register(_clear_workspace_flags,first_interval=.1)
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    if _original_draw is not None:
        VIEW3D_PT_tools_active.draw = _original_draw
        _original_draw = None
    bpy.utils.unregister_class(WL_GGT_engine_transform)
    bpy.utils.unregister_class(WL_OT_engine_transform)

