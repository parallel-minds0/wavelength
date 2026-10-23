"""Bounded GoldSrc MDL v10 decoding, using installed game/mod assets directly."""
import hashlib,math,re,struct
from pathlib import Path
from .source_assets import asset_path

LIMIT=64*1024*1024

class Reader:
    def __init__(self,data):
        if len(data)>LIMIT:raise ValueError('GoldSrc model exceeds size limit')
        self.data=data
    def unpack(self,fmt,offset):
        size=struct.calcsize('<'+fmt)
        if offset<0 or offset+size>len(self.data):raise ValueError('Truncated GoldSrc model data')
        return struct.unpack_from('<'+fmt,self.data,offset)
    def integer(self,offset):return self.unpack('i',offset)[0]
    def block(self,offset,count,stride,maximum=100000):
        if count<0 or count>maximum or offset<0 or offset+count*stride>len(self.data):raise ValueError('Invalid GoldSrc model table')
        return range(offset,offset+count*stride,stride)
    def header(self):
        if len(self.data)<244 or self.data[:4]!=b'IDST' or self.integer(4)!=10:raise ValueError('Expected GoldSrc MDL version 10')
        if self.integer(72)!=len(self.data):raise ValueError('GoldSrc model length mismatch')
        return self


class Assets:
    def __init__(self,game):
        game=Path(game).expanduser().resolve()
        if not game.is_dir():raise ValueError('Configure the installed HL1/mod game directory')
        self.mounts=[];self.dependencies={};seen=set()
        def mount(folder):
            folder=folder.resolve()
            if folder in seen or not folder.is_dir():return
            seen.add(folder);self.mounts.append(folder)
            for pak in sorted(folder.glob('pak*.pak'),reverse=True):
                with pak.open('rb') as f:
                    head=f.read(12)
                    if len(head)!=12 or head[:4]!=b'PACK':raise ValueError('Invalid GoldSrc PAK header')
                    offset,size=struct.unpack_from('<ii',head,4)
                    if offset<12 or size<0 or size%64 or size>4*1024*1024 or offset+size>pak.stat().st_size:raise ValueError('Invalid GoldSrc PAK directory')
                    f.seek(offset);directory=f.read(size)
                entries={}
                for at in range(0,size,64):
                    raw,start,length=struct.unpack_from('<56sii',directory,at);name=asset_path(raw.split(b'\0')[0].decode('ascii'))
                    if start<0 or length<0 or length>LIMIT or start+length>pak.stat().st_size:raise ValueError('Invalid GoldSrc PAK entry')
                    entries[name]=(start,length)
                self.mounts.append((pak,entries))
        mount(game)
        lib=game/'liblist.gam'
        if lib.is_file():
            match=re.search(r'^\s*fallback_dir\s+"([^"\r\n]+)"',lib.read_text(errors='replace'),re.M|re.I)
            if match and re.fullmatch(r'[\w.-]+',match[1]) and match[1] not in {'.','..'}:mount(game.parent/match[1])
        mount(game.parent/'valve')
    def read(self,name):
        name=asset_path(name)
        for mount in self.mounts:
            if isinstance(mount,tuple):
                pak,entries=mount
                if name not in entries:continue
                start,length=entries[name]
                with pak.open('rb') as f:f.seek(start);data=f.read(length)
            else:
                path=mount/name
                if not path.is_file():
                    # GoldSrc names are case-insensitive, including on Linux.
                    path=mount
                    for component in name.split('/'):
                        if not path.is_dir():break
                        path=next((p for p in path.iterdir() if p.name.casefold()==component),path/component)
                if not path.is_file() or not path.resolve().is_relative_to(mount):continue
                if path.stat().st_size>LIMIT:raise ValueError('GoldSrc asset exceeds size limit')
                data=path.read_bytes()
            self.dependencies[name]=hashlib.sha256(data).hexdigest();return data
        raise ValueError('GoldSrc asset not found: '+name)


def transform(pos,angles):
    x,y,z=angles;cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    return ((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx,pos[0]),(sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx,pos[1]),(-sy,cy*sx,cy*cx,pos[2]))

def combine(a,b):return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3))+(sum(a[i][k]*b[k][3] for k in range(3))+a[i][3],) for i in range(3))
def apply(matrix,p,normal=False):return tuple(sum(row[i]*p[i] for i in range(3))+(0 if normal else row[3]) for row in matrix)


def renderable(assets,path):
    """Sequence groups and texture-only companions are dependencies, not models."""
    try:
        reader=Reader(assets.read(path)).header()
        return reader.integer(204)>0
    except (ValueError,OSError):return False

def preview_body(assets,path):
    """Use the first visible submodel when a library MDL defaults to blank gibs."""
    r=Reader(assets.read(path)).header();body=0
    for at in r.block(r.integer(208),r.integer(204),76,32):
        count,base,models=r.unpack('3i',at+64)
        for index,model in enumerate(r.block(models,count,112,256)):
            if r.integer(model+72)>0 and r.integer(model+80)>0:
                body+=index*base;break
    return body

