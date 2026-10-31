"""Small role indexes for timers; unchanged maps should not be walked at 10 Hz."""
import bpy
from bpy.app.handlers import persistent

_cache={}


def matching(name,owner,predicate,force=False):
    objects=owner.objects;key=(name,owner.as_pointer() if hasattr(owner,'as_pointer') else 0)
    # Role membership changes with scene edits, not wall-clock time. Expiring
    # every second made idle assembly/pencil timers repeatedly walk large maps.
    stamp=len(objects)
    old=_cache.get(key)
    if force or old is None or old[0]!=stamp:
        old=(stamp,tuple(o for o in objects if predicate(o)));_cache[key]=old
    return old[1]


@persistent
def clear(*_):_cache.clear()


def register():
    clear()
    if clear not in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.append(clear)
    if clear not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(clear)
    if clear not in bpy.app.handlers.undo_post:bpy.app.handlers.undo_post.append(clear)
    if clear not in bpy.app.handlers.redo_post:bpy.app.handlers.redo_post.append(clear)


def unregister():
    for handlers in (bpy.app.handlers.depsgraph_update_post,bpy.app.handlers.load_post,bpy.app.handlers.undo_post,bpy.app.handlers.redo_post):
        if clear in handlers:handlers.remove(clear)
    clear()
