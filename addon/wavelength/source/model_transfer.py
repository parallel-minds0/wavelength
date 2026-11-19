"""Model build snapshots, target adapters and portable editable handoffs.

All conversion runs against temporary datablocks. The authoring scene/profile
and placement bindings are not changed by choosing another target game.
"""
import json,os,re,shutil,uuid,hashlib,struct
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
import bpy
from mathutils import Matrix
from . import model_pipeline,model_lifecycle as life,model_materials,profiles,mesh_assets,model_bundle

KINDS=('objects','scenes','collections','meshes','armatures','curves','lattices','materials','node_groups','images','actions')
_ACTIVE=set()


def target_settings(context,identity,game='',compiler=''):
    from . import cross_compile,source_tools
    values=dict(cross_compile.profile_settings(identity));engine=values['engine']
    defaults=source_tools.defaults(profiles.get(engine).get('platform','windows'),engine=engine) if profiles.is_source(engine) else mesh_assets.defaults(engine)
    active=context.scene.wavelength
    for key,value in defaults.items():values.setdefault(key,value)
    if active.engine==engine:
        for key in ('game_dir','compiler_dir','wrapper','unit_scale','fgd_path'):values[key]=getattr(active,key)
    # Registered overrides must win over the active template's cached paths.
    values.update(cross_compile.profile_settings(identity))
    if game:values['game_dir']=game
    if compiler:values['compiler_dir']=compiler
    values.setdefault('unit_scale',profiles.get(engine).get('unit_meters',1.))
    values.setdefault('wrapper','[]')
    return values


