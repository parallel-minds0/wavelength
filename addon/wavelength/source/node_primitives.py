"""Versioned parametric Geometry Nodes generators; Python never builds shape vertices.

Node graphs own mesh construction. This adapter validates scalar parameters,
selects profile output parts and evaluates/attaches graphs at Blender boundaries.
"""
import math
import bpy

GENERATOR='wavelength.geometry_nodes.primitives'
VERSION=1
KINDS={'ARCH','STAIRS','SPHERE','CUBE','CYLINDER','CONE'}

class Graph:
    """Small graph-building vocabulary shared by shape and pencil assets."""
    def __init__(self,name,generator,inputs):
        self.tree=bpy.data.node_groups.new(name,'GeometryNodeTree')
        self.tree['wl_generator']=generator;self.tree['wl_generator_version']=VERSION
        for name,kind,value in inputs:
            socket=self.tree.interface.new_socket(name=name,in_out='INPUT',socket_type=kind)
            if value is not None:socket.default_value=value
        self.tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        self.input=self.node('NodeGroupInput','Parameters')
        self.output=self.node('NodeGroupOutput','Evaluated geometry')
    def node(self,kind,label):
        node=self.tree.nodes.new(kind);node.label=label;return node
    def wire(self,value,socket):
        if hasattr(value,'node'):self.tree.links.new(value,socket)
        else:socket.default_value=value
    def math(self,op,a,b=0):
        node=self.node('ShaderNodeMath',op);node.operation=op
        self.wire(a,node.inputs[0]);self.wire(b,node.inputs[1]);return node.outputs[0]
    def vector(self,x=0,y=0,z=0):
        node=self.node('ShaderNodeCombineXYZ','Coordinates')
        for value,key in zip((x,y,z),'XYZ'):self.wire(value,node.inputs[key])
        return node.outputs[0]
    def split(self,value):
        node=self.node('ShaderNodeSeparateXYZ','Coordinates');self.wire(value,node.inputs[0]);return node.outputs
    def choose(self,test,a,b,kind='FLOAT'):
        node=self.node('GeometryNodeSwitch','Conditional');node.input_type=kind
        for value,key in ((test,'Switch'),(a,'True'),(b,'False')):self.wire(value,node.inputs[key])
        return node.outputs[0]
    def store(self,geometry,name,value,kind='INT',domain='FACE'):
        node=self.node('GeometryNodeStoreNamedAttribute',name);node.data_type=kind;node.domain=domain
        self.wire(geometry,node.inputs['Geometry']);node.inputs['Name'].default_value=name
        self.wire(value,node.inputs['Value']);return node.outputs['Geometry']
    def transform(self,geometry,translation=(0,0,0),rotation=(0,0,0),scale=(1,1,1)):
        node=self.node('GeometryNodeTransform','Placement / profile units')
        for value,key in ((geometry,'Geometry'),(translation,'Translation'),(rotation,'Rotation'),(scale,'Scale')):self.wire(value,node.inputs[key])
        return node.outputs['Geometry']
    def finish(self,geometry):
        self.wire(geometry,self.output.inputs['Geometry'])
        levels={};rows={}
        def level(node):
            if node.name not in levels:levels[node.name]=max((level(link.from_node)+1 for socket in node.inputs for link in socket.links),default=0)
            return levels[node.name]
        for node in self.tree.nodes:
            column=level(node);row=rows.get(column,0);rows[column]=row+1;node.location=(240*column,-200*row)
        return self.tree

