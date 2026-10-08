#!/usr/bin/env python3
"""Experimental native-shader patch for one exact Blender payload; outputs a copy.

This tests the grid mechanism, not the future C++ per-view state bridge. Do not
add its recipe to the production support manifest based on a screenshot alone.
"""
import argparse,hashlib,json,re,shutil
from pathlib import Path

EXPECTED='4b98e176544d587178ed9d4a0b29d41506b5c797fbdf4da77c0314f2061a944b'

def digest(data):return hashlib.sha256(data).hexdigest()

def patch(source,destination):
    data=source.read_bytes()
    if digest(data)!=EXPECTED:raise ValueError('Unsupported exact Blender executable')
    if destination.exists():raise FileExistsError(destination)
    changes=[]
    vertex=b'line.P = step_offs + step_size * line.P;'
    fragment=b'out_color = mix(theme.colors.grid, theme.colors.grid_emphasis, vertex_out_flat.emphasis);'
    patches=[(vertex,vertex+b'''
  if (flag_test(grid_flag, SHOW_GRID) && !flag_test(grid_flag, GRID_SIMA)) {
    float wl_step = flag_test(grid_flag, GRID_ALIGNED) ? grid_buf.steps[3].x : grid_buf.steps[0].x;
    float wl_q = line.P[1 - line.axis] / wl_step;
    vertex_out_flat.emphasis = abs(wl_q - round(wl_q)) < 0.0001f ? 1.0f : 0.0f;
  }
'''),(fragment,b'''out_color = mix(theme.colors.grid,
    flag_test(grid_flag, GRID_SIMA) ? theme.colors.grid_emphasis : float4(1.0f, 0.85f, 0.1f, theme.colors.grid.a),
    vertex_out_flat.emphasis);''')]
    result=bytearray(data)
    for needle,replacement in patches:
        if data.count(needle)!=1:raise ValueError('Shader anchor is not unique')
        offset=data.index(needle);start=data.rfind(b'\0',0,offset)+1;end=data.index(b'\0',offset)
        before=data[start:end]
        # Preserve the embedded string length, NUL terminator and all ELF offsets.
        after=re.sub(rb'^#line[^\n]*\n',b'',before,flags=re.M).replace(needle,replacement)
        after=re.sub(rb'^[ \t]+',b'',after,flags=re.M)
        after=re.sub(rb'\n\s*\n',b'\n',after)
        if len(after)>len(before):raise ValueError('No room in shader string')
        after+=b' '*(len(before)-len(after))
        result[start:end]=after
        changes.append({'offset':start,'before':before.hex(),'after':after.hex()})
    destination.write_bytes(result);shutil.copymode(source,destination)
    recipe={'schema':1,'verified':False,'experimental':True,'input_sha256':EXPECTED,
            'output_sha256':digest(result),'changes':changes,
            'limitations':'Shader prototype; requires units NONE and subdivisions 10. No C++ state bridge. Not a production recipe.'}
    destination.with_suffix('.recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    print(destination)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();patch(a.source,a.destination)
