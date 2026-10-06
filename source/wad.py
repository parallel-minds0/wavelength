"""Bounded WAD2/WAD3 mip-texture and Quake PAK/BSP readers.

Independent implementation using id's published WAD/miptex/PAK structures.
No game assets or palettes are distributed with this module.
"""
from dataclasses import dataclass
from pathlib import Path
import struct

MAX_FILE = 512 * 1024 * 1024
MAX_ENTRIES = 65536
MAX_PIXELS = 2048 * 2048


def bounded(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('Archive data extends outside the file')
    return data[offset:offset + size]


def name_string(raw):
    name = raw.split(b'\0', 1)[0].decode('ascii', errors='strict')
    if not name or any(c.isspace() or c in '{}()[]"/\\;' for c in name):
        raise ValueError('Invalid texture name')
    return name


@dataclass(frozen=True)
class Texture:
    name: str
    width: int
    height: int
    blob: bytes
    wad3: bool

    def rgba(self, palette=None, maximum=None):
        offsets = struct.unpack_from('<4I', self.blob, 24)
        if self.wad3:
            start = offsets[3] + (self.width >> 3) * (self.height >> 3)
            count = struct.unpack('<H', bounded(self.blob, start, 2))[0]
            if count != 256:
                raise ValueError('WAD3 texture requires a 256-color palette')
            palette = bounded(self.blob, start + 2, 768)
        if palette is None or len(palette) != 768:
            raise ValueError('WAD2 preview requires the Quake palette (768-byte palette.lmp)')
        pixels = bounded(self.blob, offsets[0], self.width * self.height)
        ratio = min(1, maximum / max(self.width, self.height)) if maximum else 1
        w, h = max(1, round(self.width * ratio)), max(1, round(self.height * ratio))
        colors=[tuple(c/255 for c in palette[i*3:i*3+3])+(0.0 if self.wad3 and self.name.startswith('{') and i==255 else 1.0,) for i in range(256)]
        rgba = []
        # Blender image rows start at the bottom; game miptex rows start at the top.
        for y in range(h):
            sy = min(self.height - 1, int((h - 1 - y) * self.height / h))
            for x in range(w):
                index = pixels[sy * self.width + min(self.width - 1, int(x * self.width / w))]
                rgba.extend(colors[index])
        return w, h, rgba


def texture(blob, wad3):
    if len(blob) < 40:
        raise ValueError('Truncated mip texture')
    raw, w, h, *offsets = struct.unpack_from('<16s6I', blob)
    # { starts GoldSrc masked texture names and is legal inside a texture token.
    name = raw.split(b'\0', 1)[0].decode('ascii')
    if not name or len(name)>15 or any(c.isspace() or c in '()[]"/\\;' for c in name):
        raise ValueError('Invalid mip texture name')
    if w < 8 or h < 8 or w % 8 or h % 8 or w * h > MAX_PIXELS:
        raise ValueError('Invalid or oversized mip texture dimensions')
    end = 40
    for level, offset in enumerate(offsets):
        size = (w >> level) * (h >> level)
        if offset < end:
            raise ValueError('Overlapping mip levels')
        bounded(blob, offset, size); end = offset + size
    if wad3:
        count = struct.unpack('<H', bounded(blob, end, 2))[0]
        if count != 256: raise ValueError('Invalid WAD3 palette')
        bounded(blob, end + 2, 768)
        end += 770
    return Texture(name, w, h, blob[:end], wad3)


class Wad:
    def __init__(self, path):
        self.path = Path(path).resolve()
        size = self.path.stat().st_size
        if size > MAX_FILE: raise ValueError('WAD exceeds 512 MiB safety limit')
        self.entries = {}; self.kind = None
        with self.path.open('rb') as stream:
            head = stream.read(12)
            if len(head) != 12: raise ValueError('Truncated WAD header')
            self.kind, count, offset = struct.unpack('<4sii', head)
            if self.kind not in (b'WAD2', b'WAD3'): raise ValueError('Expected WAD2 or WAD3')
            if not 0 <= count <= MAX_ENTRIES or offset < 12 or offset + count*32 > size:
                raise ValueError('Invalid WAD directory')
            stream.seek(offset); directory = stream.read(count*32)
            for i in range(count):
                pos, disk, unpacked, kind, compression, _, _, raw = struct.unpack_from('<iiiBBBB16s', directory, i*32)
                if pos < 12 or disk < 0 or pos+disk > size: raise ValueError('Invalid WAD lump range')
                if kind != (67 if self.kind==b'WAD3' else 68): continue
                if compression or disk != unpacked: raise ValueError('Compressed WAD textures are not supported')
                name=raw.split(b'\0',1)[0].decode('ascii')
                if name.casefold() in self.entries: raise ValueError('Duplicate texture names within WAD')
                self.entries[name.casefold()] = (name,pos,disk)

    def get(self, name):
        entry = self.entries.get(name.casefold())
        if entry is None: raise ValueError(f'Texture {name!r} not found in {self.path.name}')
        _, offset, size = entry
        if size > MAX_PIXELS*2+4096: raise ValueError('Texture lump exceeds safety limit')
        with self.path.open('rb') as stream:
            stream.seek(offset); blob=stream.read(size)
        result=texture(blob,self.kind==b'WAD3')
        if result.name.casefold()!=name.casefold(): raise ValueError('Texture directory/header names differ')
        return result


def write_wad(textures, wad3=False):
    textures=list(textures)
    if len(textures)>MAX_ENTRIES: raise ValueError('Too many textures')
    payload=bytearray();entries=[];names=set()
    for item in textures:
        if item.wad3!=wad3: raise ValueError('Cannot mix WAD2 and WAD3 textures')
        if item.name.casefold() in names: raise ValueError('Duplicate output texture')
        names.add(item.name.casefold())
        raw=item.name.encode('ascii').ljust(16,b'\0')
        entries.append(struct.pack('<iiiBBBB16s',12+len(payload),len(item.blob),len(item.blob),67 if wad3 else 68,0,0,0,raw))
        payload.extend(item.blob)
        if len(payload)>MAX_FILE:raise ValueError('Generated WAD exceeds safety limit')
    return struct.pack('<4sii',b'WAD3' if wad3 else b'WAD2',len(entries),12+len(payload))+payload+b''.join(entries)


def pak_entries(path):
    path=Path(path)
    if path.stat().st_size>MAX_FILE:raise ValueError('PAK exceeds safety limit')
    data=path.read_bytes()
    if len(data)<12:raise ValueError('Truncated PAK')
    magic,offset,size=struct.unpack_from('<4sii',data)
    if magic!=b'PACK' or size%64 or not 0<=size//64<=MAX_ENTRIES:raise ValueError('Invalid PAK directory')
    directory=bounded(data,offset,size)
    result={}
    for i in range(0,size,64):
        raw,pos,length=struct.unpack_from('<56sii',directory,i)
        name=raw.split(b'\0',1)[0].decode('ascii')
        result[name]=bounded(data,pos,length)
    return result


def quake_library(paks):
    """Build editor textures from embedded BSP29 data; never extract archive paths."""
    files={}
    for path in paks: files.update(pak_entries(path))
    palette=files.get('gfx/palette.lmp')
    if palette is None or len(palette)!=768:raise ValueError('Quake palette not found')
    textures={};conflicts=0
    for name,data in sorted(files.items()):
        if not name.lower().endswith('.bsp'):continue
        if len(data)<124 or struct.unpack_from('<i',data)[0]!=29:continue
        offset,size=struct.unpack_from('<ii',data,4+2*8);lump=bounded(data,offset,size)
        if len(lump)<4:raise ValueError('Truncated BSP texture lump')
        count=struct.unpack_from('<i',lump)[0]
        if not 0<=count<=MAX_ENTRIES:raise ValueError('Too many BSP textures')
        offsets=struct.unpack('<'+'i'*count,bounded(lump,4,count*4))
        valid=sorted(set(o for o in offsets if o>=0))
        for index,pos in enumerate(valid):
            if pos<4+count*4:raise ValueError('Invalid BSP mip offset')
            end=valid[index+1] if index+1<len(valid) else len(lump)
            item=texture(bounded(lump,pos,end-pos),False)
            prior=textures.get(item.name.casefold())
            if prior and prior.blob!=item.blob:conflicts+=1
            else:textures[item.name.casefold()]=item
    if not textures:raise ValueError('No BSP textures found in these PAKs')
    return list(textures.values()),palette,conflicts
