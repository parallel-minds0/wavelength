"""Assign object identities after native Blender duplication, without changing mesh data."""
import bpy
from bpy.app.handlers import persistent
from .scene import uid

_owners = {}
_updating = False
_known_ids = {}
_object_count = -1


@persistent
def update_ids(*_args):
    global _updating, _object_count
    if _updating:
        return
    if any(scene.get('wl_importing') for scene in bpy.data.scenes):return
    if len(_args)>1 and hasattr(_args[1],'updates'):
        changed=[u.id.original for u in _args[1].updates if isinstance(u.id,bpy.types.Object)]
        if not changed:return
        if len(bpy.data.objects)==_object_count and all(not o.get('wl_role') or _known_ids.get(o.as_pointer())==o.get('wl_id') for o in changed):return
    _updating = True
    try:
        objects = [obj for obj in bpy.data.objects
                   if obj.get('wl_role') and not obj.library and not obj.override_library]
        # Previously observed owners go first, so duplicating cannot rename the source ID.
        objects.sort(key=lambda obj: _owners.get(obj.get('wl_id')) != obj.as_pointer())
        by_pointer = {obj.as_pointer(): obj for obj in objects}
        duplicates = []
        owners = {}
        for obj in objects:
            identity = obj.get('wl_id')
            if not identity or identity in owners:
                if identity in owners:
                    duplicates.append((by_pointer[owners[identity]], obj))
                identity = uid()
                obj['wl_id'] = identity
            owners[identity] = obj.as_pointer()
        _owners.clear()
        _owners.update(owners)
        _known_ids.clear();_known_ids.update((o.as_pointer(),o.get('wl_id')) for o in objects)
        _object_count=len(bpy.data.objects)
        # Native Shift+D / Alt+D omit unselected editor-only visual children.
        from .entity.models import copy_references
        for source, duplicate in duplicates:
            if duplicate.get('wl_role')=='ENTITY':copy_references(source,duplicate)
        from . import source_displacement
        for source,duplicate in duplicates:
            if duplicate.get('wl_role')=='BRUSH':source_displacement.copy_surfaces(source,duplicate)
        for source,duplicate in duplicates:
            if duplicate.get('wl_source_displacement'):source_displacement.duplicate_surface(source,duplicate)
    finally:
        _updating = False


@persistent
def load_ids(*_args):
    _owners.clear();_known_ids.clear()
    update_ids()


def register():
    from .entity import icons,interaction
    icons.register()
    interaction.register()
    # Blender may expose _RestrictData while an add-on is being enabled.
    # Do not scan bpy.data here; the first depsgraph/load event will initialize IDs.
    for handlers, callback in ((bpy.app.handlers.depsgraph_update_post, update_ids),
                               (bpy.app.handlers.load_post, load_ids),
                               (bpy.app.handlers.undo_post, update_ids),
                               (bpy.app.handlers.redo_post, update_ids)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    from .entity import icons,interaction
    interaction.unregister()
    icons.unregister()
    for handlers, callback in ((bpy.app.handlers.depsgraph_update_post, update_ids),
                               (bpy.app.handlers.load_post, load_ids),
                               (bpy.app.handlers.undo_post, update_ids),
                               (bpy.app.handlers.redo_post, update_ids)):
        if callback in handlers:
            handlers.remove(callback)
    _owners.clear()
