"""One transaction owns the Python add-on and compiled Blender patch together.

The installer applies verified build-specific bytes; the C++ payload does not
perform injection. A journal and original backup support recovery and removal.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
from contextlib import contextmanager, nullcontext
from .core import sha256, install_addon
from .binary_patch import validate_recipe


def write_json(path, value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


@contextmanager
def locked(state):
    state.mkdir(parents=True,exist_ok=True)
    # Kernel releases the lock even after a killed installer process.
    import fcntl
    with (state/'lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another installer is running')
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def inventory(path):
    if path.is_symlink():raise ValueError('Symlink add-on directory is unsupported')
    if not path.exists():return None
    result={}
    for file in sorted(path.rglob('*')):
        if file.is_symlink():raise ValueError('Symlinks in add-on tree are unsupported')
        if file.is_file() and '__pycache__' not in file.parts and file.suffix not in {'.pyc','.pyo'}:
            result[str(file.relative_to(path))]=sha256(file)
    return result


def replace_file(source,target):
    # Stage on target filesystem so the replacement is atomic even across mounts.
    fd,name=tempfile.mkstemp(prefix='.wavelength-',dir=target.parent)
    os.close(fd);temporary=Path(name)
    try:
        shutil.copy2(source,temporary)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)


def status(state):
    receipt=Path(state)/'receipt.json'
    if not receipt.exists():return {'phase':'not-installed'}
    data=json.loads(receipt.read_text())
    data.setdefault('installation_mode','verified')
    if data['phase']=='installed':
        target=Path(data['blender']);addon=Path(data['addon'])
        data['native_matches']=target.is_file() and sha256(target)==data['patched_sha256']
        data['addon_matches']=inventory(addon)==data['addon_inventory']
        if data.get('runtime_dir'):
            runtime=Path(data['runtime_dir'])
            data['native_matches']=data['native_matches'] and all((runtime/name).is_file() and sha256(runtime/name)==data[key] for name,key in [('blender','runtime_payload_sha256'),('AppRun','runtime_launcher_sha256')])
    return data


def select_recipe(bundle,blender,*,allow_unverified=False):
    manifest=json.loads((bundle/'patches/manifest.json').read_text())
    digest=sha256(blender)
    for entry in manifest.get('supported_builds',[]):
        if entry.get('verified') is True and entry.get('sha256')==digest:
            relative=Path(entry['recipe'])
            recipe=(bundle/'patches'/relative).resolve()
            if not recipe.is_relative_to((bundle/'patches').resolve()):raise ValueError('Invalid recipe path')
            return recipe
    if allow_unverified:return None  # Caller attempts structural generation for actual payload.
    raise ValueError('No verified native patch for this exact Blender installation. Nothing was installed. Both components are required.')


def _restore(state,data):
    target=Path(data['blender']);addon=Path(data['addon'])
    if sha256(state/'original-blender')!=data['original_sha256']:
        raise ValueError('Original Blender backup is damaged; refusing recovery')
    if target.exists() and sha256(target) not in {data['original_sha256'],data['patched_sha256']}:
        raise ValueError('Blender changed since installation; preserve it and resolve recovery manually')
    # Leave user edits intact, including when recovering an interrupted removal.
    actual=inventory(addon)
    if actual not in (None,data['addon_inventory'],data['previous_addon_inventory']):
        raise ValueError('Add-on changed since installation; refusing to discard edits')
    if data['previous_addon_inventory'] is not None:
        if inventory(state/'original-addon')!=data['previous_addon_inventory']:
            raise ValueError('Original add-on backup is damaged; refusing recovery')
    with tempfile.TemporaryDirectory(prefix='.wl-restore-',dir=addon.parent) as temporary:
        stage=Path(temporary)
        if data['previous_addon_inventory'] is not None:
            shutil.copytree(state/'original-addon',stage/'restored')
        replace_file(state/'original-blender',target)
        if actual==data['addon_inventory']:
            os.replace(addon,stage/'discarded')
        if data['previous_addon_inventory'] is not None and not addon.exists():
            os.replace(stage/'restored',addon)
        data['phase']='removed';write_json(state/'receipt.json',data)


def install(bundle,blender,addons,state,*,allow_unverified=False,confirm_experimental=False):
    bundle=Path(bundle).resolve();blender=Path(blender).expanduser().resolve(strict=True)
    addons=Path(addons).expanduser().resolve();state=Path(state).expanduser().resolve()
    if allow_unverified and not confirm_experimental:
        raise ValueError('Experimental installation requires explicit risk confirmation')
    initial_hash=sha256(blender)
    # Native support is checked before touching even the destination directories.
    from .core import inspect_blender
    recipe_path=select_recipe(bundle,blender,allow_unverified=allow_unverified)
    experimental=recipe_path is None
    if not experimental:
        if inspect_blender(blender)['payload_inspection_required']:
            raise ValueError('Verified AppImage deployment is unsupported; use experimental mode or an extracted payload with a verified recipe')
        recipe=json.loads(recipe_path.read_text());patched=validate_recipe(recipe,blender.read_bytes())
    manifest=json.loads((bundle/'bundle.json').read_text())
    archive=(bundle/manifest['addon']).resolve()
    if not archive.is_relative_to(bundle) or sha256(archive)!=manifest['addon_sha256']:
        raise ValueError('Bundled Python add-on checksum mismatch')
    addon=addons/'wavelength'
    if state==addon or state.is_relative_to(addon) or addon.is_relative_to(state):
        raise ValueError('Installer state and add-on directories must be separate')
    if blender.is_relative_to(state) or blender.is_relative_to(addon):
        raise ValueError('Blender executable must be outside installer state and add-on directories')
    from .deployment import prepare
    with prepare(blender) if experimental else nullcontext(None) as prepared:
        return _install_prepared(bundle,blender,addons,state,archive,manifest,addon,initial_hash,
                                 prepared,patched if not experimental else prepared['patched'])


def _install_prepared(bundle,blender,addons,state,archive,manifest,addon,initial_hash,prepared,patched):
    from .deployment import stage_runtime
    with locked(state):
        old=status(state)
        if old['phase'] not in {'not-installed','removed'}:
            raise ValueError('Existing installation or interrupted transaction; remove/recover it first')
        if sha256(blender)!=initial_hash:raise ValueError('Blender changed during preparation; retry with Blender closed')
        addons.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.wl-stage-',dir=addons) as temp:
            staged=install_addon(archive,temp)
            if prepared:
                (staged/'experimental-grid.json').write_text(json.dumps({'native_component':'embedded-grid-shader-prototype','limitations':prepared['limitations']}))
            previous=inventory(addon)
            backup=state/'original-addon'
            if backup.exists():shutil.rmtree(backup)
            if addon.exists():shutil.copytree(addon,backup)
            shutil.copy2(blender,state/'original-blender')
            runtime_info={}
            if prepared:
                write_json(state/'experimental-recipe.json',prepared['recipe'])
                runtime_info['native_input_sha256']=prepared['recipe']['input_sha256']
                runtime_info['native_output_sha256']=prepared['recipe']['output_sha256']
            if prepared and prepared['runtime']:
                patched,deployment_info=stage_runtime(prepared,state)
                runtime_info.update(deployment_info)
            candidate=state/'patched-blender';candidate.write_bytes(patched);shutil.copymode(blender,candidate)
            data={'schema':1,'version':manifest['version'],'phase':'prepared','blender':str(blender),
                  'addon':str(addon),'original_sha256':sha256(blender),'patched_sha256':sha256(candidate),
                  'addon_inventory':inventory(staged),'previous_addon_inventory':previous,
                  'installation_mode':'experimental' if prepared else 'verified',
                  'native_component':prepared['recipe']['native_component'] if prepared else 'verified-recipe',
                  'validation':'structural shader compatibility and startup; renderer not certified' if prepared else 'verified-recipe',
                  'limitations':prepared['limitations'] if prepared else '',**runtime_info}
            write_json(state/'receipt.json',data)
            try:
                replace_file(candidate,blender)
                if addon.exists():os.replace(addon,Path(temp)/'previous')
                os.replace(staged,addon)
                data['phase']='installed';write_json(state/'receipt.json',data)
            except BaseException:
                _restore(state,data)
                raise
            finally:candidate.unlink(missing_ok=True)
    return status(state)


def remove(state):
    state=Path(state).expanduser().resolve()
    with locked(state):
        data=status(state)
        if data['phase'] in {'not-installed','removed'}:return data
        _restore(state,data)
        return status(state)
