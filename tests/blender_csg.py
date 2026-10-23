"""Real node-kernel, BSP/export, lifecycle and failure-preservation checks."""
import sys,traceback,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import csg,scene,pencil
bpy.context.preferences.use_preferences_save=False
ctx=bpy.context;ctx.workspace['wl_workspace']=True

def cube(name,location=(0,0,0),scale=(1,1,1),material=None):
    bpy.ops.mesh.primitive_cube_add(location=location);obj=ctx.object;obj.name=name
    obj.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:obj.data.materials.append(material)
    obj['wl_unit_meters']=1.;return obj

def vol(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);value=abs(bm.calc_volume());bm.free();return value

try:
    ctx.scene.wavelength.engine='blender'
    a=cube('Target');b=cube('Cutter',(.5,0,0));old=a.data
    csg.start(ctx,a,b,'DIFFERENCE');assert a.data==old and len(a.modifiers)==1
    b.location.x=1;ctx.view_layer.update()
    parts=csg.finalize(ctx,a);assert len(parts)==1 and abs(vol(a)-4)<1e-5
    assert not a.modifiers and b.hide_get() and b.get('wl_exclude')
    print('PASS live node movement and free-profile finalization',flush=True)
    a=cube('Cancel target');b=cube('Cancel cutter',(.5,0,0));old=a.data
    csg.start(ctx,a,b,'UNION');csg.cancel(a)
    assert a.data==old and not a.modifiers and b.display_type=='TEXTURED' and not b.hide_render and not b.get('wl_exclude')
    assert not a.get('wl_procedural_state')
    print('PASS cancellation restores operands',flush=True)
    ctx.scene.wavelength.engine='quake'
    material=bpy.data.materials.new('CSG texture');material['wl_texture']='test';material['wl_width']=64;material['wl_height']=64
    for operation,expected in [('DIFFERENCE',24),('UNION',40),('INTERSECT',8)]:
        a=cube('BSP '+operation,scale=(2,2,1),material=material);scene.mark_brush(a)
        b=cube('BSP operand',(1.5,0,0),scale=(1.5,1,2),material=material)
        # Overlap = 2*2*2 = 8; the cutter itself has volume 24.
        expected={'DIFFERENCE':24,'UNION':48,'INTERSECT':8}[operation]
        csg.start(ctx,a,b,operation)
        ctx.scene.wavelength.engine='blender';assert ctx.scene.wavelength.engine=='quake'
        try:scene.export_map(ctx.scene)
        except ValueError as exc:assert 'Finalize' in str(exc)
        else:raise AssertionError('Live CSG was exported')
        parts=csg.finalize(ctx,a)
        assert abs(sum(vol(o) for o in parts)-expected)<1e-4,(operation,len(parts),sum(vol(o) for o in parts))
        for obj in parts:
            assert obj.get('wl_role')=='BRUSH' and obj.get('wl_procedural_state')=='FINALIZED'
            faces=scene.brush_from_object(obj,'quake',True)
            assert all(f.texture=='test' for f in faces)
            assert obj.data.uv_layers
        print('PASS BSP',operation,len(parts),'brushes and export materials/UV',flush=True)
    a=cube('Missed target',material=material);b=cube('Missed cutter',(100,0,0));old=a.data
    csg.start(ctx,a,b,'INTERSECT')
    try:csg.finalize(ctx,a)
    except ValueError:pass
    else:raise AssertionError('Empty result accepted')
    assert a.data==old and a.get('wl_csg') and a.modifiers
    csg.cancel(a)
    print('PASS failed conversion preserves preview and source',flush=True)
    a=cube('Textured target',material=material);scene.mark_brush(a)
    b=cube('Untextured cutter',(.5,0,0))
    csg.start(ctx,a,b,'DIFFERENCE');parts=csg.finalize(ctx,a)
    for obj in parts:assert all(f.texture=='test' for f in scene.brush_from_object(obj,'quake',True))
    print('PASS untextured cutter inherits target material',flush=True)
    a=cube('Saved target',material=material);scene.mark_brush(a);b=cube('Saved cutter',(.5,0,0));old=a.data
    csg.start(ctx,a,b,'DIFFERENCE')
    from wavelength.source import geometry_debug
    assert geometry_debug.inspect(a,ctx.scene) is None
    original=csg.bsp_decompose.decompose
    def limited(v,f,t):return original(v,f,t,max_planes=1)
    csg.bsp_decompose.decompose=limited
    try:
        try:csg.finalize(ctx,a)
        except ValueError as exc:assert 'planes' in str(exc)
        else:raise AssertionError('Complexity limit ignored')
        assert a.data==old and a.get('wl_csg') and a.modifiers
    finally:csg.bsp_decompose.decompose=original
    path=str(Path(__file__).resolve().parents[1]/'build'/'csg-live-test.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    a=bpy.data.objects['Saved target'];b=bpy.data.objects['Saved cutter']
    assert a.get('wl_csg_cutter')==b and b.get('wl_csg_target')==a
    csg.cancel(a);assert not a.modifiers and not b.get('wl_exclude')
    material=bpy.data.materials['CSG texture']
    print('PASS complexity rollback, save/reload and cancellation',flush=True)
    a=cube('Pencil brush',material=material);scene.mark_brush(a)
    guide=pencil.create_guide(ctx,[pencil.point(p) for p in [(-.5,-.5,1),(.5,-.5,1),(.5,.5,1),(-.5,.5,1)]],(0,0,1),True,a)
    guide.wavelength_cutter.operation='SUBTRACT';guide.wavelength_cutter.through=True
    parts=[a]+pencil.apply_cut(ctx,guide)
    assert abs(sum(vol(o) for o in parts)-6)<1e-4
    for obj in parts:scene.brush_from_object(obj,'quake',True)
    print('PASS pencil through-hole decomposes into exportable BSP brushes',flush=True)
    from mathutils import Matrix
    a=cube('Transformed BSP',material=material);scene.mark_brush(a)
    a.location=(23,-11,7);a.rotation_euler=(.2,.3,.4);a.scale=(2,.5,1.5);ctx.view_layer.update()
    b=cube('Transformed cutter',material=material);b.matrix_world=a.matrix_world@Matrix.Diagonal((.5,.5,2,1))
    csg.start(ctx,a,b,'DIFFERENCE');parts=csg.finalize(ctx,a)
    assert abs(sum(vol(o) for o in parts)-6)<1e-4
    for obj in parts:scene.brush_from_object(obj,'quake',True)
    print('PASS rotated, translated and nonuniformly scaled BSP operands',flush=True)
    from wavelength.source import primitive_ui
    roots=[]
    for i in range(2):
        assert bpy.ops.wavelength.primitive(kind='CUBE',width=32,run=32,depth=32)=={'FINISHED'}
        root=primitive_ui.root_for(ctx.object);primitive_ui.finalize(root,ctx);roots.append(root)
    roots[0].location.x+=16*.0254;ctx.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    primitive_ui.select_assembly(roots[0],ctx);primitive_ui.select_assembly(roots[1],ctx)
    assert len(ctx.selected_objects)==4,len(ctx.selected_objects)
    target,cutter=csg.operands(ctx)
    assert target.parent==roots[1] and cutter.parent==roots[0]
    assert bpy.ops.wavelength.csg(operation='DIFFERENCE')=={'FINISHED'}
    ctx.view_layer.objects.active=roots[1]
    assert csg._target(ctx)==target
    assert bpy.ops.wavelength.csg_finish()=={'FINISHED'}
    print('PASS two finalized cube assemblies resolve four selected IDs to two mesh operands',flush=True)
    addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
    assert hasattr(bpy.ops.wavelength,'csg')
    print('PASS CSG registration lifecycle',flush=True)
except Exception:
    traceback.print_exc();print('FAIL CSG',flush=True)
