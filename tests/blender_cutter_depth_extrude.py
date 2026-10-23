"""Closing a subtraction path sets real volume depth via mouse/numeric extrusion."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_cutter_volume_controls.py').read_text().split('click((-3,0,.5))')[0],__file__,'exec'))
settings.operation='SPLIT' if '--test-keep-input' in sys.argv else 'SUBTRACT';settings.auto_extrude=True
for p in [(-1,-1,.5),(1,-1,.5),(1,1,.5),(-1,1,.5)]:click(p)
send('C')
def depth_stage():
    assert pencil._drawing[0]._extruding
    print('PASS closing solid subtraction starts depth extrusion',flush=True)
steps.append(depth_stage)
if '--test-keep-input' in sys.argv:
    send('B');send('B');send('B');send('WHEELUPMOUSE',shift=True);send('WHEELDOWNMOUSE',shift=True)
    def check_keep():
        assert pencil._drawing[0]._operation_settings['keep']=='OUTSIDE'
        assert pencil._drawing[0]._extruding
        print('PASS B and Shift-wheel Keep controls during depth extrusion',flush=True)
    steps.append(check_keep)
for char in '.25':
    def digit(char=char):
        window.event_simulate(type='PERIOD' if char=='.' else ('TWO' if char=='2' else 'FIVE'),value='PRESS',unicode=char)
    steps.append(digit)
send('RET')
def check():
    target=bpy.data.objects[target_name]
    bm=bmesh.new();bm.from_mesh(target.data)
    assert all(e.is_manifold for e in bm.edges)
    value=abs(bm.calc_volume())*abs(target.matrix_world.determinant());bm.free()
    root=next(o for o in bpy.context.scene.objects if pencil.is_guide(o))
    points,_=pencil.sampled(root)
    area=abs(sum(a.x*b.y-b.x*a.y for a,b in zip(points,points[1:]+points[:1])))/2
    assert abs(root.wavelength_cutter.depth-.25)<1e-6
    assert abs(value-(64-area*.25))<1e-4,value
    assert not pencil._drawing
    print('PASS automatic solid depth confirmation: capped volume matches drawn outline area times depth .25',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .2 if steps else None
    except Exception:traceback.print_exc();print('FAIL SOLID DEPTH EXTRUSION',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
