"""Real node topology, profile parts and native finalization for every primitive."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from dataclasses import replace
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import procedural as p,node_primitives as gn,primitive_ui as ui,primitives,scene
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.scene.tool_settings.use_snap=False
cases=[('ARCH',{}),('ARCH',{'angle':360,'segments':12}),('STAIRS',{'curved':True,'steps':5,'rise':16,'curve_angle':90}),('STAIRS',{'curved':True,'steps':6,'curve_angle':-120,'landing':32,'direction':90}),('SPHERE',{'sphere_type':'ICO'}),('SPHERE',{'sphere_type':'UV'}),('CUBE',{}),('CYLINDER',{}),('CONE',{})]
for owner in ('blender','source_hl2_windows'):
    ctx.scene.wavelength.engine=owner
    for kind,change in cases:
        values={**ui.DEFAULTS,**change}
        root=bpy.data.objects.new('Node '+kind,None);ctx.collection.objects.link(root)
        ui.rebuild(root,kind,values,ctx)
        definition=p.Definition.loads(root['wl_definition']);assert definition.generator==gn.GENERATOR
        parts=ui.parts_for(root);assert parts
        total=0
        for obj in parts:
            assert obj.modifiers and obj.modifiers[0].type=='NODES'
            evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            assert len(mesh.vertices)>0 and mesh.uv_layers
            bm=bmesh.new();bm.from_mesh(mesh)
            assert all(e.is_manifold for e in bm.edges),(owner,kind,change,'non-manifold',len(mesh.vertices),len(mesh.polygons),[(tuple(e.verts[0].co),tuple(e.verts[1].co),len(e.link_faces)) for e in bm.edges if not e.is_manifold][:5])
            total+=abs(bm.calc_volume())/definition.unit_meters**3;bm.free();evaluated.to_mesh_clear()
            if definition.convex_brushes:assert scene.brush_from_object(obj,owner)
        if kind in {'ARCH','STAIRS','SPHERE'}:
            legacy=primitives.generate(kind,values,validate_bsp=definition.convex_brushes,grid_step=definition.grid_step)
            expected=0
            for vertices,faces in legacy:
                data=bpy.data.meshes.new('volume reference');data.from_pydata(vertices,[],faces)
                bm=bmesh.new();bm.from_mesh(data);expected+=abs(bm.calc_volume());bm.free();bpy.data.meshes.remove(data)
            if kind!='STAIRS':assert abs(total-expected)<max(.001,expected*1e-4),(owner,kind,total,expected)
        ui.finalize(root,ctx)
        assert all(not obj.modifiers and obj.data.uv_layers for obj in parts)
        print('PASS node primitive, manifold output, profile export and finalization',owner,kind,change,flush=True)
print('PASS ALL NODE PRIMITIVES',flush=True)
