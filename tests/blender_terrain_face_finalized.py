import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import primitive_ui,terrain_face
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
ctx.scene.wavelength.engine='source_gmod_windows'
root=bpy.data.objects.new('Source stairs',None);ctx.collection.objects.link(root)
primitive_ui.rebuild(root,'STAIRS',primitive_ui.DEFAULTS,ctx)
primitive_ui.finalize(root,ctx)
source=primitive_ui.parts_for(root)[0]
bpy.ops.object.select_all(action='DESELECT');source.select_set(True);ctx.view_layer.objects.active=source
bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(source.data)
for f in bm.faces:f.select_set(False)
max(bm.faces,key=lambda f:f.normal.z).select_set(True);bmesh.update_edit_mesh(source.data)
print('SOURCE STATE',source.get('wl_procedural_state'),'ROOT STATE',root.get('wl_procedural_state'),'MODIFIERS',[(m.name,m.type) for m in source.modifiers],flush=True)
terrain_face.create(ctx)
print('PASS finalized procedural brush accepts a displacement',flush=True)

from wavelength.source import scene,primitives
def cube(name):
    if ctx.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    vertices,faces=primitives.box(-64,-64,-16,64,64,0)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([[c*.0254 for c in v] for v in vertices],[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);ctx.collection.objects.link(obj);scene.mark_brush(obj)
    return obj
def select_face(obj):
    if ctx.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);ctx.view_layer.objects.active=obj;bpy.ops.object.mode_set(mode='EDIT')
    bm=bmesh.from_edit_mesh(obj.data)
    for f in bm.faces:f.select_set(False)
    max(bm.faces,key=lambda f:f.normal.z).select_set(True);bmesh.update_edit_mesh(obj.data)
plain=cube('Ordinary cube');select_face(plain);terrain_face.create(ctx)
print('PASS ordinary cube does not require procedural finalization',flush=True)
stale=cube('Cube with inherited state');stale['wl_procedural_state']='PROCEDURAL';select_face(stale);terrain_face.create(ctx)
print('PASS stale part metadata does not block a static cube',flush=True)
# A finalized root is authoritative even if a legacy part tag disagrees.
part=primitive_ui.parts_for(root)[1];part['wl_procedural_state']='PROCEDURAL';select_face(part);terrain_face.create(ctx)
print('PASS finalized assembly overrides stale child state',flush=True)
modified=cube('Modified cube');modified.modifiers.new('My bevel','BEVEL');select_face(modified)
try:terrain_face.create(ctx)
except ValueError as exc:assert 'My bevel' in str(exc) and 'Finalize' not in str(exc)
else:raise AssertionError('Unapplied geometry modifier accepted')
assert ctx.mode=='EDIT_MESH'
print('PASS remaining modifier is identified instead of misreported as finalization',flush=True)
bpy.ops.object.mode_set(mode='OBJECT')
live=bpy.data.objects.new('Live stairs',None);ctx.collection.objects.link(live);primitive_ui.rebuild(live,'STAIRS',primitive_ui.DEFAULTS,ctx)
select_face(primitive_ui.parts_for(live)[0])
try:terrain_face.create(ctx)
except ValueError as exc:assert 'Finalize Geometry' in str(exc) and 'Live stairs' in str(exc)
else:raise AssertionError('Live assembly accepted')
print('PASS live procedural assembly still requires finalization',flush=True)
