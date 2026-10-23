exec(compile((__import__('pathlib').Path(__file__).parent/'blender_asset_placement.py').read_text(),__file__,'exec'))
from wavelength.source import asset_browser,asset_index,asset_search
from wavelength.source.entity import browser as entities
import traceback
ctx.preferences.view.show_splash=False
ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength_context.preparation=False
name=obj.name
placement.paint(ctx,obj,0,materials[0],'OBJECT')
for candidate in ctx.scene.objects:
    if candidate!=obj:candidate.hide_set(True)
obj.hide_set(False);obj.select_set(True);ctx.view_layer.objects.active=obj
entities.ensure_browser_layout(ctx,section='TEXTURES')
view=None;browser=None
asset_browser.metadata(materials[1],asset_index.record(s.engine,names[1],'MATERIAL'));asset_browser.preview(materials[1])
def fail():traceback.print_exc();bpy.ops.wm.quit_blender()
def choose(block,section):
    s.asset_browser_section=section;params=browser.spaces.active.params;params.asset_library_reference='LOCAL';params.asset_catalog_visibility='ALL'
    params.filter_asset_id.filter_material=section=='TEXTURES';params.filter_asset_id.filter_object=section=='ENTITIES'
    with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
        asset_search.ensure(browser).query=block.name;params.filter_search=block.name
        browser.spaces.active.activate_asset_by_id(block)
    def activate():
        region=next(r for r in browser.regions if r.type=='WINDOW')
        with ctx.temp_override(area=browser,region=region):
            bpy.ops.file.select_all(action='SELECT')
            browser.spaces.active.activate_asset_by_id(block)
    bpy.app.timers.register(activate,first_interval=.8)
def click():
    region=next(r for r in view.regions if r.type=='WINDOW');x=region.x+region.width//2;y=region.y+region.height//2
    ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
    ctx.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=x,y=y);ctx.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=x,y=y)
def begin():
    global view,browser
    try:
        view=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');browser=next(a for a in ctx.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
        with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):
            bpy.ops.view3d.view_axis(type='FRONT');view.spaces.active.region_3d.view_location=(0,0,0);view.spaces.active.region_3d.view_distance=6
        ctx.window_manager.wl_texture_apply_scope='AUTO'
        placement._dismissed=None
        choose(materials[1],'TEXTURES');bpy.app.timers.register(arm_texture,first_interval=1.4)
    except Exception:fail()
def arm_texture():
    try:
        with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
            selected=asset_browser.selected_asset(ctx)
            assert selected and selected.local_id==materials[1],(ctx.asset,list(ctx.selected_assets or []))
            assert placement._active is not None,'Selecting an asset must automatically arm placement'
        with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):
            bpy.ops.object.mode_set(mode='EDIT')
            assert placement.resolved_scope(ctx)=='SURFACE'
            bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
            for face in bm.faces:face.select_set(False)
            bm.faces[0].select_set(True);bm.faces[1].select_set(True);bmesh.update_edit_mesh(obj.data)
            placement._active.finish(ctx)
            assert placement._active is None,'Drag must work while Click Place is dismissed'
        region=next(r for r in browser.regions if r.type=='WINDOW');x=region.x+80;y=region.y+region.height-80
        ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
        ctx.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=x,y=y)
        ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x+15,y=y)
        region=next(r for r in view.regions if r.type=='WINDOW');x=region.x+region.width//2;y=region.y+region.height//2
        ctx.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
        ctx.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=x,y=y)
        bpy.app.timers.register(surface_done,first_interval=.5)
    except Exception:fail()
def surface_done():
    try:
        target=bpy.data.objects[name]
        with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):bpy.ops.object.mode_set(mode='OBJECT')
        assert sum(target.data.materials[p.material_index]==materials[1] for p in target.data.polygons)==2
        assert {p.index for p in target.data.polygons if p.select}=={0,1}
        print('PASS native Edit Mode drag with Click Place off assigns only two selected faces and preserves selection',flush=True)
        with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
            bpy.ops.wavelength.click_place('INVOKE_DEFAULT')
        assert ctx.window_manager.wl_click_place
        with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):bpy.ops.ed.undo_push(message='Leave Edit Mode')
        ctx.window_manager.wl_texture_apply_scope='AUTO';assert placement.resolved_scope(ctx)=='OBJECT'
        click();bpy.app.timers.register(object_done,first_interval=.5)
    except Exception:fail()
def object_done():
    try:
        target=bpy.data.objects[name];assert all(target.data.materials[p.material_index]==materials[1] for p in target.data.polygons)
        bpy.app.timers.register(undo_check,first_interval=.4)
    except Exception:fail()
def undo_check():
    try:
        assert ctx.window_manager.wl_click_place
        with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):bpy.ops.ed.undo()
        assert placement._active is None and not ctx.window_manager.wl_click_place,'Undo must dispose of the live placement session'
        target=bpy.data.objects[name]
        faces=bmesh.from_edit_mesh(target.data).faces if target.mode=='EDIT' else target.data.polygons
        assert sum(target.data.materials[p.material_index]==materials[1] for p in faces)==2,'Undo must restore only the two selected painted faces'
        if target.mode=='EDIT':
            with ctx.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):bpy.ops.object.mode_set(mode='OBJECT')
        print('PASS native browser selection, viewport face click, whole-object scope and per-click undo',flush=True)
        entities.rebuild_for_scene(ctx.scene,ctx)
        template=next(o for o in bpy.data.objects if o.get('wl_entity_browser_template')=='info_target' and o.asset_data)
        choose(template,'ENTITIES');bpy.app.timers.register(arm_entity,first_interval=1.6)
    except Exception:fail()
def arm_entity():
    try:
        global old_count,cursor
        old_count=sum(o.get('wl_role')=='ENTITY' and not o.get('wl_exclude') for o in ctx.scene.objects);cursor=ctx.scene.cursor.location.copy()
        with ctx.temp_override(area=browser,region=next(r for r in browser.regions if r.type=='WINDOW')):
            assert placement._active is not None,'Entity selection must automatically arm placement'
        click();bpy.app.timers.register(entity_done,first_interval=.5)
    except Exception:fail()
def entity_done():
    try:
        count=sum(o.get('wl_role')=='ENTITY' and not o.get('wl_exclude') for o in ctx.scene.objects)
        assert count==old_count+1 and ctx.scene.cursor.location==cursor
        assert abs(ctx.view_layer.objects.active.location.y+1)<.05,ctx.view_layer.objects.active.location[:]
        ctx.scene.wavelength_context.mode='CLEAN';click();bpy.app.timers.register(finish,first_interval=.4)
    except Exception:fail()
def finish():
    try:
        assert not ctx.window_manager.wl_click_place and placement._active is None
        print('PASS native entity selection and click placement on surface, unchanged cursor and context-state cancellation',flush=True)
        bpy.ops.screen.screenshot(filepath=str(root/'build/asset-placement-ui.png'))
    except Exception:traceback.print_exc()
    bpy.ops.wm.quit_blender()
ctx.window.event_simulate(type='ESC',value='PRESS');ctx.window.event_simulate(type='ESC',value='RELEASE')
bpy.app.timers.register(begin,first_interval=1)
