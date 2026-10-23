"""Typed DMX KeyValues2 and editable VMAP polygon topology.

VMAP stores destination-vertex half edges, with explicit opposite and next
indices. UVs belong to half-edge corners, not shared mesh vertices. This module
has no Blender dependency so malformed input can be rejected before allocation.
"""
import json,math,re,uuid
from dataclasses import dataclass,field

HEADER='<!-- dmx encoding keyvalues2 4 format vmap 40 -->\n'
@dataclass
class Element:
    kind:str
    attrs:dict=field(default_factory=dict)
    def get(self,key,default=None):return self.attrs.get(key,('',default))[1]
    def put(self,key,kind,value):self.attrs[key]=(kind,value);return self

def element(kind,**attrs):
    result=Element(kind).put('id','elementid',str(uuid.uuid4()))
    for key,(typ,value) in attrs.items():result.put(key,typ,value)
    return result

def loads(text):
    if len(text)>256*1024*1024:raise ValueError('VMAP exceeds 256 MiB text limit')
    # DMX strings allow literal newlines (binary hex blocks) and C escapes.
    pattern=re.compile(r'\s+|<!--.*?-->|//[^\n]*|"((?:\\.|[^"\\])*)"|([{}\[\],])',re.S)
    tokens=[];pos=0
    for match in pattern.finditer(text):
        if text[pos:match.start()].strip():raise ValueError('Invalid DMX token')
        pos=match.end()
        if match.group(1) is not None:
            tokens.append(re.sub(r'\\(["\\nt])',lambda m:{'n':'\n','t':'\t'}.get(m[1],m[1]),match[1]))
        elif match.group(2) and match.group(2)!=',':tokens.append(match[2])
    if text[pos:].strip():raise ValueError('Truncated DMX string')
    i=0;ids={}
    def take():
        nonlocal i
        if i>=len(tokens):raise ValueError('Truncated DMX')
        value=tokens[i];i+=1;return value
    def scalar(typ,value):
        if typ in {'int','uint64','uint8'}:return int(value,0) if value.startswith('0x') else int(value)
        if typ in {'float','time'}:
            result=float(value)
            if not math.isfinite(result):raise ValueError('Nonfinite DMX value')
            return result
        if typ=='bool':return value in {'1','true'}
        if typ in {'vector2','vector3','vector4','qangle','quaternion','matrix','color'}:
            result=tuple(float(v) for v in value.split())
            if not all(math.isfinite(v) for v in result):raise ValueError('Nonfinite DMX vector')
            return result
        return value
    def node(kind,depth=0):
        if depth>100:raise ValueError('DMX nesting exceeds 100')
        if take()!='{':raise ValueError('Expected DMX element')
        result=Element(kind)
        while tokens[i]!='}':
            key=take();typ=take()
            if typ.endswith('_array'):
                if take()!='[':raise ValueError('Expected DMX array')
                value=[];base=typ[:-6]
                while tokens[i]!=']':
                    item=take()
                    value.append(node(item,depth+1) if base=='element' and item!='element' else scalar(base,take() if base=='element' else item))
                take()
            elif tokens[i]=='{':value=node(typ,depth+1)
            else:value=scalar(typ,take())
            result.put(key,typ,value)
        take()
        if result.get('id'):ids[result.get('id')]=result
        return result
    roots=[]
    try:
        while i<len(tokens):roots.append(node(take()))
    except (IndexError,TypeError) as exc:raise ValueError('Malformed DMX element') from exc
    def resolve(obj,seen):
        if id(obj) in seen:return
        seen.add(id(obj))
        for key,(typ,value) in list(obj.attrs.items()):
            if typ=='element' and isinstance(value,str):obj.attrs[key]=(typ,ids.get(value))
            elif typ=='element_array':obj.attrs[key]=(typ,[ids.get(v) if isinstance(v,str) else v for v in value])
            value=obj.get(key)
            for child in value if isinstance(value,list) else [value]:
                if isinstance(child,Element):resolve(child,seen)
    for root in roots:resolve(root,set())
    return next((r for r in roots if r.kind=='CMapRootElement'),None) or (_ for _ in ()).throw(ValueError('Not a VMAP document'))

