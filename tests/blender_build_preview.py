"""Compile the saved trainstation preview through the normal Blender operator."""
import sys,time,os
from pathlib import Path
import bpy,addon_utils
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'addon'))
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import ui
bpy.ops.wm.open_mainfile(filepath=os.environ['WL_PREVIEW_BLEND'])
s=bpy.context.scene.wavelength
s.auto_prepare_assets=False
s.project_dir=str(root/'build/milestone5')
s.custom_model_deployment='BSP'
s.last_build='previous-full.bsp'
original=(s.map_name,s.build_output,s.source_vvis_args,s.last_build)
from unittest.mock import patch
from wavelength.source import launcher
from wavelength.source.build import pipeline
launches=[]
real_popen=ui.subprocess.Popen
def record_launch(command, *args, **kwargs):
    if command[0]=='steam.exe':
        launches.append(command)
        return None
    return real_popen(command,*args,**kwargs)

real_publish=pipeline.publish_bsp
def intercept_preview_copy(source,destination,*args,**kwargs):
    if Path(source).suffix=='.bsp' and Path(destination).parent.name=='maps':
        assert str(source)==s.last_preview_build
        return destination
    return real_publish(source,destination,*args,**kwargs)

with patch.object(launcher,'find_steam',return_value='steam.exe'), patch.object(pipeline,'publish_bsp',side_effect=intercept_preview_copy), patch.object(ui.subprocess,'Popen',side_effect=record_launch):
    assert bpy.ops.wavelength.build(preview=True,play_after_build=True)=={'FINISHED'}
    vvis=next(cmd for name,cmd in zip(ui._JOB.stage_names,ui._JOB.commands) if name=='VVIS')
    assert vvis.count('-fast')==1,vvis
    assert not launches
    while ui._JOB:
        ui.build_tick()
        time.sleep(.05)
assert len(launches)==1 and Path(s.last_preview_build).stem in launches[0]
assert not s.build_error and Path(s.last_preview_build).is_file(),s.build_error
assert Path(s.last_preview_build).stem.endswith('_wl_preview')
assert (s.map_name,s.build_output,s.source_vvis_args,s.last_build)==original
with patch.object(launcher,'find_steam',return_value='steam.exe'), patch.object(pipeline,'publish_bsp') as copy, patch.object(ui.subprocess,'Popen') as launch:
    assert bpy.ops.wavelength.launch(preview=True)=={'FINISHED'}
    assert copy.call_args.args[0]==s.last_preview_build
    assert Path(s.last_preview_build).stem in launch.call_args.args[0]
assert (s.map_name,s.build_output,s.source_vvis_args,s.last_build)==original
print('PASS isolated trainstation preview',s.last_preview_build,flush=True)


# Reuse a verified BSP as the last regular artifact and exercise both terminal
# paths before the queued full rebuild gets a chance to publish.
s.last_build=s.last_preview_build
previous=Path(s.last_build)
previous_bytes=previous.read_bytes()
for terminal in ('CANCELLED','FAILED'):
    assert bpy.ops.wavelength.build(filepath=str(previous))=={'FINISHED'}
    assert s.last_build==str(previous)
    if terminal=='CANCELLED':
        assert bpy.ops.wavelength.cancel_build()=={'FINISHED'}
    else:
        ui._JOB.state='FAILED'
        ui._JOB.message='Simulated compiler failure'
    ui.build_tick()
    assert ui._JOB is None
    assert s.last_build==str(previous) and previous.read_bytes()==previous_bytes

# Play uses the artifact's actual map stem even if authoring settings changed.
s.map_name='Changed name'
with patch.object(launcher,'find_steam',return_value='steam.exe'), patch.object(pipeline,'publish_bsp') as copy, patch.object(ui.subprocess,'Popen') as launch:
    assert bpy.ops.wavelength.launch()=={'FINISHED'}
    assert Path(copy.call_args.args[0])==previous
    assert previous.stem in launch.call_args.args[0]
assert s.map_name=='Changed name'
print('PASS last playable BSP after failed or cancelled rebuild',flush=True)

s.map_name=original[0]

# Simulate a successful VBSP that left a pointfile, as some toolchains do.
assert bpy.ops.wavelength.build(preview=True,play_after_build=True)=={'FINISHED'}
job=ui._JOB
leak_stage=job.stage_names.index('Check for leaks')
assert job.stage_names[leak_stage-1]=='VBSP'
assert job.stage_names[leak_stage+1]=='VVIS'
pointfile=job.directory/(bpy.context.scene['wl_build_pointfile_stem']+'.lin')
pointfile.write_text('0 0 0\n40 0 0\n',encoding='utf-8')
job.index=leak_stage
old_preview=s.last_preview_build
with patch.object(ui.WL_OT_launch,'launch') as launch:
    ui.build_tick()
    launch.assert_not_called()
assert ui._JOB is None and job.index==leak_stage
assert 'VBSP detected a leak' in s.build_error and pointfile.name in s.build_error
assert s.last_preview_build==old_preview and pointfile.is_file()
print('PASS VBSP pointfile blocks VVIS and preview launch',flush=True)

# Retry the failed preview through a new build queue using current scene settings.
previous_work=job.directory
assert bpy.ops.wavelength.build(repeat=True)=={'FINISHED'}
assert ui._JOB_PREVIEW and ui._JOB_PREVIEW_LAUNCH is not None
assert ui._JOB.directory!=previous_work and ui._JOB_OUTPUT is None
assert bpy.ops.wavelength.cancel_build()=={'FINISHED'}
ui.build_tick()
# A regular retry keeps the previously staged destination.
assert bpy.ops.wavelength.build(filepath=str(previous))=={'FINISHED'}
assert bpy.ops.wavelength.cancel_build()=={'FINISHED'}
ui.build_tick()
s.build_output=str(previous.with_name('other.bsp'))
assert bpy.ops.wavelength.build(repeat=True)=={'FINISHED'}
assert not ui._JOB_PREVIEW and ui._JOB_OUTPUT==previous
assert bpy.ops.wavelength.cancel_build()=={'FINISHED'}
ui.build_tick()
print('PASS rebuild repeats mode and output in a fresh staging directory',flush=True)

# Reuse the real compiler output to exercise regular BSP publication under
# a different filename without another full visibility pass.
s.map_name='authoring_name'
destination=previous.with_name(previous.stem.removesuffix('_wl_preview')+'.bsp')
assert bpy.ops.wavelength.build(filepath=str(destination))=={'FINISHED'}
job=ui._JOB
(job.directory/destination.name).write_bytes(previous_bytes)
job.state='DONE'
ui.build_tick()
assert not s.build_error and Path(s.last_build)==destination
assert destination.read_bytes()==previous_bytes and s.map_name=='authoring_name'
print('PASS regular BSP publication preserves authoring map name',flush=True)
