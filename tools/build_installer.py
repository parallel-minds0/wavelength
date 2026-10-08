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
    name=f'wavelength-installer-v{version()}-linux-x86_64'
    output=ROOT/'dist'/f'{name}.tar.gz'
    with tempfile.TemporaryDirectory(dir=ROOT/'build',prefix='bundle-') as temporary:
        bundle=Path(temporary)/name;bundle.mkdir()
        with tarfile.open(cache) as archive:archive.extractall(bundle,filter='data')
        (bundle/'python').rename(bundle/'runtime')
        shutil.copytree(ROOT/'installer',bundle/'installer',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copytree(ROOT/'patches',bundle/'patches')
        shutil.copy2(addon,bundle/'addon.zip')
        shutil.copy2(ROOT/'LICENSE',bundle/'LICENSE')
        shutil.copy2(ROOT/'docs/INSTALLER.md',bundle/'README.md')
        (bundle/'bundle.json').write_text(json.dumps({'schema':1,'version':version(),'addon':'addon.zip',
            'addon_sha256':hashlib.sha256(addon.read_bytes()).hexdigest(),'runtime':lock},indent=2)+'\n')
        launcher=bundle/'wavelength-installer'
        launcher.write_text('#!/bin/sh\nset -eu\nHERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$HERE/runtime/bin/python3" -I "$HERE/installer/entry.py" "$@"\n')
        launcher.chmod(0o755)
        # Hide system Python from PATH to verify use of bundled interpreter.
        subprocess.run([str(launcher),'--help'],check=True,env={**os.environ,'PATH':'/bin'})
        subprocess.run([str(launcher),'status'],check=True,env={**os.environ,'PATH':'/bin'})
        with tarfile.open(output,'w:gz') as archive:archive.add(bundle,arcname=name)
    print(output)
    output.with_suffix(output.suffix+'.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')

if __name__=='__main__':main()
