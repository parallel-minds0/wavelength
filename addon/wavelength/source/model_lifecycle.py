"""Persistent editable model identity, placements and independent variants.

The asset collection owns sources and dependencies; an entity is a placement.
Engine adapters only decode model data. No game files are written by these
editing operations, and source geometry never becomes accidental world brushes.
"""
import json,uuid,tempfile
from array import array
from pathlib import Path
from contextlib import contextmanager
import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix
from . import model_pipeline,profiles

SOURCE_TYPES={'MESH','ARMATURE','CURVE','LATTICE','EMPTY'}


def edit_dependencies(objects):
    """Include modelling controls, without pulling unrelated level meshes in."""
    result=set(objects);pending=list(objects)
    while pending:
        obj=pending.pop();dependencies=[]
        if obj.parent and obj.parent.type in {'EMPTY','CURVE','LATTICE'} and obj.parent.get('wl_role')!='ENTITY' and not obj.parent.get('wl_editor_helper'):
            dependencies.append(obj.parent)
        for modifier in obj.modifiers:
            for prop in modifier.bl_rna.properties:
                if prop.type=='POINTER':
                    value=getattr(modifier,prop.identifier,None)
                    if isinstance(value,bpy.types.Object) and value.type in {'ARMATURE','CURVE','LATTICE','EMPTY'}:dependencies.append(value)
        for constraint in obj.constraints:
            target=getattr(constraint,'target',None)
            if target and target.type in {'ARMATURE','CURVE','LATTICE','EMPTY'}:dependencies.append(target)
        for dependency in dependencies:
            if dependency.get('wl_role')=='ENTITY' or dependency.get('wl_model_reference') or dependency.get('wl_editor_helper'):continue
            if dependency not in result:result.add(dependency);pending.append(dependency)
    return result


def entity_for(obj):
    if obj and obj.get('wl_custom_model_owner'):return obj['wl_custom_model_owner']
    while obj and obj.get('wl_model_reference'):obj=obj.parent
    return obj if obj and obj.get('wl_role')=='ENTITY' else None


def ensure(context,asset,*,backend=None,source=None):
    """Lazily adopt existing collections without replacing their source data."""
    settings=context.scene.wavelength
    defaults={'wl_model_schema':1,'wl_model_id':asset.get('wl_custom_model_id') or uuid.uuid4().hex,
              'wl_model_backend':backend or asset.get('wl_model_backend') or model_pipeline.backend_for(asset.get('wl_owner_profile',settings.engine)).id,
              'wl_model_profile':asset.get('wl_owner_profile',settings.engine),
              'wl_model_game':asset.get('wl_game_dir',bpy.path.abspath(settings.game_dir)),
              'wl_model_unit_meters':next((o['wl_unit_meters'] for o in asset.objects if o.get('wl_unit_meters')),profiles.unit_meters(settings)),
              'wl_model_source':source or '',
              'wl_model_status':'Editable','wl_model_warnings':'[]'}
    for key,value in defaults.items():
        if key not in asset:asset[key]=value
    if source and not asset.get('wl_model_source'):asset['wl_model_source']=source
    for obj in asset.objects:
        if obj.type in SOURCE_TYPES and obj.get('wl_role')!='ENTITY':
            obj['wl_model_asset']=asset;obj['wl_role']='MODEL_SOURCE';obj['wl_exclude']=True
    return asset


def asset_for(obj):
    if not obj:return None
    direct=obj.get('wl_model_asset')
    if direct and direct.name in bpy.data.collections:return direct
    entity=entity_for(obj)
    if entity and entity.get('wl_custom_model'):return entity['wl_custom_model']
    for col in obj.users_collection:
        if col.get('wl_model_backend'):return col
    return None


def sources(asset):return [o for o in asset.objects if o.type in SOURCE_TYPES and o.get('wl_role')!='ENTITY']


