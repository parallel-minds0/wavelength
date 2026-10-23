exec(compile((__import__('pathlib').Path(__file__).parent/'blender_profile_setup.py').read_text(),__file__,'exec'))
from wavelength.source import model_browser
import traceback
ctx.preferences.view.show_splash=False;ctx.workspace['wl_layout_ready']=True
bpy.ops.wavelength.entity_browser(section='MODELS')
while model_browser._queue:model_browser.publish_batch()
choices=[o for o in bpy.data.objects if o.get('wl_model_choice') and o.asset_data]
assert len(choices)==2
def verify():
    try:
        assert all(o.get('wl_library_preview') and tuple(o.preview.image_size)==(128,128) for o in choices)
        bpy.ops.screen.screenshot(filepath=str(root/'build/profile-setup-browser.png'))
        assert any(a.type=='FILE_BROWSER' and a.ui_type=='ASSETS' for a in ctx.screen.areas)
        print('PASS native model Asset Browser displays rendered cached previews on real model-choice assets',flush=True)
        profile_setup._AUTO=True;s.auto_prepare_assets=True;profile_setup._candidate=None
        (cache/'control.json').write_text('{}')
        bpy.app.timers.register(check_auto,first_interval=.3)
    except Exception:traceback.print_exc();print('FAIL SETUP UI',flush=True)
    return None
phase='AUTO';deadline=time.monotonic()+60
def check_auto():
    global phase
    try:
        if time.monotonic()>deadline:raise AssertionError('Automatic setup did not complete')
        if phase=='AUTO':
            if profile_setup._process and profile_setup.state(s).get('state')=='READY':
                ctx.workspace['wl_enabled']=False;phase='SUSPEND'
            return .5
        assert profile_setup._process is None,'Leaving Wavelength must suspend the worker'
        print('PASS configured profile automatically resumes cached preparation; workspace suspension stops its worker',flush=True)
    except Exception:traceback.print_exc();print('FAIL AUTOMATIC SETUP',flush=True)
    bpy.ops.wm.quit_blender();return None
bpy.app.timers.register(verify,first_interval=2)
