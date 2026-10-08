"""Read local Source VPK/VMT/VTF assets without extracting game archives."""
from pathlib import Path,PurePosixPath
from array import array
import struct,zlib,re,hashlib

LIMIT=128*1024*1024

def asset_path(name):
    value=str(name).replace('\\','/').strip().lower()
    if not value or value.startswith('/') or ':' in value or any(p in {'..','.'} for p in value.split('/')):
        raise ValueError('Invalid Source asset path')
    return value

class VPK:
    def __init__(self,path):
        self.path=Path(path);self.entries={}
        with self.path.open('rb') as f:
            head=f.read(28)
            if len(head)<12:raise ValueError('Truncated VPK header')
            magic,version,size=struct.unpack_from('<III',head)
            if magic!=0x55aa1234 or version not in (1,2) or size>LIMIT:raise ValueError('Unsupported VPK header')
            self.base=(12 if version==1 else 28)+size
            f.seek(12 if version==1 else 28);tree=f.read(size)
        if len(tree)!=size:raise ValueError('Truncated VPK tree')
        pos=0
        def string():
            nonlocal pos
            end=tree.find(b'\0',pos)
            if end<0:raise ValueError('Unterminated VPK name')
            result=tree[pos:end].decode('utf-8');pos=end+1;return result
        while True:
            ext=string()
            if not ext:break
            while True:
                directory=string()
                if not directory:break
                while True:
                    name=string()
                    if not name:break
                    if pos+18>len(tree):raise ValueError('Truncated VPK entry')
                    crc,preload,index,offset,length,end=struct.unpack_from('<IHHIIH',tree,pos);pos+=18
                    if end!=65535 or pos+preload>len(tree) or length+preload>LIMIT:raise ValueError('Invalid VPK entry')
                    data=tree[pos:pos+preload];pos+=preload
                    full=asset_path(('' if directory==' ' else directory+'/')+name+('' if ext==' ' else '.'+ext))
                    self.entries[full]=(crc,index,offset,length,data)
    def read(self,name):
        crc,index,offset,length,preload=self.entries[asset_path(name)]
        if index==0x7fff:path=self.path;offset+=self.base
        else:
            if not self.path.name.endswith('_dir.vpk'):raise ValueError('Split VPK requires _dir.vpk filename')
            path=self.path.with_name(self.path.name[:-8]+f'_{index:03d}.vpk')
        with path.open('rb') as f:f.seek(offset);data=preload+f.read(length)
        if len(data)!=len(preload)+length or zlib.crc32(data)&0xffffffff!=crc:raise ValueError('VPK entry is truncated or fails CRC')
        return data

