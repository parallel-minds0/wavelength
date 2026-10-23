"""Persistent quad-surface adjacency, world-space sewing and Source UV sampling."""
import json,math,uuid
from types import SimpleNamespace
import bpy
from bpy.props import BoolProperty
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from . import procedural,profiles,workspace

OFFSET='wavelength.terrain.shared_deformation'


def links(obj):return json.loads(obj.get('wl_terrain_seams','[]'))


def identity(obj):
    if not obj.get('wl_terrain_seam_id'):obj['wl_terrain_seam_id']=str(uuid.uuid4())
    return obj['wl_terrain_seam_id']


def objects():
    found={}
    for obj in bpy.context.scene.objects:
        key=obj.get('wl_terrain_seam_id')
        if not key:continue
        if key in found:raise ValueError('Duplicated sewn terrain identity; unsew the copy before editing/export')
        found[key]=obj
    return found


def network(obj):
    if not links(obj):return [obj]
    found=objects();result=[];pending=[obj];seen=set()
    while pending:
        item=pending.pop()
        if item in seen:continue
        seen.add(item);result.append(item)
        for row in links(item):
            other=found.get(row['other'])
            if other is None:raise ValueError('A sewn displacement is missing; Unsew the remaining surfaces')
            pending.append(other)
    return result


def settings(obj):
    return SimpleNamespace(**procedural.Definition.loads(obj['wl_definition']).parameters) if obj.get('wl_procedural_state')=='FINALIZED' else obj.wavelength_terrain


def quad(obj):
    if obj.get('wl_terrain_face_corners'):
        from . import terrain_face
        terrain_face.validate_attachment(obj);return terrain_face.corners(obj)
    s=settings(obj);unit=obj['wl_unit_meters'];w=s.width*unit/2;h=s.length*unit/2
    return [Vector(p) for p in ((-w,-h,0),(w,-h,0),(w,h,0),(-w,h,0))]


def base_edges(obj):
    q=[obj.matrix_world@p for p in quad(obj)]
    return [(q[i],q[(i+1)%4]) for i in range(4)]


