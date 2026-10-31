from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source.entity import icons
from wavelength.source import identity
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
entity=bpy.data.objects.new('Light',None);c.collection.objects.link(entity);entity['wl_role']='ENTITY';entity['wl_pairs']=json.dumps([('classname','light')]);entity['wl_unit_meters']=.0254
legacy=bpy.data.objects.new('Old curve',bpy.data.curves.new('Old icon','CURVE'));c.collection.objects.link(legacy);legacy.parent=entity;legacy['wl_entity_icon_reference']=True
icons.migrate_sprites()
assert len(entity.children)==1 and entity.children[0].type=='EMPTY' and entity.children[0].get('wl_entity_icon_sprite')
assert not any(o.type in {'CURVE','MESH'} for o in c.scene.objects)
entity.select_set(True);c.view_layer.objects.active=entity;identity.update_ids()
bpy.ops.object.duplicate();duplicate=c.object;duplicate.location=(1,0,0);duplicate.rotation_euler=(1,2,3);identity.update_ids()
assert len(duplicate.children)==1 and duplicate.children[0].get('wl_entity_icon_sprite')
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
with c.temp_override(area=a,region=r):
 assert len(list(icons.sprite_instances(c)))==2
 c.scene.wavelength_context.mode='CLEAN';assert not list(icons.sprite_instances(c))
 c.scene.wavelength_context.mode='EDIT'
 a.spaces.active.overlay.show_overlays=False;assert not list(icons.sprite_instances(c))
 a.spaces.active.overlay.show_overlays=True
 a.spaces.active.region_3d.view_rotation=Vector((3,-5,4)).to_track_quat('Z','Y');a.spaces.active.region_3d.view_distance=4
 a.spaces.active.region_3d.view_location=(.5,0,0)
 assert icons._path_polylines('M10 20L30 40')[0][0][0]==(10,20)
print('PASS SVG sprites: no curve/mesh geometry, migration, native duplication, clean preview and overlay gates',flush=True)
if not bpy.app.background:
 def capture():
  with c.temp_override(area=a,region=r):icons.draw_sprites()
  output=Path(__file__).resolve().parents[1]/'build/svg-sprite-proof.png';output.parent.mkdir(exist_ok=True)
  bpy.ops.screen.screenshot(filepath=str(output));print('PASS SVG sprite GPU drawing',flush=True);bpy.ops.wm.quit_blender()
 bpy.app.timers.register(capture,first_interval=3)
