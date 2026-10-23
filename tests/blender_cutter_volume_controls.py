"""Real events: draw an open path, choose Z and finite depth, then clip with K."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_pencil_controls.py').read_text().split('steps=[];state={}')[0],__file__,'exec'))
import bmesh
settings=bpy.context.scene.wavelength_draw
settings.depth=.25;settings.keep='OUTSIDE'
if '--keep-both' in sys.argv:settings.keep='BOTH'
settings.separate_objects='--combined' not in sys.argv
steps=[];state={}
def send(kind,value='PRESS',point=(0,0,.5),shift=False):
    def step():
        with bpy.context.temp_override(area=area,region=region):
            xy=view3d_utils.location_3d_to_region_2d(region,space.region_3d,Vector(point))
            window.event_simulate(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y),shift=shift)
    steps.append(step)
def click(point):
    send('MOUSEMOVE','NOTHING',point);send('LEFTMOUSE',point=point);send('LEFTMOUSE','RELEASE',point)
click((-3,0,.5));click((3,0,.5))
send('Z');send('D');send('WHEELUPMOUSE')
send('B');send('WHEELUPMOUSE',shift=True);send('WHEELDOWNMOUSE',shift=True);send('B');send('B')
def preview():
    drawing=pencil._drawing[0];st=drawing._operation_settings
    assert st['operation']=='SPLIT' and st['direction']=='Z' and not st['through'],st
    assert abs(st['depth']-.275)<1e-6,st
    assert st['keep']==settings.keep,st
    assert len(drawing._points)==2
    print('PASS live Z direction, D depth, B/Shift-wheel keep cycling without changing depth',flush=True)
steps.append(preview)
send('RET' if '--confirm-enter' in sys.argv else 'K')
def check():
    target=bpy.data.objects[target_name]
    if target.mode=='EDIT':target.update_from_editmode()
    bm=bmesh.new();bm.from_mesh(target.data)
    assert all(e.is_manifold for e in bm.edges)
    value=abs(bm.calc_volume())*abs(target.matrix_world.determinant())
    if '--keep-both' in sys.argv:
        if '--combined' not in sys.argv:
            outputs=[obj for obj in bpy.context.selected_objects if obj.type=='MESH']
            assert len(outputs)==2,outputs
            value=0
            for obj in outputs:
                piece=bmesh.new();piece.from_mesh(obj.data);assert all(e.is_manifold for e in piece.edges)
                value+=abs(piece.calc_volume())*abs(obj.matrix_world.determinant());piece.free()
            assert abs(value-64)<1e-3,value
            print('PASS Keep Both creates two separate manifold objects and preserves total volume',flush=True)
            bm.free();bpy.ops.wm.quit_blender();return
        remaining=set(bm.verts);components=[]
        while remaining:
            pending=[remaining.pop()];component=set(pending)
            while pending:
                for edge in pending.pop().link_edges:
                    for vertex in edge.verts:
                        if vertex in remaining:remaining.remove(vertex);component.add(vertex);pending.append(vertex)
            components.append(component)
        assert len(components)==2,('Expected separate capped volumes, not only surface edges',len(components))
        assert abs(value-64)<1e-3,value
        print('PASS Keep Both produces two disconnected closed components in one mesh, preserving volume 64',flush=True)
    else:assert abs(value-55.2)<1e-3,value
    bm.free()
    assert not pencil._drawing
    assert not any(o.name.startswith(('.Cutter Work','.Cutter Volume')) for o in bpy.context.scene.objects)
    print('PASS live finite-depth clipping and correct confirmation key',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .2 if steps else None
    except Exception:traceback.print_exc();print('FAIL VOLUMETRIC CONTROLS',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
