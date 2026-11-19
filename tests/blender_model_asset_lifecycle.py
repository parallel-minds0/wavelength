"""Phase-one editing at placed poses, explicit linked placements and variants."""
import sys,json,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Matrix,Euler,Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_lifecycle as life,model_io,source_assets,studio_model,custom_models,scene
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
s.compiler_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/bin';s.unit_scale=.0254
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
def entity(name,location,rotation=(0,0,0),classname='prop_static'):
    obj=bpy.data.objects.new(name,None);ctx.scene.collection.objects.link(obj)
    obj['wl_role']='ENTITY';obj['wl_id']=uuid.uuid4().hex;obj['wl_unit_meters']=.0254;obj['wl_owner_profile']=s.engine
    obj['wl_pairs']=json.dumps([['classname',classname],['model','models/props_c17/oildrum001.mdl']])
    obj.location=location;obj.rotation_euler=rotation;ctx.view_layer.update();return obj
def points(obj):return [obj.matrix_world@v.co for v in obj.data.vertices]
def close(a,b):return max((x-y).length for x,y in zip(a,b))<1e-5
a=entity('Track placement A',(7,-2,1),(.2,.3,.8));asset=life.edit(ctx,a)
mesh=next(o for o in asset.objects if o.type=='MESH');identity=asset['wl_model_id']
assert len(identity)==32 and asset['wl_custom_model_id']==identity
assert model_io.asset_for_object(a)==asset and model_io.asset_for_object(mesh)==asset
decoded=studio_model.load(source_assets.library(s.game_dir),'models/props_c17/oildrum001.mdl')
expected=[a.matrix_world@(Vector(v)*.0254) for v in decoded['vertices']]
assert close(points(mesh),expected),'Edit Model changed physical scale/orientation/pose'
assert mesh.get('wl_exclude') and mesh['wl_custom_model_owner']==a
assert mesh.data!=next(m for m in bpy.data.meshes if m!=mesh.data and m.get('wl_source_model_key')==mesh.data.get('wl_source_model_key'))
b=entity('Track placement B',(-3,4,2),(0,0,1.2));life.attach(ctx,asset,b,select=False);ctx.view_layer.update()
ref=next(o for o in b.children if o.get('wl_model_linked_asset')==asset)
assert ref.instance_collection==asset
assert close([ref.matrix_world@v for v in points(mesh)],[b.matrix_world@a.matrix_world.inverted()@v for v in points(mesh)])
a.location.x+=1;ctx.view_layer.update();ctx.view_layer.update()
assert max(abs(ref.matrix_basis[i][j]-a.matrix_world.inverted()[i][j]) for i in range(4) for j in range(4))<1e-5
# Editing a linked placement must retain its shared asset identity.
collections_before=set(bpy.data.collections)
assert life.edit(ctx,b)==asset
assert set(bpy.data.collections)==collections_before
assert b['wl_custom_model']==asset and a['wl_custom_model']==asset
ctx.view_layer.objects.active=b
assert bpy.ops.wavelength.select_model_sources(source_name=mesh.name)=={'FINISHED'}
assert ctx.object==mesh and mesh.select_get()
original=points(mesh);wanted=[b.matrix_world@a.matrix_world.inverted()@v for v in original]
image=bpy.data.images.new('Editable original pixels',2,2);image.pixels[:]=[.2,.3,.4,1]*4
node=mesh.data.materials[0].node_tree.nodes.new('ShaderNodeTexImage');node.image=image
asset['wl_model_publish_settings']=json.dumps({'model_name':'original','output_directory':'original-output'})
variant=life.make_unique(ctx,asset,b);ctx.view_layer.update();copy=next(o for o in variant.objects if o.type=='MESH')
assert 'wl_model_publish_settings' not in variant
assert variant['wl_model_id']!=identity and variant['wl_model_parent_id']==identity
assert copy.data!=mesh.data and copy.data.materials[0]!=mesh.data.materials[0]
assert close(points(mesh),original) and close(points(copy),wanted)
before=points(copy);old_variant=variant;old_copy=copy
variant=life.detach(ctx,old_variant,b);ctx.view_layer.update();copy=next(o for o in variant.objects if o.type=='MESH')
assert b.get('wl_custom_model')==old_variant and old_variant.name in bpy.data.collections
assert copy.data!=old_copy.data and not copy.get('wl_custom_model_owner') and copy.get('wl_exclude') and close(points(copy),before)
assert variant['wl_model_id']!=old_variant['wl_model_id'] and variant.wavelength_model.origin is not None
original_image=next(n.image for n in old_copy.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Editable original'))
detached_image=next(n.image for n in copy.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Editable original'))
assert detached_image!=original_image and detached_image.packed_file and not detached_image.filepath_raw,(detached_image.name,original_image.name,bool(detached_image.packed_file),detached_image.filepath_raw,detached_image.source)
old_pixel=original_image.pixels[0];detached_image.pixels[0]=.9;detached_image.update()
assert original_image.pixels[0]==old_pixel and image.pixels[0]==old_pixel
life.attach(ctx,variant,b);ctx.view_layer.update();assert close(points(copy),before) and b['wl_custom_model']==variant
# Detaching a linked placement must not steal the other placement's sources.
c=entity('Track placement C',(2,9,4));life.attach(ctx,asset,c,select=False)
untouched=points(mesh);detached=life.detach(ctx,asset,c);ctx.view_layer.update()
assert detached!=asset and a.get('wl_custom_model')==asset and c.get('wl_custom_model')==asset and close(points(mesh),untouched)
# Original placement promotion when its origin makes an independent variant.
d=entity('Track placement D',(12,3,2));life.attach(ctx,asset,d,select=False)
promoted=next(o for o in life.bindings(asset) if o!=a)
wanted_d=[promoted.matrix_world@a.matrix_world.inverted()@v for v in points(mesh)]
unique_a=life.make_unique(ctx,asset,a);ctx.view_layer.update()
assert asset.wavelength_model.origin==promoted and d.get('wl_custom_model')==asset
assert close(points(mesh),wanted_d),'Remaining placement moved during definition promotion'
# Both levels' source meshes stay out of ordinary brush export.
assert all(o.get('wl_exclude') for col in (asset,variant,detached,unique_a) for o in life.sources(col))
# Invalid attachment is atomic with respect to model links and transforms.
bad=entity('Wrong destination',(1,2,3),classname='func_detail');snapshot=points(copy)
try:life.attach(ctx,variant,bad)
except ValueError:pass
else:raise AssertionError('Brush entity accepted an MDL model')
assert not bad.get('wl_custom_model') and close(points(copy),snapshot)
# Native entity duplication retains a linked editable-model representation.
from wavelength.source import identity as identity_system
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);ctx.view_layer.objects.active=a
identity_system.update_ids();bpy.ops.object.duplicate();duplicate=ctx.object
identity_system.update_ids();ctx.view_layer.update()
assert duplicate['wl_custom_model']==unique_a and duplicate['wl_id']!=a['wl_id']
assert any(o.get('wl_model_linked_asset')==unique_a for o in duplicate.children)
# Attachment remains discoverable after making an unbound destination active.
target=entity('UI attachment destination',(8,9,2));bpy.ops.object.select_all(action='DESELECT')
copy.select_set(True);target.select_set(True);ctx.view_layer.objects.active=target
from types import SimpleNamespace
class Layout:
    def __init__(self):self.operators=[]
    def operator(self,name,**kwargs):self.operators.append(name);return SimpleNamespace()
    def label(self,**kwargs):pass
    def box(self):return self
    def row(self,**kwargs):return self
layout=Layout();assert model_io.WL_PT_model_asset.poll(ctx)
model_io.WL_PT_model_asset.draw(SimpleNamespace(layout=layout),ctx)
assert 'wavelength.attach_model_asset' in layout.operators
assert bpy.ops.wavelength.attach_model_asset()=={'FINISHED'} and target['wl_custom_model']==variant
ctx.view_layer.objects.active=target
assert bpy.ops.wavelength.detach_model_asset()=={'FINISHED'}
assert target['wl_custom_model']==variant and model_io.active_asset(ctx)!=variant
# Unsupported texture copies cancel cleanly instead of sharing editable pixels
# or leaving a half-created asset in the level.
tiled=bpy.data.images.new('Unsupported tiled fixture',2,2,tiled=True)
tiled_node=copy.data.materials[0].node_tree.nodes.new('ShaderNodeTexImage');tiled_node.image=tiled
old_collections=set(bpy.data.collections);old_objects=set(bpy.data.objects)
try:life.detach(ctx,variant,b)
except ValueError:pass
else:raise AssertionError('Tiled image was silently shared by an independent asset')
assert set(bpy.data.collections)==old_collections and set(bpy.data.objects)==old_objects
assert b['wl_custom_model']==variant
copy.data.materials[0].node_tree.nodes.remove(tiled_node);bpy.data.images.remove(tiled)
folder=root/'build/model-lifecycle';folder.mkdir(parents=True,exist_ok=True)
names=(a.name,b.name,copy.name,asset.name,variant.name,identity)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'phase-one.blend'))
bpy.ops.wm.open_mainfile(filepath=str(folder/'phase-one.blend'))
a,b,copy=(bpy.data.objects[n] for n in names[:3]);asset=bpy.data.collections[names[3]];variant=bpy.data.collections[names[4]]
assert asset['wl_model_id']==names[5] and model_io.asset_for_object(copy)==variant
assert custom_models.definition(b)==variant
reloaded_image=next(n.image for n in copy.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Editable original'))
assert reloaded_image.packed_file and abs(reloaded_image.pixels[0]-.9)<.01,('Detached texture edits did not survive save/reload',reloaded_image.pixels[0],reloaded_image.colorspace_settings.name)
assert all(hasattr(bpy.ops.wavelength,n) for n in ('edit_model','make_model_unique','attach_model_asset','detach_model_asset'))
print('PASS mounted editable model, profile units/world pose, stable identity, independent materials, linked instances, origin promotion, attach/detach, exclusions and save/reload',flush=True)
