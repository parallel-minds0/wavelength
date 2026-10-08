#!/usr/bin/env python3
"""Validate/package by default; --publish commits, tags and atomically pushes this repo."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
REMOTE='https://github.com/parallel-minds0/wavelength.git'

def run(*args, capture=False):
    return subprocess.run(args,cwd=ROOT,check=True,text=True,
                          stdout=subprocess.PIPE if capture else None).stdout

def version():
    tree=ast.parse((ROOT/'addon/wavelength/__init__.py').read_text())
    info=next(ast.literal_eval(n.value) for n in tree.body
              if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bl_info' for t in n.targets))
    return '.'.join(map(str,info['version']))+'-pre.alpha'

def package():
    destination=ROOT/'dist'/f'wavelength-addon-v{version()}.zip'
    destination.parent.mkdir(exist_ok=True)
    source=ROOT/'addon/wavelength'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob('*')):
            relative=file.relative_to(source)
            if not file.is_file() or any(part.startswith('.') or part in {'dev','third-party','__pycache__'} for part in relative.parts):continue
            if file.suffix not in {'.py','.md','.svg','.map'} and file.name!='LICENSE':continue
            archive.write(file,Path('wavelength')/relative)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip():raise RuntimeError('Invalid package')
    print(destination)
    return destination

def validate():
    for relative in ('__init__.py','pipeline.py','toolchains.py'):
        if not (ROOT/'addon/wavelength/source/build'/relative).is_file():
            raise RuntimeError(f'Missing build package source: {relative}')
    for base in ('addon','installer','tools','tests'):
        for file in (ROOT/base).rglob('*.py'):ast.parse(file.read_text(),filename=str(file))
    run(sys.executable,'-m','unittest','discover','-s','tests','-v')
    run(sys.executable,'installer/cli.py','build-native')
    package()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    validate()
    if not args.publish:return
    if Path(run('git','rev-parse','--show-toplevel',capture=True).strip()).resolve()!=ROOT:
        raise RuntimeError('Wrong Git root; refusing to stage outside native workspace')
    if run('git','remote','get-url','origin',capture=True).strip()!=REMOTE:
        raise RuntimeError('Unexpected publication remote')
    branch=run('git','branch','--show-current',capture=True).strip()
    if not branch:raise RuntimeError('Cannot publish a detached HEAD')
    tag='v'+version()
    run('git','fetch','origin',branch,'--tags')
    if tag in run('git','tag','--list',tag,capture=True).splitlines():
        raise RuntimeError('Version tag already exists; bump version before publishing')
    run('git','merge-base','--is-ancestor',f'origin/{branch}','HEAD')
    for file in (ROOT/'addon/wavelength/source').rglob('*.py'):
        result=subprocess.run(['git','check-ignore','--quiet',str(file.relative_to(ROOT))],cwd=ROOT)
        if result.returncode==0:raise RuntimeError(f'Python source excluded by Git ignore: {file}')
        if result.returncode!=1:raise RuntimeError('Git ignore check failed')
    run('git','add','-A','--','.')
    # The exact repository boundary was verified above; nested repos are forbidden.
    staged=run('git','ls-files','--stage',capture=True)
    if any(line.startswith('160000 ') for line in staged.splitlines()):
        raise RuntimeError('Nested repository would omit source from release')
    changes=run('git','diff','--cached','--name-only',capture=True).strip()
    if changes:run('git','commit','-m',f'Release {tag}: native workspace and Blender integration research')
    run('git','tag','-a',tag,'-m',f'Wavelength {tag}; native renderer integration remains experimental and unimplemented')
    run('git','push','--atomic','origin',f'HEAD:refs/heads/{branch}',f'refs/tags/{tag}')
    print(json.dumps({'published_tag':tag,'commit':run('git','rev-parse','HEAD',capture=True).strip()}))

if __name__=='__main__':main()
