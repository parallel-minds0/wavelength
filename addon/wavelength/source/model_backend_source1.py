"""Source 1 adapter for the common editable-model contract."""
import json
from pathlib import Path
import bpy
from . import profiles,source_assets,model_pipeline

class Source1:
    id='source1';extensions={'.mdl'}
    def supports(self,engine):return profiles.is_source(engine)
    def model_path(self,asset):return 'models/wavelength/'+asset['wl_custom_model_id']+'/model.mdl'

    def validate_placement(self,context,asset,entity):
        from .entity import source_schema
        classname=dict(json.loads(entity.get('wl_pairs','[]'))).get('classname','')
        if classname=='prop_ragdoll' or not any(p['key']=='model' for p in source_schema.model_fields(context.scene.wavelength,classname,bpy.path.abspath)):
            raise ValueError('Choose a supported model entity, such as prop_static or prop_dynamic')
        if asset.wavelength_model.clips and (classname=='prop_static' or classname.startswith('prop_physics')):raise ValueError('Animated model assets require a dynamic entity')
        from .model_lifecycle import bindings
        placed=bindings(asset)
        def style(obj):
            name=dict(json.loads(obj['wl_pairs'])).get('classname','')
            return 'static' if name=='prop_static' else 'physics' if name.startswith('prop_physics') else 'dynamic'
        if placed and style(placed[0])!=style(entity):raise ValueError('Linked placements must use compatible entity types; make an independent variant')

    def bind_asset(self,context,asset):
        from . import custom_models
        return custom_models.assign(context,asset=asset)

    def editable_materials(self,context,asset):
        from . import model_materials
        warnings=[]
        materials={m for o in asset.objects if o.type=='MESH' for m in o.data.materials if m}
        for material in materials:warnings.extend(model_materials.realize(material,context.scene.wavelength))
        return warnings
    def import_model(self,context,path,skin=0,body=0):
        path=Path(path).resolve();settings=context.scene.wavelength
        game=source_assets.library(bpy.path.abspath(settings.game_dir))
        class Local:
            def read(self,name):return path.with_name(Path(name).name).read_bytes()
            def material(self,name):return game.material(name)
        normalized=path.as_posix();at=normalized.lower().rfind('/models/')
        modelpath=normalized[at+1:] if at>=0 else 'models/'+path.name
        return self._editable(context,modelpath,Local(),skin,body,context.scene.cursor.location)

    def import_reference(self,context,path,skin=0,body=0):
        """Resolve placed models and their companions from mounted game assets."""
        settings=context.scene.wavelength
        reader=source_assets.library(bpy.path.abspath(settings.game_dir))
        return self._editable(context,path,reader,skin,body,(0,0,0),mounted=True)

    def _editable(self,context,modelpath,reader,skin,body,location,mounted=False):
        from . import model_import
        settings=context.scene.wavelength
        cached,data=model_import.mesh(settings,modelpath,skin,body,None if mounted else reader)
        skeleton=None
        if not data['static']:
            from . import studio_animation,studio_model
            skeleton=studio_animation.read(reader.read(modelpath),reader.read)
            # Cached preview records may predate skeletal decode support.
            data=studio_model.load(reader,modelpath,skin,body)
        # Preview meshes are shared caches. Editable imports must own their data.
        mesh=cached.copy();obj=bpy.data.objects.new(Path(modelpath).stem,mesh)
        context.collection.objects.link(obj);obj.location=location
        obj['wl_unit_meters']=profiles.unit_meters(settings)
        warnings=json.loads(mesh.get('wl_model_warnings','[]'))
        objects=[obj]
        if skeleton:
            from . import model_skeleton
            try:rig,clips=model_skeleton.import_skeleton(context,obj,skeleton,data['weights'],profiles.unit_meters(settings))
            except Exception:
                bpy.data.objects.remove(obj,do_unlink=True);raise
            if rig:objects.append(rig)
            warnings.extend(skeleton['warnings'])
        return model_pipeline.ImportedModel(objects,warnings)
    def prepare(self,context,asset,work,*,model_name='model'):
        from . import custom_models,scene
        settings=context.scene.wavelength
        if asset.get('wl_model_game')!=bpy.path.abspath(settings.game_dir):raise ValueError('Activate the model asset’s original game directory before compiling')
        owner=asset.get('wl_model_build_owner')
        if owner is None:
            sources=[o for o in asset.objects if o.type in {'MESH','ARMATURE'} and not o.get('wl_model_collision_only')]
            if not sources:raise ValueError('Model asset has no editable meshes')
            owner=bpy.data.objects.new(asset.name+' Prop',None);context.scene.collection.objects.link(owner)
            origin=asset.wavelength_model.origin
            if origin:owner.matrix_world=origin.matrix_world.copy()
            else:owner.location=sources[0].matrix_world.translation
            owner['wl_role']='ENTITY';owner['wl_id']=scene.uid();owner['wl_owner_profile']=settings.engine
            owner['wl_unit_meters']=profiles.unit_meters(settings)
            state=asset.wavelength_model
            clips=[{key:getattr(clip,key) for key in ('name','start','end','fps','loop','activity')} for clip in state.clips]
            if not clips:clips=[clip for o in sources for clip in json.loads(o.get('wl_model_clips','[]'))]
            if clips and not state.clips:
                for values in clips:
                    clip=state.clips.add()
                    for key,value in values.items():setattr(clip,key,value)
            owner['wl_pairs']=json.dumps([['classname','prop_dynamic' if clips else 'prop_static']])
            previous=list(context.selected_objects);active=context.view_layer.objects.active
            try:
                for o in previous:o.select_set(False)
                for o in sources:o.select_set(True)
                owner.select_set(True);context.view_layer.objects.active=owner
                # This private origin is a known compiler-only prop, not a
                # placed game entity; compiling a model does not need an FGD.
                custom_models.assign(context,asset=asset,validate_schema=False)
                # A published asset is not a placed map prop. This private
                # compile origin stays out of map export until explicit placement.
                owner['wl_exclude']=True
                owner['wl_model_private_origin']=True
                asset['wl_model_build_owner']=owner
            except Exception:
                bpy.data.objects.remove(owner,do_unlink=True);raise
            finally:
                for o in context.selected_objects:o.select_set(False)
                for o in previous:
                    if o.name in context.scene.objects:o.select_set(True)
                context.view_layer.objects.active=active
        # Standalone model compilation deploys to a mounted game directory;
        # the map build still offers BSP packing for this same managed model.
        definition=custom_models.definition(owner);state=definition.wavelength_model
        old=state.deployment;state.deployment='GAME'
        try:build=custom_models.prepare(context.scene,work,entities=[owner],model_name=model_name)
        finally:state.deployment=old
        if build is None:raise ValueError('All model sources are excluded from export; enable them in the Outliner or engine tree')
        return SourceJob(build,definition,old,asset,owner)

class SourceJob:
    def __init__(self,build,definition,deployment,asset,owner):
        self.build=build;self.commands=build.commands;self.definition=definition
        self.deployment=deployment;self.asset=asset;self.owner=owner
    def finish(self):
        state=self.definition.wavelength_model;old=state.deployment;state.deployment='GAME'
        try:self.build.validated();self.build.deploy()
        finally:state.deployment=old
        self.asset['wl_model_output']=dict(json.loads(self.owner['wl_pairs']))['model']
        from . import model_browser
        model_browser.published(bpy.context,self.asset['wl_model_output'])
        return self.asset['wl_model_output']
