"""Check staged route authoring and actual Source VMF serialization."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import bpy
import wavelength
from wavelength.source import fence_route, scene, vmf

wavelength.register()
context = bpy.context
context.workspace['wl_workspace'] = True
context.scene.wavelength.engine = 'source_hl2_windows'
for obj in list(context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

assert bpy.ops.wavelength.add_fence_route() == {'FINISHED'}
route = context.object
assert fence_route.WL_PT_fence_route.poll(context)
spline = route.data.splines[0]
spline.points.add(1)
spline.points[2].co = (4, 4, 0, 1)
config = route.wl_fence_route
config.gate_center = 4
config.gate_width = 2
material = bpy.data.materials.new('concrete/concretefloor001a')
material['wl_texture'] = material.name
config.material = material
context.view_layer.update()
operate = bpy.ops.wavelength.fence_route
assert operate(action='PREVIEW') == {'FINISHED'}
assert fence_route._proposal(route).hide_render
assert 'wl_fence_output' not in route
assert operate(action='APPLY') == {'FINISHED'}
assert not fence_route._proposal(route)
output = route['wl_fence_output']
posts = list(output.objects)
assert len(posts) == 6
assert {tuple(post.location) for post in posts} == {
    (0, 0, 0), (1, 0, 0), (2, 0, 0), (4, 2, 0), (4, 3, 0), (4, 4, 0),
}
assert all(post.data.uv_layers and post.get('wl_role') == 'BRUSH' for post in posts)
assert operate(action='PREVIEW') == {'FINISHED'}
document = vmf.parse(vmf.write(scene.export_map(context.scene)))
assert len(document.entities[0].brushes) == len(posts)
assert all(len(brush) == 6 for brush in document.entities[0].brushes)
spline.points[2].co.y += 1
try:
    assert operate(action='APPLY') == {'CANCELLED'}
except RuntimeError as exc:
    assert 'Preview the current fence route' in str(exc)
assert list(output.objects) == posts
assert operate(action='DISCARD') == {'FINISHED'}
assert not fence_route._proposal(route) and list(output.objects) == posts
assert operate(action='PREVIEW') == {'FINISHED'}
bpy.ops.ed.undo_push(message='Before fence apply')
assert operate(action='APPLY') == {'FINISHED'}
assert len(output.objects) == 7
bpy.ops.ed.undo_push(message='After fence apply')
assert bpy.ops.ed.undo() == {'FINISHED'}
route = context.object
assert len(route['wl_fence_output'].objects) == 6 and fence_route._proposal(route)
assert operate(action='APPLY') == {'FINISHED'}
assert len(route['wl_fence_output'].objects) == 7

if '--demo' in sys.argv:
    from mathutils import Quaternion

    context.workspace.name = 'wavelength'
    for area in context.screen.areas:
        if area.type == 'PROPERTIES':
            area.spaces.active.context = 'OBJECT'
        if area.type == 'VIEW_3D':
            view = area.spaces.active.region_3d
            view.view_location = (2, 2, .5)
            view.view_distance = 10
            view.view_rotation = Quaternion((.85, .47, .13, .2)).normalized()
    bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index('--demo') + 1])

print('PASS fence placement, bend clearance, stale rejection, discard, undo restoration and VMF export', flush=True)
