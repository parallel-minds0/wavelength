"""Source asset bindings; payload parsing and drawing belong to native C++.

These properties name original mounted assets, never serialized mesh/pixel data.
The ordinary Python importer remains available on stock Blender builds.
"""
import json,struct
from pathlib import Path
import bpy
from . import profiles,source_assets


def enabled():
    return 'wavelength_source_assets_pending' in bpy.types.View3DOverlay.bl_rna.properties


def direct(settings):
    """Direct GPU assets serve Solid; Blender engines require ordinary datablocks."""
    owner=getattr(settings,'id_data',None)
    return enabled() and not (owner and owner.get('wl_source_blender_rendering'))


def mounts(settings):
    assets=source_assets.library(bpy.path.abspath(settings.game_dir))
    if not hasattr(assets,'_native_mounts_text'):
        from . import runtime_cache
        generation=runtime_cache.key(source_assets._library_stamp(assets))
        assets._native_mounts_text='#'+generation+'\n'+'\n'.join(str(m.path if isinstance(m,source_assets.VPK) else m) for m in assets.mounts)
    return assets._native_mounts_text


def bind_material(settings,mat,name,width,height):
    """Keep engine dimensions for projection without creating a Blender Image."""
    owner=getattr(settings,'id_data',None)
    if isinstance(owner,bpy.types.Scene) and not owner.get('wl_native_source_scene'):owner['wl_native_source_scene']=True
    mat['wl_source_mounts']=mounts(settings);mat['wl_source_native_material']=name
    mat['wl_source_revision']=mat.get('wl_source_cache_key','')
    mat['wl_texture']=name;mat['wl_width']=width;mat['wl_height']=height
    mat['wl_asset_profile']=settings.engine;mat['wl_realized']=True
    mat['wl_source_blend_checked']=True
    # Blender 5.2 always exposes a node tree. The native renderer ignores it;
    # never populate that tree with converted Source textures or shaders.
    mat.diffuse_color=(1,1,1,1)
    mat.pop('wl_source_pending',None)
    return mat


def attach(entity,path,pairs=None,settings=None):
    """One Empty per instance; all geometry/textures stay in the native cache."""
    from .entity import models
    settings=settings or bpy.context.scene.wavelength
    owner=getattr(settings,'id_data',None)
    if isinstance(owner,bpy.types.Scene) and not owner.get('wl_native_source_scene'):owner['wl_native_source_scene']=True
    values=dict(pairs if pairs is not None else json.loads(entity.get('wl_pairs','[]')))
    assets=source_assets.library(bpy.path.abspath(settings.game_dir))
    header=assets.prefix(path,156)
    if len(header)<156 or header[:4]!=b'IDST':raise ValueError('Invalid Source model header: '+path)
    unit=profiles.unit_meters(settings)
    low=struct.unpack_from('<3f',header,104);high=struct.unpack_from('<3f',header,116)
    models.remove_reference(entity)
    obj=bpy.data.objects.new(Path(path).stem+' · Source',None)
    (entity.users_collection[0] if entity.users_collection else bpy.context.scene.collection).objects.link(obj)
    obj.parent=entity;obj['wl_model_reference']=True;obj['wl_exclude']=True;obj['wl_role']='MODEL_REFERENCE'
    from .scene import uid
    obj['wl_id']=uid()
    obj['wl_source_model']=path;obj['wl_source_native_model']=path;obj['wl_source_mounts']=mounts(settings)
    obj['wl_source_unit']=float(unit);obj['wl_source_skin']=int(values.get('skin','0') or '0');obj['wl_source_body']=int(values.get('body','0') or '0')
    from . import runtime_cache
    obj['wl_source_revision']=runtime_cache.key([assets.fingerprint(p) for p in [path,path[:-4]+'.vvd',*(path[:-4]+suffix for suffix in ('.dx90.vtx','.dx80.vtx','.sw.vtx','.vtx'))]])
    # Native GPU bounds use the full model. The Empty supplies a selectable
    # editor handle without allocating any per-instance mesh data.
    obj['wl_source_bounds']=[float(v)*unit for v in (*low,*high)]
    obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.001
    obj.hide_select=False
    entity.pop('wl_model_error',None);entity.pop('wl_representation_pending',None)
    return obj


def hit(context,origin,direction,maximum=float('inf')):
    """Pick native prop bounds without rebuilding a Python model mesh."""
    from . import object_index
    visible={obj.as_pointer() for obj in context.visible_objects}
    best=None;distance=maximum
    for ref in object_index.matching('native-source-models',context.scene,lambda o:bool(o.get('wl_source_native_model'))):
        if not ref.parent or ref.as_pointer() not in visible or ref.parent.as_pointer() not in visible:continue
        bounds=ref.get('wl_source_bounds')
        if bounds is None or len(bounds)!=6:continue
        inverse=ref.matrix_world.inverted_safe();start=inverse@origin;ray=inverse.to_3x3()@direction
        near=-float('inf');far=distance
        for axis in range(3):
            low,high=sorted((bounds[axis],bounds[axis+3]))
            if abs(ray[axis])<1e-10:
                if start[axis]<low or start[axis]>high:far=-1;break
                continue
            one=(low-start[axis])/ray[axis];two=(high-start[axis])/ray[axis]
            near=max(near,min(one,two));far=min(far,max(one,two))
            if near>far:break
        at=near if near>=0 else far
        if far>=max(near,0) and 0<=at<distance:distance=at;best=ref.parent
    return best


def configure_viewports(scene=None):
    scene=scene or bpy.context.scene
    if scene and not scene.get('wl_native_source_scene'):scene['wl_native_source_scene']=True
    for window in bpy.context.window_manager.windows:
        if scene is not None and window.scene!=scene:continue
        if not hasattr(window.scene,'wavelength') or not profiles.is_source(window.scene.wavelength.engine):continue
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.shading.color_type='MATERIAL'


def migrate(scene):
    """Rebind existing engine previews once on file load; retain authoring data."""
    settings=scene.wavelength
    materials={m for obj in scene.objects if obj.type=='MESH' for m in obj.data.materials
               if m and m.get('wl_source_cache_key') and m.get('wl_texture')}
    for mat in materials:
        try:source_assets.material(settings,mat['wl_texture'],target_mat=mat)
        except (ValueError,OSError) as exc:mat['wl_asset_error']=str(exc)
    from .entity import models
    for obj in tuple(scene.objects):
        if obj.get('wl_role')!='ENTITY' or obj.get('wl_custom_model'):continue
        children=tuple(obj.children)
        if any(c.get('wl_source_native_model') for c in children):continue
        if any(c.type=='MESH' and c.data.get('wl_source_model_key') for c in children):continue
        if any(c.get('wl_source_model') for c in children):models.attach_reference(obj,settings=settings)
    configure_viewports(scene)

