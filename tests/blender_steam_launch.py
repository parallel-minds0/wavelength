"""Verify Windows Steam launch arguments without starting the game."""
import bpy,sys,tempfile,struct,json
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import textures,ui
from wavelength.source.launcher import find_steam
wavelength.register()
bpy.context.workspace['wl_workspace']=True
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);game=root/'hl2';game.mkdir();(game/'gameinfo.txt').write_text('GameInfo {}')
    bsp=root/'launch_test.bsp';data=bytearray(1036);data[:4]=b'VBSP';struct.pack_into('<i',data,4,20);bsp.write_bytes(data)
    s=bpy.context.scene.wavelength
    with patch.object(textures,'refresh'):s.engine='source_hl2_windows'
    s.game_dir=str(game);s.map_name='launch_test';s.last_build=str(bsp)
    s.launch_args=json.dumps(['-console','-dev','-game','{game_dir}','+map','{map}'])
    preview=root/'launch_test_preview.bsp'
    preview.write_bytes(data)
    s.last_preview_build=str(preview)
    original_args=s.launch_args
    s.launch_args='invalid launch configuration'
    with patch.object(ui.subprocess,'Popen') as launch:
        assert bpy.ops.wavelength.deploy_bsp(preview=True)=={'FINISHED'}
        assert not (game/'maps'/bsp.name).exists()
        assert bpy.ops.wavelength.deploy_bsp()=={'FINISHED'}
        launch.assert_not_called()
    assert (game/'maps'/preview.name).read_bytes()==bytes(data)
    assert (game/'maps'/bsp.name).read_bytes()==bytes(data)
    assert s.last_build==str(bsp) and s.last_preview_build==str(preview)
    with patch.object(ui.subprocess,'Popen') as launch:
        assert bpy.ops.wavelength.deploy_bsp(verify=True)=={'FINISHED'}
        assert bpy.ops.wavelength.deploy_bsp(verify=True,preview=True)=={'FINISHED'}
        game_preview=game/'maps'/preview.name
        changed=bytearray(data)
        changed[-1]=1
        for expected in ('differs','missing'):
            if expected=='differs':
                game_preview.write_bytes(changed)
            else:
                game_preview.unlink()
            try:
                bpy.ops.wavelength.deploy_bsp(verify=True,preview=True)
            except RuntimeError as exc:
                assert expected in str(exc)
            else:
                raise AssertionError(f'Verification accepted a {expected} copy')
            if expected=='differs':
                assert game_preview.read_bytes()==changed
            else:
                assert not game_preview.exists()
        launch.assert_not_called()
    s.launch_args=original_args
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
    # Interrupt copying after a partial write to the temporary BSP.
    import shutil
    def interrupted_copy(source, target):
        target.write(source.read(16))
        raise OSError('Simulated interrupted deployment')

    deployed=game/'maps/launch_test.bsp'
    deployed.write_bytes(b'previous map')
    with patch.object(shutil,'copyfileobj',side_effect=interrupted_copy), patch.object(ui.subprocess,'Popen') as launch:
        try:
            bpy.ops.wavelength.launch()
        except RuntimeError as exc:
            assert 'Simulated interrupted deployment' in str(exc)
        else:
            raise AssertionError('Interrupted deployment accepted')
        launch.assert_not_called()
    assert deployed.read_bytes()==b'previous map'
    assert list(deployed.parent.iterdir())==[deployed]
    combined=root/'hl2_complete'
    combined.mkdir()
    (combined/'gameinfo.txt').write_text('GameInfo {}')
    layout=Mock()
    row=layout.row.return_value
    ui.draw_game_maps_folder(layout,str(game))
    assert row.enabled is False
    assert not (combined/'maps').exists()
    (combined/'maps').mkdir()
    ui.draw_game_maps_folder(layout,str(game))
    assert row.enabled is True
    row.operator.assert_called_with('wm.path_open',text='Open Game Maps Folder',icon='FILE_FOLDER')
    assert row.operator.return_value.filepath==str(combined/'maps')
    ui.draw_game_maps_folder(layout,'')
    assert row.enabled is False
wavelength.unregister()
print('PASS WINDOWS STEAM LAUNCH: configured/registry discovery without PATH; App ID 220, game/map arguments, BSP deployment')
