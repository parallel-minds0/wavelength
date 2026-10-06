"""Built-in Half-Life/GoldSrc entity property fallback.

This is intentionally a pragmatic authoring catalog, not a replacement for a
mod's FGD. Loaded FGD data wins; these definitions fill missing inherited or
stock HL1 fields so the UI remains useful out of the box.
"""

def P(key, label=None, typ='string', default='', choices=()):
    return {'key':key,'label':label or key,'type':typ,'default':str(default),'choices':list(choices)}

def C(*items): return tuple(items)

BASE={
 'Targetname':[
  P('targetname','Target Name'),
 ],
 'Target':[
  P('target','Target'),
  P('killtarget','Kill Target'),
  P('delay','Delay Before Trigger','float','0'),
 ],
 'Master':[
  P('master','Master'),
 ],
 'Angles':[
  P('angles','Pitch Yaw Roll (Y Z X)','string','0 0 0'),
 ],
 'MoveDirection':[
  # func_door movement is stored directly as GoldSrc's `angles` vector.
  P('angles','Direction','choices','0 0 0',C(
   ('0 0 0','East (+X)','1'),
   ('0 90 0','North (+Y)','0'),
   ('0 180 0','West (-X)','0'),
   ('0 270 0','South (-Y)','0'),
   ('-90 0 0','Up (+Z)','0'),
   ('90 0 0','Down (-Z)','0'),
  )),
 ],
 'RenderFields':[
  P('rendermode','Render Mode','choices','0',C(('0','Normal','1'),('1','Color','0'),('2','Texture','0'),('3','Glow','0'),('4','Solid','0'),('5','Additive','0'))),
  P('renderamt','FX Amount','integer','255'),
  P('rendercolor','FX Color (R G B)','color255','255 255 255'),
  P('renderfx','Render FX','integer','0'),
 ],
 'Trigger':[
  P('target','Target'),P('targetname','Target Name'),P('killtarget','Kill Target'),P('netname','Net Name'),P('master','Master'),
  P('delay','Delay Before Trigger','float','0'),P('message','Message'),P('sounds','Sound Style','integer','0'),
  P('spawnflags','Spawn Flags','flags','0',C(('1','Monsters','0'),('2','No Clients','0'),('4','Pushables','0'))),
 ],
 'Light':[
  P('targetname','Target Name'),P('_light','Brightness / Color','string','255 255 255 200'),P('style','Appearance','integer','0'),
 ],
}

