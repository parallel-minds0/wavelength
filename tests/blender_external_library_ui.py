"""Native external browser: visible previews, on-demand apply and idle timers."""
import bpy,json,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,profile_ui,external_library as library,asset_browser
out=ROOT/'build/external-ui';out.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(out)
bpy.context.preferences.view.show_splash=False
wavelength.register()
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
target=None;stage=0;started=0;beats=0;last=None;gaps=[];baseline=0;visible_count=0
def heartbeat():
    global beats,last
    now=time.monotonic()
    if last is not None:gaps.append(now-last)
    last=now;beats+=1
    return .02
def tick():
    global target,stage,started,baseline,visible_count,last,beats
    try:
        if stage==0:
            target=workspace.ensure(bpy.context);bpy.context.window.workspace=target;stage=1;return 1
        if stage==1:
            if bpy.context.workspace!=target:bpy.context.window.workspace=target;return 1
            baseline=len(bpy.data.materials)
            profile_ui.apply(bpy.context,profile)
            started=time.monotonic();stage=2;return .5
        if stage==2:
            assert time.monotonic()-started<120,library._status
            if library._job is not None:return .5
            assert library._status['state']=='DONE',library._status
            assert len(bpy.data.materials)==baseline,'Browsing imported materials into map'
            area=next(a for a in bpy.context.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
            params=area.spaces.active.params
            assert params.asset_library_reference==library.reference(),params.asset_library_reference
            region=next(r for r in area.regions if r.type=='WINDOW')
            with bpy.context.temp_override(area=area,region=region):
                bpy.ops.file.select_all(action='SELECT')
                assets=[a for a in bpy.context.selected_assets if a.id_type=='MATERIAL']
            if len(assets)<library._status['ready']:return .5
            visible_count=len(assets)
            assert all(a.local_id is None for a in assets)
            # Filter to a real brick material so Use Asset must import just one.
            params.filter_search='brick/brickwall001a'
            stage=3;return 2
        if stage==3:
            area=next(a for a in bpy.context.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
            region=next(r for r in area.regions if r.type=='WINDOW')
            from wavelength.source import scene
            scene.mark_brush(bpy.context.object)
            with bpy.context.temp_override(area=area,region=region):
                bpy.ops.file.select_all(action='SELECT')
                selected=list(bpy.context.selected_assets)
                assert selected,'Filtered external material not visible'
                # Native select-all does not establish an active asset. Test the
                # same operator with its external AssetRepresentation override.
                from unittest.mock import patch
                from types import SimpleNamespace
                context=SimpleNamespace(asset=selected[0],scene=bpy.context.scene,
                                        selected_objects=bpy.context.selected_objects)
                result=asset_browser.WL_OT_use_asset.execute(SimpleNamespace(report=lambda *a:None),context)
                assert result=={'FINISHED'},result
            assert len(bpy.data.materials)==baseline+1
            mat=next(m for m in bpy.data.materials if m.get('wl_texture'))
            assert mat.get('wl_realized') and mat.preview.image_size[0]>0
            assert mat in list(bpy.context.object.data.materials)
            bpy.ops.screen.screenshot(filepath=str(out/'browser.png'))
            last=None;beats=0;gaps.clear();bpy.app.timers.register(heartbeat)
            started=time.monotonic();stage=4;return .1
        if stage==4:
            if time.monotonic()-started<5:
                view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
                with bpy.context.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):
                    bpy.ops.view3d.view_orbit(type='ORBITLEFT')
                return .1
            assert not bpy.app.timers.is_registered(library.tick),'Idle monitor still running'
            assert not bpy.app.timers.is_registered(asset_browser._auto_publish_tick)
            assert beats>=70,(beats,max(gaps))
            result={'passed':True,'external_assets':visible_count,'materials_before':baseline,
                    'materials_after_apply':len(bpy.data.materials),'idle_beats':beats,
                    'max_idle_gap':max(gaps),'p95_idle_gap':sorted(gaps)[int(len(gaps)*.95)]}
            (out/'result.json').write_text(json.dumps(result,indent=2));print('PASS EXTERNAL UI',result,flush=True)
            wavelength.unregister();bpy.ops.wm.quit_blender();return None
    except Exception:
        (out/'result.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc()}))
        traceback.print_exc();wavelength.unregister();bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=2)
