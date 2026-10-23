import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint,source_assets,scene,primitives,formats,vmf
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
folder=Path(__file__).resolve().parents[1]/'build/terrain-blend';folder.mkdir(exist_ok=True)
game=folder/'game';game.mkdir(exist_ok=True)
real=source_assets.library(r'C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod')
mounts=[str(m.path if isinstance(m,source_assets.VPK) else m).replace('\\','/') for m in real.mounts]
info='GameInfo\n{\n game "Wavelength terrain blend test"\n FileSystem\n {\n SteamAppId 4000\n SearchPaths\n {\n Game "|gameinfo_path|."\n'+''.join('Game "'+p+'"\n' for p in mounts)+'}\n}\n}\n'
(game/'gameinfo.txt').write_text(info,encoding='utf-8')
s=ctx.scene.wavelength;s.engine='source_gmod_windows';s.game_dir=str(game);s.project_dir=str(folder/'project')
a=source_assets.material(s,'brick/brickwall001a');b=source_assets.material(s,'nature/dirtfloor001a')
obj=terrain.create(ctx,paintable_surface=True);obj.data.materials.append(a)
obj.wavelength_terrain.blend_base=a;obj.wavelength_terrain.paint_material=b
material=terrain.create_blend(obj,ctx)
assert material.get('wl_source_blend') and material['wl_texture'].startswith('wavelength/generated/')
assert obj.data.materials[0]==material
project=Path(obj['wl_terrain_generated_project_file']);installed=Path(obj['wl_terrain_generated_game_file'])
assert project.read_bytes()==installed.read_bytes()
assert 'brick/brickwall001a' in project.read_text() or '$basetexture' in project.read_text()
assert terrain.create_blend(obj,ctx)==material
# The saved recipe restores a missing generated VMT during export.
installed.unlink();terrain.brushes(obj);assert installed.read_bytes()==project.read_bytes()
print('PASS two Source materials generate, stage, assign and restore a deterministic blend VMT',material['wl_texture'],flush=True)
terrain_paint.stroke(obj,Vector((0,0,0)),'TEXTURE',4,1,.9)
obj.wavelength_terrain.flat_preview=True;ctx.view_layer.update();document=scene.export_map(ctx.scene)
assert any(max(row)>0 for brush in document.entities[0].brushes for row in brush[0].vmf['dispinfo']['alphas'])
for bounds in [(-656,-656,-272,656,656,-256),(-656,-656,512,656,656,528),(-656,-656,-256,-640,656,512),(640,-656,-256,656,656,512),(-640,-656,-256,640,-640,512),(-640,640,-256,640,656,512)]:
    vertices,faces=primitives.box(*bounds);brush=[]
    for face in faces:
        f=formats.Face([list(vertices[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);brush.append(f)
    document.entities[0].brushes.append(brush)
document.entities[0].pairs.append(('skyname','sky_day01_01'))
document.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
(folder/'terrain-generated-blend.vmf').write_text(vmf.write(document),encoding='utf-8')
print('PASS painted generated-blend VMF fixture',flush=True)
