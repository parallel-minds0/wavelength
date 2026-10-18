"""Real header drawing, debounced typing and applied texture preview."""
import bpy,sys,time,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,profile_ui,external_library as library,asset_search
out=ROOT/'build/asset-search';out.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(out);bpy.context.preferences.view.show_splash=False
wavelength.register()
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
stage=0;target=None;started=0;index=0;changes=[];last='';beats=0;query='brickwall001a';deadline=0
def heartbeat():
    global beats
    beats+=1;return .02
def tick():
    global stage,target,started,index,last,deadline
    try:
        if stage==0:
            target=workspace.ensure(bpy.context);bpy.context.window.workspace=target;stage=1;return 1
        if stage==1:
            if bpy.context.workspace!=target:bpy.context.window.workspace=target;return 1
            profile_ui.apply(bpy.context,profile);started=time.monotonic();stage=2;return .5
        area=next(a for a in bpy.context.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
        params=area.spaces.active.params
        region=next(r for r in area.regions if r.type=='WINDOW')
        if stage==2:
            assert time.monotonic()-started<60
            if library._job:return .5
            assert params.import_method=='APPEND',params.import_method
            with bpy.context.temp_override(area=area,region=region):
                bpy.ops.file.select_all(action='SELECT')
                if len(bpy.context.selected_assets)<library.status()[0]:return .5
            assert params.filter_search==''
            bpy.app.timers.register(heartbeat);stage=3;return .03
        if stage==3:
            if params.filter_search!=last:
                changes.append(params.filter_search);last=params.filter_search
            if index<len(query):
                index+=1
                with bpy.context.temp_override(area=area,region=region):asset_search.ensure(area).query=query[:index]
                assert params.filter_search=='','Filter ran during typing'
                return .03
            if asset_search._pending:return .03
            assert changes==[query],changes
            assert beats>=10,beats
            assert not bpy.app.timers.is_registered(asset_search.apply_pending)
            # Exercise a real data update on a plain mesh, then view its shader.
            with bpy.data.libraries.load(str(next(library._root.glob('textures-*.blend'))),link=False) as (available,requested):
                requested.materials=[next(n for n in available.materials if 'brickwall001a' in n)]
            mat=requested.materials[0];obj=bpy.context.object
            obj.data.materials.clear();obj.data.materials.append(mat);obj.update_tag();bpy.context.view_layer.update()
            assert mat.get('wl_realized') and obj.data.uv_layers.get('wavelength')
            view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
            view.spaces.active.shading.type='MATERIAL'
            stage=4;deadline=time.monotonic()+5;return .5
        if stage==4:
            if time.monotonic()<deadline:return .5
            bpy.ops.screen.screenshot(filepath=str(out/'search-and-drop.png'))
            result={'passed':True,'typed_characters':len(query),'native_filter_changes':changes,'heartbeat_ticks':beats}
            (out/'result.json').write_text(json.dumps(result));print('PASS SEARCH AND DROP UI',result,flush=True)
            wavelength.unregister();bpy.ops.wm.quit_blender();return None
    except Exception:
        (out/'result.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc()}));traceback.print_exc()
        wavelength.unregister();bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=2)
