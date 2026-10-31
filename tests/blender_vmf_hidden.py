"""Hidden world solids, brush entities and point entities survive interchange."""
import copy
import json
import sys
from pathlib import Path

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
import wavelength
wavelength.register()
from wavelength.source import formats, scene, vmf

root = Path(__file__).resolve().parents[1]
base = vmf.parse((root / 'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
brush = copy.deepcopy(base.entities[0].brushes[0])
for face in brush:
    face.vmf['hidden'] = True
document = formats.Map([
    formats.Entity([('classname', 'worldspawn')], [brush]),
    formats.Entity([('classname', 'func_detail')], [copy.deepcopy(brush)], vmf_hidden=True),
    formats.Entity([('classname', 'info_target'), ('origin', '128 64 32'),
                    (vmf.OUTPUT + 'OnUser1', 'target\x1bUse\x1b\x1b0\x1b-1')], vmf_hidden=True),
])

def signature(doc):
    return [(e.vmf_hidden, [any((f.vmf or {}).get('hidden') for f in b) for b in e.brushes]) for e in doc.entities]

decoded = vmf.parse(vmf.write(document))
assert signature(decoded) == signature(document)
assert dict(decoded.entities[-1].pairs)[vmf.OUTPUT + 'OnUser1'] == dict(document.entities[-1].pairs)[vmf.OUTPUT + 'OnUser1']
c = bpy.context
c.scene.wavelength.engine = 'source_hl2_windows'
c.scene.wavelength.auto_prepare_assets = False
collection = scene.import_map(c.scene, decoded, defer_assets=True)
assert all(obj.hide_get() for obj in collection.objects if obj.get('wl_role') in {'BRUSH', 'ENTITY'})
exported = vmf.parse(vmf.write(scene.export_map(c.scene)))
assert signature(exported) == signature(document), signature(exported)

# Reject unknown payloads instead of treating hidden as a validation escape.
try:
    vmf.parse('world { "classname" "worldspawn" hidden { unsupported {} } }')
except ValueError as exc:
    assert 'unsupported' in str(exc)
else:
    raise AssertionError('Unknown hidden payload accepted')
print('PASS hidden VMF: world/brush/point containers, Blender visibility, output connections, scene round trip and strict validation', flush=True)

if '--map' in sys.argv:
    path = Path(sys.argv[sys.argv.index('--map') + 1])
    actual = vmf.parse(path.read_text(encoding='utf-8-sig'))
    roundtrip = vmf.parse(vmf.write(actual))
    assert signature(actual) == signature(roundtrip)
    assert sum(len(b) for e in actual.entities for b in e.brushes) == sum(len(b) for e in roundtrip.entities for b in e.brushes)
    print('PASS actual map:', path, 'entities', len(actual.entities), 'hidden entities', sum(e.vmf_hidden for e in actual.entities), 'hidden brushes', sum(any((f.vmf or {}).get('hidden') for f in b) for e in actual.entities for b in e.brushes), flush=True)
