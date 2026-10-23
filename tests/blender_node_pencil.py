"""Live native curves, angled/signed node extrusion and finalization boundary."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_pencil.py').read_text().split("addon_utils.disable('wavelength'")[0],__file__,'exec'))
from wavelength.source import node_pencil,profiles
import bmesh

def evaluated(obj):
    ctx.view_layer.update();graph=ctx.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(obj.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
def volume(mesh):
    bm=bmesh.new();bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges)
    value=bm.calc_volume();bm.free();return value
for axis,n in [('Z',Vector((0,0,1))),('X',Vector((1,0,0))),('Y',Vector((0,1,0)))]:
    rot=n.to_track_quat('Z','Y')
    coordinates=[rot@Vector(p) for p in [(-1,-1,2),(1,-1,2),(1,1,2),(-1,1,2)]]
    guide=pencil.create_guide(ctx,[pencil.point(p) for p in coordinates],n,True)
    for height in (2,-2):
        obj=pencil.create_geometry(ctx,guide,'EXTRUDE',height)
        assert obj.modifiers and obj.parent==guide
        mesh=evaluated(obj);assert abs(volume(mesh)-8)<1e-4,(axis,height,volume(mesh));bpy.data.meshes.remove(mesh)
        guide.wavelength_cutter.height=3/obj['wl_unit_meters'];node_pencil.update(obj)
        mesh=evaluated(obj);assert abs(volume(mesh)-12)<1e-4;bpy.data.meshes.remove(mesh)
        # A native control point edit must reach the graph without Python rebuild.
        bp=guide.data.splines[0].bezier_points[0];shift=rot@Vector((-.5,0,0))
        bp.co+=shift;bp.handle_left+=shift;bp.handle_right+=shift;guide.data.update_tag()
        mesh=evaluated(obj);assert volume(mesh)>12.1;bpy.data.meshes.remove(mesh)
        node_pencil.finalize(obj);assert not obj.modifiers and obj.parent is None
        saved=[tuple(v.co) for v in obj.data.vertices];guide.location.x+=10;ctx.view_layer.update()
        assert saved==[tuple(v.co) for v in obj.data.vertices]
        guide.location.x-=10;bp.co-=shift;bp.handle_left-=shift;bp.handle_right-=shift;guide.data.update_tag()
        print('PASS live node extrusion and independent finalization',axis,height,flush=True)
# Oblique extrusion follows the requested world axis instead of the face normal.
n=Vector((1,0,1)).normalized();rot=n.to_track_quat('Z','Y')
guide=pencil.create_guide(ctx,[pencil.point(rot@Vector(p)) for p in [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)]],n,True)
guide.wavelength_cutter.direction='Z';obj=pencil.create_geometry(ctx,guide,'EXTRUDE',2)
mesh=evaluated(obj);assert abs(volume(mesh)-8*n.z)<1e-4;bpy.data.meshes.remove(mesh)
unit=obj['wl_unit_meters'];ctx.scene.wavelength.engine='source_hl2_windows';node_pencil.update(obj,force=True)
assert obj['wl_unit_meters']==unit
print('PASS angled directional extrusion and fixed profile units',flush=True)
print('PASS LIVE NODE PENCIL',flush=True)
