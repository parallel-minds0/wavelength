"""Treat an entity and its editor representation as one selectable/movable unit."""
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector
from bpy.app.handlers import persistent

_keys=[]
_busy=False


def owner(obj):
    visual=False
    while obj:
        visual=visual or bool(obj.get('wl_model_reference') or obj.get('wl_entity_icon_reference'))
        if visual and obj.get('wl_role')=='ENTITY':return obj
        obj=obj.parent
    return None


def select(context, entity, extend=False):
    if not extend:
        for obj in context.selected_objects:obj.select_set(False)
    entity.select_set(True)
    context.view_layer.objects.active=entity


@persistent
def sync_selection(*_args):
    global _busy
    if _busy:return
    from .. import workspace
    context=bpy.context
    if context.mode!='OBJECT' or not workspace.active(context):return
    _busy=True
    try:
        active=context.view_layer.objects.active
        for obj in tuple(context.selected_objects):
            entity=owner(obj)
            if entity:
                obj.select_set(False);entity.select_set(True)
                if obj==active:context.view_layer.objects.active=entity
    finally:_busy=False


def hit(context, mouse):
    from . import icons
    candidates=[]
    for ref in icons.sprite_instances(context):
        point=view3d_utils.location_3d_to_region_2d(context.region,context.region_data,ref.matrix_world.translation)
        radius=icons.SPRITE_SIZE*.5*context.preferences.system.ui_scale
        if point is not None and max(abs(mouse[i]-point[i]) for i in (0,1))<=radius:
            candidates.append(((mouse-point).length_squared,ref.parent))
    if candidates:return min(candidates,key=lambda item:item[0])[1]
    origin=view3d_utils.region_2d_to_origin_3d(context.region,context.region_data,mouse)
    direction=view3d_utils.region_2d_to_vector_3d(context.region,context.region_data,mouse)
    found,location,_,_,obj,_=context.scene.ray_cast(context.evaluated_depsgraph_get(),origin,direction)
    from .. import native_source
    if native_source.enabled():
        entity=native_source.hit(context,origin,direction,(location-origin).length if found else float('inf'))
        if entity:return entity
    if found:return owner(obj.original)
    return None


class WL_OT_entity_visual_select(bpy.types.Operator):
    bl_idname='wavelength.entity_visual_select'
    bl_label='Select Entity Representation'
    bl_options={'INTERNAL'}

    @classmethod
    def poll(cls,context):
        from .. import workspace
        return (context.mode=='OBJECT' and context.area and context.area.type=='VIEW_3D' and
                context.region and context.region.type=='WINDOW' and workspace.active(context))

    def invoke(self,context,event):
        tool=context.workspace.tools.from_space_view3d_mode(context.mode,create=False)
        if tool and not (tool.idname.startswith('builtin.select') or tool.idname in {'builtin.move','builtin.transform'}):
            return {'PASS_THROUGH'}
        mouse=Vector((event.mouse_region_x,event.mouse_region_y))
        entity=hit(context,mouse)
        if entity is None:return {'PASS_THROUGH'}
        if event.shift and entity.select_get():
            entity.select_set(False);return {'FINISHED'}
        select(context,entity,event.shift)
        context.area.tag_redraw()
        self._mouse=mouse
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} or (event.type=='LEFTMOUSE' and event.value=='RELEASE'):
            return {'FINISHED'}
        if event.type=='MOUSEMOVE' and (Vector((event.mouse_region_x,event.mouse_region_y))-self._mouse).length>3:
            # Transform the owner, never the visual's local offset. Parenting
            # then carries every attached model/sprite along in either direction.
            from ..precision_move import WL_OT_precision_move
            if WL_OT_precision_move.poll(context):
                bpy.ops.wavelength.precision_move('INVOKE_DEFAULT',release_confirm=True)
            else:bpy.ops.transform.translate('INVOKE_DEFAULT',release_confirm=True)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(WL_OT_entity_visual_select)
    if sync_selection not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(sync_selection)
    config=bpy.context.window_manager.keyconfigs.addon
    if config:
        keymap=config.keymaps.new(name='3D View',space_type='VIEW_3D')
        item=keymap.keymap_items.new('wavelength.entity_visual_select','LEFTMOUSE','PRESS',shift=False)
        _keys.append((keymap,item))
        item=keymap.keymap_items.new('wavelength.entity_visual_select','LEFTMOUSE','PRESS',shift=True)
        _keys.append((keymap,item))


def unregister():
    for keymap,item in _keys:keymap.keymap_items.remove(item)
    _keys.clear()
    if sync_selection in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_selection)
    bpy.utils.unregister_class(WL_OT_entity_visual_select)
