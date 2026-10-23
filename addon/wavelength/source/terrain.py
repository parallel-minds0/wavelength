"""General Geometry Nodes heightfields with a Source displacement export adapter."""
import json,math
import bpy
from bpy.props import FloatProperty,IntProperty,EnumProperty,BoolProperty,PointerProperty
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import profiles,workspace,procedural,draw_displacement
GENERATOR='wavelength.geometry_nodes.heightfield'
VERSION=3


def update_facing(obj):
    """Reverse only face winding; keep the paint domain and sewn vertex positions."""
    name='Wavelength · Surface Facing'
    modifier=next((m for m in obj.modifiers if m.type=='NODES' and m.node_group and m.node_group.get('wl_terrain_facing')),None)
    if not obj.get('wl_terrain_reverse_facing'):
        if modifier:obj.modifiers.remove(modifier)
        return
    if obj.get('wl_procedural_state')=='FINALIZED':return
    tree=bpy.data.node_groups.get(name)
    if tree is None:
        tree=bpy.data.node_groups.new(name,'GeometryNodeTree');tree['wl_terrain_facing']=True
        tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
        tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        inp=tree.nodes.new('NodeGroupInput');reverse=tree.nodes.new('GeometryNodeFlipFaces');out=tree.nodes.new('NodeGroupOutput')
        tree.links.new(inp.outputs['Geometry'],reverse.inputs['Mesh']);tree.links.new(reverse.outputs['Mesh'],out.inputs['Geometry'])
    if modifier is None:modifier=obj.modifiers.new(name,'NODES')
    modifier.node_group=tree


def export_facing(obj,vertices,info):
    if not obj.get('wl_terrain_reverse_facing'):return vertices,info
    size=2**info['power']+1
    # Reversing the base winding swaps its U/V axes. Transpose every sampled
    # field with it so the compiler keeps each sculpted point in world space.
    vertices=[vertices[i*size+j] for j in range(size) for i in range(size)]
    info=dict(info);info['normal']=[-x for x in info['normal']]
    if 'base_corners' in info:info['base_corners']=[info['base_corners'][i] for i in (0,3,2,1)]
    info['alphas']=[list(row) for row in zip(*info['alphas'])]
    return vertices,info