def bindings(asset):return [o for o in bpy.data.objects if o.get('wl_custom_model')==asset and not o.get('wl_model_private_origin')]


def select_sources(context,asset):
    for obj in context.selected_objects:obj.select_set(False)
    selected=[o for o in sources(asset) if o.name in context.view_layer.objects]
    for obj in selected:obj.hide_set(False);obj.select_set(True)
    if selected:context.view_layer.objects.active=next((o for o in selected if o.type=='MESH'),selected[0])


@contextmanager
def selection(context,objects,active):
    previous=list(context.selected_objects);old=context.view_layer.objects.active
    try:
        for obj in previous:obj.select_set(False)
        for obj in objects:obj.select_set(True)
        context.view_layer.objects.active=active
        yield
    finally:
        for obj in context.selected_objects:obj.select_set(False)
        for obj in previous:
            if obj.name in context.view_layer.objects:obj.select_set(True)
        if old and old.name in context.view_layer.objects:context.view_layer.objects.active=old


def _parent(obj,parent):
    # Preserve basis/parent inverse rather than decomposing world matrices:
    # this also retains offsets under rotated, nonuniformly scaled sources.
    basis=obj.matrix_basis.copy()
    old=obj.parent.matrix_world@obj.matrix_parent_inverse if obj.parent else Matrix.Identity(4)
    obj.parent=parent;obj.matrix_parent_inverse=parent.matrix_world.inverted()@old;obj.matrix_basis=basis


def _anchor(context,asset,matrix):
    origin=bpy.data.objects.new(asset.name+' · Edit Origin',None)
    context.scene.collection.objects.link(origin);origin.matrix_world=matrix
    origin['wl_exclude']=True;origin['wl_editor_helper']=True
    return origin


def _reference(entity,asset):
    from .entity import models
    models.remove_reference(entity)
    ref=bpy.data.objects.new(asset.name+' · Linked Model',None)
    (entity.users_collection[0] if entity.users_collection else bpy.context.scene.collection).objects.link(ref)
    ref.instance_type='COLLECTION';ref.instance_collection=asset;ref.parent=entity
    ref.matrix_basis=asset.wavelength_model.origin.matrix_world.inverted()
    ref['wl_model_reference']=True;ref['wl_exclude']=True;ref['wl_role']='MODEL_REFERENCE'
    ref['wl_model_linked_asset']=asset


@persistent
def sync_placements(scene,depsgraph):
    """Only anchor transforms require updating linked placement inverses."""
    for update in depsgraph.updates:
        obj=update.id.original
        if not isinstance(obj,bpy.types.Object):continue
        asset=obj.get('wl_custom_model')
        if not asset or not asset.get('wl_model_schema') or asset.wavelength_model.origin!=obj:continue
        inverse=obj.matrix_world.inverted_safe()
        for entity in bindings(asset):
            if entity==obj:continue
            for ref in entity.children:
                if ref.get('wl_model_linked_asset')==asset and any(abs(ref.matrix_basis[i][j]-inverse[i][j])>1e-7 for i in range(4) for j in range(4)):
                    ref.matrix_basis=inverse


def _validate(context,asset,entity):
    settings=context.scene.wavelength
    if asset['wl_model_profile']!=settings.engine or asset['wl_model_game']!=bpy.path.abspath(settings.game_dir):raise ValueError('Activate the model asset\'s owning profile and game first')
    if entity is None or entity.get('wl_role')!='ENTITY':raise ValueError('Make the destination model entity active')
    if not any(o.type=='MESH' for o in sources(asset)):raise ValueError('The editable asset has no render meshes')
    adapter=model_pipeline.get(asset['wl_model_backend'])
    if not hasattr(adapter,'validate_placement') or not hasattr(adapter,'bind_asset'):raise ValueError('This model backend does not support in-level placements yet')
    adapter.validate_placement(context,asset,entity)


