"""Bounded, disposable decoded-asset cache. Never stores executable pickle data."""
import hashlib,json,os,zlib
from pathlib import Path

VERSION=1
LIMIT=128*1024*1024


def key(value):return hashlib.sha256(json.dumps([VERSION,value],sort_keys=True).encode()).hexdigest()


def root():
    import bpy
    return Path(bpy.utils.user_resource('CONFIG'))/'wavelength'/'runtime-assets'


def read(identity):
    try:
        path=root()/(identity+'.cache')
        if path.stat().st_size>LIMIT:return None
        decoder=zlib.decompressobj();data=decoder.decompress(path.read_bytes(),LIMIT+1)
        if len(data)>LIMIT or not decoder.eof or decoder.unused_data:return None
        return data
    except (OSError,ValueError,zlib.error):return None


def write(identity,data):
    if len(data)>LIMIT:return
    temporary=None
    try:
        directory=root();directory.mkdir(parents=True,exist_ok=True)
        path=directory/(identity+'.cache');temporary=path.with_suffix(f'.{os.getpid()}.tmp')
        temporary.write_bytes(zlib.compress(data,1));temporary.replace(path)
    except OSError:pass
    finally:
        if temporary:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass
