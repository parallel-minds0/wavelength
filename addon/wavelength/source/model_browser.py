"""Contextual entity model choices in Blender's native Asset Browser."""
import json,time,hashlib
from collections import deque
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from . import profiles,source_assets,asset_index
from .entity import source_schema

CATALOG='a1e2f3c4-1111-4000-8000-000000000003'
_queue=deque();_key=None;_owner=None;_signature=None;_return_section='ENTITIES';_fields=[]
_total=0;_ready=0
_last_target=None
_query=None
_auto_section=False
_publish_limit=96
_representation_queue=deque()
_watched_models={}


def watch_model(scene,obj):
    """Observe only the active entity; never rescan the map on a UI timer."""
    if obj is None or obj.get('wl_exclude') or obj.get('wl_custom_model'):return
    values=dict(json.loads(obj.get('wl_pairs','[]')))
    if profiles.is_source(scene.wavelength.engine):
        from . import source_pose
        source_pose.apply(obj,list(values.items()))
    token=(scene.wavelength.engine,scene.wavelength.game_dir,*(values.get(k,'') for k in ('classname','model','skin','body')))
    key=obj.as_pointer();old=_watched_models.get(key);_watched_models[key]=token
    if obj.get('wl_representation_pending'):
        if old is not None and old!=token:
            from . import asset_loading
            asset_loading.entity(scene,obj)
        return
    references=[c for c in obj.children if c.get('wl_model_reference')]
    mismatch=bool(values.get('model','').lower().endswith('.mdl') and references and
                  any(c.get('wl_source_model','').lower()!=values['model'].replace('\\','/').lower() for c in references))
    if (old is not None and old!=token) or mismatch or needs_representation(scene,obj):
        from . import asset_loading
        asset_loading.entity(scene,obj)

def needs_representation(scene,obj,children=None):
    if obj.get('wl_role')!='ENTITY' or obj.get('wl_exclude') or obj.get('wl_custom_model') or obj.get('wl_representation_pending'):return False
    if children is None:children=obj.children
    if any(c.get('wl_entity_icon_reference') for c in children):return False
    references=[c for c in children if c.get('wl_model_reference')]
    if profiles.is_goldsrc(scene.wavelength.engine):return not any(c.get('wl_goldsrc_reference') for c in references)
    return not references


def target(context=None):
    global _last_target
    context=context or bpy.context
    obj=context.view_layer.objects.active
    visual=bool(obj and obj.get('wl_model_reference') and obj.parent and obj.parent.get('wl_role')=='ENTITY')
    selected=bool(obj and obj.select_get())
    if visual:obj=obj.parent
    dropping=bool(obj and obj.get('wl_model_choice') and not any(c.name.startswith('_WL_MODEL_BROWSER_') for c in obj.users_collection))
    if dropping:obj=_last_target
    if not obj or obj.name not in context.scene.objects or obj.get('wl_role')!='ENTITY' or obj.get('wl_exclude') or (not dropping and not (selected if visual else obj.select_get())):return None,[]
    settings=context.scene.wavelength
    if not (profiles.is_source(settings.engine) or profiles.is_goldsrc(settings.engine)):return None,[]
    try:
        classname=dict(json.loads(obj.get('wl_pairs','[]'))).get('classname','')
        if profiles.is_source(settings.engine):fields=source_schema.model_fields(settings,classname,bpy.path.abspath)
        else:
            from . import goldsrc_import
            from .entity import fgd,goldsrc
            props=goldsrc.merge_properties(classname,fgd.properties(goldsrc_import.definitions(settings),classname))
            fields=[p for p in props if p['type'].lower() in {'studio','model'}]
    except (OSError,ValueError):return None,[]
    if fields:_last_target=obj;return obj,fields
    return None,[]


