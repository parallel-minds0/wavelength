"""Progressive map previews: pure decoding off-process, Blender data on the UI thread."""
import json,os,subprocess,tempfile,time
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from . import profiles,source_assets,runtime_cache

_jobs={};_waiting=[];_process=None;_request=None;_directory=None;_dirty=False;_log=None
_failures=set()
_references={}
_states_stamp=None;_states_cache={}


def _enqueue(job,waiter):
    global _dirty
    identity=runtime_cache.key(job)
    if job['kind']!='LOCAL':_jobs[identity]=job;_dirty=True
    # Rapid changes belong to one entity; publish only its newest request.
    if waiter[2]=='ENTITY':
        _waiting[:]=[(key,old) for key,old in _waiting if not (old[2]=='ENTITY' and old[1]==waiter[1])]
    _waiting.append((identity,waiter));_start_timer()


def material(settings,mat,name,paths):
    scene=next((s for s in bpy.data.scenes if hasattr(s,'wavelength') and s.wavelength==settings),bpy.context.scene)
    game=bpy.path.abspath(settings.game_dir);assets=source_assets.library(game)
    _enqueue(dict(kind='TEXTURE',game=game,paths=paths,stamps=[assets.fingerprint(p) for p in paths]),
             (scene,mat,'MATERIAL',name,settings.engine,game))


def entity(scene,obj):
    from . import native_source
    if profiles.is_source(scene.wavelength.engine):
        from . import source_pose
        source_pose.apply(obj,json.loads(obj.get('wl_pairs','[]')))
    if native_source.direct(scene.wavelength) and profiles.is_source(scene.wavelength.engine):
        from .entity import models
        models.attach_reference(obj,settings=scene.wavelength)
        return
    settings=scene.wavelength;game=bpy.path.abspath(settings.game_dir);pairs=obj.get('wl_pairs','[]')
    obj['wl_representation_pending']=True
    try:
        values=dict(json.loads(pairs));path=''
        if profiles.is_source(settings.engine):
            from .entity import source_schema
            path=source_schema.representation_model(settings,values.get('classname',''),list(values.items()),bpy.path.abspath)
        if path.lower().endswith('.mdl'):
            assets=source_assets.library(game);stem=path[:-4]
            paths=[path,stem+'.vvd',*(stem+x for x in ('.dx90.vtx','.dx80.vtx','.sw.vtx','.vtx'))]
            job=dict(kind='MODEL',game=game,path=path,skin=int(values.get('skin','0') or '0'),body=int(values.get('body','0') or '0'),stamps=[assets.fingerprint(p) for p in paths])
        else:job=dict(kind='LOCAL',object=obj.name)
        _enqueue(job,(scene,obj,'ENTITY',pairs,settings.engine,game))
    except (OSError,ValueError) as exc:
        obj['wl_model_error']=str(exc);obj.pop('wl_representation_pending',None)


def _start_timer():
    if not bpy.app.timers.is_registered(tick):bpy.app.timers.register(tick,first_interval=.05,persistent=True)


