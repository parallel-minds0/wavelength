"""Protect authored materials and bound drop-handler work to changed objects."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import external_library as library,asset_browser,workspace,profile_ui,scene,textures
wavelength.register()
def material(name):
    mat=bpy.data.materials.new(name);mat.use_fake_user=True
    mat['wl_texture']=name;mat['wl_asset_profile']='source_hl2_windows';return mat
unused=material('unused generated thumbnail')
assigned=material('assigned thumbnail');bpy.context.object.data.materials.append(assigned)
custom=material('custom thumbnail');custom.node_tree.nodes.new('ShaderNodeMath')
realized=material('realized thumbnail');realized['wl_realized']=True
library._cleanups.extend([unused,assigned,custom,realized])
while library._cleanups:library.tick()
assert bpy.data.materials.get('unused generated thumbnail') is None
assert all(bpy.data.materials.get(m.name)==m for m in (assigned,custom,realized))
objects=[]
for i in range(80):
    obj=bpy.data.objects.new('Brush '+str(i),bpy.data.meshes.new('Mesh'))
    obj['wl_role']='BRUSH';bpy.context.collection.objects.link(obj);objects.append(obj)
with patch.object(workspace,'active',return_value=True),patch.object(asset_browser,'_brush_mat_signature',return_value='') as signature:
    asset_browser.dropped(bpy.context.scene,SimpleNamespace(updates=[SimpleNamespace(id=objects[0])]))
    assert signature.call_count==1,signature.call_count
    signature.reset_mock()
    asset_browser.dropped(bpy.context.scene,SimpleNamespace(updates=[SimpleNamespace(id=custom)]))
    assert signature.call_count==0,signature.call_count
# An external drag appends a preview-only material, then a changed Object event
# must realize it and synchronize persistent face records.
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
with patch.object(textures,'refresh'):
    profile_ui.apply(bpy.context,profile)
_,root=library.cache_root(library.snapshot(bpy.context.scene.wavelength))
with bpy.data.libraries.load(str(next(root.glob('textures-*.blend'))),link=False) as (available,requested):
    requested.materials=[available.materials[0]]
mat=requested.materials[0]
obj=bpy.context.object;scene.mark_brush(obj)
obj.data.materials.clear();obj.data.materials.append(mat)
with patch.object(workspace,'active',return_value=True):
    asset_browser.dropped(bpy.context.scene,SimpleNamespace(updates=[SimpleNamespace(id=obj)]))
assert mat.get('wl_realized') and any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes)
wavelength.unregister()
print('PASS EXTERNAL MIGRATION: assigned/custom/realized preserved; 1 changed brush scanned, material events scan none')
