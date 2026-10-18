"""Display real-time sun shadows and interactive heading/elevation gizmos."""
import sys,json,time,traceback,math
from pathlib import Path
from mathutils import Euler,Vector
from unittest.mock import patch
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,ui,sun,textures
out=ROOT/'build/sun-ui';out.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(out)
bpy.context.preferences.view.show_splash=False
wavelength.register()
stage=0;target=None;entity=None;start=0
def tick():
    global stage,target,entity,start
    try:
        if stage==0:
            target=workspace.ensure(bpy.context);bpy.context.window.workspace=target;stage=1;return 1
        if stage==1:
            if bpy.context.workspace!=target:bpy.context.window.workspace=target;return 1
            with patch.object(textures,'refresh'):bpy.context.scene.wavelength.engine='source_hl2_windows'
            # Suppress game-asset indexing in this lighting-only test.
            target['wl_texture_catalog']=repr(tuple(getattr(bpy.context.scene.wavelength,k) for k in ('engine','game_dir','wad_path','texture_wads','palette_path')))
            from wavelength.source import external_library
            external_library._key='lighting-test'
            for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
            bpy.ops.mesh.primitive_plane_add(size=12)
            bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,1))
            bpy.context.scene.cursor.location=(0,0,4)
            entity=ui._spawn_point_entity(bpy.context,'light_environment')
            bpy.context.view_layer.update()
            entity.wl_sun.heading=math.radians(135);entity.wl_sun.elevation=math.radians(35)
            bpy.ops.wavelength.sun_preview()
            view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
            view.spaces.active.show_region_ui=False
            view.spaces.active.overlay.show_floor=False
            target['wl_grid']=False
            view.spaces.active.region_3d.view_location=(0,0,1.5)
            view.spaces.active.region_3d.view_distance=13
            view.spaces.active.region_3d.view_rotation=Euler((math.radians(65),0,math.radians(35))).to_quaternion()
            props=next(a for a in bpy.context.screen.areas if a.type=='PROPERTIES');props.spaces.active.context='OBJECT'
            stage=2;return 5
        if stage==2:
            light=sun.light_for(entity)
            assert light.data.type=='SUN' and light.data.energy>0
            assert sun.WL_GGT_sun.poll(bpy.context)
            bpy.ops.screen.screenshot(filepath=str(out/'sun-heading-135.png'))
            entity.wl_sun.heading=math.radians(225)
            entity.wl_sun.elevation=math.radians(55)
            stage=3;return 3
        if stage==3:
            bpy.ops.screen.screenshot(filepath=str(out/'sun-heading-225.png'))
            assert abs(math.degrees(sun.angles(sun.light_for(entity))[1])-55)<.01
            result={'passed':True,'real_light':'SUN','heading':225,'elevation':55,'preview_children':len([c for c in entity.children if c.get('wl_sun_preview')])}
            (out/'result.json').write_text(json.dumps(result));print('PASS SUN UI',result,flush=True)
            wavelength.unregister();bpy.ops.wm.quit_blender();return None
    except Exception:
        (out/'result.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc()}));traceback.print_exc()
        wavelength.unregister();bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(tick,first_interval=2)