def attach(context,asset,entity,*,select=True):
    """Attach the first placement in place; additional placements share a definition."""
    ensure(context,asset);_validate(context,asset,entity)
    adapter=model_pipeline.get(asset['wl_model_backend'])
    if entity.get('wl_custom_model')==asset:
        if select:select_sources(context,asset)
        return asset
    current=entity.get('wl_custom_model')
    if current:
        ensure(context,current)
        others=_release(context,current,entity)
        if not others:current.hide_viewport=True;current.hide_render=True
    if bindings(asset):
        previous=dict(json.loads(entity['wl_pairs'])).get('model','')
        entity['wl_custom_previous_model']=previous;entity['wl_custom_model']=asset;entity['wl_model_asset']=asset
        pairs=[p for p in json.loads(entity['wl_pairs']) if p[0]!='model']
        pairs.append(['model',adapter.model_path(asset)]);entity['wl_pairs']=json.dumps(pairs)
        _reference(entity,asset)
    else:
        if asset.name not in context.scene.collection.children and not any(o.name in context.scene.objects for o in sources(asset)):
            context.scene.collection.children.link(asset)
        objects=sources(asset)
        old_origin=asset.wavelength_model.origin
        private=asset.get('wl_model_build_owner')
        private=private if private and (private.get('wl_model_private_origin') or private.get('wl_exclude')) else None
        released=[o for o in objects if private and o.get('wl_custom_model_owner')==private]
        for obj in released:obj.pop('wl_custom_model_owner',None)
        try:
            with selection(context,[*objects,entity],entity):adapter.bind_asset(context,asset)
        except Exception:
            for obj in released:obj['wl_custom_model_owner']=private
            raise
        asset['wl_model_build_owner']=entity;entity['wl_model_asset']=asset
        if old_origin and old_origin!=entity and old_origin.get('wl_editor_helper') and not old_origin.children:
            bpy.data.objects.remove(old_origin,do_unlink=True)
        if private and private!=entity:
            private.pop('wl_custom_model',None);private.pop('wl_model_asset',None)
            if not private.children:bpy.data.objects.remove(private,do_unlink=True)
    asset['wl_model_status']='Editable · attached'
    if select:select_sources(context,asset)
    return asset


def _adopt(context,objects,name,backend,source,warnings,origin=None):
    asset=bpy.data.collections.new(name+' · Model Asset');context.scene.collection.children.link(asset)
    asset['wl_model_warnings']=json.dumps(warnings)
    for obj in objects:
        for collection in list(obj.users_collection):collection.objects.unlink(obj)
        asset.objects.link(obj)
    ensure(context,asset,backend=backend,source=source)
    if objects:
        context.view_layer.update()
        anchor=_anchor(context,asset,origin if origin is not None else objects[0].matrix_world.copy())
        asset.wavelength_model.origin=anchor;members=set(objects)
        for obj in objects:
            if obj.parent not in members:_parent(obj,anchor)
    # Editable imports own materials; cached model/browser definitions stay intact.
    materials={}
    for obj in objects:
        if obj.type=='MESH':
            for i,mat in enumerate(obj.data.materials):
                if mat:
                    if mat not in materials:materials[mat]=mat.copy()
                    obj.data.materials[i]=materials[mat]
        for values in json.loads(obj.get('wl_model_clips','[]')):
            clip=asset.wavelength_model.clips.add()
            for key,value in values.items():setattr(clip,key,value)
    adapter=model_pipeline.get(backend)
    if hasattr(adapter,'editable_materials'):
        warnings=[*warnings,*adapter.editable_materials(context,asset)];asset['wl_model_warnings']=json.dumps(warnings)
    return asset


