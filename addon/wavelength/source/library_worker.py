"""Isolated Blender process: build preview-only external material libraries."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

SCHEMA = 1


def atomic_json(path, data):
    from .library_prepare_worker import write
    write(Path(path),data)


def source_fingerprint(settings):
    """All filesystem walks happen in the worker, never the editing process."""
    from . import profiles, source_assets, textures
    paths = set()
    if profiles.is_source2(settings.engine):
        from . import source2_assets
        assets=source2_assets.library(settings.game_dir)
        paths.add(assets.game/'gameinfo.gi')
        for mount in assets.mounts:
            if isinstance(mount,source_assets.VPK):paths.add(mount.path)
            else:paths.update((mount/'materials').rglob('*.vmat'))
    elif profiles.is_source(settings.engine):
        assets = source_assets.library(settings.game_dir)
        paths.add(assets.game / 'gameinfo.txt')
        for mount in assets.mounts:
            if isinstance(mount, source_assets.VPK):
                paths.add(mount.path)
                paths.update(mount.path.parent.glob(mount.path.name.removesuffix('_dir.vpk') + '_*.vpk'))
            else:
                folder = mount / 'materials'
                if folder.is_dir():
                    paths.update(p for p in folder.rglob('*') if p.suffix.lower() in {'.vmt', '.vtf'})
    else:
        paths.update(Path(p) for p in textures.sources(settings))
        if settings.palette_path:
            paths.add(Path(settings.palette_path))
    signatures = []
    for path in sorted(paths):
        try:
            stat = path.stat()
            signatures.append((str(path), stat.st_size, stat.st_mtime_ns))
        except OSError:
            signatures.append((str(path), None, None))
    return hashlib.sha256(json.dumps([SCHEMA, signatures]).encode()).hexdigest()


def build(request):
    import bpy
    from . import textures, asset_browser
    settings = SimpleNamespace(**request['settings'])
    root = Path(request['root'])
    root.mkdir(parents=True, exist_ok=True)
    status = dict(state='INDEXING', total=0, ready=0, skipped=0, shards=0)
    def report():
        atomic_json(root / 'progress.json', status)
    report()
    fingerprint = source_fingerprint(settings)
    manifest_path = root / 'manifest.json'
    try:
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        previous = {}
    if previous.get('fingerprint') == fingerprint and all((root / name).is_file() for name in previous.get('files', [])):
        status.update(previous['status'], state='DONE', reused=True)
        report()
        return
    names = request.get('names') or textures.all_names(settings)
    if request.get('limit'):
        names = names[:request['limit']]
    atomic_json(root / 'index.json', {'names': names})
    status.update(state='BUILDING', total=len(names))
    report()
    started = last_report = time.monotonic()
    files, batch, errors = [], [], {}
    def flush():
        if not batch:
            return
        destination = root / f'textures-{len(files):04d}.blend'
        temporary = destination.with_suffix('.partial-' + str(os.getpid()))
        bpy.data.libraries.write(str(temporary), set(batch), fake_user=True, compress=True)
        temporary.replace(destination)
        files.append(destination.name)
        for material in batch:
            bpy.data.materials.remove(material)
        from . import profiles
        if profiles.is_source2(settings.engine):
            for image in list(bpy.data.images):
                if image.users==0:bpy.data.images.remove(image)
        batch.clear()
        status['shards'] = len(files)
        report()
    for name in names:
        try:
            batch.append(asset_browser.publish_material_fast(settings, name, existing_by_id={}))
            status['ready'] += 1
        except (ValueError, OSError, RuntimeError, UnicodeError) as exc:
            errors[name] = str(exc)
            status['skipped'] += 1
        if len(batch) >= (8 if settings.engine=='source2_cs2_windows' else 128):
            flush()
        if time.monotonic() - last_report >= 1:
            report()
            last_report = time.monotonic()
    flush()
    for stale in root.glob('textures-*.blend'):
        if stale.name not in files:
            stale.unlink()
    status.update(state='DONE', seconds=round(time.monotonic() - started, 3))
    atomic_json(manifest_path, {'schema': SCHEMA, 'fingerprint': fingerprint, 'files': files,
                               'status': status, 'errors': errors})
    report()


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    request = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
    try:
        from wavelength.source.library_worker import build
        build(request)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        atomic_json(Path(request['root']) / 'progress.json', {'state': 'FAILED', 'error': str(exc)})
        sys.exit(1)
