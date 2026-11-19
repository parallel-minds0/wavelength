"""Exercise stair footprint, cancellation and undo with viewport events."""
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import addon_utils
import bpy
from bpy_extras import view3d_utils
from mathutils import Vector

addon_utils.enable('wavelength', default_set=False)
ctx = bpy.context
ctx.preferences.use_preferences_save = False
ctx.preferences.view.show_splash = False
ctx.workspace['wl_workspace'] = True
ctx.workspace['wl_layout_ready'] = True
ctx.scene.wavelength.engine = 'source_hl2_windows'
ctx.scene.wavelength.grid_mode = 'ENGINE'
ctx.scene.tool_settings.use_snap = False
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
window = ctx.window
area = next(area for area in window.screen.areas if area.type == 'VIEW_3D')
region = next(region for region in area.regions if region.type == 'WINDOW')
view = area.spaces.active.region_3d
view.view_rotation = Vector((3, -4, 10)).to_track_quat('Z', 'Y')
view.view_perspective = 'PERSP'
view.view_distance = 9
view.view_location = (0, 0, 0)
steps = []


def setup():
    with ctx.temp_override(area=area, region=region):
        view.update()
        bpy.ops.wm.tool_set_by_id(name='wavelength.create_stairs_brush_tool')
        bpy.ops.ed.undo_push(message='Before stair demo')


def event(kind, value, point, **modifiers):
    def send():
        xy = view3d_utils.location_3d_to_region_2d(region, view, Vector(point))
        window.event_simulate(type=kind, value=value, x=round(region.x + xy.x),
                              y=round(region.y + xy.y), **modifiers)
    steps.append(send)


def click(point):
    event('MOUSEMOVE', 'NOTHING', point)
    event('LEFTMOUSE', 'PRESS', point)
    event('LEFTMOUSE', 'RELEASE', point)


def stairs():
    return [obj for obj in ctx.scene.objects if obj.get('wl_primitive') == 'STAIRS']


steps.append(setup)
click((-1, -1, 0))
event('MOUSEMOVE', 'NOTHING', (1, 1, 0))
event('ESC', 'PRESS', (1, 1, 0))
def check_cancel():
    assert not stairs(), 'Cancel created a stair'


steps.append(check_cancel)
click((-1, -1, 0))
click((1, 1, 0))
click((1, 1, 0))


def check_commit():
    assert len(stairs()) == 1
    assert stairs()[0].children
    print('PASS stair pointer footprint commits after cancellation', flush=True)
    with ctx.temp_override(area=area, region=region):
        assert bpy.ops.ed.undo() == {'FINISHED'}


def check_undo():
    assert not stairs()
    print('PASS stair creation undo', flush=True)
    bpy.ops.wm.quit_blender()


steps.extend((check_commit, check_undo))


def tick():
    try:
        steps.pop(0)()
        return .25 if steps else None
    except Exception:
        traceback.print_exc()
        print('FAIL STAIR POINTER EVENTS', flush=True)
        bpy.ops.wm.quit_blender()


bpy.app.timers.register(tick, first_interval=2)
