"""Scene-wide context, reversible visibility, real render exclusion and save/reload."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import context_state,context_policy,workspace,scene,vmf
from mathutils import Vector
state=ctx.scene.wavelength_context
def cube(name,location,color):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=ctx.object;obj.name=name
    mat=bpy.data.materials.new(name+' color');mat.diffuse_color=(*color,1);obj.data.materials.append(mat);return obj
game=cube('Game Model',(1.4,0,0),(0,1,0));game['wl_model_reference']=True;game['wl_exclude']=True
anchor=bpy.data.objects.new('Entity Anchor',None);ctx.collection.objects.link(anchor);anchor['wl_role']='ENTITY';anchor['wl_id']=scene.uid();anchor['wl_pairs']='[["classname","weapon_crowbar"]]';anchor['wl_unit_meters']=.0254
game.parent=anchor
helper=cube('Spawn Icon',(-1.4,0,0),(1,0,0));helper['wl_entity_icon_reference']=True
hidden=cube('Already Hidden',(-1.4,0,2),(1,0,0));hidden['wl_editor_helper']=True;hidden.hide_set(True)
manual=cube('User Hidden Content',(0,0,0),(0,0,1));manual.hide_render=True;manual.hide_set(True)
sun=bpy.data.objects.new('Game Sun',bpy.data.lights.new('Game Sun','SUN'));ctx.collection.objects.link(sun);sun.parent=anchor;sun['wl_sun_preview']=True;sun['wl_exclude']=True
second=ctx.scene.view_layers.new('Second Layer')
world=cube('World Brush',(0,0,-5),(.5,.5,.5));scene.mark_brush(world)
world.data.materials[0]['wl_texture']='brick/brickwall001a'
export_before=vmf.write(scene.export_map(ctx.scene))
assert bpy.ops.wavelength.set_context(mode='CLEAN')=={'FINISHED'}
assert vmf.write(scene.export_map(ctx.scene))==export_before,'Context visibility must not change exported map metadata'
assert not workspace.active(ctx) and not workspace.active(ctx,'preparation')
for layer in ctx.scene.view_layers:
    assert helper.hide_get(view_layer=layer) and anchor.hide_get(view_layer=layer)
    assert game.visible_get(view_layer=layer),'Hiding the empty anchor must retain its actual game mesh'
    assert sun.visible_get(view_layer=layer),'Real game lighting must remain available'
assert bpy.ops.wavelength.set_context(mode='EDIT')=={'FINISHED'}
assert not helper.hide_get() and hidden.hide_get() and manual.hide_get()
state.editing=False;assert not workspace.active(ctx) and workspace.active(ctx,'grid') and workspace.active(ctx,'preparation')
state.editing=True;state.overlays=False;assert workspace.active(ctx) and not workspace.active(ctx,'grid')
state.overlays=True
state.mode='SUSPENDED';assert not workspace.active(ctx) and not workspace.active(ctx,'preparation') and not helper.hide_get()
assert context_policy.operation_allowed(ctx,'wavelength.export_map')
state.mode='EDIT'
# Render from an ordinary Blender workspace, independently of Wavelength's tab.
ctx.workspace['wl_workspace']=False
camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));ctx.collection.objects.link(camera);ctx.scene.camera=camera
camera.location=(0,-10,1);camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=5
r=ctx.scene.render;r.engine='BLENDER_WORKBENCH';r.resolution_x=160;r.resolution_y=120;r.resolution_percentage=100;r.image_settings.file_format='PNG';r.film_transparent=True
ctx.scene.display.shading.light='FLAT';ctx.scene.display.shading.color_type='MATERIAL';ctx.scene.display.shading.show_shadows=False
def render(name):
    path=folder/(name+'.png');r.filepath=str(path);bpy.ops.render.render(write_still=True)
    image=bpy.data.images.load(str(path),check_existing=False)
    pixels=list(image.pixels);bpy.data.images.remove(image)
    red=sum(pixels[i]>.2 and pixels[i]>pixels[i+1]*1.5 and pixels[i+3]>.5 for i in range(0,len(pixels),4))
    green=sum(pixels[i+1]>.2 and pixels[i+1]>pixels[i]*1.5 and pixels[i+3]>.5 for i in range(0,len(pixels),4))
    return red,green
red,green=render('context-clean-render');assert red==0 and green>10,(red,green)
assert not helper.hide_render and manual.hide_render and not context_state.rendering()
state.render_helpers=True;red,green=render('context-diagnostic-render');assert red>10 and green>10,(red,green)
state.mode='CLEAN';red,green=render('context-clean-override-render');assert red==0 and green>10
assert not helper.hide_render and context_state.RENDER not in helper
state.mode='EDIT';state.render_helpers=False;context_state.render_begin(ctx.scene);assert helper.hide_render
context_state.render_end(ctx.scene);assert not helper.hide_render,'Cancel cleanup must restore helper flags'
state.mode='CLEAN';new=cube('New Helper',(0,0,4),(1,0,0));new['wl_editor_helper']=True
context_state.depsgraph(ctx.scene);context_state.tick();assert new.hide_get()
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'context-scene.blend'));bpy.ops.wm.open_mainfile(filepath=str(folder/'context-scene.blend'))
ctx=bpy.context;ctx.scene.wavelength_context.mode='EDIT'
assert not bpy.data.objects['Spawn Icon'].hide_get() and bpy.data.objects['Already Hidden'].hide_get()
assert not bpy.data.objects['New Helper'].hide_get() and not bpy.data.objects['Spawn Icon'].hide_render
print('PASS context capability switches, two-layer helper visibility, preserved game models/lights, clean renders outside Wavelength, diagnostic override, cancel cleanup, new helpers and save/reload restoration',flush=True)