class Snapshot:
    def __init__(self,context,asset,work,target):
        self.context=context;self.original=context.scene;self.work=Path(work)
        self.before={kind:set(getattr(bpy.data,kind)) for kind in KINDS}
        self.selected=list(context.selected_objects);self.active=context.view_layer.objects.active
        self.scene=None;self.asset=None;self.closed=False;self.owned=None
        try:
            self.asset=life.make_unique(context,asset)
            self.asset['wl_model_id']=asset['wl_model_id'];self.asset['wl_custom_model_id']=asset['wl_model_id']
            # Stable compiler node names keep cache keys independent of Blender's
            # incidental .001 suffixes and unrelated objects in the user's level.
            for index,obj in enumerate(sorted(life.sources(self.asset),key=lambda o:o.name)):
                obj.name='.wl-build-'+asset['wl_model_id']+'-'+str(index)
            self.asset.pop('wl_model_build_owner',None)
            for obj in life.sources(self.asset):
                if obj.type=='MESH':
                    for material in obj.data.materials:
                        if material:model_materials.realize(material,SimpleNamespace(game_dir=asset.get('wl_model_game','')))
            self.scene=bpy.data.scenes.new('.wavelength model build')
            self.scene.collection.children.link(self.asset)
            self.origin=self.asset.wavelength_model.origin
            if self.origin:self.scene.collection.objects.link(self.origin);self.origin.matrix_world=Matrix.Identity(4)
            self.original.collection.children.unlink(self.asset)
            if self.origin and self.origin.name in self.original.collection.objects:self.original.collection.objects.unlink(self.origin)
            self.scene.render.fps=context.scene.render.fps;self.scene.render.fps_base=context.scene.render.fps_base
            self.scene.frame_start=context.scene.frame_start;self.scene.frame_end=context.scene.frame_end
            self.scene.frame_set(context.scene.frame_current)
            settings=self.scene.wavelength
            # Raw RNA storage avoids profile/grid/asset callbacks on the real scene.
            settings['engine']=profiles.PROFILE_ORDER.index(target['engine'])
            for key in ('game_dir','compiler_dir','wrapper','unit_scale','fgd_path'):
                if key in target:settings[key]=target[key]
            settings['project_dir']=str(self.work.parent/'model-cache'/mesh_assets.slug(target['engine']))
            settings['auto_prepare_assets']=False;settings['custom_model_deployment']='GAME'
            self.asset['wl_model_profile']=target['engine'];self.asset['wl_model_game']=target.get('game_dir','')
            self.asset['wl_owner_profile']=target['engine'];self.asset['wl_game_dir']=target.get('game_dir','')
            # Foreign level dependencies must not silently pull the level into a bundle.
            members=set(life.sources(self.asset))
            collision=self.asset.wavelength_model.collision
            if collision and collision not in members:raise ValueError('Include the collision mesh in the editable model sources before conversion')
            for obj in members:
                if obj.instance_collection:raise ValueError(obj.name+': realize collection instances before packaging a model')
                for modifier in obj.modifiers:
                    for prop in modifier.bl_rna.properties:
                        if prop.type=='POINTER':
                            value=getattr(modifier,prop.identifier,None)
                            if isinstance(value,bpy.types.Object) and value not in members:raise ValueError(obj.name+': include or apply external modifier dependency '+value.name)
                    if modifier.type=='NODES':
                        for value in modifier.values():self._dependency(value,members)
                for constraint in [*obj.constraints,*[c for bone in obj.pose.bones for c in bone.constraints]] if obj.type=='ARMATURE' else obj.constraints:
                    self._dependency(getattr(constraint,'target',None),members)
                for block in (obj,obj.data,getattr(obj.data,'shape_keys',None)):
                    animation=getattr(block,'animation_data',None)
                    if animation:
                        for driver in animation.drivers:
                            for variable in driver.driver.variables:
                                for target in variable.targets:
                                    if target.id and target.id not in members and target.id not in {o.data for o in members if o.data}:
                                        raise ValueError(obj.name+': bake external driver dependencies before packaging')
            visited=set()
            def tree(group):
                if not group or group in visited:return
                visited.add(group)
                for node in group.nodes:
                    for socket in node.inputs:self._dependency(getattr(socket,'default_value',None),members)
                    tree(getattr(node,'node_tree',None))
            for obj in members:
                for modifier in obj.modifiers:
                    if modifier.type=='NODES':tree(modifier.node_group)
                if obj.type=='MESH':
                    for material in obj.data.materials:
                        if material and material.use_nodes:tree(material.node_tree)
            self.restore_selection()
        except Exception:self.close();raise

    def _dependency(self,value,members):
        if isinstance(value,bpy.types.Object) and value not in members and value!=self.origin:
            raise ValueError('Include or bake external model dependency: '+value.name)
        if isinstance(value,(bpy.types.Collection,bpy.types.Scene)) and value not in {self.asset,self.scene}:
            raise ValueError('Realize external scene/collection dependencies before packaging: '+value.name)

    @contextmanager
    def activate(self):
        window=self.context.window;old=window.scene if window else None
        try:
            if window:window.scene=self.scene
            with self.context.temp_override(scene=self.scene,view_layer=self.scene.view_layers[0]):yield bpy.context
        finally:
            if window:window.scene=old

    def close(self):
        if self.closed:return
        self.closed=True
        if self.context.window and self.context.window.scene==self.scene:self.context.window.scene=self.original
        for kind in KINDS:
            collection=getattr(bpy.data,kind)
            owned=self.owned[kind] if self.owned is not None else set(collection)-self.before[kind]
            for item in tuple(collection):
                if item in owned:
                    if kind in {'objects','scenes','collections'}:collection.remove(item,do_unlink=True)
                    else:collection.remove(item)
        if self.owned is None:self.restore_selection()

    def freeze(self):
        # Modal compilation yields to the user. Only our own staged IDs may be
        # removed later; unrelated objects created while a compiler runs survive.
        self.owned={kind:set(getattr(bpy.data,kind))-self.before[kind] for kind in KINDS}

    def restore_selection(self):
        for obj in self.context.selected_objects:obj.select_set(False)
        for obj in self.selected:
            if obj.name in self.original.objects:obj.select_set(True)
        self.context.view_layer.objects.active=self.active


def _commit(root,files):
    _commit_many([(root,files)])


def _commit_many(destinations):
    """Commit the validated set together, restoring last-working files on failure."""
    backups={}
    try:
      for root,files in destinations:
        root=Path(root)
        for name,payload in files.items():
            target=root/model_bundle.safe_path(name);target.parent.mkdir(parents=True,exist_ok=True)
            if target not in backups:backups[target]=target.read_bytes() if target.exists() else None
            temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.partial')
            try:temporary.write_bytes(payload);os.replace(temporary,target)
            finally:temporary.unlink(missing_ok=True)
    except Exception:
        for target,payload in backups.items():
            if payload is None:target.unlink(missing_ok=True)
            else:target.write_bytes(payload)
        raise


