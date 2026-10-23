"""GoldSrc entity model resolution and shared Blender geometry/materials."""
import hashlib
from pathlib import Path
from collections import OrderedDict
import bpy
from . import goldsrc_model,profiles
from .entity import fgd

_SCHEMAS={};_DECODED=OrderedDict()
BUILTINS={'item_healthkit':'w_medkit','item_battery':'w_battery','item_longjump':'w_longjump','ammo_9mmclip':'w_9mmclip','ammo_9mmAR':'w_9mmARclip','ammo_ARgrenades':'w_ARgrenade','ammo_buckshot':'w_shotbox','ammo_357':'w_357ammobox','ammo_crossbow':'w_crossbow_clip','ammo_rpgclip':'w_rpgammo','ammo_gaussclip':'w_gaussammo'}
PLAYER_MARKERS={'info_player_start','info_player_deathmatch','info_player_coop','info_teleport_destination'}
BUILTINS.update({name:'player' for name in PLAYER_MARKERS})
BUILTINS.update({'monster_scientist_dead':'scientist','monster_sitting_scientist':'scientist','monster_hevsuit_dead':'player','monster_grunt_repel':'hgrunt','monster_satchel':'w_satchel','monster_tripmine':'v_tripmine','monster_snark':'w_squeak','weapon_9mmhandgun':'w_9mmhandgun','weapon_9mmAR':'w_9mmAR','weapon_357':'w_357','weapon_handgrenade':'w_grenade','weapon_snark':'w_squeak','ammo_egonclip':'w_gaussammo','ammo_glockclip':'w_9mmclip','ammo_mp5clip':'w_9mmARclip','ammo_mp5grenades':'w_ARgrenade'})

def definitions(settings):
    schema=bpy.path.abspath(settings.fgd_path) if settings.fgd_path else ''
    if schema and Path(schema).is_file():
        cached=_SCHEMAS.get(schema)
        if not cached or any(not p.is_file() or p.stat().st_mtime_ns!=stamp for p,stamp in cached[0]):
            files=set();classes=fgd.load(schema,files=files);cached=([(p,p.stat().st_mtime_ns) for p in files],classes);_SCHEMAS[schema]=cached
        return cached[1]
    return {}

def candidates(settings,classname,pairs):
    explicit=str(dict(pairs).get('model','')).replace('\\','/').strip()
    if explicit and explicit!=':':return [explicit] if explicit.lower().endswith('.mdl') else []
    classes=definitions(settings);model=fgd.studio_model(classes,classname)
    if model:return [model]
    if classes.get(classname,{}).get('kind','').lower()=='solidclass':return []
    from .entity import icons
    if classname not in PLAYER_MARKERS and icons.has_icon(classname):return []
    from .entity.models import candidates as legacy_candidates
    names=([BUILTINS[classname]] if classname in BUILTINS else [])+legacy_candidates(classname,pairs)
    return ['models/'+name+'.mdl' for name in dict.fromkeys(names)]

def decoded(assets,path,skin,body,sequence,game):
    key=(game,path,skin,body,sequence);cached=_DECODED.get(key)
    if cached:
        data,dependencies=cached
        try:valid=all(hashlib.sha256(assets.read(name)).hexdigest()==digest for name,digest in dependencies.items())
        except ValueError:valid=False
        if valid:_DECODED.move_to_end(key);return data
    assets.dependencies.clear();data=goldsrc_model.load(assets,path,skin,body,sequence)
    _DECODED[key]=(data,dict(assets.dependencies));_DECODED.move_to_end(key)
    while len(_DECODED)>24:_DECODED.popitem(last=False)
    return data

def mesh(settings,path,assets,values):
    game=bpy.path.abspath(settings.game_dir);sequence=int(values['sequence']) if values.get('sequence') else None
    body=int(values['body'] or '0') if 'body' in values else goldsrc_model.preview_body(assets,path)
    data=decoded(assets,path,int(values.get('skin','0') or '0'),body,sequence,game)
    unit=profiles.unit_meters(settings);key=hashlib.sha256((data['key']+str(unit)).encode()).hexdigest()
    existing=next((m for m in bpy.data.meshes if m.get('wl_goldsrc_model_key')==key),None)
    if existing:return existing
    result=bpy.data.meshes.new(Path(path).stem+' · GoldSrc')
    try:
        result.from_pydata([tuple(v*unit for v in p) for p in data['vertices']],[],data['faces']);result.update()
        uv=result.uv_layers.new(name='UVMap')
        for loop in result.loops:uv.data[loop.index].uv=data['uvs'][loop.vertex_index]
        for polygon,slot in zip(result.polygons,data['slots']):polygon.material_index=slot;polygon.use_smooth=not bool(data['textures'][slot]['flags']&1)
        result.normals_split_custom_set_from_vertices(data['normals'])
        for texture in data['textures']:
            tkey=hashlib.sha256(texture['rgba']+str((texture['width'],texture['height'],texture['flags'])).encode()).hexdigest()
            mat=next((m for m in bpy.data.materials if m.get('wl_goldsrc_texture_key')==tkey),None)
            if mat is None:
                mat=bpy.data.materials.new(texture['name']);mat['wl_goldsrc_texture_key']=tkey;mat.use_nodes=True
                image=bpy.data.images.new(texture['name'],width=texture['width'],height=texture['height'],alpha=True)
                image.pixels.foreach_set([v/255 for v in texture['rgba']]);image.pack()
                node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;shader=mat.node_tree.nodes.get('Principled BSDF')
                mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.8
                if texture['flags']&0x40:mat.node_tree.links.new(node.outputs['Alpha'],shader.inputs['Alpha'])
                if texture['flags']&(4|32):
                    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Emission Color']);shader.inputs['Emission Strength'].default_value=1
            result.materials.append(mat)
        result['wl_goldsrc_model_key']=key;return result
    except Exception:bpy.data.meshes.remove(result);raise

def attach(entity,pairs):
    settings=bpy.context.scene.wavelength;assets=goldsrc_model.Assets(bpy.path.abspath(settings.game_dir));classname=dict(pairs).get('classname','')
    options=candidates(settings,classname,pairs)
    for path in options:
        try:assets.read(path)
        except ValueError:continue
        geometry=mesh(settings,path,assets,dict(pairs))
        from .entity import models
        models.remove_reference(entity)
        from . import model_import
        child=model_import.attach(bpy.context,entity,geometry,path)
        child['wl_goldsrc_reference']=True
        if classname in PLAYER_MARKERS:
            child['wl_editor_helper']=True
            child.location.z=-min(v.co.z for v in geometry.vertices)
        entity.pop('wl_model_error',None);return True
    if str(dict(pairs).get('model','')).lower().endswith('.mdl') or classname.startswith(('monster_','weapon_','ammo_')) or classname in BUILTINS:
        raise ValueError('No installed GoldSrc model found for '+classname+': '+', '.join(options[:4]))
    return False
