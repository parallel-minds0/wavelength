"""Wavelength installer foundation. Deliberately refuses unsupported binary patching."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import platform

COMPILERS = ('g++', 'clang++', 'c++', 'cl.exe', 'cl')


def project_root():
    return Path(__file__).resolve().parents[2]


def discover_compilers(root=None):
    """Prefer manually bundled toolchains; fall back to host PATH.

    Bundled compiler executable candidates must live under third-party/compilers.
    Discovery does not execute any candidate; build_native invokes the selected one.
    """
    root = Path(root) if root is not None else project_root()
    bundled = root / 'third-party' / 'compilers'
    results = []
    if bundled.is_dir():
        for name in COMPILERS:
            for candidate in sorted(bundled.rglob(name)):
                if candidate.is_file() and (os.name == 'nt' or os.access(candidate, os.X_OK)):
                    results.append(str(candidate.resolve()))
    for name in COMPILERS:
        candidate = shutil.which(name)
        if candidate:
            results.append(str(Path(candidate).resolve()))
    return list(dict.fromkeys(results))


def discover_python_runtimes(root=None):
    """Find manually supplied standalone Python runtimes, without downloading any."""
    root = Path(root) if root is not None else project_root()
    folder = root / 'third-party' / 'python'
    if not folder.is_dir():
        return []
    names = ('python', 'python3', 'python.exe', 'python3.exe')
    return [str(f.resolve()) for f in sorted(folder.rglob('*'))
            if f.is_file() and f.name in names and (os.name == 'nt' or os.access(f, os.X_OK))]


def patch_compatibility(binary, manifest_path=None):
    """Return exact-hash support status; does not modify or load target binary."""
    details = inspect_blender(binary)
    manifest_path = Path(manifest_path) if manifest_path else project_root() / 'patches' / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported patch manifest schema')
    matches = [item for item in manifest.get('supported_builds', [])
               if not details['payload_inspection_required'] and item.get('sha256') == details['sha256'] and item.get('verified') is True]
    return {**details, 'patch_supported': bool(matches),
            'patch_id': matches[0].get('id') if matches else None,
            'reason': 'Inspect the extracted Blender executable, not the AppImage runtime' if details['payload_inspection_required'] else 'Exact verified binary match' if matches else 'No verified patch for this exact executable'}

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def inspect_blender(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('Blender target must be a regular file')
    with path.open('rb') as stream:
        header = stream.read(16)
    appimage = header[:4] == b'\x7fELF' and header[8:11] in (b'AI\x01', b'AI\x02')
    return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'target_kind': 'appimage-container' if appimage else 'executable-or-file',
            'payload_inspection_required': appimage}

def build_native(source_root, build_dir, compiler=None):
    """Build a loadable C++ library with a stable C ABI; no Blender patching."""
    compiler = compiler or next(iter(discover_compilers()), None)
    if not compiler:
        raise RuntimeError('No supported C++ compiler detected')
    if Path(compiler).name.lower() in ('cl', 'cl.exe'):
        raise NotImplementedError('MSVC build adapter is not implemented')
    source_root, build_dir = Path(source_root).resolve(), Path(build_dir).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == 'Windows':
        output = build_dir / 'wavelength_grid.dll'
        shared_flags = ['-shared']
    elif system == 'Darwin':
        output = build_dir / 'libwavelength_grid.dylib'
        shared_flags = ['-dynamiclib', '-fPIC']
    else:
        output = build_dir / 'libwavelength_grid.so'
        shared_flags = ['-shared', '-fPIC']
    sources = [source_root / 'src/wavelength_grid.cpp', source_root / 'src/wavelength_abi.cpp']
    command = [compiler, '-std=c++17', *shared_flags, '-DWAVELENGTH_NATIVE_BUILD',
               *map(str, sources), '-I', str(source_root / 'include'), '-o', str(output)]
    subprocess.run(command, check=True)
    return output

def install_addon(addon_zip, scripts_addons, *, overwrite=False):
    """Install Python package to an explicit Blender scripts/addons directory.

    Requires user-provided destination; does not silently pick a Blender version.
    """
    destination = Path(scripts_addons).expanduser().resolve()
    if not destination.is_dir():
        raise ValueError('Add-on directory must already exist')
    package = destination / 'wavelength'
    if package.exists():
        if not overwrite: raise FileExistsError(f'{package} exists; refusing overwrite')
        raise NotImplementedError('Existing add-on replacement requires transactional backup')
    with zipfile.ZipFile(addon_zip) as z:
        entries = [i for i in z.infolist() if not i.is_dir()]
        for i in entries:
            p = Path(i.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] != 'wavelength':
                raise ValueError(f'Unsafe archive entry: {i.filename}')
        if not any(i.filename == 'wavelength/__init__.py' for i in entries):
            raise ValueError('Archive does not contain add-on root')
        package.mkdir()
        try:
            for i in entries:
                target = destination / i.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(i))
        except BaseException:
            shutil.rmtree(package)
            raise
    return package

def patch_blender(*args, **kwargs):
    raise NotImplementedError('No validated Blender 5.2.1 binary patch or native renderer hook exists yet; refusing modification')