class Job:
    def __init__(self,context,asset,work,target_profile,target,output,publish,package,allow_lossy,addon,model_name):
        self.context=context;self.original=asset;self.work=Path(work);self.work.mkdir(parents=True,exist_ok=True)
        self.target=target;self.output=Path(output).resolve();self.publish=publish;self.package=package;self.addon=addon
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',model_name) or re.fullmatch(r'CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]',model_name,re.I):
            raise ValueError('Enter a model name of up to 32 letters, digits, underscores or hyphens, excluding Windows reserved names')
        self.model_name=model_name.lower()
        self.commands=[];self.build=None;self.external=[];self.closed=False
        self.files={};self.primary='';self.allow_lossy=allow_lossy
        source_family=profiles.family(asset['wl_model_profile']);target_family=profiles.family(target['engine'])
        self.report={'schema':1,'asset_id':asset['wl_model_id'],'source_profile':asset['wl_model_profile'],'target_profile':target_profile,
                     'source_game':asset.get('wl_model_game',''),'target_engine':target['engine'],'warnings':[],'animations':[],
                     'materials':[],'source_unit_meters':asset.get('wl_model_unit_meters',1.),'target_unit_meters':target['unit_scale']}
        adapter=model_pipeline.route(source_family,target_family)
        self.identity=asset['wl_model_id']
        if self.identity in _ACTIVE:raise ValueError('This model already has a build running')
        _ACTIVE.add(self.identity);self.snapshot=None
        try:
            self.snapshot=Snapshot(context,asset,work,target)
            if package:self._capture_editable()
            adapter(self)
            self.snapshot.freeze()
        except Exception:self.close();raise

    def omitted(self,message):
        if not self.allow_lossy:raise ValueError(message+'; enable Allow Static/Approximate Conversion only if this omission is intentional')
        self.report['warnings'].append(message)

    def finish(self):
        if self.build:
            self.build.validated()
            self.primary=self.build.jobs[0]['model']+'.mdl'
            stage=self.build.stage
            for name in self.build.jobs[0]['materials']:self.files[name]=(stage/name).read_bytes()
            namespace=Path(self.primary).parent
            for path in (stage/namespace).glob(Path(self.primary).stem+'.*'):self.files[path.relative_to(stage).as_posix()]=path.read_bytes()
            for path in (self.work/'native'/'model_sources').rglob('*'):
                if path.is_file():self.files['sources/'+path.relative_to(self.work/'native'/'model_sources').as_posix()]=path.read_bytes()
        elif self.target['engine']=='source2_cs2_windows':self._finish_source2()
        self.report['primary']=self.primary
        self.report['files']={name:hashlib.sha256(payload).hexdigest() for name,payload in self.files.items()}
        self.files['conversion-report.json']=json.dumps(self.report,indent=2).encode()
        if self.package:
            self.write_package(self.work/'asset.wlmodel')
            self.files['asset.wlmodel']=(self.work/'asset.wlmodel').read_bytes()
        destinations=[(self.output,self.files)]
        if self.publish and self.build:destinations.extend(self.build.deployments)
        if self.publish and hasattr(self,'deployments'):destinations.extend(self.deployments)
        _commit_many(destinations)
        self.original['wl_model_last_report']=str(self.output/'conversion-report.json')
        outputs=json.loads(self.original.get('wl_model_outputs','{}'));outputs[self.report['target_profile']]={'primary':self.primary,'directory':str(self.output)}
        self.original['wl_model_outputs']=json.dumps(outputs)
        if self.target['engine']==self.original['wl_model_profile'] and self.target.get('game_dir')==self.original.get('wl_model_game'):
            self.original['wl_model_output']=self.primary
            if self.publish:
                from . import model_browser
                model_browser.published(self.context,self.primary)
        block=bpy.data.texts.get('wavelength Model Conversion Report') or bpy.data.texts.new('wavelength Model Conversion Report')
        block.clear();block.write(json.dumps(self.report,indent=2))
        return str(self.output/self.primary)

    def _capture_editable(self):
        # Package the source definition, not the target's temporary compile origin.
        with self.snapshot.activate():
            original_profile=self.snapshot.asset['wl_model_profile'];original_game=self.snapshot.asset['wl_model_game']
            self.snapshot.asset['wl_model_profile']=self.original['wl_model_profile'];self.snapshot.asset['wl_model_game']=self.original.get('wl_model_game','')
            self.snapshot.asset['wl_owner_profile']=self.original['wl_model_profile'];self.snapshot.asset['wl_game_dir']=self.original.get('wl_model_game','')
            self.snapshot.asset.pop('wl_model_build_owner',None)
            for obj in life.sources(self.snapshot.asset):obj.pop('wl_custom_model_owner',None)
            for obj in life.sources(self.snapshot.asset):
                if obj.type=='MESH':
                    for material in obj.data.materials:
                        if material and material.use_nodes:
                            for node in material.node_tree.nodes:
                                if node.type=='TEX_IMAGE' and node.image:life._pack_image(node.image)
            blend=self.work/'editable.blend'
            bpy.data.libraries.write(str(blend),{self.snapshot.asset},fake_user=True,compress=True)
            self.snapshot.asset['wl_model_profile']=original_profile;self.snapshot.asset['wl_model_game']=original_game
            self.snapshot.asset['wl_owner_profile']=original_profile;self.snapshot.asset['wl_game_dir']=original_game
        self.editable=blend

    def write_package(self,path):
        files={'editable.blend':self.editable,'conversion-report.json':json.dumps(self.report,indent=2).encode()}
        files.update({'output/'+name:payload for name,payload in self.files.items()})
        files['README.txt']=b'Import this .wlmodel through wavelength Model IO, or append its collection from editable.blend. Output contains the target handoff. Review conversion-report.json for limitations.\n'
        return model_bundle.write(path,files,{'asset_id':self.original['wl_model_id'],'editable':'editable.blend','collection':self.snapshot.asset.name,'target_profile':self.report['target_profile']})

    def close(self):
        if self.closed:return
        self.closed=True
        if self.snapshot:self.snapshot.close()
        _ACTIVE.discard(self.identity)
        for directory in self.external:
            directory=Path(directory)
            # These exact, newly-created per-job addon directories are owned by us.
            if directory.is_dir() and directory.name.startswith('wavelength_model_build_'):shutil.rmtree(directory)

    def _finish_source2(self):
        source,compiled=self.source2_dirs
        model=compiled/self.primary.replace('content/','',1)
        model=Path(str(model)+'_c')
        if not model.is_file():raise ValueError('CS2 compiler did not produce the model')
        compiled_files={}
        for path in compiled.rglob('*'):
            if not path.is_file() or not path.name.endswith('_c'):continue
            payload=path.read_bytes()
            if len(payload)<16 or not 16<=struct.unpack_from('<I',payload)[0]<=len(payload):raise ValueError('Invalid compiled CS2 resource: '+str(path))
            compiled_files[path.relative_to(compiled).as_posix()]=payload
            self.files['compiled/'+path.relative_to(compiled).as_posix()]=payload
        if self.publish:
            if not self.addon or not all(c.isalnum() or c=='_' for c in self.addon):raise ValueError('Choose a CS2 Target Addon name before deployment')
            root=Path(self.target['game_dir']).parents[1]
            self.deployments=[(root/'content/csgo_addons'/self.addon,{k.removeprefix('content/'):v for k,v in self.files.items() if k.startswith('content/')}),
                              (root/'game/csgo_addons'/self.addon,compiled_files)]


