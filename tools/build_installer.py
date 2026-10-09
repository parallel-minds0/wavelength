#!/usr/bin/env python3
"""Build the Linux installer with a pinned, bundled standalone CPython runtime."""
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
    lock=json.loads((ROOT/'installer/runtime-lock.json').read_text())
    cache=ROOT/'build/runtime.tar.gz'
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists() or hashlib.sha256(cache.read_bytes()).hexdigest()!=lock['sha256']:
        temporary=cache.with_suffix('.download')
        try:
            with urllib.request.urlopen(lock['url'],timeout=60) as incoming,temporary.open('wb') as output:
                shutil.copyfileobj(incoming,output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=lock['sha256']:raise ValueError('Runtime SHA-256 mismatch')
            os.replace(temporary,cache)
        finally:temporary.unlink(missing_ok=True)
    addon=package()
    name=f'wavelength-v{version()}-linux-x86_64'
    output=ROOT/'dist'/f'{name}.tar.gz'
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='bundle-') as temporary:
        bundle=Path(temporary)/name;bundle.mkdir()
        with tarfile.open(cache) as archive:archive.extractall(bundle,filter='data')
        (bundle/'python').rename(bundle/'runtime')
        # Release is the full editable source tree plus the private Python runtime.
        for relative in ('addon','installer','native','patches','tools','tests','docs','documentation','third-party','.github','pro'):
            if (ROOT/relative).is_dir():
                shutil.copytree(ROOT/relative,bundle/relative,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','experimental-grid.json'))
        for relative in ('LICENSE','README.md','.gitignore','wavelength-installer','edition.json'):
            if (ROOT/relative).is_file():shutil.copy2(ROOT/relative,bundle/relative)
        launcher=bundle/'wavelength-installer'
        launcher.chmod(0o755)
        # Hide system Python from PATH to verify use of bundled interpreter.
        subprocess.run([str(launcher),'--help'],check=True,env={**os.environ,'PATH':'/bin'})
        subprocess.run([str(launcher),'install','--help'],check=True,env={**os.environ,'PATH':'/bin'})
        subprocess.run([str(launcher),'status'],check=True,env={**os.environ,'PATH':'/bin'})
        for cache_dir in bundle.rglob('__pycache__'):
            if cache_dir.relative_to(bundle).parts[0]!='runtime':shutil.rmtree(cache_dir)
        # Lightweight source download uses the same installer launcher, which
        # bootstraps the pinned runtime on first use. Never include local caches.
        source_zip=ROOT/'dist'/f'wavelength-v{version()}-source.zip'
        with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(bundle.rglob('*')):
                relative=file.relative_to(bundle)
                if file.is_file() and relative.parts[0]!='runtime':archive.write(file,Path(name)/relative)
        source_zip.with_suffix('.zip.sha256').write_text(hashlib.sha256(source_zip.read_bytes()).hexdigest()+'  '+source_zip.name+'\n')
        with tarfile.open(output,'w:gz') as archive:archive.add(bundle,arcname=name)
    print(output)
    output.with_suffix(output.suffix+'.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')

if __name__=='__main__':main()
