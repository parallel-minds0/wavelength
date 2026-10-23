"""Read actual VBSP displacement grids using Valve's CCoreDispInfo convention."""
import sys,struct,json,math
from pathlib import Path
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def scale(a,s):return tuple(x*s for x in a)
def lerp(a,b,t):return add(scale(a,1-t),scale(b,t))
def distance(a,b):return math.dist(a,b)
def read(path):
    data=Path(path).read_bytes();assert data[:4]==b'VBSP'
    def lump(index):
        offset,size,version,_=struct.unpack_from('<4i',data,8+16*index);return data[offset:offset+size]
    vertices=list(struct.iter_unpack('<3f',lump(3)));edges=list(struct.iter_unpack('<2H',lump(12)));surfedges=[x[0] for x in struct.iter_unpack('<i',lump(13))];faces=lump(7);infos=lump(26);disps=list(struct.iter_unpack('<5f',lump(33)));planes=lump(1);result=[]
    for offset in range(0,len(infos),176):
        start=struct.unpack_from('<3f',infos,offset);first=struct.unpack_from('<i',infos,offset+12)[0];power=struct.unpack_from('<i',infos,offset+20)[0];face=struct.unpack_from('<H',infos,offset+36)[0]
        firstedge=struct.unpack_from('<i',faces,face*56+4)[0];count=struct.unpack_from('<h',faces,face*56+8)[0];assert count==4
        q=[]
        for se in surfedges[firstedge:firstedge+count]:q.append(vertices[edges[abs(se)][0 if se>=0 else 1]])
        at=min(range(4),key=lambda i:distance(q[i],start));q=q[at:]+q[:at];size=2**power+1;points=[]
        for row in range(size):
            # builddisp.cpp GenerateDispSurf: outer index follows point0->1;
            # inner index interpolates from that edge towards point3->2.
            a=lerp(q[0],q[1],row/(size-1));b=lerp(q[3],q[2],row/(size-1))
            for col in range(size):
                v=disps[first+row*size+col];points.append(add(lerp(a,b,col/(size-1)),scale(v[:3],v[3])))
        neighbours=[struct.unpack_from('<H',infos,offset+48+i*6)[0] for i in range(8)]
        plane=struct.unpack_from('<H',faces,face*56)[0];normal=struct.unpack_from('<3f',planes,plane*20)
        result.append(dict(base=q,positions=points,power=power,neighbours=neighbours,index=len(result),normal=normal))
    return result
if __name__=='__main__':
    actual=read(sys.argv[1]);expected=json.loads(Path(sys.argv[2]).read_text())
    for e in expected:
        a=min(actual,key=lambda a:sum(min(distance(p,q) for q in a['base']) for p in e['base']))
        error=max(distance(p,q) for p,q in zip(a['positions'],e['positions']))
        size=round(math.sqrt(len(a['positions'])));transposed=max(distance(a['positions'][i*size+j],e['positions'][j*size+i]) for i in range(size) for j in range(size))
        print(e['name'],'compiled max error',error,'transposed',transposed,'neighbours',a['neighbours'])
        assert error<.01,(e['name'],error)
        if 'normal' in e:assert sum(x*y for x,y in zip(a['normal'],e['normal']))>.99,('compiled facing reversed',e['name'])
        e['compiled']=a
    def edges(points):
        size=round(math.sqrt(len(points)));rows=[points[i*size:(i+1)*size] for i in range(size)]
        return [rows[0],[r[-1] for r in rows],rows[-1][::-1],[r[0] for r in rows[::-1]]]
    def sample(row,t):
        x=t*(len(row)-1);lo=int(x);hi=min(len(row)-1,lo+1);return lerp(row[lo],row[hi],x-lo)
    count=0
    for index,a in enumerate(expected):
        for b in expected[index+1:]:
            for ae in range(4):
                for be in range(4):
                    if max(distance(a['base'][ae],b['base'][(be+1)%4]),distance(a['base'][(ae+1)%4],b['base'][be]))>.01:continue
                    aa=edges(a['compiled']['positions'])[ae];bb=edges(b['compiled']['positions'])[be][::-1]
                    gap=max(distance(sample(aa,i/64),sample(bb,i/64)) for i in range(65))
                    assert gap<.01,('compiled seam gap',a['name'],b['name'],gap)
                    assert b['compiled']['index'] in a['compiled']['neighbours'],('missing compiled neighbour',a['name'],b['name'])
                    assert a['compiled']['index'] in b['compiled']['neighbours']
                    count+=1
    print('PASS',count,'compiled shared edges match and have reciprocal engine neighbour links')
    print('PASS compiled Source displacement positions match evaluated Blender grids')
