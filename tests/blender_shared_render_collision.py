"""Compile the saved user's models without modifying their map or game files."""
import sys,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
bpy.context.preferences.use_preferences_save=False
from wavelength.source import custom_models,export_scope,studio_model,source_assets,scene,context_policy
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\user\Projects\focus\video games\HL2-MOD\trainstation\trainstation.blend')
c=bpy.context;c.scene.wavelength.auto_prepare_assets=False
folder=root/'build/shared-render-collision';folder.mkdir(parents=True,exist_ok=True)
c.scene.wavelength.project_dir=str(folder)
owners=[obj for obj in c.scene.objects if obj.get('wl_custom_model')]
assert len(owners)>=2
for owner in owners:
 col=custom_models.definition(owner);source=col.wavelength_model.collision
 assert source and source.get('wl_custom_model_owner')==owner
 assert export_scope.Scope(c.scene).includes(owner),owner.name
 assert context_policy.role(source,c.scene.wavelength.engine)=='CONTENT'
job=custom_models.prepare(c.scene,folder/'compile')
assert job and len(job.jobs)==len(owners)
for i,command in enumerate(job.commands):
 result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=120)
 (folder/f'compiler-{i}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
 assert result.returncode==0,result.stdout[-3000:]+result.stderr[-1000:]
job.validated()
for owner in owners:
 path=dict(json.loads(owner['wl_pairs']))['model']
 data=studio_model.load(source_assets.Assets(job.stage),path)
 assert data['vertices'] and data['faces'],owner.name
 assert (job.stage/path).with_suffix('.phy').is_file(),owner.name
 print('PASS saved model',owner.name,'render triangles',len(data['faces']),'collision companion exists',flush=True)
document=scene.export_map(c.scene)
paths={dict(entity.pairs).get('model') for entity in document.entities}
assert all(dict(json.loads(owner['wl_pairs']))['model'] in paths for owner in owners)
assert any(name.endswith('.mdl') for name in job.pack)
print('PASS saved map includes model entities and BSP package includes compiled models',flush=True)
