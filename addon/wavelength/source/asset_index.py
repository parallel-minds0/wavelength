"""Local, incremental engine asset metadata. No game data enters releases."""
import hashlib,json,os,struct,uuid
from pathlib import Path

EXTENSIONS={'.vmt':'MATERIAL','.wad':'ARCHIVE','.mdl':'MODEL','.gltf':'MODEL','.glb':'MODEL','.wav':'SOUND','.ogg':'SOUND','.mp3':'SOUND','.pcf':'PARTICLE','.spr':'EFFECT'}

def identity(engine,category,path):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,f'wavelength:{engine}:{category}:{path.casefold()}'))


def model_bounds(data):
    if len(data)<140 or data[:4]!=b'IDST':raise ValueError('No supported studio model header; using a labelled placement proxy')
    version=struct.unpack_from('<i',data,4)[0]
    offset=112 if version==10 else 104 if 44<=version<=49 else None
    if offset is None:raise ValueError(f'Unsupported MDL version {version}')
    import math
    lo=struct.unpack_from('<3f',data,offset);hi=struct.unpack_from('<3f',data,offset+12)
    if not all(math.isfinite(v) for v in (*lo,*hi)) or any(a>=b for a,b in zip(lo,hi)):raise ValueError('Invalid model bounds')
    return lo,hi


def record(engine,path,category=None,source='',signature=''):
    category=category or EXTENSIONS.get(Path(path).suffix.lower(),'EFFECT')
    low=path.lower()
    if category=='MATERIAL':
        if low.startswith(('decals/','materials/decals/')):category='DECAL'
        elif low.startswith(('skybox/','materials/skybox/')):category='SKY'
    return dict(id=identity(engine,category,path),engine=engine,path=path,category=category,source=source,compiled=path,dependencies=[],signature=signature,validation='indexed',schema=1)


def discover(settings):
    from . import profiles
    rows={}
    if profiles.is_source(settings.engine):
        from .source_assets import library,VPK
        for mount in library(settings.game_dir).mounts:
            entries=mount.entries if isinstance(mount,VPK) else (str(p.relative_to(mount)).replace('\\','/') for p in mount.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS)
            for name in entries:
                if Path(name).suffix.lower() not in EXTENSIONS:continue
                row=record(settings.engine,name,source=str(mount.path if isinstance(mount,VPK) else mount))
                rows.setdefault(row['id'],row)
    roots=json.loads(getattr(settings,'asset_paths','[]') or '[]')
    if settings.game_dir and not profiles.is_source(settings.engine):roots.insert(0,settings.game_dir)
    for root in roots:
        root=Path(root).expanduser()
        if not root.is_dir():continue
        for path in root.rglob('*'):
            if path.suffix.lower() not in EXTENSIONS or not path.is_file():continue
            st=path.stat();row=record(settings.engine,str(path.relative_to(root)).replace('\\','/'),source=str(root),signature=f'{st.st_mtime_ns}:{st.st_size}')
            rows.setdefault(row['id'],row)
    return sorted(rows.values(),key=lambda row:(row['category'],row['path']))


def write_index(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps({'schema':1,'assets':rows},sort_keys=True)
    if path.is_file() and path.read_text()==payload:return False
    temp=path.with_suffix('.tmp');temp.write_text(payload);os.replace(temp,path);return True
