"""Verify Windows Steam launch arguments without starting the game."""
import bpy,sys,tempfile,struct,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import textures,ui
from wavelength.source.launcher import find_steam
wavelength.register()
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);game=root/'hl2';game.mkdir();(game/'gameinfo.txt').write_text('GameInfo {}')
    bsp=root/'launch_test.bsp';data=bytearray(1036);data[:4]=b'VBSP';struct.pack_into('<i',data,4,20);bsp.write_bytes(data)
    s=bpy.context.scene.wavelength
    with patch.object(textures,'refresh'):s.engine='source_hl2_windows'
    s.game_dir=str(game);s.map_name='launch_test';s.last_build=str(bsp)
    s.launch_args=json.dumps(['-console','-dev','-game','{game_dir}','+map','{map}'])
    for configured in ('',find_steam()):
        s.game_executable=configured
        with patch('shutil.which',return_value=None),patch.object(ui.subprocess,'Popen') as launch:
            assert bpy.ops.wavelength.launch()=={'FINISHED'}
            args=launch.call_args.args[0]
            assert Path(args[0]).name.lower()=='steam.exe'
            assert args[1:3]==['-applaunch','220'],args
            assert args[-2:]==['+map','launch_test'],args
            assert str(game) in args
        assert (game/'maps/launch_test.bsp').read_bytes()==bytes(data)
wavelength.unregister()
print('PASS WINDOWS STEAM LAUNCH: configured/registry discovery without PATH; App ID 220, game/map arguments, BSP deployment')
