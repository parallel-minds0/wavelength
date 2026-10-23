"""Render a small batch of Source model thumbnails in a separate Blender process."""
import json,sys,traceback
from pathlib import Path
from types import SimpleNamespace
import bpy
from mathutils import Vector

def render_icon(path,scene,camera,output):
    from .entity import icons
    objects=icons._direct_import(path)
    if not objects:raise ValueError('SVG has no drawable geometry')
    for index,obj in enumerate(objects):obj.location.z=index*.002
    shading=scene.display.shading
    old=(shading.light,shading.color_type,shading.show_shadows,shading.show_cavity)
    try:
        shading.light='FLAT';shading.color_type='MATERIAL';shading.show_shadows=False;shading.show_cavity=False
        camera.location=(0,0,3);camera.rotation_euler=(0,0,0);camera.data.ortho_scale=1.3;camera.data.clip_start=.01;camera.data.clip_end=10
        output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_name(output.stem+'.tmp.png')
        scene.render.filepath=str(temporary);bpy.ops.render.render(write_still=True);temporary.replace(output)
        output.with_suffix('.error').unlink(missing_ok=True)
    finally:shading.light,shading.color_type,shading.show_shadows,shading.show_cavity=old


def render_batch(request):
    from wavelength.source import model_import,profiles
    settings=SimpleNamespace(engine=request['engine'],game_dir=request['game_dir'],fgd_path=request.get('fgd_path',''),unit_scale=.0254)
    scene=bpy.context.scene
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    camera=bpy.data.objects.new('Thumbnail Camera',bpy.data.cameras.new('Thumbnail Camera'));scene.collection.objects.link(camera);scene.camera=camera
    camera.data.type='ORTHO';camera.data.lens=50
    scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=128;scene.render.resolution_y=128;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.display.shading.light='STUDIO';scene.display.shading.color_type='TEXTURE';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type='BOTH';scene.display.render_aa='8';scene.view_settings.view_transform='Standard'
    scene.view_settings.exposure=.7
    for job in request['jobs']:
        output=Path(job['output'])
        try:
            if job.get('values',{}).get('icon'):
                from .entity import icons
                render_icon(icons.ICON_ROOT/'icons'/job['values']['icon'],scene,camera,output)
                continue
            if profiles.is_goldsrc(settings.engine):
                from wavelength.source import goldsrc_import,goldsrc_model
                mesh=goldsrc_import.mesh(settings,job['path'],goldsrc_model.Assets(settings.game_dir),job.get('values',{}))
            else:
                from wavelength.source import source_assets
                decode=source_assets.decode_vtf
                source_assets.decode_vtf=lambda data,*args,**kwargs:decode(data,max_dimension=128)
                try:mesh,data=model_import.mesh(settings,job['path'],int(job.get('values',{}).get('skin','0') or '0'),int(job.get('values',{}).get('body','0') or '0'))
                finally:source_assets.decode_vtf=decode
            if not mesh.vertices:raise ValueError('Model has no render geometry')
            obj=bpy.data.objects.new('Thumbnail Model',mesh);scene.collection.objects.link(obj)
            low=Vector(tuple(min(v.co[i] for v in mesh.vertices) for i in range(3)));high=Vector(tuple(max(v.co[i] for v in mesh.vertices) for i in range(3)))
            center=(low+high)/2;radius=max((high-low).length/2,.01)
            camera.location=center+Vector((1,-1,.7)).normalized()*radius*3
            camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
            rotation=camera.rotation_euler.to_matrix().transposed()
            projected=[rotation@(Vector(corner)-center) for corner in obj.bound_box]
            camera.data.ortho_scale=max(max(abs(v.x),abs(v.y)) for v in projected)*2.35
            camera.data.clip_start=max(radius*.001,.0001);camera.data.clip_end=radius*10
            output.parent.mkdir(parents=True,exist_ok=True);temporary=output.with_name(output.stem+'.tmp.png')
            scene.render.filepath=str(temporary);bpy.ops.render.render(write_still=True)
            temporary.replace(output)
            output.with_suffix('.error').unlink(missing_ok=True)
        except Exception as exc:
            output.with_suffix('.error').write_text(str(exc),encoding='utf-8');traceback.print_exc()
        finally:
            for obj in list(bpy.data.objects):
                if obj!=camera:bpy.data.objects.remove(obj,do_unlink=True)
            for mesh in list(bpy.data.meshes):bpy.data.meshes.remove(mesh)
            for curve in list(bpy.data.curves):bpy.data.curves.remove(curve)
            for material in list(bpy.data.materials):bpy.data.materials.remove(material)
            for image in list(bpy.data.images):
                if image.type!='RENDER_RESULT':bpy.data.images.remove(image)


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    render_batch(json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8')))
