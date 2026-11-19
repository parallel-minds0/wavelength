"""Lossless Civ V geography edits; unknown/scenario bytes stay opaque."""
from dataclasses import dataclass
import struct
FIELDS=('terrain','resource','feature','river','elevation','continent','wonder','resource_amount')
@dataclass
class Map:
    raw:bytes
    width:int
    height:int
    offset:int
    tables:dict
    version:int
    title:str
    def tile(self,index):
        if not 0<=index<self.width*self.height:raise ValueError('Cell index outside map')
        return tuple(self.raw[self.offset+index*8:self.offset+(index+1)*8])
    def write(self,changes):
        output=bytearray(self.raw)
        for index,values in changes.items():
            self.tile(index)
            if len(values)!=8 or any(not isinstance(v,int) or not 0<=v<=255 for v in values):raise ValueError('Invalid Civ V cell record')
            for i,table in ((0,'terrain'),(1,'resource'),(2,'feature'),(6,'wonder')):
                if values[i]!=self.tile(index)[i] and values[i]!=255 and values[i]>=len(self.tables[table]):raise ValueError('Cell references an unknown '+table)
            if values[4]!=self.tile(index)[4] and values[4] not in (0,1,2):raise ValueError('Elevation must be flat, hills or mountain')
            start=self.offset+index*8;output[start:start+8]=bytes(values)
        return bytes(output)

def parse(payload):
    raw=bytes(payload)
    if len(raw)<42:raise ValueError('Truncated Civ5Map header')
    version=raw[0]&15
    if version not in {7,9,10,11,12}:raise ValueError('Unsupported experimental Civ5Map version: '+str(version))
    width,height=struct.unpack_from('<II',raw,1)
    if not width or not height:raise ValueError('Civ5Map needs nonzero dimensions')
    lengths=struct.unpack_from('<7I',raw,14);cursor=42;blocks=[]
    for size in lengths:
        if size>len(raw)-cursor:raise ValueError('Truncated Civ5Map type table')
        blocks.append(raw[cursor:cursor+size]);cursor+=size
    if version>=11:
        if len(raw)-cursor<4:raise ValueError('Truncated world-size field')
        size=struct.unpack_from('<I',raw,cursor)[0];cursor+=4
        if size>len(raw)-cursor:raise ValueError('Truncated world-size string')
        cursor+=size
    if width*height>(len(raw)-cursor)//8:raise ValueError('Truncated Civ5Map geography')
    tables={name:[p.decode('utf-8',errors='replace') for p in block.rstrip(b'\0').split(b'\0')] if block else [] for name,block in zip(('terrain','feature','wonder','resource'),blocks[:4])}
    return Map(raw,width,height,cursor,tables,version,blocks[5].rstrip(b'\0').decode('utf-8',errors='replace'))
