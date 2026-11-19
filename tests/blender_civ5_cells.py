import sys,json,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import civ5_cells as cells,civ5_format,profiles
context=bpy.context;context.scene.wavelength.auto_prepare_assets=False
folder=root/'build/civ5';folder.mkdir(parents=True,exist_ok=True)
game=Path(r"C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization V")
paths=list(game.rglob('*.Civ5Map'))
path=next(p for p in paths if p.name.lower()=='earth_duel.civ5map')
obj=cells.import_map(context,path);raw=path.read_bytes();original=civ5_format.parse(raw)
assert context.scene.wavelength.engine=='civ5' and profiles.get('civ5')['authoring']=='hex_cells'
assert len(obj.data.polygons)==original.width*original.height
out=folder/'unchanged.Civ5Map';cells.export_map(context,out);assert out.read_bytes()==raw
obj['wl_civ5_selected']=json.dumps([0,1]);settings=context.scene.wavelength_civ5
settings.field='terrain';settings.terrain='1';assert bpy.ops.wavelength.civ5_apply()=={'FINISHED'}
settings.field='elevation';settings.elevation='2';assert bpy.ops.wavelength.civ5_apply()=={'FINISHED'}
settings.field='river';settings.river_east=True;settings.river_southeast=True;before=obj.data.attributes['civ5_river'].data[0].value;cells.apply_cells(context,obj,[0])
assert obj.data.attributes['civ5_river'].data[0].value&248==before&248
out=folder/'edited.Civ5Map';cells.export_map(context,out);edited=out.read_bytes()
allowed={original.offset+i*8+j for i in (0,1) for j in (0,3,4)}
assert all(i in allowed for i,(a,b) in enumerate(zip(raw,edited)) if a!=b)
assert edited[original.offset+original.width*original.height*8:]==raw[original.offset+original.width*original.height*8:]
obj.data.vertices[0].co.x+=.1
try:cells.export_map(context,folder/'invalid.Civ5Map')
except ValueError:pass
else:raise AssertionError('Low-level geometry edits silently exported')
obj.data.vertices[0].co.x-=.1;cells.refresh(obj,[0])
# Exercise the same unified IO operators used by Blender's File menu.
assert bpy.ops.wavelength.export_map(filepath=str(folder/'menu.Civ5Map'),export_format='CIV5MAP')=={'FINISHED'}
assert bpy.ops.wavelength.import_map(filepath=str(path),import_format='CIV5MAP')=={'FINISHED'}
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'civ5-cells.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'civ5-cells.blend'))
obj=bpy.data.objects[obj.name] if False else bpy.context.object
cells.export_map(bpy.context,folder/'reloaded.Civ5Map')
print('PASS installed Civ V map: exact import/export, high-level cell edits only, river metadata/scenario preservation, geometry rejection, unified menus, save/reload',flush=True)
