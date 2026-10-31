"""Source bindings participate in real Eevee and Cycles renders."""
from pathlib import Path
import json
import sys
import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import wavelength
wavelength.register()
from wavelength.source import native_source,source_assets
c=bpy.context;s=c.scene.wavelength
s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add(location=(0,0,1))
cube=c.object;cube.data.materials.append(source_assets.material(s,'brick/brickwall001a'))
cube.data.uv_layers.new(name='wavelength',do_init=True)
entity=bpy.data.objects.new('Render barrel',None);c.collection.objects.link(entity)
entity.location=(2,0,0);entity['wl_role']='ENTITY'
entity['wl_pairs']=json.dumps([['classname','prop_static'],['model','models/props_c17/oildrum001.mdl']])
native_source.attach(entity,'models/props_c17/oildrum001.mdl')
bpy.ops.object.camera_add(location=(6,-9,5));camera=c.object
camera.rotation_euler=(Vector((.5,0,1))-camera.location).to_track_quat('-Z','Y').to_euler()
c.scene.camera=camera
light=bpy.data.lights.new('Render sun','SUN');light.energy=3
sun=bpy.data.objects.new('Render sun',light);c.collection.objects.link(sun);sun.rotation_euler=(.4,-.5,-.4)
c.scene.render.resolution_x=96;c.scene.render.resolution_y=96;c.scene.render.resolution_percentage=100
c.scene.render.image_settings.file_format='PNG'
folder=Path(__file__).resolve().parents[1]/'build/source-render';folder.mkdir(exist_ok=True)
for engine in ('BLENDER_EEVEE','CYCLES'):
    c.scene.render.engine=engine
    if engine=='CYCLES':c.scene.cycles.samples=8;c.scene.cycles.device='CPU'
    c.scene.render.filepath=str(folder/(engine+'.png'))
    bpy.ops.render.render(write_still=True)
    assert any(o.type=='MESH' and o.get('wl_model_reference') for o in entity.children)
    assert any(n.type=='TEX_IMAGE' and n.image for n in cube.data.materials[0].node_tree.nodes)
    assert Path(c.scene.render.filepath).is_file()
    print('PASS real Source render:',engine,flush=True)