def _start_worker():
    global _process,_request,_directory,_dirty,_log
    if _directory is None:
        _directory=Path(tempfile.mkdtemp(prefix='wavelength-map-assets-'));_request=_directory/'request.json'
    if _dirty:
        temp=_request.with_suffix('.tmp');temp.write_text(json.dumps(dict(parent_pid=os.getpid(),jobs=_jobs)),encoding='utf-8');temp.replace(_request);_dirty=False
    if _process and _process.poll()==0:
        try:states=json.loads(_request.with_suffix('.status.json').read_text())
        except (OSError,ValueError):states={}
        if any(k not in states for k in _jobs):_process=None
    if _jobs and _process is None:
        if _log:_log.close()
        _log=(_directory/'worker.log').open('ab')
        command=[bpy.app.binary_path,'--background','--factory-startup','--python',str(Path(__file__).with_name('asset_runtime_worker.py')),'--',str(_request)]
        _process=subprocess.Popen(command,stdout=_log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def tick():
    global _waiting,_states_stamp,_states_cache
    if any(scene.get('wl_importing') for scene in bpy.data.scenes):return .1
    if not _waiting:return None
    try:
        _start_worker()
        try:
            path=_request.with_suffix('.status.json');stamp=path.stat().st_mtime_ns
            if stamp!=_states_stamp:
                _states_cache=json.loads(path.read_text());_states_stamp=stamp
            states=_states_cache
        except (OSError,ValueError):states={}
        if _process and _process.poll() is not None and _process.returncode:
            states.update({k:{'error':'Asset decoding worker failed; see '+str(_directory/'worker.log')} for k in _jobs if k not in states})
        # Amortize dependency-graph updates across a small batch. Yielding after
        # every prop forces Blender to reevaluate the entire imported map.
        deadline=time.monotonic()+.008;remaining=[]
        # Round-robin rather than scanning every waiter after the time budget
        # expired. Ready jobs at the tail must not starve behind pending ones.
        waiting=_waiting
        for index,(identity,waiter) in enumerate(waiting):
            if index>=64 or time.monotonic()>=deadline:
                remaining=waiting[index:]+remaining;break
            scene,obj,kind,value,engine,game=waiter
            try:
                state=states.get(identity,{'ready':True} if identity not in _jobs else {})
                if not state:remaining.append((identity,waiter));continue
                if scene.name not in bpy.data.scenes or scene.wavelength.engine!=engine or bpy.path.abspath(scene.wavelength.game_dir)!=game:continue
                if (kind=='ENTITY' and (obj.name not in scene.objects or obj.get('wl_pairs','[]')!=value)) or (kind=='MATERIAL' and obj.name not in bpy.data.materials):continue
                error=state.get('error')
                if error:
                    obj['wl_model_error' if kind=='ENTITY' else 'wl_asset_error']=error
                    _failures.add(obj.name)
                elif kind=='MATERIAL':source_assets.material(scene.wavelength,value,target_mat=obj)
                else:
                    from .entity import models
                    from . import model_import
                    reference_key=(identity,profiles.unit_meters(scene.wavelength))
                    cached=_references.get(reference_key)
                    if cached:
                        try:
                            if cached[0].name not in bpy.data.meshes:cached=None
                        except ReferenceError:cached=None
                    def attach():
                        if cached:
                            models.remove_reference(obj)
                            model_import.attach(bpy.context,obj,cached[0],cached[1])
                            obj.pop('wl_model_error',None)
                            if cached[2]:obj['wl_model_warning']=cached[2]
                        else:
                            models.attach_reference(obj)
                            if identity in _jobs and _jobs[identity]['kind']=='MODEL':
                                child=next((c for c in obj.children if c.get('wl_model_reference') and c.type=='MESH'),None)
                                if child:_references[reference_key]=(child.data,_jobs[identity]['path'],obj.get('wl_model_warning',''))
                    window=next((w for w in bpy.context.window_manager.windows if w.scene==scene),None)
                    if window:
                        with bpy.context.temp_override(window=window):attach()
                    elif bpy.app.background:attach()
                    else:remaining.append((identity,waiter));continue
                    if obj.get('wl_model_error'):_failures.add(obj.name)
                obj.pop('wl_representation_pending' if kind=='ENTITY' else 'wl_source_pending',None)
            except ReferenceError:continue
            except (OSError,ValueError,RuntimeError) as exc:
                obj['wl_model_error' if kind=='ENTITY' else 'wl_asset_error']=str(exc)
                _failures.add(obj.name)
                obj.pop('wl_representation_pending' if kind=='ENTITY' else 'wl_source_pending',None)
        _waiting=remaining
        for window in bpy.context.window_manager.windows:
            if hasattr(window.scene,'wavelength'):
                window.scene.wavelength.status=f'Loading map previews: {len(_waiting)} remaining' if _waiting else f'Map previews ready'+(f' · {len(_failures)} unavailable' if _failures else '')
            for area in window.screen.areas:
                if area.type=='VIEW_3D':area.tag_redraw()
    except (OSError,RuntimeError) as exc:
        print('wavelength map asset loading:',exc)
    return .05 if _waiting else None


def clear():
    global _process,_request,_directory,_dirty,_log,_states_stamp,_states_cache
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if _process and _process.poll() is None:_process.terminate()
    if _log:_log.close()
    _jobs.clear();_waiting.clear();_failures.clear();_references.clear();_process=None;_request=None;_directory=None;_dirty=False;_log=None
    _states_stamp=None;_states_cache={}


@persistent
def loaded(_):
    clear()
    for scene in bpy.data.scenes:
        if not hasattr(scene,'wavelength') or not profiles.is_source(scene.wavelength.engine):continue
        from . import source_pose
        source_pose.migrate(scene)
        from . import native_source
        if native_source.enabled():
            native_source.migrate(scene)
            from . import render_support
            render_support.prepare(scene)
            continue
        materials={m for o in scene.objects if o.type=='MESH' for m in o.data.materials if m and m.get('wl_source_pending')}
        for mat in materials:
            try:source_assets.material(scene.wavelength,mat['wl_texture'],target_mat=mat,defer=True)
            except (OSError,ValueError):pass
        for obj in scene.objects:
            if obj.get('wl_representation_pending'):entity(scene,obj)


def register():
    from . import map_import
    map_import.register()
    from . import render_support
    render_support.register()
    bpy.utils.register_class(WL_OT_reload_map_assets)
    if loaded not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(loaded)


def unregister():
    from . import map_import
    map_import.unregister()
    from . import render_support
    render_support.unregister()
    clear()
    if loaded in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(loaded)
    bpy.utils.unregister_class(WL_OT_reload_map_assets)


class WL_OT_reload_map_assets(bpy.types.Operator):
    bl_idname='wavelength.reload_map_assets';bl_label='Reload Map Asset Previews'
    bl_description='Retry missing map textures and entity previews, checking game files for changes'
    @classmethod
    def poll(cls,context):return hasattr(context.scene,'wavelength') and profiles.is_source(context.scene.wavelength.engine)
    def execute(self,context):
        clear();source_assets._cache.clear();source_assets._checked.clear()
        scene=context.scene
        materials={m for o in scene.objects if o.type=='MESH' for m in o.data.materials if m and m.get('wl_texture')}
        for mat in materials:
            try:source_assets.material(scene.wavelength,mat['wl_texture'],target_mat=mat,defer=True)
            except (OSError,ValueError) as exc:mat['wl_asset_error']=str(exc)
        for obj in tuple(scene.objects):
            if obj.get('wl_role')=='ENTITY' and not obj.get('wl_custom_model'):entity(scene,obj)
        self.report({'INFO'},'Map asset previews queued; geometry remains editable')
        return {'FINISHED'}
