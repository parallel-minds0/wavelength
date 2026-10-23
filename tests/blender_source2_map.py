"""Actual CS2 material decoding, VMAP round trip and Valve DMX validation."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import source2_assets as assets,source2_map as maps,source2_dmx as dmx,textures,asset_browser
bpy.context.preferences.use_preferences_save=False
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source2_cs2_windows'
root=Path(__file__).resolve().parents[1]/'build/source2-map';root.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
names=textures.all_names(s);assert 'anubis/mudbrick02' in names
mat=textures.material(s,'anubis/mudbrick02')
assert mat['wl_source2_material']=='materials/anubis/mudbrick02.vmat'
assert any(n.type=='TEX_IMAGE' and n.image and n.image.size[0]>1 for n in mat.node_tree.nodes)
preview=asset_browser.publish_material_fast(s,'anubis/mudbrick02',existing_by_id={})
assert preview.asset_data and preview.preview.image_size[0]>0
mat=textures.material(s,'anubis/mudbrick02',target_mat=mat)
print('PASS CS2 material index, compiled VMAT/VTEX decoding, thumbnail and full material',flush=True)
bpy.ops.mesh.primitive_cube_add(size=2,location=(1,2,3));cube=ctx.object;cube.data.materials.append(mat)
cube.rotation_euler=(.1,.2,.3);cube.scale=(-1,2,1)
uv=cube.data.uv_layers.active
original=[tuple(x.uv) for x in uv.data];original_mesh=cube.data
path=root/'roundtrip.vmap';count,warnings=maps.export(ctx,path);assert count==1
document=dmx.loads(path.read_text());geometry=dmx.read_mesh(document.get('world').get('children')[0].get('meshData'))
assert len(geometry[0])==8 and len(geometry[1])==6 and geometry[3]==['materials/anubis/mudbrick02.vmat']
assert cube.data==original_mesh and [tuple(x.uv) for x in uv.data]==original
binary=root/'binary.vmap';assets.run([maps.converter(s),'-i',path,'-o',binary,'-oe','binary'])
assert binary.is_file(), 'Valve DMX rejected generated VMAP'
loaded=maps.load(binary,s);assert loaded.kind=='CMapRootElement'
count,warnings=maps.import_map(ctx,binary);assert count==1
imported=list(ctx.scene.collection.children)[-1].objects[0]
assert len(imported.data.polygons)==6
expected=sorted(tuple(round(c,4) for c in cube.matrix_world@v.co) for v in cube.data.vertices)
actual=sorted(tuple(round(c,4) for c in v.co) for v in imported.data.vertices)
assert actual==expected,(actual,expected)
def corners(obj,world):
    result=[];uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            point=obj.data.vertices[obj.data.loops[loop].vertex_index].co
            if world:point=obj.matrix_world@point
            result.append(tuple(round(c,4) for c in point)+tuple(round(c,4) for c in uv.data[loop].uv))
    return sorted(result)
assert corners(cube,True)==corners(imported,False),'VMAP corner UVs changed during mirrored-transform round trip'
assert imported.data.materials[0]['wl_source2_material']==mat['wl_source2_material']
print('PASS VMAP: Valve binary conversion and mesh/material/transform round trip',flush=True)
shipped=Path(s.game_dir).parents[1]/'content/csgo/maps/editor/toolscene_default.vmap'
count,warnings=maps.import_map(ctx,shipped);assert count>=1
print('PASS shipped CS2 binary VMAP editable mesh import',flush=True)
custom=bpy.data.materials.new('Custom VMAP material');custom.use_nodes=True
custom.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.8,.1,.2,1)
cube.data.materials.clear();cube.data.materials.append(custom)
bpy.ops.object.select_all(action='DESELECT');cube.select_set(True);ctx.view_layer.objects.active=cube
custom_path=root/'custom-content/maps/custom.vmap'
count,warnings=maps.export(ctx,custom_path,selected=True)
assert count==1
material_files=list((root/'custom-content/materials/wavelength/custom').glob('*.vmat'))
assert len(material_files)==1 and material_files[0].with_suffix('.png').is_file()
count,warnings=maps.import_map(ctx,custom_path);assert count==1 and not warnings,warnings
print('PASS custom VMAT/PNG sidecars under content root and material re-import',flush=True)
assert bpy.ops.wavelength.export_map('EXEC_DEFAULT',export_format='VMAP',filepath=str(root/'operator.vmap'))=={'FINISHED'}
print('PASS SOURCE2 MAPS',flush=True)
