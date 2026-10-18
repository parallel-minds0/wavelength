"""Thumbnail cleanup must preserve assigned, realized, and user-edited shaders."""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
from wavelength.source.asset_browser import _trim_preview_nodes,_bounded_preview

def material(name):
 m=bpy.data.materials.new(name);m['wl_texture']=name;m['wl_asset_profile']='source_hl2_windows';m['wl_realized']=False;m.use_fake_user=True;return m
unused=material('old thumbnail');assert len(unused.node_tree.nodes)==2;_trim_preview_nodes(unused);assert len(unused.node_tree.nodes)==0
assigned=material('assigned thumbnail');mesh=bpy.data.meshes.new('test');mesh.materials.append(assigned);_trim_preview_nodes(assigned);assert len(assigned.node_tree.nodes)==2
custom=material('custom shader');custom.node_tree.nodes.new('ShaderNodeMath');_trim_preview_nodes(custom);assert len(custom.node_tree.nodes)==3
realized=material('realized shader');realized['wl_realized']=True;_trim_preview_nodes(realized);assert len(realized.node_tree.nodes)==2
print('PASS THUMBNAIL CLEANUP: unused defaults freed; assigned, customized and realized shaders preserved')

preview=unused.preview_ensure();preview.image_size=(512,512);unused['wl_preview_ready']=True;assert not _bounded_preview(unused)
preview.image_size=(64,32);assert _bounded_preview(unused)
print('PASS THUMBNAIL BOUNDS: oversized saved previews will be regenerated')
