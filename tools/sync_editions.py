#!/usr/bin/env python3
"""Copy explicitly shared source, detect drift, and preserve Pro extensions.

No runtime dependency, symlink, submodule, game assets or build outputs are used.
"""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHARED=('addon','installer','native','patches','tools','tests','docs','documentation','third-party','.github')
FILES=('LICENSE','README.md','.gitignore','wavelength-installer')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def source_files(root):
    for item in (*SHARED,*FILES):
        path=root/item
        paths=path.rglob('*') if path.is_dir() else [path]
        for file in paths:
            if file.is_file() and not any(p in {'__pycache__','.git','dev','pro'} for p in file.relative_to(root).parts) and file.suffix!='.pyc' and file.name!='experimental-grid.json':yield file

def sync(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if source==target or source in target.parents:raise ValueError('Use a separate sibling source tree')
    state=target/'.wavelength-shared.json';prior=json.loads(state.read_text()) if state.exists() else {}
    files={str(p.relative_to(source)):p for p in source_files(source)}
    conflicts=[]
    for name,path in files.items():
        dest=target/name
        if dest.exists() and digest(dest)!=digest(path) and (name not in prior or digest(dest)!=prior[name]):conflicts.append(name)
    for name in set(prior)-set(files):
        dest=target/name
        if dest.exists() and digest(dest)!=prior[name]:conflicts.append(name)
    if conflicts:raise ValueError('Resolve shared-code drift before syncing: '+', '.join(conflicts))
    target.mkdir(parents=True,exist_ok=True)
    for name,path in files.items():
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    for name in set(prior)-set(files):
        dest=target/name
        if dest.is_file():dest.unlink() # Only tracked, unchanged shared files.
    state.write_text(json.dumps({name:digest(path) for name,path in files.items()},indent=2,sort_keys=True))
    (target/'edition.json').write_text(json.dumps({'edition':'pro','schema':1,'shared_version':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()},indent=2))
    return len(files)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('target',type=Path);a=p.parse_args();print('Shared files synchronized:',sync(ROOT,a.target))
