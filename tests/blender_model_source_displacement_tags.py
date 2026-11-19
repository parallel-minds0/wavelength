"""Assigned prop sources must not retain stale displacement-export identity."""
from pathlib import Path
fixture=Path(__file__).with_name('blender_custom_model_build.py').read_text()
tags=('wl_source_displacement','wl_terrain_face_corners','wl_terrain_source_corners',
      'wl_terrain_face_matrix','wl_terrain_face_id','wl_displacement','wl_terrain',
      'wl_terrain_seams','wl_terrain_detached')
injection='\nfor tag in '+repr(tags)+':mesh[tag]="stale displacement metadata"\n'
fixture=fixture.replace("entity=_spawn_point_entity(ctx,'prop_static')",injection+"entity=_spawn_point_entity(ctx,'prop_static')")
fixture=fixture.replace('job=custom_models.prepare(ctx.scene,folder/\'first\')',
    'assert not any(tag in mesh for tag in '+repr(tags)+')\njob=custom_models.prepare(ctx.scene,folder/\'first\')')
exec(compile(fixture,__file__,'exec'))
from wavelength.source import source_displacement
parent=bpy.data.objects.new('Displacement source test',None)
ctx.scene.collection.objects.link(parent)
mesh.parent=parent;mesh[source_displacement.KEY]='{}'
assert mesh.get('wl_custom_model_owner')
assert mesh not in source_displacement.surfaces(parent)
ordinary=bpy.data.objects.new('Normal displacement test',bpy.data.meshes.new('Normal displacement mesh'))
ctx.scene.collection.objects.link(ordinary);ordinary.parent=parent;ordinary[source_displacement.KEY]='{}'
assert ordinary in source_displacement.surfaces(parent)
print('PASS stale displacement tags cleared, real prop_static MDL compile, model sources excluded from displacement surfaces',flush=True)
