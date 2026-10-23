"""Use the selected game's installed Hammer schema, never a Source-wide union."""
from pathlib import Path
from . import fgd
from .. import profiles
_CACHE={}
LEGACY_MODELS={
 'item_ammo_ar2':('models/items/boxbrounds.mdl','models/items/combine_rifle_cartridge01.mdl'),
 'item_ammo_ar2_large':('models/items/largeboxbrounds.mdl','models/items/combine_rifle_cartridge01.mdl'),
 'item_ammo_pistol_large':('models/items/largeboxsrounds.mdl','models/items/boxsrounds.mdl'),
 'item_ammo_smg1_large':('models/items/largeboxmrounds.mdl','models/items/boxmrounds.mdl'),
 'weapon_bugbait':('models/spore.mdl','models/weapons/w_bugbait.mdl'),
 'physics_cannister':('models/fire_equipment/w_weldtank.mdl','models/props_c17/canister01a.mdl'),
}

def installed_representation(settings,classname,value,abspath):
    replacement=LEGACY_MODELS.get(classname)
    if not replacement or value.replace('\\','/').lower()!=replacement[0]:return value
    from .. import source_assets
    try:
        assets=source_assets.library(abspath(settings.game_dir))
        try:assets.read(value);return value
        except (OSError,ValueError):assets.read(replacement[1]);return replacement[1]
    except (OSError,ValueError):return value


def path(settings,abspath=lambda p:p):
    if getattr(settings,'fgd_path',''):return Path(abspath(settings.fgd_path)).resolve()
    game=Path(abspath(settings.game_dir)).expanduser().resolve()
    filename=profiles.get(settings.engine).get('entity_fgd')
    if not filename:raise ValueError('This Source game profile requires an explicit game FGD')
    for candidate in (game.parent/'bin'/filename,game/'bin'/filename):
        if candidate.is_file():return candidate
    raise ValueError('Game entity definitions not found: configure this profile’s FGD path ('+filename+')')


def signature(files):return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in sorted(files))


def definitions(settings,abspath=lambda p:p):
    selected=path(settings,abspath);key=(settings.engine,str(selected))
    cached=_CACHE.get(key)
    if cached and signature(cached[0])==cached[1]:return cached[2]
    files=set();classes=fgd.load(selected,files=files)
    _CACHE[key]=(files,signature(files),classes)
    return classes


def properties(settings,classname,abspath=lambda p:p):
    return fgd.properties(definitions(settings,abspath),classname)


def model_fields(settings,classname,abspath=lambda p:p):
    classes=definitions(settings,abspath)
    if classes.get(classname,{}).get('kind','').lower()=='solidclass':return []
    return [p for p in fgd.properties(classes,classname) if p['type'].lower().lstrip('*') in {'studio','model'}]


def representation_model(settings,classname,pairs=(),abspath=lambda p:p):
    classes=definitions(settings,abspath)
    if classes.get(classname,{}).get('kind','').lower()=='solidclass':return ''
    explicit=str(dict(pairs).get('model','')).strip()
    if explicit.lower().endswith('.mdl'):return installed_representation(settings,classname,explicit,abspath)
    # A brush submodel or an intentional non-model value must not receive an
    # unrelated default representation. ':' is the legacy empty-default bug.
    if explicit and explicit!=':':return ''
    return installed_representation(settings,classname,fgd.studio_model(classes,classname),abspath)


def export_pairs(settings,pairs,abspath=lambda p:p):
    """Drop invalid empty reference defaults emitted by the old FGD reader."""
    classname=dict(pairs).get('classname','')
    props={p['key']:p for p in properties(settings,classname,abspath)}
    references={'target_source','target_destination','target_name_or_class','sound','studio','model'}
    return [(k,installed_representation(settings,classname,v,abspath) if k=='model' else v) for k,v in pairs if not (v==':' and k in props and props[k]['default']=='' and props[k]['type'].lower().lstrip('*') in references)]
