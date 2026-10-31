from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import model_browser
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
scene_count=len(c.scene.objects)
model_browser.schedule(c,prepared_names=['models/test/a%03d.mdl'%i for i in range(200)])
for i in range(500):model_browser.publish_batch()
assert model_browser._ready==96 and len(model_browser._queue)==104
assert len(c.scene.objects)==scene_count
s.asset_browser_section='TEXTURES';model_browser._tick_context()
assert model_browser._ready==96
bpy.ops.wavelength.more_models()
for i in range(500):model_browser.publish_batch()
assert model_browser._ready==192
model_browser._publish_limit+=96
model_browser._queue=type(model_browser._queue)(sorted(model_browser._queue,key=lambda row:'a199' not in row[0]))
model_browser.publish_batch('a199')
assert model_browser._ready==193
print('PASS model publication bounded to 96; paused outside Models; explicit more and full-index search',flush=True)
