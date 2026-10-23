"""Real worker preparation, thumbnail reuse and targeted content invalidation."""
import sys,json,subprocess,time,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
blender=r'C:\Users\user\Desktop\blender-5.2.3-candidate+v52.32ede9dba158-windows.amd64-release\blender.exe'
folder=root/'build/library-setup-tests';folder.mkdir(exist_ok=True)
def run(engine,game,fgd,paths):
    cache=folder/engine;cache.mkdir(exist_ok=True)
    request=dict(engine=engine,game_dir=game,fgd_path=fgd,cache=str(cache),paths=paths,watch=False)
    config=cache/'request.json';config.write_text(json.dumps(request))
    result=subprocess.run([blender,'--background','--factory-startup','--threads','2','--python',str(root/'addon/wavelength/source/library_prepare_worker.py'),'--',str(config)],capture_output=True,text=True,errors='replace',timeout=120)
    (cache/'worker-test.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout[-3000:]+result.stderr
    manifest=json.loads((cache/'manifest.json').read_text());assert manifest['state']=='READY',manifest
    assert manifest['done']==manifest['total'] and manifest['errors']==0,manifest
    for entry in manifest['assets'].values():
        record=manifest['records'][entry['record']];assert (cache/record['image']).read_bytes().startswith(b'\x89PNG')
    return cache,manifest
game=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
paths=['models/weapons/w_crowbar.mdl','models/props_junk/wood_crate001a.mdl']
cache,state=run('source_hl2_windows',game,'',paths)
assert 'ENTITY:weapon_crowbar' in state['assets']
assert 'ENTITY:light' in state['assets']
assert state['assets']['ENTITY:weapon_crowbar']==state['assets']['MODEL:models/weapons/w_crowbar.mdl']
times={p.name:p.stat().st_mtime_ns for p in cache.glob('*.png')}
run('source_hl2_windows',game,'',paths)
assert times=={p.name:p.stat().st_mtime_ns for p in cache.glob('*.png')},'Unchanged content was unnecessarily rerendered'
cache,state=run('goldsrc',r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life\valve',r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life SDK\Hammer Editor\fgd\half-life\halflife.fgd',['models/w_crowbar.mdl','models/scientist.mdl','models/player.mdl','models/playert.mdl','models/concrete_gibs.mdl'])
assert 'ENTITY:info_player_start' in state['assets']
assert 'ENTITY:light' in state['assets']
assert 'MODEL:models/playert.mdl' not in state['assets']
assert 'ENTITY:weapon_crowbar' in state['assets'] and 'ENTITY:monster_scientist' in state['assets']
print('PASS Source and HL1 background setup, actual entity/model thumbnails, shared preview records and unchanged-cache reuse')
