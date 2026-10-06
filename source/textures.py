"""Local WAD libraries, paged previews, material assignment and build texture sets."""
from . import profiles
from array import array
import hashlib
import json
from pathlib import Path
import bpy
from .wad import Wad,write_wad

_libraries={}
_previews=None
_items=[]
PAGE_SIZE=32


def library(path):
    path=Path(bpy.path.abspath(path)).resolve();stat=path.stat();key=(str(path),stat.st_mtime_ns,stat.st_size)
    if key not in _libraries:
        _libraries.clear() if len(_libraries)>32 else None
        _libraries[key]=Wad(path)
    return _libraries[key]


def sources(settings):
    paths=json.loads(settings.texture_wads)
    if not isinstance(paths,list) or not all(isinstance(x,str) for x in paths):raise ValueError('Invalid WAD source list')
    return list(dict.fromkeys([*paths,*([settings.wad_path] if settings.wad_path else [])]))


def palette(settings):
    if not settings.palette_path:return None
    data=Path(bpy.path.abspath(settings.palette_path)).read_bytes()
    if len(data)!=768:raise ValueError('Palette must contain 768 bytes')
    return data


def find(settings,name,preferred=None):
    paths=sources(settings)
    if preferred:paths=[preferred,*[p for p in paths if str(Path(bpy.path.abspath(p)).resolve())!=preferred]]
    for path in paths:
        wad=library(path)
        if name.casefold() in wad.entries:return wad,wad.get(name)
    raise ValueError(f'Texture {name!r} was not found in configured WADs')


def cache_directory(settings):
    """Return a writable cache for generated local texture previews.

    A project-local cache is preferred when a Project Directory is configured.
    Browsing installed engine assets must not require a project, however, so
    profiles fall back to Blender's per-user cache area.  Keep profile IDs in
    the path to avoid collisions between WAD2/WAD3 or future game profiles.
    """
    if settings.project_dir:
        folder=Path(bpy.path.abspath(settings.project_dir))/'.texture-cache'
    else:
        profile_id=str(getattr(settings,'engine','blender') or 'blender')
        try:
            root=bpy.utils.user_resource('CACHE',path='wavelength/texture-previews',create=True)
        except (TypeError,ValueError,OSError):
            root=''
        if root:
            folder=Path(root)/profile_id
        else:
            # Last-resort conventional user cache; never write beside the add-on
            # or into the installed Half-Life directory.
            folder=Path.home()/'.cache'/'wavelength'/'texture-previews'/profile_id
    folder.mkdir(parents=True,exist_ok=True)
    return folder


def material(settings,name,preferred=None):
    wad,item=find(settings,name,preferred)
    expected=b'WAD3' if profiles.is_goldsrc(settings.engine) else b'WAD2'
    if wad.kind!=expected:raise ValueError('Texture WAD belongs to the other engine mode')
    pal=palette(settings) if not item.wad3 else None
    key=hashlib.sha256(item.blob+(pal or b'')).hexdigest()
    label='wl_'+key[:20]
    existing=bpy.data.materials.get(label)
    if existing:
        # Keep the current source path even when an identical texture moved.
        existing['wl_wad']=str(wad.path);return existing
    w,h,rgba=item.rgba(pal)
    path=cache_directory(settings)/(key+'.png')
    image=bpy.data.images.new(label,width=w,height=h,alpha=True)
    image.colorspace_settings.name='sRGB';image.pixels.foreach_set(array('f',rgba));image.update()
    image.filepath_raw=str(path);image.file_format='PNG';image.save()
    # File-backed reference survives save/reopen without packing game assets.
    image.source='FILE'
    mat=bpy.data.materials.new(label);mat.use_nodes=True
    mat['wl_texture']=item.name;mat['wl_wad']=str(wad.path);mat['wl_width']=w;mat['wl_height']=h
    mat['wl_asset_origin']='User-installed game/WAD; local use, not bundled'
    nodes=mat.node_tree.nodes;shader=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='REPEAT'
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='wavelength'
    mat.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector'])
    mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=1
    if item.wad3 and item.name.startswith('{'):
        mat.node_tree.links.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
        if hasattr(mat,'surface_render_method'):mat.surface_render_method='DITHERED'
    return mat


def assign(obj,indices,mat):
    slot=next((i for i,m in enumerate(obj.data.materials) if m==mat),None)
    if slot is None:slot=len(obj.data.materials);obj.data.materials.append(mat)
    for index in indices:obj.data.polygons[index].material_index=slot


