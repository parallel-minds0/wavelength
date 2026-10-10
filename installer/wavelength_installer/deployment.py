"""Prepare experimental payloads in isolation; Python owns deployment."""
from contextlib import contextmanager
from pathlib import Path
import os,shlex,shutil,subprocess,tempfile,uuid
from .core import inspect_blender,sha256
from .experimental import generate,analyze,LIMITATIONS

@contextmanager
def _prepare(blender):
    with tempfile.TemporaryDirectory(prefix='wl-native-') as folder:
        folder=Path(folder)
        runtime=None
        if inspect_blender(blender)['payload_inspection_required']:
            # Run only the user-selected executable, in a private staging directory.
            with (folder/'extract.log').open('w+') as log:
                try:
                    subprocess.run([str(blender),'--appimage-extract'],cwd=folder,stdout=log,stderr=log,check=True,timeout=180)
                except (subprocess.SubprocessError,OSError) as exc:
                    raise ValueError('AppImage extraction failed; use a supported extracted Blender directory. Nothing installed.') from exc
            runtime=folder/'squashfs-root'
            payload=runtime/'blender'
            if not payload.is_file() or payload.is_symlink() or not (runtime/'AppRun').is_file():
                raise ValueError('Unsupported AppImage layout: expected blender and AppRun at payload root')
            for item in runtime.rglob('*'):
                if item.is_symlink() and not item.resolve().is_relative_to(runtime.resolve()):
                    raise ValueError('AppImage contains an external symlink; refusing deployment')
        else:payload=blender
        analysis=analyze(payload.read_bytes())
        recipe,patched=generate(payload.read_bytes())
        # Structural compatibility is established here. This is not renderer certification.
        if runtime:
            payload.write_bytes(patched)
        # A structurally patchable payload must also start successfully with its resources.
        probe=None
        try:
            if runtime:command=runtime/'AppRun'
            elif recipe is None:command=blender
            else:
                fd,path=tempfile.mkstemp(prefix='.wl-probe-',dir=blender.parent)
                os.close(fd);probe=Path(path);probe.write_bytes(patched);shutil.copymode(blender,probe);command=probe
            _startup_probe(command,folder/'startup.log')
        finally:
            if probe:probe.unlink(missing_ok=True)
        yield {'recipe':recipe,'patched':patched,'runtime':runtime,'limitations':LIMITATIONS,'native_state':'available','action':analysis['action'],'analysis':{k:v for k,v in analysis.items() if k!='changes'}}


def _startup_probe(command,log_path):
    with Path(log_path).open('w+') as log:
        try:
            subprocess.run([str(command),'--background','--factory-startup','--python-exit-code','19',
                            '--python-expr','import bpy; print("WL_NATIVE_STARTUP_OK")'],
                           stdout=log,stderr=log,timeout=60,check=True)
        except (subprocess.SubprocessError,OSError) as exc:
            log.seek(0)
            raise ValueError('Patched Blender startup failed. '+log.read()[-2000:]) from exc
        log.seek(0)
        if 'WL_NATIVE_STARTUP_OK' not in log.read():raise ValueError('Patched executable did not confirm Blender startup')


def stage_runtime(prepared,state):
    """Keep AppImage resources together; replace host path with reversible launcher."""
    destination=state/('runtime-'+uuid.uuid4().hex)
    shutil.copytree(prepared['runtime'],destination,symlinks=True)
    app=destination/'AppRun'
    launcher=('#!/bin/sh\n# Wavelength experimental AppImage deployment; remove through installer.\n'
              'export WL_EXPERIMENTAL_GRID=1\nexec '+shlex.quote(str(app))+' "$@"\n').encode()
    from .management import tree_snapshot
    return launcher,{'runtime_inventory':tree_snapshot(destination),'runtime_dir':str(destination),'runtime_payload_sha256':sha256(destination/'blender'),
                     'runtime_launcher_sha256':sha256(app)}


@contextmanager
def prepare(blender, strict=True):
    # Catch preparation failures only, never exceptions from the caller's transaction.
    from contextlib import ExitStack
    with ExitStack() as stack:
        try:
            prepared=stack.enter_context(_prepare(Path(blender)))
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            if strict:
                from .lifecycle import NativeRequiredError
                raise NativeRequiredError(str(exc)) from exc
            prepared={'native_state':'unavailable','action':'unavailable','reason':str(exc),
                      'recipe':None,'patched':None,'runtime':None,'limitations':LIMITATIONS}
        yield prepared
