import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,scene,vmf,formats,primitives
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
ctx.scene.wavelength.engine='blender';obj=terrain.create(ctx,paintable_surface=True);obj.wavelength_terrain.amplitude=1;ctx.view_layer.update()
evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
assert len(mesh.vertices)==65**2 and mesh.uv_layers
first=[v.co.copy() for v in mesh.vertices];evaluated.to_mesh_clear()
obj.wavelength_terrain.seed=5;terrain.update(obj);ctx.view_layer.update()
evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
assert any((a-b.co).length>.001 for a,b in zip(first,mesh.vertices));evaluated.to_mesh_clear()
print('PASS general node terrain, UVs and seed variation',flush=True)
ctx.scene.wavelength.engine='source_gmod_windows';source=terrain.create(ctx,paintable_surface=True);source.wavelength_terrain.amplitude=64;ctx.view_layer.update()
material=bpy.data.materials.new('Terrain material');material['wl_texture']='nature/dirtfloor001a';source.data.materials.append(material);terrain.update(source);ctx.view_layer.update()
patches=terrain.patches(source);assert len(patches)==4
# Horizontal and vertical neighbours use identical global sample positions.
size=9
assert all(patches[0][0][j*size+8]==patches[1][0][j*size] for j in range(size))
assert all(patches[0][0][8*size+i]==patches[2][0][i] for i in range(size))
brushes=terrain.brushes(source);assert len(brushes)==4
assert all(b[0].vmf['dispinfo']['power']==3 for b in brushes)
# Build export in a clean scene containing only the Source terrain.
for other in list(ctx.scene.objects):
    if other!=source:bpy.data.objects.remove(other,do_unlink=True)
document=scene.export_map(ctx.scene);text=vmf.write(document)
assert text.count('dispinfo')==4
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
(folder/'terrain.vmf').write_text(text,encoding='utf-8')
# A sealed room makes this a valid standalone VBSP displacement fixture.
for bounds in [(-656,-656,-272,656,656,-256),(-656,-656,512,656,656,528),(-656,-656,-256,-640,656,512),(640,-656,-256,656,656,512),(-640,-656,-256,640,-640,512),(-640,640,-256,640,656,512)]:
    verts,faces=primitives.box(*bounds)
    brush=[]
    for face in faces:
        f=formats.Face([list(verts[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);brush.append(f)
    document.entities[0].brushes.append(brush)
document.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
(folder/'terrain-sealed.vmf').write_text(vmf.write(document),encoding='utf-8')
print('PASS Source resampling, exact neighbour seams and VMF displacement export',flush=True)
for power in ['2','4']:
    source.wavelength_terrain.power=power
    patches=terrain.patches(source);assert len(patches[0][0])==(2**int(power)+1)**2
print('PASS independent Source patch powers 2/3/4',flush=True)
bpy.ops.wavelength.terrain_finalize();assert source['wl_procedural_state']=='FINALIZED' and not source.modifiers
assert len(terrain.patches(source))==4
source.wavelength_terrain.tiles_x=3
assert len(terrain.patches(source))==4, 'Finalized patch settings must remain frozen'
try:terrain.update(source)
except ValueError:pass
else:raise AssertionError('Finalized terrain regenerated')
print('PASS terrain finalization and frozen regeneration',flush=True)
import bmesh
bm=bmesh.new();bm.from_mesh(source.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[len(bm.faces)//2+3]],context='FACES');bm.to_mesh(source.data);bm.free()
try:terrain.patches(source)
except ValueError:pass
else:raise AssertionError('Terrain hole silently exported')
print('PASS unsupported terrain topology rejected',flush=True)
addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
assert source.wavelength_terrain.tiles_x==3
print('PASS restricted addon reload',flush=True)
