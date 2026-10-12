"""Real viewport regression: native intervals, occlusion, and workspace restoration."""
import json
import os
from pathlib import Path
import sys

import bpy
import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'addon'))
import wavelength
from wavelength.source import grid, workspace

OUT = Path(os.environ.get('WL_NATIVE_GRID_PROOF_DIR', ROOT / 'build/native-grid/proof'))
OUT.mkdir(parents=True, exist_ok=True)
wavelength.register()
original = bpy.context.workspace
stage = 0
view = region = None
samples = {}


def screenshot(name):
    path = OUT / f'{name}.png'
    bpy.ops.screen.screenshot(filepath=str(path))
    return path


def pixel_near(image, point, radius=2):
    width, height = image.size
    x, y = int(point.x), int(point.y)
    values = []
    for yy in range(max(0, y-radius), min(height, y+radius+1)):
        for xx in range(max(0, x-radius), min(width, x+radius+1)):
            offset = (yy*width+xx)*4
            values.append(tuple(image.pixels[offset:offset+3]))
    return values


def screen_point(world):
    p = location_3d_to_region_2d(region, view.spaces.active.region_3d, Vector(world))
    return p + Vector((region.x, region.y))


def tick():
    global stage, view, region
    try:
        if stage == 0:
            bpy.context.window.workspace = workspace.ensure(bpy.context)
        elif stage == 1:
            view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
            region = next(r for r in view.regions if r.type == 'WINDOW')
            assert grid.native_available(view.spaces.active), 'Native RNA API missing'
            s = bpy.context.scene.wavelength
            s.engine = 'blender'
            s.metric_grid_step = 1
            s.grid_subdivisions = 5
            grid.sync_native()
            with bpy.context.temp_override(area=view, region=region):
                bpy.ops.object.select_all(action='SELECT')
                bpy.ops.object.delete()
                bpy.ops.mesh.primitive_cube_add(size=.7, location=(1, 1, .35))
                bpy.ops.object.select_all(action='DESELECT')
                bpy.ops.view3d.view_axis(type='TOP')
            view.spaces.active.region_3d.view_location = (0, 0, 0)
            view.spaces.active.region_3d.view_distance = 5
            view.spaces.active.shading.type = 'SOLID'
        elif stage == 2:
            path = screenshot('native-top')
            image = bpy.data.images.load(str(path), check_existing=False)
            parent = pixel_near(image, screen_point((-1, -.47, 0)))
            minor = pixel_near(image, screen_point((-.8, -.47, 0)))
            assert max(r-b for r,g,b in parent) > .12, ('No yellow parent', parent)
            assert max(abs(r-b) for r,g,b in minor) < .08, ('Subdivision is yellow', minor)
            samples['cube'] = pixel_near(image, screen_point((1, 1, .7)), 5)
            bpy.data.images.remove(image)
            # Leaving the workspace stops the bridge. Disable only the native flag
            # temporarily to compare the exact same visible solid surface.
            bpy.app.timers.unregister(grid.sync_native)
            view.spaces.active.overlay.wavelength_grid_enabled = False
        elif stage == 3:
            path = screenshot('native-top-disabled')
            image = bpy.data.images.load(str(path), check_existing=False)
            off = pixel_near(image, screen_point((1, 1, .7)), 5)
            assert max(abs(a-b) for p,q in zip(samples['cube'],off) for a,b in zip(p,q)) < .015, 'Grid draws over solid geometry'
            bpy.data.images.remove(image)
            grid.sync_native()
            bpy.app.timers.register(grid.sync_native, persistent=True)
            view.spaces.active.region_3d.view_rotation = Euler((.8, 0, .6)).to_quaternion()
            view.spaces.active.region_3d.view_perspective = 'PERSP'
        elif stage == 4:
            path = screenshot('native-perspective')
            image = bpy.data.images.load(str(path), check_existing=False)
            samples['perspective_cube'] = pixel_near(image, screen_point((1, 1, .7)), 3)
            bpy.data.images.remove(image)
            bpy.app.timers.unregister(grid.sync_native)
            view.spaces.active.overlay.wavelength_grid_enabled = False
        elif stage == 5:
            path = screenshot('native-perspective-disabled')
            image = bpy.data.images.load(str(path), check_existing=False)
            off = pixel_near(image, screen_point((1, 1, .7)), 3)
            assert max(abs(a-b) for p,q in zip(samples['perspective_cube'],off) for a,b in zip(p,q)) < .015, 'Perspective grid draws over solid geometry'
            bpy.data.images.remove(image)
            grid.sync_native()
            bpy.app.timers.register(grid.sync_native, persistent=True)
            bpy.context.window.workspace = original
        else:
            grid.sync_native()
            assert not grid._native, 'Workspace exit did not restore viewports'
            assert not view.spaces.active.overlay.wavelength_grid_enabled
            wavelength.unregister()
            (OUT / 'result.json').write_text(json.dumps({'passed': True, 'backend': gpu.platform.backend_type_get(), 'renderer': gpu.platform.renderer_get(), 'checks': ['yellow parent', 'grey profile subdivisions', 'orthographic solid depth', 'perspective solid depth', 'workspace restoration']}))
            print('PASS NATIVE GRID VIEWPORT', flush=True)
            bpy.ops.wm.quit_blender()
            return None
        stage += 1
        return 2
    except Exception:
        import traceback
        error = traceback.format_exc()
        print(error, flush=True)
        (OUT / 'result.json').write_text(json.dumps({'passed': False, 'error': error}))
        bpy.ops.wm.quit_blender()
        return None


bpy.app.timers.register(tick, first_interval=3)
