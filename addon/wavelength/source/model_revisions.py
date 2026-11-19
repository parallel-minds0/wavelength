"""Named model checkpoints stored as portable editable asset packages."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bpy


def records(asset):
    return json.loads(asset.get('wl_model_revisions', '[]'))


def save(context, asset, label):
    from .model_transfer import export_package

    label = label.strip()
    if not label:
        raise ValueError('Enter a revision name')
    project = context.scene.wavelength.project_dir
    if not project:
        raise ValueError('Choose a project directory before saving model revisions')
    folder = Path(bpy.path.abspath(project)) / '.wavelength' / 'model-revisions' / asset['wl_model_id']
    folder.mkdir(parents=True, exist_ok=True)
    identity = uuid.uuid4().hex
    path = folder / (identity + '.wlmodel')
    export_package(context, asset, str(path))
    entry = {
        'id': identity,
        'name': label,
        'created': datetime.now(timezone.utc).isoformat(),
        'path': str(path),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    asset['wl_model_revisions'] = json.dumps([*records(asset), entry])
    return entry


def open_variant(context, asset, identity, *, pose=None):
    from . import model_bundle, model_lifecycle
    from mathutils import Matrix

    entry = next((entry for entry in records(asset) if entry['id'] == identity), None)
    if entry is None:
        raise ValueError('The selected revision is unavailable')
    path = Path(bpy.path.abspath(entry['path']))
    if not path.is_file():
        raise ValueError('Revision package is missing: ' + str(path))
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError('Revision package has changed; choose the original checkpoint file')
    origin = asset.wavelength_model.origin
    if pose is None:
        pose = origin.matrix_world.copy() if origin else Matrix.Identity(4)
    variant = model_bundle.import_asset(context, str(path))
    variant.name = asset.name + ' · ' + entry['name']
    variant['wl_model_revision_source'] = entry['id']
    variant['wl_model_parent_id'] = asset['wl_model_id']
    variant.pop('wl_model_revisions', None)
    variant.pop('wl_model_publish_settings', None)
    imported_origin = variant.wavelength_model.origin
    if imported_origin:
        imported_origin.matrix_world = pose
    context.view_layer.update()
    model_lifecycle.select_sources(context, variant)
    return variant


def restore_placement(context, asset, identity):
    from . import model_lifecycle

    entity = model_lifecycle.entity_for(context.object)
    if entity is None or entity.get('wl_custom_model') != asset:
        raise ValueError('Select a placement attached to this model asset')
    from .model_transfer import KINDS

    pose = entity.matrix_world.copy()
    selected = list(context.selected_objects)
    active = context.view_layer.objects.active
    before = {kind: set(getattr(bpy.data, kind)) for kind in KINDS}
    try:
        variant = open_variant(context, asset, identity, pose=pose)
        # Validate and checkpoint before releasing the current placement.
        model_lifecycle._validate(context, variant, entity)
        save(context, asset, 'Before revision restore')
        history = records(asset)
    except Exception:
        for kind in KINDS:
            collection = getattr(bpy.data, kind)
            for item in tuple(collection):
                if item not in before[kind]:
                    if kind in {'objects', 'scenes', 'collections'}:
                        collection.remove(item, do_unlink=True)
                    else:
                        collection.remove(item)
        for obj in context.selected_objects:
            obj.select_set(False)
        for obj in selected:
            if obj.name in context.view_layer.objects:
                obj.select_set(True)
        context.view_layer.objects.active = active
        raise
    model_lifecycle.attach(context, variant, entity)
    variant['wl_model_revisions'] = json.dumps(history)
    variant['wl_model_status'] = 'Editable · restored revision'
    return variant
