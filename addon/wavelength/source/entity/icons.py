"""Editor-only, screen-facing SVG sprites for abstract point entities.

The Wavelength HL1 icon pack is parsed directly.  Do not depend on Blender's
optional SVG import extension: viewport icons are drawn as flat 2D artwork.
"""
from pathlib import Path
import json, math, re, xml.etree.ElementTree as ET
import bpy

from ..paths import SPRITE_ROOT
ICON_ROOT = SPRITE_ROOT
_CACHE = {}
_MANIFEST_CACHE = None
_MANIFEST_MTIME = None
_NUM = re.compile(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')
SPRITE_SIZE = 46  # Screen pixels at 100% UI scale; 15% above the original 40.


def _manifest():
    global _MANIFEST_CACHE, _MANIFEST_MTIME
    path = ICON_ROOT / 'manifest.json'
    if not path.is_file():
        _MANIFEST_CACHE = {}; _MANIFEST_MTIME = None; return {}
    try:
        mtime = path.stat().st_mtime_ns
        if _MANIFEST_CACHE is not None and _MANIFEST_MTIME == mtime:return _MANIFEST_CACHE
        data = json.loads(path.read_text(encoding='utf-8'))
        mapping = data.get('entities', {}) if isinstance(data, dict) else {}
        _MANIFEST_CACHE = mapping if isinstance(mapping, dict) else {}
        _MANIFEST_MTIME = mtime
    except (OSError, ValueError, TypeError):
        _MANIFEST_CACHE = {}; _MANIFEST_MTIME = None
    return _MANIFEST_CACHE


def icon_path(classname):
    name = _manifest().get((classname or '').strip())
    if not name:return None
    path = ICON_ROOT / 'icons' / str(name)
    return path if path.is_file() and path.suffix.lower() == '.svg' else None


def has_icon(classname):return icon_path(classname) is not None

def _pt(x,y):return (float(x), -float(y))
def _dist(a,b):return math.hypot(b[0]-a[0], b[1]-a[1])
def _cubic(p0,p1,p2,p3,n=10):
    out=[]
    for i in range(1,n+1):
        t=i/n;u=1-t
        out.append((u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0],
                    u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]))
    return out

def _arc(p0, rx, ry, rot, large, sweep, p1, n=12):
    # SVG endpoint-to-center conversion, sufficient for the icon pack's arcs.
    rx=abs(rx);ry=abs(ry)
    if rx < 1e-9 or ry < 1e-9:return [p1]
    phi=math.radians(rot%360);cp=math.cos(phi);sp=math.sin(phi)
    dx=(p0[0]-p1[0])/2;dy=(p0[1]-p1[1])/2
    xp=cp*dx+sp*dy;yp=-sp*dx+cp*dy
    lam=xp*xp/(rx*rx)+yp*yp/(ry*ry)
    if lam>1:
        q=math.sqrt(lam);rx*=q;ry*=q
    den=(rx*yp)**2+(ry*xp)**2
    coef=0 if den<1e-12 else math.sqrt(max(0,((rx*ry)**2-(rx*yp)**2-(ry*xp)**2)/den))
    if bool(large)==bool(sweep):coef=-coef
    cxp=coef*(rx*yp/ry);cyp=coef*(-ry*xp/rx)
    cx=cp*cxp-sp*cyp+(p0[0]+p1[0])/2;cy=sp*cxp+cp*cyp+(p0[1]+p1[1])/2
    def angle(u,v):return math.atan2(u[0]*v[1]-u[1]*v[0],u[0]*v[0]+u[1]*v[1])
    u=((xp-cxp)/rx,(yp-cyp)/ry);v=((-xp-cxp)/rx,(-yp-cyp)/ry)
    a0=math.atan2(u[1],u[0]);da=angle(u,v)
    if not sweep and da>0:da-=2*math.pi
    if sweep and da<0:da+=2*math.pi
    n=max(n,int(abs(da)*8))
    return [(cx+rx*math.cos(a0+da*i/n)*cp-ry*math.sin(a0+da*i/n)*sp,
             cy+rx*math.cos(a0+da*i/n)*sp+ry*math.sin(a0+da*i/n)*cp) for i in range(1,n+1)]