def source1(job):
    from .model_backend_source1 import Source1
    with job.snapshot.activate() as context:
        state=job.snapshot.asset.wavelength_model
        if not state.clips and any(o.animation_data and (o.animation_data.action or o.animation_data.nla_tracks) for o in life.sources(job.snapshot.asset)):
            clip=state.clips.add();clip.name='animation';clip.start=context.scene.frame_start;clip.end=context.scene.frame_end;clip.fps=context.scene.render.fps/context.scene.render.fps_base
        result=Source1().prepare(context,job.snapshot.asset,job.work/'native',model_name=job.model_name)
        job.build=result.build;job.commands=list(result.commands)
        job.report['animations']=[{'name':c.name,'fps':c.fps,'start':c.start,'end':c.end} for c in state.clips]
        job.report['collision']=state.collision_mode


def _clips_for_gltf(job):
    """Map supported one-action clips onto independent NLA tracks at their FPS."""
    state=job.snapshot.asset.wavelength_model;scene=job.snapshot.scene
    if not state.clips:return
    scene_rate=scene.render.fps/scene.render.fps_base
    for obj in life.sources(job.snapshot.asset):
        animation=obj.animation_data
        if not animation:continue
        active=animation.action;tracks=list(animation.nla_tracks)
        for track in tracks:track.mute=True
        for clip in state.clips:
            matching=next((t for t in tracks if t.name==clip.name),None)
            if matching:
                if len(matching.strips)!=1:raise ValueError(clip.name+': bake layered NLA to one action before model conversion')
                old=matching.strips[0];action=old.action
                start=old.action_frame_start+(clip.start-old.frame_start)/old.scale
                end=old.action_frame_start+(clip.end-old.frame_start)/old.scale
            elif active:action=active;start=clip.start;end=clip.end
            else:continue
            if start<action.frame_range[0]-.01 or end>action.frame_range[1]+.01:raise ValueError(clip.name+': clip range exceeds its action')
            track=animation.nla_tracks.new();track.name=clip.name
            # Remove the original named track after retaining its action/range,
            # so Blender does not suffix the exported animation's intended name.
            if matching:tracks.remove(matching);animation.nla_tracks.remove(matching);track.name=clip.name
            strip=track.strips.new(clip.name,1,action);strip.action_frame_start=start;strip.action_frame_end=end
            strip.scale=scene_rate/clip.fps;strip.extrapolation='NOTHING';strip.blend_type='REPLACE'
        animation.action=None
    job.report['animations']=[{'name':c.name,'fps':c.fps,'frames':c.end-c.start+1} for c in state.clips]


