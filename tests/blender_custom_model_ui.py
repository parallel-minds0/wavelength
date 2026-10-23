"""Use the actual operator and native undo in a regular Blender window."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('world=[')[0],__file__,'exec'))
import traceback
ctx.preferences.view.show_splash=False;ctx.workspace['wl_layout_ready']=True
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
steps=[]
def assign():
    original=entity['wl_pairs'];entity['wl_pairs']=json.dumps([['classname','func_door_rotating']])
    try:custom_models.assign(ctx)
    except ValueError as exc:assert 'uses BSP brushes' in str(exc),str(exc)
    else:raise AssertionError('A brush entity must not accept a studio model')
    assert mesh.parent is None and not custom_models.definition(entity)
    entity['wl_pairs']=original
    print('PASS brush door rejection identifies the brush workflow and preserves sources',flush=True)
    ctx.view_layer.objects.active=mesh
    assert custom_models.assignment_target(ctx)==entity
    visual=bpy.data.objects.new('Temporary entity preview',mesh.data.copy());ctx.collection.objects.link(visual)
    visual.parent=entity;visual['wl_model_reference']=True;visual['wl_exclude']=True
    entity.select_set(False);visual.select_set(True);ctx.view_layer.objects.active=visual
    assert custom_models.assignment_target(ctx)==entity
    bpy.ops.ed.undo_push(message='Before custom model assignment')
    with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.assign_custom_model('EXEC_DEFAULT',True)=={'FINISHED'}
    assert custom_models.definition(entity) and mesh.parent==entity
    assert 'Temporary entity preview' not in bpy.data.objects
    assert list(custom_models.definition(entity).objects)==[mesh]
    assert custom_models.WL_PT_custom_model.poll(ctx)
    print('PASS actual custom model assignment operator and contextual panel',flush=True)
steps.append(assign)
def undo():ctx.window.event_simulate(type='Z',value='PRESS',ctrl=True,x=region.x+200,y=region.y+200)
steps.append(undo)
def check():
    source=bpy.data.objects['Editable source']
    assert not source.get('wl_custom_model_owner') and source.parent is None
    assert not any(custom_models.definition(o) for o in ctx.scene.objects)
    print('PASS native undo restores independent source geometry and removes custom binding',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .6 if steps else None
    except Exception:traceback.print_exc();print('FAIL CUSTOM MODEL UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
