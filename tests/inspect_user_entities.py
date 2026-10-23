import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False);bpy.context.preferences.use_preferences_save=False
from wavelength.source.entity import source_schema
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--')+1])
s=bpy.context.scene.wavelength
print('PROFILE',s.engine,s.game_dir,'FGD',s.fgd_path,flush=True)
print('ACTIVE',bpy.context.view_layer.objects.active,flush=True)
for o in bpy.context.scene.objects:
    pairs=o.get('wl_pairs',o.get('wl_entity_pairs','[]'))
    try:classname=dict(json.loads(pairs)).get('classname','')
    except Exception:continue
    if not classname:continue
    if any(c.name.startswith('_WL_') for c in o.users_collection) and not o.select_get():continue
    try:fields=[p['key'] for p in source_schema.model_fields(s,classname,bpy.path.abspath)]
    except Exception as e:fields=str(e)
    print('ENTITY',o.name,'class',classname,'role',o.get('wl_role'),'excluded',o.get('wl_exclude'),'template',o.get('wl_entity_browser_template'),'selected',o.select_get(),'fields',fields,'collections',[c.name for c in o.users_collection],flush=True)
