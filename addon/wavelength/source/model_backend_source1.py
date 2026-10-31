"""Source 1 adapter for the common editable-model contract."""
import json
from pathlib import Path
import bpy
from . import profiles,source_assets,model_pipeline

class Source1:
    id='source1';extensions={'.mdl'}
    def supports(self,engine):return profiles.is_source(engine)
    def import_model(self,context,path,skin=0,body=0):
        from . import model_import
        path=Path(path).resolve();settings=context.scene.wavelength
        game=source_assets.library(bpy.path.abspath(settings.game_dir))
        class Local:
            def read(self,name):return path.with_name(Path(name).name).read_bytes()
            def material(self,name):return game.material(name)
        normalized=path.as_posix();at=normalized.lower().rfind('/models/')
        modelpath=normalized[at+1:] if at>=0 else 'models/'+path.name
        reader=Local()
        cached,data=model_import.mesh(settings,modelpath,skin,body,reader)
        skeleton=None
        if not data['static']:
            from . import studio_animation,studio_model
            skeleton=studio_animation.read(path.read_bytes(),reader.read)
            # Cached preview records may predate skeletal decode support.
            data=studio_model.load(reader,modelpath,skin,body)
        # Preview meshes are shared caches. Editable imports must own their data.
        mesh=cached.copy();obj=bpy.data.objects.new(path.stem,mesh)
        context.collection.objects.link(obj);obj.location=context.scene.cursor.location
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
    def prepare(self,context,asset,work):
        from . import custom_models,scene
        settings=context.scene.wavelength
        if asset.get('wl_model_game')!=bpy.path.abspath(settings.game_dir):raise ValueError('Activate the model asset’s original game directory before compiling')
        owner=asset.get('wl_model_build_owner')
        if owner is None:
            sources=[o for o in asset.objects if o.type in {'MESH','ARMATURE'}]
            if not sources:raise ValueError('Model asset has no editable meshes')
            owner=bpy.data.objects.new(asset.name+' Prop',None);context.collection.objects.link(owner)
            owner.location=sources[0].matrix_world.translation
            owner['wl_role']='ENTITY';owner['wl_id']=scene.uid();owner['wl_owner_profile']=settings.engine
            owner['wl_unit_meters']=profiles.unit_meters(settings)
            clips=[clip for o in sources for clip in json.loads(o.get('wl_model_clips','[]'))]
            owner['wl_pairs']=json.dumps([['classname','prop_dynamic' if clips else 'prop_static']])
            previous=list(context.selected_objects);active=context.view_layer.objects.active
            try:
                for o in previous:o.select_set(False)
                for o in sources:o.select_set(True)
                owner.select_set(True);context.view_layer.objects.active=owner
                custom_models.assign(context)
                if clips:
                    state=custom_models.definition(owner).wavelength_model;state.clips.clear()
                    for values in clips:
                        clip=state.clips.add()
                        for key,value in values.items():setattr(clip,key,value)
                # A published asset is not a placed map prop. This private
                # compile origin stays out of map export until explicit placement.
                owner['wl_exclude']=True
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
        try:build=custom_models.prepare(context.scene,work,entities=[owner])
        finally:state.deployment=old
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
