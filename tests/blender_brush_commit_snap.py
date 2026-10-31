"""Brush commits are independent of Live UV; snapping aligns world boundaries."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import editor,tool_snap,profiles
c=bpy.context;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
c.workspace['wl_textures']=False
s=c.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE';s.grid_step='16';s.live_texture_reproject=False
obj=c.object;obj['wl_role']='BRUSH'
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
with c.temp_override(area=a,region=r):
 bpy.ops.object.mode_set(mode='EDIT')
 bm=bmesh.from_edit_mesh(obj.data)
 for v in bm.verts:v.co.x+=.17
 bmesh.update_edit_mesh(obj.data)
 editor._edit_commit_handler(c.scene)
 assert obj.name_full in editor._edit_sessions
 bpy.ops.object.mode_set(mode='OBJECT')
 before=[obj.matrix_world@v.co for v in obj.data.vertices]
 editor._edit_commit_handler(c.scene)
 center=sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
 assert center.length<1e-6,center
 assert all((a-obj.matrix_world@v.co).length<1e-6 for a,v in zip(before,obj.data.vertices))
 # Fractional centered origins are intentional; align boundaries, not centers.
 obj.location=(.137,.183,.219);obj.scale=(.41,.63,.87);c.view_layer.update()
 old=[obj.matrix_world@v.co for v in obj.data.vertices]
 step=profiles.active_grid_step_meters(s)
 bpy.ops.wavelength.snap_grid()
 anchor=tool_snap.move_anchor(obj)
 assert all(abs(x/step-round(x/step))<1e-5 for x in anchor),anchor
 new=[obj.matrix_world@v.co for v in obj.data.vertices];delta=new[0]-old[0]
 assert all((b-a-delta).length<1e-6 for a,b in zip(old,new))
 print('PASS native edits recenter with Live UV disabled; world geometry preserved; profile-boundary snap preserves shape',flush=True)
from wavelength.source.resize_gizmo import _boundary_delta
from mathutils import Matrix
for scale in (1,2,.5):
 matrix=Matrix.Translation((.137,.183,.219))@Matrix.Diagonal((scale,scale,scale,1))
 for axis in range(3):
  anchor=Vector((.11,.23,.37))
  delta=_boundary_delta(matrix,anchor,axis,1,.21,step,True)
  anchor[axis]+=delta
  value=(matrix@anchor)[axis]
  assert abs(value/step-round(value/step))<1e-5,value
print('PASS shaping handles snap world boundaries with translated origins and non-unit object scale',flush=True)
# Exercise the actual handle setter and deferred release commit in Edit Mode.
from types import SimpleNamespace
from wavelength.source import resize_gizmo as resize
class Handle:
 is_modal=False
 def target_set_handler(self,name,get,set):self.setter=set
class Handles:
 def new(self,kind):return Handle()
with c.temp_override(area=a,region=r):
 bpy.ops.object.mode_set(mode='EDIT')
 group=SimpleNamespace(gizmos=Handles())
 resize.WL_GGT_engine_resize.setup(group,c)
 resize.WL_GGT_engine_resize.refresh(group,c)
 handle,state=group._handles[-1]
 handle.is_modal=True
 handle.setter(.3)
 bm=bmesh.from_edit_mesh(obj.data)
 before=[obj.matrix_world@v.co for v in bm.verts]
 assert resize._finish_origins()==.02,'Must wait for release'
 handle.is_modal=False
 assert resize._finish_origins() is None
 assert obj.mode=='EDIT','Must remain in Edit Mode'
 center=sum((v.co for v in bm.verts),Vector())/len(bm.verts)
 assert center.length<1e-6,center
 assert all((p-obj.matrix_world@v.co).length<1e-6 for p,v in zip(before,bm.verts))
 assert not resize._pending_origins
 print('PASS shaping release recenters live BMesh without leaving Edit Mode or moving world geometry',flush=True)
