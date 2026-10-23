import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import primitive_ui as ui,procedural as p
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
ctx.scene.wavelength.engine='blender';ctx.scene.tool_settings.use_snap=False
root=bpy.data.objects.new('Procedural Boundary Test',None);ctx.collection.objects.link(root)
ui.rebuild(root,'STAIRS',ui.DEFAULTS,ctx)
definition=p.Definition.loads(root['wl_definition']);assert definition.owner=='blender'
parts=ui.parts_for(root);assert len(parts)==1
obj=parts[0];mesh=obj.data
modifier=obj.modifiers.new('Test evaluated bevel','BEVEL');modifier.width=.01;modifier.segments=1
ctx.view_layer.update();expected=len(obj.evaluated_get(ctx.evaluated_depsgraph_get()).data.polygons)
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);ctx.view_layer.objects.active=root
ui.finalize(root,ctx)
assert p.state(root)=='FINALIZED' and not obj.modifiers
assert len(obj.data.polygons)==expected and obj.data!=mesh
assert obj['wl_owner_profile']=='blender'
ctx.scene.wavelength.engine='source_hl2_windows';before=obj.data
try:ui.rebuild(root,'STAIRS',ui.DEFAULTS,ctx)
except ValueError:pass
else:raise AssertionError('Finalized root regenerated')
assert obj.data==before
print('PASS evaluated finalization, owner preservation and regeneration guard',flush=True)
root2=bpy.data.objects.new('Source procedural',None);ctx.collection.objects.link(root2)
ui.rebuild(root2,'ARCH',ui.DEFAULTS,ctx)
d=p.Definition.loads(root2['wl_definition']);assert d.convex_brushes
ctx.scene.wavelength.engine='blender'
ui.rebuild(root2,'ARCH',{**ui.DEFAULTS,'segments':6},ctx)
assert len(ui.parts_for(root2))==6
assert p.Definition.loads(root2['wl_definition']).unit_meters==d.unit_meters
print('PASS procedural Source ownership and constraints survive active profile changes',flush=True)
part=ui.parts_for(root2)[0];before=part.data
part.data.vertices[0].co.z+=.123
try:ui.finalize(root2,ctx)
except ValueError:pass
else:raise AssertionError('Invalid BSP geometry was finalized')
assert p.state(root2)=='PROCEDURAL' and part.data==before
print('PASS failed BSP finalization preserves existing meshes/state',flush=True)
addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
print('PASS restricted addon reload',flush=True)
