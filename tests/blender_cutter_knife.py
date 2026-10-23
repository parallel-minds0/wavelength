import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Quaternion
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import pencil
bpy.context.preferences.use_preferences_save=False
bpy.context.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/cutter';folder.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(folder)
bpy.context.workspace['wl_workspace']=True;bpy.context.workspace['wl_layout_ready']=True
bpy.context.scene.wavelength.engine='blender'
def test():
    try:
        ctx=bpy.context;area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
        with ctx.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
            def cube(x):
                bpy.ops.mesh.primitive_cube_add(location=(x,0,0));return ctx.object
            target=cube(0);original=target.data
            linked=bpy.data.objects.new('Linked Duplicate',original);ctx.collection.objects.link(linked);linked.location=(5,0,0)
            mat=bpy.data.materials.new('Preserved');target.data.materials.append(mat)
            root=pencil.create_guide(ctx,[pencil.point((-2,0,1)),pencil.point((2,0,1))],(0,0,1),False,target)
            rv=ctx.region_data;rv.view_rotation=Quaternion((.9,.2,.1,.3)).normalized();rv.view_perspective='PERSP';rv.update()
            rotation=rv.view_rotation.copy();perspective=rv.view_perspective
            pencil.apply_cut(ctx,root)
            bpy.ops.object.mode_set(mode='OBJECT')
            assert len(target.data.polygons)>6,(len(target.data.vertices),len(target.data.polygons))
            assert linked.data==original and len(linked.data.polygons)==6
            assert target.data!=original and target.data.materials[0]==mat
            assert target.data.uv_layers and len(target.data.uv_layers[0].data)==len(target.data.loops)
            assert rv.view_perspective==perspective and abs(abs(rv.view_rotation.dot(rotation))-1)<1e-5
            assert not any(o.name.startswith('.Wavelength Cut Projection') for o in ctx.scene.objects)
            print('PASS open native knife cut, linked mesh isolation, material/UV preservation, viewport restoration',flush=True)
            target2=cube(-5)
            root2=pencil.create_guide(ctx,[pencil.point((-5.5,-.5,1)),pencil.point((-4.5,-.5,1)),pencil.point((-4.5,.5,1)),pencil.point((-5.5,.5,1))],(0,0,1),True,target2)
            assert len(target2.data.polygons)==6
            root2.wavelength_cutter.cut_through=True;pencil.apply_cut(ctx,root2);bpy.ops.object.mode_set(mode='OBJECT')
            assert len(target2.data.polygons)>6
            print('PASS closed-loop cut-through; closure itself leaves mesh unchanged',flush=True)
            data=target2.data;counts=(len(data.vertices),len(data.edges),len(data.polygons))
            miss=pencil.create_guide(ctx,[pencil.point((100,0,1)),pencil.point((102,0,1))],(0,0,1),False,target2)
            try:pencil.apply_cut(ctx,miss)
            except (ValueError,RuntimeError):pass
            else:raise AssertionError('Missed cut reported success')
            assert target2.data==data and counts==(len(data.vertices),len(data.edges),len(data.polygons))
            assert ctx.object==miss and ctx.mode=='OBJECT'
            print('PASS failed projection rollback and temporary object cleanup',flush=True)
            bpy.ops.screen.screenshot(filepath=str(folder/'knife-result.png'))
            curved_target=cube(0);curved_target.location.y=5
            a=pencil.point((-2,5,1));b=pencil.point((2,5,1));a['right']=[-1,6,1];b['left']=[1,6,1]
            curved=pencil.create_guide(ctx,[a,b],(0,0,1),False,curved_target)
            pencil.apply_cut(ctx,curved);bpy.ops.object.mode_set(mode='OBJECT')
            assert len(curved_target.data.vertices)>12
            print('PASS curved native knife projection',flush=True)
            edit_target=cube(10);bpy.ops.object.mode_set(mode='EDIT')
            assert pencil.WL_OT_draw_path.poll(ctx)
            edit_guide=pencil.create_guide(ctx,[pencil.point((8,0,1)),pencil.point((12,0,1))],(0,0,1),False,edit_target)
            assert len(edit_target.data.polygons)==6 and ctx.mode=='OBJECT'
            pencil.apply_cut(ctx,edit_guide);bpy.ops.object.mode_set(mode='OBJECT');assert len(edit_target.data.polygons)>6
            print('PASS Edit Mode target and guide-first mesh preservation',flush=True)
        print('PASS CUTTER KNIFE TESTS',flush=True)
    except Exception:traceback.print_exc();print('FAIL CUTTER KNIFE TESTS',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=2)
