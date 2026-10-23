"""Profile-grid placement: absolute origin, fixed depth, free-profile opt out."""
import sys,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import tool_snap,brush_create,cutter_snap,profiles
ctx=bpy.context;ctx.preferences.use_preferences_save=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='PERSP'
def check():
    try:
        with ctx.temp_override(area=area,region=region):
            st=ctx.scene.wavelength;ts=ctx.scene.tool_settings;st.engine='source_hl2_windows';st.grid_mode='ENGINE';st.grid_step='16'
            ts.use_snap=True;ts.snap_elements={'INCREMENT'};ts.use_snap_grid_absolute=False
            event=SimpleNamespace(ctrl=False,mouse_region_x=region.width*.5,mouse_region_y=region.height*.5)
            spacing=profiles.active_grid_step_meters(st);anchor=Vector((.13,.17,.23));value=Vector((.59,.72,.23))
            result=tool_snap.point(ctx,event,value,anchor)
            assert all(abs(c/spacing-round(c/spacing))<1e-5 for c in result),(spacing,result)
            # Occluding/other-depth geometry must not move an established stroke.
            cache=cutter_snap.Targets(ctx,ctx.object);plane=Vector((0,0,3));normal=Vector((0,0,1))
            with patch.object(brush_create,'_ray',return_value=(Vector((.19,.27,10)),Vector((0,0,-1)))):
                result=cache.resolve(ctx,event,plane,normal,anchor,lock_plane=True)
                assert abs(result[0].z-3)<1e-6,result
                unlocked=cache.resolve(ctx,event,plane,normal,anchor)
                assert abs(unlocked[0].z-1)<1e-6,unlocked
            # Empty-space plane axis follows the view, even at perspective edges.
            empty=cutter_snap.Targets(ctx,None)
            for ray in (Vector((.95,0,-.2)).normalized(),Vector((0,.95,-.2)).normalized()):
                with patch.object(brush_create,'_ray',return_value=(Vector((30,30,10)),ray)):
                    p,u,v,n=brush_create._plane_from_mouse(ctx,event)
                    assert p.length==0 and abs(n.z)==1,(p,n)
            ts.use_snap=False;assert tool_snap.point(ctx,event,value,anchor)==value
            ts.use_snap=True;st.grid_mode='BLENDER';assert not tool_snap.profile_grid_active(ctx)
            result=tool_snap.point(ctx,event,value,anchor)
            assert (result-anchor).length<1e-5 or result!=Vector((round(value.x/spacing)*spacing,round(value.y/spacing)*spacing,round(value.z/spacing)*spacing))
            st.engine='blender';assert not tool_snap.profile_grid_active(ctx)
            profiles.PROFILES['source_hl2_windows']['brush_semantics']=False
            st.engine='source_hl2_windows';st.grid_mode='ENGINE'
            assert tool_snap.profile_grid_active(ctx), 'Grid capability must not require BSP brush semantics'
            profiles.PROFILES['source_hl2_windows']['brush_semantics']=True
            print('PASS profile-grid absolute origin, locked depth, stable empty-space plane, snap toggle and metric/free opt out',flush=True)
    except Exception:traceback.print_exc();print('FAIL PROFILE DRAW GRID',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1)
