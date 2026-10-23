"""Blender-only controls for inspecting and sharing add-on diagnostics."""
from pathlib import Path
import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper
from . import diagnostics


class WL_OT_view_log(bpy.types.Operator):
    bl_idname = 'wavelength.view_log'
    bl_label = 'View Log'
    bl_description = 'Show a snapshot of the persistent log in this area; Shift-F5 returns to the viewport'

    def execute(self, context):
        try:
            contents = diagnostics.read()
            text = bpy.data.texts.get('Wavelength Log') or bpy.data.texts.new('Wavelength Log')
            text.clear()
            text.write(contents)
            area = context.area
            if area is not None:
                area.type = 'TEXT_EDITOR'
                area.spaces.active.text = text
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, diagnostics.error(self.bl_idname, exc))
            return {'CANCELLED'}


class WL_OT_copy_log(bpy.types.Operator):
    bl_idname = 'wavelength.copy_log'
    bl_label = 'Copy Log'
    bl_description = 'Copy the Wavelength CLI/error log to the system clipboard'

    def execute(self, context):
        try:
            contents = diagnostics.read()
            if context.window_manager is not None:
                context.window_manager.clipboard = contents
            self.report({'INFO'}, 'Wavelength log copied to clipboard')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, diagnostics.error(self.bl_idname, exc))
            return {'CANCELLED'}


class WL_OT_clear_log(bpy.types.Operator):
    bl_idname = 'wavelength.clear_log'
    bl_label = 'Clear Log'
    bl_description = 'Clear the Wavelength CLI/error log entries'

    def execute(self, context):
        diagnostics.clear()
        text = bpy.data.texts.get('Wavelength Log')
        if text is not None:
            text.clear()
        self.report({'INFO'}, 'Wavelength log cleared')
        return {'FINISHED'}


class WL_OT_export_log(bpy.types.Operator, ExportHelper):
    bl_idname = 'wavelength.export_log'
    bl_label = 'Export Log'
    bl_description = 'Save the current log for troubleshooting; review local paths before sharing'
    filename_ext = '.log'
    filter_glob: StringProperty(default='*.log', options={'HIDDEN'})

    def invoke(self, context, event):
        self.filepath = 'wavelength.log'
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        try:
            destination = Path(bpy.path.abspath(self.filepath)).expanduser()
            if diagnostics.log_path and destination.resolve() == diagnostics.log_path.resolve():
                raise ValueError('Choose a different path from the active log')
            destination.write_text(diagnostics.read(), encoding='utf-8')
            self.report({'INFO'}, f'Log saved: {destination}')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, diagnostics.error(self.bl_idname, exc))
            return {'CANCELLED'}


CLASSES = (WL_OT_view_log, WL_OT_copy_log, WL_OT_clear_log, WL_OT_export_log)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    from . import geometry_debug
    geometry_debug.register()


def unregister():
    from . import geometry_debug
    geometry_debug.unregister()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

