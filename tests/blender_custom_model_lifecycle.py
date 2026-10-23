"""Custom sources survive saves, preserve UVs and detach without moving animation."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text(),__file__,'exec'))
from wavelength.source import asset_browser
from mathutils import Vector
import math,struct
original_uv={tuple(round(v,5) for v in loop.uv) for loop in mesh.data.uv_layers.active.data}
compiled_uv={tuple(round(v,5) for v in uv) for uv in data['uvs']}
assert original_uv==compiled_uv,(original_uv,compiled_uv)
asset_browser._ensure_mesh_uv(mesh)
assert {tuple(round(v,5) for v in loop.uv) for loop in mesh.data.uv_layers['wavelength'].data}==original_uv
ctx.view_layer.objects.active=mesh
bpy.ops.object.mode_set(mode='EDIT');asset_browser._ensure_mesh_uv(mesh);bpy.ops.object.mode_set(mode='OBJECT')
entity.rotation_euler.z=math.pi/2;ctx.view_layer.update()
# Game-directory publishing uses a project-local mounted test game.
runtime=folder/'deployment-game';runtime.mkdir(exist_ok=True)
(runtime/'gameinfo.txt').write_text((job.stage/'gameinfo.txt').read_text().replace(str(job.stage),str(runtime)))
real_game=s.game_dir;s.game_dir=str(runtime);s.custom_model_directory=str(runtime)
col.wavelength_model.deployment='GAME'
publisher=custom_models.BuildModels(ctx.scene,job.stage,job.jobs,[]);publisher.validated()
model=dict(json.loads(entity['wl_pairs']))['model'];assert not (runtime/model).exists()
from wavelength.source import source_tools
bsp=folder/'deployment-test.bsp';bsp.write_bytes(b'VBSP'+struct.pack('<i',20)+bytes(64*16+4))
publisher.finish(bsp);assert (runtime/model).is_file()
assert source_assets.Assets(runtime).read(model).startswith(b'IDST')
s.game_dir=real_game;s.custom_model_directory='';col.wavelength_model.deployment='BSP'
print('PASS preserved model UVs, Edit Mode material UV alias, and deferred game-directory asset deployment',flush=True)
mesh_name=mesh.name;entity_name=entity.name
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'custom-lifecycle.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'custom-lifecycle.blend'))
ctx=bpy.context;mesh=bpy.data.objects[mesh_name];entity=bpy.data.objects[entity_name];col=custom_models.definition(entity)
assert col and col.wavelength_model.origin==entity and mesh['wl_custom_model_owner']==entity
before=[mesh.matrix_world@v.co for v in mesh.data.vertices]
ctx.view_layer.objects.active=entity
assert bpy.ops.wavelength.detach_custom_model()=={'FINISHED'}
ctx.view_layer.update()
assert not custom_models.definition(entity) and not mesh.get('wl_custom_model_owner') and not mesh.get('wl_exclude')
assert max((a-mesh.matrix_world@b.co).length for a,b in zip(before,mesh.data.vertices))<1e-5
print('PASS save/reload source ownership and detach preserve visible geometry and restore independent editing',flush=True)
