"""Bounded classic/Valve 220 MAP reader and deterministic writer."""
from dataclasses import dataclass, field
import math
import re
from .geometry import BrushError, cross, sub, dot, length, from_planes, number

MAX_BYTES = 16 * 1024 * 1024
MAX_FACES = 64
MAX_ENTITIES = 100000
TOKEN = re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|\{[^\s{}()\[\]"\\]+|[{}()\[\]]|[^\s{}()\[\]"]+')

@dataclass
class Face:
    points: list
    texture: str
    projection: list
    axes: list | None = None
    vmf: dict | None = None

    def plane(self):
        a,b,c = self.points
        n = cross(sub(c,a),sub(b,a))
        size = length(n)
        if size < 1e-10:
            raise BrushError('DEGENERATE_FACE','Collinear plane points')
        n = tuple(x/size for x in n)
        return n,dot(n,a)

@dataclass
class Entity:
    pairs: list = field(default_factory=list)
    brushes: list = field(default_factory=list)

@dataclass
class Map:
    entities: list = field(default_factory=list)

def parse(text):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise BrushError('INPUT_LIMIT','MAP exceeds 16 MiB limit')
    tokens=[]; end=0
    for match in TOKEN.finditer(text):
        if match.start()!=end:
            raise BrushError('MAP_SYNTAX',f'Invalid token at character {end}')
        end=match.end(); token=match.group()
        if not token.isspace() and not token.startswith('//'):
            tokens.append(token)
    if end!=len(text):
        raise BrushError('MAP_SYNTAX','Unterminated quoted string')
    cursor=0
    def take(expected=None):
        nonlocal cursor
        if cursor>=len(tokens):
            raise BrushError('MAP_TRUNCATED','Unexpected end of MAP')
        value=tokens[cursor]; cursor+=1
        if expected is not None and value!=expected:
            raise BrushError('MAP_SYNTAX',f'Expected {expected}, found {value[:40]}')
        return value
    def num():
        try: value=float(take())
        except ValueError as exc: raise BrushError('MAP_NUMBER','Invalid number') from exc
        if not math.isfinite(value): raise BrushError('MAP_NUMBER','Nonfinite number')
        return value
    def string():
        token=take()
        if not token.startswith('"'): raise BrushError('MAP_SYNTAX','Expected quoted property')
        return re.sub(r'\\([\\"])',r'\1',token[1:-1])
    result=Map()
    while cursor<len(tokens):
        take('{'); entity=Entity()
        while cursor<len(tokens) and tokens[cursor]!='}':
            if tokens[cursor]=='{':
                take('{'); faces=[]
                while cursor<len(tokens) and tokens[cursor]!='}':
                    points=[]
                    for _ in range(3):
                        take('(');points.append([num(),num(),num()]);take(')')
                    texture=take(); axes=None
                    if cursor<len(tokens) and tokens[cursor]=='[':
                        axes=[]
                        for _ in range(2):
                            take('[');axes.append([num(),num(),num(),num()]);take(']')
                        projection=[0,0,num(),num(),num()]
                    else: projection=[num() for _ in range(5)]
                    if 0 in projection[3:]: raise BrushError('INVALID_PROJECTION','Zero texture scale')
                    face=Face(points,texture,projection,axes);face.plane();faces.append(face)
                    if len(faces)>MAX_FACES: raise BrushError('INPUT_LIMIT','Brush exceeds 64-face safety limit')
                take('}')
                if len(faces)<4: raise BrushError('INVALID_SOLID','Brush has fewer than four planes')
                entity.brushes.append(faces)
            else: entity.pairs.append((string(),string()))
        take('}');result.entities.append(entity)
        if len(result.entities)>MAX_ENTITIES: raise BrushError('INPUT_LIMIT','Too many entities')
    if not result.entities: raise BrushError('EMPTY_MAP','No entities')
    return result

def quoted(value):
    if any(c in str(value) for c in '\n\r\0"'):
        raise BrushError('INVALID_PROPERTY','Newlines, NUL and quotes cannot be exported')
    return '"'+str(value)+'"'

def write(document):
    lines=[]
    for entity in document.entities:
        lines.append('{')
        lines.extend(quoted(k)+' '+quoted(v) for k,v in entity.pairs)
        for brush in entity.brushes:
            lines.append('{')
            for face in brush:
                if not face.texture or any(c.isspace() or c in '()[]"}' for c in face.texture):
                    raise BrushError('INVALID_TEXTURE','Invalid texture name')
                line=' '.join('( '+' '.join(number(x) for x in p)+' )' for p in face.points)+' '+face.texture+' '
                if face.axes is None:
                    line+=' '.join(number(x) for x in face.projection)
                else:
                    line+=' '.join('[ '+' '.join(number(x) for x in axis)+' ]' for axis in face.axes)
                    line+=' '+' '.join(number(x) for x in face.projection[2:])
                lines.append(line)
            lines.append('}')
        lines.append('}')
    return '\n'.join(lines)+'\n'

def brush_mesh(faces):
    return from_planes([face.plane() for face in faces])

def quake_axes(normal, projection):
    bases=[((0,0,1),(1,0,0),(0,-1,0)),((0,0,-1),(1,0,0),(0,-1,0)),
           ((1,0,0),(0,1,0),(0,0,-1)),((-1,0,0),(0,1,0),(0,0,-1)),
           ((0,1,0),(1,0,0),(0,0,-1)),((0,-1,0),(1,0,0),(0,0,-1))]
    _,s,t=max(bases,key=lambda b:dot(normal,b[0]))
    angle=math.radians(projection[2]); c=math.cos(angle); sn=math.sin(angle)
    sv=next(i for i in range(3) if s[i]);tv=next(i for i in range(3) if t[i])
    axes=[]
    for axis,shift in ((s,projection[0]),(t,projection[1])):
        v=list(axis);v[sv]=c*axis[sv]-sn*axis[tv];v[tv]=sn*axis[sv]+c*axis[tv]
        axes.append(v+[shift])
    return axes
