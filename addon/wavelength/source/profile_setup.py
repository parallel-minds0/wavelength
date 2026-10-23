"""Profile library lifecycle and bounded import of worker-rendered asset previews."""
import atexit,hashlib,json,os,subprocess,time
from pathlib import Path
from collections import deque,OrderedDict
import bpy
from bpy.props import EnumProperty
from . import profiles,workspace

_process=None;_log=None;_active=None;_candidate=None;_since=0
_cache=OrderedDict();_blocks={};_pending=deque();_AUTO=True;_CACHE_ROOT=None
_priority=None
_catalog_names={}

def configuration(settings):
    if not (profiles.is_source(settings.engine) or profiles.is_goldsrc(settings.engine)):raise ValueError('Library setup currently supports Source 1 and GoldSrc profiles')
    if not settings.game_dir:raise ValueError('Set Game Directory to the installed game or mod')
    game=Path(bpy.path.abspath(settings.game_dir)).resolve()
    if not game.is_dir():raise ValueError('Game Directory does not exist')
    fgd=bpy.path.abspath(settings.fgd_path) if settings.fgd_path else ''
    if profiles.is_source(settings.engine):
        if not (game/'gameinfo.txt').is_file():raise ValueError('Source Game Directory must contain gameinfo.txt')
        from .entity import source_schema
        fgd=str(source_schema.path(settings,bpy.path.abspath))
    elif not (game/'models').is_dir() and not list(game.glob('pak*.pak')) and not (game.parent/'valve/models').is_dir():raise ValueError('GoldSrc Game Directory has no models, PAKs or base valve content')
    if fgd and not Path(fgd).is_file():raise ValueError('Entity definitions file does not exist')
    return dict(engine=settings.engine,game_dir=str(game),fgd_path=fgd)

def folder(config):
    identity=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:24]
    return Path(_CACHE_ROOT or Path.home()/'.cache/wavelength/libraries')/identity

