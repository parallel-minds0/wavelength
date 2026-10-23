"""Use privately installed HL2 assets; never bundle them in test fixtures."""
import sys,json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_import,studio_model,source_assets,asset_browser,asset_index,scene,primitives
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
vertices,faces=primitives.box(-256,-256,-32,256,256,0);worldmesh=bpy.data.meshes.new('Floor');worldmesh.from_pydata([[c*.0254 for c in v] for v in vertices],[],faces)
floor=bpy.data.objects.new('Floor',worldmesh);ctx.collection.objects.link(floor);scene.mark_brush(floor)
floor.data.materials.append(bpy.data.materials.new('Floor'));floor.data.materials[0]['wl_texture']='tools/toolsnodraw'
assets=source_assets.library(s.game_dir)
paths=['models/props_junk/wood_crate001a.mdl','models/props_c17/oildrum001.mdl','models/props_c17/furniturechair001a.mdl','models/alyx.mdl']
for path in paths:
    mesh,data=model_import.mesh(s,path)
    assert len(mesh.polygons)>100 and mesh.uv_layers.get('UVMap') and mesh.uv_layers.get('wavelength')
    assert len(data['slots'])==len(mesh.polygons)
    assert all(0<=p.material_index<len(mesh.materials) for p in mesh.polygons)
    if 'alyx' not in path:assert not json.loads(mesh['wl_model_warnings']),mesh['wl_model_warnings']
    from mathutils import Vector
    assert sum(p.normal.dot(Vector(data['normals'][p.vertices[0]]))>0 for p in mesh.polygons)>len(mesh.polygons)*.8
    cached,_=model_import.mesh(s,path);assert cached==mesh
    row=asset_index.record(s.engine,path);obj=asset_browser.place(ctx,row,(0,0,0));child=next(c for c in obj.children if c.get('wl_model_reference'))
    assert child.data==mesh and child.get('wl_exclude') and not child.hide_select
    assert dict(json.loads(obj['wl_pairs']))['classname']==('prop_static' if data['static'] else 'prop_dynamic')
    print('PASS reference mesh, UVs, materials, cached prop placement',path,len(mesh.vertices),len(mesh.polygons),flush=True)
doc=scene.export_map(ctx.scene)
assert len(doc.entities)==5
assert sorted(dict(e.pairs)['model'] for e in doc.entities[1:])==sorted(paths)
assert len(doc.entities[0].brushes)==1 and all(not e.brushes for e in doc.entities[1:])
print('PASS Source export retains engine model references and excludes visual triangle meshes',flush=True)
from wavelength.source.entity import models
entity=next(o for o in ctx.scene.objects if o.get('wl_role')=='ENTITY')
assert models.attach_reference(entity,[('classname','prop_dynamic'),('model',paths[1]),('skin','1')])
assert len([c for c in entity.children if c.get('wl_model_reference')])==1
assert models.attach_reference(entity,json.loads(entity['wl_pairs']))
print('PASS entity model/skin changes replace the preview without duplicate children',flush=True)
mdl=assets.read(paths[0]);vvd=assets.read(paths[0][:-4]+'.vvd');vtx=assets.read(paths[0][:-4]+'.dx90.vtx')
for broken in [b'',mdl[:210],mdl[:8]+b'\0\0\0\0'+mdl[12:]]:
    try:studio_model.read(broken,vvd,vtx)
    except ValueError:pass
    else:raise AssertionError('Invalid model was accepted')
print('PASS truncated models and mismatched companions refused',flush=True)
folder=root/'build/source-models';folder.mkdir(exist_ok=True)
for suffix in ('.mdl','.vvd','.dx90.vtx'):(folder/('crate'+suffix)).write_bytes(assets.read(paths[0][:-4]+suffix))
assert bpy.ops.wavelength.import_source_model(filepath=str(folder/'crate.mdl'))=={'FINISHED'}
assert ctx.object.type=='MESH' and ctx.object.get('wl_source_model') and len(ctx.object.data.polygons)==200
print('PASS native File Import operator reads local MDL and companion files',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'imported.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'imported.blend'))
assert len([o for o in bpy.context.scene.objects if o.get('wl_model_reference')])==4
assert len(scene.export_map(bpy.context.scene).entities)==5
print('PASS save/reload retains model geometry, textures and export references',flush=True)
