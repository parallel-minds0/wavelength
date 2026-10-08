"""Installer-owned shader prototype generator; never a universal C++ injector.

Unknown executable hashes are accepted only when both complete embedded shader
sources match the researched inputs. Offsets are discovered independently.
"""
import re,struct
from .binary_patch import digest,validate_recipe

LIMITATIONS = ('Experimental GPU grid shader only; C++ per-view bridge is unfinished. '
              'Requires scene units NONE and grid subdivisions 10. Yellow grid affects '
              'all 3D views even outside engine mode. Native LOD remains active. '
              'Unknown builds may crash or render incorrectly. Quit Blender first; '
              'retain the installer state directory for removal and recovery.')
SHADER_HASHES = ['7ad1248449df754961d2201e1c01072aaba5253d2990e1d3ae83d8ccf5193707', '5f249016b03ebdfbe17346d104752f846e994a55c695435ba0bc99ff045bec0c']

def generate(data):
    if data[8:11] in (b'AI\x01',b'AI\x02'):
        raise ValueError('AppImage container must be extracted before patching its Blender ELF')
    if len(data)<64 or data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=62:
        raise ValueError('Experimental generator supports Linux x86-64 ELF Blender payloads only')
    # Validate ELF header and section/program table bounds before examining shaders.
    for offset,count,size in ((struct.unpack_from('<Q',data,32)[0],struct.unpack_from('<H',data,56)[0],struct.unpack_from('<H',data,54)[0]),
                              (struct.unpack_from('<Q',data,40)[0],struct.unpack_from('<H',data,60)[0],struct.unpack_from('<H',data,58)[0])):
        if not count or not size or offset<64 or offset+count*size>len(data):
            raise ValueError('Unsupported or malformed ELF tables')
    changes=[]
    vertex=b'line.P = step_offs + step_size * line.P;'
    fragment=b'out_color = mix(theme.colors.grid, theme.colors.grid_emphasis, vertex_out_flat.emphasis);'
    patches=[(vertex,vertex+b'''
  if (flag_test(grid_flag, SHOW_GRID) && !flag_test(grid_flag, GRID_SIMA)) {
    float wl_step = flag_test(grid_flag, GRID_ALIGNED) ? grid_buf.steps[3].x : grid_buf.steps[0].x;
    float wl_q = line.P[1 - line.axis] / wl_step;
    vertex_out_flat.emphasis = abs(step_size - wl_step) <= wl_step * 0.00001f && abs(wl_q - round(wl_q)) < 0.0001f ? 1.0f : -vertex_out_flat.emphasis - 1.0f;
  }
'''),(fragment,b'''out_color = !flag_test(grid_flag, GRID_SIMA) && vertex_out_flat.emphasis >= 0.0f ? float4(1.0f, 0.85f, 0.1f, theme.colors.grid.a) : mix(theme.colors.grid, theme.colors.grid_emphasis, flag_test(grid_flag, GRID_SIMA) ? vertex_out_flat.emphasis : -vertex_out_flat.emphasis - 1.0f);''')]
    result=bytearray(data)
    for index,(needle,replacement) in enumerate(patches):
        if data.count(needle)!=1:raise ValueError('Unsupported native grid shader: missing or ambiguous anchor. This build needs a compatible generator; force cannot safely patch it.')
        offset=data.index(needle);start=data.rfind(b'\0',0,offset)+1;end=data.index(b'\0',offset)
        before=data[start:end]
        if digest(before)!=SHADER_HASHES[index]:
            raise ValueError('Embedded grid shader differs from the researched source; no compatible experimental patch generator is available for this build')
        # Preserve the embedded string length, NUL terminator and all ELF offsets.
        after=re.sub(rb'^#line[^\n]*\n',b'',before,flags=re.M).replace(needle,replacement)
        after=re.sub(rb'^[ \t]+',b'',after,flags=re.M)
        after=re.sub(rb'\n\s*\n',b'\n',after)
        if len(after)>len(before):raise ValueError('No room in shader string')
        after+=b' '*(len(before)-len(after))
        result[start:end]=after
        changes.append({'offset':start,'before':before.hex(),'after':after.hex()})

    recipe={'schema':1,'verified':False,'experimental':True,'input_sha256':digest(data),
            'output_sha256':digest(result),'changes':changes,'limitations':LIMITATIONS,
            'native_component':'embedded-grid-shader-prototype'}
    return recipe,validate_recipe(recipe,data,allow_unverified=True)