def group():
    name='Wavelength · Heightfield Terrain · v3'
    tree=bpy.data.node_groups.get(name)
    if tree:
        if tree.get('wl_generator')!=GENERATOR:raise ValueError('Conflicting terrain node group')
        return tree
    tree=bpy.data.node_groups.new(name,'GeometryNodeTree');tree['wl_generator']=GENERATOR;tree['wl_generator_version']=VERSION
    tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    for name,kind,default in [('Width','NodeSocketFloat',16.),('Length','NodeSocketFloat',16.),('Resolution','NodeSocketInt',65),('Elevation','NodeSocketFloat',0.),('Amplitude','NodeSocketFloat',1.),('Frequency','NodeSocketFloat',.25),('Seed','NodeSocketFloat',0.),('Flat Placement','NodeSocketBool',False),('Material','NodeSocketMaterial',None)]:
        socket=tree.interface.new_socket(name=name,in_out='INPUT',socket_type=kind)
        if default is not None:socket.default_value=default
    tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    def node(kind,label):
        n=tree.nodes.new(kind);n.label=label;return n
    links=tree.links;inp=node('NodeGroupInput','Terrain definition');out=node('NodeGroupOutput','General heightfield')
    def mathnode(op,a,b):
        n=node('ShaderNodeMath',op);n.operation=op
        for value,socket in [(a,n.inputs[0]),(b,n.inputs[1])]:
            if isinstance(value,(int,float)):socket.default_value=value
            else:links.new(value,socket)
        return n.outputs[0]
    grid=node('GeometryNodeMeshGrid','Unrestricted terrain grid')
    links.new(inp.outputs['Width'],grid.inputs['Size X']);links.new(inp.outputs['Length'],grid.inputs['Size Y'])
    links.new(inp.outputs['Resolution'],grid.inputs['Vertices X']);links.new(inp.outputs['Resolution'],grid.inputs['Vertices Y'])
    position=node('GeometryNodeInputPosition','Terrain coordinates');noise=node('ShaderNodeTexNoise','Seeded terrain noise');noise.noise_dimensions='4D'
    links.new(position.outputs[0],noise.inputs['Vector']);links.new(inp.outputs['Frequency'],noise.inputs['Scale']);links.new(inp.outputs['Seed'],noise.inputs['W'])
    z=mathnode('ADD',inp.outputs['Elevation'],mathnode('MULTIPLY',mathnode('SUBTRACT',noise.outputs['Fac'],.5),mathnode('MULTIPLY',inp.outputs['Amplitude'],2)))
    # The normalized control mesh stores artist height offsets in vertex Z.
    controlpos=node('GeometryNodeInputPosition','Control positions');separate=node('ShaderNodeSeparateXYZ','Control height');links.new(controlpos.outputs[0],separate.inputs[0])
    store=node('GeometryNodeStoreNamedAttribute','Preserve artist heights');store.data_type='FLOAT';store.domain='POINT';store.inputs['Name'].default_value='wl_terrain_height'
    links.new(inp.outputs['Geometry'],store.inputs['Geometry']);links.new(separate.outputs['Z'],store.inputs['Value'])
    flatten=node('GeometryNodeSetPosition','Flatten control sampling domain');links.new(store.outputs[0],flatten.inputs['Geometry'])
    planar=node('ShaderNodeCombineXYZ','Normalized control XY');links.new(separate.outputs['X'],planar.inputs['X']);links.new(separate.outputs['Y'],planar.inputs['Y']);links.new(planar.outputs[0],flatten.inputs['Position'])
    samplepos=node('ShaderNodeVectorMath','Normalized terrain position');samplepos.operation='DIVIDE';links.new(position.outputs[0],samplepos.inputs[0])
    dimensions=node('ShaderNodeCombineXYZ','Terrain dimensions');links.new(inp.outputs['Width'],dimensions.inputs['X']);links.new(inp.outputs['Length'],dimensions.inputs['Y']);dimensions.inputs['Z'].default_value=1;links.new(dimensions.outputs[0],samplepos.inputs[1])
    def sample(name,kind='FLOAT'):
        attribute=node('GeometryNodeInputNamedAttribute',name);attribute.data_type=kind;attribute.inputs['Name'].default_value=name
        sample=node('GeometryNodeSampleNearestSurface','Sample '+name);sample.data_type=kind;links.new(flatten.outputs[0],sample.inputs['Mesh']);links.new(attribute.outputs['Attribute'],sample.inputs['Value']);links.new(samplepos.outputs[0],sample.inputs['Sample Position']);return sample.outputs['Value']
    painted=sample('wl_terrain_height');blend=sample('wl_terrain_blend')
    height=node('GeometryNodeSwitch','Placement preview / full terrain');height.input_type='FLOAT';links.new(inp.outputs['Flat Placement'],height.inputs['Switch']);links.new(mathnode('ADD',z,painted),height.inputs['False']);links.new(inp.outputs['Elevation'],height.inputs['True'])
    offset=node('ShaderNodeCombineXYZ','Height offset');links.new(height.outputs[0],offset.inputs['Z'])
    deform=node('GeometryNodeSetPosition','Evaluate terrain heights');links.new(grid.outputs['Mesh'],deform.inputs['Geometry']);links.new(offset.outputs[0],deform.inputs['Offset'])
    uv=node('GeometryNodeStoreNamedAttribute','Terrain UVs');uv.domain='CORNER';uv.data_type='FLOAT2';uv.inputs['Name'].default_value='UVMap'
    links.new(deform.outputs[0],uv.inputs['Geometry']);links.new(grid.outputs['UV Map'],uv.inputs['Value'])
    alias=node('GeometryNodeStoreNamedAttribute','Wavelength shader UVs');alias.domain='CORNER';alias.data_type='FLOAT2';alias.inputs['Name'].default_value='wavelength';links.new(uv.outputs[0],alias.inputs['Geometry']);links.new(grid.outputs['UV Map'],alias.inputs['Value'])
    mask=node('GeometryNodeStoreNamedAttribute','Painted material blend');mask.domain='POINT';mask.data_type='FLOAT';mask.inputs['Name'].default_value='wl_terrain_blend';links.new(alias.outputs[0],mask.inputs['Geometry']);links.new(blend,mask.inputs['Value'])
    vector=node('GeometryNodeStoreNamedAttribute','Shared surface deformation');vector.domain='POINT';vector.data_type='FLOAT_VECTOR';vector.inputs['Name'].default_value='wl_terrain_vector';links.new(mask.outputs[0],vector.inputs['Geometry']);links.new(sample('wl_terrain_vector','FLOAT_VECTOR'),vector.inputs['Value'])
    current=vector.outputs[0]
    for name,kind in [('wl_terrain_seam_target','FLOAT_VECTOR'),('wl_terrain_seam_weight','FLOAT')]:
        store=node('GeometryNodeStoreNamedAttribute',name);store.domain='POINT';store.data_type=kind;store.inputs['Name'].default_value=name;links.new(current,store.inputs['Geometry']);links.new(sample(name,kind),store.inputs['Value']);current=store.outputs[0]
    material=node('GeometryNodeSetMaterial','Terrain material');links.new(current,material.inputs['Geometry']);links.new(inp.outputs['Material'],material.inputs['Material']);links.new(material.outputs[0],out.inputs['Geometry'])
    levels={};rows={}
    def level(n):
        if n.name not in levels:levels[n.name]=max((level(l.from_node)+1 for s in n.inputs for l in s.links),default=0)
        return levels[n.name]
    for n in tree.nodes:
        column=level(n);row=rows.get(column,0);rows[column]=row+1;n.location=(column*240,-row*220)
    return tree


