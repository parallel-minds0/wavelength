"""Local discovery without executing candidate applications."""
from pathlib import Path
import os
import re
import shutil
from .lifecycle import read_receipt


def discover(blender=None, addons=None, state=None):
    old=read_receipt(state) if state else {}
    if blender is None:
        candidates=[]
        if old.get('blender'):candidates.append(Path(old['blender']))
        candidates+=sorted((Path.home()/'Applications').glob('blender-*/blender'),key=lambda p:tuple(map(int,re.findall(r'\d+',p.parent.name))),reverse=True)
        candidates.append(Path.home()/'Applications/blender/blender')
        if os.name == 'nt':
            programs = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files'))
            candidates += sorted((programs/'Blender Foundation').glob('Blender */blender.exe'), reverse=True)
        executable=shutil.which('blender')
        if executable:candidates.append(Path(executable))
        blender=next((p for p in candidates if p.is_file()),None)
        if blender is None:raise ValueError('Blender was not found; provide --blender and --addons')
    blender=Path(blender).expanduser().resolve()
    if blender.is_dir():
        blender = blender / ('blender.exe' if os.name == 'nt' else 'blender')
    if addons is None:
        if old.get('blender')==str(blender) and old.get('addon'):
            addons=Path(old['addon']).parent
        else:
            versions=[p.name for p in blender.parent.iterdir() if p.is_dir() and re.fullmatch(r'\d+\.\d+',p.name)] if blender.parent.is_dir() else []
            match=re.search(r'blender-(\d+\.\d+)',str(blender))
            version=max(versions,key=lambda s:tuple(map(int,s.split('.')))) if versions else (match[1] if match else None)
            if not version:raise ValueError('Cannot determine Blender version; provide --addons')
            if os.name == 'nt':
                addons = Path(os.environ.get('APPDATA', str(Path.home()/'AppData/Roaming')))/'Blender Foundation/Blender'/version/'scripts/addons'
            else:
                addons=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'blender'/version/'scripts/addons'
    return blender,Path(addons).expanduser().resolve()