# classname: (base names, direct properties)
ENTITIES={
 'trigger_once':(('Trigger',),[]),
 'trigger_multiple':(('Trigger',),[P('wait','Delay Before Reset','float','0.2')]),
 'trigger_relay':(('Targetname','Target','Master'),[P('triggerstate','Trigger State','choices','0',C(('0','Off','1'),('1','On','0'),('2','Toggle','0')))]),
 'trigger_auto':(('Target','Master'),[P('globalstate','Global State to Read'),P('triggerstate','Trigger State','choices','0',C(('0','Off','1'),('1','On','0'),('2','Toggle','0'))),P('spawnflags','Spawn Flags','flags','0',C(('1','Remove On Fire','0')))]),
 'trigger_hurt':(('Trigger',),[P('dmg','Damage','float','10'),P('damagetype','Damage Type','integer','0')]),
 'trigger_push':(('Trigger','Angles'),[P('speed','Speed of Push','float','40'),P('spawnflags','Spawn Flags','flags','0',C(('1','Once Only','0')))]),
 'trigger_teleport':(('Trigger',),[]),
 'trigger_changelevel':(('Targetname',),[P('map','New Map Name'),P('landmark','Landmark Name')]),
 'trigger_gravity':(('Trigger',),[P('gravity','Gravity (0-1)','float','1')]),
 'trigger_camera':(('Targetname','Target'),[P('wait','Hold Time','float','10'),P('moveto','Path Corner'),P('acceleration','Acceleration','float','500'),P('deceleration','Deceleration','float','500'),P('speed','Initial Speed','float','0')]),
 'game_text':(('Targetname','Target','Master'),[
  P('message','Message Text'),P('x','X Position (-1 = center)','float','-1'),P('y','Y Position (-1 = center)','float','-1'),
  P('effect','Text Effect','choices','0',C(('0','Fade In/Out','1'),('1','Credits','0'),('2','Scan Out','0'))),
  P('color','Color 1','color255','100 100 100'),P('color2','Color 2','color255','240 110 0'),
  P('fadein','Fade In Time','float','1.5'),P('fadeout','Fade Out Time','float','0.5'),P('holdtime','Hold Time','float','1.2'),P('fxtime','Effect Time','float','0.25'),
  P('channel','Text Channel','choices','1',C(('1','Channel 1','1'),('2','Channel 2','0'),('3','Channel 3','0'),('4','Channel 4','0'))),
  P('spawnflags','Spawn Flags','flags','0',C(('1','All Players','0'))),
 ]),
 'ambient_generic':(('Targetname',),[P('message','Sound File'),P('health','Volume (0-10)','integer','10'),P('pitch','Pitch','integer','100'),P('pitchstart','Start Pitch','integer','100'),P('spinup','Spin Up Time','integer','0'),P('spindown','Spin Down Time','integer','0'),P('lfotype','LFO Type','integer','0'),P('lforate','LFO Rate','integer','0'),P('lfomodpitch','LFO Pitch Mod','integer','0'),P('lfomodvol','LFO Volume Mod','integer','0'),P('cspinup','Incremental Spinup Count','integer','0'),P('spawnflags','Spawn Flags','flags','0',C(('1','Play Everywhere','0'),('16','Start Silent','0'),('32','Not Toggled','0')))]),
 'env_message':(('Targetname','Target'),[P('message','Message Name'),P('messagesound','Sound Effect'),P('messagevolume','Volume 0-10','integer','10'),P('messageattenuation','Sound Radius','integer','0'),P('spawnflags','Spawn Flags','flags','0',C(('1','Play Once','0'),('2','All Clients','0')))]),
 'env_shake':(('Targetname',),[P('amplitude','Amplitude','float','4'),P('radius','Effect Radius','float','500'),P('duration','Duration','float','1'),P('frequency','Frequency','float','2.5'),P('spawnflags','Spawn Flags','flags','0',C(('1','Global Shake','0')))]),
 'env_render':(('Targetname','Target','RenderFields'),[P('spawnflags','Spawn Flags','flags','0',C(('1','No Render FX','0'),('2','No Render Mode','0'),('4','No FX Amount','0'),('8','No FX Color','0')))]),
 'env_sprite':(('Targetname','RenderFields'),[P('model','Sprite Name'),P('scale','Scale','float','1'),P('framerate','Framerate','float','10'),P('spawnflags','Spawn Flags','flags','0',C(('1','Start On','0'),('2','Play Once','0')))]),
 'light':(('Light',),[P('spawnflags','Spawn Flags','flags','0',C(('1','Initially Dark','0')))]),
 'light_spot':(('Light','Angles'),[P('_cone','Inner Cone','float','10'),P('_cone2','Outer Cone','float','30'),P('pitch','Pitch','float','-90'),P('spawnflags','Spawn Flags','flags','0',C(('1','Initially Dark','0')))]),
 'light_environment':(('Light','Angles'),[P('pitch','Pitch','float','0')]),
 'info_player_start':(('Angles',),[]),
 'info_player_deathmatch':(('Angles',),[]),
 'info_target':(('Targetname',),[]),
 'info_landmark':(('Targetname',),[]),
 'multisource':(('Targetname','Target'),[P('globalstate','Global State Master')]),
 'multi_manager':(('Targetname',),[P('spawnflags','Spawn Flags','flags','0',C(('1','Multithreaded','0')))]),
 'path_corner':(('Targetname','Target'),[P('wait','Wait Here','float','0'),P('speed','New Train Speed','float','0'),P('message','Fire On Pass'),P('spawnflags','Spawn Flags','flags','0',C(('1','Wait for Retrigger','0'),('2','Teleport','0'),('4','Fire Once','0')))]),
 'func_wall':(('Targetname','RenderFields'),[P('spawnflags','Spawn Flags','flags','0',C(('1','Starts Off','0')))]),
 'func_illusionary':(('Targetname','RenderFields'),[P('skin','Contents','integer','-1')]),
 'func_detail':(('Targetname',),[]),
 'func_breakable':(('Targetname','Target','RenderFields'),[P('health','Strength','float','1'),P('material','Material Type','integer','0'),P('explodemagnitude','Gibs Direction / Explosion','integer','0'),P('spawnobject','Spawn On Break','integer','0'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_pushable':(('Targetname','RenderFields'),[P('size','Hull Size','integer','0'),P('buoyancy','Buoyancy','float','1'),P('friction','Friction','float','50'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_button':(('Targetname','Target','Master','Angles','RenderFields'),[P('speed','Speed','float','5'),P('wait','Delay Before Reset','float','1'),P('lip','Lip','float','0'),P('health','Health','float','0'),P('sounds','Sounds','integer','0'),P('locked_sound','Locked Sound','integer','0'),P('unlocked_sound','Unlocked Sound','integer','0'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_door':(('Targetname','Target','Master','MoveDirection','RenderFields'),[P('speed','Speed','float','100'),P('wait','Delay Before Close','float','4'),P('lip','Lip','float','0'),P('dmg','Damage Inflicted','float','0'),P('message','Message if Triggered'),P('netname','Fire on Close'),P('health','Health','float','0'),P('movesnd','Move Sound','integer','0'),P('stopsnd','Stop Sound','integer','0'),P('locked_sound','Locked Sound','integer','0'),P('unlocked_sound','Unlocked Sound','integer','0'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_door_rotating':(('Targetname','Target','Master','Angles','RenderFields'),[P('speed','Speed','float','100'),P('wait','Delay Before Close','float','4'),P('distance','Distance (degrees)','float','90'),P('dmg','Damage Inflicted','float','0'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_train':(('Targetname','Target','RenderFields'),[P('speed','Speed','float','100'),P('dmg','Damage on Block','float','0'),P('sounds','Move Sound','integer','0'),P('volume','Sound Volume','float','0.85'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_water':(('Targetname','RenderFields'),[P('skin','Contents','integer','-3'),P('waveheight','Wave Height','float','0'),P('spawnflags','Spawn Flags','flags','0')]),
 'func_rotating':(('Targetname','RenderFields'),[P('speed','Rotation Speed','float','0'),P('dmg','Damage','float','0'),P('volume','Volume','float','1'),P('sounds','Sound','integer','0'),P('spawnflags','Spawn Flags','flags','0')]),
}

def properties(classname):
    spec=ENTITIES.get(classname)
    if not spec:return []
    bases,direct=spec;merged={}
    for base in bases:
        for prop in BASE.get(base,()):merged[prop['key']]=dict(prop)
    for prop in direct:merged[prop['key']]=dict(prop)
    return list(merged.values())

def merge_properties(classname, primary=()):
    """FGD/project definitions win; built-ins fill only missing stock fields."""
    merged={p['key']:dict(p) for p in properties(classname)}
    for prop in primary:merged[prop['key']]=dict(prop)
    # Keep func_door direction as the literal `angles` value written to MAP.
    if classname=='func_door':
        direction=dict(BASE['MoveDirection'][0])
        source=merged.get('angles') or merged.get('angle') or {}
        label=str(source.get('label','')).strip()
        if label and 'angle' not in label.casefold():direction['label']=label
        merged.pop('angle',None)
        merged['angles']=direction
    return list(merged.values())

# Complete stock Half-Life 1 classname catalog.  The specialized definitions
# above provide richer editor metadata; entries below ensure every stock HL1
# mapper-facing class is available even when no external FGD is configured.
# A loaded project/mod FGD still wins field-for-field via merge_properties().
_POINT_TARGETNAME = '''
button_target cycler cycler_sprite cycler_weapon cycler_wreckage env_beam env_beverage env_blood env_bubbles env_explosion env_fade env_funnel env_global env_glow env_laser env_lightning env_message env_render env_shake env_shooter env_smoker env_sound env_spark env_sprite gibshooter infodecal info_bigmomma info_intermission info_node info_node_air info_null info_player_coop info_player_deathmatch info_player_start info_target info_teleport_destination info_landmark
item_airtank item_antidote item_battery item_healthkit item_longjump item_security item_sodacan item_suit
monster_alien_controller monster_alien_grunt monster_alien_slave monster_apache monster_babycrab monster_barnacle monster_barney monster_bigmomma monster_bullchicken monster_cockroach monster_flyer monster_flyer_flock monster_furniture monster_gargantua monster_generic monster_gman monster_grunt_repel monster_headcrab monster_hevsuit_dead monster_houndeye monster_human_assassin monster_human_grunt monster_ichthyosaur monster_leech monster_miniturret monster_nihilanth monster_osprey monster_rat monster_satchel monster_scientist monster_scientist_dead monster_sentry monster_sitting_scientist monster_snark monster_tentacle monster_tripmine monster_turret monster_zombie
player_loadsaved player_weaponstrip scripted_sentence scripted_sequence aiscripted_sequence speaker
weapon_357 weapon_9mmAR weapon_9mmhandgun weapon_crossbow weapon_crowbar weapon_egon weapon_gauss weapon_handgrenade weapon_hornetgun weapon_rpg weapon_satchel weapon_shotgun weapon_snark weapon_tripmine
ammo_357 ammo_9mmAR ammo_9mmbox ammo_9mmclip ammo_ARgrenades ammo_buckshot ammo_crossbow ammo_egonclip ammo_gaussclip ammo_glockclip ammo_mp5clip ammo_mp5grenades ammo_rpgclip
'''.split()
_POINT_TARGET = '''
game_counter game_counter_set game_end game_player_equip game_player_hurt game_player_team game_score game_team_master game_team_set game_zone_player multi_manager multisource path_corner path_track trigger_auto trigger_camera trigger_cdaudio trigger_changetarget trigger_counter trigger_endsection trigger_gravity trigger_monsterjump trigger_relay
'''.split()
_SOLID = '''
func_breakable func_button func_conveyor func_door func_door_rotating func_friction func_guntarget func_healthcharger func_illusionary func_ladder func_mortar_field func_pendulum func_plat func_platrot func_pushable func_recharge func_rot_button func_rotating func_tank func_tankcontrols func_tanklaser func_tankmortar func_tankrocket func_trackautochange func_trackchange func_tracktrain func_train func_traincontrols func_wall func_wall_toggle func_water
trigger_changelevel trigger_hurt trigger_multiple trigger_once trigger_push trigger_teleport trigger_transition
'''.split()
_OTHER = '''
game_playerdie game_playerkill game_playerspawn game_playerleave game_team_set game_text light_environment light_spot worldspawn
'''.split()

for _name in _POINT_TARGETNAME:
    ENTITIES.setdefault(_name,(('Targetname','Angles'),[]))
for _name in _POINT_TARGET:
    ENTITIES.setdefault(_name,(('Targetname','Target'),[]))
for _name in _SOLID:
    ENTITIES.setdefault(_name,(('Targetname','Target','RenderFields'),[]))
for _name in _OTHER:
    ENTITIES.setdefault(_name,((),[]))

# Stock model/sprite placement and a few high-value stock fields that are
# essential for generic asset placement without an external FGD.
ENTITIES['cycler']=(('Targetname','Angles','RenderFields'),[
    P('model','Model','studio'),P('sequence','Animation Sequence','integer','0'),P('skin','Skin','integer','0'),
])
ENTITIES['cycler_sprite']=(('Targetname','Angles','RenderFields'),[
    P('model','Sprite / Model','sprite'),P('framerate','Framerate','float','10'),P('scale','Scale','float','1'),
])
ENTITIES['monster_generic']=(('Targetname','Angles','RenderFields'),[
    P('model','Model','studio'),P('body','Body','integer','0'),P('skin','Skin','integer','0'),
])
ENTITIES['env_glow']=(('Targetname','RenderFields'),[P('model','Sprite Name','sprite'),P('scale','Scale','float','1')])
ENTITIES['info_player_coop']=(('Angles',),[])
ENTITIES['info_teleport_destination']=(('Targetname','Angles'),[])


def class_names():
    """Concrete stock HL1 classnames supplied by the built-in catalog."""
    return sorted(ENTITIES, key=str.casefold)

ENTITIES['cycler_weapon']=(('Targetname','Angles','RenderFields'),[P('model','Model','studio'),P('scale','Scale','float','1')])
ENTITIES['cycler_wreckage']=(('Targetname','Angles','RenderFields'),[P('model','Sprite Name','sprite','sprites/fire.spr'),P('framerate','Framerate','float','10.0'),P('scale','Scale','float','1.0')])
