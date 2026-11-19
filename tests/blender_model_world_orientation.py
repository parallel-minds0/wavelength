import sys,json,subprocess,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import custom_models,studio_model,source_assets
from wavelength.source.ui import _spawn_point_entity
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.compiler_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin';s.fgd_path=''
folder=root/'build/model-world-orientation';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=1,location=(2,3,4));obj=c.object;obj.scale=(.7,1.3,2.1);obj.rotation_euler=(.2,.3,.6)
entity=_spawn_point_entity(c,'prop_static');entity.location=(1,2,3);entity.rotation_euler=(.1,.4,-.8)
c.view_layer.update();world=[obj.matrix_world@v.co for v in obj.data.vertices]
obj.select_set(True);entity.select_set(True);c.view_layer.objects.active=entity
col=custom_models.assign(c);c.view_layer.update()
assert max((a-obj.matrix_world@b.co).length for a,b in zip(world,obj.data.vertices))<1e-5
job=custom_models.prepare(c.scene,folder/'compile')
for cmd in job.commands:
 result=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=90)
 (folder/'compiler.log').write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0,result.stdout[-1500:]
data=studio_model.load(source_assets.Assets(job.stage),dict(json.loads(entity['wl_pairs']))['model'])
points=[entity.matrix_world@(Vector(p)*entity['wl_unit_meters']) for p in data['vertices']]
error=max(min((p-q).length for q in points) for p in world)
print('COMPILED WORLD ORIENTATION MAX ERROR',error,flush=True)
print('EXPECTED',tuple(world[0]),'COMPILED',[tuple(p) for p in points[:3]],flush=True)

assert error<1e-5,error
print('PASS compiled asymmetric mesh preserves Blender world orientation including rotated entity and nonuniform mesh scale',flush=True)

from wavelength.source import scene as scene_io
bpy.ops.mesh.primitive_cube_add(size=.7,location=(2,3,4));collider=c.object;collider.name='External collision source';collider.rotation_euler=(.2,.3,.6)
scene_io.mark_brush(collider)
assert collider.name not in col.objects
state=col.wavelength_model
for mode in ('CONVEX','BOX','OBJECT'):
 state.collision_mode=mode;state.collision=collider
 c.view_layer.update()
 job=custom_models.prepare(c.scene,folder/mode.lower())
 for cmd in job.commands:
  result=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=90)
  (folder/(mode+'-compiler.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
  assert result.returncode==0,result.stdout[-3000:]+result.stderr[-1000:]
 path=job.stage/dict(json.loads(entity['wl_pairs']))['model']
 assert path.with_suffix('.phy').is_file(),mode
 smd=(folder/mode.lower()/'model_sources'/col['wl_custom_model_id']/'collision.smd').read_text()
 lines=smd.split('triangles\n',1)[1].splitlines()
 verts=[tuple(float(v) for v in line.split()[1:4]) for line in lines if len(line.split())==9]
 assert verts,mode
 if mode=='BOX':assert len(set(verts))==8
 if mode=='OBJECT':
  expected=[entity.matrix_world.inverted()@collider.matrix_world@v.co/entity['wl_unit_meters'] for v in collider.data.vertices]
  assert max(min((Vector(p)-q).length for p in verts) for q in expected)<1e-4
  from wavelength.source.geometry import BrushError
  try:scene_io.export_map(c.scene)
  except BrushError as exc:assert exc.code=='EMPTY_MAP',exc
  else:raise AssertionError('Collision helper exported as a world brush')
 print('PASS real StudioMDL collision mode',mode,flush=True)
