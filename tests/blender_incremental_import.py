"""Incremental staging keeps partial geometry out of the scene and rolls back."""
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import wavelength
wavelength.register()
from wavelength.source import scene,vmf
root=Path(__file__).resolve().parents[1]
document=vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
c=bpy.context;c.scene.wavelength.engine='source_hl2_windows';c.scene.wavelength.auto_prepare_assets=False
before=set(bpy.data.objects.keys());meshes=set(bpy.data.meshes.keys());collections=set(bpy.data.collections.keys())
iterator=scene.import_map_iter(c.scene,document,defer_assets=True)
kind,brush=next(iterator)
assert kind=='BRUSH' and brush.name not in c.scene.objects
iterator.close()
assert set(bpy.data.objects.keys())==before
assert set(bpy.data.meshes.keys())==meshes
assert set(bpy.data.collections.keys())==collections
assert not c.scene.get('wl_world_pairs')
iterator=scene.import_map_iter(c.scene,document,defer_assets=True)
while True:
    try:next(iterator)
    except StopIteration as result:
        collection=result.value;break
assert collection.name in c.scene.collection.children
exported=scene.export_map(c.scene)
assert sum(len(e.brushes) for e in exported.entities)==sum(len(e.brushes) for e in document.entities)
print('PASS incremental import: staged geometry, cancellation rollback, committed brush count and export',flush=True)
