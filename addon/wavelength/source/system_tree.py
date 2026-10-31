"""Derived engine/system view of Wavelength objects.

Blender Collections remain artist-owned.  This module never moves or links objects;
it only derives engine-facing categories from existing Wavelength metadata.
"""
import json

import bpy
from bpy.app.handlers import persistent

from . import profiles


def _pairs(obj, key):
    try:
        value = json.loads(obj.get(key, '[]'))
        return value if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def classname(obj):
    if obj.get('wl_role') == 'ENTITY':
        return dict(_pairs(obj, 'wl_pairs')).get('classname', '')
    if obj.get('wl_role') == 'BRUSH' and obj.get('wl_entity_id'):
        return dict(_pairs(obj, 'wl_entity_pairs')).get('classname', '')
    return ''


def brush_textures(obj):
    """Return known texture names without changing face/material metadata."""
    names = set()
    if getattr(obj, 'type', None) != 'MESH':
        return names
    for material in obj.data.materials:
        if material and material.get('wl_texture'):
            names.add(str(material['wl_texture']).casefold())
    try:
        records = json.loads(obj.data.get('wl_faces', '{}'))
        if isinstance(records, dict):
            for record in records.values():
                if isinstance(record, dict) and record.get('texture'):
                    names.add(str(record['texture']).casefold())
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return names


def is_sky(obj, engine):
    # GoldSrc sky brushes use the reserved SKY texture.  Classification is a
    # derived view: applying/removing SKY automatically changes this result.
    return profiles.is_goldsrc(engine) and 'sky' in brush_textures(obj)


def category(obj, engine):
    role = obj.get('wl_role')
    if role == 'MODEL_REFERENCE':
        if obj.parent and classname(obj.parent).casefold().startswith('prop_'):return None
        return 'MODEL_REFERENCES'
    if role == 'ENTITY':
        return 'PROPS' if classname(obj).casefold().startswith('prop_') else 'POINT_ENTITIES'
    if role == 'DISPLACEMENT':return 'DISPLACEMENTS'
    if role != 'BRUSH':
        return None
    special=special_kind(obj,engine)
    if special=='SKY': return 'SKY'
    if special in {'CLIP','ORIGIN','TRIGGER','HINT','SKIP','LIQUID'}: return 'SPECIAL_GEOMETRY'
    cls = classname(obj).casefold()
    if cls == 'func_detail':
        return 'DETAIL_BRUSHES'
    if obj.get('wl_entity_id'):
        return 'BRUSH_ENTITIES'
    return 'STRUCTURAL_BRUSHES'


CATEGORIES = (
    ('STRUCTURAL_BRUSHES', 'Structural Brushes', 'MESH_CUBE'),
    ('DETAIL_BRUSHES', 'Detail Brushes', 'MODIFIER'),
    ('SKY', 'Sky', 'WORLD'),
    ('SPECIAL_GEOMETRY', 'Special / Utility Geometry', 'MOD_WIREFRAME'),
    ('DISPLACEMENTS', 'Displacements', 'MOD_DISPLACE'),
    ('PROPS', 'Props', 'OUTLINER_OB_MESH'),
    ('POINT_ENTITIES', 'Point Entities', 'EMPTY_ARROWS'),
    ('BRUSH_ENTITIES', 'Brush Entities', 'OUTLINER_OB_MESH'),
    ('MODEL_REFERENCES', 'Model References', 'OUTLINER_COLLECTION'),
)


_group_cache = {}
_visibility_cache = {}


@persistent
def invalidate_groups(*_):
    """Scene edits invalidate classification; viewport redraws do not."""
    _group_cache.clear()
    _visibility_cache.clear()


def groups(scene):
    stamp = (scene.as_pointer(), scene.wavelength.engine, len(scene.objects))
    if stamp in _group_cache:
        return _group_cache[stamp]
    result = {key: [] for key, _label, _icon in CATEGORIES}
    engine = scene.wavelength.engine
    for obj in scene.objects:
        key = category(obj, engine)
        if key:
            result[key].append(obj)
    for objects in result.values():
        objects.sort(key=lambda obj: obj.name.casefold())
    _group_cache[stamp] = result
    return result


_HIDDEN_KEY = 'wl_system_hidden_categories'
_VIS_POLL_SECONDS = 0.12


def _hidden_categories(scene):
    try:
        value = json.loads(scene.get(_HIDDEN_KEY, '[]'))
        return {str(x) for x in value} if isinstance(value, list) else set()
    except (TypeError, ValueError, json.JSONDecodeError):
        return set()


def _set_hidden_categories(scene, values):
    scene[_HIDDEN_KEY] = json.dumps(sorted(set(values)))


def category_explicitly_hidden(scene, key):
    return key in _hidden_categories(scene)


def object_hidden(obj, view_layer=None):
    try:
        return bool(obj.hide_get(view_layer=view_layer)) if view_layer else bool(obj.hide_get())
    except (ReferenceError, RuntimeError, TypeError):
        return bool(getattr(obj, 'hide_viewport', False))