def changed(self,context):
    obj=self.id_data
    if not obj.get('wl_terrain') or obj.get('wl_procedural_state')!='PROCEDURAL':return
    try:
        update(obj)
        if 'wl_terrain_error' in obj:del obj['wl_terrain_error']
    except (ValueError,RuntimeError) as exc:obj['wl_terrain_error']=str(exc)


class WLTerrain(bpy.types.PropertyGroup):
    surface_source:PointerProperty(name='Source Brush',type=bpy.types.Object)
    flat_preview:BoolProperty(name='Flat Placement',default=False,update=changed,description='Show the undeformed footprint for placement; export always uses full terrain')
    paint_mode:EnumProperty(name='Paint',items=[('RAISE','Raise / Lower','Ctrl lowers'),('SMOOTH','Smooth','Smooth painted heights'),('TEXTURE','Texture Blend','Paint layer weight; Ctrl erases')],default='RAISE')
    paint_radius:FloatProperty(name='Radius',default=1.5,min=.001)
    paint_strength:FloatProperty(name='Height Strength',default=.25,min=.001)
    paint_opacity:FloatProperty(name='Paint Opacity',default=.2,min=.001,max=1)
    blend_base:PointerProperty(name='Base Material',type=bpy.types.Material)
    paint_material:PointerProperty(name='Paint Material',type=bpy.types.Material,update=changed)
    width:FloatProperty(name='Width',default=16,min=.001,update=changed)
    length:FloatProperty(name='Length',default=16,min=.001,update=changed)
    resolution:IntProperty(name='Resolution',default=65,min=3,max=513,update=changed,description='General terrain vertices per side, independent of Source patch resolution')
    elevation:FloatProperty(name='Elevation',default=0,update=changed)
    amplitude:FloatProperty(name='Amplitude',default=1,min=0,update=changed)
    frequency:FloatProperty(name='Frequency',default=.25,min=.00001,update=changed)
    seed:IntProperty(name='Seed',default=0,update=changed)
    power:EnumProperty(name='Patch Power',items=[('2','2 — 5×5',''),('3','3 — 9×9',''),('4','4 — 17×17','')],default='3',update=changed)
    tiles_x:IntProperty(name='Patches X',default=2,min=1,max=16,update=changed)
    tiles_y:IntProperty(name='Patches Y',default=2,min=1,max=16,update=changed)


def remember(obj):
    previous=procedural.Definition.loads(obj['wl_definition']);s=obj.wavelength_terrain
    values={key:getattr(s,key) for key in ('width','length','resolution','elevation','amplitude','frequency','seed','power','tiles_x','tiles_y')}
    from dataclasses import replace
    obj['wl_definition']=replace(previous,parameters=values,generator_version=VERSION).dumps()


_UPDATING=set()
def update(obj):
    key=obj.as_pointer()
    if key in _UPDATING:return
    _UPDATING.add(key)
    try:_update(obj)
    finally:_UPDATING.discard(key)


