"""CS2 VMAT library: private, fingerprinted, on-demand VRF texture decoding.

Archive indexing stays pure Python. Source 2 Viewer is an external dependency,
not redistributed with the addon. Original material paths survive preview and
map export; a viewport approximation never replaces the engine's shader.
"""
import hashlib,json,os,subprocess
from pathlib import Path
from .source_assets import VPK,asset_path
from . import keyvalues

def decoder():
    path=Path(os.environ.get('WAVELENGTH_SOURCE2_VIEWER',''))
    if not path.is_file():path=Path.home()/'AppData/Local/wavelength/tools/source2viewer/Source2Viewer-CLI.exe'
    if not path.is_file():raise ValueError('Install Source2Viewer-CLI in %LOCALAPPDATA%/wavelength/tools/source2viewer or set WAVELENGTH_SOURCE2_VIEWER')
    return path

def run(args,timeout=180):
    try:result=subprocess.run([str(a) for a in args],capture_output=True,text=True,errors='replace',timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except subprocess.TimeoutExpired as exc:raise ValueError('Source 2 tool timed out; see the asset worker log') from exc
    if result.returncode:raise ValueError('Source 2 tool failed: '+(result.stdout+result.stderr)[-1800:])
    return result.stdout

class Assets:
    def __init__(self,game,content_root=None):
        self.game=Path(game).resolve()
        if not (self.game/'gameinfo.gi').is_file():raise ValueError('Select the CS2 game/csgo directory containing gameinfo.gi')
        self.mounts=[]
        if content_root:self.mounts.append(Path(content_root).resolve())
        # Addon and loose source assets override stock archives.
        content=self.game.parents[1]/'content'/self.game.name
        if content.is_dir():self.mounts.append(content)
        self.mounts.append(self.game)
        for folder in (self.game,self.game.parent/'core'):
            self.mounts.extend(VPK(p) for p in sorted(folder.glob('*_dir.vpk')) if 'shader' not in p.name)
        self.index={}
        for mount in self.mounts:
            names=mount.entries if isinstance(mount,VPK) else (p.relative_to(mount).as_posix() for p in (mount/'materials').rglob('*') if p.is_file())
            for name in names:
                if name.endswith(('.vmat_c','.vmat')):
                    canonical=asset_path(name).removesuffix('_c')
                    self.index.setdefault(canonical,(mount,name))
    def materials(self,search=''):
        return sorted(name[10:-5] for name in self.index if search.casefold() in name.casefold())
    def resolve(self,name):
        path=asset_path(name)
        if not path.startswith('materials/'):path='materials/'+path
        path=path.removesuffix('_c')
        if not path.endswith('.vmat'):path+='.vmat'
        return path
    def decoded(self,name):
        canonical=self.resolve(name)
        if canonical not in self.index:raise ValueError('CS2 material not found: '+canonical)
        mount,entry=self.index[canonical]
        source=mount.path if isinstance(mount,VPK) else mount/entry
        signature=(str(source),source.stat().st_size,source.stat().st_mtime_ns,canonical)
        key=hashlib.sha256(json.dumps(signature).encode()).hexdigest()
        root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.cache')))/'wavelength/source2-materials'/key
        output=root/'material.vmat'
        if not (root/'ready.json').is_file():
            root.mkdir(parents=True,exist_ok=True)
            if isinstance(mount,VPK):run([decoder(),'-i',mount.path,'-f',entry,'-o',output,'-d','--game',self.game/'gameinfo.gi'])
            elif entry.endswith('_c'):run([decoder(),'-i',source,'-o',output,'-d','--game',self.game/'gameinfo.gi'])
            else:output.write_bytes(source.read_bytes())
            if not output.is_file():raise ValueError('CS2 decoder did not produce a VMAT')
            (root/'ready.json').write_text(json.dumps(signature))
        props=keyvalues.values(keyvalues.child(keyvalues.parse(output.read_text(encoding='utf-8-sig')),'Layer0'))
        def texture(*keys):
            value=next((props[k.lower()] for k in keys if props.get(k.lower())),None)
            if not value:return None
            relative=asset_path(value);path=root/Path(relative).name
            if not path.is_file():
                path=source.parent/Path(relative).name if not isinstance(mount,VPK) else path
            if not path.is_file():
                for folder in self.mounts:
                    if isinstance(folder,Path) and (folder/relative).is_file():return folder/relative
                return None
            return path
        return canonical,props,{'color':texture('TextureColor','TextureLayer1Color','TextureAlbedo','TextureBaseColor'),
            'normal':texture('TextureNormal','TextureLayer1Normal'),'roughness':texture('TextureRoughness','TextureLayer1Roughness'),'metallic':texture('TextureMetalness','TextureMetallic')}

_libraries={}
def library(game,content_root=None):
    key=(str(Path(game).resolve()),str(Path(content_root).resolve()) if content_root else '')
    if key not in _libraries:_libraries[key]=Assets(game,content_root)
    return _libraries[key]

def material(settings,name,target_mat=None,preview=False,content_root=None):
    import bpy
    canonical,props,images=library(bpy.path.abspath(settings.game_dir),content_root).decoded(name)
    existing=target_mat or next((m for m in bpy.data.materials if m.get('wl_source2_material')==canonical),None)
    mat=existing or bpy.data.materials.new(canonical[10:-5]);mat.use_nodes=True
    mat['wl_source2_material']=canonical;mat['wl_texture']=canonical[10:-5];mat['wl_asset_profile']=settings.engine
    mat['wl_source2_shader']=props.get('shader','');mat['wl_realized']=not preview
    if content_root:mat['wl_source2_content_root']=str(Path(content_root).resolve())
    nodes=mat.node_tree.nodes;nodes.clear();shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=''
    loaded=[]
    for channel,path in images.items():
        if not path:continue
        image=bpy.data.images.load(str(path),check_existing=True)
        if preview:
            image=image.copy();image.scale(min(image.size[0],64),min(image.size[1],64));loaded.append(image)
        if channel!='color':image.colorspace_settings.name='Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=image
        mat.node_tree.links.new(uv.outputs['UV'],node.inputs['Vector'])
        if channel=='normal':
            normal=nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(node.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:mat.node_tree.links.new(node.outputs['Color'],shader.inputs[{'color':'Base Color','roughness':'Roughness','metallic':'Metallic'}[channel]])
        if channel=='color':
            mat['wl_width']=image.size[0];mat['wl_height']=image.size[1]
            p=mat.preview_ensure()
            thumb=image.copy();thumb.scale(64,64);p.image_size=(64,64);p.image_pixels_float=thumb.pixels[:];bpy.data.images.remove(thumb)
    if not images['color']:
        # Utility and constant-color shaders are legitimate materials too.
        tint=props.get('g_vcolortint','[0.5 0.5 0.5 1]').strip('[]').split()
        try:shader.inputs['Base Color'].default_value=tuple(float(v) for v in tint[:3])+(1,)
        except (ValueError,TypeError):shader.inputs['Base Color'].default_value=(.5,.5,.5,1)
        p=mat.preview_ensure();p.image_size=(1,1);p.image_pixels_float=shader.inputs['Base Color'].default_value
    return mat