def material_uv(g,geometry):
    """Carry the assigned material and generate the UV attribute engine shaders use."""
    q=g.input.outputs;m=g.math
    material=g.node('GeometryNodeSetMaterial','Authoring material');g.wire(geometry,material.inputs['Geometry']);g.wire(q['Material'],material.inputs['Material']);geometry=material.outputs[0]
    xyz=g.split(g.node('GeometryNodeInputPosition','Projection position').outputs[0]);normal=g.split(g.node('GeometryNodeInputNormal','Projection plane').outputs[0])
    nx=m('ABSOLUTE',normal['X']);ny=m('ABSOLUTE',normal['Y']);nz=m('ABSOLUTE',normal['Z'])
    top=m('GREATER_THAN',nz,m('MAXIMUM',nx,ny));side=m('GREATER_THAN',nx,ny)
    u=g.choose(top,xyz['X'],g.choose(side,xyz['Y'],xyz['X']));v=g.choose(top,xyz['Y'],xyz['Z'])
    uv=g.vector(m('DIVIDE',u,m('MULTIPLY',q['Units'],q['Texture Width'])),m('SUBTRACT',1,m('DIVIDE',v,m('MULTIPLY',q['Units'],q['Texture Height']))))
    geometry=g.store(geometry,'UVMap',uv,kind='FLOAT2',domain='CORNER')
    return g.store(geometry,'wavelength',uv,kind='FLOAT2',domain='CORNER')

def parameters(definition):
    """Validate authoring parameters; grid fallback changes inputs, not vertices."""
    p=dict(definition.parameters);minimum=1. if definition.convex_brushes else .001
    if definition.kind not in KINDS:raise ValueError('Unsupported node primitive')
    if any(isinstance(v,(int,float)) and not math.isfinite(v) for v in p.values()):raise ValueError('Primitive parameters must be finite')
    kind=definition.kind
    if kind=='ARCH':
        if not 3<=int(p['segments'])<=64 or not 0<float(p['thickness'])<float(p['radius']) or p['depth']<minimum or not 0<p['angle']<=360 or p['angle']/p['segments']>=180:raise ValueError('Invalid arch dimensions')
    elif kind=='STAIRS':
        if not p.get('curved'):raise ValueError('Use the straight-stair node asset for straight stairs')
        if not 1<=int(p['steps'])<=64 or min(p['rise'],p['width'],p['inner_radius'])<minimum or p['landing']<0 or not 0<abs(p['curve_angle'])<=360 or abs(p['curve_angle'])/p['steps']>=180:raise ValueError('Invalid curved-stair dimensions')
        grid=definition.grid_step or 0
        if grid:
            for key in ('rise','run','width','inner_radius','landing'):
                if p.get(key,0)>0:p[key]=max(grid,round(p[key]/grid)*grid)
        p['snap']=p.get('_node_snap',grid)
    elif kind=='SPHERE':
        if p['radius']<minimum:raise ValueError('Sphere radius must be positive')
        if p.get('sphere_type','ICO')=='ICO':
            if p.get('subdivisions',1) not in (0,1):raise ValueError('Icosphere detail must be 0 or 1')
        elif p.get('sphere_type')!='UV' or not 3<=int(p.get('segments',8))<=64 or not 2<=int(p.get('rings',6))<=32:raise ValueError('Invalid sphere resolution')
    elif kind=='CUBE':
        if min(p['width'],p['run'],p['depth'])<=0:raise ValueError('Cube dimensions must be positive')
    elif min(p['radius'],p['depth'])<=0 or not 3<=int(p['segments'])<=64:raise ValueError('Invalid radial primitive dimensions')
    return p

