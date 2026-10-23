"""Editable custom Source models owned by map entities and built as dependencies."""
import hashlib,json,os,shutil,uuid,re
from pathlib import Path
import bpy
from mathutils import Matrix
from bpy.props import StringProperty,EnumProperty,FloatProperty,IntProperty,BoolProperty,PointerProperty,CollectionProperty
from . import profiles,workspace,model_materials,model_smd,model_formats,source_assets


class WLModelClip(bpy.types.PropertyGroup):
    name:StringProperty(name='Sequence',default='animation')
    start:IntProperty(name='Start',default=1)
    end:IntProperty(name='End',default=30)
    fps:FloatProperty(name='FPS',default=30,min=1,max=120)
    loop:BoolProperty(name='Loop',default=False)
    activity:StringProperty(name='Activity',description='Optional Source activity such as ACT_IDLE; game-specific sequence mapping')


class WLModelDefinition(bpy.types.PropertyGroup):
    origin:PointerProperty(name='Origin Entity',type=bpy.types.Object)
    deployment:EnumProperty(name='Deployment',items=[('PROJECT','Project Default',''),('BSP','Inside BSP',''),('GAME','Game Directory','')],default='PROJECT')
    collision_mode:EnumProperty(name='Collision',items=[('NONE','None',''),('CONVEX','Convex Hull','Build a convex hull around the render geometry'),('OBJECT','Collision Object','Build a convex hull from the chosen collision mesh')],default='NONE')
    collision:PointerProperty(name='Collision Mesh',type=bpy.types.Object)
    mass:FloatProperty(name='Mass (kg)',default=10,min=.01)
    prop_data:StringProperty(name='Physics Prop Data',default='Metal.Small')
    surface_prop:StringProperty(name='Surface Property',default='default')
    clips:CollectionProperty(type=WLModelClip)
    status:StringProperty(default='Not built')


def definition(entity):return entity.get('wl_custom_model') if entity else None


def selected_owner(context):
    obj=context.object
    if obj and obj.get('wl_custom_model_owner'):return obj['wl_custom_model_owner']
    return obj if definition(obj) else None


def assignment_target(context):
    def owner(obj):
        if obj and obj.get('wl_model_reference'):obj=obj.parent
        if obj and obj.get('wl_custom_model_owner'):obj=obj['wl_custom_model_owner']
        return obj if obj and obj.get('wl_role')=='ENTITY' and not obj.get('wl_exclude') else None
    active=owner(context.view_layer.objects.active)
    if active:return active
    candidates={entity for obj in context.selected_objects if (entity:=owner(obj)) is not None}
    if len(candidates)==1:return candidates.pop()
    if candidates:raise ValueError('Multiple target entities selected; make the intended entity active or select only one target')
    raise ValueError('Select a placed model entity (such as prop_static) together with your source meshes; a mesh alone is not an entity')


