"""Versioned straight-stair Geometry Nodes assets. Python builds graphs, not vertices."""
import bpy
from . import procedural
GENERATOR='wavelength.geometry_nodes.straight_stairs'
VERSION=1


def group():
    name='Wavelength · Straight Stairs · v1'
    existing=bpy.data.node_groups.get(name)
    if existing:
        if existing.get('wl_generator')!=GENERATOR:raise ValueError('Conflicting stair node group')
        return existing
    tree=bpy.data.node_groups.new(name,'GeometryNodeTree');tree['wl_generator']=GENERATOR;tree['wl_generator_version']=VERSION
    for name,typ,value in [('Steps','NodeSocketInt',8),('Rise','NodeSocketFloat',16.),('Run','NodeSocketFloat',32.),('Width','NodeSocketFloat',128.),('Landing','NodeSocketFloat',0.),('Units','NodeSocketFloat',1.),('Direction','NodeSocketFloat',0.),('Offset X','NodeSocketFloat',0.),('Brush Part','NodeSocketBool',False),('Part Index','NodeSocketInt',0)]:
        socket=tree.interface.new_socket(name=name,in_out='INPUT',socket_type=typ);socket.default_value=value
    tree.interface.new_socket(name='Material',in_out='INPUT',socket_type='NodeSocketMaterial')
    tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes=tree.nodes;links=tree.links
    def node(kind,label):
        n=nodes.new(kind);n.label=label;return n
    inp=node('NodeGroupInput','Profile-owned stair parameters');out=node('NodeGroupOutput','Generated stair mesh')
    def wire(value,socket):
        if isinstance(value,(int,float,bool)):socket.default_value=value
        else:links.new(value,socket)
    def math(op,a,b=0):
        n=node('ShaderNodeMath',op);n.operation=op;wire(a,n.inputs[0]);wire(b,n.inputs[1]);return n.outputs[0]
    def vector(x=0,y=0,z=0):
        n=node('ShaderNodeCombineXYZ','Dimensions / placement');wire(x,n.inputs['X']);wire(y,n.inputs['Y']);wire(z,n.inputs['Z']);return n.outputs[0]
    def transform(geometry,translation=None,scale=None,rotation=None):
        n=node('GeometryNodeTransform','Place generated geometry');links.new(geometry,n.inputs['Geometry'])
        for value,key in [(translation,'Translation'),(scale,'Scale'),(rotation,'Rotation')]:
            if value is not None:links.new(value,n.inputs[key])
        return n.outputs['Geometry']
    def cube_uv(cube):
        store=node('GeometryNodeStoreNamedAttribute','Generated UV map');store.data_type='FLOAT2';store.domain='CORNER';store.inputs['Name'].default_value='UVMap'
        links.new(cube.outputs['Mesh'],store.inputs['Geometry']);links.new(cube.outputs['UV Map'],store.inputs['Value']);return store.outputs['Geometry']
    steps=inp.outputs['Steps'];rise=inp.outputs['Rise'];run=inp.outputs['Run'];width=inp.outputs['Width'];landing=inp.outputs['Landing']
    cube=node('GeometryNodeMeshCube','Unit step box');links.new(vector(width,run,rise),cube.inputs['Size'])
    line=node('GeometryNodeMeshLine','One point per step');links.new(steps,line.inputs['Count'])
    index=node('GeometryNodeInputIndex','Step index').outputs['Index']
    setpos=node('GeometryNodeSetPosition','Step centers');links.new(line.outputs['Mesh'],setpos.inputs['Geometry'])
    links.new(vector(inp.outputs['Offset X'],math('MULTIPLY',math('ADD',index,.5),run),math('MULTIPLY',math('MULTIPLY',math('ADD',index,1),rise),.5)),setpos.inputs['Position'])
    instances=node('GeometryNodeInstanceOnPoints','Generate step solids');links.new(setpos.outputs['Geometry'],instances.inputs['Points']);links.new(cube_uv(cube),instances.inputs['Instance']);links.new(vector(1,1,math('ADD',index,1)),instances.inputs['Scale'])
    landingcube=node('GeometryNodeMeshCube','Landing');links.new(vector(width,landing,math('MULTIPLY',steps,rise)),landingcube.inputs['Size'])
    landinggeo=transform(cube_uv(landingcube),vector(inp.outputs['Offset X'],math('ADD',math('MULTIPLY',steps,run),math('MULTIPLY',landing,.5)),math('MULTIPLY',math('MULTIPLY',steps,rise),.5)))
    selectlanding=node('GeometryNodeSwitch','Optional landing');selectlanding.input_type='GEOMETRY';links.new(math('GREATER_THAN',landing,0),selectlanding.inputs['Switch']);links.new(landinggeo,selectlanding.inputs['True'])
    join=node('GeometryNodeJoinGeometry','Steps and landing');links.new(instances.outputs['Instances'],join.inputs['Geometry']);links.new(selectlanding.outputs[0],join.inputs['Geometry'])
    realize=node('GeometryNodeRealizeInstances','Realize step solids');links.new(join.outputs[0],realize.inputs['Geometry'])
    union=node('GeometryNodeMeshBoolean','Connected mesh profile output');union.operation='UNION';union.solver='EXACT';union.inputs['Self Intersection'].default_value=True;links.new(realize.outputs[0],union.inputs['Mesh 2'])
    # A BSP adapter evaluates one independently identifiable convex box per part.
    part=inp.outputs['Part Index'];islanding=math('GREATER_THAN',part,math('SUBTRACT',steps,1))
    depth=node('GeometryNodeSwitch','Part run');depth.input_type='FLOAT';links.new(islanding,depth.inputs['Switch']);links.new(run,depth.inputs['False']);links.new(landing,depth.inputs['True'])
    level=math('MINIMUM',math('ADD',part,1),steps)
    partcube=node('GeometryNodeMeshCube','Convex brush part');links.new(vector(width,depth.outputs[0],math('MULTIPLY',level,rise)),partcube.inputs['Size'])
    partgeo=transform(cube_uv(partcube),vector(inp.outputs['Offset X'],math('ADD',math('MULTIPLY',part,run),math('MULTIPLY',depth.outputs[0],.5)),math('MULTIPLY',math('MULTIPLY',level,rise),.5)))
    choose=node('GeometryNodeSwitch','Profile output adapter');choose.input_type='GEOMETRY';links.new(inp.outputs['Brush Part'],choose.inputs['Switch']);links.new(union.outputs[0],choose.inputs['False']);links.new(partgeo,choose.inputs['True'])
    geometry=transform(choose.outputs[0],scale=vector(inp.outputs['Units'],inp.outputs['Units'],inp.outputs['Units']),rotation=vector(0,0,math('MULTIPLY',inp.outputs['Direction'],.017453292519943295)))
    material=node('GeometryNodeSetMaterial','Stair material');links.new(geometry,material.inputs['Geometry']);links.new(inp.outputs['Material'],material.inputs['Material']);geometry=material.outputs['Geometry']
    attr=node('GeometryNodeStoreNamedAttribute','Stable face identity');attr.data_type='INT';attr.domain='FACE';attr.inputs['Name'].default_value='wl_face_id';links.new(geometry,attr.inputs['Geometry']);links.new(math('ADD',index,1),attr.inputs['Value'])
    part_id=node('GeometryNodeStoreNamedAttribute','Stable BSP part identity');part_id.data_type='INT';part_id.domain='FACE';part_id.inputs['Name'].default_value='wl_brush_part'
    links.new(attr.outputs['Geometry'],part_id.inputs['Geometry']);links.new(inp.outputs['Part Index'],part_id.inputs['Value']);links.new(part_id.outputs['Geometry'],out.inputs['Geometry'])
    levels={}
    def level(n):
        if n.name not in levels:levels[n.name]=max((level(link.from_node)+1 for socket in n.inputs for link in socket.links),default=0)
        return levels[n.name]
    rows={}
    for n in nodes:
        column=level(n);row=rows.get(column,0);rows[column]=row+1;n.location=(column*240,-row*220)
    return tree


