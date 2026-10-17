"""Run with Blender --background --factory-startup --python-exit-code 1 --python."""
import sys,json,tempfile
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import scene,primitives,primitive_ui,identity,editor,asset_browser,workspace,grid
wavelength.register();settings=bpy.context.scene.wavelength;settings.engine='source_hl2_linux'
assert not bpy.app.timers.is_registered(__import__('wavelength.source.transform_sync',fromlist=['tick']).tick)
for kind in ('STAIRS','ARCH','SPHERE'):
 assert bpy.ops.wavelength.primitive(kind=kind)=={'FINISHED'}
 root=bpy.context.object
 assert root['wl_primitive']==kind
 assert bool(root.get('wl_assembly_locked',True)) is True
 children=list(root.children);assert children
 assert all(c.select_get() for c in children) and root.select_get()
 assert all(all(c.lock_location) and all(c.lock_rotation) and all(c.lock_scale) for c in children)
 for obj in children:assert scene.brush_from_object(obj,settings.engine)
 values=json.loads(root['wl_parameters']);values['radius']=160;values['steps']=10
 ids=[o['wl_id'] for o in children]
 primitive_ui.rebuild(root,kind,values,bpy.context)
 assert [o['wl_id'] for o in list(root.children)[:len(ids)]]==ids
 for obj in root.children:assert scene.brush_from_object(obj,settings.engine)
 # Verify rotated primitives remain planar in Blender float32 meshes
 root.rotation_euler=(0.35,-0.25,0.6);bpy.context.view_layer.update()
 for obj in root.children:assert scene.brush_from_object(obj,settings.engine)
 root.rotation_euler=(0.0,0.0,0.0);bpy.context.view_layer.update()
 if kind=='STAIRS':
  assert len(root.children)==10
  # Clicking a single stair step in locked mode expands selection to root + all steps
  for o in bpy.context.selected_objects:o.select_set(False)
  s0=root.children[0];s0.select_set(True);bpy.context.view_layer.objects.active=s0
  primitive_ui.sync_assemblies(force=True)
  assert bpy.context.view_layer.objects.active==root
  assert root.select_get() and all(c.select_get() for c in root.children)
  # Toggle staircase to curved and verify all curved steps are planar BSP brushes
  assert bpy.ops.wavelength.stair_curve_toggle()=={'FINISHED'}
  assert json.loads(root['wl_parameters'])['curved'] is True
  for obj in root.children:assert scene.brush_from_object(obj,settings.engine)
  assert bpy.ops.wavelength.stair_curve_toggle()=={'FINISHED'}
  assert json.loads(root['wl_parameters'])['curved'] is False
 if kind=='ARCH':
  # Clicking a single child wedge in locked mode expands selection to root + all children
  for o in bpy.context.selected_objects:o.select_set(False)
  w0=root.children[0];w0.select_set(True);bpy.context.view_layer.objects.active=w0
  primitive_ui.sync_assemblies(force=True)
  assert bpy.context.view_layer.objects.active==root
  assert root.select_get() and all(c.select_get() for c in root.children)
  # Texture assignment on locked root applies to all child wedges
  settings.texture='tools/toolstrigger'
  assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
  assert all('tools/toolstrigger' in c.data.get('wl_faces','').lower() for c in root.children)
  # Unlocking allows independent child wedge selection and transform
  assert bpy.ops.wavelength.primitive_lock()=={'FINISHED'}
  assert bool(root.get('wl_assembly_locked')) is False
  assert all(not any(c.lock_location) for c in root.children)
  assert bpy.ops.wavelength.primitive_lock()=={'FINISHED'}
  assert bool(root.get('wl_assembly_locked')) is True
 if kind=='SPHERE':
  assert len(root.children)==1
  assert bpy.ops.wavelength.primitive(kind='SPHERE',sphere_type='UV',segments=12,rings=6,radius=96)=={'FINISHED'}
  uv_root=bpy.context.object
  assert len(uv_root.children)==1
  assert scene.brush_from_object(uv_root.children[0],settings.engine)
 obj=root.children[0];original=obj['wl_id'];identity.update_ids();copy=obj.copy();copy.data=obj.data.copy();bpy.context.collection.objects.link(copy);identity.update_ids()
 assert copy['wl_id']!=original and obj['wl_id']==original
 before=[obj.matrix_world@v.co for v in obj.data.vertices];obj.location.x+=.0254*16;bpy.context.view_layer.update()
 after=[obj.matrix_world@v.co for v in obj.data.vertices]
 assert all(abs((b-a).x-.0254*16)<1e-5 for a,b in zip(before,after))