class Assets:
    def __init__(self,game):
        self.game=Path(game).expanduser().resolve()
        if not (self.game/'gameinfo.txt').is_file():raise ValueError('Select a Source game directory containing gameinfo.txt')
        from . import keyvalues
        self.mounts=[];seen=set()
        document=keyvalues.parse((self.game/'gameinfo.txt').read_text(errors='replace'))
        paths=keyvalues.child(keyvalues.child(keyvalues.child(document,'gameinfo'),'filesystem'),'searchpaths')
        def mount(path):
            path=Path(path)
            if path.suffix.lower()=='.vpk' and not path.is_file():path=path.with_name(path.stem+'_dir.vpk')
            if not path.exists() or str(path) in seen:return
            seen.add(str(path))
            if path.is_dir():self.mounts.append(path)
            elif path.suffix.lower()=='.vpk':self.mounts.append(VPK(path))
        for kind,value in paths:
            if not isinstance(value,str) or not set(kind.lower().split('+'))&{'game','mod','platform'}:continue
            value=value.replace('\\','/')
            value=value.replace('|gameinfo_path|',str(self.game)+'/').replace('|all_source_engine_paths|',str(self.game.parent)+'/')
            path=Path(value)
            if not path.is_absolute():path=self.game.parent/path
            if '*' in str(path):
                if path.name!='*':raise ValueError('Unsupported Source search-path wildcard')
                for item in sorted(path.parent.glob('*')):
                    if item.is_dir() or item.suffix=='.vpk' and not re.search(r'_\d+\.vpk$',item.name):mount(item)
            else:mount(path)
        if not self.mounts:
            mount(self.game)
            for path in sorted(self.game.glob('*_dir.vpk')):mount(path)
    def read(self,name):
        name=asset_path(name)
        for mount in self.mounts:
            if isinstance(mount,VPK):
                if name in mount.entries:return mount.read(name)
            else:
                path=(mount/name).resolve()
                if path.is_relative_to(mount.resolve()) and path.is_file():
                    if path.stat().st_size>LIMIT:raise ValueError('Asset exceeds size limit')
                    return path.read_bytes()
        raise ValueError('Source asset not found: '+name)
    def materials(self,search=''):
        names=set()
        for mount in self.mounts:
            if isinstance(mount,VPK):items=mount.entries
            else:items=(str(p.relative_to(mount)) for p in (mount/'materials').rglob('*.vmt'))
            names.update(name[10:-4] for name in items if name.startswith('materials/') and name.endswith('.vmt') and search.lower() in name)
        return sorted(names)
    def material(self,name,seen=()):
        name=asset_path(name)
        if not name.startswith('materials/'):name='materials/'+name
        if not name.endswith('.vmt'):name+='.vmt'
        if name in seen or len(seen)>16:raise ValueError('VMT include cycle')
        text=self.read(name).decode('utf-8-sig',errors='replace')
        from . import keyvalues
        document=keyvalues.parse(text)
        if not document or not isinstance(document[0][1],list):raise ValueError('Invalid VMT shader block')
        shader,pairs=document[0];result=keyvalues.values(pairs)
        if shader.lower()=='patch':
            include=result.get('include')
            if not include:raise ValueError('Patch material is missing include')
            result=self.material(include,(*seen,name))
            for k,v in keyvalues.values(keyvalues.child(pairs,'insert')).items():result.setdefault(k,v)
            result.update(keyvalues.values(keyvalues.child(pairs,'replace')))
        return result

