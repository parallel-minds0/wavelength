"""Verify UI timers remain active while the native asset browser fills."""
import bpy,sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import profile_ui,asset_browser,workspace
wavelength.register();profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
out=ROOT/'build/texture-ui';out.mkdir(exist_ok=True);target=None;stage=0;beats=0;started=None;last=None;max_gap=0

def heartbeat():
 global beats,last,max_gap
 now=time.monotonic()
 if last is not None:max_gap=max(max_gap,now-last)
 last=now;beats+=1
 return .02

def tick():
 global stage,target,started,beats,last,max_gap
 try:
  if stage==0:
   target=workspace.ensure(bpy.context);bpy.context.window.workspace=target;stage=1;return 1
  if stage==1:
   if bpy.context.window.workspace!=target:bpy.context.window.workspace=target;return 1
   profile_ui.apply(bpy.context,profile);started=time.monotonic();beats=0;last=None;max_gap=0;bpy.app.timers.register(heartbeat);stage=2;return .5
  published,total,loading=asset_browser.sync_status()
  if published<160 and time.monotonic()-started<100:return .5
  assert published>=160,('Loading did not progress',published,total)
  assert beats>=25,('UI timers starved',beats)
  placeholders=[m for m in bpy.data.materials if m.get('wl_asset_profile')=='source_hl2_windows' and not m.get('wl_realized')]
  assert all(not m.node_tree or not m.node_tree.nodes for m in placeholders)
  bpy.app.timers.unregister(heartbeat)
  if bpy.app.timers.is_registered(asset_browser._auto_publish_tick):bpy.app.timers.unregister(asset_browser._auto_publish_tick)
  area=next(a for a in bpy.context.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
  assert area.spaces.active.params.asset_catalog_visibility=='ALL'
  region=next(r for r in area.regions if r.type=='WINDOW')
  with bpy.context.temp_override(area=area,region=region):
   bpy.ops.file.select_all(action='SELECT')
   visible=[a.local_id for a in bpy.context.selected_assets if isinstance(a.local_id,bpy.types.Material)]
  assert len(visible)>0,'Asset Browser still displays no material assets'
  assert any(m.preview and m.preview.image_size[0]>0 for m in visible)
  result={'passed':True,'published':published,'visible_materials':len(visible),'indexed':total,'ui_timer_ticks':beats,'max_timer_gap_seconds':round(max_gap,3),'seconds':round(time.monotonic()-started,2)}
  (out/'result.json').write_text(json.dumps(result,indent=2));bpy.ops.screen.screenshot(filepath=str(out/'browser.png'));print('PASS RESPONSIVE TEXTURE UI',result,flush=True);bpy.ops.wm.quit_blender();return None
 except Exception:
  import traceback
  (out/'result.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc()}));traceback.print_exc();bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=2)
