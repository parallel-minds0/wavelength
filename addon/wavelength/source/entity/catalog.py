from .. import profiles
"""Engine-specific starter catalogs, extended by the project's game FGD."""
import bpy
from . import fgd

COMMON='info_player_start info_player_deathmatch light light_spot func_door func_wall func_button trigger_multiple trigger_once trigger_relay trigger_changelevel'.split()
CATALOG={
 'quake':COMMON+' info_intermission info_teleport_destination light_fluoro light_fluorospark light_globe light_torch_small_walltorch func_plat func_train func_episodegate func_bossgate trigger_secret trigger_counter trigger_teleport trigger_setskill trigger_onlyregistered monster_army monster_dog monster_ogre monster_knight monster_hell_knight monster_zombie monster_wizard monster_demon1 monster_shambler monster_enforcer monster_tarbaby monster_fish monster_boss monster_oldone item_health item_armor1 item_armor2 item_armorInv item_shells item_spikes item_rockets item_cells item_key1 item_key2 item_artifact_super_damage item_artifact_invulnerability item_artifact_envirosuit item_artifact_invisibility weapon_supershotgun weapon_nailgun weapon_supernailgun weapon_grenadelauncher weapon_rocketlauncher weapon_lightning ambient_drip ambient_drone ambient_comp_hum ambient_thunder ambient_light_buzz ambient_swamp1 ambient_swamp2'.split(),
 'goldsrc':[],
 'goldsrc_linux':[],
 'goldsrc_linux_steam':[],
}
_items=[]

def items(settings,context):
    global _items
    if profiles.is_goldsrc(settings.engine):
        from . import goldsrc as goldsrc_entities
        names={name:'' for name in goldsrc_entities.class_names()}
    else:
        names={name:'' for name in CATALOG[settings.engine]}
    if settings.fgd_path:
        try:
            for name,definition in fgd.load(bpy.path.abspath(settings.fgd_path)).items():
                if definition['kind'].lower()!='baseclass':names[name]=definition['description']
        except (OSError,ValueError):pass
    _items=[(name,name,description) for name,description in sorted(names.items())]
    return _items


def choose(settings,context):
    settings.entity_class=settings.entity_choice
