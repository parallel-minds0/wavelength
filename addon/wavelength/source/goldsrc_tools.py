"""Discover Windows Half-Life assets and an existing compatible GoldSrc toolchain."""
import json,os,re,struct
from pathlib import Path

def defaults(search_roots=()):
    from .launcher import registry_paths
    from .wad import Wad
    from .build.toolchains import resolve_compiler
    steam=[Path(p) for p in registry_paths() if isinstance(p,str) and p]
    steam=[p.parent if p.suffix.lower()=='.exe' else p for p in steam]
    steam.append(Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam')
    libraries=list(steam)
    for root in steam:
        try:
            text=(root/'steamapps/libraryfolders.vdf').read_text(encoding='utf-8')
            libraries.extend(Path(p.replace('\\\\','\\')) for p in re.findall(r'"path"\s+"([^"]+)"',text))
        except OSError:pass
    common=[p/'steamapps/common' for p in libraries]
    install=next((p/'Half-Life' for p in common if (p/'Half-Life/hl.exe').is_file()),common[0]/'Half-Life')
    game=install/'valve';wads=[]
    for path in sorted(game.glob('*.wad'),key=lambda p:p.name.lower()):
        try:
            wad=Wad(path)
            if wad.kind==b'WAD3' and wad.entries:wads.append(str(path))
        except (OSError,ValueError,UnicodeError,struct.error):pass
    active=next((p for p in wads if Path(p).name.lower()=='halflife.wad'),wads[0] if wads else '')
    fgd=next((p/'Half-Life SDK/Hammer Editor/fgd/half-life/halflife.fgd' for p in common if (p/'Half-Life SDK/Hammer Editor/fgd/half-life/halflife.fgd').is_file()),None)
    roots=[Path.cwd(),Path(__file__).resolve(),*(Path(p) for p in search_roots if p)]
    roots=list(dict.fromkeys(p for root in roots for p in (root,*root.parents)))
    tools=[Path(os.environ['WAVELENGTH_GOLDSRC_TOOLS'])] if os.environ.get('WAVELENGTH_GOLDSRC_TOOLS') else []
    cache=Path.home()/'.cache/wavelength/goldsrc-windows-tools.json'
    try:tools.append(Path(json.loads(cache.read_text())['compiler_dir']))
    except (OSError,ValueError,KeyError,TypeError):pass
    for root in roots:
        tools.extend(root.glob('bin/sdhlt*/sdhlt*/tools/Win64'))
        tools.extend(root.glob('bin/sdhlt*/tools/Win64'))
        tools.extend([root/'bin/goldsrc',root/'tools/goldsrc'])
    compiler=''
    for tool in tools:
        try:
            for stage in ('hlcsg','hlbsp','hlvis','hlrad'):resolve_compiler(tool,stage)
            compiler=str(tool);break
        except ValueError:pass
    if compiler:
        try:
            cache.parent.mkdir(parents=True,exist_ok=True)
            cache.write_text(json.dumps({'compiler_dir':compiler}))
        except OSError:pass
    return dict(game_dir=str(game),game_executable=str(install/'hl.exe'),fgd_path=str(fgd) if fgd else '',
                compiler_dir=compiler,texture_wads=json.dumps(wads),wad_path=active,
                launch_args=json.dumps(['-console','-dev','-game','{game_dir}','+map','{map}']),map_name='wavelength_hl1_windows')
