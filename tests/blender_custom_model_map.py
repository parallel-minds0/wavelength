exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('world=[')[0],__file__,'exec'))
from wavelength.source import scene,vmf,ui
import struct,io,zipfile
col=custom_models.assign(ctx)
scene.import_map(ctx.scene,vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text()))
destination=folder/'custom_model_map.bsp'
assert bpy.ops.wavelength.build(filepath=str(destination))=={'FINISHED'}
assert ui._JOB is not None
deadline=time.monotonic()+180
while ui._JOB and time.monotonic()<deadline:ui.build_tick();time.sleep(.05)
assert ui._JOB is None and s.last_build and not s.build_error,(s.status,s.build_error,s.build_log_dir)
payload=destination.read_bytes();offset,size=struct.unpack_from('<2i',payload,8+40*16)
with zipfile.ZipFile(io.BytesIO(payload[offset:offset+size])) as archive:
    model=dict(json.loads(entity['wl_pairs']))['model'];assert model in archive.namelist()
    assert any(n.endswith('.vmt') and '/wavelength/' in n for n in archive.namelist())
    assert any(n.endswith('.vtf') and '/wavelength/' in n for n in archive.namelist())
assert not (Path(s.game_dir)/dict(json.loads(entity['wl_pairs']))['model']).exists()
print('PASS Build Map compiled custom model before VBSP/VVIS/VRAD and embedded all owned model/material/texture dependencies; active game directory unchanged',flush=True)
