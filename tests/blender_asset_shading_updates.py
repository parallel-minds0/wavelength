"""Unrelated asset shading tags do not recheck map face assignments."""
from pathlib import Path
import sys,json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import scene,editor,asset_browser
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
c.scene.wavelength.engine='blender'
def material(name):
 mat=bpy.data.materials.new(name);mat['wl_texture']=name;mat['wl_asset_profile']='blender';mat['wl_realized']=True;mat['wl_width']=64;mat['wl_height']=64;return mat
one=material('first');two=material('second');objects=[]
for i in range(50):
 bpy.ops.mesh.primitive_cube_add(location=(i*3,0,0));obj=c.object;scene.mark_brush(obj);obj.data.materials.append(one);editor.apply_uv(obj,'blender');objects.append(obj)
c.view_layer.update();asset_browser.dropped(c.scene);c.view_layer.update()
with patch.object(asset_browser,'_brush_mat_signature',wraps=asset_browser._brush_mat_signature) as signature:
 col=bpy.data.collections.new('Unlinked test');col.use_fake_user=True
 obj=bpy.data.objects.new('Template',None);col.objects.link(obj);obj.asset_mark();c.view_layer.update()
 assert signature.call_count==0,signature.call_count
with patch.object(asset_browser,'_brush_mat_signature',wraps=asset_browser._brush_mat_signature) as signature:
 objects[4].data.materials[0]=two;c.view_layer.update()
 assert signature.call_count>0
 assert all(v['texture']=='second' for v in json.loads(objects[4].data['wl_faces']).values())
print('PASS unrelated template shading skips brush checks; material assignment still updates face metadata',flush=True)
