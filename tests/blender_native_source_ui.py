"""GPU smoke test for native VPK/VMT/VTF and instanced MDL rendering."""
from pathlib import Path
import json,sys,time,traceback,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import native_source,source_assets,identity
if os.environ.get('WL_NATIVE_PREVIEW_MODE','SOLID')=='SOLID':
    # This smoke check isolates the direct C++ GPU path. Normal map imports now
    # preload Blender rendering datablocks once, even while Solid is selected.
    from wavelength.source import render_support
    if bpy.app.timers.is_registered(render_support.tick):bpy.app.timers.unregister(render_support.tick)
assert native_source.enabled(),'This check requires the native Source asset build'
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True;c.workspace['wl_system_tree_layout_v1']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=os.environ.get('WL_SOURCE_GAME',r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
images=len(bpy.data.images)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1));cube=c.object
cube.data.materials.append(source_assets.material(s,'brick/brickwall001a'))
cube.data.uv_layers.new(name='wavelength',do_init=True)
for i in range(2):
    obj=bpy.data.objects.new('Native barrel '+str(i),None);c.collection.objects.link(obj)
    obj.location=(3,i*2.5,0);obj['wl_role']='ENTITY'
    obj['wl_pairs']=json.dumps([['classname','prop_static'],['model','models/props_c17/oildrum001.mdl']])
    native_source.attach(obj,'models/props_c17/oildrum001.mdl')
    assert len(obj.children)==1 and obj.children[0].type=='EMPTY'
native_source.configure_viewports()
a=next(a for a in c.screen.areas if a.type=='VIEW_3D')
if os.environ.get('WL_NATIVE_PREVIEW_MODE'):a.spaces.active.shading.type=os.environ['WL_NATIVE_PREVIEW_MODE']
if os.environ.get('WL_NATIVE_PREVIEW_MODE')=='RENDERED':
    light=bpy.data.lights.new('Render test sunlight','SUN');light.energy=3
    sun=bpy.data.objects.new('Render test sunlight',light);c.collection.objects.link(sun);sun.rotation_euler=(.4,-.5,-.4)
a.spaces.active.region_3d.view_rotation=Vector((6,-10,6)).to_track_quat('Z','Y')
a.spaces.active.region_3d.view_location=(1.5,1,1)
a.spaces.active.region_3d.view_distance=11
start=time.monotonic();settled=None
def check():
    global settled
    try:
        a.tag_redraw();pending=a.spaces.active.overlay.wavelength_source_assets_pending
        if pending:settled=None
        elif settled is None:settled=time.monotonic()
        if time.monotonic()-start>40:raise AssertionError('Native asset loading timed out')
        if settled is None or time.monotonic()-settled<3:return .1
        assert a.spaces.active.overlay.wavelength_source_assets_failures==0
        mode=os.environ.get('WL_NATIVE_PREVIEW_MODE')
        if mode in {'MATERIAL','RENDERED'}:
            from wavelength.source import render_support
            if render_support._jobs:return .1
            refs=[o for o in c.scene.objects if o.type=='MESH' and o.get('wl_model_reference')]
            assert len(refs)==2 and refs[0].data==refs[1].data,'Render props must share a Blender mesh'
            assert len(bpy.data.images)>images,'Blender material engines need texture Images'
            assert any(n.type=='TEX_IMAGE' and n.image for n in cube.data.materials[0].node_tree.nodes)
        else:
            assert len(bpy.data.images)==images,'Solid native upload created a Blender Image'
            assert len([o for o in c.scene.objects if o.type=='MESH'])==1,'Solid native props created Blender meshes'
        if mode:assert a.spaces.active.shading.type==mode
        output=Path(__file__).resolve().parents[1]/('build/native-source-assets-'+mode.lower()+'.png' if mode else 'build/native-source-assets.png')
        output.parent.mkdir(exist_ok=True);bpy.ops.screen.screenshot(filepath=str(output))
        print('PASS Source shading:',mode or 'SOLID','native Solid / shared Blender material-render assets',flush=True)
        bpy.ops.wm.quit_blender()
    except Exception:
        traceback.print_exc();print('FAIL native Source GPU',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=2)
