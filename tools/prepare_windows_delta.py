#!/usr/bin/env python3
"""Generate a Windows native patch; do not execute Blender or test injection."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    args=parser.parse_args()
    folder=ROOT/'build/windows-original'
    folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'blender.zip'
    with urllib.request.urlopen('https://download.blender.org/release/Blender5.2/blender-5.2.2-windows-x64.zip',timeout=120) as src,archive.open('wb') as dst:
        shutil.copyfileobj(src,dst)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!='3849d17a682cba006075aaa3f3597ecb5c9c30ec31035b2e092c53e40679b535':
        raise SystemExit('Official Blender archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        matches=[name for name in z.namelist() if name.endswith('/blender.exe')]
        if len(matches)!=1:raise SystemExit('Unexpected Blender archive layout')
        original=folder/'blender.exe';original.write_bytes(z.read(matches[0]))
    candidates=list(args.build.glob('bin/blender.exe'))+list(args.build.glob('bin/Release/blender.exe'))
    if len(candidates)!=1:raise SystemExit('Cannot locate internally compiled executable')
    subprocess.run([sys.executable,str(ROOT/'tools/make_binary_patch.py'),'--original',str(original),'--patched',str(candidates[0]),'--platform','windows-x86_64','--output',str(ROOT/'build/windows-patch')],check=True)

if __name__=='__main__': main()