def _path_polylines(d):
    toks=_NUM.findall(d or '');i=0;cmd=None;cur=(0.,0.);start=cur;last_ctrl=None;line=[];out=[]
    def flush(closed=False):
        nonlocal line
        if len(line)>1:out.append((line,closed))
        line=[]
    def num():
        nonlocal i
        v=float(toks[i]);i+=1;return v
    while i<len(toks):
        if toks[i].isalpha():cmd=toks[i];i+=1
        if not cmd:break
        rel=cmd.islower();C=cmd.upper()
        try:
            if C=='M':
                x,y=num(),num();p=(cur[0]+x,cur[1]+y) if rel else (x,y)
                if line:flush()
                cur=start=p;line=[p];last_ctrl=None;cmd='l' if rel else 'L'
            elif C=='L':
                x,y=num(),num();p=(cur[0]+x,cur[1]+y) if rel else (x,y);line.append(p);cur=p;last_ctrl=None
            elif C=='H':
                x=num();p=(cur[0]+x,cur[1]) if rel else (x,cur[1]);line.append(p);cur=p;last_ctrl=None
            elif C=='V':
                y=num();p=(cur[0],cur[1]+y) if rel else (cur[0],y);line.append(p);cur=p;last_ctrl=None
            elif C=='C':
                x1,y1,x2,y2,x,y=[num() for _ in range(6)]
                p1=(cur[0]+x1,cur[1]+y1) if rel else (x1,y1);p2=(cur[0]+x2,cur[1]+y2) if rel else (x2,y2);p3=(cur[0]+x,cur[1]+y) if rel else (x,y)
                line.extend(_cubic(cur,p1,p2,p3));cur=p3;last_ctrl=p2
            elif C=='S':
                x2,y2,x,y=[num() for _ in range(4)];p1=(2*cur[0]-last_ctrl[0],2*cur[1]-last_ctrl[1]) if last_ctrl else cur
                p2=(cur[0]+x2,cur[1]+y2) if rel else (x2,y2);p3=(cur[0]+x,cur[1]+y) if rel else (x,y)
                line.extend(_cubic(cur,p1,p2,p3));cur=p3;last_ctrl=p2
            elif C=='A':
                rx,ry,rot,large,sweep,x,y=[num() for _ in range(7)];p=(cur[0]+x,cur[1]+y) if rel else (x,y)
                line.extend(_arc(cur,rx,ry,rot,int(large),int(sweep),p));cur=p;last_ctrl=None
            elif C=='Z':
                if line and line[-1]!=start:line.append(start)
                cur=start;flush(True);last_ctrl=None;cmd=None
            else:break
        except (ValueError,IndexError):break
    if line:flush()
    return out

def _style(el, inherited):
    s=dict(inherited);raw=el.get('style','')
    for item in raw.split(';'):
        if ':' in item:
            k,v=item.split(':',1);s[k.strip()]=v.strip()
    for k in ('fill','stroke','stroke-width'):
        if el.get(k) is not None:s[k]=el.get(k)
    return s

def _svg_geometry(path):
    root=ET.parse(path).getroot();vb=[float(x) for x in root.get('viewBox','0 0 64 64').replace(',',' ').split()]
    if len(vb)!=4:vb=[0,0,64,64]
    shapes=[]
    def walk(el, inherited):
        tag=el.tag.rsplit('}',1)[-1];s=_style(el,inherited)
        if tag in {'defs','filter','feMorphology','feFlood','feComposite'}:return
        lines=[]
        try:
            if tag=='path':lines=_path_polylines(el.get('d',''))
            elif tag=='circle':
                cx=float(el.get('cx',0));cy=float(el.get('cy',0));r=float(el.get('r',0));pts=[(cx+r*math.cos(2*math.pi*j/32),cy+r*math.sin(2*math.pi*j/32)) for j in range(32)];lines=[(pts,True)]
            elif tag=='ellipse':
                cx=float(el.get('cx',0));cy=float(el.get('cy',0));rx=float(el.get('rx',0));ry=float(el.get('ry',0));pts=[(cx+rx*math.cos(2*math.pi*j/32),cy+ry*math.sin(2*math.pi*j/32)) for j in range(32)];lines=[(pts,True)]
            elif tag=='line':lines=[([(float(el.get('x1',0)),float(el.get('y1',0))),(float(el.get('x2',0)),float(el.get('y2',0)))],False)]
            elif tag in {'polyline','polygon'}:
                vals=[float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',el.get('points',''))];pts=list(zip(vals[::2],vals[1::2]));lines=[(pts,tag=='polygon')]
            elif tag=='rect':
                x=float(el.get('x',0));y=float(el.get('y',0));w=float(el.get('width',0));h=float(el.get('height',0));lines=[([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],True)]
        except ValueError:pass
        stroke=s.get('stroke','none');fill=s.get('fill','none');width=float(s.get('stroke-width','3').replace('px','') or 3)
        if lines and (stroke!='none' or fill!='none'):shapes.append((lines,stroke,fill,width))
        for ch in el:walk(ch,s)
    walk(root,{'fill':root.get('fill','none'),'stroke':root.get('stroke','none'),'stroke-width':root.get('stroke-width','3')})
    return vb,shapes

def _material(name, rgba):
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name);mat.diffuse_color=rgba;return mat

