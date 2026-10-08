"""Source 1 toolchain boundaries; runtime platform is separate from compiler host."""
from pathlib import Path
import os,struct

def defaults(platform):
    bases=[Path.home()/'.local/share/Steam/steamapps/common',Path.home()/'.steam/steam/steamapps/common']
    if os.name=='nt':bases.insert(0,Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam/steamapps/common')
    for base in bases:
        root=base/'Half-Life 2'
        if (root/'hl2/gameinfo.txt').is_file():
            tool=next((d for d in (root/'bin',root/'bin/linux64',root/'bin/x64') if (d/'vbsp').is_file() or (d/'vbsp.exe').is_file()),root/'bin')
            definition=next((p for p in (root/'bin/halflife2.fgd',root/'bin/x64/halflife2.fgd') if p.is_file()),None)
            return {'game_dir':str(root/'hl2'),'compiler_dir':str(tool),'fgd_path':str(definition) if definition else '',
                    'launch_args':'["-console", "-dev", "-game", "{game_dir}", "+map", "{map}"]'}
    return {'launch_args':'["-console", "-dev", "-game", "{game_dir}", "+map", "{map}"]'}

def compiler_args(stage,game_dir):
    directory=Path(game_dir)
    if not (directory/'gameinfo.txt').is_file():raise ValueError('Source game directory must contain gameinfo.txt')
    # Relative map paths work for native tools and Wine. Z: maps host absolute paths.
    return ['-game',str(directory),'level.vmf' if stage=='vbsp' else 'level.bsp']

def validate_bsp(data):
    if len(data)<1036 or data[:4]!=b'VBSP':raise ValueError('Expected a Source VBSP header')
    if struct.unpack_from('<i',data,4)[0]!=20:raise ValueError('Expected Half-Life 2 BSP version 20')
    for i in range(64):
        offset,length=struct.unpack_from('<ii',data,8+16*i)
        if offset<0 or length<0 or (length and (offset<1036 or offset+length>len(data))):raise ValueError('Invalid Source BSP lump bounds')
