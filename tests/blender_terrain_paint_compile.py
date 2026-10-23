import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint,source_assets,scene,primitives,formats,vmf
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
settings=ctx.scene.wavelength;settings.engine='source_gmod_windows';settings.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod'
assets=source_assets.library(settings.game_dir);material=None
for name in assets.materials('blend'):
    try:
        props=assets.material(name)
        if not props.get('_wl_shader','').startswith('worldvertextransition') or not props.get('$basetexture2'):continue
        material=source_assets.material(settings,name);break
    except (ValueError,OSError,KeyError):continue
assert material is not None,'No installed Source transition material found'
obj=terrain.create(ctx,paintable_surface=True);s=obj.wavelength_terrain;s.width=s.length=512;s.amplitude=32
obj.data.materials.append(material);terrain.sync_material(obj,force=True)
terrain_paint.stroke(obj,Vector((0,0,0)),'RAISE',3,1,.5)
terrain_paint.stroke(obj,Vector((0,0,0)),'TEXTURE',3,1,.9)
s.flat_preview=True;ctx.view_layer.update();document=scene.export_map(ctx.scene)
assert any(max(row)>0 for b in document.entities[0].brushes for row in b[0].vmf['dispinfo']['alphas'])
for bounds in [(-656,-656,-272,656,656,-256),(-656,-656,512,656,656,528),(-656,-656,-256,-640,656,512),(640,-656,-256,656,656,512),(-640,-656,-256,640,-640,512),(-640,640,-256,640,656,512)]:
    vertices,faces=primitives.box(*bounds);brush=[]
    for face in faces:
        f=formats.Face([list(vertices[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);brush.append(f)
    document.entities[0].brushes.append(brush)
document.entities[0].pairs.append(('skyname','sky_day01_01'))
document.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
(folder/'terrain-painted.vmf').write_text(vmf.write(document),encoding='utf-8')
print('PASS real installed transition material and painted VMF',material['wl_texture'],flush=True)
