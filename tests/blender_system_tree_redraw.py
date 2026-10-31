"""Tree redraws classify once; unsupported texture rules never decode faces."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import wavelength
wavelength.register()
from wavelength.source import system_tree, system_tree_view

scene = bpy.context.scene
scene.wavelength.engine = 'source_hl2_windows'
mesh = bpy.data.meshes.new('Tree test brush')
brush = bpy.data.objects.new('Tree test brush', mesh)
scene.collection.objects.link(brush)
brush['wl_role'] = 'BRUSH'
mesh['wl_faces'] = json.dumps({'1': {'texture': 'sky'}})
prop = bpy.data.objects.new('Tree test prop', None)
scene.collection.objects.link(prop)
prop['wl_role'] = 'ENTITY'
prop['wl_pairs'] = json.dumps([['classname', 'prop_static']])

class Layout:
    def row(self, **kwargs): return self
    def operator(self, *args, **kwargs): return SimpleNamespace()
    def label(self, **kwargs): pass
    def separator(self, **kwargs): pass

# Measure the actual panel draw contract rather than a second implementation.
# Every category eye must reuse the grouping made at the start of this redraw.
with patch.object(system_tree, 'groups', wraps=system_tree.groups) as groups:
    with patch.object(system_tree, 'brush_textures', side_effect=AssertionError('Source redraw decoded brush textures')):
        system_tree_view.WL_PT_engine_tree.draw(SimpleNamespace(layout=Layout()), bpy.context)
    assert groups.call_count == 1, groups.call_count

# Reuse changes no visibility semantics, including mixed visibility.
system_tree.invalidate_groups()
with patch.object(system_tree, 'category', wraps=system_tree.category) as classify:
    first = system_tree.groups(scene)
    calls = classify.call_count
    assert system_tree.groups(scene) is first
    assert classify.call_count == calls, 'Unchanged tree redraw rescanned the map'
    prop['wl_pairs'] = json.dumps([['classname', 'info_target']])
    prop.update_tag()
    bpy.context.view_layer.update()
    assert prop in system_tree.groups(scene)['POINT_ENTITIES']
    assert classify.call_count > calls, 'Scene edit did not invalidate classification'
prop['wl_pairs'] = json.dumps([['classname', 'prop_static']])
prop.update_tag()
bpy.context.view_layer.update()
objects = [brush, prop]
assert system_tree.category_visibility(scene, 'PROPS', objects=objects) == 'VISIBLE'
system_tree.set_object_hidden(prop, True)
assert system_tree.category_visibility(scene, 'PROPS', objects=objects) == 'MIXED'
bpy.context.view_layer.update()
assert system_tree.tree_visibility(scene, 'PROPS', bpy.context.view_layer, objects) == 'MIXED'
system_tree.set_object_hidden(brush, True)
bpy.context.view_layer.update()
assert system_tree.tree_visibility(scene, 'PROPS', bpy.context.view_layer, objects) == 'HIDDEN'
assert system_tree.category_visibility(scene, 'PROPS', objects=objects) == 'HIDDEN'

from wavelength.source import object_index
object_index.clear()
with patch.object(system_tree, 'classname', wraps=system_tree.classname) as classify:
    predicate = lambda obj: system_tree.classname(obj) == 'prop_static'
    assert prop in object_index.matching('test_props', scene, predicate)
    calls = classify.call_count
    object_index.matching('test_props', scene, predicate)
    assert classify.call_count == calls
    prop['wl_pairs'] = json.dumps([['classname', 'info_target']])
    prop.update_tag()
    bpy.context.view_layer.update()
    assert prop not in object_index.matching('test_props', scene, predicate)

# Already-hidden parents must still hide a reference that arrives later.
child = bpy.data.objects.new('Delayed reference', None)
scene.collection.objects.link(child)
child.parent = prop
child['wl_model_reference'] = True
system_tree.set_object_hidden(prop, True)
assert child.hide_get()
assert system_tree.special_kind(brush, 'quake') == 'SKY'
assert system_tree.special_kind(brush, 'goldsrc') == 'SKY'
print('PASS System Tree: one grouping per redraw, Source skips face parsing, mixed visibility and delayed references preserved', flush=True)
