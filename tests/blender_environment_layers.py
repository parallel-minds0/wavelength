"""Privateer-sized units, small patch: paint -> overrides -> reopen -> Godot bundle."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import environment_layers as env, environment_godot as adapter

wavelength.register()
context=bpy.context
context.preferences.use_preferences_save=False
context.workspace['wl_workspace']=True
context.scene.wavelength.engine='godot4'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
OUTPUT=ROOT/'build/privateer';OUTPUT.mkdir(parents=True,exist_ok=True)


def material(name,color):
    result=bpy.data.materials.new(name);result.diffuse_color=(*color,1);result.use_nodes=True
    result.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    return result


grass=material('Meadow',(.11,.26,.08));bark=material('Tree',(.15,.32,.07));stone=material('Rocks',(.35,.3,.27))
mesh=bpy.data.meshes.new('Sculptable patch cage')
size=32
mesh.from_pydata([(x,y,.1*x+.03*y) for y in range(size+1) for x in range(size+1)],[],
                 [(y*(size+1)+x,y*(size+1)+x+1,(y+1)*(size+1)+x+1,(y+1)*(size+1)+x)
                  for y in range(size) for x in range(size)])
terrain=bpy.data.objects.new('Privateer editable patch',mesh);context.collection.objects.link(terrain)
terrain.location=(100,-50,5);terrain.data.materials.append(grass)
context.view_layer.objects.active=terrain;terrain.select_set(True)
palette=bpy.data.collections.new('Reusable two-tree palette');context.scene.collection.children.link(palette)
rocks_palette=bpy.data.collections.new('Reusable rock palette');context.scene.collection.children.link(rocks_palette)
for name,collection,radius,depth,mat in [('Pine A',palette,1,5,bark),('Pine B',palette,.7,3,bark),('Boulder',rocks_palette,.7,.8,stone)]:
    bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=radius,radius2=.1,depth=depth,location=(0,0,0))
    proto=context.object;proto.name=name
    # Feet on the origin; prototypes hidden but Geometry Nodes still instances them.
    for v in proto.data.vertices:v.co.z+=depth/2
    proto.data.materials.append(mat)
    for old in list(proto.users_collection):old.objects.unlink(proto)
    collection.objects.link(proto);proto.hide_set(True);proto.hide_render=True
    env.identity(proto)
trees=env.add_layer(terrain,name='Trees');trees.palette=palette;trees.density=.18;trees.seed=93
rocks=env.add_layer(terrain,name='Rocks');rocks.palette=rocks_palette;rocks.density=.06;rocks.align_normal=True
clearing=env.add_layer(terrain,'EXCLUSION','Clearing')
paint=env.add_layer(terrain,'MATERIAL','Meadow paint');paint.material=grass
for layer in (trees,rocks):
    # Brush the same native groups used by the artist UI, not a special test mask.
    env.stamp(terrain,layer,(116,-34,7),80,1,1)
env.stamp(terrain,paint,(110,-40,6),10,1,1)
group=terrain.vertex_groups[clearing.mask]
for vertex in mesh.vertices:
    world=terrain.matrix_world@vertex.co
    if (world.x-116)**2+(world.y+34)**2<36:group.add([vertex.index],1,'REPLACE')
context.view_layer.update()
positions=[tuple(v.co) for v in mesh.vertices]
assert max(g.weight for v in mesh.vertices for g in v.groups if g.group==group.index)==1
first=env.records(context,terrain,trees)
assert len(first)>20
assert len({r['prototype'] for r in first})==2
assert all((Matrix(r['matrix']).translation.x-116)**2+(Matrix(r['matrix']).translation.y+34)**2>16 for r in first)
assert env.records(context,terrain,trees)==first
removed=first[0]['id'];moved=first[1]['id']
env.set_override(trees,removed,delete=True)
proto=next(p for p in palette.objects if env.identity(p)==first[1]['prototype'])
matrix=Matrix(first[1]['matrix']);matrix.translation+=Vector((1,2,3))
env.set_override(trees,moved,proto,matrix)
manual=Matrix.Translation((116,-34,9))
env.set_override(trees,'manual:hero-tree',proto,manual)
expected=env.records(context,terrain,trees)
assert removed not in {r['id'] for r in expected}
assert next(r for r in expected if r['id']==moved)['matrix']==[list(row) for row in matrix]
assert next(r for r in expected if r['id']=='manual:hero-tree')['matrix']==[list(row) for row in manual]
rocks_before=env.records(context,terrain,rocks)
trees.density=.1
assert env.records(context,terrain,rocks)==rocks_before
assert next(r for r in env.records(context,terrain,trees) if r['id']==moved)['matrix']==[list(row) for row in matrix]
trees.density=.18
trees.preview_fraction=.5
visual=env.preview(context,terrain,trees)
assert len(visual.data.vertices)<len(expected)
env.preview(context,terrain,rocks)
assert len([o for o in context.scene.objects if o.get('wl_environment_layer')])==2
assert positions==[tuple(v.co) for v in mesh.vertices]
assert len(terrain.modifiers)==0
subdivision=terrain.modifiers.new('Native non-destructive subdivision','SUBSURF')
subdivision.subdivision_type='SIMPLE';subdivision.levels=1
context.view_layer.update()
subdivided=env.records(context,terrain,trees)
assert {r['id'] for r in subdivided}=={r['id'] for r in expected}
terrain.modifiers.remove(subdivision)
context.view_layer.update()
instances=[i for i in context.evaluated_depsgraph_get().object_instances if i.is_instance]
assert len(instances)==len(visual.data.vertices)+len(rocks_before), (len(instances),len(visual.data.vertices),len(rocks_before))
from wavelength.source.terrain_revision import copy_surface
independent=copy_surface(terrain)
assert independent.wavelength_environment_layers[0].preview is None
assert independent.wavelength_environment_layers[0].overrides==trees.overrides
assert independent.wavelength_environment_layers[0].uid!=trees.uid
assert independent.data!=terrain.data
independent_mesh=independent.data;bpy.data.objects.remove(independent)
bpy.data.meshes.remove(independent_mesh)
for obj in context.selected_objects:obj.select_set(False)
terrain.hide_set(False);terrain.select_set(True);context.view_layer.objects.active=terrain
terrain.wavelength_environment_active=0
# Exercise the artist entry point and correction transaction, not only its API.
assert bpy.ops.wavelength.environment_layer(action='PAINT')=={'FINISHED'}
assert context.mode=='PAINT_WEIGHT'
assert context.tool_settings.weight_paint.brush is not None
assert terrain.vertex_groups.active.name==trees.mask
bpy.ops.object.mode_set(mode='OBJECT')
context.scene.cursor.location=(116,-34,9)
assert bpy.ops.wavelength.environment_layer(action='EDIT')=={'FINISHED'}
assert context.object.get('wl_environment_edit')=='manual:hero-tree'
context.object.location.z+=1
assert bpy.ops.wavelength.environment_layer(action='DISCARD')=={'FINISHED'}
assert env.records(context,terrain,trees)==expected
context.view_layer.update()
# A runnable artist example with a useful startup view.
for area in context.screen.areas if context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=(116,-34,8)
        area.spaces.active.region_3d.view_distance=55
        area.spaces.active.shading.color_type='MATERIAL'
saved=OUTPUT/'privateer-environment-demo.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(saved))
bpy.ops.wm.open_mainfile(filepath=str(saved))
terrain=bpy.data.objects['Privateer editable patch'];trees=terrain.wavelength_environment_layers[0]
assert env.records(context,terrain,trees)==expected
assert terrain.wavelength_environment_layers[2].kind=='EXCLUSION'
assert terrain.wavelength_environment_layers[3].material.name=='Meadow'
before=(context.scene,len(bpy.data.objects),len(bpy.data.meshes),context.view_layer.objects.active)
project=OUTPUT/'godot';project.mkdir(exist_ok=True)
(project/'project.godot').write_text('[application]\nconfig/name="Wavelength Privateer patch"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
path,doc=adapter.export(context,[terrain],str(project/'environment'))
assert before==(context.scene,len(bpy.data.objects),len(bpy.data.meshes),context.view_layer.objects.active)
assert len(doc['prototypes'])==3
exported=[r for b in doc['batches'] if b['layer']==trees.uid for r in b['instances']]
assert len(exported)==len(expected), 'Preview thinning leaked into export'
reference={r['id']:r for r in expected}
for record in exported:
    assert record['transform']==adapter.godot_transform(reference[record['id']]['matrix'])
masks=json.loads((path.parent/doc['terrain'][0]['masks']).read_text())
assert len(masks['masks'])==4 and max(masks['masks'][terrain.wavelength_environment_layers[2].uid])==1
assert (len(doc['terrain']),len(doc['prototypes']))==(1,3)
assert adapter.godot_transform(manual)[9:]==[116.,9.,34.]
prior=path.read_bytes()
trees.overrides=json.dumps({'bad':{'prototype':'missing','matrix':[list(row) for row in Matrix.Identity(4)]}})
try:adapter.export(context,[terrain],str(project/'environment'))
except ValueError as exc:assert 'missing palette' in str(exc)
else:raise AssertionError('Missing override prototype silently discarded')
assert path.read_bytes()==prior
trees.overrides=json.dumps({r['id']:{k:v for k,v in r.items() if k!='id'} for r in expected if r['id'] in {moved,'manual:hero-tree'}} | {removed:{'deleted':True}})
report={'status':'PASS','trees':len(expected),'rocks':len(rocks_before),'manual_id':'manual:hero-tree',
        'excluded_id':removed,'terrain':terrain.name,'moved_id':moved,'clearing_center_godot':[116,0,34]}
(OUTPUT/'validation.json').write_text(json.dumps(report,indent=2))
print('PASS ENVIRONMENT LAYERS',json.dumps(report),flush=True)
wavelength.unregister()
