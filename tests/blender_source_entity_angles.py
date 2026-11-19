"""Compare Source QAngle import/export against Valve AngleMatrix coefficients."""
import sys,math,json,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Matrix
wavelength.register()
from wavelength.source import source_pose as pose,scene,formats
c=bpy.context;c.preferences.use_preferences_save=False
s=c.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete'
def reference(pitch,yaw,roll):
 sp,cp=math.sin(math.radians(pitch)),math.cos(math.radians(pitch));sy,cy=math.sin(math.radians(yaw)),math.cos(math.radians(yaw));sr,cr=math.sin(math.radians(roll)),math.cos(math.radians(roll))
 return Matrix(((cp*cy,sp*sr*cy-cr*sy,sp*cr*cy+sr*sy),(cp*sy,sp*sr*sy+cr*cy,sp*cr*sy-sr*cy),(-sp,sr*cp,cr*cp)))
def close(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(3) for j in range(3))<2e-5
rng=random.Random(18)
for p,y,r in [(0,90,0),(90,0,0),(0,0,90),(33,142,-27),(-90,225,40),*(tuple(rng.uniform(-360,360) for i in range(3)) for j in range(100))]:
 pairs=[('classname','prop_dynamic'),('angles',f'{p} {y} {r}')]
 assert close(pose.rotation(pairs).to_matrix(),reference(p,y,r))
 obj=bpy.data.objects.new('Pose check',None);c.collection.objects.link(obj);pose.apply(obj,pairs,force=True);c.view_layer.update()
 assert pose.export_pairs(obj,pairs)==pairs
 obj.rotation_euler.rotate_axis('Z',.3);c.view_layer.update()
 exported=pose.export_pairs(obj,pairs)
 assert close(pose.rotation(exported).to_matrix(),obj.matrix_world.to_quaternion().to_matrix())
 bpy.data.objects.remove(obj,do_unlink=True)
cube=bpy.data.objects['Cube'];scene.mark_brush(cube)
mat=bpy.data.materials.new('Angle test nodraw');mat['wl_texture']='tools/toolsnodraw';cube.data.materials.clear();cube.data.materials.append(mat)
pairs=[('classname','info_target'),('origin','128 256 64'),('angles','25 120 -35')]
scene.import_map(c.scene,formats.Map([formats.Entity([('classname','worldspawn')],[]),formats.Entity(pairs,[])]),defer_assets=False)
obj=next(o for o in c.scene.objects if o.get('wl_role')=='ENTITY')
c.view_layer.update();assert close(obj.matrix_world.to_quaternion().to_matrix(),reference(25,120,-35))
exported=scene.export_map(c.scene);entity=next(e for e in exported.entities if dict(e.pairs).get('classname')=='info_target')
assert dict(entity.pairs)['angles']=='25 120 -35'
obj.rotation_euler.rotate_axis('Z',.3);c.view_layer.update()
exported=scene.export_map(c.scene);entity=next(e for e in exported.entities if dict(e.pairs).get('classname')=='info_target')
assert close(pose.rotation(entity.pairs).to_matrix(),obj.matrix_world.to_quaternion().to_matrix())
# A model-only refresh with unchanged keys must not undo a Blender rotation.
world=obj.matrix_world.copy();pose.apply(obj,pairs);c.view_layer.update();assert close(obj.matrix_world.to_quaternion().to_matrix(),world.to_quaternion().to_matrix())
print('PASS Valve AngleMatrix agreement: cardinal, mixed axes, gimbal cases, 100 random rotations; real entity import/export; rotated export; model refresh preserves edits',flush=True)



# Legacy scalar keys crash the installed HL2 server through recursive KeyValue.
from wavelength.source import vmf
for scalar,expected in [('90','0 90 0'),('-1','-90 0 0'),('-2','90 0 0'),('0','0 0 0')]:
 pairs=[('classname','info_player_start'),('angle',scalar),('targetname','retained')]
 original=list(pairs)
 canonical=pose.canonical_pairs(pairs)
 assert 'angle' not in dict(canonical) and dict(canonical)['angles']==expected
 assert pairs==original and dict(canonical)['targetname']=='retained'
 assert close(pose.rotation(pairs).to_matrix(),pose.rotation(canonical).to_matrix())
 document=formats.Map([formats.Entity([('classname','worldspawn')],[]),formats.Entity(pairs,[])])
 written=vmf.write(document)
 assert '"angle"' not in written and f'"angles" "{expected}"' in written
 obj=bpy.data.objects.new('Legacy angle',None);c.collection.objects.link(obj)
 pose.apply(obj,pairs,force=True);c.view_layer.update()
 assert dict(pose.export_pairs(obj,pairs))['angles']==expected
 bpy.data.objects.remove(obj,do_unlink=True)
assert pose.canonical_pairs([('angle','90'),('angles','15 20 30')])==[('angles','15 20 30')]
print('PASS legacy Source angle normalization, vertical sentinels, VMF output and unchanged authoring pairs')
