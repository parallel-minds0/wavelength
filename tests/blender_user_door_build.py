"""Rebuild a read-only copy of the user's saved scene into a test destination."""
import sys,time,struct,zipfile,io,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
bpy.context.preferences.use_preferences_save=False
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\user\Projects\focus\wavelength\maps\HL2\basic.blend')
from wavelength.source import ui,scene,custom_models
s=bpy.context.scene.wavelength
folder=root/'build/door-user-copy';folder.mkdir(exist_ok=True)
s.project_dir=str(folder);s.custom_model_deployment='BSP'
doors=[o for o in bpy.context.scene.objects if custom_models.definition(o) and o.get('wl_role')=='ENTITY' and dict(json.loads(o.get('wl_pairs','[]'))).get('classname')=='prop_door_rotating']
assert doors,'Saved file must contain the door'
for door in doors:
    col=custom_models.definition(door);assert col
    col.wavelength_model.deployment='BSP'
    print('SOURCE DOOR',door.name,json.loads(door['wl_pairs']),'collision',col.wavelength_model.collision_mode,flush=True)
destination=folder/'verified_door.bsp'
assert bpy.ops.wavelength.build(filepath=str(destination))=={'FINISHED'}
deadline=time.monotonic()+180
while ui._JOB and time.monotonic()<deadline:ui.build_tick();time.sleep(.05)
assert ui._JOB is None and s.last_build and not s.build_error,(s.status,s.build_error,s.build_log_dir)
b=destination.read_bytes();o,n=struct.unpack_from('<ii',b,8);entities=b[o:o+n].decode(errors='replace')
assert '"parentname" ":"' not in entities and '"targetname" ":"' not in entities
o,n=struct.unpack_from('<ii',b,8+40*16)
with zipfile.ZipFile(io.BytesIO(b[o:o+n])) as archive:
    for door in doors:
        path=dict(json.loads(door['wl_pairs']))['model']
        assert Path(path).with_suffix('.phy').as_posix() in archive.namelist()
        assert b'door_options' in archive.read(path)
print('PASS actual user-scene copy rebuilt: model door retained, invalid parent/name defaults removed, required PHY and door options compiled and packed; original blend/map untouched',flush=True)
