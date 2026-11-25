"""Real Estuary patch acceptance. Reads the original blend; saves a separate artist copy."""
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path(r'C:/Users/user/Projects/focus/video games/lightracinggame/light-racer')
SOURCE=PROJECT/'development/environment/maps/city-design/iteration-10/blender/estuary-nature-rev010.blend'
OUT=ROOT/'build/privateer-complete';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import environment_layers as env, environment_materials as materials
from wavelength.source import environment_adopt as adoption, environment_godot as adapter

bpy.ops.wm.read_factory_settings(use_empty=True)
wavelength.register()
context=bpy.context;context.preferences.use_preferences_save=False
context.workspace['wl_workspace']=True;context.scene.wavelength.engine='godot4'
context.scene.unit_settings.system='METRIC';context.scene.unit_settings.scale_length=1
names=['Terrain_1792_512','Forest_Points_Editable_0','Forest_Points_Editable_1','Forest_Points_Editable_2','forest_rocks_small_0']
source_hash=hashlib.file_digest(SOURCE.open('rb'),'sha256').hexdigest()
with bpy.data.libraries.load(str(SOURCE),link=False) as (source,target):
    assert all(name in source.objects for name in names)
    target.objects=list(names)
for obj in list(bpy.data.objects):
    if not obj.users_collection:context.scene.collection.objects.link(obj)
terrain=bpy.data.objects['Terrain_1792_512'];terrain.name='Estuary · editable artist patch'
context.view_layer.update()
bm=bmesh.new();bm.from_mesh(terrain.data)
outside=[v for v in bm.verts if not (1860<= (terrain.matrix_world@v.co).x<=1988 and 572<= (terrain.matrix_world@v.co).y<=700)]
bmesh.ops.delete(bm,geom=outside,context='VERTS');bm.to_mesh(terrain.data);bm.free();terrain.data.update()
assert len(terrain.data.polygons)>500
for obj in context.scene.objects:
    obj.hide_set(obj!=terrain);obj.hide_render=obj!=terrain
terrain.select_set(True);context.view_layer.objects.active=terrain
sources=[bpy.data.objects[name] for name in names[1:]]
context.view_layer.update()
adopted=[];before_counts={}
for source in sources:
    before_counts[source.name]=len(source.data.vertices)
    layer=adoption.adopt(context,terrain,source)
    if layer:
        assert len(layer.placements.data.vertices)+len(layer.adopt_remainder.data.vertices)==before_counts[source.name]
        layer.adopt_remainder.hide_set(True);layer.adopt_remainder.hide_render=True
        adopted.append(layer)
assert len([l for l in adopted if 'adopted' in l.name])>=2
unmodified={l.uid:env.records(context,terrain,l) for l in adopted}
assert sum(len(records) for records in unmodified.values())>30
surface=env.Surface(context,terrain)
x0,y0,x1,y1=surface.bounds
center=surface.hit((x0+x1)/2,(y0+y1)/2)[0];surface.close()
clearing=env.add_layer(terrain,'EXCLUSION','Protected clearing')
env.stamp(terrain,clearing,center,24,1,strength=10)
palette=bpy.data.collections.new('Estuary · reusable trees');context.scene.collection.children.link(palette)
for layer in adopted:
    if 'Editable' not in layer.name and layer.name.split(' ')[0] not in {'0','1','2'}:continue
    proto=env.palette(layer)[0]
    if proto.name not in palette.objects:palette.objects.link(proto)
if len(palette.objects)<2:
    for layer in adopted[:3]:
        proto=env.palette(layer)[0]
        if proto.name not in palette.objects:palette.objects.link(proto)
new_trees=env.add_layer(terrain,name='Painted tree palette');new_trees.palette=palette
new_trees.density=.012;new_trees.seed=412;new_trees.scale_min=.5;new_trees.scale_max=.8
env.stamp(terrain,new_trees,center+Vector((-24,5,0)),45,1,2)
# Add a retained manual tree inside the clearing and an explicit correction.
proto=env.palette(new_trees)[0]
env.set_override(new_trees,'manual:estuary-hero',proto,Matrix.Translation(center))
first_layer=adopted[0]
if unmodified[first_layer.uid]:
    record=unmodified[first_layer.uid][0];pose=Matrix(record['matrix']);pose.translation.x+=2
    env.set_override(first_layer,record['id'],env.palette(first_layer)[0],pose)
