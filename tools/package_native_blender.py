#!/usr/bin/env python3
"""Package a compiled native Blender with a session-local wavelength launcher."""
import argparse
import io
from pathlib import Path
import tarfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]


def checksum(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    path.with_suffix(path.suffix + '.sha256').write_text(f'{digest}  {path.name}\n')


def package(runtime, output):
    runtime = runtime.resolve()
    if not (runtime / 'blender').is_file():
        raise ValueError('Expected the installed build/bin directory containing blender')
    for path in runtime.rglob('*'):
        if path.is_symlink() and (not path.exists() or not path.resolve().is_relative_to(runtime)):
            raise ValueError(f'Runtime contains a broken or external symlink: {path}')
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = 'wavelength-native'
    with tarfile.open(output, 'w:gz', compresslevel=3) as archive:
        for path in sorted(runtime.iterdir()):
            if path.name in {'makesdna', 'makesrna', 'datatoc', 'datatoc_icon', 'shader_tool'}:
                continue
            archive.add(path, arcname=f'{prefix}/{path.name}')
        for path in sorted((ROOT / 'addon/wavelength').rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                archive.add(path, arcname=f'{prefix}/wavelength/addon/wavelength/{path.relative_to(ROOT / "addon/wavelength")}')
        for path in sorted((ROOT / 'native/blender').iterdir()):
            if path.is_file():
                archive.add(path, arcname=f'{prefix}/wavelength/native/{path.name}')
        archive.add(ROOT / 'LICENSE', arcname=f'{prefix}/wavelength/LICENSE')
        archive.add(ROOT / 'tools/launch_workspace.py', arcname=f'{prefix}/wavelength/tools/launch_workspace.py')
        launcher = b'#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$HERE/blender" --factory-startup --python "$HERE/wavelength/tools/launch_workspace.py" "$@"\n'
        entry = tarfile.TarInfo(f'{prefix}/Launch-wavelength')
        entry.mode = 0o755
        entry.size = len(launcher)
        archive.addfile(entry, io.BytesIO(launcher))
    checksum(output)
    return output


def source_package(source, output):
    """Include patched Blender sources and its dependency build recipes, not binaries."""
    source = source.resolve()
    if not (source / 'source/blender/draw/engines/overlay/overlay_grid.hh').is_file():
        raise ValueError('Expected the matching patched Blender source directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz', compresslevel=3) as archive:
        for path in sorted(source.iterdir()):
            if path.name in {'.git', 'lib', '__pycache__'}:
                continue
            archive.add(path, arcname=f'wavelength-native-source/blender/{path.name}')
        for path in sorted((ROOT / 'native/blender').iterdir()):
            if path.is_file():
                archive.add(path, arcname=f'wavelength-native-source/wavelength/{path.name}')
        instructions = ('The Blender tree already includes the wavelength patch.\n'
                        'See wavelength/source.json for exact upstream and dependency revisions.\n'
                        'Obtain lib/linux_x64 at the pinned revision and check out its Git LFS assets.\n'
                        'Dependency source build recipes are included in blender/build_files/build_environment.\n'
                        'Configure with cmake -S blender -B build -G Ninja -DCMAKE_BUILD_TYPE=Release\n'
                        'Then cmake --build build --parallel 4 and cmake --install build --prefix "$PWD/build/bin".\n'
                        'See wavelength/README.md for the test build limitations and grid API.\n').encode()
        entry = tarfile.TarInfo('wavelength-native-source/BUILD.txt')
        entry.size = len(instructions)
        archive.addfile(entry, io.BytesIO(instructions))
    checksum(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--source-output', type=Path)
    args = parser.parse_args()
    print(package(args.runtime, args.output))
    if args.source and args.source_output:
        print(source_package(args.source, args.source_output))
