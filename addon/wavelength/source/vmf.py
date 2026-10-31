"""Source 1 VMF interchange, including displacements and hidden containers."""
import json,re,math
from . import formats,displacement

TOKEN=re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
OUTPUT='__vmf_output__'
EDITOR_ROOTS={'versioninfo','visgroups','viewsettings','cameras',
              'palette_plus','colorcorrection_plus','light_plus','postprocess_plus','bgimages_plus'}

def parse(text):
    tokens=[m.group() for m in TOKEN.finditer(text) if not m.group().isspace() and not m.group().startswith('//')]
    i=0
    def token():
        nonlocal i
        if i>=len(tokens):raise ValueError('Truncated VMF')
        t=tokens[i];i+=1
        # Hammer stores entity-output fields separated by literal ESC bytes.
        # VMF quoted values are not strict JSON strings; retain those bytes.
        return json.loads(t,strict=False) if t.startswith('"') else t
    def block():
        # An explicit stack supports editor nesting without a fixed depth cap or
        # consuming Python call-stack frames. Braces and values remain validated.
        nonlocal i
        stack=[[]]
        while i<len(tokens):
            if tokens[i]=='}':
                if len(stack)==1:raise ValueError('Unexpected VMF closing brace')
                i+=1;stack.pop();continue
            key=token()
            if key=='{':raise ValueError('Missing VMF key')
            if i<len(tokens) and tokens[i]=='{':
                i+=1;child=[];stack[-1].append((key,child));stack.append(child)
            else:
                if i>=len(tokens) or tokens[i]=='}':raise ValueError('Missing VMF value')
                stack[-1].append((key,token()))
        if len(stack)!=1:raise ValueError('Unclosed VMF block')
        return stack[0]
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
            d=values(v);p=numbers(d['plane'],9);u=numbers(d['uaxis'],5);w=numbers(d['vaxis'],5)
            if not u[4] or not w[4]:raise ValueError('VMF texture scale cannot be zero')
            face=formats.Face([p[n:n+3] for n in (0,3,6)],d['material'],[0,0,float(d.get('rotation',0)),u[4],w[4]],[u[:4],w[:4]])
            face.vmf={key:d[key] for key in ('lightmapscale','smoothing_groups','id') if key in d}
            for key,value in v:
                if key=='dispinfo':face.vmf['dispinfo']=displacement.parse(value)
            faces.append(face)
        if len(faces)<4:raise ValueError('VMF solid requires at least four faces')
        return faces
    def contents(items, hidden=False):
        # Hammer wraps quick-hidden solids/entities instead of adding an entity
        # key. Unwrap only this editor container; retain all ordinary validation.
        for key,value in items:
            if key=='hidden' and isinstance(value,list):
                yield from contents(value,True)
            else:
                yield key,value,hidden
    entities=[]
    for kind,pairs,entity_hidden in contents(root):
        if kind not in {'world','entity'}:
            if kind in {'cordon','cordons'} and values(pairs).get('active','0')=='0':continue
            if kind not in EDITOR_ROOTS:raise ValueError(f'Unsupported VMF root block: {kind}')
            continue
        props=[];brushes=[]
        for k,v,brush_hidden in contents(pairs):
            if isinstance(v,str):
                if k not in {'id','mapversion'}:props.append((k,v))
            elif k=='solid':
                brush=solid(v)
                if brush_hidden:
                    for face in brush:face.vmf['hidden']=True
                brushes.append(brush)
            elif k=='connections':props.extend((OUTPUT+key,value) for key,value in v)
            elif k not in {'editor','group'}:raise ValueError(f'Unsupported VMF entity block: {k}')
        if kind=='world':props=[(k,v) for k,v in props if k!='classname'];props.insert(0,('classname','worldspawn'))
        entities.append(formats.Entity(props,brushes,vmf_hidden=entity_hidden))
    if sum(dict(e.pairs).get('classname')=='worldspawn' for e in entities)!=1:raise ValueError('VMF requires exactly one world')
    return formats.Map(entities)

