"""Diagnose the reported cave without overwriting the user's saved map."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False);bpy.context.preferences.use_preferences_save=False
from wavelength.source import terrain,terrain_sew as sew,scene,vmf
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--')+1])
ctx=bpy.context;ctx.workspace['wl_workspace']=True
surfaces=[o for o in ctx.scene.objects if o.get('wl_terrain_seams')]
assert len(surfaces)==4
ctx.view_layer.update()
for o in surfaces:terrain.sync_material(o)
ctx.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
before={o.name:[o.matrix_world@v.co for v in o.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices] for o in surfaces}
for o in surfaces:o.select_set(True)
ctx.view_layer.objects.active=surfaces[0]
assert bpy.ops.wavelength.terrain_flip_facing()=={'FINISHED'}
expected=[]
center=sum((o.matrix_world.translation for o in surfaces),Vector())/len(surfaces)
for o in surfaces:
    after=[o.matrix_world@v.co for v in o.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices]
    error=max((p-q).length for p,q in zip(before[o.name],after));print('POSITION ERROR',o.name,error,flush=True)
    assert error<1e-5
    sew.validate_export(o)
    vertices,_,info=terrain.patches(o)[0];vertices,info=terrain.export_facing(o,vertices,info);unit=o['wl_unit_meters']
    normal=(o.matrix_world.to_3x3().inverted().transposed()@Vector(info['normal'])).normalized()
    assert normal.dot(center-o.matrix_world.translation)>0,('front must face cave interior',o.name)
    expected.append(dict(name=o.name,base=[list(o.matrix_world@Vector(p)/unit) for p in info['base_corners']],positions=[list(o.matrix_world@Vector(p)/unit) for p in vertices],normal=list(normal)))
folder=root/'build/terrain-facing-user';folder.mkdir(exist_ok=True)
(folder/'expected.json').write_text(json.dumps(expected),encoding='utf-8')
(folder/'facing-fixed.vmf').write_text(vmf.write(scene.export_map(ctx.scene)),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'basic-facing-fixed.blend'))
print('PASS user cave fronts face inward, all sculpted positions and sewn joins retained; original map unchanged',flush=True)
