"""Verify edge alignment and trim hotspots persist as exportable brush UVs."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bmesh
import bpy
import wavelength
from wavelength.source import scene, texture_layout

wavelength.register()
context=bpy.context
context.workspace['wl_workspace']=True
settings=context.scene.wavelength
settings.auto_prepare_assets=False
settings.engine='source_hl2_windows'
settings.game_dir=''
settings.texture='dev/dev_measuregeneric01b'
obj=context.object
scene.mark_brush(obj)
mat=bpy.data.materials.new('Trim test')
mat['wl_texture']=settings.texture
mat['wl_width']=128
mat['wl_height']=64
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
context.scene.tool_settings.mesh_select_mode=(False,False,True)
bpy.ops.object.mode_set(mode='EDIT')
bm=bmesh.from_edit_mesh(obj.data)
for face in bm.faces:face.select_set(False)
source=next(face for face in bm.faces if face.normal.z>.9)
edge=source.edges[0]
destination=next(face for face in edge.link_faces if face!=source)
source.select_set(True)
destination.select_set(True)
bm.faces.active=source
layer=bm.loops.layers.uv['wavelength']
bm.faces.index_update()
bm.verts.index_update()
source_index,destination_index=source.index,destination.index
edge_indices={vertex.index for vertex in edge.verts}
reference={loop.vert.index:loop[layer].uv.copy() for loop in source.loops}
assert bpy.ops.wavelength.face_texture_layout(action='EDGE')=={'FINISHED'}
bm=bmesh.from_edit_mesh(obj.data)
bm.faces.ensure_lookup_table()
source,destination=bm.faces[source_index],bm.faces[destination_index]
layer=bm.loops.layers.uv['wavelength']
for loop in destination.loops:
    if loop.vert.index in edge_indices:
        assert (loop[layer].uv-reference[loop.vert.index]).length<1e-6
assert all(loop[layer].uv==reference[loop.vert.index] for loop in source.loops)
source.select_set(False)
bm.faces.active=destination
square=mat.wl_hotspots.add()
square.minimum=(.5,.25)
square.maximum=(.75,.75)
wide=mat.wl_hotspots.add()
wide.minimum=(0,0)
wide.maximum=(.5,.25)
assert bpy.ops.wavelength.face_texture_layout(action='HOTSPOT')=={'FINISHED'}
uvs=[tuple(loop[layer].uv) for loop in destination.loops]
assert set(uvs)=={(.5,.25),(.75,.25),(.5,.75),(.75,.75)}
ids=bm.faces.layers.int['wl_face_id']
fid=str(destination[ids])
record=json.loads(obj.data['wl_faces'])[fid]
assert record['texture']==mat['wl_texture'] and record['axes']
bpy.ops.object.mode_set(mode='OBJECT')
from wavelength.source import editor
editor.apply_uv(obj,settings.engine)
polygon=next(p for p in obj.data.polygons if str(obj.data.attributes['wl_face_id'].data[p.index].value)==fid)
assert set(tuple(obj.data.uv_layers['wavelength'].data[i].uv) for i in polygon.loop_indices)==set(uvs)
assert len(scene.brush_from_object(obj,settings.engine,require_texture=True))==6
print('PASS edge seam continuity, material hotspot aspect selection and Source projection reconstruction',flush=True)