def godot(job):
    with job.snapshot.activate() as context:
        _pbr_limits(job)
        _clips_for_gltf(job)
        for obj in life.sources(job.snapshot.asset):
            if obj.type in {'CURVE','LATTICE'} or obj.get('wl_model_collision_only'):obj.hide_render=True
        state=job.snapshot.asset.wavelength_model
        if state.collision_mode!='NONE':job.omitted('Godot collision reconstruction is not implemented; render meshes and animation are exported')
        primary=job.work/(job.model_name+'.glb')
        result=bpy.ops.export_scene.gltf(filepath=str(primary),export_format='GLB',use_selection=False,use_active_scene=True,
            use_renderable=True,
            export_animations=True,export_animation_mode='NLA_TRACKS',export_anim_slide_to_zero=True,export_frame_range=False,
            export_extras=False,export_cameras=False,export_lights=False,export_yup=True)
        if result!={'FINISHED'}:raise ValueError('glTF model export did not finish')
        payload=primary.read_bytes()
        if payload[:4]!=b'glTF' or struct.unpack_from('<I',payload,8)[0]!=len(payload):raise ValueError('Invalid glTF model output')
        job.primary=primary.name;job.files[job.primary]=payload
        job.report['target_unit_meters']=1.;job.report['collision']='manual' if state.collision_mode!='NONE' else 'none'


def _pbr_limits(job):
    """Native VMT shader features have no automatic Principled equivalent."""
    materials={m for o in life.sources(job.snapshot.asset) if o.type=='MESH' for m in o.data.materials if m}
    for material in materials:
        props=json.loads(material.get('wl_model_source_vmt','{}'))
        unsupported=sorted(key for key,value in props.items() if value and
            key in {'$detail','$envmap','$phong','$selfillum','$rimlight','$basetexturetransform','$bumptransform','$color','$color2'})
        if unsupported:job.omitted(material.name+': native shader features require baking/manual authoring for this target: '+', '.join(unsupported))


