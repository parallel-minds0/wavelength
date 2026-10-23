"""Compile editable custom models with the installed game's actual StudioMDL."""
import sys,time,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import custom_models,studio_model,source_assets,model_formats
from wavelength.source.ui import _spawn_point_entity
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.compiler_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin';s.fgd_path=''
s.auto_prepare_assets=False  # Tests start their own bounded preparation workers explicitly.
folder=root/'build/custom-models';folder.mkdir(exist_ok=True);s.project_dir=str(folder)
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1,location=(2,0,1));mesh=ctx.object;mesh.name='Editable source'
mat=bpy.data.materials.new('Custom color');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.2,.5,.8,1);mesh.data.materials.append(mat)
entity=_spawn_point_entity(ctx,'prop_static');entity.location=(2,0,0);mesh.select_set(True);entity.select_set(True);ctx.view_layer.objects.active=entity
world=[mesh.matrix_world@v.co for v in mesh.data.vertices];col=custom_models.assign(ctx);ctx.view_layer.update()
assert max((a-mesh.matrix_world@b.co).length for a,b in zip(world,mesh.data.vertices))<1e-6
job=custom_models.prepare(ctx.scene,folder/'first');assert len(job.commands)==1
for i,cmd in enumerate(job.commands):
    result=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=60)
    (folder/f'model-stage-{i}.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout[-4000:]+result.stderr[-1000:]
job.validated();assert job.pack and any(n.endswith('.mdl') for n in job.pack)
data=studio_model.load(source_assets.Assets(job.stage),dict(json.loads(entity['wl_pairs']))['model'])
assert data['static'] and len(data['faces'])==12
assert min(p[2] for p in data['vertices'])>-1 and max(p[2] for p in data['vertices'])>50
cached=custom_models.prepare(ctx.scene,folder/'cached');assert not cached.commands;cached.validated()
entity.location.x+=10;ctx.view_layer.update();moved=custom_models.prepare(ctx.scene,folder/'moved');assert not moved.commands
entity.location.x-=10;ctx.view_layer.update()
mesh.data.vertices[0].co.x-=.1;changed=custom_models.prepare(ctx.scene,folder/'changed');assert changed.commands
print('PASS real StudioMDL compiled editable static source, generated material/VTF, cached unchanged dependencies and invalidated mesh edits',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'custom-model.blend'))
