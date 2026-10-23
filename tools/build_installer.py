#!/usr/bin/env python3
"""Package platform-specific installers with pinned private Python runtimes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from release import ROOT,package,version


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform',choices=('linux-x86_64','windows-x86_64'),default='windows-x86_64' if os.name == 'nt' else 'linux-x86_64')
    args=parser.parse_args()
    lock=json.loads((ROOT/'installer/runtime-lock.json').read_text())['runtimes'][args.platform]
    windows=args.platform=='windows-x86_64'
    cache=ROOT/'build'/('python-windows.zip' if windows else 'runtime.tar.gz')
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists() or hashlib.sha256(cache.read_bytes()).hexdigest()!=lock['sha256']:
        temporary=cache.with_suffix('.download')
        try:
            with urllib.request.urlopen(lock['url'],timeout=60) as incoming,temporary.open('wb') as output:
                shutil.copyfileobj(incoming,output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=lock['sha256']:raise ValueError('Runtime SHA-256 mismatch')
            os.replace(temporary,cache)
        finally:temporary.unlink(missing_ok=True)
    # Source downloads and full installers use the same pinned native payload.
    native=ROOT/'patches/native'
    manifest=native/'manifest.json'
    if not manifest.is_file(): raise ValueError('Native patch manifest is missing')
    entries=[e for e in json.loads(manifest.read_text())['patches'] if e['platform']==args.platform]
    if not entries: raise ValueError('No native patch for this installer platform')
    for entry in entries:
        target=(native/entry['file']).resolve()
        if not target.is_relative_to(native.resolve()): raise ValueError('Invalid native patch path')
        if not target.exists():
            with urllib.request.urlopen(entry['url'],timeout=120) as incoming,target.open('wb') as output:
                shutil.copyfileobj(incoming,output)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=entry['patch_sha256']:
            raise ValueError('Native patch checksum mismatch')
    addon=package()
    name=f'wavelength-v{version()}-{args.platform}'
    output=ROOT/'dist'/(name+('.zip' if windows else '.tar.gz'))
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='bundle-') as temporary:
        bundle=Path(temporary)/name;bundle.mkdir()
        if windows:
            with zipfile.ZipFile(cache) as archive:archive.extractall(bundle/'runtime')
        else:
            with tarfile.open(cache) as archive:archive.extractall(bundle,filter='data')
            (bundle/'python').rename(bundle/'runtime')
        # Release is the full editable source tree plus the private Python runtime.
        for relative in ('addon','installer','native','patches','tools','tests','docs','documentation','third-party','.github','pro'):
            if (ROOT/relative).is_dir():
                shutil.copytree(ROOT/relative,bundle/relative,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','experimental-grid.json','dev'))
        for relative in ('LICENSE','README.md','TODO.md','.gitignore','wavelength-installer','wavelength-installer.cmd','edition.json'):
            if (ROOT/relative).is_file():shutil.copy2(ROOT/relative,bundle/relative)
        launcher=bundle/'wavelength-installer'
        launcher.chmod(0o755)
        # Cross-packaging is permitted; executing each runtime is mandatory in its CI OS.
        if windows == (os.name == 'nt'):
            interpreter=bundle/('runtime/python.exe' if windows else 'runtime/bin/python3')
            for arguments in (['--help'],['install','--help'],['status']):
                subprocess.run([str(interpreter),'-I','-B',str(bundle/'installer/entry.py'),*arguments],check=True)
        for cache_dir in bundle.rglob('__pycache__'):
            if cache_dir.relative_to(bundle).parts[0]!='runtime':shutil.rmtree(cache_dir)
        # Lightweight source download uses the same installer launcher, which
        # bootstraps the pinned runtime on first use. Never include local caches.
        source_zip=ROOT/'dist'/f'wavelength-v{version()}-{args.platform}-source.zip'
        with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(bundle.rglob('*')):
                relative=file.relative_to(bundle)
                if file.is_file() and relative.parts[0]!='runtime':archive.write(file,Path(name)/relative)
        source_zip.with_suffix('.zip.sha256').write_text(hashlib.sha256(source_zip.read_bytes()).hexdigest()+'  '+source_zip.name+'\n')
        if windows:
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(bundle.rglob('*')):
                    if file.is_file(): archive.write(file,Path(name)/file.relative_to(bundle))
        else:
            with tarfile.open(output,'w:gz') as archive:archive.add(bundle,arcname=name)
    print(output)
    output.with_suffix(output.suffix+'.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')

if __name__=='__main__':main()
