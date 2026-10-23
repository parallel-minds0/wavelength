import sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint as paint,source_assets,asset_browser
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
ctx.scene.wavelength.engine='blender';obj=terrain.create(ctx,paintable_surface=True);s=obj.wavelength_terrain;s.amplitude=0

def heights(obj):
    ctx.view_layer.update();evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:return [v.co.z for v in mesh.vertices]
    finally:evaluated.to_mesh_clear()
assert max(heights(obj))<1e-6
assert paint.stroke(obj,Vector((0,0,0)),'RAISE',2,1,.5)>0
assert max(heights(obj))>.9,(max(heights(obj)),max(v.co.z for v in obj.data.vertices),[(s.name,s.identifier) for s in obj.modifiers[0].node_group.interface.items_tree if s.item_type=='SOCKET'])
center=max(v.co.z for v in obj.data.vertices)
paint.stroke(obj,Vector((0,0,0)),'SMOOTH',2,1,.5)
assert max(v.co.z for v in obj.data.vertices)<center
s.flat_preview=True
assert max(heights(obj))<1e-6
s.flat_preview=False
assert max(heights(obj))>.5
paint.stroke(obj,Vector((0,0,0)),'TEXTURE',2,1,.8)
ctx.view_layer.update();ev=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=ev.to_mesh()
assert mesh.uv_layers.get('wavelength')
assert max(v.value for v in mesh.attributes['wl_terrain_blend'].data)>.7
ev.to_mesh_clear()
base=bpy.data.materials.new('Base');base.diffuse_color=(1,0,0,1);obj.data.materials.append(base)
paintmat=bpy.data.materials.new('Paint');paintmat.diffuse_color=(0,1,0,1);s.paint_material=paintmat
preview=paint.preview_material(obj);assert preview.use_nodes and any(n.type=='ATTRIBUTE' for n in preview.node_tree.nodes)
print('PASS height raise/smooth, flat preview, named UVs and general material mask',flush=True)
ctx.scene.wavelength.engine='source_gmod_windows';source=terrain.create(ctx,paintable_surface=True);source.wavelength_terrain.amplitude=0
class Assets:
    game='mock terrain materials'
    def material(self,name):return {'$basetexture':'red','$basetexture2':'green','_wl_shader':'worldvertextransition'}
    def read(self,name):return name.encode()
def decode(data):return (2,2,2,2,bytes(([255,0,0,255] if b'red' in data else [0,255,0,255])*4))
with patch.object(source_assets,'library',return_value=Assets()),patch.object(source_assets,'decode_vtf',side_effect=decode):
    material=source_assets.material(ctx.scene.wavelength,'nature/test_terrain')
assert material.get('wl_source_blend') and any(n.type=='MIX_RGB' for n in material.node_tree.nodes)
source.data.materials.append(material)
asset_browser.dropped(ctx.scene)
modifier=source.modifiers[0]
socket=next(s for s in modifier.node_group.interface.items_tree if s.item_type=='SOCKET' and s.name=='Material' and s.in_out=='INPUT')
assert paint.input_value(modifier,socket.identifier)==material
replacement=material.copy();source.data.materials.append(replacement);asset_browser.dropped(ctx.scene)
assert paint.input_value(modifier,socket.identifier)==replacement
material=replacement
paint.stroke(source,Vector((0,0,0)),'RAISE',8,.5,.5)
paint.stroke(source,Vector((0,0,0)),'TEXTURE',8,1,.8)
source.wavelength_terrain.flat_preview=True
assert max(heights(source))<1e-6
brushes=terrain.brushes(source)
assert any(max(row)>0 for b in brushes for row in b[0].vmf['dispinfo']['alphas'])
assert any(max(row)>0 for b in brushes for row in b[0].vmf['dispinfo']['distances'])
assert max(heights(source))<1e-6, 'Export must restore flat placement preview'
print('PASS dropped material sync, Source blend shader, painted alphas and full export under flat preview',flush=True)

# A real shader render checks the material/UV route rather than only node links.
for other in list(ctx.scene.objects):
    if other!=source:bpy.data.objects.remove(other,do_unlink=True)
shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
color=shader.inputs['Base Color'].links[0].from_socket
material.node_tree.links.new(color,shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=1
camera_data=bpy.data.cameras.new('Terrain render test');camera=bpy.data.objects.new('Terrain render test',camera_data);ctx.collection.objects.link(camera);camera.location=(0,0,30);camera_data.type='ORTHO';camera_data.ortho_scale=30;ctx.scene.camera=camera
ctx.scene.render.engine='CYCLES';ctx.scene.cycles.device='CPU';ctx.scene.cycles.samples=4
ctx.scene.render.resolution_x=ctx.scene.render.resolution_y=64;ctx.scene.render.resolution_percentage=100
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
ctx.scene.render.filepath=str(folder/'terrain-material.png');bpy.ops.render.render(write_still=True)
image=bpy.data.images.load(ctx.scene.render.filepath,check_existing=False);pixels=list(image.pixels)
assert max(pixels[(32*64+32)*4:(32*64+32)*4+3])>.2
print('PASS terrain material renders visible color through named UVs',flush=True)
