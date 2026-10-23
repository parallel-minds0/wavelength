import sys,json,traceback,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import mesh_assets,profiles,scene
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
root=Path(__file__).resolve().parents[1]/'build/mesh-assets';root.mkdir(exist_ok=True)
try:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
    ctx.scene.wavelength.engine='godot4';ctx.scene.wavelength.map_name='mesh_smoke'
    image=bpy.data.images.new('Export checker',2,2,alpha=True)
    image.pixels[:]=[1,0,0,1,0,1,0,1,0,0,1,1,1,1,1,1]
    material=bpy.data.materials.new('Export painted');material.use_nodes=True
    tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    material.node_tree.links.new(tex.outputs['Color'],material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    bpy.ops.mesh.primitive_cube_add(location=(0,0,1));obj=ctx.object;obj.name='StaticCube';obj.data.materials.append(material)
    obj['private_entity_metadata']='must not export'
    bpy.ops.mesh.primitive_cube_add(location=(20,0,0));helper=ctx.object;helper['wl_exclude']=True
    bpy.ops.mesh.primitive_cube_add(location=(30,0,0));entity_child=ctx.object
    parent=bpy.data.objects.new('Entity helper',None);ctx.collection.objects.link(parent);parent['wl_role']='ENTITY';entity_child.parent=parent
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj;ctx.view_layer.update()
    initial=(obj.data,obj.matrix_world.copy(),list(obj.data.materials),set(bpy.data.objects),set(bpy.data.materials),set(bpy.data.images))
    path,manifest=mesh_assets.export(ctx,str(root/'godot'))
    assert len(manifest['objects'])==1 and not manifest['entities']
    data=path.read_bytes();assert data[:4]==b'glTF'
    size,kind=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+size])
    assert doc['meshes'] and doc['images'] and doc['textures'] and not any('extras' in n for n in doc.get('nodes',[]))
    assert not doc.get('animations') and not doc.get('skins')
    print('PASS Godot GLB contains mesh, UVs and embedded image; no helpers or entity metadata',flush=True)
    assert obj.data==initial[0] and obj.matrix_world==initial[1] and list(obj.data.materials)==initial[2]
    assert set(bpy.data.objects)==initial[3] and set(bpy.data.materials)==initial[4] and set(bpy.data.images)==initial[5]
    assert list(ctx.selected_objects)==[obj] and ctx.object==obj
    assert list(image.pixels[:4])==[1.,0.,0.,1.]
    print('PASS source data, transforms, selection and materials unchanged; no temporary ID leaks',flush=True)
    prior=path.read_bytes();noise=material.node_tree.nodes.new('ShaderNodeTexNoise')
    material.node_tree.links.new(noise.outputs['Color'],material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    try:mesh_assets.export(ctx,str(root/'godot'))
    except ValueError as exc:assert 'bake' in str(exc).lower()
    else:raise AssertionError('Unsupported shader silently exported')
    material.node_tree.nodes.remove(noise)
    material.node_tree.links.new(tex.outputs['Color'],material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    assert path.read_bytes()==prior and set(bpy.data.objects)==initial[3] and set(bpy.data.images)==initial[5]
    print('PASS unsupported shader preserves previous export and cleans staging data',flush=True)
    ctx.scene.wavelength.engine='source2_cs2_windows';ctx.scene.wavelength.map_name='mesh_smoke'
    assert not profiles.requires_convex_brushes(ctx.scene.wavelength.engine)
    path,manifest=mesh_assets.export(ctx,str(root/'cs2'),True)
    assert path.suffix=='.vmdl' and path.is_file()
    assert len(manifest['objects'])==1 and manifest['meters_per_unit']==.0254
    assert list(path.parent.glob('*.fbx')) and list((path.parents[3]/'materials/wavelength/mesh_smoke').glob('*.vmat'))
    print('PASS CS2 FBX, VMAT, PNG and ModelDoc bundle',path,flush=True)
    # A procedural basic cube must evaluate directly, without BSP finalization.
    bpy.ops.wavelength.primitive(kind='CUBE',width=32,run=32,depth=32)
    ctx.scene.wavelength.map_name='procedural_smoke'
    path,manifest=mesh_assets.export(ctx,str(root/'cs2'),True)
    assert len(manifest['objects'])==1
    print('PASS procedural node mesh exports without destructive finalization',flush=True)
    print('PASS MESH ASSETS',flush=True)
except Exception:traceback.print_exc();print('FAIL MESH ASSETS',flush=True)
