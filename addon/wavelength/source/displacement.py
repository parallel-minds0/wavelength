"""Source displacement data and geometry, independent of Blender.

Rows follow Valve's start-corner ordering: columns run along corner 0 -> 3,
rows along 0 -> 1 in Source's clockwise winding (CCW in our mesh adapter).
"""
import copy,math
from .geometry import number,sub,dot,cross,length

WIDTHS={'normals':3,'distances':1,'offsets':3,'offset_normals':3,'alphas':1,
        'multiblend':4,'alphablend':4,**{'multiblend_color_'+str(i):3 for i in range(4)}}


def numbers(text,count=None,integer=False):
    parts=str(text).strip().strip('[]').split()
    try:values=[float(x) for x in parts]
    except ValueError as exc:raise ValueError('Invalid displacement number') from exc
    if count is not None and len(values)!=count:raise ValueError('Invalid displacement row length')
    if not all(math.isfinite(x) for x in values):raise ValueError('Displacement contains non-finite data')
    if integer and any(x!=int(x) for x in values):raise ValueError('Displacement requires integer values')
    return [int(x) for x in values] if integer else values


def parse(pairs):
    scalars={k:v for k,v in pairs if isinstance(v,str)}
    power=numbers(scalars.get('power','4'),1,True)[0]
    if power not in (2,3,4):raise ValueError('Source displacement power must be 2, 3 or 4')
    size=2**power+1
    info={'power':power,'startposition':numbers(scalars.get('startposition',''),3),
          'flags':numbers(scalars.get('flags','0'),1,True)[0],
          'elevation':numbers(scalars.get('elevation','0'),1)[0],
          'subdiv':numbers(scalars.get('subdiv','0'),1,True)[0], '_raw':copy.deepcopy(pairs)}
    if info['subdiv'] not in (0,1):raise ValueError('Invalid displacement subdivision flag')
    if not -(2**31)<=info['flags']<2**32:raise ValueError('Displacement flags exceed 32 bits')
    blocks={k:v for k,v in pairs if not isinstance(v,str)}
    for key,width in WIDTHS.items():
        if key not in blocks:
            if key in ('normals','distances'):raise ValueError('Displacement is missing '+key)
            continue
        rows=dict(blocks[key])
        if len(rows)!=size or set(rows)!={'row'+str(i) for i in range(size)}:
            raise ValueError('Invalid displacement '+key+' row count')
        info[key]=[numbers(rows['row'+str(i)],size*width) for i in range(size)]
    if 'triangle_tags' in blocks:
        rows=dict(blocks['triangle_tags'])
        if rows and set(rows)!={'row'+str(i) for i in range(size-1)}:raise ValueError('Invalid displacement triangle tag rows')
        info['triangle_tags']=[numbers(rows['row'+str(i)],2*(size-1),True) for i in range(size-1)] if rows else []
        if any(not 0<=v<=65535 for row in info['triangle_tags'] for v in row):raise ValueError('Displacement triangle flags exceed 16 bits')
    if 'allowed_verts' in blocks:
        values=blocks['allowed_verts']
        if len(values)!=1 or values[0][0]!='10':raise ValueError('Invalid displacement allowed-vertex mask')
        info['allowed_verts']=numbers(values[0][1],10,True)
        if any(not -(2**31)<=v<2**32 for v in info['allowed_verts']):raise ValueError('Displacement allowed-vertex mask exceeds 32 bits')
    return info


def pairs(info):
    """Serialize known fields, retaining unknown extension fields and blocks."""
    power=info['power']
    if power not in (2,3,4):raise ValueError('Source displacement power must be 2, 3 or 4')
    size=2**power+1
    known={'power':str(power),'startposition':'['+' '.join(number(x) for x in info['startposition'])+']',
           'flags':str(int(info.get('flags',0))),'elevation':number(info.get('elevation',0)),
           'subdiv':str(int(info.get('subdiv',0)))}
    for key,width in WIDTHS.items():
        rows=info.get(key)
        if rows is None:
            if key not in ('normals','distances','offsets','offset_normals','alphas'):continue
            rows=[([0,0,1]*size if key=='offset_normals' else [0]*(size*width)) for _ in range(size)]
        if len(rows)!=size or any(len(row)!=size*width for row in rows):raise ValueError('Invalid displacement '+key+' grid')
        known[key]=[('row'+str(i),' '.join(number(x) for x in row)) for i,row in enumerate(rows)]
    tags=info.get('triangle_tags',[[9]*(2*(size-1)) for _ in range(size-1)])
    if tags and (len(tags)!=size-1 or any(len(row)!=2*(size-1) for row in tags)):raise ValueError('Invalid displacement triangle tags')
    known['triangle_tags']=[('row'+str(i),' '.join(str(int(x)) for x in row)) for i,row in enumerate(tags)]
    allowed=info.get('allowed_verts',[-1]*10)
    if len(allowed)!=10:raise ValueError('Invalid displacement allowed-vertex mask')
    known['allowed_verts']=[('10',' '.join(str(int(x)) for x in allowed))]
    # Do not introduce optional grids omitted by the source file on a round trip.
    original=info.get('_raw');result=[];used=set()
    if original is not None:
        for key,value in original:
            result.append((key,known.get(key,copy.deepcopy(value))));used.add(key)
        for key in ('normals','distances'):
            if key not in used:result.append((key,known[key]))
    else:result=list(known.items())
    parse(result)  # Shared validation applies to generated and imported data.
    return result


def quad(vertices,polygon,start):
    if len(polygon)!=4:raise ValueError('Source displacement must belong to a four-sided brush face')
    points=[tuple(vertices[i]) for i in polygon]
    index=min(range(4),key=lambda i:length(sub(points[i],start)))
    if length(sub(points[index],start))>.1:raise ValueError('Displacement start position is not a face corner')
    return points[index:]+points[:index]


def base(quad,u,v):
    return tuple(quad[0][i]*(1-u)*(1-v)+quad[1][i]*u*(1-v)+quad[2][i]*u*v+quad[3][i]*(1-u)*v for i in range(3))


def grid(info,quad,normal):
    size=2**info['power']+1;result=[]
    for j in range(size):
        for i in range(size):
            p=base(quad,i/(size-1),j/(size-1));offset=info.get('offsets')
            result.append(tuple(p[k]+normal[k]*info.get('elevation',0)+
                (offset[j][i*3+k] if offset else 0)+info['normals'][j][i*3+k]*info['distances'][j][i] for k in range(3)))
    return result


def triangles(size):
    """Valve's alternating diagonals, with outward Blender winding."""
    result=[]
    for j in range(size-1):
        for i in range(size-1):
            a=j*size+i;b=a+1;c=a+size;d=c+1
            result.extend(((a,b,c),(b,d,c)) if a%2 else ((a,d,c),(a,b,d)))
    return result


def topology(size):
    return [(j*size+i,j*size+i+1,(j+1)*size+i+1,(j+1)*size+i) for j in range(size-1) for i in range(size-1)]