def set_origin(context,asset,position):
    """Move the shared pivot while preserving source and linked-instance geometry."""
    if context.mode!='OBJECT':raise ValueError('Set the model origin in Object Mode')
    root=asset.wavelength_model.origin
    if root is None:raise ValueError('The model origin is missing')
    placements=bindings(asset)
    for obj in {root,*placements}:
        animation=obj.animation_data
        if obj.constraints or animation and (animation.action or animation.nla_tracks or animation.drivers):
            raise ValueError('Bake placement animation or constraints before changing the model origin: '+obj.name)
    context.view_layer.update()
    old=root.matrix_world.copy()
    if abs(old.determinant())<1e-12:raise ValueError('The model origin transform is singular')
    selected=entity_for(context.object)
    new=old.copy()
    if selected in placements:
        if abs(selected.matrix_world.determinant())<1e-12:raise ValueError('The selected placement transform is singular')
        new.translation=old@selected.matrix_world.inverted()@position
    else:new.translation=position
    delta=old.inverted()@new
    entities={obj:obj.matrix_world.copy() for obj in placements if obj!=root}
    children={child:child.matrix_parent_inverse.copy() for child in root.children}
    references={ref:ref.matrix_basis.copy() for obj in placements for ref in obj.children if ref.get('wl_model_linked_asset')==asset}
    try:
        root.matrix_world=new
        for child,inverse in children.items():
            child.matrix_parent_inverse=new.inverted()@old@inverse
        for obj,matrix in entities.items():obj.matrix_world=matrix@delta
        for ref in references:ref.matrix_basis=new.inverted()
        context.view_layer.update()
    except Exception:
        root.matrix_world=old
        for child,inverse in children.items():child.matrix_parent_inverse=inverse
        for obj,matrix in entities.items():obj.matrix_world=matrix
        for ref,matrix in references.items():ref.matrix_basis=matrix
        context.view_layer.update()
        raise
    asset['wl_model_status']='Editable · origin changed'
    from . import model_collision_preview
    model_collision_preview.clear()


def add_sources(context,asset,selected):
    """Add ordinary sources to the shared definition, preserving their authored pose."""
    settings=context.scene.wavelength
    if context.mode!='OBJECT':raise ValueError('Manage model parts in Object Mode')
    if asset['wl_model_profile']!=settings.engine or asset['wl_model_game']!=bpy.path.abspath(settings.game_dir):
        raise ValueError('Activate the model asset owning profile and game first')
    origin=asset.wavelength_model.origin
    if origin is None:raise ValueError('The model origin is missing')
    existing=set(sources(asset))
    objects=edit_dependencies(set(selected)-existing-{origin})
    if not objects:raise ValueError('Select new mesh parts or modelling controls with this asset')
    for obj in objects:
        if obj.type not in SOURCE_TYPES or obj.get('wl_role')=='ENTITY' or obj.get('wl_model_reference') or obj.get('wl_editor_helper'):
            raise ValueError('Choose editable source parts: '+obj.name)
        owner=asset_for(obj)
        if owner and owner!=asset or obj.get('wl_custom_model_owner') and obj.get('wl_custom_model_owner')!=origin:
            raise ValueError('Part belongs to another model asset: '+obj.name)
        if obj.library or obj.data and obj.data.library:
            raise ValueError('Make linked objects local first: '+obj.name)
        if obj.parent and obj.parent not in objects|existing|{origin}:
            raise ValueError('Include the part parent: '+obj.name)
    context.view_layer.update()
    for obj in objects:
        if obj.name not in asset.objects:asset.objects.link(obj)
        if obj.parent not in objects|existing|{origin}:_parent(obj,origin)
        if bindings(asset):obj['wl_custom_model_owner']=origin
        for key in ('wl_source_displacement','wl_terrain_face_corners','wl_terrain_source_corners',
                    'wl_terrain_face_matrix','wl_terrain_face_id','wl_displacement','wl_terrain',
                    'wl_terrain_seams','wl_terrain_detached'):
            obj.pop(key,None)
    ensure(context,asset)
    asset['wl_model_status']='Editable · parts changed'
    return objects


