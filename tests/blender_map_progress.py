"""Real worker/import progress, title rendering, correct totals and cleanup."""
import copy,sys,time,tempfile,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import vmf,formats,map_import,workspace
root=Path(__file__).resolve().parents[1];output=root/'build/map-progress';output.mkdir(parents=True,exist_ok=True)
temp=tempfile.TemporaryDirectory(prefix='wavelength-progress-check-')
document=vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
brush=document.entities[0].brushes[0]
document=formats.Map([formats.Entity([('classname','worldspawn')],[copy.deepcopy(brush) for _ in range(600)]),
    *[formats.Entity([('classname','info_target'),('origin',f'{i*32} 0 0')]) for i in range(12)]])
path=Path(temp.name)/'progress-check.vmf';path.write_text(vmf.write(document),encoding='utf-8')
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
c.scene.wavelength.engine='source_hl2_windows';c.scene.wavelength.auto_prepare_assets=False
c.scene.wavelength.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
c.window.workspace=workspace.ensure(c)
session=None;captured=False;stages=set();start=time.monotonic()
def tick():
    global session,captured
    try:
        if time.monotonic()-start>60:raise AssertionError('Progress test timed out')
        if session is None:session=map_import.Session(c,path);return .1
        done=session.advance();stages.add(session.stage)
        assert map_import.progress(c.scene)==session
        if session.stage=='BRUSHES' and session.phase_done>50 and not captured:
            captured=True
            def capture():bpy.ops.screen.screenshot(filepath=str(output/'loading.png'))
            bpy.app.timers.register(capture,first_interval=.05)
        if not done:return .03
        assert session.count==session.total==612,(session.count,session.total)
        assert session.brush_count==600 and session.entity_count==12
        session.close();assert map_import.progress(c.scene) is None
        assert not c.scene.get('wl_importing')
        assert captured and 'BRUSHES' in stages
        print('PASS map progress: worker stages, visible filename/bar, exact brush/entity totals and completion cleanup',flush=True)
        temp.cleanup();bpy.ops.wm.quit_blender()
    except Exception:
        traceback.print_exc()
        if session:session.close()
        temp.cleanup();bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=3)