def dumps(root):
    def scalar(value):
        if value is None:return ''
        if isinstance(value,bool):return '1' if value else '0'
        if isinstance(value,(tuple,list)):return ' '.join(format(v,'.9g') for v in value)
        return format(value,'.9g') if isinstance(value,float) else str(value)
    def node(obj,level):
        pad='\t'*level;lines=[json.dumps(obj.kind),pad+'{']
        for key,(typ,value) in obj.attrs.items():
            prefix=pad+'\t'+json.dumps(key)+' '+json.dumps(typ)+' '
            if isinstance(value,Element):lines.append(prefix+'\n'+node(value,level+1).split('\n',1)[1])
            elif typ.endswith('_array'):
                lines.append(prefix+'[')
                for index,item in enumerate(value):lines.append(pad+'\t\t'+(node(item,level+2) if isinstance(item,Element) else json.dumps(scalar(item)))+(',' if index<len(value)-1 else ''))
                lines.append(pad+'\t]')
            else:lines.append(prefix+json.dumps(scalar(value)))
        lines.append(pad+'}');return '\n'.join(lines)
    return HEADER+node(root,0)+'\n'

def stream(name,typ,data,flags=0):
    semantic,_,index=name.partition(':')
    result=element('CDmePolygonMeshDataStream',name=('string',name),standardAttributeName=('string',semantic),semanticName=('string',semantic),semanticIndex=('int',int(index or 0)),vertexBufferLocation=('int',0),dataStateFlags=('int',flags),data=(typ+'_array',data))
    result.put('subdivisionBinding','CDmePolygonMeshSubdivisiondataBinding',element('CDmePolygonMeshSubdivisiondataBinding',name=('string','subdivisionBinding'),targetDataType=('int',1 if name=='texcoord:0' and flags else -1),targetStreamIndex=('int',0 if name=='texcoord:0' and flags else -1),streamSourceType=('int',0 if name=='texcoord:0' and flags else 1)))
    return result

def data_array(size,streams):return element('CDmePolygonMeshDataArray',size=('int',size),streams=('element_array',streams))

