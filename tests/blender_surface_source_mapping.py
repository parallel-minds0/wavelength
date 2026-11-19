exec(compile((__import__('pathlib').Path(__file__).parent/'blender_surface_tools.py').read_text(),__file__,'exec'))
from mathutils import Vector
from wavelength.source import formats
s.engine='source_hl2_windows';s.game_dir='';s.texture=names[1];s.texture_alignment='FACE';s.texture_lightmap=32
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
records=json.loads(obj.data['wl_faces'])
for record in records.values():
    face=formats.Face(**record)
    assert record['vmf']['lightmapscale']=='32'
    assert all(abs(Vector(axis[:3]).dot(Vector(face.plane()[0])))<1e-5 for axis in face.axes)
from unittest.mock import patch
records['1']['vmf'].update(smoothing_groups='5', contents='32', flags='128')
obj.data['wl_faces']=json.dumps(records)
face_ids=obj.data.attributes['wl_face_id']
index=next(i for i,d in enumerate(face_ids.data) if d.value==1)
other=next(i for i,d in enumerate(face_ids.data) if d.value!=1)
before=obj.data['wl_faces']
with patch.object(asset_browser,'reveal_texture') as reveal:
    surface_tools.sample(ctx,obj,index,'TEXTURE')
    assert (s.texture_lightmap,s.texture_smoothing_groups,s.texture_contents,s.texture_surface_flags)==(32,'5','32','128')
    assert json.loads(ctx.scene['_wl_asset_clipboard'])['path']==names[1]
    reveal.assert_called_once()
    surface_tools.sample(ctx,obj,other,'TEXTURE')
    assert (s.texture_lightmap,s.texture_smoothing_groups,s.texture_contents,s.texture_surface_flags)==(32,'0','','')
assert obj.data['wl_faces']==before
print('PASS Source lightmap scale persists and face alignment axes lie in the surface plane',flush=True)