def schedule(context=None,force=False,prepared_names=None):
    global _key,_owner,_total,_ready,_publish_limit
    context=context or bpy.context;s=context.scene.wavelength
    key=(s.engine,bpy.path.abspath(s.game_dir))
    if key==_key and _owner==context.scene and not force:return
    if prepared_names is not None:assets=None
    elif profiles.is_goldsrc(s.engine):
        from .goldsrc_model import Assets
        assets=Assets(key[1])
    else:assets=source_assets.library(key[1])
    names=set(prepared_names or [])
    from .asset_browser import ensure_catalog_file
    ensure_catalog_file(s)
    for mount in assets.mounts if assets else []:
        if isinstance(mount,source_assets.VPK):names.update(n for n in mount.entries if n.startswith('models/') and n.endswith('.mdl'))
        elif isinstance(mount,tuple):names.update(n for n in mount[1] if n.startswith('models/') and n.endswith('.mdl'))
        else:names.update(p.relative_to(mount).as_posix() for p in (mount/'models').rglob('*.mdl'))
    if profiles.is_goldsrc(s.engine) and assets:
        from .goldsrc_model import renderable
        names={name for name in names if renderable(assets,name)}
    colname='_WL_MODEL_BROWSER_'+hashlib.sha256(repr(key).encode()).hexdigest()[:16]
    collection=bpy.data.collections.get(colname)
    if collection is None:collection=bpy.data.collections.new(colname)
    collection.use_fake_user=True
    for owner in bpy.data.scenes:
        for parent in (owner.collection,*owner.collection.children_recursive):
            if collection.name in parent.children:parent.children.unlink(collection)
    collection.hide_viewport=True;collection.hide_render=True
    for obj in bpy.data.objects:
        if obj.get('wl_model_choice') and obj.asset_data:obj.asset_clear()
    _queue.clear();_ready=0;_publish_limit=96;_total=len(names);_key=key;_owner=context.scene
    existing={o.get('wl_source_model'):o for o in collection.objects}
    _queue.extend((path,existing.get(path),collection) for path in sorted(names))


def published(context,path):
    """Insert/rebuild one newly compiled asset without rescanning the library."""
    global _total,_publish_limit
    s=context.scene.wavelength;key=(s.engine,bpy.path.abspath(s.game_dir))
    if _key!=key or _owner!=context.scene:schedule(context)
    name='_WL_MODEL_BROWSER_'+hashlib.sha256(repr(key).encode()).hexdigest()[:16]
    collection=bpy.data.collections[name]
    obj=next((o for o in collection.objects if o.get('wl_source_model')==path),None)
    if obj:obj['wl_preview_ready']=False
    else:_total+=1
    for row in list(_queue):
        if row[0]==path:_queue.remove(row)
    _queue.appendleft((path,obj,collection));_publish_limit=max(_publish_limit,_ready+1)
    publish_batch()
    from .external_library import refresh_browsers
    refresh_browsers()


def publish_batch(query=''):
    global _ready
    from .asset_browser import metadata,preview
    deadline=time.monotonic()+.008
    while _queue and _ready<_publish_limit and time.monotonic()<deadline:
        if query and not all(word in _queue[0][0].lower() for word in query.split()):break
        path,obj,col=_queue.popleft()
        if obj is None:
            obj=bpy.data.objects.new(path.removeprefix('models/'),None);col.objects.link(obj)
            obj['wl_model_choice']=True;obj['wl_source_model']=path;obj['wl_exclude']=True;obj['wl_asset_template']=True
        row=asset_index.record(_key[0],path);row['game_dir']=_key[1];row['validation']='Choose to assign this engine model to the selected entity'
        metadata(obj,row);obj.asset_data.catalog_id=CATALOG
        if not obj.get('wl_preview_ready'):preview(obj)
        _ready+=1


