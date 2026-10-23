"""Screen-radius geometry targeting and surface-oriented placement cursor."""
from types import SimpleNamespace
from math import sin,cos,tau
import gpu
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils as view
from gpu_extras.batch import batch_for_shader
from . import tool_snap,brush_create

class Targets:
    def __init__(self,context,target):
        self.vertices=[];self.edges=[];self.faces=[];self.bvh=None;self.hidden_vertices=set()
        if target:
            if target.mode=='EDIT':
                mesh=bmesh.from_edit_mesh(target.data)
                mesh.verts.index_update()
                self.vertices=[target.matrix_world@v.co for v in mesh.verts]
                self.hidden_vertices={v.index for v in mesh.verts if v.hide}
                self.edges=[tuple(v.index for v in e.verts) for e in mesh.edges if not e.hide]
                self.faces=[tuple(v.index for v in p.verts) for p in mesh.faces if not p.hide]
            else:
                evaluated=target.evaluated_get(context.evaluated_depsgraph_get());mesh=evaluated.data
                self.vertices=[evaluated.matrix_world@v.co for v in mesh.vertices]
                self.edges=[tuple(e.vertices) for e in mesh.edges];self.faces=[tuple(p.vertices) for p in mesh.polygons]
            if self.faces:self.bvh=BVHTree.FromPolygons(self.vertices,self.faces)
        self.center=sum(self.vertices,Vector())/len(self.vertices) if self.vertices else Vector()
        self.radius=max(((v-self.center).length for v in self.vertices),default=0)+1
        self.key=None;self.screen=[]
    def resolve(self,context,event,plane,normal,anchor,lock_plane=False):
        origin,direction=brush_create._ray(context,event)
        if self.vertices:
            advance=(self.center-origin).dot(direction)-self.radius
            if advance>0:origin+=direction*advance
        hit=self.bvh.ray_cast(origin,direction) if self.bvh and not lock_plane else (None,None,None,None)
        location,up,index,_=hit
        if location is None:location=brush_create._intersect_plane(origin,direction,plane,normal);up=normal
        if location is None:return None
        raw=location.copy();kind='FACE' if index is not None else 'PLANE';highlight=[]
        geometry_enabled=not getattr(event,'ctrl',False)
        if geometry_enabled or tool_snap.grid_enabled(context,event):
            ts=context.scene.tool_settings;elements=set(ts.snap_elements)
            # Knife-style geometry targets coexist with the chosen grid target.
            elements={'VERTEX','EDGE'} if geometry_enabled else set()
            key=(tuple(v for row in context.region_data.perspective_matrix for v in row),context.region.width,context.region.height)
            if key!=self.key:
                self.screen=[view.location_3d_to_region_2d(context.region,context.region_data,v) for v in self.vertices];self.key=key
            mouse=Vector((event.mouse_region_x,event.mouse_region_y));radius=14*context.preferences.system.ui_scale
            # Include boundary vertices/edges just outside the mesh silhouette.
            candidates=[]
            def visible(p):
                if lock_plane and abs((p-plane).dot(normal))>1e-5:return False
                if not self.bvh:return True
                hit=self.bvh.ray_cast(origin,(p-origin).normalized())
                return hit[0] is None or (hit[0]-origin).length>=(p-origin).length-1e-4
            if 'VERTEX' in elements:
                for i,p in enumerate(self.screen):
                    if i not in self.hidden_vertices and p is not None and (p-mouse).length<=radius and visible(self.vertices[i]):candidates.append(((p-mouse).length,self.vertices[i], 'VERTEX',[self.vertices[i]]))
            if not candidates and elements & {'EDGE','EDGE_MIDPOINT'}:
                for a,b in self.edges:
                    pa,pb=self.screen[a],self.screen[b]
                    if pa is None or pb is None:continue
                    delta=pb-pa;t=.5 if 'EDGE_MIDPOINT' in elements and 'EDGE' not in elements else max(0,min(1,(mouse-pa).dot(delta)/max(delta.length_squared,1e-12)))
                    distance=(pa+delta*t-mouse).length
                    if distance>radius:continue
                    # Perspective-correct interpolation along the projected edge.
                    matrix=context.region_data.perspective_matrix
                    wa=(matrix@self.vertices[a].to_4d()).w;wb=(matrix@self.vertices[b].to_4d()).w
                    t=t*wa/max(1e-12,(1-t)*wb+t*wa)
                    p=self.vertices[a].lerp(self.vertices[b],t)
                    if visible(p):candidates.append((distance,p,'EDGE',[self.vertices[a],self.vertices[b]]))
            if candidates:
                _,location,kind,highlight=min(candidates,key=lambda c:(round(c[0],4),(c[1]-origin).length))
            else:
                location=tool_snap.point(context,event,location,anchor)
                location-=up*(location-raw).dot(up)
                if tool_snap.grid_enabled(context,event):kind='GRID'
        return location,up,kind,highlight


