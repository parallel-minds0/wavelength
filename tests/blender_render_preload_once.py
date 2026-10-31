"""One dependency-closure load; repeat requests/mode switches reuse live assets."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import source_assets,native_source,render_bundle,render_support
c=bpy.context;s=c.scene.wavelength
s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
for i,name in enumerate(('brick/brickwall001a','tools/toolsnodraw')):
    bpy.ops.mesh.primitive_cube_add(location=(i*3,0,0))
    c.object.data.materials.append(source_assets.material(s,name))
for i in range(3):
    entity=bpy.data.objects.new('Shared barrel '+str(i),None);c.collection.objects.link(entity)
    entity['wl_role']='ENTITY';entity['wl_pairs']=json.dumps([['classname','prop_static'],['model','models/props_c17/oildrum001.mdl']])
    native_source.attach(entity,'models/props_c17/oildrum001.mdl')
def counts():return len(bpy.data.images),len(bpy.data.meshes),len(bpy.data.materials),len(bpy.data.objects)
initial=counts();request=render_bundle.Request(c.scene);start=time.monotonic()
while not request.poll():
    assert counts()==initial,'Polling prepared assets changed live Blender datablocks'
    assert time.monotonic()-start<60,'Preload worker did not complete'
    time.sleep(.02)
assert counts()==initial
request.publish();assert request.library_loads==1
references=[o for o in c.scene.objects if o.type=='MESH' and o.get('wl_model_reference')]
assert len(references)==3 and len({o.data.as_pointer() for o in references})==1
loaded=counts()
for _ in range(5):
    assert request.poll();request.publish()
    assert counts()==loaded and request.library_loads==1
assert not render_support.prepare(c.scene),'Already-loaded map queued a second preload'
native_source.migrate(c.scene)
assert counts()==loaded,'Opening an already-preloaded scene rebuilt assets'
for area in c.screen.areas:
    if area.type=='VIEW_3D':
        for mode in ('MATERIAL','SOLID','RENDERED','MATERIAL'):
            area.spaces.active.shading.type=mode;render_support.tick()
            assert not render_support._jobs and counts()==loaded
request.close()
print('PASS preload once: no live-ID churn while polling; one library load; shared prop mesh; idempotent bind; mode switching and migration reuse assets',flush=True)
