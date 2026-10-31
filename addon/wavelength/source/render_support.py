"""Prepare renderer datablocks off-process and publish one coherent asset batch."""
from collections import deque
import time
import bpy
from bpy.app.handlers import persistent
from . import profiles,render_bundle

_jobs=deque()
_scenes=set()


def prepare(scene):
    if not profiles.is_source(scene.wavelength.engine):return False
    if any(job.scene==scene for job in _jobs):return False
    def unresolved(mat):
        return mat and mat.get('wl_source_native_material') and not (mat.node_tree and any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes))
    if not any(obj.get('wl_source_native_model') or (obj.type=='MESH' and any(unresolved(m) for m in obj.data.materials)) for obj in scene.objects):return False
    scene['wl_source_render_preparing']=True
    try:_jobs.append(render_bundle.Request(scene))
    except Exception:
        scene.pop('wl_source_render_preparing',None);raise
    _scenes.add(scene.as_pointer())
    return True


def progress(scene):
    return next((job for job in _jobs if job.scene==scene),None)


def step(blocking=False):
    if not _jobs:return
    job=_jobs[0]
    finished=False
    try:
        if blocking:
            while not job.poll():time.sleep(.05)
        elif not job.poll():return
        job.publish()
        finished=True
    except Exception as exc:
        finished=True
        job.scene.wavelength.status='Render asset preparation failed: '+str(exc)
        if blocking:raise
    finally:
        if blocking or finished:
            job.scene.pop('wl_source_render_preparing',None)
            job.close();_jobs.popleft()


def tick():
    try:
        for window in bpy.context.window_manager.windows:
            scene=window.scene
            if scene.get('wl_importing'):continue
            if not hasattr(scene,'wavelength') or not profiles.is_source(scene.wavelength.engine):continue
            if scene.get('wl_native_source_scene'):
                key=scene.as_pointer()
                if key not in _scenes:
                    if not prepare(scene) and scene.get('wl_source_blender_rendering'):_scenes.add(key)
        # Imports preload regardless of the selected viewport mode. Mode
        # switching subsequently reuses the same bound datablocks.
        if _jobs and not _jobs[0].scene.get('wl_importing'):step()
    except (ReferenceError,RuntimeError):pass
    return .15 if _jobs else .4


@persistent
def before_render(scene,*args):
    if not hasattr(scene,'wavelength') or not profiles.is_source(scene.wavelength.engine):return
    prepare(scene)
    while _jobs:step(blocking=True)


@persistent
def loaded(*args):
    while _jobs:
        job=_jobs.popleft()
        try:job.close();job.scene.pop('wl_source_render_preparing',None)
        except ReferenceError:pass
    _scenes.clear();render_bundle.clear()


def register():
    if not bpy.app.timers.is_registered(tick):bpy.app.timers.register(tick,first_interval=.4,persistent=True)
    if before_render not in bpy.app.handlers.render_init:bpy.app.handlers.render_init.append(before_render)
    if loaded not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(loaded)


def unregister():
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if before_render in bpy.app.handlers.render_init:bpy.app.handlers.render_init.remove(before_render)
    if loaded in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(loaded)
    loaded()