def _direct_import(path):
    vb,shapes=_svg_geometry(path);scale=1.0/max(vb[2],vb[3],1.0);cx=vb[0]+vb[2]/2;cy=vb[1]+vb[3]/2
    imported=[]
    white=_material('WL Entity Icon White',(1,1,1,1));dark=_material('WL Entity Icon Dark',(0.01,0.01,0.01,1))
    for si,(lines,stroke,fill,width) in enumerate(shapes):
        # The pack deliberately uses a thick white under-stroke and a dark top stroke.
        color=white if ('white' in str(stroke).lower() or str(stroke).lower() in {'#fff','#ffffff'}) else dark
        curve=bpy.data.curves.new(f'WL SVG {path.stem} {si}','CURVE');curve.dimensions='3D';curve.resolution_u=1
        curve.bevel_depth=max(0.006,width*scale*0.5);curve.bevel_resolution=0;curve.materials.append(color)
        for pts,closed in lines:
            if len(pts)<2:continue
            sp=curve.splines.new('POLY');sp.points.add(len(pts)-1)
            for p,co in zip(sp.points,pts):p.co=((co[0]-cx)*scale,(-co[1]+cy)*scale,0,1)
            sp.use_cyclic_u=closed
        obj=bpy.data.objects.new(f'WL SVG {path.stem} {si}',curve);bpy.context.scene.collection.objects.link(obj);imported.append(obj)
    return imported

def _icon_collection(path):
    key=str(path.resolve());cached=_CACHE.get(key)
    if cached and cached.name in bpy.data.collections:return cached
    for collection in bpy.data.collections:
        if collection.get('wl_entity_icon_cache')==key:_CACHE[key]=collection;return collection
    imported=_direct_import(path)
    if not imported:raise RuntimeError(f'SVG contained no supported geometry: {path}')
    collection=bpy.data.collections.new('WL Icon '+path.stem);collection['wl_entity_icon_cache']=key
    for obj in imported:
        for owner in list(obj.users_collection):owner.objects.unlink(obj)
        collection.objects.link(obj);obj['wl_exclude']=True;obj['wl_role']='ENTITY_ICON_SOURCE';obj.hide_select=True
    _CACHE[key]=collection;return collection

def remove_reference(entity):
    if entity is None:return
    if entity.get('_wl_reference_fresh'):return
    for child in list(entity.children):
        if child.get('wl_entity_icon_reference'):bpy.data.objects.remove(child,do_unlink=True)

def attach_reference(entity,pairs=None):
    """Attach a lightweight marker; SVG artwork is drawn flat per viewport."""
    if entity is None or entity.get('wl_role')!='ENTITY':return False
    if pairs is None:
        try:pairs=json.loads(entity.get('wl_pairs','[]'))
        except (TypeError,ValueError):pairs=[]
    classname=dict(pairs).get('classname',entity.name);path=icon_path(classname)
    remove_reference(entity)
    if path is None:return False
    owner=entity.users_collection[0] if entity.users_collection else bpy.context.scene.collection
    obj=bpy.data.objects.new(classname+' icon',None);owner.objects.link(obj)
    obj.parent=entity;obj.location=(0,0,0)
    obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.001
    obj['wl_exclude']=True;obj['wl_role']='ENTITY_ICON_REFERENCE'
    obj['wl_entity_icon_reference']=True;obj['wl_entity_icon_sprite']=True
    obj['wl_entity_icon_asset']=str(path);obj.hide_select=True;obj.hide_render=True
    obj['wl_native_sprite']=_native_shape(path)
    entity.empty_display_size=.001
    return True


_sprite_cache={}
_draw_handle=None


