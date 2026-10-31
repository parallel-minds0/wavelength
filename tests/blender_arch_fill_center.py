import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,wavelength
wavelength.register()
from wavelength.source import primitive_ui as ui,node_primitives as gn,scene
c=bpy.context;c.preferences.use_preferences_save=False;c.scene.tool_settings.use_snap=False
for engine in ('blender','source_hl2_windows'):
 c.scene.wavelength.engine=engine
 for angle in (180,360,90):
  root=bpy.data.objects.new('Fill test',None);c.collection.objects.link(root)
  settings={**ui.DEFAULTS,'fill_center':True,'radius':128.,'thickness':7.,'angle':angle}
  ui.rebuild(root,'ARCH',settings,c)
  volume=0
  for obj in ui.parts_for(root):
   mesh=obj.evaluated_get(c.evaluated_depsgraph_get()).to_mesh()
   bm=bmesh.new();bm.from_mesh(mesh)
   assert all(e.is_manifold for e in bm.edges),(engine,angle,'nonmanifold')
   volume+=abs(bm.calc_volume())/obj.get('wl_unit_meters',1.)**3
   bm.free();obj.evaluated_get(c.evaluated_depsgraph_get()).to_mesh_clear()
   if engine!='blender':assert scene.brush_from_object(obj,engine)
  expected=8*.5*128**2*math.sin(math.radians(angle/8))*64
  assert abs(volume-expected)<expected*1e-4,(engine,angle,volume,expected)
  assert json.loads(root['wl_parameters'])['thickness']==7.
  c.view_layer.objects.active=ui.parts_for(root)[0]
  gn.set_input(c.object.modifiers[0],'Fill Center',False)
  assert ui.sync_arch_inputs(root,c)
  assert json.loads(root['wl_parameters'])['thickness']==7.
  print('PASS Fill Center volume/manifold/export/manual thickness restore',engine,angle,flush=True)
print('PASS ALL FILL CENTER',flush=True)