def read(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def state(settings):
    try:config=configuration(settings)
    except ValueError as exc:return dict(state='NEEDS_CONFIGURATION',message=str(exc))
    root=folder(config);control=read(root/'control.json',{})
    if control.get('manual'):
        value=dict(manifest(root));value.update(state=control.get('state','PAUSED'),message=control.get('message','Cached previews remain available'));return value
    return manifest(root) or dict(state='READY_FOR_SETUP',message='Game content ready to index')

def manifest(root):
    path=root/'manifest.json'
    try:stamp=path.stat().st_mtime_ns
    except OSError:return {}
    old=_cache.get(str(root))
    if not old or old[0]!=stamp:
        value=read(path,{})
        old_records=old[1].get('records',{}) if old else {}
        changed={key for key,record in value.get('records',{}).items() if (record.get('image'),record.get('stamp'),record.get('error'))!=(old_records.get(key,{}).get('image'),old_records.get(key,{}).get('stamp'),old_records.get(key,{}).get('error'))}
        _cache[str(root)]=(stamp,value);_cache.move_to_end(str(root))
        while len(_cache)>4:_cache.popitem(last=False)
        for (key,asset),names in list(_blocks.items()):
            if key!=str(root):continue
            entry=value.get('assets',{}).get(asset,{});record=value.get('records',{}).get(entry.get('record'),{})
            if entry.get('record') in changed:
                for name in names:
                    block=bpy.data.objects.get(name)
                    if matches(block,key,asset):block['wl_library_preview_error']=record.get('error','')
            if entry.get('record') in changed and record.get('image'):
                for name in names:_pending.append((key,asset,name,record['image']))
    return _cache[str(root)][1]

def matches(block,key,asset):
    if not block or not block.asset_data or block.get('wl_library_key')!=key:return False
    try:row=json.loads(block.get('wl_asset','{}'))
    except (TypeError,ValueError):return False
    return row.get('category','')+':'+row.get('path','')==asset

def apply(block,root,asset,image=None):
    if image is None:
        value=manifest(root);entry=value.get('assets',{}).get(asset,{});image=value.get('records',{}).get(entry.get('record'),{}).get('image')
    if not image:return False
    # Workers only produce hash-named PNGs inside this profile cache.
    path=root/image
    if path.parent!=root or path.suffix!='.png' or not path.is_file():return False
    token=image+':'+str(path.stat().st_mtime_ns)
    if block.get('wl_library_preview')==token:return False
    texture=bpy.data.images.load(str(path),check_existing=False)
    try:
        preview=block.preview_ensure();preview.image_size=tuple(texture.size);preview.image_pixels_float=list(texture.pixels)
        block['wl_library_preview']=token;block['wl_preview_ready']=True
    finally:bpy.data.images.remove(texture)
    return True

def register_asset(block,row,settings=None):
    if row.get('category') not in {'MODEL','ENTITY'}:return
    settings=settings or getattr(bpy.context.scene,'wavelength',None)
    if settings is None or row.get('engine')!=settings.engine:return
    if row.get('game_dir') and Path(bpy.path.abspath(row['game_dir'])).resolve()!=Path(bpy.path.abspath(settings.game_dir)).resolve():return
    try:root=folder(configuration(settings))
    except ValueError:return
    asset=row['category']+':'+row['path'];key=str(root)
    if block.get('wl_library_key') and block.get('wl_library_key')!=key:
        block.pop('wl_library_preview',None);block['wl_preview_ready']=False
    _blocks.setdefault((key,asset),set()).add(block.name);block['wl_library_key']=key
    value=manifest(root);entry=value.get('assets',{}).get(asset,{});record=value.get('records',{}).get(entry.get('record'),{})
    block['wl_library_preview_error']=record.get('error','')
    if record.get('image') and block.get('wl_library_preview')!=record['image']+':'+str(record.get('stamp',0)):
        _pending.append((key,asset,block.name,record['image']))

def stop(manual=False,reason='Profile inactive',cancel=False):
    global _process,_log,_active
    if _process and _process.poll() is None:
        _process.terminate()
        try:_process.wait(timeout=2)
        except subprocess.TimeoutExpired:_process.kill()
    if _log:_log.close()
    if _active:
        root=Path(_active);root.mkdir(parents=True,exist_ok=True)
        (root/'control.json').write_text(json.dumps(dict(manual=manual,state='CANCELLED' if cancel else 'PAUSED',message=reason)),encoding='utf-8')
    _process=None;_log=None;_active=None

def start(settings,force=False):
    global _process,_log,_active
    config=configuration(settings);root=folder(config)
    if _active==str(root) and _process and _process.poll() is None:return
    stop();root.mkdir(parents=True,exist_ok=True)
    (root/'control.json').write_text('{}',encoding='utf-8')
    if force:
        value=read(root/'manifest.json',{});value['version']=-1;(root/'manifest.json').write_text(json.dumps(value),encoding='utf-8')
    value=read(root/'manifest.json',{});value.update(state='INDEXING',current='Discovering game content');(root/'manifest.json').write_text(json.dumps(value),encoding='utf-8')
    request=dict(config,cache=str(root),watch=True,parent_pid=os.getpid())
    (root/'request.json').write_text(json.dumps(request),encoding='utf-8');_log=(root/'worker.log').open('a',encoding='utf-8')
    try:
        _process=subprocess.Popen([bpy.app.binary_path,'--background','--factory-startup','--threads','2','--python',str(Path(__file__).with_name('library_prepare_worker.py')),'--',str(root/'request.json')],stdout=_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except Exception:_log.close();_log=None;raise
    _active=str(root)

def _tick_context():
    global _candidate,_since,_process,_log,_priority
    try:
        context=bpy.context;s=getattr(context.scene,'wavelength',None)
        if not s or not workspace.active(context,'preparation'):
            if _process:stop()
            return 1.
        try:config=configuration(s)
        except ValueError:
            _candidate=None
            if _process:stop()
            return 1.
        root=folder(config);key=str(root)
        if _active and _active!=key:stop()
        if _candidate!=key:
            _candidate=key;_since=time.monotonic()
            for block in list(bpy.data.objects):
                if block.asset_data and block.get('wl_asset_profile')==s.engine and block.get('wl_asset_category') in {'MODEL','ENTITY'}:
                    try:register_asset(block,json.loads(block['wl_asset']),s)
                    except (KeyError,ValueError):pass
        info=manifest(root)
        if 'models' in info:
            names=tuple(info['models']);old_names=_catalog_names.get(key)
            _catalog_names[key]=names
            if old_names!=names and s.asset_browser_section=='MODELS':
                from . import model_browser
                model_browser.schedule(context,force=True,prepared_names=names)
        if _active==key:
            searches=[]
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type=='FILE_BROWSER' and area.ui_type=='ASSETS' and area.spaces.active.params:
                        query=area.spaces.active.params.filter_search.strip()
                        if query:searches.append(query)
            priority=(key,tuple(sorted(set(searches))))
            if priority!=_priority:
                _priority=priority;(root/'priority.json').write_text(json.dumps(priority[1]),encoding='utf-8')
        if _process and _process.poll() is not None:
            code=_process.returncode;_process=None
            if _log:_log.close();_log=None
            if info.get('state')!='READY':
                (root/'control.json').write_text(json.dumps(dict(manual=True,state='FAILED',message=f'Preparation worker exited ({code}); see worker.log')),encoding='utf-8')
        if _AUTO and s.auto_prepare_assets and not bpy.app.background and not _process and not read(root/'control.json',{}).get('manual') and time.monotonic()-_since>2:start(s)
        changed=False;deadline=time.monotonic()+.006
        while _pending and time.monotonic()<deadline:
            profile,asset,name,image=_pending.popleft();block=bpy.data.objects.get(name)
            if profile==key and matches(block,key,asset):changed=apply(block,root,asset,image) or changed
        if changed:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type=='FILE_BROWSER':area.tag_redraw()
    except (OSError,ValueError,RuntimeError,ReferenceError) as exc:
        if hasattr(bpy.context.scene,'wavelength'):bpy.context.scene.wavelength.status='Library setup: '+str(exc)
    return .3

def tick():
    if workspace.active(bpy.context,'preparation'):return _tick_context()
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if workspace.active(bpy.context,'preparation'):return _tick_context()
    return _tick_context()

class WL_OT_library_setup(bpy.types.Operator):
    bl_idname='wavelength.library_setup';bl_label='Prepare Profile Assets'
    action:EnumProperty(items=[('START','Start / Resume',''),('PAUSE','Pause',''),('CANCEL','Cancel',''),('REFRESH','Refresh Changed Content','')],default='START')
    def execute(self,context):
        if self.action in {'START','REFRESH'} and not workspace.active(context,'preparation'):
            self.report({'WARNING'},'Enable Asset Preparation in Level Editing within the Wavelength workspace')
            return {'CANCELLED'}
        try:
            if self.action in {'PAUSE','CANCEL'}:
                config=configuration(context.scene.wavelength);root=folder(config)
                if _active==str(root):stop(manual=True,reason='Cancelled by user' if self.action=='CANCEL' else 'Paused by user',cancel=self.action=='CANCEL')
                else:
                    root.mkdir(parents=True,exist_ok=True);(root/'control.json').write_text(json.dumps(dict(manual=True,state='CANCELLED' if self.action=='CANCEL' else 'PAUSED')),encoding='utf-8')
            else:
                if self.action=='REFRESH':stop()
                start(context.scene.wavelength)
        except (ValueError,OSError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class WL_PT_library_setup(bpy.types.Panel):
    bl_label='Profile Setup';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='scene';bl_parent_id='WL_PT_main';bl_order=-10
    @classmethod
    def poll(cls,context):return workspace.active(context) and (profiles.is_source(context.scene.wavelength.engine) or profiles.is_goldsrc(context.scene.wavelength.engine))
    def draw(self,context):
        layout=self.layout;s=context.scene.wavelength;info=state(s)
        layout.prop(s,'auto_prepare_assets');layout.label(text=info.get('state','READY_FOR_SETUP').replace('_',' ').title())
        if info.get('total'):
            layout.progress(factor=info.get('done',0)/max(1,info['total']),text=f"{info.get('done',0)}/{info['total']} previews · {info.get('errors',0)} unavailable")
        layout.label(text=str(info.get('message') or info.get('current') or '')[:90])
        row=layout.row(align=True);row.operator(WL_OT_library_setup.bl_idname,text='Start / Resume').action='START';row.operator(WL_OT_library_setup.bl_idname,text='Pause').action='PAUSE'
        row=layout.row(align=True);row.operator(WL_OT_library_setup.bl_idname,text='Refresh').action='REFRESH';row.operator(WL_OT_library_setup.bl_idname,text='Cancel').action='CANCEL'
        try:layout.label(text='Cache: '+str(folder(configuration(s))))
        except ValueError:pass

def register():
    for cls in (WL_OT_library_setup,WL_PT_library_setup):bpy.utils.register_class(cls)
    bpy.app.timers.register(tick,first_interval=1,persistent=True);atexit.register(stop)

def unregister():
    stop()
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    atexit.unregister(stop)
    for cls in (WL_PT_library_setup,WL_OT_library_setup):bpy.utils.unregister_class(cls)
