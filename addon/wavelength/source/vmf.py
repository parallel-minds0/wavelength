"""Source 1 VMF brush/point/brush-entity interchange. No displacement conversion."""
import json,re,math
from . import formats

TOKEN=re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
OUTPUT='__vmf_output__'

def parse(text):
    if len(text.encode())>formats.MAX_BYTES:raise ValueError('VMF exceeds size limit')
    tokens=[m.group() for m in TOKEN.finditer(text) if not m.group().isspace() and not m.group().startswith('//')]
    i=0
    def token():
        nonlocal i
        if i>=len(tokens):raise ValueError('Truncated VMF')
        t=tokens[i];i+=1
        return json.loads(t) if t.startswith('"') else t
    def block(depth=0):
        nonlocal i
        if depth>64:raise ValueError('VMF nesting limit')
        result=[]
        while i<len(tokens):
            if tokens[i]=='}':
                if depth==0:raise ValueError('Unexpected VMF closing brace')
                i+=1;return result
            k=token()
            if k=='{':raise ValueError('Missing VMF key')
            if i<len(tokens) and tokens[i]=='{':i+=1;v=block(depth+1)
            else:v=token()
            result.append((k,v))
        if depth:raise ValueError('Unclosed VMF block')
        return result
    root=block()
    if i!=len(tokens):raise ValueError('Unexpected VMF closing brace')
    def values(pairs):return {k:v for k,v in pairs if isinstance(v,str)}
    def numbers(value,count):
        found=[float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',value)]
        if len(found)!=count or not all(math.isfinite(x) for x in found):raise ValueError('Invalid VMF plane or axis')
        return found
    def solid(pairs):
        faces=[]
        for k,v in pairs:
            if k!='side':continue
            if any(key=='dispinfo' for key,_ in v):raise ValueError('Source displacements are not supported; import refused')
            d=values(v);p=numbers(d['plane'],9);u=numbers(d['uaxis'],5);w=numbers(d['vaxis'],5)
            if not u[4] or not w[4]:raise ValueError('VMF texture scale cannot be zero')
            face=formats.Face([p[n:n+3] for n in (0,3,6)],d['material'],[0,0,float(d.get('rotation',0)),u[4],w[4]],[u[:4],w[:4]])
            face.vmf={key:d[key] for key in ('lightmapscale','smoothing_groups') if key in d}
            faces.append(face)
        if not 4<=len(faces)<=formats.MAX_FACES:raise ValueError('Unsupported VMF solid face count')
        return faces
    entities=[]
    for kind,pairs in root:
        if kind not in {'world','entity'}:
            if kind=='cordons' and values(pairs).get('active','0')=='0':continue
            if kind not in {'versioninfo','visgroups','viewsettings','cameras'}:raise ValueError(f'Unsupported VMF root block: {kind}')
            continue
        props=[];brushes=[]
        for k,v in pairs:
            if isinstance(v,str):
                if k not in {'id','mapversion'}:props.append((k,v))
            elif k=='solid':brushes.append(solid(v))
            elif k=='connections':props.extend((OUTPUT+key,value) for key,value in v)
            elif k!='editor':raise ValueError(f'Unsupported VMF entity block: {k}')
        if kind=='world':props=[(k,v) for k,v in props if k!='classname'];props.insert(0,('classname','worldspawn'))
        entities.append(formats.Entity(props,brushes))
    if sum(dict(e.pairs).get('classname')=='worldspawn' for e in entities)!=1:raise ValueError('VMF requires exactly one world')
    return formats.Map(entities)

def write(document):
    lines=[];counter=0
    def identity():
        nonlocal counter
        counter+=1;return str(counter)
    def prop(k,v):lines.append(json.dumps(str(k),ensure_ascii=False)+' '+json.dumps(str(v),ensure_ascii=False))
    def start(k):lines.extend([k,'{'])
    def end():lines.append('}')
    start('versioninfo');prop('editorversion',400);prop('editorbuild',0);prop('mapversion',1);prop('formatversion',100);prop('prefab',0);end()
    for entity in document.entities:
        world=dict(entity.pairs).get('classname')=='worldspawn'
        start('world' if world else 'entity');prop('id',identity())
        for k,v in entity.pairs:
            if k in {'id','mapversion','wad'} or k.startswith(OUTPUT):continue
            prop(k,v)
        outputs=[(k[len(OUTPUT):],v) for k,v in entity.pairs if k.startswith(OUTPUT)]
        if outputs:
            start('connections')
            for k,v in outputs:prop(k,v)
            end()
        for brush in entity.brushes:
            start('solid');prop('id',identity())
            for face in brush:
                start('side');prop('id',identity())
                prop('plane',' '.join('('+' '.join(formats.number(x) for x in point)+')' for point in face.points))
                name=face.texture.replace('\\','/').strip()
                if name.startswith('materials/'):name=name[10:]
                if name.lower().endswith('.vmt'):name=name[:-4]
                if not name or '..' in name.split('/'):raise ValueError('Invalid Source material path')
                prop('material',name)
                axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
                for index,key in enumerate(('uaxis','vaxis')):
                    prop(key,'['+' '.join(formats.number(x) for x in axes[index])+'] '+formats.number(face.projection[3+index]))
                prop('rotation',formats.number(face.projection[2]))
                metadata=face.vmf or {}
                prop('lightmapscale',metadata.get('lightmapscale','16'));prop('smoothing_groups',metadata.get('smoothing_groups','0'));end()
            end()
        end()
    return '\n'.join(lines)+'\n'
