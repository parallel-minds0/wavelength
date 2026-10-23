import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import procedural as p,node_stairs as gn,primitive_ui as ui,scene
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.scene.tool_settings.use_snap=False
for owner in ['blender','source_hl2_windows']:
    ctx.scene.wavelength.engine=owner
    for landing in [0,32]:
        root=bpy.data.objects.new('Node stairs',None);ctx.collection.objects.link(root)
        values={**ui.DEFAULTS,'landing':landing}
        ui.rebuild(root,'STAIRS',values,ctx)
        d=p.Definition.loads(root['wl_definition']);assert d.generator==gn.GENERATOR
        parts=ui.parts_for(root);assert len(parts)==(8+(landing>0) if d.convex_brushes else 1)
        meshes=p.validate(d,p.evaluate(d))
        total=0
        for obj in parts:
            assert len(obj.modifiers)==1 and obj.modifiers[0].type=='NODES'
            evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            bm=bmesh.new();bm.from_mesh(mesh)
            assert mesh.uv_layers and len(mesh.uv_layers[0].data)==len(mesh.loops)
            assert all(e.is_manifold for e in bm.edges),(owner,landing,len(mesh.vertices),len(mesh.polygons))
            total+=abs(bm.calc_volume())/d.unit_meters**3
            bm.free();evaluated.to_mesh_clear()
        expected=128*32*16*sum(range(1,9))+128*landing*128
        assert abs(total-expected)<expected*1e-5,(owner,landing,total,expected)
        if d.convex_brushes:
            assert all(len(scene.brush_from_object(obj,owner))==6 for obj in parts)
        material=bpy.data.materials.new('Node test material');material['wl_texture']='test/material'
        for obj in parts:obj.data.materials.append(material)
        ui.rebuild(root,'STAIRS',{**values,'steps':4},ctx)
        parts=ui.parts_for(root)
        assert len(parts)==(4+(landing>0) if d.convex_brushes else 1)
        ui.finalize(root,ctx);assert all(not obj.modifiers and obj.data.uv_layers and material in obj.data.materials[:] for obj in parts)
        print('PASS node generation, profile geometry, volume, finalization',owner,landing,flush=True)
print('PASS NODE STAIRS',flush=True)

# Legacy identity stays Python; no automatic migration of existing stairs.
ctx.scene.wavelength.engine='blender'
legacy=bpy.data.objects.new('Legacy stairs',None);ctx.collection.objects.link(legacy)
legacy['wl_primitive']='STAIRS';legacy['wl_parameters']='{}'
ui.rebuild(legacy,'STAIRS',ui.DEFAULTS,ctx)
assert p.Definition.loads(legacy['wl_definition']).generator==p.PYTHON_GENERATOR
assert not ui.parts_for(legacy)[0].modifiers
print('PASS legacy generator preserved',flush=True)

root=bpy.data.objects.new('Live node evaluation',None);ctx.collection.objects.link(root)
ui.rebuild(root,'STAIRS',ui.DEFAULTS,ctx);obj=ui.parts_for(root)[0];modifier=obj.modifiers[0]
identifier=next(s.identifier for s in modifier.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name=='Rise')
base=obj.data;original_vertex=base.vertices[0].co.copy()
getattr(modifier.properties.inputs,identifier).value=32
ctx.view_layer.update();evaluated=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
bm=bmesh.new();bm.from_mesh(mesh);assert abs(abs(bm.calc_volume())-128*32*32*36)<1e-4;bm.free();evaluated.to_mesh_clear()
assert obj.data==base and obj.data.vertices[0].co==original_vertex
print('PASS live node input changes geometry without Python mesh regeneration',flush=True)

bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
ctx.workspace['wl_workspace']=True
for _ in range(4):ui.sync_assemblies(force=True)
assert ctx.view_layer.objects.active==obj and obj.select_get()
assert all(part.select_get() for part in ui.parts_for(root))
ctx.workspace['wl_workspace']=False
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj
old_background=bpy.app.background
# force=False intentionally skips all selection work in background; a GUI regression
# below checks the workspace-specific behavior as well.
ui.sync_assemblies()
assert ctx.view_layer.objects.active==obj
print('PASS node mesh remains active across assembly synchronization',flush=True)
