"""Bounded Source 1 MDL44–49 + VVD4 + VTX7 reference-pose mesh reader.

Layout reference: Valve source-sdk-2013 public/studio.h and optimize.h.
No game data or third-party importer code is bundled.
"""
import math,struct

LIMIT=2_000_000


class Reader:
    def __init__(self,data):self.data=data
    def get(self,fmt,offset):
        size=struct.calcsize('<'+fmt)
        if offset<0 or offset+size>len(self.data):raise ValueError('Truncated Source model data')
        return struct.unpack_from('<'+fmt,self.data,offset)
    def integer(self,offset):return self.get('i',offset)[0]
    def array(self,offset,count,stride):
        if count<0 or count>LIMIT or offset<0 or offset+count*stride>len(self.data):raise ValueError('Invalid Source model table bounds')
        return range(offset,offset+count*stride,stride)
    def string(self,offset):
        if not 0<=offset<len(self.data):raise ValueError('Invalid Source model string offset')
        end=self.data.find(b'\0',offset,min(len(self.data),offset+4096))
        if end<0:raise ValueError('Unterminated Source model string')
        return self.data[offset:end].decode('utf-8',errors='replace')


def renderable(assets,path):
    """Animation-only MDLs are dependencies, not standalone render models."""
    try:
        data=assets.read(path);reader=Reader(data)
        return data[:4]==b'IDST' and 44<=reader.integer(4)<=49 and reader.integer(232)>0
    except (OSError,ValueError):return False

