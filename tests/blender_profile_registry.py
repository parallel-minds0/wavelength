import sys,traceback,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import profile_ui,profiles
from wavelength.source.profile_store import Store
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
temporary=tempfile.TemporaryDirectory();registry=Store(temporary.name);original=profile_ui.store;profile_ui.store=lambda:registry
try:
    s=ctx.scene.wavelength;s.engine='godot4';s.profile_name='Parent project';s.grid_step='32'
    bpy.ops.mesh.primitive_cube_add();obj=ctx.object;data=obj.data;matrix=obj.matrix_world.copy()
    parent=registry.save(profile_ui.snapshot(ctx,'Parent',parent='godot4'))
    profile_ui.apply(ctx,parent)
    assert s.profile_id==parent['id'] and s.saved_profile==parent['id'] and s.engine=='godot4'
    child=registry.save({'schema':2,'name':'Child','parent':parent['id'],'settings':{'metric_grid_step':.25}})
    s.game_dir='must not leak';profile_ui.apply(ctx,child)
    assert s.game_dir=='' and s.metric_grid_step==.25 and s.grid_step=='32'
    assert obj.data==data and obj.matrix_world==matrix
    # Rename and remove are registry operations, never object deletion.
    s.saved_profile=child['id']
    assert bpy.ops.wavelength.profile(action='RENAME',name='Renamed')=={'FINISHED'}
    assert registry.get(child['id'])['name']=='Renamed'
    assert bpy.ops.wavelength.profile(action='REMOVE')=={'FINISHED'}
    assert obj.name in ctx.scene.objects and s.engine=='godot4'
    profile_ui.apply(ctx,registry.get('godot4'))
    assert s.profile_id=='godot4' and s.game_dir==''
    try:registry.remove('godot4')
    except ValueError:pass
    else:raise AssertionError('Builtin removed')
    assert 'source' in [item[0] for item in profile_ui.parents(None,ctx)]
    assert 'godot4' in [item[0] for item in profile_ui.items(None,ctx)]
    assert parent['id'] in [item[0] for item in profile_ui.items(None,ctx)]
    # Invalid field types cannot leave the scene halfway through a load.
    before=(s.engine,s.metric_grid_step,s.game_dir,s.profile_id)
    invalid=dict(parent,settings={**parent['settings'],'metric_grid_step':'invalid'})
    try:profile_ui.apply(ctx,invalid)
    except (TypeError,ValueError):pass
    else:raise AssertionError('Invalid field type accepted')
    assert (s.engine,s.metric_grid_step,s.game_dir,s.profile_id)==before
    path=str(Path(temporary.name)/'project.json')
    s.auto_prepare_assets=False;s.mesh_export_selected=True
    assert bpy.ops.wavelength.save_project(filepath=path)=={'FINISHED'}
    s.auto_prepare_assets=True;s.mesh_export_selected=False
    assert bpy.ops.wavelength.load_project(filepath=path)=={'FINISHED'}
    assert not s.auto_prepare_assets and s.mesh_export_selected
    profile_ui.apply(ctx,registry.get('source_windows'))
    assert s.engine=='source_windows' and s.game_dir=='' and not profiles.get(s.engine)['build_supported']
    print('PASS registered profiles: inherited settings, same-backend reset, protected templates, rename/remove and unchanged geometry',flush=True)
    addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
    print('PASS registry lifecycle',flush=True)
except Exception:traceback.print_exc();print('FAIL REGISTRY',flush=True)
finally:profile_ui.store=original;temporary.cleanup()
