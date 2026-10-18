"""Real Blender regression: profile refresh transaction and truthful completion."""
import sys,uuid
from pathlib import Path
from unittest.mock import patch
from collections import deque
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import profile_ui,textures,ui,asset_browser as assets
wavelength.register()
profile={'schema':1,'id':str(uuid.uuid4()),'name':'refresh test','settings':{'engine':'source_hl2_windows','game_dir':'C:/test/game','fgd_path':'C:/test/test.fgd','texture_wads':'[]','palette_path':''}}
with patch.object(textures,'refresh') as refresh:
 profile_ui.apply(bpy.context,profile)
 assert refresh.call_count==1,refresh.call_count
assert not ui._IN_ENGINE_CHANGE
invalid={**profile,'settings':{**profile['settings'],'game_dir':123}}
try:
 with patch.object(textures,'refresh'):profile_ui.apply(bpy.context,invalid)
except TypeError:pass
else:raise AssertionError('Invalid property type accepted')
assert not ui._IN_ENGINE_CHANGE
assets._AUTO_QUEUE=deque(['good','unsupported']);assets._AUTO_TRIM.clear();assets._AUTO_PUBLISHED=0;assets._AUTO_TOTAL=2;assets._AUTO_SKIPPED.clear()
def publish(s,name,**kwargs):
 if name=='unsupported':raise ValueError('No supported base texture')
with patch.object(assets,'publish_material_fast',side_effect=publish):assets._publish_batch(bpy.context.scene.wavelength,4)
assert assets._AUTO_PUBLISHED==1 and len(assets._AUTO_SKIPPED)==1
assert assets.texture_status_label()=='1 ready, 1 skipped',assets.texture_status_label()
print('PASS PROFILE REFRESH AND COMPLETION: one refresh, guard restored, skipped entries reported')
wavelength.unregister()