def remove_source(context,asset,obj):
    """Release one source object without deleting its editable data."""
    members=set(sources(asset))
    if obj not in members:raise ValueError('Choose a source part from this asset')
    remaining=members-{obj}
    if obj.type=='MESH' and not any(part.type=='MESH' for part in remaining):
        raise ValueError('Keep at least one render mesh in the asset')
    if obj in edit_dependencies(remaining) or any(part.parent==obj for part in remaining):
        raise ValueError('This part is still required by another source: '+obj.name)
    if asset.wavelength_model.collision==obj:
        raise ValueError('Choose a different collision source before removing this part')
    world=obj.matrix_world.copy()
    if obj.name not in context.scene.collection.objects:context.scene.collection.objects.link(obj)
    asset.objects.unlink(obj)
    if obj.parent==asset.wavelength_model.origin:
        obj.parent=None
        obj.matrix_world=world
    obj.pop('wl_model_asset',None)
    obj.pop('wl_custom_model_owner',None)
    obj.pop('wl_custom_model_previous_exclude',None)
    # Released parts remain model content rather than becoming accidental BSP brushes.
    obj['wl_role']='MODEL_SOURCE'
    obj['wl_exclude']=True
    asset['wl_model_status']='Editable · parts changed'


def create(context,name):
    """Register ordinary authored sources while retaining their mesh data and world pose."""
    if context.mode!='OBJECT':raise ValueError('Create model assets in Object Mode')
    backend=model_pipeline.backend_for(context.scene.wavelength.engine)
    selected=list(context.selected_objects)
    if not selected or not any(obj.type=='MESH' for obj in selected):
        raise ValueError('Select at least one mesh')
    objects=sorted(edit_dependencies(selected),key=lambda obj:obj.name)
    for obj in objects:
        if obj.type not in SOURCE_TYPES or obj.get('wl_role')=='ENTITY' or obj.get('wl_model_reference'):
            raise ValueError('Select editable meshes and modelling controls: '+obj.name)
        if asset_for(obj) or obj.get('wl_custom_model_owner'):
            raise ValueError('Object already belongs to a model asset: '+obj.name)
        if obj.library or obj.data and obj.data.library:
            raise ValueError('Make linked objects local before creating a model asset: '+obj.name)
        if obj.parent and obj.parent not in objects:
            raise ValueError('Select the parent together with its source: '+obj.name)
    active=context.object if context.object in objects else selected[0]
    context.view_layer.update()
    location,rotation,_=active.matrix_world.decompose()
    origin=Matrix.LocRotScale(location,rotation,None)
    asset=bpy.data.collections.new(name.strip() or active.name)
    context.scene.collection.children.link(asset)
    snapshots={obj:(dict(obj.items()),obj.parent,obj.matrix_parent_inverse.copy(),obj.matrix_basis.copy()) for obj in objects}
    anchor=None
    try:
        for obj in objects:asset.objects.link(obj)
        ensure(context,asset,backend=backend.id)
        anchor=_anchor(context,asset,origin)
        asset.wavelength_model.origin=anchor
        for obj in objects:
            if obj.parent not in objects:_parent(obj,anchor)
        select_sources(context,asset)
        return asset
    except Exception:
        for obj,(properties,parent,inverse,basis) in snapshots.items():
            obj.parent=parent;obj.matrix_parent_inverse=inverse;obj.matrix_basis=basis
            for key in list(obj.keys()):
                if key not in properties:del obj[key]
            for key,value in properties.items():obj[key]=value
        if anchor:bpy.data.objects.remove(anchor,do_unlink=True)
        bpy.data.collections.remove(asset)
        raise


