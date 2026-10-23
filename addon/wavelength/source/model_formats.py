"""Small deterministic Source model/material packaging primitives."""
import io,struct,zipfile
from .source_assets import asset_path


def vtf(width,height,pixels,normal=False):
    if not 1<=width<=4096 or not 1<=height<=4096 or len(pixels)!=width*height*4:raise ValueError('Invalid model texture dimensions')
    if width&(width-1) or height&(height-1):raise ValueError('Source model textures need power-of-two dimensions')
    head=bytearray(80);head[:4]=b'VTF\0';struct.pack_into('<3I',head,4,7,2,80)
    struct.pack_into('<HHIHH',head,16,width,height,0x100|0x200|(0x80 if normal else 0x40),1,0)
    struct.pack_into('<fI',head,48,1.,0);head[56]=1;struct.pack_into('<I',head,57,0xffffffff);struct.pack_into('<H',head,63,1)
    return bytes(head)+bytes(pixels)


def pack_bsp(data,assets):
    from .source_tools import validate_bsp
    validate_bsp(data);offset,size=struct.unpack_from('<2i',data,8+40*16)
    entries={}
    if size:
        with zipfile.ZipFile(io.BytesIO(data[offset:offset+size])) as archive:
            for info in archive.infolist():
                if info.is_dir():continue
                name=asset_path(info.filename)
                if info.file_size>128*1024*1024 or name in entries:raise ValueError('Invalid existing BSP resource archive')
                entries[name]=archive.read(info)
    for name,payload in assets.items():entries[asset_path(name)]=payload
    if sum(map(len,entries.values()))>512*1024*1024:raise ValueError('Model package exceeds 512 MiB')
    output=io.BytesIO()
    # Source's BSP filesystem expects stored entries (or branch-specific LZMA),
    # not ordinary ZIP Deflate. A generic ZIP reader masks this incompatibility.
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,payload in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED;archive.writestr(info,payload)
    base=data[:offset] if size and offset+size==len(data) else data
    base=bytearray(base+b'\0'*((-len(base))%4));new_offset=len(base);payload=output.getvalue();base.extend(payload)
    struct.pack_into('<2i',base,8+40*16,new_offset,len(payload));validate_bsp(base)
    return bytes(base)


def quote(value):
    value=str(value)
    if any(c in value for c in ('"','\n','\r','\0')):raise ValueError('Unsupported quote/newline in model name or path')
    return '"'+value.replace('\\','/')+'"'


