"""Native toolbar identities with wavelength controllers and exclusive G/R/S.

The native event filter skips competing transform keymap entries only when this
module's route operator polls. No user keymap flags or preferences are mutated.
Tool definitions are adapted per context; the original definitions remain intact.
"""
import bpy
from . import workspace

NATIVE={'builtin.move':'MOVE','builtin.rotate':'ROTATE','builtin.scale':'SCALE','builtin.transform':'TRANSFORM'}
LEGACY={'wavelength.precision_move_tool':'builtin.move',**{'wavelength.engine_'+name+'_tool':'builtin.'+name for name in ('rotate','scale','transform')}}
_keys=[];_original_tools=None;_states={}

def available(context):
    from .precision_move import WL_OT_precision_move
    return bool(WL_OT_precision_move.poll(context) and context.object)

class WL_OT_profile_grid_context(bpy.types.Operator):
    """Native adapters query this context gate, then the profile spacing RNA."""
    bl_idname='wavelength.profile_grid_context';bl_label='Profile Grid Context'
    @classmethod
    def poll(cls,context):
        from . import tool_snap
        return bool(context.area and context.area.type=='VIEW_3D' and workspace.active(context,'snapping') and tool_snap.profile_grid_active(context))
    def execute(self,context):return {'FINISHED'}

class WL_OT_transform_route(bpy.types.Operator):
    bl_idname='wavelength.transform_route';bl_label='Profile Transform'
    kind:bpy.props.EnumProperty(items=[(key,key.title(),'') for key in ('MOVE','ROTATE','SCALE')],default='MOVE')
    @classmethod
    def poll(cls,context):return available(context)
    def invoke(self,context,event):
        if self.kind=='MOVE':bpy.ops.wavelength.precision_move('INVOKE_DEFAULT')
        else:bpy.ops.wavelength.engine_transform('INVOKE_DEFAULT',kind=self.kind)
        return {'FINISHED'}

class WL_GGT_native_transform(bpy.types.GizmoGroup):
    bl_idname='WL_GGT_native_transform';bl_label='Profile Transform Controllers'
    bl_space_type='VIEW_3D';bl_region_type='WINDOW';bl_options={'3D','PERSISTENT'}
    @classmethod
    def poll(cls,context):
        tool=context.workspace.tools.from_space_view3d_mode(context.mode,create=False)
        return available(context) and workspace.active(context,'gizmos') and tool and tool.idname in NATIVE
    def setup(self,context):
        from .precision_move import WL_GGT_move
        from .engine_tools import WL_GGT_engine_transform
        WL_GGT_move.setup(self,context);WL_GGT_engine_transform.setup(self,context)
    def draw_prepare(self,context):
        from .precision_move import WL_GGT_move
        from .engine_tools import WL_GGT_engine_transform
        tool=context.workspace.tools.from_space_view3d_mode(context.mode,create=False).idname
        WL_GGT_move.draw_prepare(self,context);WL_GGT_engine_transform.draw_prepare(self,context)
        for arrow in self.arrows:arrow.hide=tool not in {'builtin.move','builtin.transform'}

def draw_settings(context,layout,tool):
    layout.label(text='Profile transform · World axes')
    layout.prop(context.scene.tool_settings,'use_snap',text='Snap')

# docs:begin transform-routing

def tools_from_context(cls,context,mode=None):
    enabled=available(context) and (mode is None or mode=='OBJECT')
    def adapt(item):
        if item is None:return None
        if type(item) is tuple:return tuple(adapt(t) for t in item)
        if enabled and item.idname in NATIVE:
            kind=NATIVE[item.idname]
            return item._replace(widget='WL_GGT_native_transform',widget_properties=None,
                keymap=None if kind=='TRANSFORM' else ['3D View Tool: wavelength '+kind],operator='wavelength.transform_route',draw_settings=draw_settings)
        return item
    for item in _original_tools(cls,context,mode):yield adapt(item)

