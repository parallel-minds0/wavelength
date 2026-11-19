"""Bidirectional native restrictions/engine checkboxes drive all game output."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import scene,export_scope as inclusion,system_tree,mesh_assets,custom_models,model_smd,validation
from wavelength.source.ui import _spawn_point_entity
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_hl2_windows';s.grid_mode='ENGINE'
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.compiler_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin';s.fgd_path=''
folder=Path(__file__).resolve().parents[1]/'build/export-inclusion';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mat=bpy.data.materials.new('Nodraw');mat['wl_texture']='tools/toolsnodraw'
def brush(name,x):
 bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,0));o=c.object;o.name=name;scene.mark_brush(o);o.data.materials.append(mat);return o
a=brush('Always on',0);b=brush('Restricted',3)
assert len(scene.export_map(c.scene).entities[0].brushes)==2
# Native camera restriction propagates to engine state and VMF export.
b.hide_render=True
scope=inclusion.Scope(c.scene);assert inclusion.state(scope,[a,b])=='MIXED'
assert len(scene.export_map(c.scene).entities[0].brushes)==1
assert bpy.ops.wavelength.export_inclusion(category='STRUCTURAL_BRUSHES')=={'FINISHED'}
assert not a.hide_render and not b.hide_render
assert bpy.ops.wavelength.export_inclusion(category='STRUCTURAL_BRUSHES')=={'FINISHED'}
assert a.hide_render and b.hide_render
bpy.ops.wavelength.export_inclusion(category='STRUCTURAL_BRUSHES')
# Eye visibility is independent of output.
b.hide_set(True);assert len(scene.export_map(c.scene).entities[0].brushes)==2
# Nested native collection checkbox and camera restrictions.
outer=bpy.data.collections.new('Export outer');c.scene.collection.children.link(outer)
inner=bpy.data.collections.new('Export inner');outer.children.link(inner)
for coll in list(b.users_collection):coll.objects.unlink(b)
inner.objects.link(b);c.view_layer.update()
layer=c.view_layer.layer_collection.children[outer.name];layer.exclude=True
assert not inclusion.Scope(c.scene).includes(b)
assert len(scene.export_map(c.scene).entities[0].brushes)==1
# Re-enabling in the second tree restores a collection path in the first.
bpy.ops.wavelength.export_inclusion(object_name=b.name)
assert not layer.exclude and inclusion.Scope(c.scene).includes(b)
inner.hide_render=True;assert len(scene.export_map(c.scene).entities[0].brushes)==1
# Objects linked into an additional enabled collection remain included.
c.scene.collection.objects.link(b);assert inclusion.Scope(c.scene).includes(b)
c.scene.collection.objects.unlink(b);inner.hide_render=False
# Invalid unchecked geometry does not block validation/export.
b['wl_csg']=True;b.hide_render=True
scene.export_map(c.scene)
assert not any(d.get('object')==b.name for d in validation.validate(c.scene))
b.pop('wl_csg');b.hide_render=False
# Mesh handoff uses same inclusion, regardless of viewport eye.
b.wavelength_context_role='CONTENT'
s.engine='godot4'
assert b in mesh_assets.candidates(c)
b.hide_render=True;assert b not in mesh_assets.candidates(c)
s.engine='source_hl2_windows';b.hide_render=False
# Custom model sources, dependencies and compilation follow the same choices.
bpy.ops.object.select_all(action='DESELECT')
entity=_spawn_point_entity(c,'prop_static');entity.select_set(True);b.select_set(True);c.view_layer.objects.active=entity
col=custom_models.assign(c);b.hide_render=True
assert not inclusion.Scope(c.scene).includes(entity)
assert custom_models.prepare(c.scene,folder/'excluded') is None
b.hide_render=False;entity.hide_render=True
assert custom_models.prepare(c.scene,folder/'owner-excluded') is None
entity.hide_render=False
bpy.ops.mesh.primitive_cube_add(size=.4,location=(3,1,0));extra=c.object;extra.name='Unchecked model source'
extra.select_set(True);entity.select_set(True);c.view_layer.objects.active=entity
custom_models.assign(c);extra.hide_render=True
text=model_smd.export(col,c.scene,{None:'plain',mat:'nodraw'})['reference.smd']
assert 'object_Unchecked model source' not in text
job=custom_models.prepare(c.scene,folder/'included');assert len(job.jobs)==1
# Temporary clean-render helper suppression never changes authored inclusion.
a['_wl_context_render_restore']=False;a.hide_render=True
assert inclusion.Scope(c.scene).includes(a)
a.hide_render=False;del a['_wl_context_render_restore']
b.hide_render=True
layer.exclude=True
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'inclusion.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'inclusion.blend'))
assert not inclusion.Scope(bpy.context.scene).includes(bpy.data.objects['Restricted'])
assert bpy.data.objects['Restricted'].hide_render
print('PASS native and category/object checkboxes, nested/excluded/linked collections, map/mesh/validation/model builds, viewport independence and render-policy isolation',flush=True)
