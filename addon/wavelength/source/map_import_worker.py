"""Parse/validate map files off-process; stream bounded brush records to the UI."""
import json,sys,traceback,time
from pathlib import Path
from dataclasses import asdict


def run(request):
    from wavelength.source import formats,vmf,map_prepare,worker_status
    folder=Path(request);config=json.loads((folder/'request.json').read_text(encoding='utf-8'))
    def status(value):
        worker_status.publish(folder/'status.jsonl',value)
    try:
        path=Path(config['path'])
        status(dict(state='READING'))
        text=path.read_text(encoding='utf-8-sig')
        status(dict(state='PARSING'))
        document=(vmf.parse if path.suffix.lower()=='.vmf' else formats.parse)(text)
        if sum(dict(e.pairs).get('classname')=='worldspawn' for e in document.entities)!=1:raise ValueError('Exactly one worldspawn is required')
        total=sum(len(e.brushes) for e in document.entities)
        status(dict(state='VALIDATING',done=0,total=total))
        indices={id(e):i for i,e in enumerate(document.entities)};count=0
        last_progress=time.monotonic()
        with (folder/'brushes.jsonl').open('w',encoding='utf-8') as stream:
            for entity,brush,vertices,polygons in map_prepare.geometry(document):
                stream.write(json.dumps([indices[id(entity)],[asdict(f) for f in brush],vertices,polygons],separators=(',',':'))+'\n');count+=1
                if time.monotonic()-last_progress>=.1:
                    status(dict(state='VALIDATING',done=count,total=total));last_progress=time.monotonic()
        metadata=dict(entities=[dict(pairs=e.pairs,brushes=len(e.brushes),hidden=e.vmf_hidden) for e in document.entities],
                      brush_count=count,valve_axes=any(f.axes for e in document.entities for b in e.brushes for f in b))
        (folder/'metadata.json').write_text(json.dumps(metadata,separators=(',',':')),encoding='utf-8')
        status(dict(state='READY'))
    except Exception as exc:
        traceback.print_exc();status(dict(state='ERROR',message=str(exc)))


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    run(sys.argv[sys.argv.index('--')+1])
