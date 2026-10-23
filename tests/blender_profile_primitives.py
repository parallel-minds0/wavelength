import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import primitives,profiles,primitive_ui
bpy.context.preferences.use_preferences_save=False
for kind,extra in [('ARCH',{}),('ARCH',{'angle':360}),('STAIRS',{}),('STAIRS',{'curved':True}),('STAIRS',{'curved':True,'curve_angle':-90,'landing':32})]:
    values={**primitive_ui.DEFAULTS,**extra}
    bsp=primitives.generate(kind,values,validate_bsp=True)
    mesh=primitives.generate(kind,values,validate_bsp=False)
    assert len(bsp)>1 and len(mesh)==1,(kind,len(bsp),len(mesh))
    verts,faces=mesh[0];data=bpy.data.meshes.new('Test');data.from_pydata(verts,[],faces)
    bm=bmesh.new();bm.from_mesh(data)
    assert all(e.is_manifold for e in bm.edges),(kind,extra,[(tuple(v.co for v in e.verts),len(e.link_faces)) for e in bm.edges if not e.is_manifold])
    assert abs(bm.calc_volume())>0
    bm.free();bpy.data.meshes.remove(data)
    print('PASS unrestricted connected mesh / BSP convex parts',kind,extra,flush=True)
assert not profiles.requires_convex_brushes('blender')
assert all(profiles.requires_convex_brushes(k) for k in profiles.PROFILES if k!='blender')
profiles.PROFILES['test_future_mesh']={'brush_semantics':False}
assert not profiles.requires_convex_brushes('test_future_mesh')
print('PASS explicit profile constraints default unrestricted',flush=True)