def edit(context,entity):
    """Decode a mounted prop at its exact pose, or enter its editable definition."""
    if context.mode!='OBJECT':raise ValueError('Leave Edit Mode before opening a model asset')
    asset=asset_for(entity)
    if asset:
        ensure(context,asset)
        adapter=model_pipeline.get(asset['wl_model_backend'])
        if hasattr(adapter,'editable_materials'):adapter.editable_materials(context,asset)
        select_sources(context,asset);return asset
    settings=context.scene.wavelength
    owner_profile=entity.get('wl_owner_profile') or entity.get('wl_profile')
    if owner_profile and owner_profile!=settings.engine:raise ValueError('Activate the placed model\'s owning profile first')
    values=dict(json.loads(entity.get('wl_pairs','[]')));path=values.get('model','')
    if not path:raise ValueError('The selected entity has no model to edit')
    backend=model_pipeline.backend_for(settings.engine,path)
    importer=getattr(backend,'import_reference',None)
    if importer is None:raise ValueError('This model backend does not support editing mounted references yet')
    transform=entity.matrix_world.copy()
    with selection(context,[entity],entity):result=importer(context,path,int(values.get('skin',0)),int(values.get('body',0)))
    asset=None
    try:
        for obj in result.objects:obj.matrix_world=transform@obj.matrix_world
        context.view_layer.update()
        asset=_adopt(context,result.objects,entity.name,backend.id,path,result.warnings,origin=transform)
        return attach(context,asset,entity)
    except Exception:
        for obj in result.objects:
            if obj.name in bpy.data.objects:bpy.data.objects.remove(obj,do_unlink=True)
        if asset:bpy.data.collections.remove(asset)
        raise


def _release(context,asset,entity):
    """Move the old definition to a remaining placement before replacing its origin."""
    from .entity import models
    others=[o for o in bindings(asset) if o!=entity]
    if asset.wavelength_model.origin==entity:
        origin=others[0] if others else _anchor(context,asset,entity.matrix_world.copy())
        old=entity.matrix_world.copy();delta=origin.matrix_world@old.inverted()
        members=set(sources(asset))
        for obj in members:
            if obj.parent not in members:
                world=delta@obj.matrix_world;basis=obj.matrix_basis.copy();obj.parent=origin
                obj.matrix_parent_inverse=origin.matrix_world.inverted()@world@basis.inverted();obj.matrix_basis=basis
        asset.wavelength_model.origin=origin
        for obj in members:
            if others:obj['wl_custom_model_owner']=origin
            else:obj.pop('wl_custom_model_owner',None)
        if others:models.remove_reference(origin);asset['wl_model_build_owner']=origin
        else:asset.pop('wl_model_build_owner',None)
    models.remove_reference(entity);entity.pop('wl_custom_model',None);entity.pop('wl_model_asset',None)
    previous=entity.pop('wl_custom_previous_model','')
    pairs=[p for p in json.loads(entity.get('wl_pairs','[]')) if p[0]!='model']
    if previous:pairs.append(['model',previous])
    entity['wl_pairs']=json.dumps(pairs)
    context.view_layer.update()
    for other in others:
        if other!=asset.wavelength_model.origin:_reference(other,asset)
    return others


def _owned_image(image):
    """Own dirty pixel buffers as well as IDs, and never save to a source path."""
    if image.source not in {'FILE','GENERATED'} or image.is_multiview:raise ValueError('Bake tiled, movie or multiview images before making an independent model asset')
    pixels=array('f',[0.])*len(image.pixels)
    if not pixels:raise ValueError('Load the missing model image before detaching: '+image.name)
    image.pixels.foreach_get(pixels);copy=image.copy()
    try:
        copy.pixels.foreach_set(pixels);copy.update()
        # Generated Image.copy/pack alone need not preserve a dirty buffer in a
        # saved blend. Give this copy its own temporary file, then pack that file.
        _pack_image(copy)
        copy['wl_model_owned_image']=True
        return copy
    except Exception:
        bpy.data.images.remove(copy);raise