def _source2_material(job,material,index,root):
    key='material_'+str(index);folder=Path('materials/wavelength')/job.original['wl_model_id']
    (root/folder).mkdir(parents=True,exist_ok=True)
    shader=mesh_assets._shader(material)
    def image_input(socket,normal=False):
        if not socket.is_linked:return None
        node=socket.links[0].from_node
        if normal:
            if node.type!='NORMAL_MAP' or node.space!='TANGENT' or not node.inputs['Color'].is_linked:raise ValueError(material.name+': bake normal/bump nodes before CS2 model conversion')
            if abs(node.inputs['Strength'].default_value-1)>1e-6:raise ValueError(material.name+': bake normal strength into the texture before CS2 conversion')
            node=node.inputs['Color'].links[0].from_node
        if node.type!='TEX_IMAGE' or not node.image:raise ValueError(material.name+': bake procedural model textures before CS2 conversion')
        vector=node.inputs['Vector']
        if vector.is_linked and (vector.links[0].from_node.type not in {'UVMAP','TEX_COORD'} or vector.links[0].from_node.type=='TEX_COORD' and vector.links[0].from_socket.name!='UV'):
            raise ValueError(material.name+': bake texture coordinates to UVs before CS2 model conversion')
        return node.image
    fields={'shader':'csgo_complex.vfx','g_vColorTint':'[1 1 1 0]'}
    for socket,field,suffix,normal in (('Base Color','TextureColor','color',False),('Normal','TextureNormal','normal',True),('Roughness','TextureRoughness','roughness',False),('Metallic','TextureMetalness','metalness',False)):
        value=shader.inputs[socket] if shader else None
        image=image_input(value,normal) if value else None
        if image:
            copy=life._owned_image(image)
            try:
                if normal:
                    from array import array
                    pixels=array('f',[0.])*(copy.size[0]*copy.size[1]*4);copy.pixels.foreach_get(pixels)
                    for channel in range(1,len(pixels),4):pixels[channel]=1-pixels[channel]
                    copy.pixels.foreach_set(pixels);copy.update()
                relative=folder/(key+'_'+suffix+'.png');copy.file_format='PNG';copy.filepath_raw=str(root/relative);copy.save()
                fields[field]=relative.as_posix()
            finally:bpy.data.images.remove(copy)
        else:
            color=value.default_value if value else tuple(material.diffuse_color) if socket=='Base Color' else .5 if socket=='Roughness' else 0.
            components=tuple(color)[:3] if hasattr(color,'__len__') else (color,)*3
            fields[field]='['+' '.join(str(float(v)) for v in components)+' 0]'
    if shader and (shader.inputs['Alpha'].is_linked or shader.inputs['Alpha'].default_value<.999):
        props=json.loads(material.get('wl_model_source_vmt','{}'));fields['F_ALPHA_TEST' if props.get('$alphatest')=='1' else 'F_TRANSLUCENT']=1
    path=folder/(key+'.vmat')
    (root/path).write_text('Layer0\n{\n'+''.join(' '+k+' '+(str(v) if isinstance(v,int) else json.dumps(v))+'\n' for k,v in fields.items())+'}\n')
    return path.as_posix()


