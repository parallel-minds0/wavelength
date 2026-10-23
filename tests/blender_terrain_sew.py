import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_sew as sew,terrain_paint as paint,scene,vmf,formats,primitives
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True;ctx.scene.wavelength.engine='source_gmod_windows'
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
unit=.0254
material=bpy.data.materials.new('Transition');material['wl_texture']='concrete/blendconcdirt003a';material['wl_source_blend']=True
def make(name,a,b,u,v,n,power):
    obj=terrain.create_footprint(ctx,Vector(a)*unit,Vector(b)*unit,Vector(u),Vector(v),Vector(n));obj.name=name
    terrain.enable_paint(obj);obj.wavelength_terrain.tiles_x=obj.wavelength_terrain.tiles_y=1;obj.wavelength_terrain.power=power
    obj.data.materials.append(material);terrain.sync_material(obj,True)
    return obj
left=make('Floor left',(-256,-128,0),(0,128,0),(1,0,0),(0,1,0),(0,0,1),'2')
right=make('Floor right',(0,-128,0),(256,128,0),(1,0,0),(0,1,0),(0,0,1),'3')
wall=make('Cave wall',(256,128,0),(256,-128,256),(0,-1,0),(0,0,1),(-1,0,0),'3')
ceiling=make('Cave ceiling',(0,128,256),(256,-128,256),(1,0,0),(0,-1,0),(0,0,-1),'4')
items=[left,right,wall,ceiling]
right.wavelength_terrain.resolution=129;ceiling.wavelength_terrain.resolution=33
left.wavelength_terrain.amplitude=8;right.wavelength_terrain.amplitude=5;wall.wavelength_terrain.amplitude=3;ceiling.wavelength_terrain.amplitude=8
# Start with mismatched geometry along a matching base edge.
paint.stroke(left,Vector((128*unit,0,0)),'RAISE',2,.2,.5)
assert sew.sew(items)==3
assert len(sew.network(left))==4
sew.validate_export(left)
surfaces={o:sew.Surface(o) for o in items}
def edge_uv(edge,t):return ((t,0),(1,t),(1-t,1),(0,1-t))[edge]
for a,ae,b,be,reverse in sew.pairs(items):
    for i in range(257):
        t=i/256;pa=surfaces[a].sample(*edge_uv(ae,t))[0];pb=surfaces[b].sample(*edge_uv(be,1-t if reverse else t))[0]
        assert (a.matrix_world@pa-b.matrix_world@pb).length<1e-5
print('PASS world-space sewing across separate floor, wall and ceiling objects with mixed Source powers',flush=True)
base=sew.frames(items);before=[p.copy() for p in sew.positions(wall,base[wall])]
assert paint.network_stroke(items,base,Vector((256*unit,0,0)),Vector((-1,0,1)).normalized(),'RAISE',2,.3,.5)>0
sew.validate_export(left)
after=sew.positions(wall,base[wall]);assert any((a-b).length>.01 for a,b in zip(before,after))
assert any(abs(d.vector.x)>.001 for d in right.data.attributes['wl_terrain_vector'].data)
paint.network_stroke(items,base,Vector((256*unit,0,0)),Vector((-1,0,1)).normalized(),'TEXTURE',2,.3,.8)
paint.network_stroke(items,base,Vector((256*unit,0,0)),Vector((-1,0,1)).normalized(),'SMOOTH',2,.3,.25)
sew.validate_export(left)
print('PASS continuous vector sculpting, texture painting and smoothing preserve shared edges',flush=True)
assert sew.sew(items,smooth=True)==3;sew.validate_export(left)
doc=scene.export_map(ctx.scene);assert len(doc.entities[0].brushes)==4
assert all(b[0].vmf.get('dispinfo') for b in doc.entities[0].brushes)
assert any(max(r)>0 for b in doc.entities[0].brushes for r in b[0].vmf['dispinfo']['alphas'])
print('PASS UV-domain Source displacement export includes sideways movement and painted alpha',flush=True)
# Reconstruct each Source edge from VMF normals/distances, then compare samples
# along the shared geometric edge (including interpolated coarser-power segments).
def reconstruct(obj):
    parts=terrain.brushes(obj);info=parts[0][0].vmf['dispinfo'];q=[obj.matrix_world@p/unit for p in sew.quad(obj)];size=2**info['power']+1;rows=[]
    for j in range(size):
        row=[]
        for i in range(size):
            u=i/(size-1);v=j/(size-1);p=q[0]*((1-u)*(1-v))+q[1]*(u*(1-v))+q[2]*(u*v)+q[3]*((1-u)*v)
            p+=Vector(info['normals'][j][i*3:i*3+3])*info['distances'][j][i];row.append(p)
        rows.append(row)
    return [rows[0],[r[-1] for r in rows],rows[-1][::-1],[r[0] for r in rows[::-1]]]
