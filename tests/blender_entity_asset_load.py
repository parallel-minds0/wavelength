import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Matrix,Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source.entity import browser
from wavelength.source import model_browser
from wavelength.source import asset_index
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path=''
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
def orphan(name,collection):
    o=bpy.data.objects.new(name,None);collection.objects.link(o)
    o['wl_role']='ENTITY';o['wl_exclude']=True;o['wl_entity_browser_template']='prop_static';o['wl_entity_browser_profile']=bpy.context.scene.wavelength.engine
    o['wl_pairs']=json.dumps([['classname','prop_static'],['targetname','keep_me'],['skin','2']]);return o
browser_collection=bpy.data.collections.new('_WL_ENTITY_BROWSER_ASSETS_test');ctx.scene.collection.children.link(browser_collection)
template=orphan('Template stays excluded',browser_collection)
bpy.app.handlers.depsgraph_update_post.remove(browser._depsgraph)
placed=orphan('Saved placement',ctx.collection);placed.location=(1,2,3);placed.select_set(True);ctx.view_layer.objects.active=placed
folder=root/'build/entity-model-browser';folder.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'legacy-unfinalized.blend'))
bpy.app.handlers.depsgraph_update_post.append(browser._depsgraph)
bpy.ops.wm.open_mainfile(filepath=str(folder/'legacy-unfinalized.blend'))
assert browser._depsgraph in bpy.app.handlers.depsgraph_update_post
assert browser.repair_loaded_drops in bpy.app.handlers.load_post
placed=bpy.data.objects['Saved placement'];template=bpy.data.objects['Template stays excluded']
assert not placed.get('wl_entity_browser_template') and not placed.get('wl_exclude')
assert dict(json.loads(placed['wl_pairs']))['targetname']=='keep_me' and dict(json.loads(placed['wl_pairs']))['skin']=='2'
assert (placed.location-Vector((1,2,3))).length<1e-6
assert template.get('wl_entity_browser_template')=='prop_static' and template.get('wl_exclude')
assert model_browser.target()[0]==placed
model_browser.assign(bpy.context,asset_index.record(bpy.context.scene.wavelength.engine,'models/props_junk/wood_crate001a.mdl'))
assert dict(json.loads(placed['wl_pairs']))['model']=='models/props_junk/wood_crate001a.mdl'
assert len([c for c in placed.children if c.get('wl_model_reference')])==1
print('PASS file load repairs placed prop_static, retains authored values/transform, and enables the assignment target; source template stays excluded',flush=True)
new=orphan('Dropped after load',bpy.context.collection);bpy.context.view_layer.update()
assert not new.get('wl_entity_browser_template') and not new.get('wl_exclude')
print('PASS entity asset drop handler survives opening a blend and finalizes subsequent placements',flush=True)
