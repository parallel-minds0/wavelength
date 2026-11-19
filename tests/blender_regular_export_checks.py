"""Standard Blender file exporters share object/collection inclusion checks."""
import sys,json,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
bpy.context.preferences.use_preferences_save=False
addon_utils.enable('wavelength',default_set=True)
addon_utils.enable('io_scene_fbx',default_set=True)
addon_utils.enable('io_scene_gltf2',default_set=True)
from wavelength.source import export_scope,regular_exports
export_scope.enable_policy();regular_exports.install()
c=bpy.context;c.scene.wavelength.auto_prepare_assets=False
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for name,x in [('Included',0),('Excluded',3),('CollectionOff',6)]:
 bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,0));c.object.name=name
bpy.data.objects['Excluded'].hide_render=True
collection=bpy.data.collections.new('Disabled Collection');c.scene.collection.children.link(collection)
obj=bpy.data.objects['CollectionOff']
for parent in list(obj.users_collection):parent.objects.unlink(obj)
collection.objects.link(obj);collection.hide_render=True;c.view_layer.update()
folder=root/'build/regular-export-checks';folder.mkdir(parents=True,exist_ok=True)
selection={obj.name:obj.select_get() for obj in c.scene.objects}
for suffix,operator,kwargs in [('obj',bpy.ops.wm.obj_export,{'export_materials':False}),('ply',bpy.ops.wm.ply_export,{}),('stl',bpy.ops.wm.stl_export,{})]:
 path=folder/('check.'+suffix);result=operator(filepath=str(path),**kwargs);assert result=={'FINISHED'},(suffix,result)
 if suffix=='obj':
  text=path.read_text();assert 'o Included' in text and 'Excluded' not in text and 'CollectionOff' not in text,text[:300]
 elif suffix=='stl':assert struct.unpack_from('<I',path.read_bytes(),80)[0]==12
 elif suffix=='ply':assert b'element face 6\n' in path.read_bytes()[:1000]
 print('PASS native',suffix,flush=True)
path=folder/'check.fbx';assert bpy.ops.export_scene.fbx(filepath=str(path),bake_anim=False)=={'FINISHED'}
data=path.read_bytes();assert b'Included' in data and b'Excluded' not in data and b'CollectionOff' not in data
print('PASS FBX inclusion',flush=True)
path=folder/'check.gltf';assert bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLTF_SEPARATE')=={'FINISHED'}
data=json.loads(path.read_text());names={node.get('name') for node in data.get('nodes',[])}
assert 'Included' in names and 'Excluded' not in names and 'CollectionOff' not in names,names
print('PASS glTF inclusion',flush=True)
path=folder/'check.usda';assert bpy.ops.wm.usd_export(filepath=str(path))=={'FINISHED'}
text=path.read_text();assert 'Included' in text and 'Excluded' not in text and 'CollectionOff' not in text
print('PASS USD inclusion',flush=True)
assert selection=={obj.name:obj.select_get() for obj in c.scene.objects}
# Selection-only remains an additional restriction, never an override.
bpy.ops.object.select_all(action='DESELECT');bpy.data.objects['Excluded'].select_set(True)
path=folder/'selected.obj';bpy.ops.wm.obj_export(filepath=str(path),export_selected_objects=True,export_materials=False)
assert not path.exists() or '\no ' not in path.read_text()
print('PASS selection-only intersection and unchanged authoring selection',flush=True)

path=folder/'check.abc'
assert bpy.ops.wm.alembic_export(filepath=str(path),start=1,end=1,as_background_job=False)=={'FINISHED'}
old=set(c.scene.objects)
assert bpy.ops.wm.alembic_import(filepath=str(path),as_background_job=False)=={'FINISHED'}
names={obj.name for obj in c.scene.objects if obj not in old}
assert names and all('Excluded' not in name and 'CollectionOff' not in name for name in names),names
print('PASS Alembic inclusion',flush=True)
