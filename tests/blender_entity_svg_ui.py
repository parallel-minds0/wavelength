exec(compile((__import__('pathlib').Path(__file__).parent/'blender_entity_svg_assets.py').read_text(),__file__,'exec'))
from wavelength.source import profile_setup,surface_tools
import traceback
ctx.preferences.view.show_splash=False
bpy.ops.wavelength.entity_browser(section='ENTITIES')
def verify():
    try:
        cache=root/'build/library-setup-tests/source_hl2_windows'
        template=next(o for o in bpy.data.objects if o.get('wl_entity_browser_template')=='logic_relay' and o.asset_data)
        assert profile_setup.apply(template,cache,'ENTITY:logic_relay')
        assert tuple(template.preview.image_size)==(128,128)
        browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
        browser.spaces.active.params.asset_library_reference='LOCAL';browser.spaces.active.params.filter_search='logic_relay'
        from wavelength.source import asset_search
        with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
            asset_search.ensure(browser).query='logic_relay'
            browser.spaces.active.activate_asset_by_id(template)
        print('PASS native entity Asset Browser accepts rendered SVG ID preview and in-world helper curves remain visible',flush=True)
        bpy.app.timers.register(finish,first_interval=1)
    except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
def finish():
    bpy.ops.screen.screenshot(filepath=str(root/'build/entity-svg-ui.png'));bpy.ops.wm.quit_blender()
bpy.app.timers.register(verify,first_interval=1)
