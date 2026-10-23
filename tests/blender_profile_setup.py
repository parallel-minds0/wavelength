"""Real lifecycle controls, bounded preview import and dependency invalidation."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import profile_setup,asset_browser,asset_index,source_assets
profile_setup._AUTO=False
test=root/'build/profile-setup-integration'/str(time.time_ns());test.mkdir(parents=True,exist_ok=True);profile_setup._CACHE_ROOT=test/'cache'
game=test/'tiny-game';game.mkdir(exist_ok=True)
manifest=json.loads((root/'build/library-setup-tests/source_hl2_windows/manifest.json').read_text())
original=source_assets.Assets(s.game_dir)
for record in manifest['records'].values():
    for path,digest in record['dependencies'].items():
        if digest and not path.startswith('wavelength/icons/'):
            out=game/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(original.read(path))
(game/'gameinfo.txt').write_text('"GameInfo" { "FileSystem" { "SearchPaths" { "Game" "'+str(game).replace('\\','/')+'" } } }')
fgd=test/'tiny.fgd';fgd.write_text('@PointClass studio("models/weapons/w_crowbar.mdl") = weapon_crowbar []\n@PointClass studio("models/props_junk/wood_crate001a.mdl") = crate []')
s.game_dir=str(game);s.fgd_path=str(fgd);s.auto_prepare_assets=False
assert profile_setup.state(s)['state']=='READY_FOR_SETUP'
blocks=[]
for category,path in [('MODEL','models/weapons/w_crowbar.mdl'),('ENTITY','weapon_crowbar')]:
    obj=bpy.data.objects.new('Preview '+category,None);ctx.collection.objects.link(obj)
    asset_browser.metadata(obj,asset_index.record(s.engine,path,category));asset_browser.preview(obj);blocks.append(obj)
assert bpy.ops.wavelength.library_setup(action='START')=={'FINISHED'}
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    profile_setup.tick();state=profile_setup.state(s)
    if state.get('state')=='READY' and all(o.get('wl_library_preview') for o in blocks):break
    assert state.get('state')!='FAILED',state
    time.sleep(.1)
else:raise AssertionError(profile_setup.state(s))
assert all(tuple(o.preview.image_size)==(128,128) for o in blocks)
assert all(o.type=='EMPTY' for o in blocks),'Thumbnail work must not import model meshes into the user scene'
cache=profile_setup.folder(profile_setup.configuration(s));before={p.name:p.stat().st_mtime_ns for p in cache.glob('*.png')}
assert bpy.ops.wavelength.library_setup(action='PAUSE')=={'FINISHED'}
assert profile_setup.state(s)['state']=='PAUSED'
assert bpy.ops.wavelength.library_setup(action='START')=={'FINISHED'}
deadline=time.monotonic()+30
while time.monotonic()<deadline:
    profile_setup.tick()
    if profile_setup.state(s).get('state')=='READY':break
    time.sleep(.1)
assert before=={p.name:p.stat().st_mtime_ns for p in cache.glob('*.png')}
ctx.scene.wavelength_context.mode='CLEAN';profile_setup.tick()
assert profile_setup._process is None,'Clean Preview must stop background preparation'
ctx.scene.wavelength_context.mode='EDIT'
assert bpy.ops.wavelength.library_setup(action='START')=={'FINISHED'}
state=profile_setup.state(s);key=state['assets']['MODEL:models/weapons/w_crowbar.mdl']['record'];record=state['records'][key]
material=next(p for p in record['dependencies'] if p.endswith('.vmt'))
with (game/material).open('a') as stream:stream.write('\n// changed material for invalidation test\n')
bpy.ops.wavelength.library_setup(action='REFRESH')
deadline=time.monotonic()+30
while time.monotonic()<deadline:
    profile_setup.tick()
    if (cache/record['image']).stat().st_mtime_ns!=before[record['image']] and profile_setup.state(s).get('state')=='READY':break
    time.sleep(.1)
assert (cache/record['image']).stat().st_mtime_ns!=before[record['image']]
assert all(p.stat().st_mtime_ns==before[p.name] for p in cache.glob('*.png') if p.name!=record['image'])
bpy.ops.wavelength.library_setup(action='CANCEL');assert profile_setup.state(s)['state']=='CANCELLED'
assert profile_setup._process is None
print('PASS real profile setup index/render/ready, native asset image previews, pause/resume/cancel, cache reuse and targeted material invalidation; editor remains metadata-only',flush=True)
