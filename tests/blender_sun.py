"""Sun preview data, two-way direction/brightness, export and lifecycle."""
import bpy,sys,json,math
from pathlib import Path
from unittest.mock import patch
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import ui,sun,scene,textures,workspace
wavelength.register()
s=bpy.context.scene.wavelength
with patch.object(textures,'refresh'):s.engine='source_hl2_windows'
s.texture='brick/brickwall001a'
world=bpy.context.object;scene.mark_brush(world)
records=json.loads(world.data['wl_faces'])
for record in records.values():record['texture']=s.texture
world.data['wl_faces']=json.dumps(records)
material=bpy.data.materials.new('Sun test brush');material['wl_texture']=s.texture;world.data.materials.clear();world.data.materials.append(material)
entity=ui._spawn_point_entity(bpy.context,'light_environment')
bpy.context.view_layer.update()
light=sun.light_for(entity)
assert light and light.type=='LIGHT' and light.data.type=='SUN'
assert light.get('wl_exclude') and not light.get('wl_role')
assert abs(light.data.energy-2)<1e-5
sun.ensure(entity);assert len([o for o in entity.children if o.get('wl_sun_preview')])==1
entity.wl_sun.heading=math.pi/2
entity.wl_sun.elevation=math.pi/6
bpy.context.view_layer.update()
ray=light.matrix_world.to_quaternion()@Vector((0,0,-1))
assert (ray-Vector((0,math.sqrt(.75),-.5))).length<1e-5,ray
exported=dict(sun.export_pairs(entity,json.loads(entity['wl_pairs'])))
assert abs(float(exported['pitch'])+30)<1e-4,exported
assert abs(float(exported['angles'].split()[1])-90)<1e-4,exported
# Native light rotation, color and strength must update engine metadata.
light.rotation_euler=(0,0,0);light.data.energy=3.5;light.data.color=(.5,.25,.1)
bpy.context.view_layer.update();sun.queue(entity);sun.flush()
assert abs(float(dict(json.loads(entity['wl_pairs']))['pitch'])+90)<1e-4
assert float(dict(json.loads(entity['wl_pairs']))['_light'].split()[-1])==350
# Applying raw entity fields must update the real light in the other direction.
entity['wl_pairs']=json.dumps(sun.replace(json.loads(entity['wl_pairs']),{'pitch':'-20','angles':'0 180 0','_light':'255 128 64 400','SunSpreadAngle':'5'}))
sun.queue(entity);sun.flush();bpy.context.view_layer.update()
assert abs(sun.angles(light)[1]-math.radians(20))<1e-5
assert abs(light.data.energy-4)<1e-5
assert abs(math.degrees(light.data.angle)-5)<1e-5
document=scene.export_map(bpy.context.scene)
assert sum(dict(e.pairs).get('classname')=='light_environment' for e in document.entities)==1
assert len([e for e in document.entities if dict(e.pairs).get('classname')!='worldspawn'])==1
# A selected preview light resolves to the same entity inspector and gizmo.
assert ui._entity_property_target(light)[0]=='wl_pairs'
assert not sun.WL_GGT_sun.poll(bpy.context)
with patch.object(workspace,'active',return_value=True):assert sun.WL_GGT_sun.poll(bpy.context)
sun.loaded();sun.flush();assert sun.light_for(entity)==light
light_name=light.name
bpy.data.objects.remove(entity,do_unlink=True);sun.flush()
assert bpy.data.objects.get(light_name) is None,'Deleting the sun left an orphan light'
wavelength.unregister();wavelength.register();wavelength.unregister()
print('PASS SUN: real light, heading/elevation, native edits, metadata edits, single exported entity, preview inspector and reload')
