"""Source 1 toolchain boundaries; runtime platform is separate from compiler host."""
from pathlib import Path
import os,struct

def defaults(platform):
    bases=[Path.home()/'.local/share/Steam/steamapps/common',Path.home()/'.steam/steam/steamapps/common']
    if os.name=='nt':bases.insert(0,Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam/steamapps/common')
    for base in bases:
        root=base/'Half-Life 2'
        if (root/'hl2/gameinfo.txt').is_file():
            candidates=[root/'bin',root/'bin/linux64',root/'bin/x64',Path(__file__).resolve().parents[4]/'bin/source-tools-plusplus/tools++_linux']
            if os.environ.get('WAVELENGTH_SOURCE_TOOLS'):candidates.insert(0,Path(os.environ['WAVELENGTH_SOURCE_TOOLS']))
            tool=next((d for d in candidates if any((d/n).is_file() for n in ('vbsp','vbsp_linux','vbsp++','vbsp.exe'))),root/'bin')
            definition=next((p for p in (root/'bin/halflife2.fgd',root/'bin/x64/halflife2.fgd') if p.is_file()),None)
            game=root/'hl2_complete' if (root/'hl2_complete/gameinfo.txt').is_file() else root/'hl2'
            return {'game_dir':str(game),'compiler_dir':str(tool),'fgd_path':str(definition) if definition else '',
                    'launch_args':'["-console", "-dev", "-game", "{game_dir}", "+map", "{map}"]'}
    return {'launch_args':'["-console", "-dev", "-game", "{game_dir}", "+map", "{map}"]'}

def compiler_args(stage,game_dir,map_name="level"):
    validate_map_name(map_name)
    directory=Path(game_dir)
    if not (directory/'gameinfo.txt').is_file():raise ValueError('Source game directory must contain gameinfo.txt')
    # Relative map paths work for native tools and Wine. Z: maps host absolute paths.
    return ['-game',str(directory),map_name+('.vmf' if stage=='vbsp' else '.bsp')]

def validate_bsp(data):
    if len(data)<1036 or data[:4]!=b'VBSP':raise ValueError('Expected a Source VBSP header')
    if struct.unpack_from('<i',data,4)[0]!=20:raise ValueError('Expected Half-Life 2 BSP version 20')
    for i in range(64):
        offset,length=struct.unpack_from('<ii',data,8+16*i)
        if offset<0 or length<0 or (length and (offset<1036 or offset+length>len(data))):raise ValueError('Invalid Source BSP lump bounds')


def runtime_game(directory):
    """Current HL2 installs use the combined game DLL and mounted episode assets."""
    directory=Path(directory)
    combined=directory.parent/'hl2_complete'
    if directory.name=='hl2' and (combined/'gameinfo.txt').is_file():return combined
    return directory


def validate_map_name(value):
    """The name must survive Linux paths, Source commands and embedded BSP assets."""
    import re
    if not re.fullmatch(r'[a-z0-9_-]+',value):
        raise ValueError('Source map name must use lowercase letters, numbers, underscores or hyphens')
    return value


def validate_map_assets(data, name):
    """Catch renamed compiled maps without rewriting their embedded resources."""
    import io,zipfile
    validate_bsp(data);validate_map_name(name)
    offset,size=struct.unpack_from('<ii',data,8+16*40)
    if not size:return
    try:
        with zipfile.ZipFile(io.BytesIO(data[offset:offset+size])) as archive:
            for entry in archive.infolist():
                parts=entry.filename.replace('\\','/').lower().split('/')
                if len(parts)>=4 and parts[:2]==['materials','maps'] and parts[-1].startswith('cubemapdefault') and parts[2]!=name:
                    raise ValueError(f"BSP contains embedded assets for '{parts[2]}', but is named '{name}'. Rebuild with this output filename; do not rename the compiled BSP.")
    except zipfile.BadZipFile as exc:raise ValueError('Invalid embedded BSP asset archive; rebuild the map') from exc