def polygon_mesh(vertices,faces,uvs,materials,material_indices):
    """Build manifold half-edge pairs, including the void side of open borders."""
    edges=[];lookup={};face_edges=[]
    for face_id,face in enumerate(faces):
        if len(face)<3 or len(set(face))!=len(face):raise ValueError('Degenerate VMAP polygon')
        loop=[]
        for corner,b in enumerate(face):
            a=face[corner-1]
            if not (0<=a<len(vertices) and 0<=b<len(vertices)):raise ValueError('VMAP vertex index out of range')
            if (a,b) in lookup:raise ValueError('Nonmanifold or inconsistently wound mesh; fix geometry before VMAP export')
            if (b,a) in lookup:index=lookup[(b,a)]^1
            else:
                index=len(edges);edges.extend([{'vertex':b,'face':-1,'next':-1,'uv':(0,0)},{'vertex':a,'face':-1,'next':-1,'uv':(0,0)}])
            lookup[(a,b)]=index
            edges[index].update(face=face_id,uv=uvs[face_id][corner]);loop.append(index)
        for j,index in enumerate(loop):edges[index]['next']=loop[(j+1)%len(loop)]
        face_edges.append(loop[0])
    # Boundary half edges form their own loops in reverse order.
    starts={edges[i^1]['vertex']:i for i,e in enumerate(edges) if e['face']==-1}
    for i,e in enumerate(edges):
        if e['face']==-1:e['next']=starts.get(e['vertex'],i)
    vertex_edges=[-1]*len(vertices)
    for i,e in enumerate(edges):vertex_edges[edges[i^1]['vertex']]=i
    mesh=element('CDmePolygonMesh')
    arrays={'vertexEdgeIndices':vertex_edges,'vertexDataIndices':list(range(len(vertices))),'edgeVertexIndices':[e['vertex'] for e in edges],'edgeOppositeIndices':[i^1 for i in range(len(edges))],'edgeNextIndices':[e['next'] for e in edges],'edgeFaceIndices':[e['face'] for e in edges],'edgeDataIndices':[i//2 for i in range(len(edges))],'edgeVertexDataIndices':list(range(len(edges))),'faceEdgeIndices':face_edges,'faceDataIndices':list(range(len(faces)))}
    for key,value in arrays.items():mesh.put(key,'int_array',value)
    mesh.put('materials','string_array',materials)
    mesh.put('vertexData','CDmePolygonMeshDataArray',data_array(len(vertices),[stream('position:0','vector3',vertices,3)]))
    normals=[];tangents=[]
    for face in faces:
        a,b,c=(vertices[i] for i in face[:3]);u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);length=math.sqrt(sum(x*x for x in n))
        n=tuple(x/length for x in n) if length else (0,0,1)
        length=math.sqrt(sum(x*x for x in u));t=tuple(x/length for x in u) if length else (1,0,0)
        normals.append(n);tangents.append((*t,1))
    mesh.put('faceVertexData','CDmePolygonMeshDataArray',data_array(len(edges),[stream('texcoord:0','vector2',[e['uv'] for e in edges],1),stream('texcoord:1','vector2',[(0,0)]*len(edges),1),stream('normal:0','vector3',[normals[e['face']] if e['face']>=0 else (0,0,1) for e in edges],1),stream('tangent:0','vector4',[tangents[e['face']] if e['face']>=0 else (1,0,0,1) for e in edges],1),stream('VertexPaintBlendParams:0','vector4',[(0,0,0,0)]*len(edges),1),stream('VertexPaintTintColor:0','vector4',[(1,1,1,1)]*len(edges),1)]))
    mesh.put('edgeData','CDmePolygonMeshDataArray',data_array(len(edges)//2,[stream('flags:0','int',[0]*(len(edges)//2),3)]))
    mesh.put('faceData','CDmePolygonMeshDataArray',data_array(len(faces),[stream('materialindex:0','int',material_indices,8),stream('flags:0','int',[0]*len(faces),3),stream('textureScale:0','vector2',[(1,1)]*len(faces)),stream('textureAxisU:0','vector4',[(1,0,0,0)]*len(faces)),stream('textureAxisV:0','vector4',[(0,1,0,0)]*len(faces)),stream('lightmapScaleBias:0','int',[0]*len(faces),1)]))
    mesh.put('subdivisionData','CDmePolygonMeshSubdivisionData',element('CDmePolygonMeshSubdivisionData',subdivisionLevels=('int_array',[0]*len(edges)),streams=('element_array',[stream('texcoord:0','vector2',[]),stream('displacement:0','vector3',[])])))
    return mesh

def stream_data(mesh,array,name):
    block=mesh.get(array)
    if not isinstance(block,Element):return []
    return next((s.get('data',[]) for s in block.get('streams',[]) if s and (s.get('name')==name or s.get('semanticName','')+':'+str(s.get('semanticIndex',0))==name)),[])

def read_mesh(mesh):
    subdivision=mesh.get('subdivisionData')
    if subdivision and any(subdivision.get('subdivisionLevels',[])):
        raise ValueError('VMAP subdivision surfaces must be converted to ordinary meshes in Hammer before importing')
    positions=stream_data(mesh,'vertexData','position:0');vi=mesh.get('vertexDataIndices',list(range(len(positions))))
    vertices=[positions[i] for i in vi];ev=mesh.get('edgeVertexIndices',[]);en=mesh.get('edgeNextIndices',[])
    uvs=stream_data(mesh,'faceVertexData','texcoord:0');ei=mesh.get('edgeVertexDataIndices',list(range(len(ev))))
    indices=stream_data(mesh,'faceData','materialindex:0');fi=mesh.get('faceDataIndices',list(range(len(indices))))
    faces=[];corners=[]
    for start in mesh.get('faceEdgeIndices',[]):
        loop=[];seen=set();edge=start
        while edge not in seen:
            if edge<0 or edge>=len(ev) or edge>=len(en):raise ValueError('Invalid VMAP half-edge index')
            seen.add(edge);loop.append(edge);edge=en[edge]
        if edge!=start or len(loop)<3:raise ValueError('Invalid VMAP face loop')
        faces.append([ev[e] for e in loop]);corners.append([uvs[ei[e]] if uvs else (0,0) for e in loop])
    if any(v<0 or v>=len(vertices) for f in faces for v in f):raise ValueError('Invalid VMAP vertex reference')
    if indices and any(i<0 or i>=len(indices) for i in fi):raise ValueError('Invalid VMAP face-data reference')
    return vertices,faces,corners,mesh.get('materials',[]),[indices[i] for i in fi] if indices else [0]*len(faces)
