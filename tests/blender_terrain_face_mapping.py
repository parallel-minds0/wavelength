from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,addon_utils

addon_utils.enable('wavelength',default_set=False)
from wavelength.source import scene,terrain_face,terrain_sew

context=bpy.context
context.workspace['wl_workspace']=True
context.scene.wavelength.auto_prepare_assets=False
context.scene.wavelength.engine='blender'
for obj in list(context.scene.objects):
    bpy.data.objects.remove(obj,do_unlink=True)
material=bpy.data.materials.new('Mapped terrain material')
material['wl_texture']='nature/dirtfloor001a'
for x in (0,2,10):
    bpy.ops.mesh.primitive_plane_add(size=2,location=(x,0,0))
    context.object.data.materials.append(material)
for obj in context.scene.objects:
    obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
terrain_face.map_selected_faces(context)
patches=sorted((o for o in context.scene.objects if o.get('wl_face_mapping')),key=lambda p:p.parent.location.x)
assert len(patches)==3
assert set(terrain_sew.network(patches[0]))==set(patches[:2])
assert terrain_sew.network(patches[2])==[patches[2]]
for patch in patches:
    host=patch.parent
    modifier=terrain_face.mapping_modifier(patch)
    assert len(host.data.polygons)==1
    assert len(host.evaluated_get(context.evaluated_depsgraph_get()).data.polygons)==64**2
    modifier.show_viewport=False
    context.view_layer.update()
    assert len(host.evaluated_get(context.evaluated_depsgraph_get()).data.polygons)==1
    exported=terrain_face.export_mesh(host,context.evaluated_depsgraph_get())
    assert len(exported.polygons)==64**2 and not modifier.show_viewport
    bpy.data.meshes.remove(exported)
    modifier.show_viewport=True
    context.view_layer.update()
retired={'map_heightfields','copy_heightfield_inputs','edit_heightfield_group',
         'terrain_add','terrain_paint','terrain_sew','terrain_finalize',
         'terrain_blend','displacement_from_face'}
assert retired.isdisjoint(dir(bpy.ops.wavelength))
assert not hasattr(bpy.types,'WL_PT_face_heightfields')
assert not hasattr(bpy.types,'WL_PT_mapped_terrain_paint')
for patch in patches:
    patch.wavelength_terrain.elevation=.2
context.view_layer.update()
assert max(v.co.z for v in patches[0].parent.evaluated_get(context.evaluated_depsgraph_get()).data.vertices)>.19
terrain_sew.validate_export(patches[0])
modifier=terrain_face.mapping_modifier(patches[1])
modifier.show_render=False
exported=terrain_face.export_mesh(patches[1].parent,context.evaluated_depsgraph_get())
assert len(exported.polygons)==1 and modifier.show_viewport
bpy.data.meshes.remove(exported)
context.scene.wavelength.engine='source_hl2_windows'
document=scene.export_map(context.scene)
assert len(document.entities[0].brushes)==2
assert all(brush[0].vmf['dispinfo'] for brush in document.entities[0].brushes)
bpy.ops.mesh.primitive_cube_add(size=2,location=(20,0,0))
brush=context.object
scene.mark_brush(brush)
brush.data.materials.append(material)
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(brush.data)
for face in bm.faces:face.select_set(False)
for face in bm.faces:
    if face.normal.z>.9 or face.normal.x>.9:face.select_set(True)
bmesh.update_edit_mesh(brush.data)
terrain_face.map_selected_faces(context)
brush_patches=[o for o in brush.children if o.get('wl_face_mapping')]
assert len(brush_patches)==2 and set(terrain_sew.network(brush_patches[0]))==set(brush_patches)
patch=brush_patches[0]
document=scene.export_map(context.scene)
assert len(document.entities[0].brushes)==3
assert sum(bool((f.vmf or {}).get('dispinfo')) for b in document.entities[0].brushes for f in b)==4
terrain_face.mapping_modifier(patch).show_render=False
document=scene.export_map(context.scene)
assert len(document.entities[0].brushes)==3
assert sum(bool((f.vmf or {}).get('dispinfo')) for b in document.entities[0].brushes for f in b)==2
print('PASS multi-mesh face mapping, automatic seams, geometry controls, viewport/render switches and Source export',flush=True)

