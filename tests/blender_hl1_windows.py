"""Verify Windows HL1 profile discovery, models, round trips and native compilers."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import profiles,goldsrc_import
from wavelength.source.build.toolchains import resolve_compiler
s.engine='goldsrc_windows'
assert profiles.is_goldsrc(s.engine) and profiles.get(s.engine)['steam_app_id']=='70'
assert Path(s.game_dir,'liblist.gam').is_file() and Path(s.game_executable).is_file()
assert Path(s.fgd_path).is_file() and json.loads(s.texture_wads) and Path(s.wad_path).is_file()
from wavelength.source import textures
assert len(textures.all_names(s))>100
assert all(Path(p).is_file() for p in json.loads(s.texture_wads))
tool=s.compiler_dir;assert tool
entity=_spawn_point_entity(ctx,'monster_scientist')
assert any(c.type=='MESH' and c.data.polygons for c in entity.children)
s.engine='blender';s.engine='goldsrc_windows';assert s.compiler_dir==tool
folder=root/'build/hl1-windows-profile';folder.mkdir(exist_ok=True)
from wavelength.source import scene,formats
material=bpy.data.materials.new('HL1 wall');material['wl_texture']=next(n for n in textures.all_names(s) if n.lower().startswith('c1a0'))
for axis in range(3):
    for sign in (-1,1):
        position=[0,0,0];position[axis]=sign*4
        bpy.ops.mesh.primitive_cube_add(size=1,location=position);wall=ctx.object
        wall.scale=[8.5,8.5,8.5];wall.scale[axis]=.5;wall.data.materials.append(material);scene.mark_brush(wall)
_spawn_point_entity(ctx,'info_player_start')
ctx.view_layer.update()
document=scene.export_map(ctx.scene);textures.build_wad(s,document,folder,ctx.scene.objects)
document.entities[0].brushes[0][0].texture='NULL'
textures.build_wad(s,document,folder,ctx.scene.objects)
(folder/'level.map').write_text(formats.write(document))
for stage in profiles.get(s.engine)['stages']:
    exe=resolve_compiler(tool,stage)
    args=['-nowadtextures','level.map'] if stage=='hlcsg' else ['level.bsp']
    result=subprocess.run([str(exe),*args],cwd=folder,capture_output=True,text=True,errors='replace',timeout=60)
    (folder/(stage+'.log')).write_text(result.stdout+result.stderr)
    assert result.returncode==0,(stage,result.stdout[-2000:],result.stderr)
data=(folder/'level.bsp').read_bytes();assert int.from_bytes(data[:4],'little')==30
import struct
texoff,texlen=struct.unpack_from('<2i',data,4+2*8)
infooff,infolen=struct.unpack_from('<2i',data,4+6*8)
faceoff,facelen=struct.unpack_from('<2i',data,4+7*8)
for at in range(faceoff,faceoff+facelen,20):
    info=struct.unpack_from('<H',data,at+10)[0];texture=struct.unpack_from('<i',data,infooff+info*40+32)[0]
    offset=struct.unpack_from('<i',data,texoff+4+texture*4)[0]
    if offset>=0:assert data[texoff+offset:texoff+offset+16].split(b'\0')[0].lower()!=b'null','NULL face was not stripped by the compiler'
print('PASS Windows HL1 discovery: game, WAD textures, FGD, entity model, profile round trip and four native compiler stages producing BSP30',flush=True)
