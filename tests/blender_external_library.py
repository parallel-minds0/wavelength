"""Full installed-game cold/warm external-library generation and map isolation."""
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import profile_ui,external_library as library,textures,asset_browser
wavelength.register()
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
out=ROOT/'build/external-library';out.mkdir(parents=True,exist_ok=True)
initial=len(bpy.data.materials)
started=time.monotonic()
with patch.object(textures,'all_names',side_effect=AssertionError('UI indexed game archives')):
    profile_ui.apply(bpy.context,profile)
apply_seconds=time.monotonic()-started
assert len(bpy.data.materials)==initial
def wait():
    timings=[];deadline=time.monotonic()+240
    while library._job is not None and time.monotonic()<deadline:
        before=time.monotonic();library.tick();timings.append(time.monotonic()-before)
        time.sleep(.2)
    assert library._job is None,'Worker timed out'
    assert library._status['state']=='DONE',library._status
    return max(timings,default=0)
max_tick=wait()
assert len(bpy.data.materials)==initial,('Catalog leaked into map',len(bpy.data.materials))
manifest=json.loads((library._root/'manifest.json').read_text())
assert manifest['status']['ready']>6000,manifest['status']
files=manifest['files'];root=library._root
with bpy.data.libraries.load(str(root/files[0]),link=False) as (available,requested):
    assert len(available.materials)==128
    requested.materials=[available.materials[0]]
material=requested.materials[0]
assert material.preview and 0<material.preview.image_size[0]<=64
assert material.asset_data and not material.get('wl_realized')
assert len(bpy.data.materials)==initial+1
textures.realize_material(bpy.context.scene.wavelength,material)
assert material.get('wl_realized') and any(n.type=='TEX_IMAGE' for n in material.node_tree.nodes)
mtimes={name:(root/name).stat().st_mtime_ns for name in files}
warm=time.monotonic();library.schedule(bpy.context,force=True);wait();warm=time.monotonic()-warm
assert library._status.get('reused')
assert mtimes=={name:(root/name).stat().st_mtime_ns for name in files}
assert not bpy.app.timers.is_registered(asset_browser._auto_publish_tick)
# The parent monitor explicitly stops; no periodic catalog refresh remains.
assert library.tick() is None
result={'passed':True,'apply_seconds':apply_seconds,'max_parent_tick_seconds':max_tick,'warm_seconds':warm,
        'materials_before':initial,'materials_after_browsing':initial,'materials_after_import':len(bpy.data.materials),
        'status':library._status,'root':str(root)}
(out/'result.json').write_text(json.dumps(result,indent=2));print('PASS EXTERNAL LIBRARY',result,flush=True)
wavelength.unregister()