# Verify Make Hollow creates a locked 6-wall assembly
settings.brush_type='CUBE';settings.brush_size=128;settings.hollow_thickness=16
assert bpy.ops.wavelength.add_brush()=={'FINISHED'}
assert bpy.ops.wavelength.make_hollow()=={'FINISHED'}
hollow_root=bpy.context.object
assert hollow_root.get('wl_assembly')=='HOLLOW' and bool(hollow_root.get('wl_assembly_locked')) is True
assert len(primitive_ui.parts_for(hollow_root))==6
assert all(all(w.lock_location) for w in primitive_ui.parts_for(hollow_root))
# Native material assets and reusable previews, no custom gallery required.
mat=bpy.data.materials.new('test native');mat['wl_texture']='dev/test';mat.use_nodes=True
from wavelength.source.asset_index import record
asset_browser.metadata(mat,record(settings.engine,'dev/test','MATERIAL'))
assert mat.asset_data and mat['wl_asset_id']
assert mat.asset_data.catalog_id==asset_browser.TEXTURES_CATALOG_ID
from wavelength.source.entity import browser
assert browser.rebuild(bpy.context)>0
ent_objs=[o for o in bpy.data.objects if o.get('wl_entity_browser_template') and o.asset_data is not None]
assert len({o['wl_entity_browser_template'] for o in ent_objs})>10
assert all(o.asset_data.catalog_id==asset_browser.ENTITIES_CATALOG_ID for o in ent_objs)
# Verify section filter strictly separates Textures vs Entities
class _DummyFilter:
 filter_material=False;filter_object=False;filter_action=True;filter_world=True
class _DummyParams:
 filter_asset_id=_DummyFilter()
browser._apply_section_id_filter(_DummyParams,'TEXTURES')
assert _DummyParams.filter_asset_id.filter_material is True and _DummyParams.filter_asset_id.filter_object is False and _DummyParams.filter_asset_id.filter_action is False
browser._apply_section_id_filter(_DummyParams,'ENTITIES')
assert _DummyParams.filter_asset_id.filter_material is False and _DummyParams.filter_asset_id.filter_object is True
# Verify automatic texture loading on profile/settings selection (e.g. goldsrc_linux)
settings.engine='goldsrc_linux'
if settings.wad_path:
 pub,total,_=asset_browser.sync_status(settings)
 assert total>0 and pub>0
 auto_mats=[m for m in bpy.data.materials if m.get('wl_asset_profile')=='goldsrc_linux' and m.asset_data is not None]
 assert len(auto_mats)>0 and auto_mats[0].preview.image_size[0]==64
 # Realizing an auto-published material populates its full-res shader node tree in-place
 from wavelength.source import textures
 realized=textures.realize_material(settings,auto_mats[0])
 assert realized is auto_mats[0] and realized.get('wl_realized') is True
 assert any(n.type=='TEX_IMAGE' and n.image for n in realized.node_tree.nodes)
# Verify straight and curved stairs are 100% planar and on-grid under engine profiles (including odd grid-step widths)
from wavelength.source import validation,brush_create,profiles,diagnostics
from mathutils import Vector
settings.engine='quake';settings.grid_step='16'
unit=profiles.unit_meters(settings);step_m=16.0*unit
assert bpy.ops.wavelength.primitive(kind='STAIRS',steps=6,rise=16,run=32,width=48,curved=False)=={'FINISHED'}
st_root=bpy.context.object
for part in st_root.children:
 for v in part.data.vertices:
  w=(part.matrix_world@v.co)/unit
  assert all(abs(c-round(c/16.0)*16.0)<1e-4 for c in w),f'Off-grid straight stair vertex: {tuple(w)}'
