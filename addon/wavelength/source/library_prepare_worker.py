"""Profile indexing and incremental thumbnail preparation outside the editor."""
import hashlib,json,sys,time,traceback,os
from pathlib import Path
from types import SimpleNamespace

VERSION=3

def parent_alive(pid):
    if not pid:return True
    if os.name!='nt':return os.getppid()==pid
    import ctypes
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return False
    try:
        code=ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))

def write(path,value):
    import uuid
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(json.dumps(value),encoding='utf-8')
        for attempt in range(12):
            try:temp.replace(path);return
            except PermissionError:
                if attempt==11:raise
                time.sleep(min(.01*2**attempt,.2))
    finally:temp.unlink(missing_ok=True)

def run(request):
    import bpy
    from wavelength.source import profiles,source_assets,goldsrc_model,goldsrc_import,model_thumbnail_worker
    from wavelength.source.entity import fgd,source_schema,goldsrc,icons
    from wavelength.source import studio_model
    settings=SimpleNamespace(engine=request['engine'],game_dir=request['game_dir'],fgd_path=request.get('fgd_path',''),unit_scale=.0254)
    root=Path(request['cache']);root.mkdir(parents=True,exist_ok=True);manifest=root/'manifest.json'
    try:previous=json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError,ValueError):previous={}
    records=previous.get('records',{}) if previous.get('version')==VERSION else {}
    original_library=source_assets.library
    def prepare():
        nonlocal records
        source=profiles.is_source(settings.engine)
        assets=source_assets.Assets(settings.game_dir) if source else goldsrc_model.Assets(settings.game_dir)
        game_read=assets.read;dependencies={}
        def original_read(name):
            if name.startswith('wavelength/icons/'):return (icons.ICON_ROOT/'icons'/Path(name).name).read_bytes()
            return game_read(name)
        def read(name):
            name=source_assets.asset_path(name)
            try:data=original_read(name)
            except (OSError,ValueError):dependencies[name]=None;raise
            dependencies[name]=hashlib.sha256(data).hexdigest();return data
        assets.read=read
        if source:source_assets.library=lambda game:assets
        classes=source_schema.definitions(settings) if source else fgd.load(settings.fgd_path) if settings.fgd_path else {}
        names=set();watch_files=set()
        for mount in assets.mounts:
            if isinstance(mount,Path):
                watch_files.add(mount)
                names.update(p.relative_to(mount).as_posix().lower() for p in (mount/'models').rglob('*') if p.is_file() and p.suffix.lower()=='.mdl')
                for directory in ('models','materials'):
                    watch_files.add(mount/directory)
                    watch_files.update((mount/directory).rglob('*'))
                watch_files.update(p for p in (mount/'gameinfo.txt',mount/'liblist.gam') if p.is_file())
            elif isinstance(mount,tuple):
                names.update(n for n in mount[1] if n.startswith('models/') and n.endswith('.mdl'));watch_files.add(mount[0])
            else:
                names.update(n for n in mount.entries if n.startswith('models/') and n.endswith('.mdl'))
                watch_files.update(mount.path.parent.glob(mount.path.name.removesuffix('_dir.vpk')+'*.vpk'))
        if settings.fgd_path:watch_files.update(Path(settings.fgd_path).parent.glob('*.fgd'))
        if source:
            for files,_,_ in source_schema._CACHE.values():watch_files.update(files)
        if not source:names={name for name in names if goldsrc_model.renderable(assets,name)}
        else:names={name for name in names if studio_model.renderable(assets,name)}
        watch_files.update(icons.ICON_ROOT.rglob('*'))
        if request.get('paths') is not None:names.intersection_update(request['paths'])
        entities={name for name,_,_ in fgd.entity_classes(classes)}
        if not source:entities.update(goldsrc.class_names())
        entries={};jobs={}
        def add(key,path,values):
            path=source_assets.asset_path(path)
            identity=hashlib.sha256(json.dumps([VERSION,path,values],sort_keys=True).encode()).hexdigest()
            entries[key]={'record':identity};jobs[identity]=(path,values)
        for name in sorted(names):
            body=goldsrc_model.preview_body(assets,name) if not source else 0
            add('MODEL:'+name,name,{'body':str(body)} if body else {})
        for classname in sorted(entities):
            props=fgd.properties(classes,classname)
            if not source:props=goldsrc.merge_properties(classname,props)
            pairs=[('classname',classname),*((p['key'],p['default']) for p in props if p.get('default','')!='')]
            path=source_schema.representation_model(settings,classname,pairs) if source else ''
            if not source:
                for candidate in goldsrc_import.candidates(settings,classname,pairs):
                    try:read(candidate);path=candidate;break
                    except (OSError,ValueError):pass
            if not path:
                icon=icons.icon_path(classname)
                if icon:
                    add('ENTITY:'+classname,'wavelength/icons/'+icon.name,{'icon':icon.name})
                continue
            if request.get('paths') is not None and path.lower() not in names:continue
            values={k:v for k,v in pairs if k in {'skin','body','sequence'} and v not in {'',':','-1'}}
            # Default zero skin/body share the model tile's render.
            values={k:v for k,v in values.items() if k=='sequence' or v!='0'}
            add('ENTITY:'+classname,path,values)
        state={'version':VERSION,'state':'PREPARING','done':0,'total':len(jobs),'errors':0,'assets':entries,'records':{key:records[key] for key in jobs if key in records},'models':sorted(names),'current':'Index complete'}
        write(manifest,state)
        checks={}
        pending=list(jobs)
        aliases={identity:[] for identity in jobs}
        for key,entry in entries.items():aliases[entry['record']].append(key)
        aliases={identity:' '.join(keys).lower() for identity,keys in aliases.items()}
        pending.sort(key=lambda identity:'entity:' not in aliases[identity])
        while pending:
            if not parent_alive(request.get('parent_pid')):return watch_files
            try:priority=json.loads((root/'priority.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):priority=[]
            selected=next((i for i,identity in enumerate(pending) if any(query and all(word in aliases[identity] for word in query.lower().split()) for query in priority)),0)
            identity=pending.pop(selected);path,values=jobs[identity]
            state['current']=path;write(manifest,state)
            record=records.get(identity,{});valid=bool(record and (root/record.get('image','missing')).is_file()) or bool(record.get('error'))
            if not record.get('dependencies'):valid=False
            if valid:
                for name,digest in record['dependencies'].items():
                    if name not in checks:
                        try:checks[name]=hashlib.sha256(original_read(name)).hexdigest()
                        except (OSError,ValueError):checks[name]=None
                    if checks[name]!=digest:valid=False;break
            if not valid:
                dependencies.clear();output=root/(identity+'.png');output.with_suffix('.error').unlink(missing_ok=True)
                if values.get('icon'):read(path)
                if source:
                    # Use the same tracked reader for geometry and materials.
                    from wavelength.source import model_import
                    old_mesh=model_import.mesh
                    def mesh(s,p,skin=0,body=0,reader=None):return old_mesh(s,p,skin,body,assets)
                    model_import.mesh=mesh
                try:
                    # GoldSrc uses a new Assets instance inside the renderer;
                    # record its geometry/texture/pose dependencies as well.
                    old_assets=goldsrc_model.Assets
                    if not source:goldsrc_model.Assets=lambda game:assets
                    model_thumbnail_worker.render_batch(dict(engine=settings.engine,game_dir=settings.game_dir,fgd_path=settings.fgd_path,jobs=[dict(path=path,values=values,output=str(output))]))
                finally:
                    goldsrc_model.Assets=old_assets
                    if source:model_import.mesh=old_mesh
                failure=output.with_suffix('.error')
                record={'dependencies':dict(dependencies),'image':output.name if output.is_file() and not failure.is_file() else '',
                        'stamp':output.stat().st_mtime_ns if output.is_file() else 0,'error':failure.read_text(encoding='utf-8') if failure.is_file() else ''}
            state['records'][identity]=record;state['done']+=1;state['errors']+=bool(record.get('error'));write(manifest,state)
        records=state['records'];state.update(state='READY',current='Library ready');write(manifest,state)
        return watch_files
    def signature(files):
        result=[]
        for p in sorted(files):
            try:s=p.stat();result.append((str(p),s.st_mtime_ns,s.st_size))
            except OSError:result.append((str(p),None,None))
        return result
    try:
        files=prepare();stamp=signature(files)
        while request.get('watch',True):
            time.sleep(20)
            if not parent_alive(request.get('parent_pid')):return
            changed=signature(files)
            if changed!=stamp:files=prepare();stamp=signature(files)
    finally:source_assets.library=original_library

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    request=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8'))
    try:run(request)
    except Exception as exc:
        target=Path(request['cache'])/'manifest.json'
        try:value=json.loads(target.read_text(encoding='utf-8'))
        except (OSError,ValueError):value={}
        value.update(version=VERSION,state='FAILED',message=str(exc));write(target,value);traceback.print_exc();raise
