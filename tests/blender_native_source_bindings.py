"""Native Source references allocate no model meshes, Images, or shader nodes.

Run with WL_SOURCE_GAME set to a mounted HL2 installation. Stock Blender can
exercise the binding contract; the native UI check additionally verifies drawing.
"""
import json,os,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import native_source,source_assets,model_import,studio_model,asset_loading
from wavelength.source.entity import models
c=bpy.context;c.preferences.use_preferences_save=False
c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=os.environ.get('WL_SOURCE_GAME',r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete')
before=(len(bpy.data.meshes),len(bpy.data.images))
with patch.object(native_source,'enabled',return_value=True),patch.object(model_import,'mesh',side_effect=AssertionError('Blender mesh conversion called')),patch.object(studio_model,'load',side_effect=AssertionError('Python model decoding called')),patch.object(source_assets,'decoded_preview',side_effect=AssertionError('Python texture decoding called')):
    mat=source_assets.material(s,'brick/brickwall001a',defer=True)
    assert mat.get('wl_source_native_material')=='brick/brickwall001a'
    assert not any(n.type=='TEX_IMAGE' for n in mat.node_tree.nodes)
    assert mat['wl_width']>0 and mat['wl_height']>0
    assert not mat.get('wl_source_pending') and not asset_loading._waiting
    for i in range(10):
        obj=bpy.data.objects.new('Native prop '+str(i),None);c.collection.objects.link(obj)
        obj['wl_role']='ENTITY';obj['wl_pairs']=json.dumps([['classname','prop_static'],['model','models/props_c17/oildrum001.mdl']])
        asset_loading.entity(c.scene,obj)
        assert len(obj.children)==1 and obj.children[0].type=='EMPTY'
        ref=obj.children[0];assert ref.get('wl_source_native_model')=='models/props_c17/oildrum001.mdl'
        assert ref.parent==obj and ref.get('wl_source_mounts') and not obj.get('wl_representation_pending')
    assert before==(len(bpy.data.meshes),len(bpy.data.images))
    c.view_layer.update()
    assert native_source.hit(c,Vector((0,-5,.5)),Vector((0,1,0))) is not None
    assert native_source.hit(c,Vector((0,-5,.5)),Vector((0,1,0)),.1) is None
assert not asset_loading._waiting
print('PASS native Source bindings: 10 instances, zero mesh/image conversion, original material dimensions, no decode worker',flush=True)
