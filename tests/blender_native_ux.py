"""Exercise real UI drawing, selection binding, workspace scope and lifecycle."""
import json
import sys
import traceback
from pathlib import Path
from unittest.mock import patch
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'addon'))
import wavelength
from wavelength.source import ui, workspace, native_ui, textures, primitive_ui

out = ROOT / 'build/native-ux'
out.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory = str(out)
bpy.context.preferences.view.show_splash = False
wavelength.register()
original = bpy.context.workspace
baseline = [a.type for a in bpy.context.screen.areas]
stage = 0
target = None


def tick():
    global stage, target
    try:
        if stage == 0:
            target = workspace.ensure(bpy.context)
            bpy.context.window.workspace = target
        elif stage == 1:
            if bpy.context.workspace != target:
                bpy.context.window.workspace = target
                return 1
            with patch.object(textures, 'refresh'):
                bpy.context.scene.wavelength.engine = 'source_hl2_windows'
            target['wl_entity_catalog'] = 'source_hl2_windows|'
            assert ui.WL_PT_main.bl_space_type == 'PROPERTIES'
            assert ui.WL_PT_entity.bl_context == 'object'
            assert ui.WL_PT_texture.bl_category == 'Item'
            assert not hasattr(bpy.types, 'WL_PT_system_tree')
            assert not hasattr(bpy.types, 'WL_PT_authoring')
            props = next(a for a in bpy.context.screen.areas if a.type == 'PROPERTIES')
            props.spaces.active.context = 'SCENE'
            view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
            view.spaces.active.show_region_ui = False
        elif stage == 2:
            bpy.ops.screen.screenshot(filepath=str(out / 'scene.png'))
            bpy.ops.object.empty_add()
            obj = bpy.context.object
            obj.name = 'UX Test Light'
            obj['wl_role'] = 'ENTITY'
            obj['wl_id'] = 'ux-test-light'
            obj['wl_pairs'] = json.dumps([['classname', 'light'], ['_light', '255 255 255 200']])
            next(a for a in bpy.context.screen.areas if a.type == 'PROPERTIES').spaces.active.context = 'OBJECT'
        elif stage == 3:
            assert bpy.context.scene.wavelength.entity_editor_binding
            assert ui.WL_PT_entity.poll(bpy.context)
            bpy.ops.screen.screenshot(filepath=str(out / 'entity.png'))
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.object
            obj['wl_role'] = 'BRUSH'
            bpy.ops.object.mode_set(mode='EDIT')
            view = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
            view.spaces.active.show_region_ui = True
            assert ui.WL_PT_texture.poll(bpy.context)
            with bpy.context.temp_override(area=view, region=next(r for r in view.regions if r.type == 'WINDOW')):
                bpy.ops.wm.call_menu(name='WL_MT_face_mapping')
        elif stage == 4:
            bpy.ops.screen.screenshot(filepath=str(out / 'faces.png'))
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.window.workspace = original
        elif stage == 5:
            assert not workspace.active()
            assert not native_ui.WL_PT_object.poll(bpy.context)
            assert baseline == [a.type for a in bpy.context.screen.areas]
            wavelength.unregister()
            assert not native_ui._hooks and not native_ui._registered
            wavelength.register()
            wavelength.unregister()
            (out / 'result.json').write_text(json.dumps({'passed': True, 'checks': ['real panel drawing', 'entity selection binding', 'face context', 'workspace isolation', 'register/unregister twice']}))
            print('PASS NATIVE UX', flush=True)
            bpy.ops.wm.quit_blender()
            return None
        stage += 1
        return 2
    except Exception:
        (out / 'result.json').write_text(json.dumps({'passed': False, 'error': traceback.format_exc()}))
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None


bpy.app.timers.register(tick, first_interval=2)