def read(mdl,vvd,vtx,skin=0,body=0):
    m,d,t=Reader(mdl),Reader(vvd),Reader(vtx)
    if mdl[:4]!=b'IDST' or not 44<=m.integer(4)<=49:raise ValueError('Supported Source model versions are 44–49 (HL2/GMod); this is not a compatible MDL')
    if m.integer(76)!=len(mdl):raise ValueError('Truncated MDL file length')
    checksum=m.integer(8)
    if vvd[:4]!=b'IDSV' or d.integer(4)!=4:raise ValueError('Unsupported VVD vertex file')
    if t.integer(0)!=7:raise ValueError('Unsupported VTX triangle file')
    if checksum!=d.integer(8) or checksum!=t.integer(16):raise ValueError('MDL/VVD/VTX checksums differ; use companions from the same model build')
    if not 1<=d.integer(12)<=8 or t.integer(20)<1:raise ValueError('Invalid model LOD count')
    count=d.integer(16);start=d.integer(56);fixcount,fixstart=d.get('2i',48)
    ids=[]
    for offset in d.array(fixstart,fixcount,12):
        lod,first,n=d.get('3i',offset)
        if lod<0 or first<0 or n<0 or len(ids)+n>LIMIT:raise ValueError('Invalid VVD fixup')
        d.array(start+first*48,n,48);ids.extend(range(first,first+n))
    if not fixcount:ids=list(range(len(d.array(start,count,48))))
    if len(ids)!=count:raise ValueError('VVD fixup count does not match LOD zero')
    vertices=[];normals=[];uvs=[]
    for index in ids:
        values=d.get('8f',start+index*48+16)
        if not all(math.isfinite(x) for x in values):raise ValueError('Non-finite model vertex')
        vertices.append(values[:3]);normals.append(values[3:6]);uvs.append((values[6],1-values[7]))
    numtex,texstart,numdirs,dirstart,numrefs,numskins,skinstart,numbodies,bodystart=m.get('9i',204)
    m.array(skinstart,numrefs*numskins,2)
    if numrefs<0 or numskins<0:raise ValueError('Invalid skin table')
    materials=[m.string(p+m.integer(p)) for p in m.array(texstart,numtex,64)]
    directories=[m.string(m.integer(p)) for p in m.array(dirstart,numdirs,4)]
    if skin<0 or skin>=max(1,numskins) or body<0:raise ValueError('Invalid model skin/body selection')
    skinrefs=list(m.get(str(numrefs)+'H',skinstart+skin*numrefs*2)) if numrefs and numskins else list(range(numtex))
    tbodies,tbodystart=t.get('2i',28)
    if tbodies!=numbodies:raise ValueError('MDL/VTX body tables disagree')
    faces=[];slots=[]
    for bi,bp in enumerate(m.array(bodystart,numbodies,16)):
        _,models,base,modeloff=m.get('4i',bp);vp=tbodystart+bi*8;vmodels,vmodeloff=t.get('2i',vp)
        if vmodels!=models or models<1 or base<1:raise ValueError('Invalid model bodypart')
        mi=(body//base)%models;mp=bp+modeloff+mi*148;m.get('148s',mp)
        meshes,meshoff,nverts,vertexoff=m.get('4i',mp+72)
        if vertexoff<0 or vertexoff%48 or nverts<0:raise ValueError('Invalid model vertex offset')
        modelbase=vertexoff//48
        if modelbase+nverts>len(vertices):raise ValueError('Model vertex range exceeds VVD')
        vm=vp+vmodeloff+mi*8;lods,lodoff=t.get('2i',vm)
        if lods<1:raise ValueError('Model has no reference LOD')
        lp=vm+lodoff;vmeshes,vmeshoff=t.get('2i',lp)
        if meshes!=vmeshes:raise ValueError('MDL/VTX mesh tables disagree')
        for meshindex,mesh in enumerate(m.array(mp+meshoff,meshes,116)):
            mat,_,meshverts,meshbase=m.get('4i',mesh)
            if meshbase<0 or meshverts<0 or meshbase+meshverts>nverts:raise ValueError('Invalid mesh vertex range')
            if mat<0 or mat>=len(skinrefs) or skinrefs[mat]>=numtex:raise ValueError('Invalid model material index')
            vmsh=lp+vmeshoff+meshindex*9;groups,groupoff=t.get('2i',vmsh)
            for gp in t.array(vmsh+groupoff,groups,25):
                nv,vo,ni,io,ns,so=t.get('6i',gp)
                remap=[]
                for p in t.array(gp+vo,nv,9):
                    original=t.get('H',p+4)[0]
                    if original>=meshverts or meshbase+original>=nverts:raise ValueError('VTX references an invalid mesh vertex')
                    remap.append(modelbase+meshbase+original)
                indices=[t.get('H',p)[0] for p in t.array(gp+io,ni,2)]
                if any(i>=nv for i in indices):raise ValueError('VTX index exceeds strip-group vertices')
                for sp in t.array(gp+so,ns,27):
                    n,first=t.get('2i',sp);flags=t.get('B',sp+18)[0]
                    if first<0 or n<0 or first+n>ni:raise ValueError('Invalid VTX strip range')
                    seq=[remap[i] for i in indices[first:first+n]]
                    if flags&1:
                        if n%3:raise ValueError('Incomplete VTX triangle list')
                        triangles=[seq[i:i+3] for i in range(0,n,3)]
                    elif flags&2:triangles=[(seq[i+1],seq[i],seq[i+2]) if i%2 else seq[i:i+3] for i in range(n-2)]
                    else:raise ValueError('Unsupported VTX strip topology')
                    for tri in triangles:
                        # Source's clockwise front becomes Blender's CCW front.
                        if len(set(tri))==3:faces.append((tri[0],tri[2],tri[1]));slots.append(skinrefs[mat])
                        if len(faces)>LIMIT:raise ValueError('Source model exceeds triangle limit')
    if not faces:raise ValueError('Selected model body has no renderable triangles')
    used=sorted({i for f in faces for i in f});remap={old:new for new,old in enumerate(used)}
    return dict(vertices=[vertices[i] for i in used],normals=[normals[i] for i in used],uvs=[uvs[i] for i in used],faces=[tuple(remap[i] for i in f) for f in faces],slots=slots,materials=materials,directories=directories,static=bool(m.integer(152)&16),skins=max(1,numskins),checksum=checksum)


def load(assets,path,skin=0,body=0):
    from .source_assets import asset_path
    path=asset_path(path)
    if not path.startswith('models/') or not path.endswith('.mdl'):raise ValueError('Choose a models/...mdl asset from the active game')
    stem=path[:-4];mdl=assets.read(path);vvd=assets.read(stem+'.vvd')
    for suffix in ('.dx90.vtx','.dx80.vtx','.sw.vtx','.vtx'):
        try:vtx=assets.read(stem+suffix)
        except (OSError,ValueError):continue
        break
    else:raise ValueError('Model triangle companion is missing: '+stem+'.dx90.vtx')
    return read(mdl,vvd,vtx,skin,body)