assert bpy.ops.wavelength.stair_curve_toggle()=={'FINISHED'}
for part in st_root.children:
 assert scene.brush_from_object(part,settings.engine)
 for v in part.data.vertices:
  w=(part.matrix_world@v.co)/unit
  assert all(abs(c-round(c/16.0)*16.0)<1e-4 for c in w),f'Off-grid curved stair vertex: {tuple(w)}'
# Verify interactive viewport stair creation (_stairs_parts) places all vertices on the grid even for odd-step width/length
s_parts=brush_create._stairs_parts(settings,Vector((0,0,0)),Vector((3*step_m,5*step_m,0)),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)),step_m)
for pv,pf in s_parts:
 for v in pv:
  w=v/unit
  assert all(abs(c-round(c/16.0)*16.0)<1e-4 for c in w),f'Off-grid interactive stair vertex: {tuple(w)}'
# Verify Blender profile neither enforces BSP planarity/brush tags nor snaps to grid unless snap_to_grid is enabled
settings.engine='blender';settings.snap_to_grid=False;settings.metric_grid_step=0.5
assert profiles.snap_enabled(settings) is False
assert brush_create._step(bpy.context)==0.0
assert bpy.ops.wavelength.primitive(kind='STAIRS',steps=4,rise=0.17,run=0.29,width=1.13,curved=False)=={'FINISHED'}
bl_stairs=bpy.context.object
assert all(c.get('wl_role')!='BRUSH' for c in bl_stairs.children)
xs=sorted({round((bl_stairs.children[0].matrix_world@v.co).x,4) for v in bl_stairs.children[0].data.vertices})
assert abs((xs[-1]-xs[0])-1.13)<1e-3
# When snap_to_grid is enabled in Blender profile, stairs snap to metric_grid_step
settings.snap_to_grid=True;settings.metric_grid_step=0.25
assert profiles.snap_enabled(settings) is True
assert bpy.ops.wavelength.primitive(kind='STAIRS',steps=4,rise=0.26,run=0.49,width=0.75,curved=False)=={'FINISHED'}
bl_snapped=bpy.context.object
for part in bl_snapped.children:
 for v in part.data.vertices:
  w=part.matrix_world@v.co
  assert all(abs(c-round(c/0.25)*0.25)<1e-4 for c in w),f'Off-grid snapped Blender stair vertex: {tuple(w)}'
# Verify CLI/error log operators
diagnostics.info('Test','CLI log check')
assert diagnostics.counts()[2]>0
assert bpy.ops.wavelength.copy_log()=={'FINISHED'}
assert bpy.ops.wavelength.clear_log()=={'FINISHED'}
# Verify Multi-Object Edit Mode on locked assemblies (Tab / assembly_editmode_toggle)
import bmesh
settings.engine='quake';settings.grid_step='16'
primitive_ui.select_assembly(st_root,bpy.context,True)
assert bpy.ops.wavelength.stair_curve_toggle()=={'FINISHED'}
assert bpy.context.mode=='OBJECT' and bpy.context.view_layer.objects.active==st_root
assert bpy.ops.wavelength.assembly_editmode_toggle()=={'FINISHED'}
assert bpy.context.mode=='EDIT_MESH'
st_parts=primitive_ui.parts_for(st_root)
assert set(bpy.context.objects_in_mode_unique_data)==set(st_parts)
for p in st_parts:
 bm=bmesh.from_edit_mesh(p.data)
 for v in bm.verts:v.select=False
 for f in bm.faces:f.select=False
 bmesh.update_edit_mesh(p.data)
