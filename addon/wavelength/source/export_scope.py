"""One inclusion policy for native Outliner flags, engine trees and exporters."""
import bpy
from bpy.app.handlers import persistent


def render_disabled(obj):
    # Clean-render policy temporarily hides editor helpers. Its saved user flag
    # remains authoritative for export, including builds started from handlers.
    return bool(obj.get('_wl_context_render_restore',obj.hide_render))


class Scope:
    """Resolve enabled collection paths once per export or tree redraw."""
    def __init__(self,scene,view_layer=None):
        self.scene=scene
        if not scene.get('_wl_export_inclusion_policy'):scene['_wl_export_inclusion_policy']=True
        if view_layer is None:
            view_layer=bpy.context.view_layer if bpy.context.scene==scene else scene.view_layers[0]
        self.layer=view_layer;self.objects=set();self.paths={}
        def visit(layer,path,blocked=False):
            collection=layer.collection
            path=(*path,layer)
            blocked=blocked or layer.exclude or collection.hide_render
            for obj in collection.objects:
                self.paths.setdefault(obj,[]).append(path)
                if not blocked:self.objects.add(obj)
            for child in layer.children:visit(child,path,blocked)
        visit(view_layer.layer_collection,())
    def includes(self,obj):
        if obj not in self.objects or render_disabled(obj):return False
        definition=obj.get('wl_custom_model')
        return definition is None or self.includes_model_sources(definition)

    def includes_model_sources(self,definition):
        state=definition.wavelength_model
        collision=state.collision if state.collision_mode=='OBJECT' else None
        return any(source.type=='MESH' and not source.get('wl_model_collision_only') and
                   (source!=collision or source.get('wl_custom_model_owner')==state.origin) and
                   source in self.objects and not render_disabled(source) for source in definition.objects)

    def enable_path(self,obj):
        if obj in self.objects:return
        paths=self.paths.get(obj,())
        if paths:
            # Restore one membership path; linked duplicates need only one.
            for layer in min(paths,key=len):
                layer.exclude=False;layer.collection.hide_render=False
            self.objects.add(obj)


def set_enabled(scope,obj,enabled):
    if enabled:
        scope.enable_path(obj)
        definition=obj.get('wl_custom_model')
        if definition:
            collision=definition.wavelength_model.collision if definition.wavelength_model.collision_mode=='OBJECT' else None
            sources=[source for source in definition.objects if source.type=='MESH' and (source!=collision or source.get('wl_custom_model_owner')==definition.wavelength_model.origin)]
            if sources and not any(scope.includes(source) for source in sources):
                for source in sources:set_enabled(scope,source,True)
    saved='_wl_context_render_restore'
    if saved in obj:obj[saved]=not enabled
    else:obj.hide_render=not enabled


def state(scope,objects):
    values=[scope.includes(obj) for obj in objects]
    return 'EMPTY' if not values else 'ON' if all(values) else 'MIXED' if any(values) else 'OFF'


class WL_OT_export_inclusion(bpy.types.Operator):
    bl_idname='wavelength.export_inclusion';bl_label='Include in Export and Compilation'
    bl_description='Toggle inclusion in game export, compilation and rendering; synchronized with native Outliner restrictions'
    bl_options={'REGISTER','UNDO'}
    object_name:bpy.props.StringProperty()
    category:bpy.props.StringProperty()
    def execute(self,context):
        from . import system_tree
        scope=Scope(context.scene,context.view_layer)
        if self.category:objects=system_tree.groups(context.scene).get(self.category,[])
        else:
            obj=context.scene.objects.get(self.object_name);objects=[obj] if obj else []
        enabled=state(scope,objects)!='ON'
        for obj in objects:set_enabled(scope,obj,enabled)
        system_tree.invalidate_groups()
        for window in context.window_manager.windows:
            for area in window.screen.areas:area.tag_redraw()
        return {'FINISHED'}


def draw(layout,scope,objects,*,category='',object_name=''):
    status=state(scope,objects)
    op=layout.operator('wavelength.export_inclusion',text='',emboss=False,
        icon='CHECKBOX_HLT' if status=='ON' else 'REMOVE' if status=='MIXED' else 'CHECKBOX_DEHLT')
    op.category=category;op.object_name=object_name


@persistent
def enable_policy(*_):
    for scene in bpy.data.scenes:
        if not scene.get('_wl_export_inclusion_policy'):scene['_wl_export_inclusion_policy']=True
    return None


@persistent
def policy_update(scene,*_):
    if not scene.get('_wl_export_inclusion_policy'):scene['_wl_export_inclusion_policy']=True


def register():
    bpy.utils.register_class(WL_OT_export_inclusion)
    from . import regular_exports
    regular_exports.install()
    bpy.app.handlers.load_post.append(enable_policy)
    bpy.app.handlers.depsgraph_update_post.append(policy_update)
    bpy.app.timers.register(enable_policy,first_interval=.01)

def unregister():
    from . import regular_exports
    regular_exports.uninstall()
    if policy_update in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(policy_update)
    if enable_policy in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(enable_policy)
    if bpy.app.timers.is_registered(enable_policy):bpy.app.timers.unregister(enable_policy)
    bpy.utils.unregister_class(WL_OT_export_inclusion)
