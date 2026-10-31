"""Decode requested map assets in a separate Blender process, without scene edits."""
import json,sys,time,traceback,os
from pathlib import Path
from types import SimpleNamespace


def run(request_path):
    from wavelength.source import source_assets,model_import
    request_path=Path(request_path);status_path=request_path.with_suffix('.status.json')
    try:completed=json.loads(status_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):completed={}
    last_work=time.monotonic()
    while True:
        request=json.loads(request_path.read_text(encoding='utf-8'))
        from wavelength.source.library_prepare_worker import parent_alive
        if not parent_alive(request.get('parent_pid')):return
        pending=[(k,v) for k,v in request['jobs'].items() if k not in completed]
        if not pending:
            if time.monotonic()-last_work>3:return
            time.sleep(.1);continue
        for identity,job in pending:
            try:
                assets=source_assets.library(job['game']);settings=SimpleNamespace(game_dir=job['game'])
                paths=job.get('paths',[])
                warnings=[]
                if job['kind']=='MODEL':
                    try:_,data=model_import.decoded(settings,job['path'],job['skin'],job['body'],assets)
                    except ValueError as exc:
                        if str(exc)!='Invalid model skin/body selection':raise
                        _,data=model_import.decoded(settings,job['path'],0,0,assets)
                    paths=[]
                    for name in data['materials']:
                        for directory in [*data['directories'],'']:
                            candidate=(directory.replace('\\','/').rstrip('/')+'/'+name).strip('/').lower()
                            try:
                                props=assets.material(candidate)
                                paths.extend('materials/'+source_assets.asset_path(props[field]).removeprefix('materials/').removesuffix('.vtf')+'.vtf'
                                             for field in ('$basetexture','$basetexture2','%tooltexture') if props.get(field))
                                break
                            except (OSError,ValueError):continue
                for path in dict.fromkeys(paths):
                    try:source_assets.decoded_preview(assets,path)
                    except (OSError,ValueError) as exc:
                        if job['kind']=='TEXTURE':raise
                        warnings.append(str(exc))
                completed[identity]={'ready':True,'warnings':warnings}
            except Exception as exc:
                completed[identity]={'error':str(exc)}
            # Windows readers may briefly hold the destination open. Retry the
            # atomic replace off-thread, retaining completed jobs across restarts.
            from wavelength.source.library_prepare_worker import write
            write(status_path,completed)
            last_work=time.monotonic()


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    run(sys.argv[sys.argv.index('--')+1])
