"""Engine-category inspector in the right-hand workspace stack.

Uses a dedicated Properties space, with native panels suppressed only in that
space. The regular Properties editor and artist-owned Collections stay intact.
"""
import bpy
from . import system_tree

_areas=set()
_polls=[]


def is_tree(context):
    area=getattr(context,'area',None)
    if not area or area.type!='PROPERTIES':return False
    if area.as_pointer() in _areas:return True
    # These per-space flags are saved in .blend files, unlike runtime pointers.
    space=area.spaces.active
    if (context.workspace and context.workspace.get('wl_workspace') and
        hasattr(space,'show_properties_scene') and space.show_properties_scene and
        all(not getattr(space,p.identifier) for p in space.bl_rna.properties
            if p.identifier.startswith('show_properties_') and p.identifier!='show_properties_scene')):
        _areas.add(area.as_pointer());return True
    return False


def configure(area):
    area.type='PROPERTIES';_areas.add(area.as_pointer())
    space=area.spaces.active
    for prop in space.bl_rna.properties:
        if prop.identifier.startswith('show_properties_'):
            setattr(space,prop.identifier,prop.identifier=='show_properties_scene')
    space.context='SCENE';space.show_region_header=False


def ensure(context):
    """Reuse an extra Outliner, otherwise take the top of Properties."""
    if bpy.app.background or not context.window:return
    screen=context.screen
    for area in screen.areas:
        with context.temp_override(area=area):
            if is_tree(context):return
    outliners=[a for a in screen.areas if a.type=='OUTLINER']
    properties=[a for a in screen.areas if a.type=='PROPERTIES']
    if not outliners or not properties:return
    inspector=max(properties,key=lambda a:a.x)
    stack=[a for a in outliners if abs(a.x-inspector.x)<8 and a.y>=inspector.y+inspector.height-8]
    if not stack:return
    if len(stack)>1:
        configure(min(stack,key=lambda a:a.y));return
    upper=inspector
    if upper.height<360:return
    before={a.as_pointer() for a in screen.areas}
    with context.temp_override(area=upper):
        bpy.ops.screen.area_split(direction='HORIZONTAL',factor=.66)
    new=next((a for a in screen.areas if a.as_pointer() not in before),None)
    if new:
        def finish():
            try:
                middle=max((upper,new),key=lambda a:a.y)
                configure(middle)
            except ReferenceError:pass
        bpy.app.timers.register(finish,first_interval=.05)


class WL_OT_system_tree_expand(bpy.types.Operator):
    bl_idname='wavelength.system_tree_expand';bl_label='Expand Engine Category'
    category:bpy.props.StringProperty()
    def execute(self,context):
        key='wl_tree_open_'+self.category
        context.scene[key]=not context.scene.get(key,False)
        return {'FINISHED'}


class WL_PT_engine_tree(bpy.types.Panel):
    bl_label='System Tree';bl_space_type='PROPERTIES';bl_region_type='WINDOW'
    bl_order=-100
    bl_options={'HEADER_LAYOUT_EXPAND'}
    @classmethod
    def poll(cls,context):return hasattr(context.scene,'wavelength') and is_tree(context)
    def draw(self,context):
        layout=self.layout
        from . import render_support
        if context.scene.get('wl_importing') or render_support.progress(context.scene):
            from . import map_import
            map_import.draw_progress(layout,context.scene);return
        if context.scene.wavelength.engine=='blender':
            layout.label(text='Choose an engine profile',icon='INFO');return
        groups=system_tree.groups(context.scene)
        for key,label,icon in system_tree.CATEGORIES:
            objects=groups[key];row=layout.row(align=True)
            expanded=context.scene.get('wl_tree_open_'+key,False)
            op=row.operator('wavelength.system_tree_expand',text='',icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT',emboss=False);op.category=key
            row.label(text=f'{label} ({len(objects)})',icon=icon)
            hidden=system_tree.category_explicitly_hidden(context.scene,key)
            state=system_tree.tree_visibility(context.scene,key,context.view_layer,objects)
            op=row.operator('wavelength.system_category_visibility',text='',icon='HIDE_ON' if hidden else 'REMOVE' if state=='MIXED' else 'HIDE_OFF',emboss=False);op.category=key
            if expanded:
                for obj in objects:
                    row=layout.row(align=True);row.separator(factor=1.5)
                    op=row.operator('wavelength.system_select',text=obj.name,icon='OBJECT_DATA',emboss=False);op.object_name=obj.name
                    op=row.operator('wavelength.system_visibility',text='',icon='HIDE_ON' if system_tree.object_hidden(obj,context.view_layer) else 'HIDE_OFF',emboss=False);op.object_name=obj.name
        if bpy.ops.wavelength.reload_map_assets.poll():
            layout.separator()
            layout.operator('wavelength.reload_map_assets',text='Reload Asset Previews',icon='FILE_REFRESH')


def _ordered_panels():
    panels=[]
    for name in dir(bpy.types):
        cls=getattr(bpy.types,name)
        if (isinstance(cls,type) and issubclass(cls,bpy.types.Panel) and cls!=WL_PT_engine_tree
            and getattr(cls,'bl_space_type','')=='PROPERTIES' and getattr(cls,'bl_context','')=='scene'):
            panels.append(cls)
    by_name={c.__name__:c for c in panels}
    def depth(c):
        parent=by_name.get(getattr(c,'bl_parent_id',''))
        return 1+depth(parent) if parent else 0
    return sorted(panels,key=depth)


def register():
    for cls in (WL_OT_system_tree_expand,WL_PT_engine_tree):bpy.utils.register_class(cls)
    def scoped_poll(original):
        def poll(cls,context):
            return not is_tree(context) and (original(context) if original else True)
        return classmethod(poll)
    panels=_ordered_panels()
    for cls in reversed(panels):bpy.utils.unregister_class(cls)
    for cls in panels:
        old=cls.__dict__.get('poll');bound=getattr(cls,'poll',None)
        _polls.append((cls,old));cls.poll=scoped_poll(bound)
        bpy.utils.register_class(cls)


def unregister():
    for cls,old in reversed(_polls):bpy.utils.unregister_class(cls)
    for cls,old in _polls:
        if old is None:delattr(cls,'poll')
        else:cls.poll=old
        bpy.utils.register_class(cls)
    _polls.clear();_areas.clear()
    for cls in (WL_PT_engine_tree,WL_OT_system_tree_expand):bpy.utils.unregister_class(cls)
