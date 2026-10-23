"""Surface stamping is independent of scene selection and Edit/Object Mode."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import asset_placement as placement,textures,scene
import bmesh
s.engine='goldsrc_windows'
names=[n for n in textures.all_names(s) if n.lower().startswith('c1a0')][:2]
materials=[textures.material(s,n) for n in names]
bpy.ops.mesh.primitive_cube_add();obj=ctx.object;scene.mark_brush(obj);s.texture=names[0]
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
data=json.dumps(dict(category='MATERIAL',path=names[1],engine=s.engine,material=materials[1].name))
before=json.loads(obj.data['wl_faces']);uv_before=[tuple(v.uv) for v in obj.data.uv_layers['wavelength'].data]
assert bpy.ops.wavelength.stamp_asset(data=data,object_name=obj.name,face=1,scope='SURFACE')=={'FINISHED'}
assert sum(obj.data.materials[p.material_index]==materials[1] for p in obj.data.polygons)==1
records=json.loads(obj.data['wl_faces']);assert sum(v['texture']!=before[k]['texture'] for k,v in records.items())==1
for polygon in obj.data.polygons:
    if polygon.index!=1:
        assert all(tuple(obj.data.uv_layers['wavelength'].data[i].uv)==uv_before[i] for i in polygon.loop_indices)
bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
for face in bm.faces:face.select_set(False)
bm.faces[4].select_set(True);bmesh.update_edit_mesh(obj.data)
selection=[face.select for face in bm.faces]
assert bpy.ops.wavelength.stamp_asset(data=data,object_name=obj.name,face=2,scope='SURFACE')=={'FINISHED'}
bm=bmesh.from_edit_mesh(obj.data);assert [face.select for face in bm.faces]==selection and obj.mode=='EDIT'
assert sum(obj.data.materials[f.material_index]==materials[1] for f in bm.faces)==2
bpy.ops.object.mode_set(mode='OBJECT')
assert bpy.ops.wavelength.stamp_asset(data=data,object_name=obj.name,face=0,scope='OBJECT')=={'FINISHED'}
assert all(obj.data.materials[p.material_index]==materials[1] for p in obj.data.polygons)
cursor=ctx.scene.cursor.location.copy();data=json.dumps(dict(category='ENTITY',path='info_target',engine=s.engine))
assert bpy.ops.wavelength.stamp_asset(data=data,location=(1.25,2.5,3.75))=={'FINISHED'}
assert tuple(ctx.object.location)==(1.25,2.5,3.75) and ctx.scene.cursor.location==cursor
assert dict(json.loads(ctx.object['wl_pairs']))['classname']=='info_target'
print('PASS clicked surface only in Object/Edit Mode, unchanged neighboring UVs and face selection, whole-object scope and entity placement without moving 3D cursor',flush=True)