def _update(obj):
    if obj.get('wl_procedural_state')=='FINALIZED':raise ValueError('Terrain is finalized; edit its mesh directly')
    definition=procedural.Definition.loads(obj['wl_definition']);s=obj.wavelength_terrain;unit=definition.unit_meters
    modifier=next((m for m in obj.modifiers if m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==GENERATOR),None)
    from . import terrain_paint
    if paintable(obj):terrain_paint.ensure_control(obj)
    if modifier is None:modifier=obj.modifiers.new('Wavelength · Terrain Generator','NODES');modifier.node_group=group()
    modifier.node_group=group()  # Upgrade the graph without replacing the painted control mesh.
    values=dict(Width=s.width*unit,Length=s.length*unit,Resolution=s.resolution,Elevation=s.elevation*unit,Amplitude=s.amplitude*unit,Frequency=s.frequency/unit,Seed=float(s.seed),Material=terrain_paint.preview_material(obj))
    values['Flat Placement']=s.flat_preview
    if not paintable(obj):values.update(Resolution=2,Elevation=0.,Amplitude=0.)
    for socket in modifier.node_group.interface.items_tree:
        if socket.item_type=='SOCKET' and socket.in_out=='INPUT' and socket.name in values:
            if hasattr(modifier,'properties'):getattr(modifier.properties.inputs,socket.identifier).value=values[socket.name]
            else:modifier[socket.identifier]=values[socket.name]
    if obj.get('wl_terrain_vector_surface'):
        from . import terrain_sew
        terrain_sew.update_preview(obj)
    remember(obj);obj.update_tag()


_MATERIAL_SIGNATURES={}
def sync_material(obj,force=False):
    if obj.get('wl_procedural_state')!='PROCEDURAL':return
    signature=tuple((m.as_pointer(),bool(m.get('wl_realized'))) if m else (0,False) for m in obj.data.materials)
    key=obj.as_pointer()
    if force or _MATERIAL_SIGNATURES.get(key)!=signature:
        previous=_MATERIAL_SIGNATURES.get(key,())
        added=[m for m in obj.data.materials if m and m.as_pointer() not in {row[0] for row in previous}]
        if previous and added and obj.data.materials:obj.data.materials[0]=added[-1]
        _MATERIAL_SIGNATURES[key]=tuple((m.as_pointer(),bool(m.get('wl_realized'))) if m else (0,False) for m in obj.data.materials)
        update(obj)


def paintable(obj):return obj.get('wl_terrain_stage','DISPLACEMENT')=='DISPLACEMENT'


def enable_paint(obj):
    if obj.get('wl_procedural_state')!='PROCEDURAL':raise ValueError('Finalized terrain cannot enable procedural painting')
    obj['wl_terrain_stage']='DISPLACEMENT';obj.wavelength_terrain.flat_preview=False
    update(obj)


def create(context,paintable_surface=False):
    settings=context.scene.wavelength;unit=profiles.unit_meters(settings)
    if settings.engine!='blender' and not profiles.is_source(settings.engine):raise ValueError('Terrain output is currently supported for Blender and Source profiles')
    data=bpy.data.meshes.new('Terrain');obj=bpy.data.objects.new('Terrain',data);context.collection.objects.link(obj);obj.location=context.scene.cursor.location
    try:
        from dataclasses import replace
        d=procedural.define('TERRAIN',settings.engine,{},unit,profile_id=settings.profile_id,profile_name=settings.profile_name)
        d=replace(d,generator=GENERATOR,generator_version=VERSION,convex_brushes=False)
        obj['wl_definition']=d.dumps();obj['wl_terrain']=True;obj['wl_procedural_state']='PROCEDURAL';obj['wl_owner_profile']=settings.engine;obj['wl_unit_meters']=unit;obj['wl_terrain_stage']='DISPLACEMENT' if paintable_surface else 'PLANE'
        if profiles.is_source(settings.engine):
            s=obj.wavelength_terrain;s.width=s.length=1024;s.amplitude=0;s.frequency=.004
        obj.wavelength_terrain.amplitude=0
        update(obj)
    except Exception:
        bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(data);raise
    if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);context.view_layer.objects.active=obj
    return obj


def create_footprint(context,a,b,u,v,n):
    from mathutils import Matrix
    obj=create(context);s=obj.wavelength_terrain;unit=obj['wl_unit_meters']
    width=abs((b-a).dot(u));length=abs((b-a).dot(v))
    minimum=max(profiles.unit_meters(context.scene.wavelength),1e-3)
    s.width=max(width,minimum)/unit;s.length=max(length,minimum)/unit
    frame=Matrix((u,v,n)).transposed().to_4x4();frame.translation=(a+b)*.5;obj.matrix_world=frame
    update(obj);return obj


