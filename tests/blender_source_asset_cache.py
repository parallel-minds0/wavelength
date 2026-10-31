import sys,json,tempfile,time,struct,zlib,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import source_assets as assets,runtime_cache,asset_loading as loading,model_import,scene
from tests.test_source_assets import AssetTests
suite=unittest.TestSuite([AssetTests('test_vectorized_dxt_matches_portable_decoder')]);assert unittest.TextTestRunner().run(suite).wasSuccessful()
s=bpy.context.scene.wavelength;s.engine='source_hl2_windows'
def drain():
 start=time.monotonic()
 while loading._waiting and time.monotonic()-start<60:loading.tick();time.sleep(.03)
 assert not loading._waiting,'Worker did not complete'
 assert not loading._failures,loading._failures
with tempfile.TemporaryDirectory() as temp:
 game=Path(temp)/'game';(game/'materials').mkdir(parents=True)
 (game/'gameinfo.txt').write_text('GameInfo { FileSystem { SearchPaths { game "|gameinfo_path|." } } }')
 vtf=game/'materials/red.vtf';vtf.write_bytes(AssetTests().vtf(13,struct.pack('<HHI',0xf800,0,0)))
 (game/'materials/test.vmt').write_text('LightmappedGeneric { "$basetexture" "red" }')
 s.game_dir=str(game)
 mat=assets.material(s,'test');assert mat['wl_width']==4 and mat['wl_realized']
 with patch.object(assets,'decode_vtf',side_effect=AssertionError('Repeated VTF decode')):
  assert assets.material(s,'test')==mat
  for image in list(bpy.data.images):
   if image.name.startswith('wl_source_image_'):bpy.data.images.remove(image)
  bpy.data.materials.remove(mat)
  mat=assets.material(s,'test')
 # Replacing a mounted VTF must not return the old material/image.
 vtf.write_bytes(AssetTests().vtf(13,struct.pack('<HHI',0x001f,0,0)))
 new=assets.material(s,'test');assert new!=mat
 image=next(n.image for n in new.node_tree.nodes if n.type=='TEX_IMAGE')
 assert image.pixels[2]>.9 and image.pixels[0]<.1
 identity=assets.preview_key(assets.library(str(game)),'materials/red.vtf')
 (runtime_cache.root()/(identity+'.cache')).write_bytes(zlib.compress(b'corrupt decoded preview'))
 bpy.data.images.remove(image);assets.preview_image(assets.library(str(game)),'materials/red.vtf')
 # Defer a cold image, save it still pending, and resume on file load.
 (game/'materials/second.vtf').write_bytes(AssetTests().vtf(13,struct.pack('<HHI',0x07e0,0,0)))
 (game/'materials/second.vmt').write_text('LightmappedGeneric { "$basetexture" "second" }')
 pending=assets.material(s,'second',defer=True);assert pending.get('wl_source_pending') and not pending.get('wl_realized')
 mesh=bpy.data.meshes.new('holder');mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)]);obj=bpy.data.objects.new('holder',mesh);bpy.context.scene.collection.objects.link(obj);mesh.materials.append(pending)
 path=Path(temp)/'pending.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path));bpy.ops.wm.open_mainfile(filepath=str(path))
 s=bpy.context.scene.wavelength;drain()
 pending=bpy.data.objects['holder'].data.materials[0];assert pending.get('wl_realized') and not pending.get('wl_source_pending')
 assert len([n for n in pending.node_tree.nodes if n.type=='TEX_IMAGE' and n.image])==1
 loading.clear()
 # Decoded geometry survives a new process/LRU, but companion edits invalidate it.
 (game/'models').mkdir();model=game/'models/test.mdl';vertex=game/'models/test.vvd'
 model.write_bytes(b'model');vertex.write_bytes(b'first');(game/'models/test.dx90.vtx').write_bytes(b'indices')
 lib=assets.Assets(game)
 data=dict(vertices=[[0,0,0],[1,0,0],[0,1,0]],normals=[[0,0,1]]*3,uvs=[[0,0],[1,0],[0,1]],faces=[[0,1,2]],slots=[0],materials=['test'],directories=[''],static=True,checksum=1)
 with patch('wavelength.source.studio_model.load',return_value=data) as decoder:
  model_import.decoded(s,'models/test.mdl',0,0,lib)
  assert decoder.call_count==1
  model_import._DECODED.clear();model_import.decoded(s,'models/test.mdl',0,0,lib);assert decoder.call_count==1
  vertex.write_bytes(b'updated vertex companion')
  model_import.decoded(s,'models/test.mdl',0,0,lib);assert decoder.call_count==2
 print('PASS decoded texture disk reuse, edited texture invalidation, corrupt-cache repair, deferred worker, pending save/reload',flush=True)
# Multiple props must share one worker job and one Blender mesh.
s=bpy.context.scene.wavelength;s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin\halflife2.fgd'
objects=[]
for i in range(20):
 obj=bpy.data.objects.new('crate-'+str(i),None);bpy.context.scene.collection.objects.link(obj);obj['wl_role']='ENTITY';obj['wl_pairs']=json.dumps([['classname','prop_static'],['model','models/props_junk/wood_crate001a.mdl']]);objects.append(obj);loading.entity(bpy.context.scene,obj)
assert len(loading._jobs)==1,len(loading._jobs)
drain();meshes=[next(c.data for c in obj.children if c.get('wl_model_reference')) for obj in objects];assert len(set(meshes))==1
with patch('wavelength.source.studio_model.load',side_effect=AssertionError('Repeated geometry decode')):
 assert model_import.mesh(s,'models/props_junk/wood_crate001a.mdl')[0]==meshes[0]
loading.clear();print('PASS repeated props: one worker decode job, shared mesh, no repeated studio decode',flush=True)