rock_layer=next((l for l in adopted if 'rocks' in l.name),None)
if rock_layer:
    rocks=env.add_layer(terrain,name='Painted rocks');rocks.palette=rock_layer.palette;rocks.align_normal=True
    rocks.density=.008;rocks.scale_min=.7;rocks.scale_max=1.1
    env.stamp(terrain,rocks,center+Vector((28,-8,0)),34,1,2)
terrain.wavelength_environment_material_adapter='PRIVATEER'
terrain.wavelength_environment_native_material='res://development/environment/maps/city-design/iteration-11/runtime/materials/Terrain.res'
paint=env.add_layer(terrain,'MATERIAL','Meadow clearing');paint.biome='1'
env.stamp(terrain,paint,center,29,1,10)
base=terrain.data.materials[0]
original_nodes=len(base.node_tree.nodes)
materials.refresh(terrain)
assert len(base.node_tree.nodes)==original_nodes
assert terrain.data.materials[0]!=base
assert any(m.type=='NODES' and m.node_group.get('wl_environment_mask_attributes') for m in terrain.modifiers)
for layer in terrain.wavelength_environment_layers:
    if layer.kind=='DISTRIBUTION':env.preview(context,terrain,layer)
context.view_layer.update()
expected={l.uid:env.records(context,terrain,l) for l in terrain.wavelength_environment_layers if l.kind=='DISTRIBUTION'}
assert any(r['id']=='manual:estuary-hero' for r in expected[new_trees.uid])
for obj in context.selected_objects:obj.select_set(False)
terrain.select_set(True);context.view_layer.objects.active=terrain
terrain.wavelength_environment_active=len(terrain.wavelength_environment_layers)-1
for area in context.screen.areas if context.screen else []:
    if area.type=='VIEW_3D':
        area.spaces.active.clip_end=30000
        area.spaces.active.region_3d.view_location=center
        area.spaces.active.region_3d.view_distance=190
        area.spaces.active.shading.type='SOLID';area.spaces.active.shading.color_type='MATERIAL'
saved=OUT/'Privateer-Estuary-Editable.blend'
clearing_id=clearing.uid;paint_id=paint.uid;tree_variants=len(palette.objects)
bpy.ops.wm.save_as_mainfile(filepath=str(saved),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(saved))
terrain=bpy.data.objects['Estuary · editable artist patch']
for layer in terrain.wavelength_environment_layers:
    if layer.kind=='DISTRIBUTION':
        current=env.records(context,terrain,layer)
        before={r['id']:r for r in expected[layer.uid]};after={r['id']:r for r in current}
        if before!=after:
            print('REOPEN DIFFERENCE',layer.name,'overrides',layer.overrides,'missing',set(before)-set(after),'extra',set(after)-set(before),flush=True)
            for key in before.keys() & after.keys():
                if before[key]!=after[key]:print('CHANGED',key,before[key],after[key],flush=True);break
        assert before==after
bundle=PROJECT/'development/environment/maps/wavelength-estuary-edit-test/environment'
path,doc=adapter.export(context,[terrain],str(bundle))
assert doc['terrain'][0]['material_adapter']['adapter']=='PRIVATEER'
assert hashlib.file_digest(SOURCE.open('rb'),'sha256').hexdigest()==source_hash
report={'source_sha256':source_hash,'blend':str(saved),'bundle':str(path),'terrain_id':env.identity(terrain),
        'bounds':list(surface.bounds),'center_blender':list(center),
        'placements':sum(len(v) for v in expected.values()),'adopted':sum(len(v) for v in unmodified.values()),
        'original_point_counts':before_counts,'clearing_id':clearing_id,'material_layer':paint_id,
        'tree_variants':tree_variants,'prototype_count':len(doc['prototypes'])}
(OUT/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS PRIVATEER REAL PATCH',json.dumps(report),flush=True)
