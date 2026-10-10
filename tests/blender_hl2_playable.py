"""Opt-in real HL2 fixture: run with Blender --background --factory-startup --python.
Creates local game-textured .blend and compiles through the same Build Map operator.
WL_HL2_OUTPUT selects the output directory; nothing is copied into the game here.
"""
import json, os, sys, time
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import scene,vmf,textures,editor,ui
wavelength.register()
for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
s=bpy.context.scene.wavelength;s.engine='source_hl2_linux'
output=Path(os.environ.get('WL_HL2_OUTPUT',str(ROOT.parent/'maps/hl2-playable'))).resolve();output.mkdir(parents=True,exist_ok=True)
s.project_dir=str(output);s.map_name=os.environ.get('WL_HL2_MAP','wavelength_playable');s.build_output=str(output/(s.map_name+'.bsp'));s.timeout=300
if os.environ.get('WL_HL2_GAME'):s.game_dir=os.environ['WL_HL2_GAME']
if os.environ.get('WAVELENGTH_SOURCE_TOOLS'):s.compiler_dir=os.environ['WAVELENGTH_SOURCE_TOOLS']
doc=vmf.parse((ROOT/'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
for entity in doc.entities:
 for brush in entity.brushes:
  for face in brush:face.points=[[x*4 for x in p] for p in face.points]
 if dict(entity.pairs).get('classname')=='info_player_start':entity.pairs=[('classname','info_player_start'),('origin','0 -352 8'),('angles','0 90 0')]
 if dict(entity.pairs).get('classname')=='light':entity.pairs=[('classname','light'),('origin','0 0 400'),('_light','255 244 224 1200')]
scene.import_map(bpy.context.scene,doc)
for kind,location,params in [('STAIRS',(-280,-128,0),dict(steps=8,rise=16,run=32,width=128,landing=80)),('ARCH',(160,140,0),dict(radius=160,thickness=24,depth=48,segments=12)),('SPHERE',(280,-160,64),dict(radius=64,subdivisions=1))]:
 bpy.context.scene.cursor.location=tuple(x*.0254 for x in location)
 assert bpy.ops.wavelength.primitive(kind=kind,**params)=={'FINISHED'}
 root=bpy.context.object
 for obj in root.children:
  mat=textures.material(s,'dev/dev_measuregeneric01b');textures.assign(obj,range(len(obj.data.polygons)),mat);editor.apply_uv(obj,s.engine)
bpy.context.view_layer.update()
(output/(s.map_name+'.vmf')).write_text(vmf.write(scene.export_map(bpy.context.scene)))
assert bpy.ops.wavelength.build(filepath=s.build_output)=={'FINISHED'}
while ui._JOB is not None:
 ui.build_tick();time.sleep(.05)
assert s.last_build and not s.build_error,(s.status,s.build_error)
bpy.ops.wm.save_as_mainfile(filepath=str(output/(s.map_name+'.blend')))
(output/'build-result.json').write_text(json.dumps({'bsp':s.last_build,'logs':s.build_log_dir,'game':s.game_dir,'status':s.status},indent=2))
print('WL_HL2_BUILD_OK',s.last_build)