out={o:reconstruct(o) for o in items}
for a,ae,b,be,reverse in sew.pairs(items):
    aa=out[a][ae];bb=out[b][be][::-1] if reverse else out[b][be]
    def sample(row,t):
        x=t*(len(row)-1);lo=int(x);hi=min(len(row)-1,lo+1);return row[lo].lerp(row[hi],x-lo)
    assert max((sample(aa,i/64)-sample(bb,i/64)).length for i in range(65))<.01
print('PASS exported VMF edges match between powers 2, 3 and 4, including interpolation',flush=True)
right.wavelength_terrain.power='2'
try:sew.validate_export(left)
except ValueError as exc:assert 'sampling changed' in str(exc)
else:raise AssertionError('Changed Source sample lattice silently accepted')
right.wavelength_terrain.power='3';sew.validate_export(left)
folder=Path(__file__).resolve().parents[1]/'build/terrain-sew';folder.mkdir(exist_ok=True)
for bounds in [(-800,-800,-272,800,800,-256),(-800,-800,512,800,800,528),(-800,-800,-256,-784,800,512),(784,-800,-256,800,800,512),(-784,-800,-256,784,-784,512),(-784,784,-256,784,800,512)]:
    vertices,faces=primitives.box(*bounds);brush=[]
    for face in faces:
        f=formats.Face([list(vertices[i]) for i in (face[0],face[2],face[1])],'tools/toolsnodraw',[0,0,0,1,1]);f.axes=formats.quake_axes(f.plane()[0],f.projection);brush.append(f)
    doc.entities[0].brushes.append(brush)
doc.entities[0].pairs.append(('skyname','sky_day01_01'));doc.entities.append(formats.Entity([('classname','info_player_start'),('origin','0 0 128')],[]))
(folder/'sewn-cave.vmf').write_text(vmf.write(doc),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'sewn.blend'));bpy.ops.wm.open_mainfile(filepath=str(folder/'sewn.blend'))
left=bpy.context.scene.objects['Floor left'];right=bpy.context.scene.objects['Floor right'];wall=bpy.context.scene.objects['Cave wall'];ceiling=bpy.context.scene.objects['Cave ceiling'];items=sew.network(left)
assert len(items)==4;sew.validate_export(left)
print('PASS saved neighbour links, vector fields and node graph reload',flush=True)
left.wavelength_terrain.flat_preview=True
# Export temporarily disables both the height and vector placement previews.
sew.validate_export(left);assert left.wavelength_terrain.flat_preview
left.wavelength_terrain.flat_preview=False
for obj in items:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    assert bpy.ops.wavelength.terrain_finalize()=={'FINISHED'}
sew.validate_export(left);assert len(scene.export_map(bpy.context.scene).entities[0].brushes)==4
print('PASS flat preview is ignored for export and finalized networks preserve shared surfaces',flush=True)
wall.location.x+=1;bpy.context.view_layer.update()
try:sew.validate_export(left)
except ValueError as exc:assert 'moved apart' in str(exc)
else:raise AssertionError('Moved seam silently exported')
wall.location.x-=1;bpy.context.view_layer.update()
sew.unsew([wall]);assert len(sew.network(left))==2 and not sew.links(ceiling)
assert wall.get('wl_terrain_vector_surface')
print('PASS moved seams rejected; Unsew retains deformed geometry',flush=True)

