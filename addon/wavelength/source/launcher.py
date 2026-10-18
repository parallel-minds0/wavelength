"""Locate the Steam client without requiring Windows users to edit PATH."""
import os
from pathlib import Path
import shutil


def registry_paths():
    if os.name!='nt':return []
    import winreg
    found=[]
    for hive,key,names in (
        (winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam',('SteamExe','SteamPath')),
        (winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Valve\Steam',('InstallPath',)),
        (winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam',('InstallPath',)),
    ):
        try:
            with winreg.OpenKey(hive,key) as handle:
                for name in names:
                    try:found.append(winreg.QueryValueEx(handle,name)[0])
                    except OSError:pass
        except OSError:pass
    return found


def find_steam(configured='',game_dir=''):
    candidates=[]
    if configured:
        path=Path(configured)
        if path.stem.casefold()=='steam' or path.is_dir():candidates.append(path)
    candidates.extend(Path(p) for p in registry_paths() if isinstance(p,str) and p)
    candidates.extend(Path(p) for name in ('steam','steam.exe') if (p:=shutil.which(name)))
    if os.name=='nt':
        candidates.extend(Path(os.environ.get(name,default))/'Steam' for name,default in (
            ('PROGRAMFILES(X86)','C:/Program Files (x86)'),('PROGRAMFILES','C:/Program Files')))
    if game_dir:
        candidates.extend(Path(game_dir).parents)
    for candidate in candidates:
        if candidate.is_dir():
            candidate=candidate/('steam.exe' if os.name=='nt' else 'steam')
        if candidate.is_file() and candidate.stem.casefold()=='steam':return str(candidate)
    raise ValueError('Steam client not found. Set Game Executable to your Steam.exe in Scene Properties > Project & Toolchain.')
