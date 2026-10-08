import bpy,sys,tempfile,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'addon'))
import wavelength
from wavelength.source import vmf,scene,profiles
wavelength.register();s=bpy.context.scene.wavelength
for profile in ('source_hl2_linux','source_hl2_windows'):
 s.engine=profile
 from wavelength.source.entity import catalog
 assert any(x[0]=='npc_citizen' for x in catalog.items(s,bpy.context))
 assert s.launch_args!='[]'
 assert all(getattr(s,field)=='[]' for field in ('source_vbsp_args','source_vvis_args','source_vrad_args'))
scene.import_map(bpy.context.scene,vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text()))
text=vmf.write(scene.export_map(bpy.context.scene));doc=vmf.parse(text)
assert len(doc.entities[0].brushes)==6
out=root/'build/source-smoke.vmf'
assert bpy.ops.wavelength.export_map(filepath=str(out))=={'FINISHED'}
assert out.read_text().startswith('versioninfo')
obj=next(o for o in bpy.context.scene.objects if o.get('wl_role')=='BRUSH')
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
s.texture='tools/toolsnodraw'
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
assert 'tools/toolsnodraw' in vmf.write(scene.export_map(bpy.context.scene))
# Verify Source build orchestration using explicit fake compiler fixtures, not game compilers.
import time,os
from wavelength.source import ui
with tempfile.TemporaryDirectory() as folder:
    folder=Path(folder);game=folder/'hl2';game.mkdir();(game/'gameinfo.txt').write_text('GameInfo {}')
    tools=folder/'bin';tools.mkdir()
    for stage in ('vbsp','vvis','vrad'):
        tool=tools/stage
        tool.write_text('#!/usr/bin/env python3\nimport sys,json,struct\nfrom pathlib import Path\nPath("'+stage+'.args.json").write_text(json.dumps(sys.argv[1:]))\n'+('Path("chosen.bsp").write_bytes(b"VBSP"+struct.pack("<i",20)+bytes(1028))\n' if stage=='vbsp' else ''))
        tool.chmod(0o755)
    s.compiler_dir=str(tools);s.game_dir=str(game);s.project_dir=str(folder/'work')
    s.source_vbsp_args='' # Recover an older saved scene with empty compiler arguments.
    out=folder/'chosen.bsp'
    bpy.ops.wavelength.build(filepath=str(out))
    while ui._JOB:ui.build_tick();time.sleep(.02)
    assert out.is_file(),s.status
    assert json.loads((ui._JOB_PATH/'vbsp.args.json').read_text())==['-game',str(game),'chosen.vmf']
    assert not (ui._JOB_PATH/'textures.wad').exists()
wavelength.unregister()
print('PASS Source Linux/Windows profiles, catalog, six-brush VMF scene roundtrip, export operator and Source material assignment')
