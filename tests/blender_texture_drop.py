"""Real dependency graph: plain/unselected meshes and a brush's first drop."""
import sys,json
from pathlib import Path
from unittest.mock import patch
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import profile_ui,textures,workspace,external_library as library,asset_browser,scene
wavelength.register()
profile=next(p for p in profile_ui.store().all() if p['settings']['engine']=='source_hl2_windows')
with patch.object(textures,'refresh'):profile_ui.apply(bpy.context,profile)
_,root=library.cache_root(library.snapshot(bpy.context.scene.wavelength))
def load(link=False):
    with bpy.data.libraries.load(str(next(root.glob('textures-*.blend'))),link=link) as (available,requested):
        requested.materials=[available.materials[0]]
    return requested.materials[0]
with patch.object(workspace,'active',return_value=True):
    plain=bpy.context.object
    plain.select_set(False)
    original=[tuple(x.uv) for x in plain.data.uv_layers.active.data]
    mat=load();plain.data.materials.clear();plain.data.materials.append(mat)
    plain.update_tag();bpy.context.view_layer.update()
    assert mat.get('wl_realized'),'Ordinary unselected mesh kept a placeholder shader'
    assert [tuple(x.uv) for x in plain.data.uv_layers['wavelength'].data]==original
    assert any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes)
    bpy.ops.mesh.primitive_cube_add()
    brush=bpy.context.object;scene.mark_brush(brush)
    asset_browser._BRUSH_MAT_SIGS.pop(brush.as_pointer(),None)
    mat=load();brush.data.materials.append(mat);brush.update_tag();bpy.context.view_layer.update()
    assert mat.get('wl_realized')
    assert brush.data.uv_layers.get('wavelength'),'First brush drop skipped UV setup'
    records=json.loads(brush.data['wl_faces'])
    assert all(r['texture']==mat['wl_texture'] for r in records.values())
    # A plain mesh with no UVs receives non-degenerate projection coordinates.
    bpy.ops.mesh.primitive_cube_add();bare=bpy.context.object
    for layer in list(bare.data.uv_layers):bare.data.uv_layers.remove(layer)
    bare.data.materials.append(load());bare.update_tag();bpy.context.view_layer.update()
    assert len({tuple(x.uv) for x in bare.data.uv_layers['wavelength'].data})>1
    bpy.ops.mesh.primitive_cube_add();linked_target=bpy.context.object
    linked=load(link=True);assert linked.library
    linked_target.data.materials.append(linked);linked_target.update_tag(refresh={'OBJECT'});bpy.context.view_layer.update()
    fixed=linked_target.material_slots[0].material
    assert not fixed.library and fixed.get('wl_realized'),'Linked drop kept read-only placeholder'
wavelength.unregister();wavelength.register();wavelength.unregister()
print('PASS REAL MATERIAL DROPS: ordinary/unselected meshes, first brush UV and face records, UV-less mesh, reload')
