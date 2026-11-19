"""Exercise attached Source 1 model preflight without StudioMDL or a game install."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import wavelength
from wavelength.source import custom_models, textures

wavelength.register()
ctx = bpy.context
ctx.workspace['wl_workspace'] = True
settings = ctx.scene.wavelength
with patch.object(textures, 'refresh'):
    settings.engine = 'source_hl2_windows'
bpy.ops.mesh.primitive_cube_add()
mesh = ctx.object
mesh.name = 'Preflight cube'
entity = bpy.data.objects.new('Preflight prop', None)
ctx.collection.objects.link(entity)
entity['wl_role'] = 'ENTITY'
entity['wl_pairs'] = json.dumps([['classname', 'prop_static']])
entity['wl_unit_meters'] = 0.0254
entity.select_set(True)
ctx.view_layer.objects.active = entity
definition = custom_models.assign(ctx, validate_schema=False)
fixture = [(tuple(v.co)) for v in mesh.data.vertices]
subsurf = mesh.modifiers.new('Evaluated geometry', 'SUBSURF')
subsurf.levels = 1
with patch.object(custom_models, 'stage_game', side_effect=AssertionError('Preflight staged a build')):
    assert bpy.ops.wavelength.custom_model_preflight() == {'FINISHED'}
    report = bpy.data.texts['wavelength Model Preflight']
    assert 'Preflight cube: 48 evaluated triangles' in report.as_string(), report.as_string()
    assert [(tuple(v.co)) for v in mesh.data.vertices] == fixture
    assert ctx.view_layer.objects.active == entity
    for layer in list(mesh.data.uv_layers):
        mesh.data.uv_layers.remove(layer)
    mesh.data.update()
    ctx.view_layer.update()
    try:
        bpy.ops.wavelength.custom_model_preflight()
    except RuntimeError as exc:
        assert 'UV unwrap the model before compiling: Preflight cube' in str(exc)
    else:
        raise AssertionError('Missing UV accepted')
    assert 'UV unwrap' in report.as_string()
print('PASS Source 1 model preflight')