def group(kind,sphere_type='ICO'):
    name=f'wavelength · {kind.title()} {sphere_type if kind=="SPHERE" else ""} · v1'
    existing=bpy.data.node_groups.get(name)
    if existing:
        if existing.get('wl_generator')!=GENERATOR:raise ValueError('Conflicting primitive node group')
        return existing
    inputs=[('Geometry','NodeSocketGeometry',None),('Radius','NodeSocketFloat',128.),('Thickness','NodeSocketFloat',32.),('Depth','NodeSocketFloat',64.),('Angle','NodeSocketFloat',180.),('Segments','NodeSocketInt',8),('Rings','NodeSocketInt',6),('Detail','NodeSocketInt',1),('Steps','NodeSocketInt',8),('Rise','NodeSocketFloat',16.),('Run','NodeSocketFloat',32.),('Width','NodeSocketFloat',128.),('Landing','NodeSocketFloat',0.),('Inner Radius','NodeSocketFloat',64.),('Sweep','NodeSocketFloat',90.),('Snap','NodeSocketFloat',0.),('Direction','NodeSocketFloat',0.),('Units','NodeSocketFloat',1.),('Brush Part','NodeSocketBool',False),('Part Index','NodeSocketInt',0),('Material','NodeSocketMaterial',None)]
    inputs.extend([('Texture Width','NodeSocketFloat',64.),('Texture Height','NodeSocketFloat',64.)])
    g=Graph(name,GENERATOR,inputs);q=g.input.outputs;m=g.math
    index=g.node('GeometryNodeInputIndex','Element index').outputs[0]
    if kind in {'ARCH','STAIRS'}:
        cube=g.node('GeometryNodeMeshCube','Parametric cell');cube.inputs['Size'].default_value=(1,1,1)
        count=q['Segments'] if kind=='ARCH' else m('ADD',q['Steps'],m('GREATER_THAN',q['Landing'],0))
        line=g.node('GeometryNodeMeshLine','One point per solid part');g.wire(count,line.inputs['Count'])
        line.inputs['Offset'].default_value=(0,0,0)
        points=g.store(line.outputs['Mesh'],'wl_brush_part',index,domain='POINT')
        instance=g.node('GeometryNodeInstanceOnPoints','Generate cell topology');g.wire(points,instance.inputs['Points']);g.wire(cube.outputs['Mesh'],instance.inputs['Instance'])
        realize=g.node('GeometryNodeRealizeInstances','Make part coordinates editable');g.wire(instance.outputs['Instances'],realize.inputs[0])
        single=g.store(cube.outputs['Mesh'],'wl_brush_part',q['Part Index'],domain='POINT')
        geometry=g.choose(q['Brush Part'],single,realize.outputs[0],'GEOMETRY')
        attr=g.node('GeometryNodeInputNamedAttribute','Part identity');attr.data_type='INT';attr.inputs['Name'].default_value='wl_brush_part';part=attr.outputs['Attribute']
        xyz=g.split(g.node('GeometryNodeInputPosition','Cell corner').outputs[0])
        corner=[m('ADD',xyz[key],.5) for key in 'XYZ']
        if kind=='ARCH':
            theta=m('ADD',m('SUBTRACT',math.pi/2,m('MULTIPLY',q['Angle'],math.pi/360)),m('MULTIPLY',m('DIVIDE',m('ADD',part,corner[1]),q['Segments']),m('MULTIPLY',q['Angle'],math.pi/180)))
            radius=m('ADD',m('SUBTRACT',q['Radius'],q['Thickness']),m('MULTIPLY',corner[0],q['Thickness']))
            position=g.vector(m('MULTIPLY',radius,m('COSINE',theta)),m('MULTIPLY',corner[2],m('MULTIPLY',q['Depth'],-1)),m('MULTIPLY',radius,m('SINE',theta)))
        else:
            left=m('GREATER_THAN',q['Sweep'],0);sign=g.choose(left,1,-1)
            half=m('ADD',q['Inner Radius'],m('MULTIPLY',q['Width'],.5))
            snap=q['Snap'];safe=m('MAXIMUM',snap,1e-9)
            half=g.choose(m('GREATER_THAN',snap,0),m('MULTIPLY',m('ROUND',m('DIVIDE',half,safe)),snap),half)
            center=m('MULTIPLY',half,m('MULTIPLY',sign,-1))
            radius=m('ADD',q['Inner Radius'],m('MULTIPLY',g.choose(left,corner[0],m('SUBTRACT',1,corner[0])),q['Width']))
            landing=m('GREATER_THAN',part,m('SUBTRACT',q['Steps'],1))
            theta=m('MULTIPLY',m('DIVIDE',m('ADD',part,corner[1]),q['Steps']),m('MULTIPLY',m('ABSOLUTE',q['Sweep']),math.pi/180))
            end=m('MULTIPLY',m('ABSOLUTE',q['Sweep']),math.pi/180)
            x=m('ADD',center,m('MULTIPLY',sign,m('MULTIPLY',radius,m('COSINE',theta))))
            y=m('MULTIPLY',radius,m('SINE',theta))
            landingx=m('ADD',m('ADD',center,m('MULTIPLY',sign,m('MULTIPLY',radius,m('COSINE',end)))),m('MULTIPLY',m('MULTIPLY',sign,-1),m('MULTIPLY',m('SINE',end),m('MULTIPLY',q['Landing'],corner[1]))))
            landingy=m('ADD',m('MULTIPLY',radius,m('SINE',end)),m('MULTIPLY',m('COSINE',end),m('MULTIPLY',q['Landing'],corner[1])))
            x=g.choose(landing,landingx,x);y=g.choose(landing,landingy,y)
            # Grid rounding happens in authoring space, after direction rotation.
            angle=m('MULTIPLY',q['Direction'],math.pi/180);c=m('COSINE',angle);s=m('SINE',angle)
            rx=m('SUBTRACT',m('MULTIPLY',x,c),m('MULTIPLY',y,s));ry=m('ADD',m('MULTIPLY',x,s),m('MULTIPLY',y,c))
            x=g.choose(m('GREATER_THAN',snap,0),m('MULTIPLY',m('ROUND',m('DIVIDE',rx,safe)),snap),rx)
            y=g.choose(m('GREATER_THAN',snap,0),m('MULTIPLY',m('ROUND',m('DIVIDE',ry,safe)),snap),ry)
            position=g.vector(x,y,m('MULTIPLY',corner[2],m('MULTIPLY',m('MINIMUM',m('ADD',part,1),q['Steps']),q['Rise'])))
        setpos=g.node('GeometryNodeSetPosition','Evaluate parametric corners');g.wire(geometry,setpos.inputs['Geometry']);g.wire(position,setpos.inputs['Position']);geometry=setpos.outputs[0]
        union=g.node('GeometryNodeMeshBoolean','Connected mesh / BSP parts');union.operation='UNION';union.solver='EXACT';union.inputs['Self Intersection'].default_value=True;g.wire(geometry,union.inputs['Mesh 2'])
        geometry=g.choose(q['Brush Part'],geometry,union.outputs[0],'GEOMETRY')
    else:
        node=g.node({'CUBE':'GeometryNodeMeshCube','CYLINDER':'GeometryNodeMeshCylinder','CONE':'GeometryNodeMeshCone','SPHERE':'GeometryNodeMeshUVSphere' if sphere_type=='UV' else 'GeometryNodeMeshIcoSphere'}[kind],'Native primitive')
        if kind=='CUBE':g.wire(g.vector(q['Width'],q['Run'],q['Depth']),node.inputs['Size'])
        elif kind in {'CYLINDER','CONE'}:
            node.fill_type='NGON';g.wire(q['Segments'],node.inputs['Vertices']);g.wire(q['Depth'],node.inputs['Depth'])
            if kind=='CONE':g.wire(q['Radius'],node.inputs['Radius Bottom']);node.inputs['Radius Top'].default_value=0
            else:g.wire(q['Radius'],node.inputs['Radius'])
        else:
            g.wire(q['Radius'],node.inputs['Radius'])
            if sphere_type=='UV':g.wire(q['Segments'],node.inputs['Segments']);g.wire(q['Rings'],node.inputs['Rings'])
            else:g.wire(m('ADD',q['Detail'],1),node.inputs['Subdivisions'])
        geometry=node.outputs['Mesh']
    if kind!='STAIRS':geometry=g.transform(geometry,rotation=g.vector(0,0,m('MULTIPLY',q['Direction'],math.pi/180)))
    geometry=g.transform(geometry,scale=g.vector(q['Units'],q['Units'],q['Units']))
    geometry=material_uv(g,geometry)
    geometry=g.store(geometry,'wl_face_id',m('ADD',index,1))
    return g.finish(geometry)

