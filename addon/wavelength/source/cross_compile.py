"""Cross-profile conversion contract and conservative, explicit backend registry.

Conversion never edits the authoring scene. Unknown entities/properties stay in
the conversion report rather than silently being treated as compatible.
"""
from . import profiles

FAMILIES=('blender','quake','goldsrc','source','source2','godot','godot4','civ5')
BACKENDS={(a,b):None for a in FAMILIES for b in FAMILIES if a!=b}
LEVEL_BACKENDS=dict(BACKENDS)
POINTS={
    'info_player_start':set(),
    'info_player_terrorist':{'priority','enabled'},
    'info_player_counterterrorist':{'priority','enabled'},
    'info_target':set(),'info_landmark':set(),
}
BRUSHES={'func_buyzone':{'teamnum'},'func_bomb_target':{'heistbomb','bomb_mount_target','bomb_site_designation'},'func_detail':set()}


def profile_settings(identity):
    if identity in profiles.PROFILES:return {'engine':identity}
    # Registered profiles inherit engine routing and target path overrides.
    from . import profile_ui
    return profile_ui.store().get(identity)['settings']


def profile_family(identity):return profiles.family(profile_settings(identity)['engine'])


def source1_to_source2(pairs,kind='point'):
    values={str(k).lower():str(v) for k,v in pairs}
    classname=values.get('classname','')
    result={'status':'manual','source_class':classname,'source_pairs':list(pairs),'properties':{},'warnings':[]}
    table=BRUSHES if kind=='brush' else POINTS
    if classname not in table:
        result['warnings'].append('No verified '+kind+' entity mapping; replace manually')
        return result
    if any(k.startswith('__vmf_output__') for k in values):
        result['warnings'].append('Entity I/O conversion is a stub; preserve connections for manual conversion')
        return result
    allowed=table[classname]|{'classname','targetname','parentname'}
    properties={k:v for k,v in values.items() if k in allowed}
    properties['classname']=classname
    if 'teamnum' in properties:properties['TeamNum']=properties.pop('teamnum')
    if classname in {'info_player_terrorist','info_player_counterterrorist'} and 'enabled' not in properties and 'startdisabled' in values:
        properties['enabled']='0' if values['startdisabled']=='1' else '1'
    ignored=set(values)-allowed-{'origin','angles','angle','id','startdisabled'}
    if ignored:result['warnings'].append('Properties need review: '+', '.join(sorted(ignored)))
    result.update(status='converted',properties=properties)
    if kind=='brush' and classname=='func_detail':
        # Source 2 stores detail as ordinary editable meshes excluded from VIS,
        # not as a runtime func_detail entity or structural world walls.
        result['geometry_mode']='detail'
        result['warnings'].append('Detail brushes become editable meshes excluded from visibility blocking')
    return result


BACKENDS['source','source2']=source1_to_source2


def convert_entity(source_profile,target_profile,pairs,kind='point'):
    source=profile_family(source_profile);target=profile_family(target_profile)
    adapter=BACKENDS.get((source,target))
    if adapter:return adapter(pairs,kind)
    return {'status':'stub','source_class':dict(pairs).get('classname',''),'source_pairs':list(pairs),'properties':{},
            'warnings':[f'Entity conversion backend {source} → {target} is not implemented']}


def _source1_level(context,filepath,source_profile,target_profile,**options):
    from . import source2_map,mesh_assets,source_tools
    from types import SimpleNamespace
    import json
    defaults=mesh_assets.defaults('source2_cs2_windows');active=context.scene.wavelength;target=profile_settings(target_profile)
    game=options.pop('target_game_dir','') or target.get('game_dir') or (active.game_dir if profiles.is_source2(active.engine) else defaults.get('game_dir',''))
    compiler=options.pop('target_compiler_dir','') or target.get('compiler_dir') or (active.compiler_dir if profiles.is_source2(active.engine) else defaults.get('compiler_dir',''))
    settings=SimpleNamespace(engine=target['engine'],profile_id=target_profile,game_dir=game,compiler_dir=compiler,grid_step=target.get('grid_step',active.grid_step))
    source=profile_settings(source_profile);engine=source['engine']
    override=options.pop('source_game_dir','')
    cached=json.loads(active.get('_wl_engine_configs','{}')).get(engine,{})
    source_game=override or source.get('game_dir') or (active.game_dir if active.engine==engine else '') or cached.get('game_dir')
    if not source_game:source_game=source_tools.defaults(profiles.get(engine).get('platform','windows'),engine=engine).get('game_dir','')
    # The selected source profile is an explicit conversion input. Stale
    # per-material provenance must not override its resolved game directory.
    source_settings=SimpleNamespace(game_dir=source_game,source_override=bool(source_game))
    return source2_map.export(context,filepath,source_profile=source_profile,convert_entities=True,target_settings=settings,source_settings=source_settings,**options)


LEVEL_BACKENDS['source','source2']=_source1_level


def register_backend(source_family,target_family,*,level=None,entities=None):
    """Extension seam for engine modules; no routing changes required in the UI."""
    key=(source_family,target_family)
    if level is not None:LEVEL_BACKENDS[key]=level
    if entities is not None:BACKENDS[key]=entities


def compile_level(context,filepath,source_profile,target_profile,**options):
    """Global dispatch; other profile pairs deliberately expose explicit stubs."""
    adapter=LEVEL_BACKENDS.get((profile_family(source_profile),profile_family(target_profile)))
    if adapter:return adapter(context,filepath,source_profile,target_profile,**options)
    raise ValueError(f'Cross-compiling {source_profile} → {target_profile} is a stub; no output was written')


def scene_entities(context,selected=False,source_profile=None):
    """Snapshot point entities and brush groups once, respecting export scope."""
    import json
    from .export_scope import Scope
    scope=Scope(context.scene,context.view_layer);groups={};records=[];engines={}
    objects=context.selected_objects if selected else context.scene.objects
    for obj in objects:
        if not scope.includes(obj):continue
        if obj.get('wl_entity_browser_template') or obj.get('wl_asset_template') or obj.get('wl_model_reference') or obj.get('wl_exclude') or obj.library:continue
        if obj.get('wl_role')=='ENTITY':key='wl_pairs';kind='point'
        elif obj.get('wl_entity_id'):key='wl_entity_pairs';kind='brush'
        else:continue
        if kind=='brush' and obj['wl_entity_id'] in groups:
            record=groups[obj['wl_entity_id']];record['objects'].append(obj)
            record['conversion']['source_transforms'].append({'object':obj.name,'world_matrix_meters':[list(row) for row in obj.matrix_world]})
            continue
        pairs=json.loads(obj.get(key,'[]'))
        origin=source_profile or obj.get('wl_profile') or context.scene.get('wl_import_profile')
        if not origin:
            origin='source_hl2_windows' if obj.get('_wl_source_angles') else context.scene.wavelength.engine
        if origin not in engines:engines[origin]=profile_settings(origin)['engine']
        conversion=convert_entity(engines[origin],'source2_cs2_windows',pairs,kind)
        conversion.update(name=obj.name,kind=kind,source_profile=origin,source_transforms=[{'object':obj.name,'world_matrix_meters':[list(row) for row in obj.matrix_world]}])
        record={'objects':[obj],'conversion':conversion};records.append(record)
        if kind=='brush':groups[obj['wl_entity_id']]=record
    return records
