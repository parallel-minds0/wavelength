"""Browser thumbnails never create scene Image IDs or template instances."""
import sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import profile_setup
from wavelength.source.entity import browser
c=bpy.context;c.preferences.use_preferences_save=False
s=c.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
s.fgd_path=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\bin\halflife2.fgd'
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);image=bpy.data.images.new('fixture',width=2,height=2,alpha=True)
 image.pixels[:]=[.25,.5,.75,1]*4;image.file_format='PNG';image.filepath_raw=str(root/'thumb.png');image.save();bpy.data.images.remove(image)
 reference=bpy.data.images.load(str(root/'thumb.png'));expected=list(reference.pixels);bpy.data.images.remove(reference)
 block=bpy.data.objects.new('Unlinked preview',None);block.asset_mark()
 before=set(bpy.data.images)
 assert profile_setup.apply(block,root,'ENTITY:light','thumb.png')
 assert set(bpy.data.images)==before
 assert tuple(block.preview.image_size)==(2,2)
 assert max(abs(a-b) for a,b in zip(block.preview.image_pixels_float,expected))<.01,(list(block.preview.image_pixels_float[:4]),expected[:4])
 assert not profile_setup.apply(block,root,'ENTITY:light','thumb.png')
count=len(c.scene.objects);published=browser.rebuild(c)
col=browser._asset_collection(c.scene);pointers={o.as_pointer() for o in col.objects}
assert published>100 and len(c.scene.objects)==count
assert browser.rebuild(c)==published and pointers=={o.as_pointer() for o in col.objects}
assert col.use_fake_user and all(col not in sc.collection.children_recursive for sc in bpy.data.scenes)
print('PASS thumbnail pixels without Image IDs; unlinked persistent templates; repeated browser switch reuses IDs',flush=True)
