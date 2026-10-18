"""Real Blender regression: bounded full-library thumbnail loading and lazy shaders."""
import json,sys,time,ctypes,os
from pathlib import Path
from collections import deque
from unittest.mock import patch
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import asset_browser as assets,profile_ui,source_assets
wavelength.register()
s=bpy.context.scene.wavelength
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
profile_ui.apply(bpy.context,profile)
# A slow item must yield before the rest of the library is processed.
queue=assets._AUTO_QUEUE;published=assets._AUTO_PUBLISHED
assets._AUTO_QUEUE=deque(['one','two','three']);seen=[]
with patch.object(assets,'publish_material_fast',side_effect=lambda *a,**kw:seen.append(a[1])),patch.object(assets.time,'monotonic',side_effect=[0.0,0.1]):
 assert assets._publish_batch(s,24,time_budget=.025)==1
assert seen==['one'] and len(assets._AUTO_QUEUE)==2
assets._AUTO_QUEUE=queue;assets._AUTO_PUBLISHED=published
started=time.monotonic();batches=0;maximum=0;last=0
while assets._AUTO_QUEUE:
 start=time.monotonic();assets._publish_batch(s,4,time_budget=.025);maximum=max(maximum,time.monotonic()-start);batches+=1
 if assets._AUTO_PUBLISHED-last>=1000:
  print('TEXTURE PROGRESS',assets._AUTO_PUBLISHED,'/',assets._AUTO_TOTAL,flush=True);last=assets._AUTO_PUBLISHED
materials=[m for m in bpy.data.materials if m.get('wl_asset_profile')==s.engine]
thumbs=[m for m in materials if not m.get('wl_realized')]
assert len(thumbs)>5000,len(thumbs)
assert all(not m.node_tree or not m.node_tree.nodes for m in thumbs),'Thumbnail-only material allocated a shader graph'
assert len(bpy.data.images)<10,'Full-size images were eagerly created'
assert all(m.preview and m.preview.image_size[0]<=64 and m.preview.image_size[1]<=64 for m in thumbs)
# Applying an asset must still realize its real texture in the same material.
name='brick/brickwall001a';m=next(m for m in materials if m.get('wl_texture')==name)
assert source_assets.material(s,name,target_mat=m)==m
assert m.use_nodes and any(n.type=='TEX_IMAGE' and n.image for n in m.node_tree.nodes)
assert any(n.type=='OUTPUT_MATERIAL' and n.inputs['Surface'].is_linked for n in m.node_tree.nodes)
# Repeated refreshes must not duplicate the asset library.
count=len(bpy.data.materials);assets.schedule_profile_sync(bpy.context,s);assert len(bpy.data.materials)==count
peak=None
if os.name=='nt':
 from ctypes import wintypes
 class Counters(ctypes.Structure):
  _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(x,ctypes.c_size_t) for x in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
 counters=Counters();counters.cb=ctypes.sizeof(counters);get=ctypes.windll.kernel32.GetCurrentProcess;get.restype=wintypes.HANDLE
 fn=ctypes.windll.psapi.GetProcessMemoryInfo;fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];assert fn(get(),ctypes.byref(counters),counters.cb)
 peak=round(counters.PeakWorkingSetSize/2**20,1)
result={'passed':True,'indexed':assets._AUTO_TOTAL,'published':assets._AUTO_PUBLISHED,'thumbnail_materials':len(thumbs),'batches':batches,'seconds':round(time.monotonic()-started,2),'max_batch_seconds':round(maximum,3),'peak_working_set_MiB':peak,'images':len(bpy.data.images)}
output=ROOT/'build/texture-loading';output.mkdir(parents=True,exist_ok=True);(output/'result.json').write_text(json.dumps(result,indent=2));print('PASS FULL TEXTURE LOAD '+json.dumps(result),flush=True)
wavelength.unregister()