# docs:end transform-routing

def sync():
    """Refresh tool runtime bindings on workspace/profile/context transitions."""
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type!='VIEW_3D':continue
            region=next((r for r in area.regions if r.type=='WINDOW'),None)
            if region is None:continue
            with bpy.context.temp_override(window=window,area=area,region=region):
                ctx=bpy.context
                if ctx.mode!='OBJECT':continue
                tool=ctx.workspace.tools.from_space_view3d_mode('OBJECT',create=False)
                if not tool:continue
                name=LEGACY.get(tool.idname,tool.idname)
                if name not in NATIVE:continue
                expected=VIEW3D_PT_tools_active._tool_get_by_id(ctx,name)[0]
                if expected is None:continue
                wanted=expected.widget or ''
                key=(ctx.workspace.as_pointer(),ctx.mode)
                state=(name,wanted,available(ctx))
                if tool.idname!=name or _states.get(key)!=state:
                    bpy.ops.wm.tool_set_by_id(name=name);_states[key]=state
    return .1

def register():
    global _original_tools
    for cls in (WL_OT_profile_grid_context,WL_OT_transform_route,WL_GGT_native_transform):bpy.utils.register_class(cls)
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    _original_tools=VIEW3D_PT_tools_active.tools_from_context.__func__
    VIEW3D_PT_tools_active.tools_from_context=classmethod(tools_from_context)
    kc=bpy.context.window_manager.keyconfigs.addon
    if kc:
        km=kc.keymaps.new(name='Object Mode',space_type='EMPTY')
        for key,kind in [('G','MOVE'),('R','ROTATE'),('S','SCALE')]:
            item=km.keymap_items.new('wavelength.transform_route',key,'PRESS');item.properties.kind=kind;_keys.append((km,item))
        for kind in NATIVE.values():
            km=kc.keymaps.new(name='3D View Tool: wavelength '+kind,space_type='VIEW_3D',region_type='WINDOW')
            if kind!='TRANSFORM':
                item=km.keymap_items.new('wavelength.transform_route','LEFTMOUSE','CLICK_DRAG');item.properties.kind=kind;_keys.append((km,item))
    if not bpy.app.timers.is_registered(sync):bpy.app.timers.register(sync,first_interval=.1,persistent=True)

def unregister():
    global _original_tools
    if bpy.app.timers.is_registered(sync):bpy.app.timers.unregister(sync)
    from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active
    if _original_tools:
        VIEW3D_PT_tools_active.tools_from_context=classmethod(_original_tools);_original_tools=None
    # Runtime tool bindings are stored on the workspace, independently of Python
    # definitions. Restore them before unregistering their custom gizmo group.
    for ws in bpy.data.workspaces:
        tool=ws.tools.from_space_view3d_mode('OBJECT',create=False)
        if not tool or tool.idname not in NATIVE:continue
        item=VIEW3D_PT_tools_active._tool_get_by_id(bpy.context,tool.idname)[0]
        if item is None:continue
        fallback=VIEW3D_PT_tools_active._tool_get_by_id(bpy.context,tool.idname_fallback)[0] if tool.idname_fallback else None
        tool.setup(idname=item.idname,keymap=item.keymap[0] if item.keymap else '',
            gizmo_group=item.widget or '',operator=item.operator or '',data_block=item.data_block or '',brush_type=item.brush_type or 'ANY',
            cursor=item.cursor or 'DEFAULT',index=tool.index,options=item.options or set(),
            idname_fallback=tool.idname_fallback,
            keymap_fallback=(fallback.keymap[0]+' (fallback)') if fallback and fallback.keymap else '')
    for km,item in _keys:km.keymap_items.remove(item)
    _keys.clear();_states.clear()
    for cls in (WL_GGT_native_transform,WL_OT_transform_route,WL_OT_profile_grid_context):bpy.utils.unregister_class(cls)