def load(assets,path,skin=0,body=0,sequence=None):
    path=asset_path(path);r=Reader(assets.read(path)).header();bones=[]
    bone_offsets=list(r.block(r.integer(144),r.integer(140),112,128))
    # Sample frame zero of the requested sequence. Separate sequence groups are
    # read only if this pose needs them; animation playback is not imported.
    animation=None;anim_at=0
    sequences=list(r.block(r.integer(168),r.integer(164),176,4096))
    if sequences:
        if sequence is None:
            idle=next((i for i,p in enumerate(sequences) if r.unpack('32s',p)[0].lower().startswith(b'idle')),0)
            sequence=next((i for i,p in enumerate(sequences) if r.integer(p+40)==1),idle)
        if not 0<=sequence<len(sequences):raise ValueError('GoldSrc sequence index out of range')
        seq=sequences[sequence];group=r.integer(seq+156);anim_at=r.integer(seq+124)
        if group:
            groups=list(r.block(r.integer(176),r.integer(172),104,32))
            if group>=len(groups):raise ValueError('Invalid GoldSrc sequence group')
            name=r.unpack('64s',groups[group]+32)[0].split(b'\0')[0].decode(errors='replace').replace('\\','/')
            if not name.lower().startswith('models/'):name=str(Path(path).parent/Path(name).name)
            animation=Reader(assets.read(name))
            if animation.data[:4]!=b'IDSQ' or animation.integer(4)!=10:raise ValueError('Invalid GoldSrc sequence companion')
        else:animation=r
    for index,at in enumerate(bone_offsets):
        parent=r.integer(at+32);values=list(r.unpack('6f',at+64));scales=r.unpack('6f',at+88)
        if animation:
            base=anim_at+index*12
            for channel,offset in enumerate(animation.unpack('6H',base)):
                if offset:
                    valid,total=animation.unpack('2B',base+offset)
                    if not valid or valid>total:raise ValueError('Invalid GoldSrc pose animation')
                    values[channel]+=animation.unpack('h',base+offset+2)[0]*scales[channel]
        matrix=transform(values[:3],values[3:])
        if parent!=-1:
            if not 0<=parent<len(bones):raise ValueError('Invalid GoldSrc bone hierarchy')
            matrix=combine(bones[parent],matrix)
        bones.append(matrix)
    textures=r
    if not r.integer(180):textures=Reader(assets.read(path[:-4]+'t.mdl')).header()
    texture_list=[]
    for at in textures.block(textures.integer(184),textures.integer(180),80,4096):
        name=textures.unpack('64s',at)[0].split(b'\0')[0].decode(errors='replace');flags,w,h,index=textures.unpack('4i',at+64)
        if not 1<=w<=4096 or not 1<=h<=4096:raise ValueError('Invalid GoldSrc texture size')
        textures.block(index,w*h+768,1,LIMIT);indices=textures.data[index:index+w*h];palette=textures.data[index+w*h:index+w*h+768]
        rgba=bytearray(w*h*4)
        for y in range(h):
            for x in range(w):
                pixel=indices[y*w+x];dest=((h-1-y)*w+x)*4
                rgba[dest:dest+4]=palette[pixel*3:pixel*3+3]+bytes([0 if flags&0x40 and pixel==255 else 255])
        texture_list.append(dict(name=name,flags=flags,width=w,height=h,rgba=bytes(rgba)))
    refs=textures.integer(192);families=textures.integer(196)
    textures.block(textures.integer(200),refs*families,2,100000)
    if not 0<=skin<families:raise ValueError('GoldSrc skin index out of range')
    skinrefs=textures.unpack(str(refs)+'H',textures.integer(200)+skin*refs*2)
    vertices=[];normals=[];uvs=[];faces=[];slots=[]
    for at in r.block(r.integer(208),r.integer(204),76,32):
        count,base,models=r.unpack('3i',at+64)
        if count<1 or base<1:raise ValueError('Invalid GoldSrc bodygroup')
        r.block(models,count,112,256);model=models+((body//base)%count)*112
        meshes,mesh_at,nv,vbones,v_at,nn,nbones,n_at=r.unpack('8i',model+72)
        positions=[r.unpack('3f',p) for p in r.block(v_at,nv,12)];normal_data=[r.unpack('3f',p) for p in r.block(n_at,nn,12)]
        r.block(vbones,nv,1);r.block(nbones,nn,1)
        for mesh in r.block(mesh_at,meshes,20,256):
            tri_at=r.integer(mesh+4);slot=r.integer(mesh+8)
            if not 0<=slot<len(skinrefs) or skinrefs[slot]>=len(texture_list):raise ValueError('Invalid GoldSrc material reference')
            slot=skinrefs[slot];tex=texture_list[slot]
            for _ in range(100000):
                count=r.unpack('h',tri_at)[0];tri_at+=2
                if not count:break
                if not 3<=abs(count)<=20000:raise ValueError('Invalid GoldSrc triangle command')
                command=[]
                for p in r.block(tri_at,abs(count),8,20000):
                    vi,ni,u,v=r.unpack('4h',p)
                    if not 0<=vi<nv or not 0<=ni<nn:raise ValueError('Invalid GoldSrc vertex index')
                    vb=r.data[vbones+vi];nb=r.data[nbones+ni]
                    if vb>=len(bones) or nb>=len(bones):raise ValueError('Invalid GoldSrc vertex bone')
                    command.append(len(vertices));vertices.append(apply(bones[vb],positions[vi]));normals.append(apply(bones[nb],normal_data[ni],True));uvs.append((u/tex['width'],1-v/tex['height']))
                for i in range(2,len(command)):
                    face=(command[0],command[i-1],command[i]) if count<0 else ((command[i-2],command[i-1],command[i]) if i%2==0 else (command[i-1],command[i-2],command[i]))
                    faces.append(face);slots.append(slot)
                tri_at+=abs(count)*8
            else:raise ValueError('GoldSrc triangle command limit exceeded')
    if not faces:raise ValueError('GoldSrc model has no visible geometry for this body selection')
    key=hashlib.sha256(repr(sorted(assets.dependencies.items())).encode()+str((skin,body,sequence)).encode()).hexdigest()
    return dict(vertices=vertices,normals=normals,uvs=uvs,faces=faces,slots=slots,textures=texture_list,key=key)
