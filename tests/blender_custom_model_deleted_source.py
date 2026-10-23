"""Native scene deletion must remove retained model sources from export."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('world=[')[0],__file__,'exec'))
col=custom_models.assign(ctx)
for o in ctx.selected_objects:o.select_set(False)
bpy.ops.mesh.primitive_monkey_add();monkey=ctx.object;monkey.name='Deleted Monkey'
mesh.select_set(True);entity.select_set(True);ctx.view_layer.objects.active=entity
custom_models.assign(ctx)
for o in ctx.selected_objects:o.select_set(False)
monkey.select_set(True);ctx.view_layer.objects.active=monkey
bpy.ops.object.delete()
assert 'Deleted Monkey' not in ctx.scene.objects
assert 'Deleted Monkey' in col.objects,'Reproduce retention by the internal collection'
from wavelength.source import model_smd
text=model_smd.export(col,ctx.scene,{None:'default',mat:'color'})['reference.smd']
assert 'object_Deleted Monkey' not in text and 'object_Editable source' in text
job=custom_models.prepare(ctx.scene,folder/'deleted-source')
for command in job.commands:
    result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=60)
    assert result.returncode==0,result.stdout[-3000:]+result.stderr
job.validated()
data=studio_model.load(source_assets.Assets(job.stage),dict(json.loads(entity['wl_pairs']))['model'])
assert len(data['faces'])==12
print('PASS native deletion leaves internal reference but exports/compiles only the surviving scene mesh; deleted Suzanne excluded')
