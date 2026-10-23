"""Real placement gestures must commit node assemblies for every brush primitive."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_pencil_controls.py').read_text().split("with bpy.context.temp_override(area=area,region=region):")[0],__file__,'exec'))
from wavelength.source import primitive_ui as ui,procedural
import bmesh
steps=[]
for kind in ('CUBE','CYLINDER','CONE','SPHERE','ARCH','STAIRS'):
    def setup(kind=kind):
        bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
        bpy.context.scene.wavelength.stair_curved=True
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.wm.tool_set_by_id(name='wavelength.create_'+kind.lower()+'_brush_tool')
    steps.append(setup)
    for typ,val,pt in [('MOUSEMOVE','NOTHING',(-1,-1,0)),('LEFTMOUSE','PRESS',(-1,-1,0)),('LEFTMOUSE','RELEASE',(-1,-1,0)),('MOUSEMOVE','NOTHING',(1,1,0)),('LEFTMOUSE','PRESS',(1,1,0)),('LEFTMOUSE','RELEASE',(1,1,0)),('LEFTMOUSE','PRESS',(1,1,0)),('LEFTMOUSE','RELEASE',(1,1,0))]:
        def send(typ=typ,val=val,pt=pt):
            xy=view3d_utils.location_3d_to_region_2d(region,space.region_3d,Vector(pt))
            window.event_simulate(type=typ,value=val,x=int(region.x+xy.x),y=int(region.y+xy.y))
        steps.append(send)
    def verify(kind=kind):
        obj=bpy.context.object;assert obj and obj.type=='MESH',(kind,obj)
        root=ui.root_for(obj);assert root and root.get('wl_primitive')==kind,(kind,root)
        assert procedural.Definition.loads(root['wl_definition']).generator.startswith('wavelength.geometry_nodes.')
        assert obj.modifiers and obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons
        print('PASS actual brush placement commits node mesh',kind,flush=True)
    steps.append(verify)
def tick():
    try:
        if steps:steps.pop(0)();return .18
        print('PASS PRIMITIVE PLACEMENT',flush=True);bpy.ops.wm.quit_blender()
    except Exception:traceback.print_exc();print('FAIL PRIMITIVE PLACEMENT',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