def set_input(modifier,name,value):
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type=='SOCKET' and socket.in_out=='INPUT' and socket.name==name:
            if hasattr(modifier,'properties'):getattr(modifier.properties.inputs,socket.identifier).value=value
            else:modifier[socket.identifier]=value
            return
    raise ValueError('Missing generator input '+name)

def attach(obj,definition,index=0):
    p=parameters(definition);modifier=obj.modifiers.new('wavelength · Primitive Generator','NODES');modifier.node_group=group(definition.kind,p.get('sphere_type','ICO'))
    names={'radius':'Radius','thickness':'Thickness','depth':'Depth','angle':'Angle','segments':'Segments','rings':'Rings','subdivisions':'Detail','steps':'Steps','rise':'Rise','run':'Run','width':'Width','landing':'Landing','inner_radius':'Inner Radius','curve_angle':'Sweep','snap':'Snap','direction':'Direction'}
    for key,name in names.items():
        if key in p:set_input(modifier,name,p[key])
    set_input(modifier,'Units',definition.unit_meters);set_input(modifier,'Brush Part',definition.convex_brushes);set_input(modifier,'Part Index',index)
    set_input(modifier,'Material',next((mat for mat in obj.data.materials if mat),None))
    sync_materials(obj)
    modifier.show_in_editmode=False
    return modifier