# The same system must attach Source dispinfo to original sides of distinct
# brushes, rather than replacing them with independent backing solids.
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
material=bpy.data.materials['Transition']
import bmesh
from wavelength.source import terrain_face
def attached(name,bounds,axis):
    vertices,faces=primitives.box(*bounds);mesh=bpy.data.meshes.new(name);mesh.from_pydata([[c*unit for c in p] for p in vertices],[],faces);mesh.update();mesh.materials.append(material)
    source=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(source);scene.mark_brush(source)
    bpy.ops.object.select_all(action='DESELECT');source.select_set(True);bpy.context.view_layer.objects.active=source;bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(mesh)
    for face in bm.faces:face.select_set(False)
    max(bm.faces,key=lambda f:f.normal.dot(Vector(axis))).select_set(True);bmesh.update_edit_mesh(mesh)
    return terrain_face.create(bpy.context),source
a,ab=attached('Brush floor left',(-256,-128,-32,0,128,0),(0,0,1))
b,bb=attached('Brush floor right',(0,-128,-32,256,128,0),(0,0,1))
c,cb=attached('Brush cave wall',(256,-128,0,288,128,256),(-1,0,0))
d,db=attached('Brush cave ceiling',(0,-128,256,256,128,288),(0,0,-1))
for obj in (a,b,c,d):obj.wavelength_terrain.amplitude=8
assert sew.sew([a,b,c,d])==3
base=sew.frames([a,b,c,d]);paint.network_stroke([a,b,c,d],base,Vector((256*unit,0,0)),Vector((-1,0,1)).normalized(),'RAISE',2,.2,.5)
sew.validate_export(a);document=scene.export_map(bpy.context.scene)
assert len(document.entities[0].brushes)==4 and all(len(brush)==6 for brush in document.entities[0].brushes)
assert sum(bool(f.vmf and f.vmf.get('dispinfo')) for brush in document.entities[0].brushes for f in brush)==4
print('PASS stitched cave made from four distinct original brush faces preserves the original solids',flush=True)
(folder/'sewn-brush-cave.vmf').write_text(vmf.write(formats.Map([formats.Entity(doc.entities[0].pairs,document.entities[0].brushes+doc.entities[0].brushes[-6:]),doc.entities[-1]])),encoding='utf-8')

# General Blender terrain uses the same adjacency system without Source output.
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.scene.wavelength.engine='blender'
def plane(a,b):
    obj=terrain.create_footprint(bpy.context,Vector(a),Vector(b),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));terrain.enable_paint(obj);return obj
x=plane((-4,-2,0),(0,2,0));y=plane((0,-2,0),(4,2,0));z=plane((4,-2,0),(8,0,0))
try:sew.sew([y,z])
except ValueError as exc:assert 'full base edge' in str(exc)
else:raise AssertionError('Partial edge silently sewn')
assert not y.get('wl_terrain_seams') and not z.get('wl_terrain_vector_surface')
assert sew.sew([x,y])==1
base=sew.frames([x,y]);paint.network_stroke([x,y],base,Vector(),Vector((0,0,1)),'RAISE',1,.2,.5);sew.validate_export(x)
print('PASS Blender-owned sewing and early rejection of unsupported partial-edge joins',flush=True)
p=plane((-4,2,0),(0,6,0));q=plane((0,2,0),(4,6,0));assert sew.sew([x,y,p,q])==4
base=sew.frames([x,y,p,q]);paint.network_stroke([x,y,p,q],base,Vector((0,2,0)),Vector((0,0,1)),'RAISE',1,.4,.5);sew.validate_export(x)
print('PASS four-way shared corner stays closed during painting',flush=True)
