"""Wavelength Asset Browser backed by Blender's native Asset Browser.

Python add-ons cannot register a new Blender Space type.  We therefore publish
active-profile entity templates as Current File assets.  Blender supplies the
thumbnail/name tile UI and native drag from the Asset Browser into a 3D View.
A depsgraph finalizer turns dropped templates into normal Wavelength entities.
"""
import json
import bpy

_ASSET_COLLECTION = '_WL_ENTITY_BROWSER_ASSETS'
_TEMPLATE_KEY = 'wl_entity_browser_template'
_BUSY = False


def _catalog(context):
    from . import catalog as entities
    s=context.scene.wavelength
    return list(entities.items(s, context))


def _defaults(settings, classname):
    from ..ui import _entity_creation_defaults
    return _entity_creation_defaults(settings, classname)


def _asset_collection(scene):
    name=_ASSET_COLLECTION+'_'+scene.wavelength.engine
    collection=bpy.data.collections.get(name)
    if collection is None:
        collection=bpy.data.collections.new(name)
        scene.collection.children.link(collection)
    collection.hide_viewport=True
    collection.hide_render=True
    return collection


def rebuild_for_scene(scn, context=None, quiet=False):
    """Rebuild Current File entity assets for the active Wavelength profile."""
    s=scn.wavelength
    if s.engine=='blender':
        raise ValueError('Choose Quake or Half-Life / GoldSrc before opening the Entity Browser')
    for other_col in list(bpy.data.collections):
        if other_col.name.startswith(_ASSET_COLLECTION+'_') and other_col.name!=_ASSET_COLLECTION+'_'+s.engine:
            for obj in list(other_col.objects):
                if obj.asset_data is not None:
                    try:obj.asset_clear()
                    except Exception:pass
    collection=_asset_collection(scn)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    from . import catalog as entities
    count=0
    for classname, label, description in list(entities.items(s, context)):
        obj=bpy.data.objects.new(classname, None)
        collection.objects.link(obj)
        obj.empty_display_type='PLAIN_AXES'
        obj.empty_display_size=0.4
        obj[_TEMPLATE_KEY]=classname
        obj['wl_role']='ENTITY'
        obj['wl_exclude']=True
        pairs=_defaults(s, classname)
        obj['wl_pairs']=json.dumps(pairs)
        obj['wl_entity_browser_profile']=s.engine

        try:
            obj.asset_mark()
            if obj.asset_data:
                obj.asset_data.description=description or f'Wavelength {classname}'
                obj.asset_data.author='Wavelength'
                try: obj.asset_data.catalog_id=_CATALOG_ID
                except Exception: pass
                try: obj.asset_data.tags.new('Wavelength')
                except Exception: pass
        except Exception:
            continue
        from ..asset_browser import preview,metadata
        from ..asset_index import record
        metadata(obj,record(s.engine,classname,'ENTITY',source=s.fgd_path or 'Built-in registry'))
        preview(obj)
        count+=1
    if not quiet:
        s.status=f'Entity Browser: {count} {s.engine} entities published as Current File assets'
    return count


def rebuild(context):
    """Rebuild Current File entity assets for the active Wavelength profile."""
    scn=getattr(context,'scene',None) or bpy.context.scene
    return rebuild_for_scene(scn, context=context, quiet=False)


def _is_template_source(obj):
    return any(c.name.startswith(_ASSET_COLLECTION) for c in obj.users_collection)


def _finalize_drop(scene, obj):
    from .. import scene as wl_scene, profiles
    from . import models as entity_models
    classname=str(obj.get(_TEMPLATE_KEY,'')).strip()
    if not classname or _is_template_source(obj):
        return False
    s=scene.wavelength
    # The browser is profile-specific.  Never silently turn an old profile's
    # template into a different game's entity.
    if obj.get('wl_entity_browser_profile') != s.engine:
        return False
    obj['wl_role']='ENTITY'
    obj['wl_id']=wl_scene.uid()
    obj['wl_pairs']=json.dumps(_defaults(s, classname))
    obj['wl_exclude']=False
    obj.empty_display_type='ARROWS'
    obj.empty_display_size=profiles.engine_to_world(s,16)
    obj['wl_unit_meters']=profiles.unit_meters(s)
    obj.name=classname
    del obj[_TEMPLATE_KEY]
    if 'wl_entity_browser_profile' in obj:
        del obj['wl_entity_browser_profile']
    if profiles.is_goldsrc(s.engine):
        try: entity_models.attach_reference(obj, json.loads(obj['wl_pairs']))
        except Exception: pass
    s.status=f'Placed {classname} from Entity Browser'
    return True