def assign(context,row):
    obj,fields=target(context)
    if obj is None:raise ValueError('Select an entity with a model property first')
    if obj.get('wl_custom_model'):raise ValueError('This entity owns editable custom model sources; detach that custom model before choosing a compiled game model')
    s=context.scene.wavelength
    if row['engine']!=s.engine:raise ValueError('Model belongs to another game profile')
    if row.get('game_dir') and row['game_dir']!=bpy.path.abspath(s.game_dir):raise ValueError('Model belongs to another game installation')
    key=s.model_browser_field
    if key not in {p['key'] for p in fields}:key=fields[0]['key']
    path=source_assets.asset_path(row['path']);values=dict(json.loads(obj['wl_pairs']));classname=values['classname']
    # Validate/load before changing either entity properties or the current preview.
    from . import model_import,native_source
    replacing=key=='model' and values.get('model')!=path
    if profiles.is_goldsrc(s.engine):
        from . import goldsrc_import,goldsrc_model
        variant=dict(values)
        if replacing or key!='model':variant.update(skin='0',body='0')
        mesh=goldsrc_import.mesh(s,path,goldsrc_model.Assets(bpy.path.abspath(s.game_dir)),variant);data={}
    elif native_source.enabled():
        import struct
        header=source_assets.library(bpy.path.abspath(s.game_dir)).prefix(path,156)
        if len(header)<156 or header[:4]!=b'IDST':raise ValueError('Invalid Source model header: '+path)
        mesh=None;data={'static':bool(struct.unpack_from('<I',header,152)[0]&16)}
    else:mesh,data=model_import.mesh(s,path,0 if replacing or key!='model' else int(values.get('skin','0') or '0'),0 if replacing or key!='model' else int(values.get('body','0') or '0'))
    if classname=='prop_static' and not data['static']:raise ValueError('This model was not compiled for prop_static; use a dynamic/physics entity or choose a static-prop model')
    if key=='model' and (classname.startswith('prop_physics') or classname=='prop_ragdoll'):
        try:source_assets.library(bpy.path.abspath(s.game_dir)).read(path[:-4]+'.phy')
        except (OSError,ValueError) as exc:raise ValueError('This physics entity needs a model with its .phy collision companion: '+path) from exc
    pairs=[p for p in json.loads(obj['wl_pairs']) if p[0]!=key];pairs.append([key,path]);obj['wl_pairs']=json.dumps(pairs)
    if replacing:obj['wl_pairs']=json.dumps([[k,'0' if k in {'skin','body'} else v] for k,v in pairs])
    if key=='model':
        from .entity import models
        if profiles.is_source(s.engine):
            from . import asset_loading
            asset_loading.entity(context.scene,obj)
        else:
            models.remove_reference(obj)
            child=model_import.attach(context,obj,mesh,path)
            if profiles.is_goldsrc(s.engine):child['wl_goldsrc_reference']=True
    s.status=f'{obj.name}: {key} = {path}'
    # Invalidate the property editor's read/apply binding after this direct edit.
    s.entity_editor_binding=''
    return obj


def _tick_context():
    global _signature,_return_section,_fields,_query,_auto_section,_publish_limit
    publishing=False
    try:
        from . import workspace
        if not hasattr(bpy.context.scene,'wavelength') or not workspace.active():return .3
        while _representation_queue:
            scene,entity=_representation_queue[0]
            if scene!=bpy.context.scene:break
            _representation_queue.popleft()
            if entity.name in scene.objects and needs_representation(scene,entity):
                from . import asset_loading
                asset_loading.entity(scene,entity)
                break
        child=bpy.context.view_layer.objects.active
        if child and child.get('wl_model_reference') and child.parent and child.parent.get('wl_role')=='ENTITY':
            child.select_set(False);child.parent.select_set(True);bpy.context.view_layer.objects.active=child.parent
        s=bpy.context.scene.wavelength;obj,fields=target()
        if obj:watch_model(bpy.context.scene,obj)
        sig=(bpy.context.scene.as_pointer(),obj.as_pointer() if obj else 0,s.engine,s.game_dir,s.fgd_path,tuple(p['key'] for p in fields))
        if sig!=_signature and not getattr(bpy.context.window_manager,'wl_click_place',False):
            _signature=sig
            if obj:
                _fields=[(p['key'],p.get('label',p['key']),p['key']) for p in fields]
                if s.model_browser_field not in {p['key'] for p in fields}:s.model_browser_field=fields[0]['key']
                if s.asset_browser_section!='MODELS':_return_section=s.asset_browser_section;_auto_section=True
                schedule();s.asset_browser_section='MODELS'
                if not bpy.app.background and bpy.context.window and not any(a.type=='FILE_BROWSER' and a.ui_type=='ASSETS' for a in bpy.context.window.screen.areas):
                    from .entity.browser import ensure_browser_layout
                    ensure_browser_layout(bpy.context,section='MODELS')
            elif s.asset_browser_section=='MODELS' and _auto_section:s.asset_browser_section=_return_section;_auto_section=False
        if s.asset_browser_section=='MODELS' and _queue and _owner==bpy.context.scene and _key==(s.engine,bpy.path.abspath(s.game_dir)):
            query='';interacting=False
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type=='FILE_BROWSER' and area.ui_type=='ASSETS' and s.asset_browser_section=='MODELS' and area.spaces.active.params:
                        query=area.spaces.active.params.filter_search.lower().strip()
                        region=next((r for r in area.regions if r.type=='WINDOW'),None)
                        if region:
                            with bpy.context.temp_override(area=area,region=region):
                                asset=getattr(bpy.context,'asset',None);block=asset.local_id if asset else None
                                interacting=interacting or bool(block and block.get('wl_asset_category')=='MODEL')
            if query!=_query:
                _query=query
                _publish_limit=_ready+96
                if query:
                    ordered=sorted(_queue,key=lambda row:not all(word in row[0].lower() for word in query.split()))
                    _queue.clear();_queue.extend(ordered)
            if not interacting:
                ready=_ready;publish_batch(query);publishing=_ready!=ready
            if publishing:
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type=='FILE_BROWSER':area.tag_redraw()
        return .15 if publishing else .3
    except (ReferenceError,ValueError,OSError,RuntimeError,AttributeError,TypeError) as exc:
        if hasattr(bpy.context.scene,'wavelength'):bpy.context.scene.wavelength.status=str(exc)
        return .5


