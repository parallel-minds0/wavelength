"""Exercise the landing fit through the registered Blender operator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import bpy
import wavelength
from mathutils import Vector
from wavelength.source import landing_stairs, primitive_ui, procedural, scene, vmf

wavelength.register()
context = bpy.context
context.workspace['wl_workspace'] = True
settings = context.scene.wavelength
settings.engine = 'source_hl2_windows'
settings.grid_mode = 'ENGINE'
settings.grid_step = '16'
for obj in list(context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


def empty(name, position):
    obj = bpy.data.objects.new(name, None)
    context.collection.objects.link(obj)
    obj.location = position
    return obj


root = empty('Landing-linked stair', (0, 0, 0))
primitive_ui.rebuild(root, 'STAIRS', primitive_ui.DEFAULTS, context)
context.view_layer.objects.active = root
assert landing_stairs.WL_PT_landing_stair.poll(context)
link = root.wl_landing_stair
link.lower = empty('Lower connection', (1, 2, 1))
link.upper = empty('Upper connection', (4, 6, 3))
link.steps = 7
context.view_layer.update()
original = root['wl_definition']
run = bpy.ops.wavelength.landing_stair
assert run(action='PREVIEW') == {'FINISHED'}
proposal = landing_stairs._proposal(root)
assert proposal['wl_exclude'] and proposal.hide_render and proposal.hide_select
assert root['wl_definition'] == original
link.upper.location.z += .37
context.view_layer.update()
try:
    assert run(action='APPLY') == {'CANCELLED'}
except RuntimeError as exc:
    assert 'Preview the current connections' in str(exc)
assert root['wl_definition'] == original and landing_stairs._proposal(root) == proposal
assert run(action='DISCARD') == {'FINISHED'} and not landing_stairs._proposal(root)
assert run(action='PREVIEW') == {'FINISHED'}
bpy.ops.ed.undo_push(message='Before landing fit')
assert run(action='APPLY') == {'FINISHED'}
bpy.ops.ed.undo_push(message='After landing fit')
assert bpy.ops.ed.undo() == {'FINISHED'}
root = context.object
link = root.wl_landing_stair
assert root['wl_definition'] == original and landing_stairs._proposal(root)
assert run(action='APPLY') == {'FINISHED'}
assert not landing_stairs._proposal(root)
context.view_layer.update()
definition = procedural.Definition.loads(root['wl_definition'])
parts = primitive_ui.parts_for(root)
assert definition.grid_step is None and len(parts) == 7
assert all(part.modifiers[0].type == 'NODES' for part in parts)
assert all(len(scene.brush_from_object(part, definition.owner)) == 6 for part in parts)
material = bpy.data.materials.new('concrete/concretefloor001a')
material['wl_texture'] = material.name
for part in parts:
    part.data.materials.append(material)
document = vmf.parse(vmf.write(scene.export_map(context.scene)))
assert len(document.entities[0].brushes) == 7
assert (root.matrix_world.translation - link.lower.location).length < 1e-5
last = parts[-1].evaluated_get(context.evaluated_depsgraph_get())
end = link.upper.matrix_world.translation
top_end = Vector((0, max(v[1] for v in last.bound_box), max(v[2] for v in last.bound_box)))
assert (last.matrix_world @ top_end - end).length < 1e-5
upper = link.upper
link.upper = None
try:
    assert run(action='PREVIEW') == {'CANCELLED'}
except RuntimeError as exc:
    assert 'Choose lower and upper' in str(exc)
assert len(primitive_ui.parts_for(root)) == 7 and not landing_stairs._proposal(root)
link.upper = upper
if '--demo' in sys.argv:
    from mathutils import Quaternion

    width = definition.parameters['width'] * definition.unit_meters
    for marker, sign in ((link.lower, -1), (link.upper, 1)):
        marker.empty_display_type = 'SPHERE'
        marker.empty_display_size = .12
        marker.show_in_front = True
        bpy.ops.mesh.primitive_cube_add(size=1)
        platform = context.object
        platform.name = marker.name.replace('connection', 'landing')
        platform.matrix_world = root.matrix_world.copy()
        platform.location = marker.location + root.matrix_world.to_3x3() @ Vector((0, sign * .75, -.15))
        platform.scale = (width, 1.5, .3)
        marker.parent = platform
        context.view_layer.update()
        marker.matrix_parent_inverse = platform.matrix_world.inverted()
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    context.view_layer.objects.active = root
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            view = area.spaces.active.region_3d
            view.view_location = (link.lower.matrix_world.translation + link.upper.matrix_world.translation) * .5
            view.view_distance = 11
            view.view_rotation = Quaternion((.83, .48, .14, .24)).normalized()
        elif area.type == 'PROPERTIES':
            area.spaces.active.context = 'OBJECT'
    bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index('--demo') + 1])
assert run(action='PREVIEW') == {'FINISHED'}
parts = primitive_ui.finalize(root, context)
assert not any(obj.get('wl_landing_proposal') for obj in context.scene.objects)
assert all(not part.modifiers and part.parent is None for part in parts)
print('PASS landing fit preview, stale proposal, discard, exact HL2 endpoints, convex brushes and finalization', flush=True)
