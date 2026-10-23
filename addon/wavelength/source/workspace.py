"""Workspace lifecycle; no transform-correction timers or global editing hooks."""
import bpy
from bpy.app.handlers import persistent

MARKER = 'wl_workspace'

def active(context=None, feature=None):
    from . import context_policy
    return context_policy.allows(context or bpy.context,feature)


def ensure(context, reset=False):
    if bpy.app.background or not context.window:
        return None
    existing = next((ws for ws in bpy.data.workspaces if ws.get(MARKER) or ws.name == 'wavelength'), None)
    original = context.window.workspace
    if existing and reset:
        existing["wl_layout_ready"]=False
        return existing
    if existing and not reset:
        existing[MARKER] = True
        return existing
    # Duplicate a layout, never change the user's existing workspace.
    before = set(bpy.data.workspaces)
    bpy.ops.workspace.duplicate()
    created = next(ws for ws in bpy.data.workspaces if ws not in before)
    created.name = 'wavelength' if not existing else 'wavelength reset'
    created[MARKER] = True
    for area in created.screens[0].areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.show_region_ui = False
            area.spaces.active.show_region_tool_header = True
    context.window.workspace = original
    return created


@persistent
def load(_unused=None):
    if not bpy.app.timers.is_registered(startup):
        bpy.app.timers.register(startup, first_interval=.2)


def startup():
    if bpy.app.background:
        return None
    try:
        for window in bpy.context.window_manager.windows:
            with bpy.context.temp_override(window=window):
                ensure(bpy.context)
    except (RuntimeError, AttributeError):
        return 1.0
    return None


def watch():
    if bpy.app.background:return None
    try:
        for window in bpy.context.window_manager.windows:
            with bpy.context.temp_override(window=window):
                if not active(feature='preparation'):continue
                ws=window.workspace
                if not ws.get('wl_layout_ready'):
                    from .entity.browser import ensure_browser_layout
                    ensure_browser_layout(bpy.context);ws['wl_layout_ready']=True
                settings=window.scene.wavelength
                if settings.engine!='blender':
                    from . import external_library,asset_browser
                    texture_token=repr(tuple(getattr(settings,k) for k in external_library.FIELDS))
                    if external_library._key is None or ws.get('wl_texture_catalog')!=texture_token or external_library._status.get('state')=='PAUSED':
                        asset_browser.schedule_profile_sync(bpy.context)
                        ws['wl_texture_catalog']=texture_token
                token=settings.engine+'|'+settings.fgd_path
                if settings.engine!='blender' and settings.asset_browser_section=='ENTITIES' and ws.get('wl_entity_catalog')!=token:
                    from .entity.browser import rebuild
                    rebuild(bpy.context);ws['wl_entity_catalog']=token
    except (RuntimeError,AttributeError,ValueError) as exc:
        print('Wavelength workspace:',exc)
    return .5


class WL_OT_workspace(bpy.types.Operator):
    bl_idname='wavelength.workspace'; bl_label='Open Wavelength Workspace'
    reset:bpy.props.BoolProperty(default=False)
    def execute(self, context):
        ws=ensure(context, self.reset)
        if ws: context.window.workspace=ws
        return {'FINISHED'}


class WL_OT_workspace_toggle(bpy.types.Operator):
    bl_idname='wavelength.workspace_toggle'; bl_label='Toggle Wavelength Feature'
    feature:bpy.props.StringProperty()
    def execute(self, context):
        key='wl_'+self.feature
        if self.feature=='snapping':
            context.scene.tool_settings.use_snap=not context.scene.tool_settings.use_snap
        else:context.workspace[key]=not context.workspace.get(key, True)
        for area in context.screen.areas: area.tag_redraw()
        return {'FINISHED'}


def draw_controls(layout, context):
    if not active(context):
        layout.operator('wavelength.workspace', icon='WORKSPACE')
        if not (context.workspace and context.workspace.get(MARKER)):
            return False
    row=layout.row(align=True)
    for name,label in [('enabled','Editing'),('grid','Grid'),('snapping','Snap'),('gizmos','Handles'),('textures','Live UV')]:
        op=row.operator('wavelength.workspace_toggle',text=label,depress=context.scene.tool_settings.use_snap if name=='snapping' else context.workspace.get('wl_'+name,True));op.feature=name
    return True


def register():
    for cls in (WL_OT_workspace, WL_OT_workspace_toggle): bpy.utils.register_class(cls)
    if load not in bpy.app.handlers.load_post: bpy.app.handlers.load_post.append(load)
    load()
    if not bpy.app.timers.is_registered(watch):bpy.app.timers.register(watch,first_interval=.5,persistent=True)


def unregister():
    if bpy.app.timers.is_registered(watch):bpy.app.timers.unregister(watch)
    if startup and bpy.app.timers.is_registered(startup): bpy.app.timers.unregister(startup)
    if load in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(load)
    for cls in (WL_OT_workspace_toggle, WL_OT_workspace): bpy.utils.unregister_class(cls)
