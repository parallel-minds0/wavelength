"""Read a user map in an isolated session; write diagnostics only under build/."""
import sys,json,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False);bpy.context.preferences.use_preferences_save=False
from wavelength.source import terrain,terrain_sew,terrain_face,scene,vmf
path=sys.argv[sys.argv.index('--')+1];bpy.ops.wm.open_mainfile(filepath=path)
folder=root/'build/user-terrain';folder.mkdir(exist_ok=True);rows=[]
print('ENGINE',bpy.context.scene.wavelength.engine,flush=True)
print('GAME',bpy.context.scene.wavelength.game_dir,flush=True)
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':print('MESH',obj.name,'role',obj.get('wl_role'),'terrain',obj.get('wl_terrain'),'excluded',obj.get('wl_exclude'),'faces',len(obj.data.polygons),'materials',[m.get('wl_texture') if m else None for m in obj.data.materials],flush=True)
    if not obj.get('wl_terrain'):continue
    print('TERRAIN',obj.name,'parent',obj.parent.name if obj.parent else None,'source',obj.wavelength_terrain.surface_source.name if obj.wavelength_terrain.surface_source else None,'detached',obj.get('wl_terrain_detached'),'vector',obj.get('wl_terrain_vector_surface'),'links',obj.get('wl_terrain_seams'),'matrix',[list(row) for row in obj.matrix_world],flush=True)
    try:
        for vertices,_,info in terrain.patches(obj):
            if not obj.get('wl_terrain_face_corners'):continue
            unit=obj['wl_unit_meters'];q=terrain_sew.quad(obj)
            rows.append(dict(name=obj.name,base=[list(obj.matrix_world@p/unit) for p in q],positions=[list(obj.matrix_world@Vector(p)/unit) for p in vertices],power=info['power']))
    except Exception:traceback.print_exc()
(folder/'expected.json').write_text(json.dumps(rows),encoding='utf-8')
try:(folder/'user-copy.vmf').write_text(vmf.write(scene.export_map(bpy.context.scene)),encoding='utf-8')
except Exception:traceback.print_exc()
