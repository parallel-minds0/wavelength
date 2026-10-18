"""Native external asset-library integration; no catalog materials in the map."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import bpy

FIELDS = ('engine', 'game_dir', 'wad_path', 'texture_wads', 'palette_path')
_job = None
_key = None
_root = None
_owner = None
_status = {}
_last_shards = -1
_refresh_at = 0
_cleanups = []
_completed = set()
_display_name = 'Textures'


def snapshot(settings):
    values = {name: getattr(settings, name) for name in FIELDS}
    for name in ('game_dir', 'wad_path', 'palette_path'):
        if values[name]:
            values[name] = str(Path(bpy.path.abspath(values[name])).resolve())
    values['texture_wads'] = json.dumps([str(Path(bpy.path.abspath(p)).resolve())
                                       for p in json.loads(values['texture_wads'] or '[]')])
    values['project_dir'] = ''
    return values


def cache_root(values):
    key = hashlib.sha256(json.dumps([1, bpy.app.version[:2], values], sort_keys=True).encode()).hexdigest()[:24]
    base = Path(bpy.utils.user_resource('CONFIG')) / 'wavelength' / 'asset-libraries'
    return key, base / key


def library_name():
    return 'Wavelength: ' + _display_name


def register_library():
    if _root is None:
        return
    libraries = bpy.context.preferences.filepaths.asset_libraries
    library = next((lib for lib in libraries if Path(lib.path) == _root), None)
    if library is None:
        library = libraries.new(name=library_name(), directory=str(_root))
    elif library.name != library_name():
        library.name = library_name()
    return library


def reference():
    library = register_library()
    return library.name if library else 'LOCAL'


def status():
    return (_status.get('ready', 0), _status.get('total', 0), _job is not None)


def label():
    if _status.get('state') == 'FAILED':
        return 'Texture library failed: ' + _status.get('error', 'see worker log')[:80]
    ready, total, loading = status()
    skipped = _status.get('skipped', 0)
    if loading:
        return f'{ready}/{total} cached, {skipped} skipped (background)'
    return f'{ready} cached, {skipped} skipped'


def cached_names(settings, search=''):
    _, root = cache_root(snapshot(settings))
    try:
        names = json.loads((root / 'index.json').read_text(encoding='utf-8'))['names']
    except (OSError, ValueError, KeyError):
        return []
    needle = search.casefold()
    return [name for name in names if needle in name.casefold()]


def schedule(context=None, settings=None, force=False):
    global _job, _key, _root, _owner, _status, _last_shards, _refresh_at, _display_name
    scene = getattr(context, 'scene', None) or bpy.context.scene
    settings = settings or scene.wavelength
    if settings.engine == 'blender':
        stop()
        return
    values = snapshot(settings)
    from . import profiles
    _display_name = getattr(settings, 'profile_name', '') or profiles.get(settings.engine)['label']
    key, root = cache_root(values)
    if key == _key:
        if _job is not None or (key in _completed and not force):
            return
    stop()
    _key, _root, _owner = key, root, scene
    root.mkdir(parents=True, exist_ok=True)
    try:
        _status = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))['status']
    except (OSError, ValueError, KeyError):
        _status = dict(state='STARTING', ready=0, total=0, skipped=0, shards=0)
    register_library()
    from .asset_browser import TEXTURES_CATALOG_ID
    (root / 'blender_assets.cats.txt').write_text(
        f'VERSION 1\n\n{TEXTURES_CATALOG_ID}:Wavelength/Textures:Textures\n', encoding='utf-8')
    request_path = root / 'request.json'
    request_path.write_text(json.dumps({'root': str(root), 'settings': values}), encoding='utf-8')
    args = [bpy.app.binary_path, '--background', '--factory-startup', '--disable-autoexec', '--threads', '1', '--python-exit-code', '1',
            '--python', str(Path(__file__).with_name('library_worker.py')), '--', str(request_path)]
    options = {}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    with (root / 'worker.log').open('w', encoding='utf-8') as log:
        _job = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, **options)
    _last_shards = _status.get('shards', 0)
    _refresh_at = time.monotonic()
    # Migrate old in-map thumbnails in bounded batches; keep every used/custom material.
    _cleanups.clear()
    for mat in bpy.data.materials:
        if mat.get('wl_asset_profile') and mat.get('wl_texture') and not mat.get('wl_realized'):
            _cleanups.append(mat)
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=.5)


def refresh_browsers():
    from . import workspace
    from .entity import browser
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if not workspace.active():
                continue
            for area in window.screen.areas:
                if area.type == 'FILE_BROWSER' and area.ui_type == 'ASSETS':
                    browser._configure_asset_area(area, window.scene.wavelength.asset_browser_section)
                    if window.scene.wavelength.asset_browser_section == 'TEXTURES':
                        with bpy.context.temp_override(area=area):
                            bpy.ops.asset.library_refresh()


def tick():
    global _job, _status, _last_shards, _refresh_at
    started = time.monotonic()
    while _cleanups and time.monotonic() - started < .004:
        mat = _cleanups.pop()
        try:
            if mat.users <= int(mat.use_fake_user) and not mat.get('wl_realized'):
                nodes = mat.node_tree.nodes if mat.node_tree else []
                if all(n.type in {'BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'} for n in nodes):
                    bpy.data.materials.remove(mat)
        except ReferenceError:
            pass
    if _job is None:
        return .5 if _cleanups else None
    try:
        progress = json.loads((_root / 'progress.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        progress = _status
    finished = _job.poll() is not None
    if finished and (_job.returncode != 0 or progress.get('state') != 'DONE'):
        progress = {**progress, 'state': 'FAILED', 'error': progress.get('error', 'See ' + str(_root / 'worker.log'))}
    changed = progress != _status
    _status = progress
    if _owner and hasattr(_owner, 'wavelength'):
        total = progress.get('total', 0)
        if _owner.wavelength.texture_count != total:
            _owner.wavelength.texture_count = total
    shards = progress.get('shards', 0)
    if finished or (shards != _last_shards and time.monotonic() - _refresh_at >= 3):
        refresh_browsers()
        _last_shards, _refresh_at = shards, time.monotonic()
    elif changed:
        from .asset_browser import _tag_asset_browsers_redraw
        _tag_asset_browsers_redraw()
    if finished:
        if progress.get('state') == 'DONE':
            _completed.add(_key)
        _job = None
    return .5 if _job or _cleanups else None


def stop():
    global _job
    if _job is not None:
        if _job.poll() is None:
            _job.terminate()
            try:
                _job.wait(timeout=.25)
            except subprocess.TimeoutExpired:
                _job.kill()
        _job = None
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    _cleanups.clear()


def unregister():
    global _key, _root, _owner, _status
    stop()
    _key = _root = _owner = None
    _status = {}
    _completed.clear()