def patches(obj):
    """Sample the evaluated general mesh. Shared global samples guarantee seams."""
    definition=procedural.Definition.loads(obj['wl_definition'])
    if not paintable(obj):raise ValueError('Convert the terrain plane to a paintable displacement before Source export')
    if obj.get('wl_terrain_vector_surface'):
        from . import terrain_sew
        return terrain_sew.patches(obj)
    if not profiles.is_source(definition.owner):raise ValueError('Terrain belongs to a non-Source profile; convert ownership explicitly before Source export')
    s=obj.wavelength_terrain
    if obj.get('wl_procedural_state')=='FINALIZED':
        from types import SimpleNamespace
        s=SimpleNamespace(**definition.parameters)
    power=int(s.power);segments=2**power;nx=s.tiles_x*segments;ny=s.tiles_y*segments
    from . import terrain_paint
    previous=terrain_paint.full_surface(obj)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        if not mesh.vertices or not mesh.polygons:raise ValueError('Terrain has no surface')
        vertices=[v.co.copy() for v in mesh.vertices];mesh.calc_loop_triangles()
        attached=bool(obj.get('wl_terrain_face_corners'))
        if attached:
            from . import terrain_face
            terrain_face.validate_attachment(obj)
            quad=terrain_face.corners(obj)
            width=s.width*definition.unit_meters;length=s.length*definition.unit_meters
            for p in vertices:
                u,v=terrain_face.parameters(obj,p,quad);p.x=(u-.5)*width;p.y=(v-.5)*length
        for tri in mesh.loop_triangles:
            a,b,c=(vertices[i] for i in tri.vertices)
            if (b-a).cross(c-a).z<=1e-10:raise ValueError('Source terrain conversion requires an unfolded heightfield; overhangs and vertical faces need model output')
        # Use Blender's evaluated triangulation: terrain quads are non-planar.
        bvh=BVHTree.FromPolygons(vertices,[tuple(t.vertices) for t in mesh.loop_triangles],all_triangles=True)
        low=Vector(tuple(min(p[i] for p in vertices) for i in range(3)));high=Vector(tuple(max(p[i] for p in vertices) for i in range(3)))
        edges={}
        for polygon in mesh.polygons:
            ids=list(polygon.vertices)
            for a,b in zip(ids,ids[1:]+ids[:1]):
                key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
        tolerance=max(high.x-low.x,high.y-low.y)*1e-5
        for (a,b),count in edges.items():
            if count>2:raise ValueError('Source terrain conversion requires a manifold heightfield')
            if count==1:
                outer=any(abs(vertices[a][axis]-bound)<tolerance and abs(vertices[b][axis]-bound)<tolerance for axis in (0,1) for bound in (low[axis],high[axis]))
                if not outer:raise ValueError('Terrain has an internal hole or non-rectangular boundary; use model output')
        margin=max(1,(high-low).length);samples={};weights={}
        attribute=mesh.attributes.get('wl_terrain_blend')
        for j in range(ny+1):
            for i in range(nx+1):
                x=low.x+(high.x-low.x)*i/nx;y=low.y+(high.y-low.y)*j/ny
                hit,_,triangle,_=bvh.ray_cast(Vector((x,y,high.z+margin)),Vector((0,0,-1)))
                if hit is None:
                    # Float ray tests can miss exact grid edges. Find an adjacent
                    # triangle, then evaluate its plane at the original XY sample.
                    epsilon=max(high.x-low.x,high.y-low.y)*1e-5
                    xx=max(low.x+epsilon,min(high.x-epsilon,x+epsilon));yy=max(low.y+epsilon,min(high.y-epsilon,y+epsilon))
                    hit,_,triangle,_=bvh.ray_cast(Vector((xx,yy,high.z+margin)),Vector((0,0,-1)))
                if hit is None:
                    raise ValueError(f'Terrain has a hole or unsupported boundary at sample {i},{j}; Source resampling refused')
                a,b,c=(vertices[k] for k in mesh.loop_triangles[triangle].vertices)
                normal=(b-a).cross(c-a)
                z=a.z-(normal.x*(x-a.x)+normal.y*(y-a.y))/normal.z
                samples[i,j]=(x,y,z)
                if attribute:
                    from mathutils.geometry import barycentric_transform
                    bary=barycentric_transform(Vector((x,y,z)),a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
                    ids=mesh.loop_triangles[triangle].vertices
                    weights[i,j]=max(0,min(1,sum(bary[k]*attribute.data[ids[k]].value for k in range(3))))
                else:weights[i,j]=0

        result=[]
        for ty in range(s.tiles_y):
            for tx in range(s.tiles_x):
                size=segments+1
                verts=[samples[tx*segments+i,ty*segments+j] for j in range(size) for i in range(size)]
                faces=[(j*size+i,j*size+i+1,(j+1)*size+i+1,(j+1)*size+i) for j in range(segments) for i in range(segments)]
                info=dict(power=power,normal=[0,0,1],patch=[tx,ty],alphas=[[weights[tx*segments+i,ty*segments+j]*255 for i in range(size)] for j in range(size)])
                if attached:
                    if s.tiles_x!=1 or s.tiles_y!=1:raise ValueError('A brush-face displacement must have exactly one patch')
                    verts=[tuple(terrain_face.position(obj,p[0]/width+.5,p[1]/length+.5,quad)+Vector((0,0,p[2]))) for p in verts]
                    info['base_corners']=[list(p) for p in quad]
                result.append((verts,faces,info))
        return result
    finally:
        evaluated.to_mesh_clear();terrain_paint.restore_surface(obj,previous)


def brushes(obj,validate_seams=True):
    if validate_seams and obj.get('wl_terrain_seams'):
        from . import terrain_sew
        terrain_sew.validate_export(obj)
    x=obj.matrix_world.to_3x3().col[0].normalized();y=obj.matrix_world.to_3x3().col[1].normalized()
    if abs(x.dot(y))>1e-5 and not obj.get('wl_terrain_face_corners'):raise ValueError('Apply terrain shear before Source displacement export')
    material=next((m for m in obj.data.materials if m and m.get('wl_texture')),None)
    if material is None:raise ValueError('Assign a Source material to the terrain before export')
    ensure_generated_material(obj,material)
    result=[]
    for verts,faces,info in patches(obj):
        verts,info=export_facing(obj,verts,info)
        if any(value>1e-5 for row in info['alphas'] for value in row) and not material.get('wl_source_blend'):raise ValueError('Texture-painted Source terrain requires a WorldVertexTransition material')
        mesh=bpy.data.meshes.new('.Terrain displacement export');temporary=bpy.data.objects.new('.Terrain displacement export',mesh)
        try:
            mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(material)
            temporary.matrix_world=obj.matrix_world.copy();temporary['wl_unit_meters']=obj['wl_unit_meters'];temporary['wl_displacement']=json.dumps(info)
            brush=draw_displacement.brush(temporary);brush[0].vmf['dispinfo']['alphas']=info['alphas'];result.append(brush)
        finally:bpy.data.objects.remove(temporary,do_unlink=True);bpy.data.meshes.remove(mesh)
    return result


def blend_settings(obj,context):
    definition=procedural.Definition.loads(obj['wl_definition']);settings=context.scene.wavelength
    if not profiles.is_source(definition.owner) or settings.engine!=definition.owner:raise ValueError('Activate the terrain owning Source profile first')
    if definition.owner_profile_id and definition.owner_profile_id!=settings.profile_id:raise ValueError('Activate the terrain owning saved profile first')
    if not settings.project_dir:raise ValueError('Configure a project directory before generating terrain materials')
    return settings


def create_blend(obj,context):
    from . import source_assets,terrain_blend
    settings=blend_settings(obj,context);s=obj.wavelength_terrain
    base=s.blend_base or next((m for m in obj.data.materials if m),None);paint=s.paint_material
    if not base or not paint or not base.get('wl_texture') or not paint.get('wl_texture'):raise ValueError('Choose two Source materials for the terrain layers')
    for material in (base,paint):
        if material.get('wl_asset_profile') and material['wl_asset_profile']!=settings.engine:raise ValueError('Terrain layers must belong to the active Source profile')
    assets=source_assets.library(bpy.path.abspath(settings.game_dir))
    a=assets.material(base['wl_texture']);b=assets.material(paint['wl_texture'])
    name,text=terrain_blend.recipe(a,b)
    # Confirm both referenced VTFs exist before staging any generated material.
    for values in (a,b):
        for key in ('$basetexture','$bumpmap'):
            if values.get(key):assets.read('materials/'+terrain_blend.texture_reference(values[key])+'.vtf')
    project_file,game_file=terrain_blend.stage(bpy.path.abspath(settings.game_dir),bpy.path.abspath(settings.project_dir),name,text)
    material=source_assets.material(settings,name)
    material['wl_generated_terrain_vmt']=text;material['wl_generated_terrain_name']=name
    material['wl_terrain_layer_sources']=json.dumps([base['wl_texture'],paint['wl_texture']])
    s.blend_base=base
    if obj.data.materials:obj.data.materials[0]=material
    else:obj.data.materials.append(material)
    obj['wl_terrain_generated_project_file']=str(project_file);obj['wl_terrain_generated_game_file']=str(game_file)
    sync_material(obj,force=True)
    return material


def ensure_generated_material(obj,material):
    text=material.get('wl_generated_terrain_vmt')
    if not text:return
    from . import terrain_blend
    settings=blend_settings(obj,bpy.context)
    terrain_blend.stage(bpy.path.abspath(settings.game_dir),bpy.path.abspath(settings.project_dir),material['wl_generated_terrain_name'],text)


class WL_OT_terrain_blend(bpy.types.Operator):
    bl_idname='wavelength.terrain_blend';bl_label='Create Blend Material';bl_options={'REGISTER','UNDO'}
    bl_description='Generate a two-layer Source VMT in the project and game material directories, then assign it to the terrain'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain') and context.object.get('wl_procedural_state')=='PROCEDURAL' and profiles.is_source(context.object.get('wl_owner_profile',''))
    def execute(self,context):
        try:material=create_blend(context.object,context)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Created '+material['wl_texture']);return {'FINISHED'}


class WL_OT_terrain_add(bpy.types.Operator):
    bl_idname='wavelength.terrain_add';bl_label='Terrain';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and (context.scene.wavelength.engine=='blender' or profiles.is_source(context.scene.wavelength.engine))
    def execute(self,context):
        try:create(context)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_terrain_enable_paint(bpy.types.Operator):
    bl_idname='wavelength.terrain_enable_paint';bl_label='Create Paintable Displacement';bl_options={'REGISTER','UNDO'}
    bl_description='Subdivide the flat terrain footprint into a general paintable surface; Source conversion happens on export'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain') and context.object.get('wl_procedural_state')=='PROCEDURAL' and not paintable(context.object)
    def execute(self,context):
        try:enable_paint(context.object)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_terrain_update(bpy.types.Operator):
    bl_idname='wavelength.terrain_update';bl_label='Update Terrain';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain') and context.object.get('wl_procedural_state')=='PROCEDURAL'
    def execute(self,context):
        try:update(context.object)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_terrain_finalize(bpy.types.Operator):
    bl_idname='wavelength.terrain_finalize';bl_label='Finalize Terrain';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return WL_OT_terrain_update.poll(context)
    def execute(self,context):
        obj=context.object
        if not obj or not obj.get('wl_terrain') or obj.get('wl_procedural_state')=='FINALIZED':return {'CANCELLED'}
        try:
            if profiles.is_source(obj['wl_owner_profile']):patches(obj)
            from . import terrain_paint
            previous=terrain_paint.full_surface(obj)
            dg=context.evaluated_depsgraph_get();mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        finally:
            if 'previous' in locals():terrain_paint.restore_surface(obj,previous)
        old=obj.data
        if not any(mesh.materials):
            mesh.materials.clear()
            for mat in old.materials:mesh.materials.append(mat)
        obj.data=mesh;obj.modifiers.clear();obj['wl_procedural_state']='FINALIZED'
        if old.users==0:bpy.data.meshes.remove(old)
        return {'FINISHED'}


class WL_OT_terrain_flip_facing(bpy.types.Operator):
    bl_idname='wavelength.terrain_flip_facing';bl_label='Flip Terrain Facing';bl_options={'REGISTER','UNDO'}
    bl_description='Reverse selected terrain fronts without moving sculpted points or sewn edges; Source renders the front side'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain')
    def execute(self,context):
        selected=[o for o in context.selected_objects if o.get('wl_terrain')]
        if any(o.get('wl_procedural_state')=='FINALIZED' and o.data.users>1 for o in selected):
            self.report({'ERROR'},'Make finalized terrain meshes single-user before flipping their facing');return {'CANCELLED'}
        for obj in selected:
            obj['wl_terrain_reverse_facing']=not obj.get('wl_terrain_reverse_facing',False)
            if obj.get('wl_procedural_state')=='FINALIZED':obj.data.flip_normals();obj.data.update()
            else:update_facing(obj)
            obj.update_tag()
        return {'FINISHED'}


class WL_PT_terrain(bpy.types.Panel):
    bl_label='Wavelength Terrain';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.object and context.object.get('wl_terrain')
    def draw(self,context):
        obj=context.object;s=obj.wavelength_terrain;layout=self.layout
        layout.operator('wavelength.terrain_flip_facing',icon='NORMALS_FACE')
        layout.label(text=f"{obj['wl_owner_profile']} · {obj['wl_procedural_state'].title()}")
        if obj['wl_procedural_state']=='FINALIZED':layout.label(text='Edit the baked heightfield mesh');return
        layout.prop(s,'flat_preview')
        if obj.get('wl_terrain_face_corners'):
            if obj.get('wl_terrain_detached'):layout.label(text='Independent surface from brush face')
            else:
                row=layout.row();row.enabled=False;row.prop(s,'surface_source');layout.label(text='Footprint follows the original brush face')
                layout.operator('wavelength.displacement_detach')
        else:
            layout.prop(s,'width');layout.prop(s,'length')
        if not paintable(obj):
            layout.label(text='Flat terrain footprint');layout.operator('wavelength.terrain_enable_paint',icon='MESH_GRID');return
        for key in ('resolution','elevation','amplitude','frequency','seed'):layout.prop(s,key)
        if profiles.is_source(obj['wl_owner_profile']):
            layout.separator();layout.label(text='Source output sampling')
            layout.prop(s,'power')
            if not obj.get('wl_terrain_face_corners'):
                layout.prop(s,'tiles_x');layout.prop(s,'tiles_y')
        if obj.get('wl_terrain_error'):layout.label(text=obj['wl_terrain_error'],icon='ERROR')
        layout.separator();layout.prop(s,'paint_mode');layout.prop(s,'paint_radius');layout.prop(s,'paint_strength' if s.paint_mode!='TEXTURE' else 'paint_opacity')
        layout.operator('wavelength.terrain_sew',icon='AUTOMERGE_ON')
        from . import terrain_sew
        if terrain_sew.links(obj):
            try:layout.label(text=f'{len(terrain_sew.network(obj))} connected surfaces')
            except ValueError as exc:layout.label(text=str(exc),icon='ERROR')
            row=layout.row(align=True);row.operator('wavelength.terrain_sew',text='Smooth Seams').smooth=True;row.operator('wavelength.terrain_unsew',text='Unsew')
        if s.paint_mode=='TEXTURE':
            if profiles.is_source(obj['wl_owner_profile']):
                layout.prop(s,'blend_base');layout.prop(s,'paint_material',text='Second Material');layout.operator('wavelength.terrain_blend')
                layout.label(text='Or assign an existing transition material')
            else:layout.prop(s,'paint_material')
        from .terrain_paint import paint_button
        paint_button(layout,context,text='Paint Terrain')
        layout.operator('wavelength.terrain_update');layout.operator('wavelength.terrain_finalize')


def menu(self,context):
    if workspace.active(context) and (context.scene.wavelength.engine=='blender' or profiles.is_source(context.scene.wavelength.engine)):self.layout.operator('wavelength.terrain_add',icon='MESH_GRID')
CLASSES=(WLTerrain,WL_OT_terrain_blend,WL_OT_terrain_add,WL_OT_terrain_enable_paint,WL_OT_terrain_update,WL_OT_terrain_finalize,WL_OT_terrain_flip_facing,WL_PT_terrain)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Object.wavelength_terrain=PointerProperty(type=WLTerrain)
    bpy.types.VIEW3D_MT_mesh_add.append(menu)
    from . import terrain_paint
    terrain_paint.register()
    from . import terrain_face
    terrain_face.register()
    from . import terrain_sew
    terrain_sew.register()
def unregister():
    from . import terrain_sew
    terrain_sew.unregister()
    from . import terrain_face
    terrain_face.unregister()
    from . import terrain_paint
    terrain_paint.unregister()
    _MATERIAL_SIGNATURES.clear()
    try:bpy.types.VIEW3D_MT_mesh_add.remove(menu)
    except Exception:pass
    if hasattr(bpy.types.Object,'wavelength_terrain'):del bpy.types.Object.wavelength_terrain
    for cls in reversed(CLASSES):
        try:bpy.utils.unregister_class(cls)
        except RuntimeError:pass
