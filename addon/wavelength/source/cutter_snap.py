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
    def __init__(self,context,target,scene_targets=False,always_geometry=False):
        self.vertices=[];self.edges=[];self.faces=[];self.bvh=None;self.hidden_vertices=set()
        self.always_geometry=always_geometry
        targets=[target] if target else []
        if scene_targets:
            targets=[o for o in context.visible_objects if o.type=='MESH' and not any(o.get(k) for k in ('wl_exclude','wl_cutter_guide','wl_editor_helper','wl_asset_template','wl_entity_browser_template'))]
        for target in targets:
            offset=len(self.vertices)
            if target.mode=='EDIT':
                mesh=bmesh.from_edit_mesh(target.data)
                mesh.verts.index_update()
                self.vertices.extend(target.matrix_world@v.co for v in mesh.verts)
                self.hidden_vertices.update(offset+v.index for v in mesh.verts if v.hide)
                self.edges.extend(tuple(offset+v.index for v in e.verts) for e in mesh.edges if not e.hide)
                self.faces.extend(tuple(offset+v.index for v in p.verts) for p in mesh.faces if not p.hide)
            else:
                evaluated=target.evaluated_get(context.evaluated_depsgraph_get());mesh=evaluated.data
                self.vertices.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
                self.edges.extend(tuple(offset+i for i in e.vertices) for e in mesh.edges)
                self.faces.extend(tuple(offset+i for i in p.vertices) for p in mesh.polygons)
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
        geometry_enabled=self.always_geometry or not getattr(event,'ctrl',False)
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


def creation_targets(context):
    """Short-lived scene snapshot shared by passive brush and pencil hover.

    Use live edit meshes, visible evaluated meshes and world transforms. Hidden
    editor helpers cannot steal a target, and the BVH rejects occluded vertices.
    Modal tools own a snapshot for the duration of their creation operation.
    """
    import time
    key=(context.scene.as_pointer(),context.view_layer.as_pointer(),context.mode)
    now=time.monotonic();entry=_hover_cache.get('creation')
    if not entry or entry[0]!=key or now-entry[1]>.25:
        entry=(key,now,Targets(context,None,scene_targets=True,always_geometry=True))
        _hover_cache['creation']=entry
    return entry[2]


def creation_point(context,value,plane,normal,targets):
    """Snap a proposed brush endpoint without breaking its construction plane.

    Brush dragging uses an offset virtual cursor. Project the actual proposed
    endpoint, rather than the hardware mouse, so snapping doesn't cause a jump.
    """
    xy=view.location_3d_to_region_2d(context.region,context.region_data,value)
    if xy is None:return None
    event=SimpleNamespace(mouse_region_x=xy.x,mouse_region_y=xy.y,ctrl=False)
    return targets.resolve(context,event,plane,normal,plane,lock_plane=True)
def hover_result(context,xy):
    from . import pencil
    if pencil._drawing or not context.region_data:return
    target=pencil.selected_target(context)
    if target is None:return
    # Cache for a short hover burst; rebuild after edits rather than retaining stale geometry.
    # Blender's tool cursor callback supplies window pixels, unlike modal events.
    event=SimpleNamespace(mouse_region_x=xy[0]-context.region.x,mouse_region_y=xy[1]-context.region.y,ctrl=False)
    plane,u,v,n=pencil.target_plane(context,event,target)
    import time
    key=(context.scene.as_pointer(),target.as_pointer(),context.mode)
    now=time.monotonic();entry=_hover_cache.get('cutter')
    if not entry or entry[0]!=key or now-entry[1]>.25:
        entry=(key,now,Targets(context,target,always_geometry=True));_hover_cache['cutter']=entry
    return entry[2].resolve(context,event,plane,n,plane)


def hover(context,tool,xy):
    draw(context,hover_result(context,xy),pixel=True)
