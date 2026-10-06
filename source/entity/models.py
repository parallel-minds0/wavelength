"""Editor-only visual references for GoldSrc point entities."""
from pathlib import Path
import bpy

from ..paths import MODEL_ROOT
_CACHE = {}

ALIASES = {
    'monster_scientist':'scientist','monster_barney':'barney','monster_gman':'gman',
    'monster_headcrab':'headcrab','monster_babycrab':'baby_headcrab','monster_zombie':'zombie',
    'monster_houndeye':'houndeye','monster_bullchicken':'bullsquid','monster_alien_slave':'islave',
    'monster_alien_grunt':'agrunt','monster_alien_controller':'controller','monster_human_grunt':'hgrunt',
    'monster_human_assassin':'hassassin','monster_tentacle':'tentacle','monster_gargantua':'garg',
    'monster_bigmomma':'big_mom','monster_nihilanth':'nihilanth','monster_ichthyosaur':'ichthyosaur',
    'monster_leech':'leech','monster_barnacle':'barnacle','monster_apache':'apache','monster_osprey':'osprey',
    'monster_sentry':'sentry','monster_turret':'turret','monster_miniturret':'miniturret',
}

def _model_property(pairs):
    values=dict(pairs)
    raw=values.get('model','').replace('\\','/').strip()
    if not raw:return None
    name=Path(raw).name
    return Path(name).stem

def candidates(classname,pairs=()):
    out=[]
    explicit=_model_property(pairs)
    if explicit:out.append(explicit)
    alias=ALIASES.get(classname)
    if alias:out.append(alias)
    out.append(classname)
    for prefix in ('monster_','item_','weapon_','ammo_'):
        if classname.startswith(prefix):
            base=classname[len(prefix):];out.append(base)
            if prefix=='weapon_':out.extend(('w_'+base,'v_'+base,'p_'+base))
    # Stable de-duplication.
    return list(dict.fromkeys(x for x in out if x))

def asset_path(classname,pairs=()):
    if not MODEL_ROOT.is_dir():return None
    for name in candidates(classname,pairs):
        direct=MODEL_ROOT/name/'model.gltf'
        if direct.is_file():return direct
        # Converter output is normally flat, but tolerate a nested model directory.
        nested=MODEL_ROOT/name/name/'model.gltf'
        if nested.is_file():return nested
    return None

def _import_collection(path):
    key=str(path.resolve())
    cached=_CACHE.get(key)
    if cached and cached.name in bpy.data.collections:return cached
    for collection in bpy.data.collections:
        if collection.get('wl_model_cache')==key:
            _CACHE[key]=collection
            return collection
    before=set(bpy.data.objects)
    result=bpy.ops.import_scene.gltf(filepath=str(path))
    if 'FINISHED' not in result:raise RuntimeError(f'glTF import failed: {path}')
    imported=[o for o in bpy.data.objects if o not in before]
    if not imported:raise RuntimeError(f'glTF contained no objects: {path}')
    collection=bpy.data.collections.new('WL Model '+path.parent.name)
    collection['wl_model_cache']=key
    for obj in imported:
        for owner in list(obj.users_collection):owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj['wl_exclude']=True
        obj['wl_role']='MODEL_SOURCE'
    _CACHE[key]=collection
    return collection

def remove_reference(entity):
    for child in list(entity.children):
        if child.get('wl_model_reference'):
            bpy.data.objects.remove(child,do_unlink=True)
    # Model and SVG representations are mutually exclusive.
    try:
        from . import icons as entity_icons
        entity_icons.remove_reference(entity)
    except Exception:
        pass

def attach_reference(entity,pairs=None):
    """Attach a cheap, editor-only model collection instance to a point entity."""
    if entity is None or entity.get('wl_role')!='ENTITY':return False
    if pairs is None:
        import json
        try:pairs=json.loads(entity.get('wl_pairs','[]'))
        except (TypeError,ValueError):pairs=[]
    classname=dict(pairs).get('classname',entity.name)
    path=asset_path(classname,pairs)
    remove_reference(entity)
    if path is None:
        # Only known abstract/editor entities receive SVGs. Entities expected to
        # have models remain unresolved rather than being hidden behind an icon.
        try:
            from . import icons as entity_icons
            return entity_icons.attach_reference(entity,pairs)
        except Exception as exc:
            print(f'Wavelength: entity icon reference failed for {classname}: {exc}')
            return False
    try:collection=_import_collection(path)
    except Exception as exc:
        print(f'Wavelength: model reference failed for {classname}: {exc}')
        return False
    ref=bpy.data.objects.new(classname+' visual',None)
    # Link beside the entity so collection ownership remains predictable.
    owners=list(entity.users_collection)
    (owners[0] if owners else bpy.context.scene.collection).objects.link(ref)
    ref.instance_type='COLLECTION';ref.instance_collection=collection
    ref.parent=entity
    ref.location=(0.0,0.0,0.0)
    ref.rotation_euler=(0.0,0.0,0.0)
    ref.scale=(0.0254,0.0254,0.0254)
    ref['wl_exclude']=True;ref['wl_role']='MODEL_REFERENCE';ref['wl_model_reference']=True
    ref['wl_model_asset']=str(path)
    ref.hide_select=True
    return True