def _pack_image(image):
    with tempfile.TemporaryDirectory(prefix='wavelength-model-image-') as folder:
        image.file_format='OPEN_EXR' if image.is_float else 'PNG'
        image.filepath_raw=str(Path(folder)/('texture.exr' if image.is_float else 'texture.png'))
        try:
            image.save();payload=Path(image.filepath_raw).read_bytes();image.source='FILE'
            # Passing bytes replaces an earlier packed file as well. pack()
            # without data can otherwise keep stale pixels from the first copy.
            image.pack(data=payload,data_len=len(payload))
        finally:image.filepath_raw=''


@persistent
def save_owned_images(_):
    """Save only our detached/variant images, never a source game's image file."""
    for image in tuple(bpy.data.images):
        if image.get('wl_model_owned_image') and image.is_dirty:_pack_image(image)


def make_unique(context,asset,entity=None):
    """Stage independent datablocks; failed dependency copies leave no half asset."""
    kinds=('objects','collections','meshes','armatures','curves','lattices','materials','node_groups','images','actions')
    before={kind:set(getattr(bpy.data,kind)) for kind in kinds}
    try:return _make_unique(context,asset,entity)
    except Exception:
        for kind in kinds:
            collection=getattr(bpy.data,kind)
            for item in tuple(collection):
                if item not in before[kind]:collection.remove(item,do_unlink=True) if kind in {'objects','collections'} else collection.remove(item)
        raise


