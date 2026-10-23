"""Exercise the actual external material-library worker with bounded inputs."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import external_library,library_worker
bpy.context.preferences.use_preferences_save=False
bpy.context.scene.wavelength.engine='source2_cs2_windows'
root=Path(__file__).resolve().parents[1]/'build/source2-library'
request={'root':str(root),'settings':external_library.snapshot(bpy.context.scene.wavelength),'names':['anubis/mudbrick02']}
library_worker.build(request)
manifest=json.loads((root/'manifest.json').read_text())
assert manifest['status']['ready']==1 and manifest['status']['skipped']==0,manifest
with bpy.data.libraries.load(str(root/manifest['files'][0]),assets_only=True) as (source,target):
    assert source.materials
    target.materials=source.materials
mat=target.materials[0]
assert mat.asset_data and mat['wl_source2_material']=='materials/anubis/mudbrick02.vmat'
assert mat.preview.image_size[0]>0
print('PASS CS2 external library worker, asset shard and saved material thumbnail',flush=True)