def draw(context,result,pixel=False):
    if result is None:return
    co,normal,kind,highlight=result
    project=lambda p:view.location_3d_to_region_2d(context.region,context.region_data,p)
    center=project(co)
    if center is None:return
    # Keep cursor the same apparent size at any zoom level.
    nearby=view.region_2d_to_location_3d(context.region,context.region_data,center+Vector((12,0)),co)
    size=max(1e-6,(nearby-co).length)
    u,v,n=brush_create._axis_basis(normal)
    ring=[co+(u*cos(tau*i/32)+v*sin(tau*i/32))*size for i in range(33)]
    positions=[p for a,b in zip(ring,ring[1:]) for p in (a,b)]+[co-u*size*1.4,co+u*size*1.4,co-v*size*1.4,co+v*size*1.4,co,co+n*size]
    shader=gpu.shader.from_builtin('UNIFORM_COLOR')
    color=(1,.65,.08,1) if kind in {'VERTEX','EDGE'} else (.25,1,.55,1)
    def batch(mode,points):
        if pixel:
            points=[project(p) for p in points]
            if any(p is None for p in points):return
            points=[p+Vector((context.region.x,context.region.y)) for p in points]
        if points:
            shader.bind();shader.uniform_float('color',color);batch_for_shader(shader,mode,{'pos':points}).draw(shader)
    gpu.state.depth_test_set('NONE')
    try:
        batch('LINES',positions)
        if kind=='VERTEX':gpu.state.point_size_set(10);batch('POINTS',highlight)
        elif kind=='EDGE':batch('LINES',highlight)
    finally:gpu.state.point_size_set(1);gpu.state.depth_test_set('NONE' if pixel else 'LESS_EQUAL')

_hover_cache={}
def hover_result(context,xy):
    from . import pencil
    if pencil._drawing or not context.region_data:return
    target=context.object if context.object and context.object.type=='MESH' else None
    if target is None:
        current=pencil.guide(context)
        if current:target=current.wavelength_cutter.target
    key=(target.as_pointer() if target else 0,context.mode)
    # Cache for a short hover burst; rebuild after edits rather than retaining stale geometry.
    import time
    now=time.monotonic();entry=_hover_cache.get('entry')
    if not entry or entry[0]!=key or now-entry[1]>.5:
        if target and target.mode=='EDIT':target.update_from_editmode()
        entry=(key,now,Targets(context,target));_hover_cache['entry']=entry
    # Blender's tool cursor callback supplies window pixels, unlike modal events.
    event=SimpleNamespace(mouse_region_x=xy[0]-context.region.x,mouse_region_y=xy[1]-context.region.y,ctrl=False)
    plane,u,v,n=brush_create._plane_from_mouse(context,event)
    return entry[2].resolve(context,event,plane,n,plane,lock_plane=tool_snap.profile_grid_active(context))


def hover(context,tool,xy):
    draw(context,hover_result(context,xy),pixel=True)