def _make_unique(context,asset,entity=None):
    """Copy editable geometry/materials/actions and remap internal rig dependencies."""
    ensure(context,asset)
    if entity:_validate(context,asset,entity)
    original=list(edit_dependencies(sources(asset)));mapping={};materials={};actions={};images={};groups={}
    collision=asset.wavelength_model.collision if asset.wavelength_model.collision_mode=='OBJECT' else None
    collision_only=collision if collision and collision not in original else None
    if collision_only:original.extend(o for o in edit_dependencies([collision_only]) if o not in original)
    def own_tree(tree):
        for node in tree.nodes:
            image=getattr(node,'image',None)
            if image:
                if image not in images:
                    images[image]=_owned_image(image)
                node.image=images[image]
            group=getattr(node,'node_tree',None)
            if group:
                if group not in groups:
                    groups[group]=group.copy();own_tree(groups[group])
                node.node_tree=groups[group]
    variant=bpy.data.collections.new(asset.name+' · Variant');context.scene.collection.children.link(variant)
    for key,value in asset.items():
        if key.startswith('wl_model_') and key not in {'wl_model_id','wl_model_build_owner','wl_model_output','wl_model_log','wl_model_publish_settings','wl_model_revisions'}:variant[key]=value
    ensure(context,variant);variant['wl_model_parent_id']=asset['wl_model_id']
    origin=asset.wavelength_model.origin
    delta=entity.matrix_world@origin.matrix_world.inverted() if entity and origin else Matrix.Identity(4)
    for obj in original:
        clone=obj.copy()
        if obj.data:clone.data=obj.data.copy()
        variant.objects.link(clone);mapping[obj]=clone
        clone.pop('wl_custom_model_owner',None);clone.pop('wl_custom_model_previous_exclude',None);clone['wl_model_asset']=variant
        clone['wl_role']='MODEL_SOURCE';clone['wl_exclude']=True
        if obj==collision_only:clone['wl_model_collision_only']=True
        if clone.type=='MESH':
            for i,mat in enumerate(clone.data.materials):
                if mat:
                    if mat not in materials:
                        materials[mat]=mat.copy()
                        if materials[mat].use_nodes:own_tree(materials[mat].node_tree)
                    clone.data.materials[i]=materials[mat]
    anchor=_anchor(context,variant,entity.matrix_world.copy() if entity else origin.matrix_world.copy() if origin else Matrix.Identity(4))
    variant.wavelength_model.origin=anchor
    worlds={obj:delta@obj.matrix_world for obj in original}
    for obj,clone in mapping.items():
        world=worlds[obj];parent=mapping.get(obj.parent,anchor);basis=obj.matrix_basis.copy()
        parent_world=worlds[obj.parent] if obj.parent in mapping else anchor.matrix_world
        clone.parent=parent;clone.matrix_parent_inverse=parent_world.inverted()@world@basis.inverted();clone.matrix_basis=basis
        for modifier in clone.modifiers:
            for prop in modifier.bl_rna.properties:
                if prop.type=='POINTER' and not prop.is_readonly:
                    value=getattr(modifier,prop.identifier,None)
                    if isinstance(value,bpy.types.Object) and value in mapping:setattr(modifier,prop.identifier,mapping[value])
            if modifier.type=='NODES' and modifier.node_group:
                group=modifier.node_group
                if group not in groups:groups[group]=group.copy();own_tree(groups[group])
                modifier.node_group=groups[group]
                try:inputs=list(modifier.items())
                except TypeError:inputs=[]
                for key,value in inputs:
                    if isinstance(value,bpy.types.Object) and value in mapping:modifier[key]=mapping[value]
        for constraint in clone.constraints:
            if hasattr(constraint,'target') and constraint.target in mapping:constraint.target=mapping[constraint.target]
        if clone.type=='ARMATURE':
            for bone in clone.pose.bones:
                for constraint in bone.constraints:
                    if hasattr(constraint,'target') and constraint.target in mapping:constraint.target=mapping[constraint.target]
        for block in (clone,clone.data,getattr(clone.data,'shape_keys',None)):
            animation=getattr(block,'animation_data',None)
            if not animation:continue
            def independent(action):
                if action and action not in actions:actions[action]=action.copy()
                return actions.get(action)
            if animation.action:animation.action=independent(animation.action)
            for track in animation.nla_tracks:
                for strip in track.strips:
                    if strip.action:strip.action=independent(strip.action)
            for fcurve in animation.drivers:
                for variable in fcurve.driver.variables:
                    for target in variable.targets:
                        if target.id in mapping:target.id=mapping[target.id]
    for tree in [*[m.node_tree for m in materials.values() if m.use_nodes],*groups.values()]:
        for node in tree.nodes:
            for socket in node.inputs:
                value=getattr(socket,'default_value',None)
                if isinstance(value,bpy.types.Object) and value in mapping:socket.default_value=mapping[value]
                elif isinstance(value,bpy.types.Material) and value in materials:socket.default_value=materials[value]
    state=asset.wavelength_model;new=variant.wavelength_model
    for key in ('deployment','collision_mode','mass','prop_data','surface_prop'):setattr(new,key,getattr(state,key))
    new.collision=mapping.get(state.collision,state.collision)
    for old in state.clips:
        clip=new.clips.add()
        for key in ('name','start','end','fps','loop','activity'):setattr(clip,key,getattr(old,key))
    context.view_layer.update()
    if entity:
        others=_release(context,asset,entity)
        if not others:asset.hide_viewport=True;asset.hide_render=True
        attach(context,variant,entity)
    else:select_sources(context,variant)
    return variant


def detach(context,asset,entity):
    """Copy this placement out for independent modelling; leave placements intact."""
    ensure(context,asset)
    if entity.get('wl_custom_model')!=asset:raise ValueError('Select a placement of this model asset')
    detached=make_unique(context,asset)
    origin=detached.wavelength_model.origin
    # The copy was made at the authoring origin. Its editable anchor places it
    # at the selected instance without editing the original definition or entity.
    origin.matrix_world=entity.matrix_world.copy();context.view_layer.update()
    for obj in sources(detached):
        obj.pop('wl_custom_model_owner',None);obj['wl_role']='MODEL_SOURCE';obj['wl_exclude']=True;obj['wl_model_asset']=detached
    detached['wl_model_status']='Editable · detached';select_sources(context,detached)
    return detached
