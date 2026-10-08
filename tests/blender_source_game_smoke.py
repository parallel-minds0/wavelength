"""Opt-in integration against user-installed HL2 and real native compiler tools."""
import bpy,sys,os,time,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ.get('WL_TEST_ADDONS',str(root/'addon')))
import wavelength
from wavelength.source import scene,vmf,source_assets,ui
wavelength.register();s=bpy.context.scene.wavelength;s.engine='source_hl2_linux'
game=Path(os.environ.get('WL_HL2_GAME',str(Path.home()/'.local/share/Steam/steamapps/common/Half-Life 2/hl2')))
tools=Path(os.environ.get('WAVELENGTH_SOURCE_TOOLS',str(root.parent/'bin/source-tools-plusplus/tools++_linux')))
work=Path(os.environ.get('WL_SOURCE_TEST_OUTPUT',str(root.parent/'maps/source1-smoke')));work.mkdir(parents=True,exist_ok=True)
s.game_dir=str(game);s.compiler_dir=str(tools);s.project_dir=str(work);s.source_vrad_args='["-cpu"]'
scene.import_map(bpy.context.scene,vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text()))
brushes=[o for o in bpy.context.scene.objects if o.get('wl_role')=='BRUSH']
for o in bpy.context.selected_objects:o.select_set(False)
for obj in brushes:
    bpy.context.view_layer.objects.active=obj;obj.select_set(True);s.texture='dev/dev_measuregeneric01b'
    assert bpy.ops.wavelength.apply_texture()=={'FINISHED'},s.status
    mat=obj.data.materials[-1];assert mat.get('wl_width')==128,mat.get('wl_width')
    assert any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes)
    obj.select_set(False)
# Exercise the live timer: movement must reproject world-aligned texture UVs.
from wavelength.source import editor
obj=brushes[0];editor._live_tick()
before=[tuple(v.uv) for v in obj.data.uv_layers['wavelength'].data]
obj.location.x+=.0254;bpy.context.view_layer.update();editor._live_tick()
after=[tuple(v.uv) for v in obj.data.uv_layers['wavelength'].data]
assert before!=after,'Live reprojection did not follow object movement'
obj.location.x-=.0254;bpy.context.view_layer.update();editor._live_tick()
entity=next(o for o in bpy.context.scene.objects if o.get('wl_role')=='ENTITY')
bpy.context.view_layer.objects.active=entity;entity.select_set(True)
assert bpy.ops.wavelength.source_output(event='OnUser1',target='!self',input_name='FireUser2')=={'FINISHED'}
assert vmf.OUTPUT+'OnUser1' in dict(json.loads(entity['wl_pairs']))
out=work/'wavelength_source_smoke.bsp'
assert bpy.ops.wavelength.build(filepath=str(out))=={'FINISHED'},s.status
while ui._JOB:ui.build_tick();time.sleep(.03)
assert out.is_file() and not s.build_error,(s.status,s.build_error)
s.grid_mode='ENGINE';s.grid_step='16'
bpy.ops.wm.save_as_mainfile(filepath=str(work/'wavelength_source_smoke.blend'))
print('PASS installed-game VPK/VMT/VTF, real texture dimensions, entity output UI, VBSP/VVIS/VRAD and chosen BSP output',out)
if not bpy.app.background:
    from mathutils import Quaternion
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.show_region_ui=True
            area.spaces.active.shading.type='WIREFRAME'
            area.spaces.active.region_3d.view_rotation=Quaternion((1,0,0,0))
            area.spaces.active.region_3d.view_perspective='ORTHO'
            area.spaces.active.region_3d.view_distance=18
            area.spaces.active.region_3d.view_location=(0,0,1)
    def capture():
        bpy.ops.screen.screenshot(filepath=str(work/'source-ui.png'));bpy.ops.wm.quit_blender()
    bpy.app.timers.register(capture,first_interval=5)
