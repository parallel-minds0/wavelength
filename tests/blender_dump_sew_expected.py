import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False);bpy.context.preferences.use_preferences_save=False
from wavelength.source import terrain,terrain_sew
bpy.ops.wm.open_mainfile(filepath=str(root/'build/terrain-sew/sewn.blend'))
rows=[]
for obj in bpy.context.scene.objects:
    if not obj.get('wl_terrain'):continue
    for vertices,_,info in terrain.patches(obj):
        unit=obj['wl_unit_meters'];rows.append(dict(name=obj.name,base=[list(obj.matrix_world@p/unit) for p in terrain_sew.quad(obj)],positions=[list(obj.matrix_world@__import__('mathutils').Vector(p)/unit) for p in vertices]))
(root/'build/terrain-sew/expected.json').write_text(json.dumps(rows),encoding='utf-8')