def sync_materials(obj):
    material=next((mat for mat in obj.data.materials if mat),None)
    values={'Material':material,'Texture Width':material.get('wl_width',64) if material else 64.,'Texture Height':material.get('wl_height',64) if material else 64.}
    for modifier in obj.modifiers:
        if modifier.type!='NODES' or not modifier.node_group or not str(modifier.node_group.get('wl_generator','')).startswith('wavelength.geometry_nodes.'):continue
        for socket in modifier.node_group.interface.items_tree:
            if socket.item_type!='SOCKET' or socket.in_out!='INPUT' or socket.name not in values:continue
            value=values[socket.name]
            previous=getattr(modifier.properties.inputs,socket.identifier).value if hasattr(modifier,'properties') else modifier.get(socket.identifier)
            if previous!=value:set_input(modifier,socket.name,value)

def evaluate(definition):
    p=parameters(definition)
    count=(int(p['segments']) if definition.kind=='ARCH' else int(p['steps'])+(p['landing']>0) if definition.kind=='STAIRS' else 1) if definition.convex_brushes else 1
    # Coarse curved grids can collapse a cell; retry progressively finer inputs.
    steps=[p.get('snap',0)/(2**i) for i in range(9)]+[0] if definition.kind=='STAIRS' and p.get('snap') else [0]
    from . import procedural
    for snap in steps:
        result=[]
        for index in range(count):
            data=bpy.data.meshes.new('.Node primitive evaluation');obj=bpy.data.objects.new('.Node primitive evaluation',data);bpy.context.scene.collection.objects.link(obj)
            try:
                modifier=attach(obj,definition,index)
                if definition.kind=='STAIRS':set_input(modifier,'Snap',snap)
                bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
                try:result.append(([tuple(c/definition.unit_meters for c in v.co) for v in mesh.vertices],[tuple(face.vertices) for face in mesh.polygons]))
                finally:evaluated.to_mesh_clear()
            finally:bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data)
        try:procedural.validate(definition,result)
        except ValueError:
            if snap:continue
            raise
        # Keep the chosen quantization with the versioned definition's parameters.
        if definition.kind=='STAIRS':definition.parameters['_node_snap']=snap
        return result
    raise ValueError('Curved stair grid produces degenerate geometry')
