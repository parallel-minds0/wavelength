import sys,math
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import primitive_ui as ui,engine_tools as et,axis_guides,tool_snap,profiles
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE';s.grid_step='16'
c.scene.tool_settings.use_snap=False;c.scene.tool_settings.snap_elements={'VERTEX'}
root=bpy.data.objects.new('Grid scale root',None);c.collection.objects.link(root)
ui.rebuild(root,'CUBE',ui.DEFAULTS,c);root.select_set(True);c.view_layer.objects.active=root;c.view_layer.update()
area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
with c.temp_override(area=area,region=region):
 op=SimpleNamespace(kind='SCALE',axis='X',release_confirm=False)
 class ContextProxy:
  window_manager=SimpleNamespace(modal_handler_add=lambda operator:None)
  def __getattr__(self,name):return getattr(c,name)
 et.WL_OT_engine_transform.invoke(op,ContextProxy(),SimpleNamespace(mouse_x=0,ctrl=True))
 assert op._dimensions.x>0,'Empty parent produced zero scale dimensions'
 s.grid_step='32'
 event=SimpleNamespace(type='MOUSEMOVE',value='NOTHING',mouse_x=53,shift=False,ctrl=True)
 assert et.WL_OT_engine_transform.modal(op,c,event)=={'RUNNING_MODAL'}
 step=profiles.active_grid_step_meters(s)
 size=op._dimensions.x*root.scale.x
 assert abs(size/step-round(size/step))<1e-5,(size,step)
 axis_guides.finish(op,c)
print('PASS procedural-parent scaling uses generated dimensions and updated grid spacing, despite magnet off, Vertex target and Ctrl held',flush=True)


