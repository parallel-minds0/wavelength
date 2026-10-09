import sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import asset_browser,asset_index,source_assets,scene,primitive_ui,vmf,formats
wavelength.register();s=bpy.context.scene.wavelength;s.engine='source_hl2_linux'
game=Path.home()/'.local/share/Steam/steamapps/common/Half-Life 2/hl2_complete';s.game_dir=str(game)
if game.exists():
 mat=asset_browser.publish_material(bpy.context,'dev/dev_measuregeneric01b');assert mat.asset_data and mat.preview.image_size[0]==64
 rows=asset_index.discover(s);models=[r for r in rows if r['category']=='MODEL'];assert models
 row=next((r for r in models if r['path']=='models/props_c17/oildrum001.mdl'),models[0]);proxy=asset_browser.publish_proxy(bpy.context,row);data=json.loads(proxy['wl_asset']);assert 'bounds' in data,data
 entity=asset_browser.place(bpy.context,data);assert dict(json.loads(entity['wl_pairs']))['model']==row['path'];assert entity.children
 print('PASS REAL SOURCE MATERIAL / MDL BOUNDS / NATIVE ASSETS',len(rows))
# A representative export with three separate editable generators and a sealed room.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for kind,location in [('STAIRS',(-3,0,0)),('ARCH',(4,0,1)),('SPHERE',(0,-5,2))]:
 bpy.context.scene.cursor.location=location;bpy.ops.wavelength.primitive(kind=kind,radius=64,steps=4,rise=8,run=16,width=64,depth=16,thickness=16)
mat=bpy.data.materials.get('primitive fixture') or bpy.data.materials.new('primitive fixture');mat['wl_texture']='tools/toolsnodraw'
for obj in bpy.context.scene.objects:
 if obj.get('wl_role')=='BRUSH':obj.data.materials.append(mat)
# Keep production fixtures separate from existing user maps.
out=ROOT.parent/'maps/milestones-1-2';out.mkdir(exist_ok=True)
from wavelength.source.primitives import box
unit=.0254
for dims in [(-512,-512,-16,512,512,0),(-512,-512,384,512,512,400),(-528,-512,-16,-512,512,400),(512,-512,-16,528,512,400),(-528,-528,-16,528,-512,400),(-528,512,-16,528,528,400)]:
 verts,faces=box(*dims);mesh=bpy.data.meshes.new('room');mesh.from_pydata([tuple(c*unit for c in v) for v in verts],[],faces);mesh.update();obj=bpy.data.objects.new('room',mesh);bpy.context.collection.objects.link(obj);scene.mark_brush(obj);mesh.materials.append(mat)
from wavelength.source.ui import _spawn_point_entity
bpy.context.scene.cursor.location=(0,0,1);_spawn_point_entity(bpy.context,'info_player_start')
(out/'primitives.vmf').write_text(vmf.write(scene.export_map(bpy.context.scene)))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'primitives.blend'))
print('PASS PRIMITIVE EXPORT',out)
wavelength.unregister()