# Apply face texture across multiple child brushes in Multi-Object Edit Mode
bm0=bmesh.from_edit_mesh(st_parts[0].data);bm0.faces.ensure_lookup_table();bm0.faces[0].select=True;bmesh.update_edit_mesh(st_parts[0].data)
bm1=bmesh.from_edit_mesh(st_parts[1].data);bm1.faces.ensure_lookup_table();bm1.faces[0].select=True;bmesh.update_edit_mesh(st_parts[1].data)
settings.texture='CRATE1_5'
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
assert bpy.context.mode=='EDIT_MESH' and set(bpy.context.objects_in_mode_unique_data)==set(st_parts)
# Manipulate individual vertices on two different child steps and snap them to grid in Multi-Object Edit Mode
bm0=bmesh.from_edit_mesh(st_parts[0].data);bm0.verts.ensure_lookup_table()
bm1=bmesh.from_edit_mesh(st_parts[1].data);bm1.verts.ensure_lookup_table()
orig_v0_x=bm0.verts[0].co.x
orig_v1_y=bm1.verts[0].co.y
bm0.verts[0].co.x+=17.3*unit;bm0.verts[0].select=True;bmesh.update_edit_mesh(st_parts[0].data)
bm1.verts[0].co.y+=15.8*unit;bm1.verts[0].select=True;bmesh.update_edit_mesh(st_parts[1].data)
assert bpy.ops.wavelength.snap_grid()=={'FINISHED'}
# Exit Multi-Object Edit Mode back to Object Mode via assembly_editmode_toggle
assert bpy.ops.wavelength.assembly_editmode_toggle()=={'FINISHED'}
assert bpy.context.mode=='OBJECT'
assert bpy.context.view_layer.objects.active==st_root
assert st_root.select_get() and all(p.select_get() for p in st_parts)
assert abs(st_parts[0].data.vertices[0].co.x-(orig_v0_x+16.0*unit))<1e-4
assert abs(st_parts[1].data.vertices[0].co.y-(orig_v1_y+16.0*unit))<1e-4
assert all(p.location.length<1e-6 for p in st_parts)
# Verify brush creation starts at a neutral size regardless of grid_step and supports infinite mouse dragging (GRAB_CURSOR)
assert {'GRAB_CURSOR','BLOCKING'}.issubset(brush_create.WL_OT_cube_brush_create.bl_options)
settings.engine='quake';settings.grid_step='256';settings.brush_type='CUBE';settings.brush_height_steps=1
neutral_q=brush_create._neutral_size(settings)
assert abs(neutral_q-16.0*unit)<1e-6
init_drag_q=brush_create._initial_drag_point(settings,Vector((0,0,0)),Vector((1,0,0)),Vector((0,1,0)))
verts_q,_=brush_create._box_geometry(settings,Vector((0,0,0)),init_drag_q,Vector((0,0,1)),256.0*unit)
assert abs((max(v.x for v in verts_q)-min(v.x for v in verts_q))-16.0*unit)<1e-6
assert abs((max(v.z for v in verts_q)-min(v.z for v in verts_q))-16.0*unit)<1e-6
settings.engine='blender';settings.metric_grid_step=8.0;settings.brush_type='CUBE'
assert abs(brush_create._neutral_size(settings)-1.0)<1e-6
init_drag_b=brush_create._initial_drag_point(settings,Vector((0,0,0)),Vector((1,0,0)),Vector((0,1,0)))
verts_b,_=brush_create._box_geometry(settings,Vector((0,0,0)),init_drag_b,Vector((0,0,1)),8.0)
assert abs((max(v.x for v in verts_b)-min(v.x for v in verts_b))-1.0)<1e-6
assert abs((max(v.z for v in verts_b)-min(v.z for v in verts_b))-1.0)<1e-6
wavelength.unregister();print('PASS FOUNDATION: registration, convex primitives, persistent regeneration, IDs, geometry translation, native material/entity assets, multi-object assembly edit mode, neutral creation size & infinite drag')





