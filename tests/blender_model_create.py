"""Ordinary Blender meshes become a standalone editable model without geometry changes."""
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import wavelength
from wavelength.source import model_io,model_lifecycle as life,model_pipeline,textures,export_scope
wavelength.register()
ctx=bpy.context
with patch.object(textures,'refresh'):
    ctx.scene.wavelength.engine='source_hl2_windows'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(location=(3,4,5))
mesh=ctx.object
mesh.rotation_euler=(.2,.3,.4)
mesh.scale=(2,1,.5)
ctx.view_layer.update()
before=[mesh.matrix_world@v.co for v in mesh.data.vertices]
data=mesh.data
assert bpy.ops.wavelength.create_model_asset(name='Curved track')=={'FINISHED'}
asset=model_io.active_asset(ctx)
assert asset and asset.name=='Curved track' and mesh.data==data
assert life.bindings(asset)==[] and mesh.get('wl_exclude')
ctx.view_layer.update()
assert max((a-mesh.matrix_world@v.co).length for a,v in zip(before,mesh.data.vertices))<1e-5
assert ctx.object==mesh
scope=export_scope.Scope(ctx.scene)
assert scope.includes_model_sources(asset)
collections=set(bpy.data.collections)
try:
    life.create(ctx,'Repeated')
except ValueError as exc:
    assert 'already belongs' in str(exc)
else:
    raise AssertionError('Accepted duplicate model ownership')
assert set(bpy.data.collections)==collections
# The ordinary source enters the actual Source adapter preparation path.
folder=Path(__file__).resolve().parents[1]/'build/authored-model'
folder.mkdir(parents=True,exist_ok=True)
s=ctx.scene.wavelength
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
s.compiler_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/bin'
s.project_dir=str(folder)
# Creation records the active game as ownership, so use its captured value.
asset['wl_model_game']=s.game_dir
job=model_pipeline.get('source1').prepare(ctx,asset,folder/'stage')
assert job.commands or job.build.jobs
for command in job.commands:
    result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=90)
    assert result.returncode==0,result.stdout[-2000:]+result.stderr[-1000:]
job.build.validated()
assert mesh.data==data
print('PASS authored model creation, world pose, ownership rejection and Source build preparation')