def _depsgraph(scene, depsgraph):
    global _BUSY
    from ..workspace import active
    if _BUSY or not active() or not hasattr(scene,'wavelength'):
        return
    _BUSY=True
    try:
        for obj in list(scene.objects):
            if obj.get(_TEMPLATE_KEY) and not _is_template_source(obj):
                _finalize_drop(scene,obj)
    finally:
        _BUSY=False


_LAYOUT_MARKER = 'wl_asset_browser_layout_v2'
_CATALOG_ID = '7d3c0fd7-53ef-4b20-9c3b-b6e2f8a7a119'
_OTHER_ID_FILTERS = (
    'filter_action',
    'filter_annotations',
    'filter_brush',
    'filter_group',
    'filter_node_tree',
    'filter_palettes',
    'filter_scene',
    'filter_world',
)


def _apply_section_id_filter(params, section):
    """Strictly separate Textures (Material assets) from Entities (Object assets)."""
    id_filter=getattr(params,'filter_asset_id',None)
    if id_filter is None:
        return
    is_textures=(section!='ENTITIES')
    for attr in _OTHER_ID_FILTERS:
        if hasattr(id_filter,attr):
            try:setattr(id_filter,attr,False)
            except Exception:pass
    if hasattr(id_filter,'filter_material'):
        try:id_filter.filter_material=bool(is_textures)
        except Exception:pass
    if hasattr(id_filter,'filter_object'):
        try:id_filter.filter_object=bool(not is_textures)
        except Exception:pass


def _configure_asset_area(area, section=None):
    """Configure one FILE_BROWSER area as a Wavelength Asset Browser host."""
    if not area:
        return
    if section is None:
        scn=getattr(bpy.context,'scene',None)
        if scn and hasattr(scn,'wavelength'):
            section=getattr(scn.wavelength,'asset_browser_section','TEXTURES')
        else:
            section=area.get('wl_asset_section','TEXTURES')
    area.type='FILE_BROWSER'
    area.ui_type='ASSETS'
    try:
        area['wl_asset_browser']=True
        area['wl_asset_section']=section
    except Exception:
        pass
    try:
        space=area.spaces.active
        params=getattr(space,'params',None)
        if params:
            for attr in ('asset_library_reference','asset_library_ref'):
                if hasattr(params,attr):
                    try:setattr(params,attr,'LOCAL')
                    except Exception:pass
            if hasattr(params,'catalog_id'):
                try: params.catalog_id='00000000-0000-0000-0000-000000000000'
                except Exception: pass
            _apply_section_id_filter(params, section)
            if hasattr(params,'filter_search') and area.get('_wl_init_search') is None:
                try:
                    params.filter_search=''
                    area['_wl_init_search']=True
                except Exception:
                    pass
    except Exception:
        pass
    area.tag_redraw()


def apply_section_to_open_browsers(context, section):
    """Switch all open Wavelength Asset Browser areas to the selected section."""
    from .. import asset_browser
    asset_browser.schedule_profile_sync(context)
    wm=getattr(context,'window_manager',None) or getattr(bpy.context,'window_manager',None)
    if not wm:
        return
    for window in wm.windows:
        if not window.screen:
            continue
        for area in window.screen.areas:
            if _is_wavelength_asset_area(area):
                _configure_asset_area(area, section=section)


def _is_wavelength_asset_area(area):
    return area.type=='FILE_BROWSER' and area.ui_type=='ASSETS'


def _window_for_context(context):
    if getattr(context,'window',None):
        return context.window
    wm=getattr(context,'window_manager',None) or bpy.context.window_manager
    return wm.windows[0] if wm and wm.windows else None


def _find_browser(screen):
    return next((a for a in screen.areas if _is_wavelength_asset_area(a)),None)