def parameters(definition):
    p=dict(definition.parameters)
    if p.get('curved'):raise ValueError('Straight stair nodes do not support curved stairs yet')
    for key in ['rise','run','width','landing']:
        value=float(p[key]);g=definition.grid_step or 0
        if g>0 and value>0:value=max(g,round(value/g)*g)
        p[key]=value
    if not 1<=int(p['steps'])<=64 or min(p['rise'],p['run'],p['width'])<(1 if definition.convex_brushes else .001) or p['landing']<0:raise ValueError('Invalid stair dimensions')
    return p


def attach(obj,definition,index=0):
    p=parameters(definition);modifier=obj.modifiers.new('Wavelength · Stair Generator','NODES');modifier.node_group=group()
    values={'Steps':int(p['steps']),'Rise':p['rise'],'Run':p['run'],'Width':p['width'],'Landing':p['landing'],'Units':definition.unit_meters,'Direction':p.get('direction',0),'Brush Part':definition.convex_brushes,'Part Index':index,'Offset X':p['width']/2-round((p['width']/2)/definition.grid_step)*definition.grid_step if definition.convex_brushes and definition.grid_step else 0.,'Material':obj.data.materials[0] if obj.data.materials else None}
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type=='SOCKET' and socket.in_out=='INPUT':
            if hasattr(modifier,'properties'):getattr(modifier.properties.inputs,socket.identifier).value=values[socket.name]
            else:modifier[socket.identifier]=values[socket.name]
    return modifier


def evaluate(definition):
    p=parameters(definition);count=int(p['steps'])+(p['landing']>0) if definition.convex_brushes else 1
    result=[]
    for index in range(count):
        data=bpy.data.meshes.new('.Stair evaluation');obj=bpy.data.objects.new('.Stair evaluation',data);bpy.context.scene.collection.objects.link(obj)
        try:
            attach(obj,definition,index);bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            try:result.append(([tuple(c/definition.unit_meters for c in v.co) for v in mesh.vertices],[tuple(f.vertices) for f in mesh.polygons]))
            finally:evaluated.to_mesh_clear()
        finally:bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
    return result
