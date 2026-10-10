"""Structural shader classification and bounded, idempotent ELF replacements.

Unknown instructions are never stripped speculatively. Each whole NUL-delimited
string is replaced once, even when it contains both shader stages.
"""
import re,struct
from .binary_patch import digest,validate_recipe

PATCH_ID='wavelength-selected-grid'
PATCH_VERSION=1
LIMITATIONS=('Experimental native shader patch, not a certified C++ renderer bridge. '
             'Legacy yellow coloring affects all native 3D grids and native LOD remains active. '
             'The current Python workspace grid does not require this patch. '
             'Quit Blender before changing its executable; keep installer backups for removal.')
SHADER_HASHES=['7ad1248449df754961d2201e1c01072aaba5253d2990e1d3ae83d8ccf5193707','5f249016b03ebdfbe17346d104752f846e994a55c695435ba0bc99ff045bec0c']
VERTEX=b'line.P = step_offs + step_size * line.P;'
FRAGMENT=b'out_color = mix(theme.colors.grid, theme.colors.grid_emphasis, vertex_out_flat.emphasis);'
V_BLOCK=b'''if (flag_test(grid_flag, SHOW_GRID) && !flag_test(grid_flag, GRID_SIMA)) {
float wl_step = flag_test(grid_flag, GRID_ALIGNED) ? grid_buf.steps[3].x : grid_buf.steps[0].x;
float wl_q = line.P[1 - line.axis] / wl_step;
vertex_out_flat.emphasis = abs(step_size - wl_step) <= wl_step * 0.00001f && abs(wl_q - round(wl_q)) < 0.0001f ? 1.0f : -vertex_out_flat.emphasis - 1.0f;
}'''
F_CURRENT=b'out_color = !flag_test(grid_flag, GRID_SIMA) && vertex_out_flat.emphasis >= 0.0f ? float4(1.0f, 0.85f, 0.1f, theme.colors.grid.a) : mix(theme.colors.grid, theme.colors.grid_emphasis, flag_test(grid_flag, GRID_SIMA) ? vertex_out_flat.emphasis : -vertex_out_flat.emphasis - 1.0f);'
V_LEGACY=V_BLOCK.replace(b'abs(step_size - wl_step) <= wl_step * 0.00001f && ',b'')
F_LEGACY=b'out_color = mix(theme.colors.grid, float4(1.0f, 0.85f, 0.1f, theme.colors.grid.a), vertex_out_flat.emphasis);'

def _flex(value):
    tokens=re.findall(rb'[A-Za-z_]\w*|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fu]?|[^\s]',value)
    return re.compile(rb'\s*'.join(re.escape(t) for t in tokens))


def _elf(data):
    if data[8:11] in (b'AI\x01',b'AI\x02'):raise ValueError('AppImage container requires extraction before shader analysis')
    if len(data)<64 or data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=62:raise ValueError('Native shader support requires a Linux x86-64 ELF payload')
    for offset,count,size in ((struct.unpack_from('<Q',data,32)[0],struct.unpack_from('<H',data,56)[0],struct.unpack_from('<H',data,54)[0]),(struct.unpack_from('<Q',data,40)[0],struct.unpack_from('<H',data,60)[0],struct.unpack_from('<H',data,58)[0])):
        if not count or not size or offset<64 or offset+count*size>len(data):raise ValueError('Malformed ELF tables')


def _region(text,kind):
    markers=list(re.finditer(rb'(VERTEX|FRAGMENT)_SHADER_CREATE_INFO\s*\(\s*overlay_grid_next\s*\)',text))
    matching=[m for m in markers if m[1].decode().lower()==kind]
    if not markers:return 0,len(text)
    if len(matching)!=1:raise ValueError('Ambiguous shader identity')
    start=matching[0].start();end=next((m.start() for m in markers if m.start()>start),len(text))
    return start,end


def classify(text,kind):
    start,end=_region(text,kind);part=text[start:end]
    current=V_BLOCK if kind=='vertex' else F_CURRENT
    legacy=V_LEGACY if kind=='vertex' else F_LEGACY
    anchor=VERTEX if kind=='vertex' else FRAGMENT
    for state,block in (('CURRENT',current),('LEGACY',legacy)):
        hits=list(_flex(block).finditer(part))
        if len(hits)==1:
            clean=part[:hits[0].start()]+part[hits[0].end():]
            if re.search(rb'\bwl_\w+',clean) or (kind=='fragment' and re.search(rb'out_color\s*=\s*[^;]*0\.85',clean)):return 'UNKNOWN'
            if kind=='vertex' and len(list(_flex(VERTEX).finditer(clean)))!=1:return 'UNKNOWN'
            return state
        if hits:return 'UNKNOWN'
    # Fragment markers are scoped to the fragment body/output statement; vertex
    # wl_step never contaminates classification of a combined source string.
    marker=rb'\bwl_\w+' if kind=='vertex' else rb'out_color\s*=[^;]*(?:\bwl_\w+|0\.85f?)'
    if re.search(marker,part) or len(list(_flex(anchor).finditer(part)))!=1:return 'UNKNOWN'
    return 'ORIGINAL'


def revert(text,kind):
    state=classify(text,kind)
    if state=='UNKNOWN':raise ValueError('Unrecognized or ambiguous shader edits; refusing repair')
    if state=='ORIGINAL':return text
    a,b=_region(text,kind);part=text[a:b]
    block=(V_BLOCK if state=='CURRENT' else V_LEGACY) if kind=='vertex' else (F_CURRENT if state=='CURRENT' else F_LEGACY)
    part=_flex(block).sub(b'' if kind=='vertex' else FRAGMENT,part,count=1)
    return text[:a]+part+text[b:]


