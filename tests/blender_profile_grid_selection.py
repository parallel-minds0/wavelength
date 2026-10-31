"""Profile selection immediately activates inherited spacing and effective subdivisions."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import profile_ui,profiles,grid
from wavelength.source.profile_store import Store
c=bpy.context;c.preferences.use_preferences_save=False
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
s=c.scene.wavelength
with tempfile.TemporaryDirectory() as folder:
 registry=Store(folder);original=profile_ui.store;profile_ui.store=lambda:registry
 try:
  first=registry.save({'schema':2,'name':'GMod profile','parent':'source_gmod_windows','settings':{'grid_step':'64'}})
  second=registry.save({'schema':2,'name':'GMod finer','parent':first['id'],'settings':{'grid_step':'8','unit_scale':.02}})
  s.engine='blender';s.metric_grid_step=.125
  s.saved_profile=first['id']
  assert s.engine=='source_gmod_windows' and s.profile_id==first['id']
  assert s.grid_mode=='ENGINE' and s.grid_step=='64'
  spacing,count=profiles.display_grid(s)
  assert abs(spacing-profiles.unit_meters(s)*64)<1e-6 and count==8
  assert s.grid_subdivisions==0 and s.effective_grid_subdivisions==8
  grid.sync_native()
  area=next(a for a in c.screen.areas if a.type=='VIEW_3D')
  assert abs(area.spaces.active.overlay.wavelength_grid_spacing-spacing)<1e-6
  s.saved_profile=second['id']
  assert s.profile_id==second['id'] and s.grid_step=='8' and abs(profiles.display_grid(s)[0]-.16)<1e-6
  s.effective_grid_subdivisions=4;assert s.grid_subdivisions==4 and profiles.display_grid(s)[1]==4
  s.saved_profile='blender'
  assert s.engine=='blender' and s.grid_mode=='BLENDER' and s.effective_grid_subdivisions==10
  assert s.metric_grid_step==1
  print('PASS profile picker activates backend, inherited/same-backend grid spacing, native overlay and effective subdivisions; Blender restoration',flush=True)
 finally:profile_ui.store=original
