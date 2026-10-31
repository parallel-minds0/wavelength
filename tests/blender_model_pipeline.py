"""End-to-end model adapter round trip through the real Source compiler."""
import sys,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_io,model_pipeline,source_assets,studio_model,model_import
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows'
s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
s.compiler_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin';s.fgd_path=''
folder=root/'build/model-pipeline';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
# Extract an installed static model and its binary peers, without decompilers.
assets=source_assets.library(s.game_dir);local=folder/'input';local.mkdir(exist_ok=True)
path='models/props_c17/oildrum001.mdl'
for suffix in ('.mdl','.vvd','.dx90.vtx'):
 (local/('oildrum001'+suffix)).write_bytes(assets.read(path[:-4]+suffix))
original=(local/'oildrum001.mdl').read_bytes()
asset=model_io.import_asset(ctx,str(local/'oildrum001.mdl'))
obj=ctx.object;assert obj.type=='MESH' and obj.get('wl_role')=='MODEL_SOURCE'
assert model_io.active_asset(ctx)==asset and model_pipeline.get(asset['wl_model_backend']).supports(s.engine)
assert not obj.get('wl_model_reference') and obj.data.users==1
obj.data.vertices[0].co.z+=.01
# Build this asset alone and validate the actual compiler output. Redirect only
# the final deployment to the test folder, never modify the installed game.
job=model_pipeline.get('source1').prepare(ctx,asset,folder/'stage')
assert len(job.build.jobs)==1
for command in job.commands:
 result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=90)
 (folder/'compiler.log').write_text(result.stdout+result.stderr)
 assert result.returncode==0,result.stdout[-2500:]+result.stderr[-1000:]
original_deploy=job.build.deploy
# Validation still checks real mounted destinations; redirect after validation.
def deploy():
 assert job.build.deployments
 job.build.deployments=[(folder/'deployed',files) for _,files in job.build.deployments]
 original_deploy()
job.build.deploy=deploy
from wavelength.source import model_browser
original_publish=model_browser.published
model_browser.published=lambda context,path:None
output=job.finish();model_browser.published=original_publish;assert output.startswith('models/wavelength/')
class Deployed:
 def read(self,name):return (folder/'deployed'/name).read_bytes()
data=studio_model.load(Deployed(),output)
assert data['static'] and data['faces']
assert (local/'oildrum001.mdl').read_bytes()==original
assert model_io.active_asset(ctx)==asset
print('PASS engine-neutral asset identity, editable independent MDL import, real StudioMDL rebuild, validated deployment, original asset preserved',flush=True)
# A different adapter uses exactly the same core dispatch.
class Fake:
 id='test';extensions={'.test'}
 def supports(self,engine):return engine=='test'
model_pipeline.register(Fake());assert model_pipeline.backend_for('test','mesh.test').id=='test'
model_pipeline.unregister('test')
try:model_pipeline.backend_for('test','mesh.test')
except ValueError:pass
else:raise AssertionError('Removed adapter still available')
print('PASS engine-independent backend registration/removal and format routing',flush=True)