def _legacy_normalize(text):
    text=re.sub(rb'^#line[^\n]*\n',b'',text,flags=re.M)
    text=re.sub(rb'^[ \t]+',b'',text,flags=re.M)
    return re.sub(rb'\n\s*\n',b'\n',text).rstrip()


def _fit(text,size):
    candidates=(text.rstrip(),_legacy_normalize(text))
    for candidate in candidates:
        if len(candidate)<=size:return candidate+b' '*(size-len(candidate))
    # Only remove comments/indentation, never merge identifiers or preprocessor lines.
    candidate=re.sub(rb'/\*.*?\*/',b' ',candidates[-1],flags=re.S)
    candidate=re.sub(rb'//[^\n]*',b'',candidate)
    candidate=re.sub(rb'[ \t]+',b' ',candidate)
    if len(candidate)>size:raise ValueError('Insufficient capacity in embedded shader string')
    return candidate+b' '*(size-len(candidate))


def analyze(data):
    result={'patch_id':PATCH_ID,'patch_version':PATCH_VERSION,'state':'incompatible','action':'unavailable','reason':'','diagnostics':{}}
    try:
        _elf(data);ranges={};states={}
        for index,kind in enumerate(('vertex','fragment')):
            marker=re.compile(kind.upper().encode()+rb'_SHADER_CREATE_INFO\s*\(\s*overlay_grid_next\s*\)')
            hits=list(marker.finditer(data))
            if not hits:
                # Compatibility for exact legacy complete-string fingerprints.
                anchor=VERTEX if kind=='vertex' else FRAGMENT
                hits=list(_flex(anchor).finditer(data))
                hits=[m for m in hits if digest(data[data.rfind(b'\0',0,m.start())+1:data.find(b'\0',m.end())])==SHADER_HASHES[index]]
            spans=set()
            for hit in hits:
                a=data.rfind(b'\0',0,hit.start())+1;b=data.find(b'\0',hit.end())
                if b<0:raise ValueError('Unterminated shader source')
                spans.add((a,b))
            if len(hits)!=1 or len(spans)!=1:raise ValueError(f'{kind}: expected one shader identity, found {len(hits)}')
            span=spans.pop();ranges[kind]=span;states[kind]=classify(data[span[0]:span[1]],kind)
        result['diagnostics']=states
        if 'UNKNOWN' in states.values():raise ValueError('Unknown shader instructions or partial edit cannot be safely reconstructed')
        if all(s=='CURRENT' for s in states.values()):
            result.update(state='patched',action='keep',reason='Both current shader stages are already present',changes=[]);return result
        working={span:data[span[0]:span[1]] for span in ranges.values()}
        for kind,span in ranges.items():
            if states[kind]=='CURRENT':continue
            text=revert(working[span],kind);a,b=_region(text,kind);part=text[a:b]
            anchor=VERTEX if kind=='vertex' else FRAGMENT
            replacement=VERTEX+b'\n'+V_BLOCK if kind=='vertex' else F_CURRENT
            part=_flex(anchor).sub(lambda m:replacement,part,count=1)
            working[span]=text[:a]+part+text[b:]
        changes=[]
        for (a,b),text in working.items():
            after=_fit(text,b-a);before=data[a:b]
            if after!=before:changes.append({'offset':a,'before':before.hex(),'after':after.hex()})
        result.update(state='pristine' if all(s=='ORIGINAL' for s in states.values()) else 'partial',action='patch' if all(s=='ORIGINAL' for s in states.values()) else 'repair',reason='Recognized bounded shader replacement',changes=changes)
    except (ValueError,struct.error) as exc:result.update(state='incompatible',action='unavailable',reason=str(exc))
    return result


def build_recipe(data,analysis=None):
    analysis=analysis or analyze(data)
    if analysis['action']=='unavailable':raise ValueError(analysis['reason'])
    if analysis['action']=='keep':return None,data
    result=bytearray(data)
    for change in analysis['changes']:
        at=change['offset'];after=bytes.fromhex(change['after']);result[at:at+len(after)]=after
    recipe={'schema':1,'verified':False,'experimental':True,'input_sha256':digest(data),'output_sha256':digest(result),'changes':analysis['changes'],'patch_id':PATCH_ID,'patch_version':PATCH_VERSION,'limitations':LIMITATIONS,'native_component':'embedded-grid-shader-prototype'}
    return recipe,validate_recipe(recipe,data,allow_unverified=True)


def generate(data):return build_recipe(data)


def revert_binary(data):
    """Remove recognized shader edits without shifting ELF offsets.

    This restores shader behavior, not the original file's formatting/hash.
    """
    inspection=analyze(data)
    if inspection['action']=='unavailable':raise ValueError(inspection['reason'])
    if inspection['state']=='pristine':return data
    spans={}
    for kind in ('vertex','fragment'):
        marker=re.compile(kind.upper().encode()+rb'_SHADER_CREATE_INFO\s*\(\s*overlay_grid_next\s*\)')
        hits=list(marker.finditer(data))
        if len(hits)!=1:raise ValueError('Cannot uniquely locate shader for structural removal')
        hit=hits[0];start=data.rfind(b'\0',0,hit.start())+1;end=data.find(b'\0',hit.end())
        spans.setdefault((start,end),[]).append(kind)
    result=bytearray(data)
    for (start,end),kinds in spans.items():
        text=data[start:end]
        for kind in kinds:text=revert(text,kind)
        result[start:end]=_fit(text,end-start)
    result=bytes(result)
    if len(result)!=len(data) or analyze(result)['state']!='pristine':
        raise ValueError('Structural removal did not produce pristine shader state')
    return result
