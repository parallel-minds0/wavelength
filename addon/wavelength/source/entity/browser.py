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
    # Keep this independent from ui.py to avoid an import cycle during register.
    primary=[]
    if settings.fgd_path:
        try:
            from . import fgd
            primary=fgd.properties(fgd.load(bpy.path.abspath(settings.fgd_path)), classname)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            primary=[]
    if getattr(settings, 'engine', '') in {'goldsrc','goldsrc_linux','goldsrc_linux_steam'}:
        try:
            from . import goldsrc as goldsrc_entities
            primary=goldsrc_entities.merge_properties(classname, primary)
        except Exception:
            pass
    pairs=[['classname', classname]]
    seen={'classname'}
    for prop in primary:
        key=str(prop.get('key','')).strip()
        value=str(prop.get('default','')).strip()
        if key and key not in seen and value:
            pairs.append([key,value]); seen.add(key)
    return pairs


def _asset_collection(scene):
    collection=bpy.data.collections.get(_ASSET_COLLECTION)
    if collection is None:
        collection=bpy.data.collections.new(_ASSET_COLLECTION)
        scene.collection.children.link(collection)
    collection.hide_viewport=True
    collection.hide_render=True
    return collection


def rebuild(context):
    """Rebuild Current File entity assets for the active Wavelength profile."""
    s=context.scene.wavelength
    if s.engine=='blender':
        raise ValueError('Choose Quake or Half-Life / GoldSrc before opening the Entity Browser')
    collection=_asset_collection(context.scene)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    count=0
    for classname, label, description in _catalog(context):
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

        # TODO: attach deterministic cached PNG/SVG previews here.
        # Runtime model-preview generation was intentionally removed: Blender does
        # not reliably render our temporary collection-instance templates.
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
            # Asset marking exists in supported Blender versions; keep templates
            # harmless if Blender changes this API.
            continue
        count+=1
    s.status=f'Entity Browser: {count} {s.engine} entities published as Current File assets'
    return count


def _is_template_source(obj):
    return any(c.name==_ASSET_COLLECTION for c in obj.users_collection)


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
    if _BUSY or not hasattr(scene,'wavelength'):
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


def _configure_asset_area(area):
    """Configure one FILE_BROWSER area as a Wavelength-only Asset Browser host."""
    if not area:
        return
    area.type='FILE_BROWSER'
    area.ui_type='ASSETS'
    try:
        area['wl_asset_browser']=True
    except Exception:
        pass
    try:
        space=area.spaces.active
        params=getattr(space,'params',None)
        if params:
            # Wavelength uses Current File assets so drag/drop remains native, but this
            # area is a distinct Asset Browser instance.  Prefer a dedicated catalog
            # filter where Blender exposes it; fall back to a Wavelength search scope.
            for attr in ('asset_library_reference','asset_library_ref'):
                if hasattr(params,attr):
                    try:setattr(params,attr,'LOCAL')
                    except Exception:pass
            if hasattr(params,'catalog_id'):
                try: params.catalog_id=_CATALOG_ID
                except Exception: pass
            # Do not mutate any other Asset Browser area; this filter belongs only here.
            if hasattr(params,'filter_search'):
                try: params.filter_search='Wavelength'
                except Exception: pass
    except Exception:
        pass
    area.tag_redraw()


def _is_wavelength_asset_area(area):
    if area.type!='FILE_BROWSER':
        return False
    try:
        return area.ui_type=='ASSETS' and bool(area.get('wl_asset_browser', False))
    except Exception:
        return False


def _window_for_context(context):
    if getattr(context,'window',None):
        return context.window
    wm=getattr(context,'window_manager',None) or bpy.context.window_manager
    return wm.windows[0] if wm and wm.windows else None


def _find_browser(screen):
    return next((a for a in screen.areas if _is_wavelength_asset_area(a)),None)


def ensure_browser_layout(context):
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
        _configure_asset_area(existing)
        return window,screen,existing

    viewports=[a for a in screen.areas if a.type=='VIEW_3D']
    if not viewports:
        raise ValueError('No 3D Viewport is available to split')
    viewport=max(viewports,key=lambda a:a.width*a.height)
    before={a.as_pointer() for a in screen.areas}
    with bpy.context.temp_override(window=window,screen=screen,area=viewport):
        # Split the viewport itself.  Blender keeps the Timeline as a separate area.
        bpy.ops.screen.area_split(direction='HORIZONTAL',factor=0.76)
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
    _configure_asset_area(browser)
    try: window.workspace[_LAYOUT_MARKER]=True
    except Exception: pass
    return window,screen,browser


class WL_OT_entity_browser_refresh(bpy.types.Operator):
    bl_idname='wavelength.entity_browser_refresh'
    bl_label='Refresh Wavelength Asset Browser'
    bl_description='Rebuild Wavelength assets from the active game profile/FGD'
    def execute(self,context):
        try:
            s=context.scene.wavelength
            if s.engine=='blender':
                raise ValueError('Choose Quake or Half-Life / GoldSrc first')
            count=rebuild(context)
            area=_find_browser(context.screen) if getattr(context,'screen',None) else None
            if area: _configure_asset_area(area)
            self.report({'INFO'},f'Rebuilt {count} Wavelength assets')
            return {'FINISHED'}
        except Exception as exc:
            context.scene.wavelength.status=str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class WL_OT_entity_browser(bpy.types.Operator):
    bl_idname='wavelength.entity_browser'
    bl_label='Wavelength Asset Browser'
    bl_description='Open the dedicated Wavelength Asset Browser below the 3D Viewport'
    def execute(self,context):
        try:
            s=context.scene.wavelength
            # Do this before touching the layout.  Neutral Blender mode has no entity
            # catalog to publish and should leave the user's workspace unchanged.
            if s.engine=='blender':
                raise ValueError('Choose Quake or Half-Life / GoldSrc before opening the Wavelength Asset Browser')
            window,screen,browser=ensure_browser_layout(context)
            # Rebuild only after the active game is known, then re-apply this area's
            # Wavelength-only filter.  Other Asset Browser instances are untouched.
            with bpy.context.temp_override(window=window,screen=screen,area=browser,scene=context.scene):
                count=rebuild(bpy.context)
                _configure_asset_area(browser)
            s.status=f'Wavelength Asset Browser: {count} {s.engine} entities'
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