def ensure_browser_layout(context, section=None):
    """Create/reuse the Wavelength browser only on explicit user request.

    The largest VIEW_3D is split.  The lower slice becomes the browser, leaving the
    upper slice as VIEW_3D and the pre-existing Timeline directly below untouched.
    """
    if bpy.app.background:
        raise ValueError('Wavelength Asset Browser requires the Blender UI')
    window=_window_for_context(context)
    if not window:
        raise ValueError('No Blender window is available')
    screen=window.screen
    existing=_find_browser(screen)
    if existing:
        _configure_asset_area(existing, section=section)
        return window,screen,existing

    viewports=[a for a in screen.areas if a.type=='VIEW_3D']
    if not viewports:
        raise ValueError('No 3D Viewport is available to split')
    viewport=max(viewports,key=lambda a:a.width*a.height)
    before={a.as_pointer() for a in screen.areas}
    with bpy.context.temp_override(window=window,screen=screen,area=viewport):
        # Split the viewport itself.  Blender keeps the Timeline as a separate area.
        bpy.ops.screen.area_split(direction='HORIZONTAL',factor=0.24)
    created=[a for a in screen.areas if a.as_pointer() not in before]
    if not created:
        raise RuntimeError('Blender did not create the Asset Browser area')
    new_area=created[0]

    # After a split Blender may keep either half under the original area pointer.
    # Select the physically lower half as the browser, then explicitly restore the
    # upper half to VIEW_3D.  This guarantees Viewport -> Browser -> Timeline.
    pair=[viewport,new_area]
    browser=min(pair,key=lambda a:a.y)
    upper=max(pair,key=lambda a:a.y)
    if upper.type!='VIEW_3D':
        upper.type='VIEW_3D'
    # Area dimensions settle on the next UI cycle after splitting.
    def finish_layout():
        try:
            pair_now=[a for a in screen.areas if a.as_pointer() in {viewport.as_pointer(),new_area.as_pointer()}]
            if len(pair_now)==2:
                lower=min(pair_now,key=lambda a:a.y);upper=max(pair_now,key=lambda a:a.y)
                upper.type='VIEW_3D';upper.spaces.active.show_region_ui=True
                _configure_asset_area(lower, section=section)
        except ReferenceError:pass
        return None
    bpy.app.timers.register(finish_layout,first_interval=.05)
    try: window.workspace[_LAYOUT_MARKER]=True
    except Exception: pass
    return window,screen,browser


class WL_OT_entity_browser_refresh(bpy.types.Operator):
    bl_idname='wavelength.entity_browser_refresh'
    bl_label='Refresh Wavelength Asset Browser'
    bl_description='Rebuild Wavelength textures and entities from the active game profile'
    def execute(self,context):
        try:
            from .. import asset_browser
            s=context.scene.wavelength
            if s.engine=='blender':
                raise ValueError('Choose Quake or Half-Life / GoldSrc first')
            count=rebuild(context)
            asset_browser.schedule_profile_sync(context,settings=s,force=True)
            pub,total,_=asset_browser.sync_status(s)
            area=_find_browser(context.screen) if getattr(context,'screen',None) else None
            if area: _configure_asset_area(area, section=s.asset_browser_section)
            self.report({'INFO'},f'Synced {pub}/{total} textures and {count} entities')
            return {'FINISHED'}
        except Exception as exc:
            context.scene.wavelength.status=str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class WL_OT_entity_browser(bpy.types.Operator):
    bl_idname='wavelength.entity_browser'
    bl_label='Wavelength Asset Browser'
    bl_description='Open the dedicated Wavelength Asset Browser below the 3D Viewport'
    section:bpy.props.EnumProperty(
        name='Section',
        items=[
            ('','Current','Keep current section'),
            ('TEXTURES','Textures','Browse profile textures'),
            ('ENTITIES','Entities','Browse profile entities'),
        ],
        default='',
        options={'SKIP_SAVE'},
    )
    def execute(self,context):
        try:
            from .. import asset_browser
            s=context.scene.wavelength
            if s.engine=='blender':
                raise ValueError('Choose Quake or Half-Life / GoldSrc before opening the Wavelength Asset Browser')
            if self.section in {'TEXTURES','ENTITIES'}:
                s.asset_browser_section=self.section
            target_section=s.asset_browser_section
            window,screen,browser=ensure_browser_layout(context, section=target_section)
            with bpy.context.temp_override(window=window,screen=screen,area=browser,scene=context.scene):
                count=rebuild(bpy.context)
                asset_browser.schedule_profile_sync(bpy.context,settings=s)
                _configure_asset_area(browser, section=target_section)
            pub,total,loading=asset_browser.sync_status(s)
            if target_section=='TEXTURES':
                s.status=f'Wavelength Asset Browser (Textures): {pub}/{total} {s.engine} textures' + (' loading…' if loading else '')
            else:
                s.status=f'Wavelength Asset Browser (Entities): {count} {s.engine} entities'
            return {'FINISHED'}
        except Exception as exc:
            context.scene.wavelength.status=str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


_CLASSES=(WL_OT_entity_browser_refresh, WL_OT_entity_browser)

def register():
    for cls in _CLASSES:
        try:bpy.utils.register_class(cls)
        except RuntimeError:pass
    if _depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph)

def unregister():
    if _depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph)
    for cls in reversed(_CLASSES):
        try:bpy.utils.unregister_class(cls)
        except RuntimeError:pass