def tick():
    from . import workspace
    if bpy.app.background:return _tick_context()
    delays=[]
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if workspace.active():delays.append(_tick_context())
    return min(delays,default=.3)


@persistent
def loaded(_):
    global _signature,_key,_last_target,_auto_section
    _auto_section=False
    _signature=None;_key=None;_last_target=None;_queue.clear()
    _representation_queue.clear()
    _watched_models.clear()
    scene=bpy.context.scene
    if hasattr(scene,'wavelength') and (profiles.is_source(scene.wavelength.engine) or profiles.is_goldsrc(scene.wavelength.engine)):
        children={}
        for obj in scene.objects:
            if obj.parent:children.setdefault(obj.parent.as_pointer(),[]).append(obj)
        _representation_queue.extend((scene,obj) for obj in scene.objects if needs_representation(scene,obj,children.get(obj.as_pointer(),[])))
    for obj in bpy.data.objects:
        if obj.get('wl_model_reference') and obj.type=='MESH' and obj.parent and obj.parent.get('wl_role')=='ENTITY':obj.hide_select=False
    if not bpy.app.timers.is_registered(tick):bpy.app.timers.register(tick,first_interval=.1,persistent=True)


def placed(obj):
    """Finish native asset placement outside depsgraph callbacks."""
    def focus():
        global _signature
        try:
            for window in bpy.context.window_manager.windows:
                with bpy.context.temp_override(window=window):
                    if obj.name not in bpy.context.view_layer.objects:continue
                    obj.hide_select=False;obj.hide_viewport=False;obj.hide_set(False)
                    for selected in bpy.context.selected_objects:selected.select_set(False)
                    obj.select_set(True);bpy.context.view_layer.objects.active=obj
                    if (profiles.is_source(bpy.context.scene.wavelength.engine) or profiles.is_goldsrc(bpy.context.scene.wavelength.engine)) and not any(c.get('wl_model_reference') for c in obj.children):
                        from .entity import models
                        models.attach_reference(obj)
                    _signature=None
                    from . import workspace
                    if workspace.active():_tick_context()
                    break
        except ReferenceError:pass
    bpy.app.timers.register(focus,first_interval=.01)


class WL_OT_more_models(bpy.types.Operator):
    bl_idname='wavelength.more_models';bl_label='Load More Models'
    bl_description='Publish the next 96 model choices; search covers the full indexed library'
    def execute(self,context):
        global _publish_limit
        _publish_limit+=96
        return {'FINISHED'}


def register():
    bpy.utils.register_class(WL_OT_more_models)
    if loaded not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(loaded)
    if not bpy.app.timers.is_registered(initialize):bpy.app.timers.register(initialize,first_interval=.05)
    if not bpy.app.timers.is_registered(tick):bpy.app.timers.register(tick,first_interval=.3,persistent=True)


def unregister():
    global _key,_signature
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if bpy.app.timers.is_registered(initialize):bpy.app.timers.unregister(initialize)
    if loaded in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(loaded)
    _queue.clear();_key=None;_signature=None
    _representation_queue.clear()
    bpy.utils.unregister_class(WL_OT_more_models)


def initialize():loaded(None)
