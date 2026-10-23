"""Scene context transitions, reversible helper visibility and clean render hooks."""
import json,uuid
import bpy
from bpy.props import BoolProperty,EnumProperty,PointerProperty
from bpy.app.handlers import persistent
from . import context_policy as policy

_dirty=set();_renders=set();_owners={};_busy=False
VIEW='_wl_context_view_restore';RENDER='_wl_context_render_restore'

def rendering(scene=None):return bool(_renders) if scene is None else scene.as_pointer() in _renders

def layer_key(scene,layer):
    if not scene.get('_wl_context_id'):scene['_wl_context_id']=uuid.uuid4().hex
    try:
        if not layer.get('_wl_context_id'):layer['_wl_context_id']=uuid.uuid4().hex
        return scene['_wl_context_id']+':'+layer['_wl_context_id']
    except TypeError:return scene['_wl_context_id']+':'+layer.name

def viewport_hidden(scene):
    state=getattr(scene,'wavelength_context',None)
    return bool(state and (state.mode=='CLEAN' or not state.helpers))

def apply_scene(scene):
    global _busy
    if _busy or not hasattr(scene,'wavelength_context'):return
    _busy=True
    try:
        clean=viewport_hidden(scene);engine=getattr(getattr(scene,'wavelength',None),'engine','blender')
        for obj in scene.objects:
            saved=json.loads(obj.get(VIEW,'{}'))
            helper=clean and policy.role(obj,engine) in {'HELPER','LIBRARY'}
            if not helper and not saved:continue
            for layer in scene.view_layers:
                if obj.name not in layer.objects:continue
                key=layer_key(scene,layer)
                if helper:
                    if key not in saved:saved[key]=bool(obj.hide_get(view_layer=layer))
                    if not obj.hide_get(view_layer=layer):obj.hide_set(True,view_layer=layer)
                elif key in saved:
                    obj.hide_set(saved.pop(key),view_layer=layer)
            if saved:obj[VIEW]=json.dumps(saved)
            elif VIEW in obj:del obj[VIEW]
    finally:_busy=False

def changed(self,context):
    owner=getattr(self,'id_data',None)
    scenes=[owner] if isinstance(owner,bpy.types.Scene) else [s for s in bpy.data.scenes if owner and owner.name in s.objects]
    for scene in scenes:
        _dirty.add(scene.as_pointer());apply_scene(scene)
    try:
        from . import grid
        grid.sync_native()
    except (RuntimeError,AttributeError):pass
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:area.tag_redraw()

class WLContext(bpy.types.PropertyGroup):
    mode:EnumProperty(name='Context',items=[('EDIT','Level Editing','Enable configured Wavelength editing capabilities'),('CLEAN','Clean Preview','Hide editor helpers and suspend editing/preparation; preserve visible game content'),('SUSPENDED','Suspended','Suspend Wavelength tools and preparation without changing authored content')],default='EDIT',update=changed)
    editing:BoolProperty(name='Editing Tools',default=True,update=changed)
    overlays:BoolProperty(name='Wavelength Overlays',default=True,update=changed)
    preparation:BoolProperty(name='Asset Preparation',default=True,update=changed)
    helpers:BoolProperty(name='Show Editor Helpers',default=True,update=changed)
    render_helpers:BoolProperty(name='Include Helpers in Renders',default=False,description='Diagnostic rendering only; Clean Preview always excludes helpers')

class WL_OT_context(bpy.types.Operator):
    bl_idname='wavelength.set_context';bl_label='Set Wavelength Context';bl_options={'REGISTER','UNDO'}
    mode:EnumProperty(items=[('EDIT','Level Editing',''),('CLEAN','Clean Preview',''),('SUSPENDED','Suspended','')],default='EDIT')
    def execute(self,context):context.scene.wavelength_context.mode=self.mode;return {'FINISHED'}

class WL_PT_context(bpy.types.Panel):
    bl_label='Wavelength Context';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='scene';bl_order=-30
    @classmethod
    def poll(cls,context):return hasattr(context.scene,'wavelength_context')
    def draw(self,context):
        layout=self.layout;state=context.scene.wavelength_context
        layout.prop(state,'mode');layout.prop(state,'helpers')
        row=layout.row(align=True);row.prop(state,'editing');row.prop(state,'overlays');layout.prop(state,'preparation')
        layout.prop(state,'render_helpers')
        layout.label(text='Game geometry and models retain their visibility')
        layout.label(text='Render policy applies in every workspace')