def set_object_hidden(obj, hidden, view_layer=None):
    for child in obj.children:
        if child.get('wl_model_reference') or child.get('wl_entity_icon_reference'):
            set_object_hidden(child,hidden,view_layer)
    try:
        # The visibility watcher also runs when nothing changed. Reapplying a
        # hide flag tags Blender's dependency graph and invalidates the viewport.
        if object_hidden(obj, view_layer) == bool(hidden):
            return
        if view_layer:
            obj.hide_set(bool(hidden), view_layer=view_layer)
        else:
            obj.hide_set(bool(hidden))
    except (ReferenceError, RuntimeError, TypeError):
        pass


def set_category_hidden(scene, key, hidden, view_layer=None):
    hidden_keys = _hidden_categories(scene)
    if hidden:
        hidden_keys.add(key)
    else:
        hidden_keys.discard(key)
    _set_hidden_categories(scene, hidden_keys)
    for obj in groups(scene).get(key, []):
        set_object_hidden(obj, hidden, view_layer)


def category_visibility(scene, key, view_layer=None, *, objects=None):
    # A tree redraw already classified the scene. Reuse that group instead of
    # rescanning and sorting the entire map once for every category's eye icon.
    if objects is None:
        objects = groups(scene).get(key, [])
    if not objects:
        return 'EMPTY'
    states = [not object_hidden(obj, view_layer) for obj in objects]
    if all(states):
        return 'VISIBLE'
    if any(states):
        return 'MIXED'
    return 'HIDDEN'


def tree_visibility(scene, key, view_layer, objects):
    """Reuse eye states until a dependency-graph edit changes visibility."""
    stamp = (scene.as_pointer(), view_layer.as_pointer(), key)
    if stamp not in _visibility_cache:
        _visibility_cache[stamp] = category_visibility(scene, key, view_layer, objects=objects)
    return _visibility_cache[stamp]


def _visibility_tick():
    # Only explicit Wavelength category hides have synchronization semantics.
    # If any member is externally revealed (e.g. normal Outliner), reveal the
    # entire category and clear the explicit category-off state.
    try:
        for scene in bpy.data.scenes:
            from . import context_state
            if context_state.viewport_hidden(scene):continue
            hidden_keys = _hidden_categories(scene)
            if not hidden_keys:
                continue
            grouped = groups(scene)
            changed = False
            for key in tuple(hidden_keys):
                objects = grouped.get(key, [])
                if not objects:
                    hidden_keys.discard(key); changed = True
                    continue
                if any(not object_hidden(obj) for obj in objects):
                    for obj in objects:
                        set_object_hidden(obj, False)
                    hidden_keys.discard(key); changed = True
                else:
                    # A delayed model preview must inherit its hidden entity.
                    for obj in objects:set_object_hidden(obj, True)
            if changed:
                _set_hidden_categories(scene, hidden_keys)
    except (ReferenceError, RuntimeError, AttributeError):
        pass
    return _VIS_POLL_SECONDS


def register():
    invalidate_groups()
    for handlers in (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.load_post,
                     bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
        if invalidate_groups not in handlers:handlers.append(invalidate_groups)
    from . import system_tree_view
    system_tree_view.register()
    if not bpy.app.timers.is_registered(_visibility_tick):
        bpy.app.timers.register(_visibility_tick, first_interval=_VIS_POLL_SECONDS, persistent=True)


def unregister():
    for handlers in (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.load_post,
                     bpy.app.handlers.undo_post, bpy.app.handlers.redo_post):
        if invalidate_groups in handlers:handlers.remove(invalidate_groups)
    invalidate_groups()
    from . import system_tree_view
    system_tree_view.unregister()
    if bpy.app.timers.is_registered(_visibility_tick):
        bpy.app.timers.unregister(_visibility_tick)

SPECIAL_TEXTURES_GOLDSRC={'sky':'SKY','clip':'CLIP','origin':'ORIGIN','aaatrigger':'TRIGGER','hint':'HINT','skip':'SKIP'}
SPECIAL_TEXTURES_QUAKE={'sky':'SKY','clip':'CLIP','trigger':'TRIGGER','hint':'HINT','skip':'SKIP','*water':'LIQUID','*lava':'LIQUID','*slime':'LIQUID'}

def special_kind(obj,engine):
    table=SPECIAL_TEXTURES_GOLDSRC if profiles.is_goldsrc(engine) else SPECIAL_TEXTURES_QUAKE if engine=='quake' else {}
    # Source has no classification rules in these legacy texture tables. Do not
    # decode every brush's face JSON merely to compare it against an empty table.
    if not table:return ''
    names=brush_textures(obj)
    kinds={kind for tex,kind in table.items() if any(name==tex or (tex.startswith('*') and name.startswith(tex)) for name in names)}
    return sorted(kinds)[0] if kinds else ''