# Paint the two hidden controls from an active visible host. Source layers are
# built in an isolated game folder that mounts the installed game textures.
from mathutils import Vector
from wavelength.source import terrain,terrain_paint,source_assets,vmf

root=Path(__file__).resolve().parents[1]/'build/mapped-terrain-paint'
game=root/'game'
game.mkdir(parents=True,exist_ok=True)
real=source_assets.library(r'C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete')
paths=[str(m.path if isinstance(m,source_assets.VPK) else m).replace(chr(92),'/') for m in real.mounts]
search_paths=''.join('Game "'+path+'"\n' for path in paths)
(game/'gameinfo.txt').write_text('GameInfo { game "Paint test" FileSystem { SteamAppId 220 SearchPaths { Game "|gameinfo_path|."\n'+search_paths+' } } }',encoding='utf-8')
settings=context.scene.wavelength
settings.game_dir=str(game)
settings.project_dir=str(root/'project')
a,b=patches[:2]
for obj in context.selected_objects:obj.select_set(False)
a.parent.select_set(True)
context.view_layer.objects.active=a.parent
assert terrain_paint.paint_target(context,a.name)==a
terrain_face.mapping_modifier(b).show_render=True
base_material=source_assets.material(settings,'brick/brickwall001a')
paint_material=source_assets.material(settings,'nature/dirtfloor001a')
transition=terrain.create_blend(a,context,base=base_material,paint=paint_material)
b.data.materials[0]=transition
terrain.sync_material(b,force=True)
assert transition.get('wl_source_blend') and b.data.materials[0]==transition
assert (game/'materials'/(transition['wl_texture']+'.vmt')).is_file()
context.view_layer.update()
hit,_,_,_=a.evaluated_get(context.evaluated_depsgraph_get()).ray_cast(Vector((0,0,2)),Vector((0,0,-1)))
assert hit and a.hide_get()
members=terrain_sew.network(a)
base=terrain_sew.frames(members)
point=Vector((1,0,0));direction=Vector((0,0,1))
assert terrain_paint.network_stroke(members,base,point,direction,'RAISE',.8,.3,.6)
height_snapshot={obj:terrain_sew.positions(obj,base[obj]) for obj in members}
assert terrain_paint.network_stroke(members,base,point,direction,'TEXTURE',.8,.3,.6)
assert all(height_snapshot[obj]==terrain_sew.positions(obj,base[obj]) for obj in members)
context.view_layer.update()
terrain_sew.validate_export(a)
document=vmf.parse(vmf.write(scene.export_map(context.scene)))
painted=[face.vmf['dispinfo'] for entity in document.entities for solid in entity.brushes for face in solid
         if face.texture==transition['wl_texture'] and (face.vmf or {}).get('dispinfo')]
assert len(painted)==2
assert all(max(max(row) for row in data['alphas'])>0 for data in painted)
assert all(max(max(row) for row in data['distances'])>.1 for data in painted)
assert a.modifiers and b.modifiers and context.object==a.parent
print('PASS hidden mapped paint targets, sewn height/texture strokes, generated VMT and VMF roundtrip',flush=True)

from wavelength.source import terrain_migration
copy = terrain_migration.migrate_legacy(context, a)
assert copy['wl_exclude'] and copy['wl_terrain_migration_source'] == a
assert copy.data.polygons and copy.data.attributes.get('wl_terrain_blend')
assert vmf.write(scene.export_map(context.scene)) == vmf.write(document)
print('PASS legacy evaluated mesh migration preserves paint and leaves VMF export intact')