def write(document):
    lines=[];counter=0
    # Allocate all IDs before serializing side references (overlays/cubemaps).
    identifiers={};old_sides={}
    def allocate(item):
        nonlocal counter
        counter+=1;identifiers[id(item)]=str(counter)
    for entity in document.entities:
        allocate(entity)
        for brush in entity.brushes:
            allocate(brush)
            for face in brush:
                allocate(face)
                old=(face.vmf or {}).get('id')
                if old:old_sides.setdefault(str(old),[]).append(identifiers[id(face)])
    def remap(value):
        result=[]
        for old in str(value).split():
            targets=old_sides.get(old,[])
            if len(targets)!=1:raise ValueError('Missing or ambiguous VMF side reference '+old+'; reassign overlay/cubemap sides after duplication')
            result.append(targets[0])
        return ' '.join(result)
    def identity():
        nonlocal counter
        counter+=1;return str(counter)
    def prop(k,v):
        # Output separators must remain literal ESC, not JSON's \u001b text.
        value='"'+'\x1b'.join(json.dumps(part,ensure_ascii=False)[1:-1] for part in str(v).split('\x1b'))+'"'
        lines.append(json.dumps(str(k),ensure_ascii=False)+' '+value)
    def start(k):lines.extend([k,'{'])
    def end():lines.append('}')
    start('versioninfo');prop('editorversion',400);prop('editorbuild',0);prop('mapversion',1);prop('formatversion',100);prop('prefab',0);end()
    for entity in document.entities:
        world=dict(entity.pairs).get('classname')=='worldspawn'
        if entity.vmf_hidden and not world:start('hidden')
        start('world' if world else 'entity');prop('id',identifiers[id(entity)])
        for k,v in entity.pairs:
            if k in {'id','mapversion','wad'} or k.startswith(OUTPUT):continue
            prop(k,remap(v) if k.lower()=='sides' else v)
        outputs=[(k[len(OUTPUT):],v) for k,v in entity.pairs if k.startswith(OUTPUT)]
        if outputs:
            start('connections')
            for k,v in outputs:
                # Stock HL2 Hammer splits outputs on commas and crashes on an
                # ESC-only record (its next-field pointer becomes null). Newer
                # tools also accept commas. Convert only losslessly: an embedded
                # comma in a parameter still requires the extended ESC format.
                fields=v.split('\x1b')
                if len(fields)==5 and not any(',' in field for field in fields):
                    v=','.join(fields)
                prop(k,v)
            end()
        for brush in entity.brushes:
            hidden=any((face.vmf or {}).get('hidden') for face in brush)
            if hidden:start('hidden')
            start('solid');prop('id',identifiers[id(brush)])
            for face in brush:
                start('side');prop('id',identifiers[id(face)])
                prop('plane',' '.join('('+' '.join(formats.number(x) for x in point)+')' for point in face.points))
                name=face.texture.replace('\\','/').strip()
                if name.startswith('materials/'):name=name[10:]
                if name.lower().endswith('.vmt'):name=name[:-4]
                if not name or '..' in name.split('/'):raise ValueError('Invalid Source material path')
                prop('material',name)
                axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
                for index,key in enumerate(('uaxis','vaxis')):
                    axis=list(axes[index]);scale=face.projection[3+index]
                    magnitude=sum(x*x for x in axis[:3])**.5
                    if magnitude>1e-12:
                        # VBSP divides raw U/V directions by lightmapscale.
                        # Store texture frequency in scale, not axis length, so
                        # UV-equivalent fits do not multiply lightmap density.
                        axis[:3]=[x/magnitude for x in axis[:3]]
                        scale/=magnitude
                    def projection_number(value):
                        text=f'{value:.12f}'.rstrip('0').rstrip('.')
                        return '0' if text in {'','-0'} else text
                    prop(key,'['+' '.join(projection_number(x) for x in axis)+'] '+projection_number(scale))
                prop('rotation',formats.number(face.projection[2]))
                metadata=face.vmf or {}
                prop('lightmapscale',metadata.get('lightmapscale','16'));prop('smoothing_groups',metadata.get('smoothing_groups','0'))
                disp=metadata.get('dispinfo')
                if disp:
                    def write_pairs(items):
                        for key,value in items:
                            if isinstance(value,str):prop(key,value)
                            else:start(key);write_pairs(value);end()
                    start('dispinfo');write_pairs(displacement.pairs(disp));end()
                end()
            end()
            if hidden:end()
        end()
        if entity.vmf_hidden and not world:end()
    return '\n'.join(lines)+'\n'
