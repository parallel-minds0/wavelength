"""Profile edge measurements: real edit BMesh, transforms and context gating."""
import sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
import bpy,bmesh
import wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import measurements,grid
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE';s.unit_scale=.0254
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
obj=ctx.object;obj.scale=(.8128,.4064,.2032);obj.rotation_euler=(.2,.4,.1)
with ctx.temp_override(area=area,region=region):
 assert not measurements.enabled(ctx),'Object Mode must never show dimensions'
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');ctx.view_layer.update()
 assert measurements.enabled(ctx)
 segments=list(measurements.edge_segments(ctx));assert len(segments)==12
 lengths=sorted({round((b-a).length/s.unit_scale,3) for a,b,_ in segments})
 assert lengths==[16,32,64],lengths
 assert measurements.format_length(s,.8128)=='32 u'
 s.grid_step='64';assert measurements.format_length(s,.8128)=='32 u'
 s.unit_scale=.01;assert measurements.format_length(s,.32)=='32 u'
 s.grid_mode='BLENDER';assert measurements.format_length(s,.32)=='0.32 m'
 s.grid_mode='ENGINE';s.unit_scale=.0254;s.grid_step='16'
 bm=bmesh.from_edit_mesh(obj.data);edge=next(iter(bm.edges));before=(obj.matrix_world@edge.verts[0].co-obj.matrix_world@edge.verts[1].co).length
 edge.verts[0].co.x+=.5;bmesh.update_edit_mesh(obj.data)
 after=list(measurements.edge_segments(ctx))[0];assert not math.isclose((after[1]-after[0]).length,before),'Live vertex edit not read'
 edge.verts[0].co.x-=.5;bmesh.update_edit_mesh(obj.data)
 area.spaces.active.overlay.show_overlays=False;assert not measurements.enabled(ctx)
 area.spaces.active.overlay.show_overlays=True;s.show_edge_measurements=False;assert not measurements.enabled(ctx)
 s.show_edge_measurements=True;ctx.workspace['wl_workspace']=False;assert not measurements.enabled(ctx)
 ctx.workspace['wl_workspace']=True;ctx.scene.wavelength_context.mode='CLEAN';assert not measurements.enabled(ctx)
 ctx.scene.wavelength_context.mode='EDIT'
 assert measurements.enabled(ctx)
 bpy.ops.mesh.select_all(action='DESELECT');assert not list(measurements.edge_segments(ctx))
 bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.object.mode_set(mode='OBJECT')
 bpy.ops.mesh.primitive_cube_add(size=.25,location=(1,0,0));second=ctx.object
 obj.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
 assert len(list(measurements.edge_segments(ctx)))==24,'Multi-object Edit Mode missed an object'
 bpy.ops.object.mode_set(mode='OBJECT');bpy.data.objects.remove(second,do_unlink=True)
 ctx.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
print('PASS EDIT MEASUREMENTS: world scale, rotation, live edits, profile conversion, grid-step independence, selection, object/workspace/overlay/context gates',flush=True)
if bpy.app.background:
 bpy.ops.object.mode_set(mode='OBJECT');wavelength.unregister();wavelength.register();assert len(grid._handles)==2;wavelength.unregister()
 print('PASS measurement registration cleanup/reload',flush=True)
else:
 obj.rotation_euler=(0,0,0)
 view=area.spaces.active.region_3d;view.view_rotation=Vector((5,-8,5)).to_track_quat('Z','Y');view.view_location=(0,0,0);view.view_distance=3.8;view.view_perspective='PERSP'
 area.spaces.active.shading.type='SOLID';area.spaces.active.overlay.show_floor=False
 OUT=ROOT/'build/edit-measurements';OUT.mkdir(parents=True,exist_ok=True)
 def capture():
  with ctx.temp_override(area=area,region=region):
   labels=list(measurements.label_candidates(ctx));assert labels,'No visible measurement candidates'
   measurements.draw()
  bpy.ops.screen.screenshot(filepath=str(OUT/'edit-measurements.png'))
  print('PASS VISIBLE LABELS '+str([(text) for _,text in labels]),flush=True)
  bpy.ops.wm.quit_blender()
 bpy.app.timers.register(capture,first_interval=3)