def assign(context):
    from .entity import source_schema,models
    context.view_layer.update();s=context.scene.wavelength
    if context.mode!='OBJECT':raise ValueError('Assign model sources in Object Mode')
    if not profiles.is_source(s.engine):raise ValueError('Custom model compilation currently requires a Source profile')
    entity=assignment_target(context)
    classname=dict(json.loads(entity.get('wl_pairs','[]'))).get('classname','')
    kind=source_schema.definitions(s,bpy.path.abspath).get(classname,{}).get('kind','').lower()
    if kind=='solidclass':raise ValueError(f'{classname} uses BSP brushes, not MDL models. Select convex brushes and use Make Brush Entity; model doors use prop_door_rotating with a compatible door model')
    if not any(p['key']=='model' for p in source_schema.model_fields(s,classname,bpy.path.abspath)):raise ValueError(f'{classname or entity.name} has no assignable model property in the active game; choose a model entity such as prop_static, prop_dynamic or prop_physics')
    if classname=='prop_ragdoll':raise ValueError('Custom ragdolls need articulated collision joints; use static, dynamic or rigid physics props for this model pipeline')
    objects={o for o in context.selected_objects if o!=entity and o.type in {'MESH','ARMATURE'} and not o.get('wl_model_reference') and o.get('wl_role')!='ENTITY'}
    for obj in list(objects):objects.update(c for c in obj.children_recursive if c.type in {'MESH','ARMATURE'} and not c.get('wl_model_reference') and c.get('wl_role')!='ENTITY')
    for obj in list(objects):
        if obj.type=='MESH':objects.update(m.object for m in obj.modifiers if m.type=='ARMATURE' and m.object)
    if not any(o.type=='MESH' for o in objects):raise ValueError('Select at least one model mesh along with the entity')
    existing=definition(entity)
    if existing and (existing.get('wl_owner_profile')!=s.engine or existing.get('wl_game_dir')!=bpy.path.abspath(s.game_dir)):raise ValueError('Activate this custom model’s owning game profile before editing its sources')
    if existing and existing.wavelength_model.origin!=entity:raise ValueError('Add source objects on the custom model’s origin entity, not a shared instance')
    if any(o.get('wl_custom_model_owner') and o.get('wl_custom_model_owner')!=entity for o in objects):raise ValueError('Source objects already belong to another custom model')
    if any(o.get('wl_entity_id') for o in objects):raise ValueError('Convert brush entities to ordinary model meshes before assignment')
    model_id=existing['wl_custom_model_id'] if existing else uuid.uuid4().hex;collection=existing or bpy.data.collections.new('Model · '+entity.name)
    collection['wl_custom_model_id']=model_id;collection['wl_owner_profile']=s.engine;collection['wl_game_dir']=bpy.path.abspath(s.game_dir)
    state=collection.wavelength_model;state.origin=entity
    if classname.startswith('prop_physics') or classname=='prop_door_rotating':state.collision_mode='CONVEX'
    animated=any(o.animation_data and (o.animation_data.action or o.animation_data.nla_tracks) for o in objects)
    if animated and classname=='prop_static':
        if not existing:bpy.data.collections.remove(collection)
        raise ValueError('An animated model needs a dynamic entity, not prop_static')
    if animated and classname.startswith('prop_physics'):
        if not existing:bpy.data.collections.remove(collection)
        raise ValueError('Use a dynamic entity for animated models; rigid physics props cannot animate their shape')
    if animated and not state.clips:
        clip=state.clips.add();clip.start=context.scene.frame_start;clip.end=context.scene.frame_end;clip.fps=context.scene.render.fps/context.scene.render.fps_base
    if not existing:entity['wl_custom_previous_model']=dict(json.loads(entity['wl_pairs'])).get('model','')
    models.remove_reference(entity)
    for obj in objects:
        if obj.name not in collection.objects:collection.objects.link(obj)
        if not obj.get('wl_custom_model_owner'):obj['wl_custom_model_previous_exclude']=bool(obj.get('wl_exclude'))
        obj['wl_custom_model_owner']=entity;obj['wl_exclude']=True
        parent=obj.parent;inside=False
        while parent:
            if parent in objects:inside=True;break
            parent=parent.parent
        if not inside:
            basis=obj.matrix_basis.copy();old_parent=obj.parent.matrix_world@obj.matrix_parent_inverse if obj.parent else Matrix.Identity(4)
            obj.parent=entity;obj.matrix_parent_inverse=entity.matrix_world.inverted()@old_parent;obj.matrix_basis=basis
    entity['wl_custom_model']=collection;entity['wl_owner_profile']=s.engine
    pairs=[p for p in json.loads(entity['wl_pairs']) if p[0]!='model'];pairs.append(['model','models/wavelength/'+model_id+'/model.mdl']);entity['wl_pairs']=json.dumps(pairs)
    entity.select_set(True);context.view_layer.objects.active=entity
    context.view_layer.update()
    return collection