class Surface:
    """Sample evaluated positions/masks by UV, including sideways deformation."""
    def __init__(self,obj):
        from . import terrain_paint
        previous=terrain_paint.full_surface(obj)
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles();uv=mesh.uv_layers.get('UVMap')
            if uv is None:raise ValueError('Sewn displacement needs its original UVMap sampling domain')
            self.points=[v.co.copy() for v in mesh.vertices]
            if any(not math.isfinite(c) for p in self.points for c in p):raise ValueError('Displacement contains non-finite coordinates')
            self.uv=[Vector((*uv.data[i].uv,0)) for i in range(len(mesh.loops))]
            self.tris=[(tuple(t.vertices),tuple(t.loops)) for t in mesh.loop_triangles]
            if not self.tris:raise ValueError('Displacement has no surface')
            self.tree=BVHTree.FromPolygons(self.uv,[loops for _,loops in self.tris],all_triangles=True)
            mask=mesh.attributes.get('wl_terrain_blend');self.mask=[d.value for d in mask.data] if mask else [0.]*len(mesh.vertices)
        finally:evaluated.to_mesh_clear();terrain_paint.restore_surface(obj,previous)
    def sample(self,u,v):
        p=Vector((u,v,0));hit,_,tri,_=self.tree.ray_cast(Vector((u,v,1)),Vector((0,0,-1)))
        if hit is None:
            x=max(1e-6,min(1-1e-6,u+1e-6));y=max(1e-6,min(1-1e-6,v+1e-6))
            hit,_,tri,_=self.tree.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
        if hit is None:raise ValueError('Displacement UV domain has a hole or changed boundary')
        ids,loops=self.tris[tri];a,b,c=(self.uv[i] for i in loops)
        weights=barycentric_transform(p,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        point=sum((self.points[index]*weights[k] for k,index in enumerate(ids)),Vector())
        mask=max(0,min(1,sum(self.mask[index]*weights[k] for k,index in enumerate(ids))))
        return point,mask


def controls(obj):
    rows=[[] for _ in range(4)]
    for v in obj.data.vertices:
        x,y=v.co.x,v.co.y
        if abs(y+.5)<1e-6:rows[0].append((x,v.index))
        if abs(x-.5)<1e-6:rows[1].append((y,v.index))
        if abs(y-.5)<1e-6:rows[2].append((-x,v.index))
        if abs(x+.5)<1e-6:rows[3].append((-y,v.index))
    result=[[index for _,index in sorted(row)] for row in rows]
    if any(len(row)!=65 for row in result):raise ValueError('Sewing needs the intact 65×65 terrain control mesh')
    return result


def offset_group():
    name='Wavelength · Shared Surface Deformation · v1';tree=bpy.data.node_groups.get(name)
    if tree:return tree
    tree=bpy.data.node_groups.new(name,'GeometryNodeTree');tree['wl_generator']=OFFSET
    tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Flat Placement',in_out='INPUT',socket_type='NodeSocketBool')
    inp=tree.nodes.new('NodeGroupInput');out=tree.nodes.new('NodeGroupOutput');attr=tree.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='FLOAT_VECTOR';attr.inputs['Name'].default_value='wl_terrain_vector'
    switch=tree.nodes.new('GeometryNodeSwitch');switch.input_type='VECTOR';tree.links.new(inp.outputs['Flat Placement'],switch.inputs['Switch']);tree.links.new(attr.outputs['Attribute'],switch.inputs['False'])
    offset=tree.nodes.new('GeometryNodeSetPosition');tree.links.new(inp.outputs[0],offset.inputs['Geometry']);tree.links.new(switch.outputs[0],offset.inputs['Offset'])
    target=tree.nodes.new('GeometryNodeInputNamedAttribute');target.data_type='FLOAT_VECTOR';target.inputs['Name'].default_value='wl_terrain_seam_target'
    weight=tree.nodes.new('GeometryNodeInputNamedAttribute');weight.data_type='FLOAT';weight.inputs['Name'].default_value='wl_terrain_seam_weight'
    edge=tree.nodes.new('ShaderNodeMath');edge.operation='GREATER_THAN';tree.links.new(weight.outputs['Attribute'],edge.inputs[0]);edge.inputs[1].default_value=.99999
    preview=tree.nodes.new('GeometryNodeSwitch');preview.input_type='BOOLEAN';tree.links.new(inp.outputs['Flat Placement'],preview.inputs['Switch']);tree.links.new(edge.outputs[0],preview.inputs['False'])
    seam=tree.nodes.new('GeometryNodeSetPosition');tree.links.new(offset.outputs[0],seam.inputs['Geometry']);tree.links.new(preview.outputs[0],seam.inputs['Selection']);tree.links.new(target.outputs['Attribute'],seam.inputs['Position']);tree.links.new(seam.outputs[0],out.inputs[0])
    levels={};rows={}
    def level(n):
        if n.name not in levels:levels[n.name]=max((level(l.from_node)+1 for s in n.inputs for l in s.links),default=0)
        return levels[n.name]
    for n in tree.nodes:
        column=level(n);row=rows.get(column,0);rows[column]=row+1;n.location=(column*220,-row*190)
    return tree


def update_preview(obj):
    from .terrain_paint import input_value
    for m in obj.modifiers:
        if m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==OFFSET:
            socket=next(s for s in m.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name=='Flat Placement')
            input_value(m,socket.identifier,obj.wavelength_terrain.flat_preview,True)


def prepare(obj):
    from . import terrain
    if obj.get('wl_procedural_state')!='PROCEDURAL' or not terrain.paintable(obj):raise ValueError('Sewing and connected painting require unfinalized paintable displacements')
    if obj.data.users!=1:raise ValueError('Make terrain control meshes single-user before sewing')
    obj.data.attributes.get('wl_terrain_vector') or obj.data.attributes.new('wl_terrain_vector','FLOAT_VECTOR','POINT')
    obj.data.attributes.get('wl_terrain_seam_target') or obj.data.attributes.new('wl_terrain_seam_target','FLOAT_VECTOR','POINT')
    obj.data.attributes.get('wl_terrain_seam_weight') or obj.data.attributes.new('wl_terrain_seam_weight','FLOAT','POINT')
    obj['wl_terrain_vector_surface']=True;terrain.update(obj)
    if not any(m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==OFFSET for m in obj.modifiers):
        modifier=obj.modifiers.new('Wavelength · Shared Surface Deformation','NODES');modifier.node_group=offset_group()
    update_preview(obj)


def frames(items):
    result={}
    for obj in items:
        surface=Surface(obj);attr=obj.data.attributes['wl_terrain_vector']
        result[obj]=[surface.sample(v.co.x+.5,v.co.y+.5)[0]-Vector((0,0,v.co.z))-attr.data[v.index].vector for v in obj.data.vertices]
    return result


def positions(obj,base):
    attr=obj.data.attributes['wl_terrain_vector']
    return [obj.matrix_world@(p+Vector((0,0,v.co.z))+attr.data[v.index].vector) for p,v in zip(base,obj.data.vertices)]


def pairs(items):
    found={o.get('wl_terrain_seam_id'):o for o in items};result=[];seen=set()
    for obj in items:
        for row in links(obj):
            other=found.get(row['other'])
            if other is None:raise ValueError('Missing sewn neighbour')
            key=tuple(sorted(((obj.as_pointer(),row['edge']),(other.as_pointer(),row['other_edge']))))
            if key in seen:continue
            seen.add(key);a,b=base_edges(obj)[row['edge']];c,d=base_edges(other)[row['other_edge']]
            if row['reverse']:c,d=d,c
            tolerance=max(obj['wl_unit_meters'],other['wl_unit_meters'])*.05
            if max((a-c).length,(b-d).length)>max(tolerance,1e-5):raise ValueError('Sewn base edges moved apart; move connected surfaces together or Unsew')
            result.append((obj,row['edge'],other,row['other_edge'],row['reverse']))
    return result


def knots(obj,edge):
    d=procedural.Definition.loads(obj['wl_definition'])
    s=settings(obj);count=math.gcd(64,s.resolution-1)
    if not profiles.is_source(d.owner):return count
    return math.gcd(count,(2**int(s.power))*(s.tiles_x if edge%2==0 else s.tiles_y))


def constrain(items,base=None,smooth=False,geometry=True):
    """Union shared corners, then interpolate seams on the common export lattice."""
    base=base or frames(items);edges={o:controls(o) for o in items};world={o:positions(o,base[o]) for o in items};parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    def union(x,y):parent[find(x)]=find(y)
    matched=pairs(items)
    for a,ae,b,be,reverse in matched:
        aa=edges[a][ae];bb=edges[b][be][::-1] if reverse else edges[b][be]
        for i,j in zip(aa,bb):union((a,i),(b,j))
    groups={}
    for item in parent:groups.setdefault(find(item),[]).append(item)
    targets={};mask_targets={}
    materials={next((m for m in o.data.materials if m),None) for o in items};sync_mask=len(materials)==1
    for group in groups.values():
        target=sum((world[o][i] for o,i in group),Vector())/len(group)
        if smooth:
            adjacent=[]
            for o,i in group:
                for e in o.data.edges:
                    if i in e.vertices:
                        j=e.vertices[1] if e.vertices[0]==i else e.vertices[0]
                        if (o,j) not in parent:adjacent.append(world[o][j])
            if adjacent:target=target.lerp(sum(adjacent,Vector())/len(adjacent),.25)
        alpha=sum(o.data.attributes['wl_terrain_blend'].data[i].value for o,i in group)/len(group)
        for item in group:targets[item]=target;mask_targets[item]=alpha
    # All patches retain independent topology. Coarse-knot interpolation makes
    # different Source powers agree even between their sampled edge vertices.
    for a,ae,b,be,reverse in matched:
        aa=edges[a][ae];bb=edges[b][be][::-1] if reverse else edges[b][be];step=64//math.gcd(knots(a,ae),knots(b,be))
        anchors={i:targets[a,aa[i]].copy() for i in range(0,65,step)}
        masks={i:mask_targets[a,aa[i]] for i in range(0,65,step)}
        for i in range(65):
            lo=min(64,(i//step)*step);hi=min(64,lo+step);t=(i-lo)/step
            target=anchors[lo].lerp(anchors[hi],t);targets[a,aa[i]]=target;targets[b,bb[i]]=target
            alpha=masks[lo]*(1-t)+masks[hi]*t;mask_targets[a,aa[i]]=alpha;mask_targets[b,bb[i]]=alpha
    for (obj,index),target in targets.items():
        if geometry:
            attr=obj.data.attributes['wl_terrain_vector'];attr.data[index].vector+=obj.matrix_world.inverted().to_3x3()@(target-world[obj][index])
            obj.data.attributes['wl_terrain_seam_target'].data[index].vector=obj.matrix_world.inverted()@target
            obj.data.attributes['wl_terrain_seam_weight'].data[index].value=1.
        if sync_mask:obj.data.attributes['wl_terrain_blend'].data[index].value=mask_targets[obj,index]
    for obj in items:obj.data.update();obj.update_tag()


def sew(selected,smooth=False):
    from . import terrain
    selected=list(dict.fromkeys(selected))
    if len(selected)<2:raise ValueError('Select at least two paintable displacement surfaces')
    definitions=[procedural.Definition.loads(o['wl_definition']) for o in selected]
    if len({(d.owner,d.owner_profile_id,d.unit_meters) for d in definitions})!=1:raise ValueError('Sewn surfaces must share their owning profile and units')
    for obj in selected:
        if obj.get('wl_procedural_state')!='PROCEDURAL' or not terrain.paintable(obj) or obj.data.users!=1:raise ValueError('Select unfinalized paintable surfaces with single-user control meshes')
        controls(obj)
    edges={o:base_edges(o) for o in selected};matches=[];occupied={};found=objects()
    for obj in selected:
        for row in links(obj):
            other=found.get(row['other'])
            if other is None:raise ValueError('A sewn neighbour is missing; Unsew before sewing again')
            occupied[obj,row['edge']]=(other,row['other_edge'])
    for index,a in enumerate(selected):
        for b in selected[index+1:]:
            tolerance=max(1e-5,a['wl_unit_meters']*.05)
            for ae,(p,q) in enumerate(edges[a]):
                for be,(r,s) in enumerate(edges[b]):
                    for reverse in (False,True):
                        x,y=(s,r) if reverse else (r,s)
                        if max((p-x).length,(q-y).length)<=tolerance:
                            for key in ((a,ae),(b,be)):
                                if key in occupied and occupied[key]!=(b,be) and occupied[key]!=(a,ae):raise ValueError('More than two patches meet along an edge; non-manifold sewing refused')
                            occupied[a,ae]=(b,be);occupied[b,be]=(a,ae);matches.append((a,ae,b,be,reverse));break
    if not matches or any(not any(o in (a,b) for a,_,b,_,_ in matches) for o in selected):raise ValueError('Every selected surface needs a matching full base edge; partial-edge joins are not supported yet')
    # Validate existing connected members before adding links or changing geometry.
    items=list(dict.fromkeys(o for obj in selected for o in network(obj)))
    for obj in items:
        if obj.get('wl_procedural_state')!='PROCEDURAL':raise ValueError('Connected finalized surfaces cannot be resewn or painted')
        if obj.data.users!=1:raise ValueError('Make connected terrain control meshes single-user before sewing')
        if abs(obj.matrix_world.determinant())<1e-12:raise ValueError('Sewn surfaces need nonzero object scale')
        controls(obj)
    pairs(items)
    for obj in items:prepare(obj)
    for a,ae,b,be,reverse in matches:
        for obj,edge,other,other_edge in ((a,ae,b,be),(b,be,a,ae)):
            records=links(obj);row=dict(other=identity(other),edge=edge,other_edge=other_edge,reverse=reverse)
            if row not in records:records.append(row)
            identity(obj);obj['wl_terrain_seams']=json.dumps(records)
    bpy.context.view_layer.update();constrain(items,smooth=smooth)
    return len(matches)


def unsew(selected):
    selected=set(selected);all_objects=list(bpy.context.scene.objects)
    for obj in list(selected):
        for row in links(obj):
            others=[o for o in all_objects if o!=obj and o.get('wl_terrain_seam_id')==row['other']]
            duplicate=any(o!=obj and o.get('wl_terrain_seam_id')==obj.get('wl_terrain_seam_id') for o in all_objects)
            if not duplicate:
                for other in others:other['wl_terrain_seams']=json.dumps([r for r in links(other) if r['other']!=obj.get('wl_terrain_seam_id')])
        obj['wl_terrain_seams']='[]'
        if any(o!=obj and o.get('wl_terrain_seam_id')==obj.get('wl_terrain_seam_id') for o in all_objects):obj['wl_terrain_seam_id']=str(uuid.uuid4())


def patches(obj):
    """Source sampling follows UV topology instead of flattening world geometry."""
    from . import terrain_face
    d=procedural.Definition.loads(obj['wl_definition']);s=settings(obj);surface=Surface(obj);q=quad(obj)
    if not profiles.is_source(d.owner):raise ValueError('Source output requires Source-owned surfaces')
    if obj.get('wl_terrain_face_corners') and (s.tiles_x!=1 or s.tiles_y!=1):raise ValueError('A brush-face displacement must have one patch')
    segments=2**int(s.power);result=[]
    def point(u,v):return q[0]*((1-u)*(1-v))+q[1]*(u*(1-v))+q[2]*(u*v)+q[3]*((1-u)*v)
    for ty in range(s.tiles_y):
        for tx in range(s.tiles_x):
            size=segments+1;vertices=[];alphas=[]
            for j in range(size):
                row=[]
                for i in range(size):
                    p,mask=surface.sample((tx+i/segments)/s.tiles_x,(ty+j/segments)/s.tiles_y);vertices.append(tuple(p));row.append(mask*255)
                alphas.append(row)
            corners=[list(point(u,v)) for u,v in ((tx/s.tiles_x,ty/s.tiles_y),((tx+1)/s.tiles_x,ty/s.tiles_y),((tx+1)/s.tiles_x,(ty+1)/s.tiles_y),(tx/s.tiles_x,(ty+1)/s.tiles_y))]
            faces=[(j*size+i,j*size+i+1,(j+1)*size+i+1,(j+1)*size+i) for j in range(segments) for i in range(segments)]
            result.append((vertices,faces,dict(power=int(s.power),normal=[0,0,1],base_corners=corners,vector_surface=True,alphas=alphas)))
    return result


def validate_export(obj):
    items=network(obj)
    if len(items)==1:return
    surfaces={o:Surface(o) for o in items}
    def uv(edge,t):return ((t,0),(1,t),(1-t,1),(0,1-t))[edge]
    for a,ae,b,be,reverse in pairs(items):
        if a.get('wl_exclude') or b.get('wl_exclude'):raise ValueError('A sewn neighbour is excluded from export; Unsew or include it')
        count=math.gcd(knots(a,ae),knots(b,be));anchors=[a.matrix_world@surfaces[a].sample(*uv(ae,i/count))[0] for i in range(count+1)]
        for i in range(65):
            t=i/64;pa=surfaces[a].sample(*uv(ae,t))[0];pb=surfaces[b].sample(*uv(be,1-t if reverse else t))[0]
            if (a.matrix_world@pa-b.matrix_world@pb).length>max(a['wl_unit_meters']*.01,1e-5):raise ValueError('Sewn surfaces have diverged; select the network and Sew Displacements again')
            x=t*count;lo=int(x);hi=min(count,lo+1)
            if (a.matrix_world@pa-anchors[lo].lerp(anchors[hi],x-lo)).length>max(a['wl_unit_meters']*.01,1e-5):raise ValueError('Source power or display sampling changed; Sew Displacements again before export')


class WL_OT_terrain_sew(bpy.types.Operator):
    bl_idname='wavelength.terrain_sew';bl_label='Sew Displacements';bl_options={'REGISTER','UNDO'}
    bl_description='Sew matching full edges of selected displacement surfaces and keep painting continuous across them'
    smooth:BoolProperty(name='Smooth Seams',default=False,description='Relax shared boundary positions toward adjacent interior rows')
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain')
    def execute(self,context):
        try:
            selected=[o for o in context.selected_objects if o.get('wl_terrain')]
            if self.smooth and len(selected)==1:selected=network(selected[0])
            count=sew(selected,self.smooth)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},f'Sewed {count} shared edges');return {'FINISHED'}


class WL_OT_terrain_unsew(bpy.types.Operator):
    bl_idname='wavelength.terrain_unsew';bl_label='Unsew Displacements';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return WL_OT_terrain_sew.poll(context)
    def execute(self,context):
        try:unsew([o for o in context.selected_objects if o.get('wl_terrain')])
        except ValueError as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


def menu(self,context):
    if WL_OT_terrain_sew.poll(context):self.layout.operator('wavelength.terrain_sew');self.layout.operator('wavelength.terrain_unsew')


def register():
    bpy.utils.register_class(WL_OT_terrain_sew);bpy.utils.register_class(WL_OT_terrain_unsew);bpy.types.VIEW3D_MT_object_context_menu.append(menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu);bpy.utils.unregister_class(WL_OT_terrain_unsew);bpy.utils.unregister_class(WL_OT_terrain_sew)