def source2(job):
    _pbr_limits(job)
    state=job.snapshot.asset.wavelength_model
    if state.clips or any(o.animation_data and (o.animation_data.action or o.animation_data.nla_tracks) for o in life.sources(job.snapshot.asset)):
        job.omitted('CS2 animated ModelDoc conversion is not implemented; this conversion contains the evaluated static pose only')
    if state.collision_mode!='NONE':job.omitted('CS2 collision reconstruction needs ModelDoc setup; this conversion contains render geometry only')
    game=Path(job.target.get('game_dir','')).resolve()
    if not (game/'gameinfo.gi').is_file():raise ValueError('Select the CS2 game/csgo directory')
    if job.publish and (not job.addon or not all(c.isascii() and (c.isalnum() or c=='_') for c in job.addon)):raise ValueError('Set a CS2 Target Addon name, or turn off Deploy to Game')
    root=game.parents[1];name='wavelength_model_build_'+uuid.uuid4().hex
    source=root/'content/csgo_addons'/name;compiled=root/'game/csgo_addons'/name
    if source.exists() or compiled.exists():raise ValueError('Temporary model addon already exists')
    source.mkdir(parents=True);job.external=[source,compiled];job.source2_dirs=(source,compiled)
    remaps=[];materials={};proxies={};meshes=[]
    with job.snapshot.activate() as context:
        from .export_scope import Scope
        scope=Scope(context.scene,context.view_layer)
        depsgraph=context.evaluated_depsgraph_get()
        for obj in list(life.sources(job.snapshot.asset)):
            if obj.type!='MESH' or obj.get('wl_model_collision_only') or not scope.includes(obj):continue
            mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
            matrix=Matrix.Scale(1/.0254,4)@obj.matrix_world;mesh.transform(matrix)
            if matrix.determinant()<0:mesh.flip_normals()
            for index,material in enumerate(mesh.materials):
                if not material:continue
                if material not in materials:
                    relative=_source2_material(job,material,len(materials),source);materials[material]=relative
                    # FBX texture filenames and Blender's .001 suffixes are not
                    # engine material paths. Use a clean reference-only proxy.
                    proxy=bpy.data.materials.new(relative);proxies[material]=proxy;remaps.append((proxy.name,relative))
                mesh.materials[index]=proxies[material]
            clone=bpy.data.objects.new(obj.name+' static',mesh);context.scene.collection.objects.link(clone);meshes.append(clone)
        if not meshes:raise ValueError('The model has no render meshes')
        # Only evaluated render meshes enter the FBX; authoring controls stay in
        # the editable package but cannot become accidental model geometry.
        for obj in context.scene.objects:obj.select_set(False)
        for obj in meshes:obj.select_set(True)
        context.view_layer.objects.active=meshes[0]
        model=Path('models/wavelength')/job.original['wl_model_id']/(job.model_name+'.fbx');(source/model).parent.mkdir(parents=True,exist_ok=True)
        result=bpy.ops.export_scene.fbx(filepath=str(source/model),use_selection=True,object_types={'MESH'},use_mesh_modifiers=False,bake_anim=False,
            axis_forward='Y',axis_up='Z',apply_unit_scale=False,global_scale=.01,path_mode='RELATIVE',embed_textures=False,use_triangles=True)
        if result!={'FINISHED'}:raise ValueError('FBX model export did not finish')
        primary=model.with_suffix('.vmdl');(source/primary).write_text(mesh_assets.modeldoc(model.as_posix(),remaps))
    compiler=Path(job.target['compiler_dir'])/'resourcecompiler.exe'
    if not compiler.is_file():raise ValueError('Configure the CS2 ResourceCompiler directory')
    job.commands=[[str(compiler),'-i',str(source/primary),'-game',str(game),'-addon',name,'-nop4','-f','-unbufferedio','-noassert']]
    job.primary='content/'+primary.as_posix()
    for path in source.rglob('*'):
        if path.is_file():job.files['content/'+path.relative_to(source).as_posix()]=path.read_bytes()
    job.report['target_unit_meters']=.0254;job.report['collision']='manual' if state.collision_mode!='NONE' else 'none'
    job.report['materials']=[{'source':m.name,'target':path} for m,path in materials.items()]


def prepare(context,asset,work,target_profile,output,*,publish=True,package=False,allow_lossy=False,game='',compiler='',addon='',model_name='model'):
    life.ensure(context,asset)
    if not game and target_profile==asset['wl_model_profile']:game=asset.get('wl_model_game','')
    values=target_settings(context,target_profile,game,compiler)
    return Job(context,asset,work,target_profile,values,output,publish,package,allow_lossy,addon,model_name)


def export_package(context,asset,path):
    import tempfile
    life.ensure(context,asset)
    with tempfile.TemporaryDirectory(prefix='wavelength-model-package-') as work:
        job=Job.__new__(Job);job.work=Path(work);job.original=asset;job.files={}
        job.report={'schema':1,'asset_id':asset['wl_model_id'],'target_profile':asset['wl_model_profile'],'warnings':[]}
        target=target_settings(context,asset['wl_model_profile'],asset.get('wl_model_game',''))
        job.snapshot=Snapshot(context,asset,work,target)
        try:job._capture_editable();return job.write_package(path)
        finally:job.snapshot.close()


model_pipeline.register_route('source','source',source1)
model_pipeline.register_route('source','godot',godot)
model_pipeline.register_route('source','source2',source2)