def stage_game(settings,work):
    game=Path(bpy.path.abspath(settings.game_dir)).resolve();assets=source_assets.library(game);stage=work/'model_game';stage.mkdir(parents=True,exist_ok=True)
    q=model_formats.quote;paths=[('Game',stage),('GameBin',game/'bin')]
    paths.extend(('Game' if isinstance(m,Path) else 'Game',m if isinstance(m,Path) else m.path) for m in assets.mounts)
    paths.append(('Platform',game.parent/'platform'))
    text='"GameInfo"\n{\n "game" "Wavelength model build"\n "FileSystem" {\n "SteamAppId" '+q(profiles.get(settings.engine).get('steam_app_id','220'))+'\n "SearchPaths" {\n'+''.join(q(k)+' '+q(str(p))+'\n' for k,p in paths)+'}\n}\n}\n'
    (stage/'gameinfo.txt').write_text(text,encoding='utf-8');return stage


def prepare(scene,work):
    """Snapshot sources; return queued compiler commands and a validation step."""
    entities=[o for o in scene.objects if definition(o) and not o.get('wl_exclude')]
    if not entities:return None
    s=scene.wavelength;stage=stage_game(s,work)
    from .build.toolchains import resolve_compiler
    compiler=resolve_compiler(bpy.path.abspath(s.compiler_dir),'studiomdl',bool(json.loads(s.wrapper)))
    jobs=[];commands=[];seen={}
    for entity in entities:
        col=definition(entity);state=col.wavelength_model
        if col.get('wl_owner_profile')!=s.engine or col.get('wl_game_dir')!=bpy.path.abspath(s.game_dir):raise ValueError('Custom model belongs to another engine/game profile')
        if state.origin is None:raise ValueError('Custom model origin is missing')
        if any(abs(v-1)>1e-5 for v in entity.matrix_world.to_scale()):raise ValueError('Keep the model entity scale at 1; resize the editable source meshes instead')
        classname=dict(json.loads(entity['wl_pairs'])).get('classname','')
        if classname=='prop_static' and state.clips:raise ValueError('Animated custom models cannot use prop_static')
        if classname.startswith('prop_physics') and state.clips:raise ValueError('Rigid physics custom models cannot have animation clips; use a dynamic entity')
        if classname=='prop_ragdoll':raise ValueError('Custom ragdoll collision-joint export is not implemented')
        physics=classname.startswith('prop_physics')
        if classname=='prop_door_rotating' and state.collision_mode=='NONE':state.collision_mode='CONVEX'
        if physics and state.collision_mode=='NONE':raise ValueError('Physics custom model needs collision')
        if state.collision_mode=='OBJECT' and not state.collision:raise ValueError('Choose a collision mesh')
        if state.collision and state.collision.name not in col.objects:raise ValueError('Add the collision mesh to this custom model’s source objects first')
        if state.collision and state.collision.name not in scene.objects:raise ValueError('Collision source was removed from the scene; choose a collision mesh or use Convex Hull')
        mid=col['wl_custom_model_id']
        if not re.fullmatch('[0-9a-f]{32}',mid):raise ValueError('Invalid managed custom-model identity')
        style='PHYSICS' if physics else 'STATIC' if classname=='prop_static' else 'DYNAMIC'
        if mid in seen:
            if seen[mid]!=(col,style):raise ValueError('A shared custom model must use compatible entity types; make a separate model for static versus dynamic/physics use')
            continue
        seen[mid]=(col,style)
        namespace='wavelength/'+mid;source=work/'model_sources'/mid;source.mkdir(parents=True,exist_ok=True)
        materials={None}
        for obj in col.objects:
            if obj.name in scene.objects and obj.type=='MESH' and obj!=state.collision:materials.update(obj.data.materials)
        names={mat:f'material_{i}' for i,mat in enumerate(sorted(materials,key=lambda m:m.name if m else ''))}
        files={}
        for mat,name in names.items():files.update(model_materials.convert(mat,namespace+'/'+name,s))
        smds=model_smd.export(col,scene,names)
        qc=[f'$modelname {model_formats.quote(namespace+"/model.mdl")}','$body body "reference.smd"',f'$cdmaterials {model_formats.quote(namespace+"/")}','$surfaceprop '+model_formats.quote(state.surface_prop)]
        if physics:
            from . import keyvalues
            props=keyvalues.child(keyvalues.parse(source_assets.library(bpy.path.abspath(s.game_dir)).read('scripts/propdata.txt').decode(errors='replace')),'PropData.txt')
            if state.prop_data.casefold() not in {k.casefold() for k,v in props if isinstance(v,list)}:raise ValueError('Physics prop-data base is not defined by this game: '+state.prop_data)
            qc.append('$keyvalues\n{\n prop_data\n {\n base '+model_formats.quote(state.prop_data)+'\n health 0\n }\n}')
        if classname=='prop_static':qc.append('$staticprop')
        if classname=='prop_door_rotating':qc.append('$keyvalues\n{\n door_options\n {\n skin0 { surfaceprop '+model_formats.quote(state.surface_prop)+' }\n defaults { open "DoorSound.Null" close "DoorSound.Null" move "DoorSound.Null" locked "DoorSound.Null" unlocked "DoorSound.Null" }\n }\n}')
        if state.clips:
            used=set()
            for i,clip in enumerate(state.clips):
                if not clip.name or clip.name in used:raise ValueError('Model animation sequence names must be nonempty and unique')
                used.add(clip.name);qc.append(f'$sequence {model_formats.quote(clip.name)} "clip_{i}.smd" fps {clip.fps:g}'+(' loop' if clip.loop else '')+(' activity '+model_formats.quote(clip.activity)+' 1' if clip.activity else ''))
        else:qc.append('$sequence idle "reference.smd" fps 30')
        if state.collision_mode!='NONE':qc.append('$collisionmodel "collision.smd"\n{\n $mass '+str(state.mass)+'\n}')
        smds['model.qc']='\n'.join(qc)+'\n'
        for name,text in smds.items():(source/name).write_text(text,encoding='utf-8')
        for name,payload in files.items():
            dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
        digest=hashlib.sha256()
        for name,text in sorted(smds.items()):digest.update(name.encode()+text.encode())
        for name,payload in sorted(files.items()):digest.update(name.encode()+payload)
        digest.update(str((str(compiler),compiler.stat().st_mtime_ns,compiler.stat().st_size,s.engine,s.game_dir)).encode());fingerprint=digest.hexdigest()
        cache=Path(bpy.path.abspath(s.project_dir))/'.wavelength'/'models'/mid
        cache.mkdir(parents=True,exist_ok=True)
        try:manifest=json.loads((cache/'manifest.json').read_text())
        except (OSError,ValueError):manifest={}
        for name in manifest.get('files',{}):
            safe=source_assets.asset_path(name)
            if not (safe.startswith('models/'+namespace+'/model.') or safe.startswith('materials/'+namespace+'/')):raise ValueError('Invalid custom-model cache resource path')
        cached=manifest.get('fingerprint')==fingerprint and all((cache/name).is_file() and hashlib.sha256((cache/name).read_bytes()).hexdigest()==sha for name,sha in manifest.get('files',{}).items()) and bool(manifest.get('files'))
        if cached:
            for name in manifest['files']:
                dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(cache/name,dest)
        else:
            def native_path(path):return 'Z:'+str(path).replace('/',chr(92)) if compiler.suffix.lower()=='.exe' and os.name!='nt' else str(path)
            commands.append([*json.loads(s.wrapper),str(compiler),'-nop4','-game',native_path(stage),native_path(source/'model.qc')])
        jobs.append(dict(entity=entity,collection=col,cache=cache,fingerprint=fingerprint,materials=list(files),physics=physics,collision=state.collision_mode!='NONE',mid=mid))
        state.status='Cached' if cached else 'Queued for compilation'
    return BuildModels(scene,stage,jobs,commands)