def _sprite(path):
    path=Path(path);key=(str(path),path.stat().st_mtime_ns)
    if key not in _sprite_cache:_sprite_cache[key]=_svg_geometry(path)
    return _sprite_cache[key]


def sprite_instances(context):
    from .. import workspace,context_state
    if not workspace.active(context,'gizmos') or context_state.viewport_hidden(context.scene):return
    if not context.space_data.overlay.show_overlays:return
    from .. import object_index
    visible={o.as_pointer() for o in context.visible_objects}
    for obj in object_index.matching('entity-sprites',context.scene,lambda o:bool(o.get('wl_entity_icon_sprite'))):
        if obj.parent and obj.as_pointer() in visible and obj.parent.as_pointer() in visible:
            yield obj


def _color(value):
    value=str(value).strip().lower()
    if value in {'white','#fff','#ffffff'}:return (1,1,1,1)
    if value.startswith('#') and len(value)==7:
        return tuple(int(value[i:i+2],16)/255 for i in (1,3,5))+(1,)
    return (.01,.01,.01,1)


_sprite_batches={}
_shaders=None
_batch_checks={}


def _batches(path):
    """Tessellate SVGs once in icon-local coordinates, never per entity/frame."""
    global _shaders
    import gpu
    from gpu_extras.batch import batch_for_shader
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    import time
    now=time.monotonic();raw=str(path);checked=_batch_checks.get(raw)
    if checked and now-checked[0]<1:return checked[1]
    path=Path(path);key=(str(path),path.stat().st_mtime_ns)
    if _shaders is None:_shaders=(gpu.shader.from_builtin('UNIFORM_COLOR'),gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR'))
    if key in _sprite_batches:
        _batch_checks[raw]=(now,_sprite_batches[key]);return _sprite_batches[key]
    vb,shapes=_sprite(path);scale=1/max(vb[2],vb[3],1)
    def local(p):return ((p[0]-vb[0]-vb[2]/2)*scale,-(p[1]-vb[1]-vb[3]/2)*scale,0)
    result=[]
    for lines,stroke,fill,width in shapes:
        if fill!='none':
            polygons=[[Vector(local(p)) for p in pts] for pts,closed in lines if closed and len(pts)>2]
            triangles=tessellate_polygon(polygons) if polygons else []
            flat=[v for polygon in polygons for v in polygon]
            if triangles:result.append((False,batch_for_shader(_shaders[0],'TRIS',{'pos':[flat[v] if isinstance(v,int) else v for tri in triangles for v in tri]}),_color(fill),0))
        if stroke!='none':
            segments=[]
            for pts,closed in lines:
                pairs=list(zip(pts,pts[1:]))
                if closed and len(pts)>1:pairs.append((pts[-1],pts[0]))
                segments.extend(local(p) for pair in pairs for p in pair)
            if segments:result.append((True,batch_for_shader(_shaders[1],'LINES',{'pos':segments}),_color(stroke),width*scale))
    _sprite_batches[key]=result;_batch_checks[raw]=(now,result)
    return result


def _native_shape(path):
    """Serialize one immutable local-space glyph, shared by every instance.

    Native overlay sync uploads this prototype once; per-frame projection and
    all drawing use Blender's C++ renderer and GPU instance buffers.
    """
    import hashlib
    from array import array
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    path=Path(path);identity=hashlib.sha256((str(path)+str(path.stat().st_mtime_ns)+'glyph-v1').encode()).hexdigest()[:24]
    label='.wavelength glyph '+identity
    existing=bpy.data.meshes.get(label)
    if existing is not None:return existing
    vb,shapes=_sprite(path);scale=1/max(vb[2],vb[3],1);vertices=[]
    def local(p):return Vector(((p[0]-vb[0]-vb[2]/2)*scale,-(p[1]-vb[1]-vb[3]/2)*scale,0))
    def triangle(points,color):
        for v in points:vertices.extend((*v,*color))
    for lines,stroke,fill,width in shapes:
        if fill!='none':
            polygons=[[local(p) for p in pts] for pts,closed in lines if closed and len(pts)>2]
            flat=[v for polygon in polygons for v in polygon]
            for tri in tessellate_polygon(polygons) if polygons else []:triangle([flat[v] if isinstance(v,int) else v for v in tri],_color(fill))
        if stroke!='none':
            half=max(width*scale,1/SPRITE_SIZE)/2;color=_color(stroke)
            for pts,closed in lines:
                pairs=list(zip(pts,pts[1:]))
                if closed and len(pts)>1:pairs.append((pts[-1],pts[0]))
                for a,b in pairs:
                    a,b=local(a),local(b);d=b-a
                    if d.length<1e-9:continue
                    offset=Vector((-d.y,d.x,0)).normalized()*half
                    triangle((a-offset,b-offset,b+offset),color);triangle((a-offset,b+offset,a+offset),color)
    data=bpy.data.meshes.new(label);data['wl_svg_triangles']=array('f',vertices)
    data['wl_svg_source']=str(path)
    return data


def _native_sync():
    from .. import workspace,context_state
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            enabled=workspace.active(bpy.context,'gizmos') and not context_state.viewport_hidden(window.scene)
            for area in window.screen.areas:
                if area.type!='VIEW_3D':continue
                overlay=area.spaces.active.overlay
                if hasattr(overlay,'wavelength_entity_icons'):
                    value=bool(enabled and overlay.show_overlays)
                    if overlay.wavelength_entity_icons!=value:overlay.wavelength_entity_icons=value
    return .25


def draw_sprites():
    import gpu
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    context=bpy.context
    if hasattr(context.space_data.overlay,'wavelength_entity_icons'):return
    if not context.region_data:return
    gpu.state.blend_set('ALPHA')
    try:
        size=SPRITE_SIZE*context.preferences.system.ui_scale
        for obj in sprite_instances(context):
            center=location_3d_to_region_2d(context.region,context.region_data,obj.matrix_world.translation)
            if center is None or center.x < -size or center.y < -size or center.x>context.region.width+size or center.y>context.region.height+size:continue
            try:batches=_batches(obj['wl_entity_icon_asset'])
            except (OSError,ValueError,ET.ParseError):continue
            with gpu.matrix.push_pop():
                gpu.matrix.translate((center.x,center.y,0));gpu.matrix.scale((size,size,1))
                for line,batch,color,width in batches:
                    shader=_shaders[1 if line else 0];shader.bind();shader.uniform_float('color',color)
                    if line:
                        shader.uniform_float('viewportSize',(context.region.width,context.region.height))
                        shader.uniform_float('lineWidth',max(1,width*size))
                    batch.draw(shader)
    finally:gpu.state.blend_set('NONE')


@bpy.app.handlers.persistent
def migrate_sprites(*_args):
    # Existing .blend files retain entity transforms and properties; replace only
    # legacy editor curve references, once, without touching actual model meshes.
    parents={obj.parent for obj in tuple(bpy.data.objects)
             if obj.get('wl_entity_icon_reference') and not obj.get('wl_entity_icon_sprite') and obj.parent}
    for entity in parents:attach_reference(entity)
    for obj in bpy.data.objects:
        if obj.get('wl_entity_icon_sprite') and not obj.get('wl_native_sprite'):
            try:obj['wl_native_sprite']=_native_shape(obj['wl_entity_icon_asset'])
            except (OSError,ValueError,KeyError):pass


def _startup_sprites():
    migrate_sprites()


def register():
    global _draw_handle
    if _draw_handle is None and 'wavelength_entity_icons' not in bpy.types.View3DOverlay.bl_rna.properties:
        _draw_handle=bpy.types.SpaceView3D.draw_handler_add(draw_sprites,(),'WINDOW','POST_PIXEL')
    if migrate_sprites not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(migrate_sprites)
    if not bpy.app.timers.is_registered(_startup_sprites):bpy.app.timers.register(_startup_sprites,first_interval=.1)
    if not bpy.app.timers.is_registered(_native_sync):bpy.app.timers.register(_native_sync,first_interval=.1,persistent=True)


def unregister():
    global _draw_handle,_shaders
    if _draw_handle is not None:bpy.types.SpaceView3D.draw_handler_remove(_draw_handle,'WINDOW');_draw_handle=None
    if migrate_sprites in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(migrate_sprites)
    if bpy.app.timers.is_registered(_startup_sprites):bpy.app.timers.unregister(_startup_sprites)
    if bpy.app.timers.is_registered(_native_sync):bpy.app.timers.unregister(_native_sync)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D' and hasattr(area.spaces.active.overlay,'wavelength_entity_icons'):area.spaces.active.overlay.wavelength_entity_icons=False
    _sprite_cache.clear();_sprite_batches.clear();_batch_checks.clear();_shaders=None
