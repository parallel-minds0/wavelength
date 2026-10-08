"""Assign object identities after native Blender duplication, without changing mesh data."""
import bpy
from bpy.app.handlers import persistent
from .scene import uid

_owners = {}
_updating = False


@persistent
def update_ids(*_args):
    global _updating
    if _updating:
        return
    _updating = True
    try:
        objects = [obj for obj in bpy.data.objects
                   if obj.get('wl_role') and not obj.library and not obj.override_library]
        # Previously observed owners go first, so duplicating cannot rename the source ID.
        objects.sort(key=lambda obj: _owners.get(obj.get('wl_id')) != obj.as_pointer())
        owners = {}
        for obj in objects:
            identity = obj.get('wl_id')
            if not identity or identity in owners:
                identity = uid()
                obj['wl_id'] = identity
            owners[identity] = obj.as_pointer()
        _owners.clear()
        _owners.update(owners)
    finally:
        _updating = False


@persistent
def load_ids(*_args):
    _owners.clear()
    update_ids()


def register():
    # Blender may expose _RestrictData while an add-on is being enabled.
    # Do not scan bpy.data here; the first depsgraph/load event will initialize IDs.
    for handlers, callback in ((bpy.app.handlers.depsgraph_update_post, update_ids),
                               (bpy.app.handlers.load_post, load_ids),
                               (bpy.app.handlers.undo_post, update_ids),
                               (bpy.app.handlers.redo_post, update_ids)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    for handlers, callback in ((bpy.app.handlers.depsgraph_update_post, update_ids),
                               (bpy.app.handlers.load_post, load_ids),
                               (bpy.app.handlers.undo_post, update_ids),
                               (bpy.app.handlers.redo_post, update_ids)):
        if callback in handlers:
            handlers.remove(callback)
    _owners.clear()