class BuildModels:
    def __init__(self,scene,stage,jobs,commands):self.scene=scene;self.stage=stage;self.jobs=jobs;self.commands=commands;self.pack={};self.deployments=[]
    def validated(self):
        from . import studio_model
        for job in self.jobs:
            mid=job['mid'];model='models/wavelength/'+mid+'/model'
            data=studio_model.load(source_assets.Assets(self.stage),model+'.mdl')
            if job['collision'] and not (self.stage/(model+'.phy')).is_file():raise ValueError('Model compiler produced no required collision data')
            files={p.relative_to(self.stage).as_posix():p.read_bytes() for p in (self.stage/('models/wavelength/'+mid)).glob('model.*') if p.is_file()}
            files.update({name:(self.stage/name).read_bytes() for name in job['materials']})
            manifest={'fingerprint':job['fingerprint'],'files':{name:hashlib.sha256(payload).hexdigest() for name,payload in files.items()}}
            for name,payload in files.items():
                path=job['cache']/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
            (job['cache']/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            state=job['collection'].wavelength_model;deployment=state.deployment if state.deployment!='PROJECT' else self.scene.wavelength.custom_model_deployment
            if deployment=='BSP':self.pack.update(files)
            else:
                root=Path(bpy.path.abspath(self.scene.wavelength.custom_model_directory or self.scene.wavelength.game_dir)).resolve()
                mounts=source_assets.library(bpy.path.abspath(self.scene.wavelength.game_dir)).mounts
                if not (root==Path(bpy.path.abspath(self.scene.wavelength.game_dir)).resolve() or any(isinstance(p,Path) and root==p.resolve() for p in mounts)):raise ValueError('Model deployment directory must be a directory mounted by the active game profile')
                self.deployments.append((root,files))
            state.status='Compiled; deployment queued'
    def finish(self,path):
        from .source_tools import validate_bsp
        validate_bsp(path.read_bytes())
        if self.pack:path.write_bytes(model_formats.pack_bsp(path.read_bytes(),self.pack))
        backups={}
        try:
            for root,files in self.deployments:
                for name,payload in files.items():
                    target=root/name;backups[target]=target.read_bytes() if target.exists() else None
                    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.wavelength-tmp');temporary.write_bytes(payload);temporary.replace(target)
        except Exception:
            for target,payload in backups.items():
                if payload is None:target.unlink(missing_ok=True)
                else:target.write_bytes(payload)
            raise
        for job in self.jobs:job['collection'].wavelength_model.status='Built'


class WL_OT_assign_custom_model(bpy.types.Operator):
    bl_idname='wavelength.assign_custom_model';bl_label='Assign Selected Model to Entity';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and profiles.is_source(context.scene.wavelength.engine)
    def execute(self,context):
        try:col=assign(context)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Custom model assigned; Build Map compiles its dependencies');return {'FINISHED'}


class WL_OT_custom_clip(bpy.types.Operator):
    bl_idname='wavelength.custom_model_clip';bl_label='Animation Clip';bl_options={'REGISTER','UNDO'}
    remove:IntProperty(default=-1)
    def execute(self,context):
        entity=selected_owner(context)
        if not entity:return {'CANCELLED'}
        clips=definition(entity).wavelength_model.clips
        if self.remove>=0:clips.remove(self.remove)
        else:
            clip=clips.add();clip.name='animation_'+str(len(clips));clip.start=context.scene.frame_start;clip.end=context.scene.frame_end;clip.fps=context.scene.render.fps/context.scene.render.fps_base
        return {'FINISHED'}


class WL_OT_detach_custom_model(bpy.types.Operator):
    bl_idname='wavelength.detach_custom_model';bl_label='Detach Custom Model';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        entity=selected_owner(context);col=definition(entity)
        if not col:return {'CANCELLED'}
        if any(o!=entity and definition(o)==col for o in bpy.data.objects):
            self.report({'ERROR'},'Other entities share this custom model; remove those bindings first');return {'CANCELLED'}
        origin=bpy.data.objects.new('Detached Model Sources',None);context.collection.objects.link(origin);origin.matrix_world=entity.matrix_world.copy()
        for obj in col.objects:
            if obj.parent==entity:
                inverse=obj.matrix_parent_inverse.copy();basis=obj.matrix_basis.copy();obj.parent=origin;obj.matrix_parent_inverse=inverse;obj.matrix_basis=basis
            obj['wl_exclude']=obj.get('wl_custom_model_previous_exclude',False)
            obj.pop('wl_custom_model_owner',None);obj.pop('wl_custom_model_previous_exclude',None)
        entity.pop('wl_custom_model',None)
        old=entity.pop('wl_custom_previous_model','');pairs=[p for p in json.loads(entity['wl_pairs']) if p[0]!='model']
        if old:pairs.append(['model',old])
        entity['wl_pairs']=json.dumps(pairs);bpy.data.collections.remove(col)
        from .entity import models
        models.attach_reference(entity);return {'FINISHED'}


class WL_PT_custom_model(bpy.types.Panel):
    bl_label='Wavelength Custom Model';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return workspace.active(context) and profiles.is_source(context.scene.wavelength.engine) and context.object
    def draw(self,context):
        l=self.layout;entity=selected_owner(context)
        if not entity:
            obj=context.object
            if obj and obj.get('wl_role')=='ENTITY':
                from .entity import source_schema
                classname=dict(json.loads(obj.get('wl_pairs','[]'))).get('classname','')
                kind=source_schema.definitions(context.scene.wavelength,bpy.path.abspath).get(classname,{}).get('kind','').lower()
                if kind=='solidclass':
                    l.label(text=classname+' uses brush geometry',icon='INFO')
                    l.label(text='Select convex brushes: Make Brush Entity')
                    l.label(text='MDL assignment requires a model entity');return
            l.operator('wavelength.assign_custom_model');l.label(text='Select source meshes and a model entity');return
        col=definition(entity);state=col.wavelength_model
        l.label(text=col.name);l.label(text=state.status);l.prop(state,'deployment')
        if state.deployment=='PROJECT':l.prop(context.scene.wavelength,'custom_model_deployment')
        l.prop(context.scene.wavelength,'custom_model_directory');l.prop(state,'collision_mode')
        if state.collision_mode=='OBJECT':l.prop(state,'collision')
        if state.collision_mode!='NONE':l.prop(state,'mass')
        l.prop(state,'surface_prop')
        if dict(json.loads(entity.get('wl_pairs','[]'))).get('classname','').startswith('prop_physics'):l.prop(state,'prop_data')
        l.label(text='Scene-frame animation clips')
        for i,clip in enumerate(state.clips):
            box=l.box();row=box.row();row.prop(clip,'name');row.operator('wavelength.custom_model_clip',text='',icon='X').remove=i
            row=box.row(align=True);row.prop(clip,'start');row.prop(clip,'end');box.prop(clip,'fps');box.prop(clip,'loop');box.prop(clip,'activity')
        l.operator('wavelength.custom_model_clip',text='Add Animation Clip',icon='ADD');l.label(text='Edit source meshes and rigs normally; Build Map updates them')
        l.operator('wavelength.assign_custom_model',text='Add Selected Sources');l.operator('wavelength.detach_custom_model')


CLASSES=(WLModelClip,WLModelDefinition,WL_OT_assign_custom_model,WL_OT_custom_clip,WL_OT_detach_custom_model,WL_PT_custom_model)
def object_menu(self,context):
    if workspace.active(context) and profiles.is_source(context.scene.wavelength.engine):
        self.layout.separator()
        self.layout.operator(WL_OT_assign_custom_model.bl_idname,icon='OUTLINER_OB_MESH')

def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Collection.wavelength_model=PointerProperty(type=WLModelDefinition)
    bpy.types.VIEW3D_MT_object.append(object_menu)
def unregister():
    bpy.types.VIEW3D_MT_object.remove(object_menu)
    del bpy.types.Collection.wavelength_model
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
