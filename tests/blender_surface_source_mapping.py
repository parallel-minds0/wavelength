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
print('PASS Source lightmap scale persists and face alignment axes lie in the surface plane',flush=True)
