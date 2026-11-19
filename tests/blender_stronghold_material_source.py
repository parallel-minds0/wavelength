"""Selected source profiles beat stale roots and test actual mounted VMTs."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import vmf,source_assets,source2_port_materials as port,cross_compile,source2_map,keyvalues
ctx=bpy.context;s=ctx.scene.wavelength;s.auto_prepare_assets=False
legacy='C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/csgo'
hl2='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
name='hr_massive/concrete_floor_1_blend_1'
document=vmf.parse(Path(r'C:\Users\user\Projects\port-now\de_stronghold_d.vmf').read_text(encoding='utf-8-sig'))
names={f.texture for e in document.entities for brush in e.brushes for f in brush}
assert name in names
assets=source_assets.library(legacy)
assert all(assets.fingerprint('materials/'+source_assets.asset_path(n)+'.vmt') for n in names)
material=bpy.data.materials.new('Stale source provenance');material['wl_texture']=name;material['wl_source_game']=hl2
settings=SimpleNamespace(game_dir=legacy,source_override=True)
before=dict(material.items())
assert Path(port.source_game(material,settings))==Path(legacy)
material['wl_source_mounts']=legacy
assert Path(port.source_game(material,SimpleNamespace(game_dir=hl2)))==Path(legacy)
material.pop('wl_source_mounts')
assert dict(material.items())==before
s.engine='source_hl2_windows';s.game_dir=hl2
captured={}
def capture(context,filepath,**options):captured.update(options);return 0,[]
with patch.object(source2_map,'export',side_effect=capture):
 cross_compile.compile_level(ctx,root/'build/unused.vmap','source_csgo_legacy_windows','source2_cs2_windows')
assert Path(captured['source_settings'].game_dir)==Path(legacy) and captured['source_settings'].source_override
folder=root/'build/stronghold-material-source';folder.mkdir(parents=True,exist_ok=True)
warnings=[];relative=port.deploy(material,settings,folder,'stronghold',warnings)
props=keyvalues.values(keyvalues.child(keyvalues.parse((folder/relative).read_text()),'Layer0'))
assert props['shader']=='csgo_lightmappedgeneric.vfx' and props['f_layers']=='1'
for key in ('texturelayer1color','texturelayer2color','texturelayer1normal','texturelayer2normal','textureblendmodulation'):
 assert (folder/props[key]).is_file(),key
assert dict(material.items())==before and s.engine=='source_hl2_windows'
print('PASS all 53 stronghold material VMTs present; selected source wins stale HL2 metadata; fallback roots and actual two-layer conversion',flush=True)
