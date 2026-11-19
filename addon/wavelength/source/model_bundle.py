"""Portable editable model archives with verified, contained dependencies."""
import hashlib,json,os,uuid,zipfile,stat
from pathlib import Path,PurePosixPath


def safe_path(name):
    path=PurePosixPath(name.replace('\\','/'))
    if not name or path.as_posix()=='.' or path.is_absolute() or '..' in path.parts or ':' in name:raise ValueError('Unsafe model package path: '+name)
    return path.as_posix()


def write(path,files,metadata):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.partial')
    manifest={**metadata,'schema':1,'files':{}}
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,source in sorted(files.items()):
                name=safe_path(name)
                if name=='manifest.json':raise ValueError('manifest.json is reserved')
                payload=source if isinstance(source,bytes) else Path(source).read_bytes()
                manifest['files'][name]=hashlib.sha256(payload).hexdigest();archive.writestr(name,payload)
            archive.writestr('manifest.json',json.dumps(manifest,indent=2))
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
    return manifest


def extract(path,destination):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        normalized=[safe_path(n).casefold() for n in names]
        if len(names)!=len(set(normalized)):raise ValueError('Duplicate model package entries')
        for info in archive.infolist():
            safe_path(info.filename)
            if stat.S_ISLNK(info.external_attr>>16):raise ValueError('Model package symlinks are not supported')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('schema')!=1 or not isinstance(manifest.get('files'),dict):raise ValueError('Unsupported model package manifest')
        if set(names)!=set(manifest['files'])|{'manifest.json'}:raise ValueError('Model package contains unlisted or missing files')
        # Verify everything before exposing an editable asset to Blender.
        for name,digest in manifest['files'].items():
            payload=archive.read(name)
            if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('Model package checksum mismatch: '+name)
        for name in manifest['files']:
            target=destination/safe_path(name)
            if not target.resolve().is_relative_to(destination):raise ValueError('Model package escapes its destination')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    return manifest


def import_asset(context,path):
    import tempfile,bpy
    from . import model_lifecycle
    with tempfile.TemporaryDirectory(prefix='wavelength-model-package-') as folder:
        manifest=extract(path,folder)
        if not isinstance(manifest.get('editable'),str) or manifest['editable'] not in manifest['files'] or not isinstance(manifest.get('collection'),str):raise ValueError('Package has no editable model definition')
        source=Path(folder)/safe_path(manifest['editable'])
        if not source.is_file() or source.suffix.lower()!='.blend':raise ValueError('Package has no editable blend asset')
        with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
            name=manifest['collection']
            if name not in available.collections:raise ValueError('Editable model collection is missing')
            loaded.collections=[name]
        asset=loaded.collections[0]
        context.scene.collection.children.link(asset)
        old_id=asset.get('wl_model_id','');asset['wl_model_id']=uuid.uuid4().hex
        asset['wl_model_parent_id']=old_id;asset.pop('wl_model_build_owner',None);asset.pop('wl_custom_model_id',None)
        origin=asset.wavelength_model.origin
        if origin and not origin.users_collection:context.scene.collection.objects.link(origin)
        model_lifecycle.ensure(context,asset);model_lifecycle.select_sources(context,asset)
        asset['wl_model_status']='Editable · imported package'
        return asset