class WL_PT_object_context(bpy.types.Panel):
    bl_label='Wavelength Visibility Role';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return context.object is not None and hasattr(context.scene,'wavelength_context')
    def draw(self,context):
        self.layout.prop(context.object,'wavelength_context_role')
        engine=getattr(getattr(context.scene,'wavelength',None),'engine','blender')
        self.layout.label(text='Resolved: '+policy.role(context.object,engine).title())

@persistent
def depsgraph(scene,*_):
    if not _busy and viewport_hidden(scene):_dirty.add(scene.as_pointer())

def tick():
    for scene in bpy.data.scenes:
        if scene.as_pointer() in _dirty:
            _dirty.discard(scene.as_pointer());apply_scene(scene)
    return .25

@persistent
def render_begin(scene,*_):
    _renders.add(scene.as_pointer())
    from . import profile_setup,external_library
    profile_setup.stop();external_library.stop()
    state=getattr(scene,'wavelength_context',None)
    engine=getattr(getattr(scene,'wavelength',None),'engine','blender')
    for obj in scene.objects:
        role=policy.role(obj,engine)
        hide=role=='LIBRARY' or (role=='HELPER' and (not state or state.mode=='CLEAN' or not state.render_helpers))
        if not hide:continue
        if RENDER not in obj:obj[RENDER]=bool(obj.hide_render)
        _owners.setdefault(obj,set()).add(scene.as_pointer());obj.hide_render=True

@persistent
def render_end(scene,*_):
    _renders.discard(scene.as_pointer())
    for obj,owners in list(_owners.items()):
        owners.discard(scene.as_pointer())
        if owners:continue
        try:
            if RENDER in obj:obj.hide_render=bool(obj[RENDER]);del obj[RENDER]
        except ReferenceError:pass
        _owners.pop(obj,None)

@persistent
def loaded(*_):
    _renders.clear();_owners.clear();_dirty.clear()
    for obj in bpy.data.objects:
        if RENDER in obj:obj.hide_render=bool(obj[RENDER]);del obj[RENDER]
    for scene in bpy.data.scenes:_dirty.add(scene.as_pointer());apply_scene(scene)

@persistent
def undo_redo(*_):
    for scene in bpy.data.scenes:_dirty.add(scene.as_pointer())

HANDLERS=(('depsgraph_update_post',depsgraph),('render_init',render_begin),('render_pre',render_begin),('render_complete',render_end),('render_cancel',render_end),('load_post',loaded),('undo_post',undo_redo),('redo_post',undo_redo))
CLASSES=(WLContext,WL_OT_context,WL_PT_context,WL_PT_object_context)

def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.wavelength_context=PointerProperty(type=WLContext)
    bpy.types.Object.wavelength_context_role=EnumProperty(name='Role',items=[('AUTO','Automatic','Resolve game content versus editor helpers from Wavelength metadata'),('CONTENT','Visible Content','Preserve as visible scene content'),('HELPER','Editor Helper','Exclude from clean preview and normal renders')],default='AUTO',update=changed)
    for name,callback in HANDLERS:
        handlers=getattr(bpy.app.handlers,name)
        if callback not in handlers:handlers.append(callback)
    bpy.app.timers.register(tick,first_interval=.25,persistent=True)
    # Add-on enable runs with restricted bpy.data; restore after registration.
    bpy.app.timers.register(loaded,first_interval=.1)

def unregister():
    for name,callback in HANDLERS:
        handlers=getattr(bpy.app.handlers,name)
        if callback in handlers:handlers.remove(callback)
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if bpy.app.timers.is_registered(loaded):bpy.app.timers.unregister(loaded)
    for scene in bpy.data.scenes:render_end(scene)
    # Restore only visibility owned by this context policy.
    for scene in bpy.data.scenes:
        scene.wavelength_context.mode='EDIT';scene.wavelength_context.helpers=True;apply_scene(scene)
    del bpy.types.Object.wavelength_context_role;del bpy.types.Scene.wavelength_context
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