def image_size(w,h,fmt):
    if fmt in (13,20):return max(1,(w+3)//4)*max(1,(h+3)//4)*8
    if fmt in (14,15):return max(1,(w+3)//4)*max(1,(h+3)//4)*16
    channels={0:4,1:4,2:3,3:3,5:1,6:2,8:1,11:4,12:4,16:4}
    if fmt not in channels:raise ValueError(f'Unsupported VTF pixel format {fmt}')
    return w*h*channels[fmt]

def decode_vtf(data,max_dimension=512):
    if len(data)<64 or data[:4]!=b'VTF\0':raise ValueError('Invalid VTF header')
    major,minor,header=struct.unpack_from('<III',data,4)
    if major!=7 or minor>5 or header>len(data) or header<64:raise ValueError('Unsupported VTF version/header')
    width,height,flags,frames=struct.unpack_from('<HHIH',data,16)
    fmt=struct.unpack_from('<I',data,52)[0];mips=data[56]
    depth=struct.unpack_from('<H',data,63)[0] if minor>=2 and len(data)>=65 else 1
    if not width or not height or width*height>67108864 or not frames or not 1<=mips<=16 or depth!=1 or flags&0x4000:
        raise ValueError('Unsupported VTF dimensions, volume or cubemap')
    offset=header
    if minor>=3:
        if len(data)<80:raise ValueError('Truncated VTF resource table')
        count=struct.unpack_from('<I',data,68)[0]
        if count>32 or 80+8*count>header:raise ValueError('Invalid VTF resource count')
        offset=None
        for i in range(count):
            tag,res=struct.unpack_from('<II',data,80+8*i)
            if tag==0x30:offset=res
        if offset is None:raise ValueError('VTF has no high-resolution image resource')
    else:
        lw,lh=data[61:63]
        if lw and lh:offset+=image_size(lw,lh,struct.unpack_from('<I',data,57)[0])
    wanted=0
    while max(width>>wanted,height>>wanted)>max_dimension and wanted<mips-1:wanted+=1
    for mip in range(mips-1,wanted,-1):offset+=image_size(max(1,width>>mip),max(1,height>>mip),fmt)*frames
    w,h=max(1,width>>wanted),max(1,height>>wanted);size=image_size(w,h,fmt)
    if offset<header or offset+size>len(data):raise ValueError('Truncated VTF image')
    pixels=data[offset:offset+size];rgba=bytearray(w*h*4)
    def put(x,y,color):
        if x<w and y<h:rgba[((h-1-y)*w+x)*4:((h-1-y)*w+x)*4+4]=bytes(color)
    if fmt in (13,14,15,20):
        stride=8 if fmt in (13,20) else 16
        for by in range((h+3)//4):
            for bx in range((w+3)//4):
                off=(by*((w+3)//4)+bx)*stride;block=pixels[off:off+stride];c=0 if stride==8 else 8
                a,b,bits=struct.unpack_from('<HHI',block,c)
                def rgb(v):return ((v>>11)*255//31,((v>>5)&63)*255//63,(v&31)*255//31,255)
                colors=[rgb(a),rgb(b)]
                if a>b or stride==16:colors += [tuple((2*colors[0][j]+colors[1][j])//3 for j in range(4)),tuple((colors[0][j]+2*colors[1][j])//3 for j in range(4))]
                else:colors += [tuple((colors[0][j]+colors[1][j])//2 for j in range(4)),(0,0,0,0)]
                if fmt==15:
                    aa,bb=block[0],block[1];alphas=[aa,bb]
                    alphas += [((7-i)*aa+i*bb)//7 for i in range(1,7)] if aa>bb else [((5-i)*aa+i*bb)//5 for i in range(1,5)]+[0,255]
                    abits=int.from_bytes(block[2:8],'little')
                for i in range(16):
                    color=list(colors[(bits>>(2*i))&3])
                    if fmt==14:color[3]=((int.from_bytes(block[:8],'little')>>(4*i))&15)*17
                    elif fmt==15:color[3]=alphas[(abits>>(3*i))&7]
                    put(bx*4+i%4,by*4+i//4,color)
    else:
        channels=image_size(1,1,fmt)
        for i in range(w*h):
            p=pixels[i*channels:(i+1)*channels]
            if fmt==0:color=p
            elif fmt==1:color=(p[3],p[2],p[1],p[0])
            elif fmt==2:color=(*p,255)
            elif fmt==3:color=(p[2],p[1],p[0],255)
            elif fmt==5:color=(p[0],p[0],p[0],255)
            elif fmt==6:color=(p[0],p[0],p[0],p[1])
            elif fmt==8:color=(255,255,255,p[0])
            elif fmt==11:color=(p[1],p[2],p[3],p[0])
            else:color=(p[2],p[1],p[0],p[3] if fmt==12 else 255)
            put(i%w,i//w,color)
    return width,height,w,h,rgba

_cache={}
def library(game):
    key=str(Path(game).expanduser().resolve())
    if key not in _cache:_cache[key]=Assets(key)
    return _cache[key]

def material(settings,name):
    import bpy
    assets=library(bpy.path.abspath(settings.game_dir));name=asset_path(name)
    if name.startswith('materials/'):name=name[10:]
    if name.endswith('.vmt'):name=name[:-4]
    props=assets.material(name);base=props.get('$basetexture') or props.get('%tooltexture')
    if not base:raise ValueError('Material has no supported base/tool texture: '+name)
    base=asset_path(base)
    if not base.startswith('materials/'):base='materials/'+base
    if not base.endswith('.vtf'):base+='.vtf'
    data=assets.read(base);key='wl_source_'+hashlib.sha256((str(assets.game)+name).encode()+data).hexdigest()[:20]
    existing=bpy.data.materials.get(key)
    if existing:return existing
    width,height,w,h,rgba=decode_vtf(data)
    image=bpy.data.images.new(key,width=w,height=h,alpha=True)
    image.pixels.foreach_set(array('f',(x/255 for x in rgba)));image.update();image.pack()
    mat=bpy.data.materials.new(key);mat.use_nodes=True
    mat['wl_texture']=name;mat['wl_width']=width;mat['wl_height']=height
    mat['wl_asset_origin']='User-installed Source game; private preview'
    nodes=mat.node_tree.nodes;shader=nodes.get('Principled BSDF');tex=nodes.new('ShaderNodeTexImage');tex.image=image
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='wavelength';mat.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector'])
    mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=1
    if props.get('$translucent')=='1' or props.get('$alphatest')=='1':mat.node_tree.links.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
    return mat