def refresh(settings,context=None):
    global _items,_previews
    _items=[]
    if _previews is not None:
        _previews.clear()
    if not settings.wad_path:return
    try:
        wad=library(settings.wad_path)
        names=sorted((entry[0] for entry in wad.entries.values() if settings.texture_search.casefold() in entry[0].casefold()),key=str.casefold)
        pages=max(1,(len(names)+PAGE_SIZE-1)//PAGE_SIZE)
        page=min(settings.texture_page,pages-1)
        settings.texture_count=len(names)
        pal=palette(settings) if wad.kind==b'WAD2' else None
        if not bpy.app.background and _previews is None:
            from bpy.utils import previews
            _previews=previews.new()
        for index,name in enumerate(names[page*PAGE_SIZE:(page+1)*PAGE_SIZE]):
            item=wad.get(name);icon=0
            if _previews is not None:
                w,h,pixels=item.rgba(pal,64)
                preview=_previews.new(name);preview.image_size=(w,h);preview.image_pixels_float=pixels;icon=preview.icon_id
            _items.append((name,name,f'{item.width} × {item.height} · {wad.path.name}',icon,index))
        if _items and settings.texture not in {item[0] for item in _items}:settings.texture_choice=_items[0][0]
        settings.status=f'{len(names)} textures · page {page+1}/{pages}'
    except (ValueError,OSError,UnicodeError) as exc:settings.status=str(exc)



def all_names(settings, search=''):
    """Return every texture name in the active WAD matching search, without paging."""
    if not settings.wad_path:
        return []
    wad=library(settings.wad_path)
    needle=(search or '').casefold()
    return sorted((entry[0] for entry in wad.entries.values() if needle in entry[0].casefold()),key=str.casefold)

def preview_icon(settings,name):
    """Create/reuse a preview icon lazily for the full texture browser."""
    global _previews
    if bpy.app.background or not settings.wad_path:
        return 0
    if _previews is None:
        from bpy.utils import previews
        _previews=previews.new()
    existing=_previews.get(name)
    if existing is not None:
        return existing.icon_id
    wad=library(settings.wad_path);item=wad.get(name)
    pal=palette(settings) if wad.kind==b'WAD2' else None
    w,h,pixels=item.rgba(pal,64)
    preview=_previews.new(name);preview.image_size=(w,h);preview.image_pixels_float=pixels
    return preview.icon_id


def enum_items(self,context):return _items or [('__none__','No textures','Load a WAD library',0,0)]

def select(self,context):
    if self.texture_choice!='__none__':self.texture=self.texture_choice


def build_wad(settings,document,work,objects):
    """Build a used-texture-only WAD so multiple libraries work deterministically."""
    used={face.texture.casefold():face.texture for entity in document.entities for brush in entity.brushes for face in brush}
    preferred={}
    for obj in objects:
        if obj.type!='MESH' or not obj.get('wl_role') or obj.get('wl_exclude'):continue
        for polygon in obj.data.polygons:
            if polygon.material_index>=len(obj.data.materials):continue
            mat=obj.data.materials[polygon.material_index]
            if mat and mat.get('wl_wad') and mat.get('wl_texture'):
                key=mat['wl_texture'].casefold();source=mat['wl_wad']
                if key in preferred and preferred[key]!=source:
                    if library(source).get(mat['wl_texture']).blob!=library(preferred[key]).get(mat['wl_texture']).blob:
                        raise ValueError(f'Conflicting texture {mat["wl_texture"]} from multiple WADs')
                preferred[key]=source
    result=[]
    for key,name in sorted(used.items()):
        wad,item=find(settings,name,preferred.get(key));result.append(item)
        # Compilers need the complete animation/random-tile family, not just frame 0.
        if len(name)>2 and (name[0]=='+' or (profiles.is_goldsrc(settings.engine) and name[0]=='-')):
            for entry in wad.entries.values():
                other=entry[0]
                if len(other)>2 and other[0]==name[0] and other[2:].casefold()==name[2:].casefold():
                    if other.casefold() not in {t.name.casefold() for t in result}:result.append(wad.get(other))
    path=Path(work)/'textures.wad';path.write_bytes(write_wad({t.name.casefold():t for t in result}.values(),profiles.is_goldsrc(settings.engine)))
    world=document.entities[0];world.pairs=[(k,v) for k,v in world.pairs if k not in {'wad','_wad'}]+[('wad',path.name)]
    return path


def close():
    global _previews,_items
    if _previews is not None:
        from bpy.utils import previews
        previews.remove(_previews);_previews=None
    _items=[];_libraries.clear()
