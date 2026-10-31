"""An isolated render-asset transaction; only the completed bundle reaches the map."""
import json,os,subprocess,tempfile,time
from pathlib import Path
import bpy
from . import runtime_cache,profiles,worker_status

_loaded={}


def load_library(path,material_names,mesh_names):
    """One local ID dependency closure, with no per-asset link/copy cycles."""
    with bpy.data.libraries.load(str(path),link=False) as (source,target):
        target.materials=list(material_names);target.meshes=list(mesh_names)
    return ({name:mat for name,mat in zip(material_names,target.materials) if mat},
            {name:mesh for name,mesh in zip(mesh_names,target.meshes) if mesh})


class Request:
    def __init__(self,scene):
        self.scene=scene;self.process=None;self.log=None;self.directory=None
        self.materials={m for o in scene.objects if o.type=='MESH' for m in o.data.materials if m and m.get('wl_source_native_material')}
        self.references=[o for o in scene.objects if o.get('wl_source_native_model')]
        self.models={}
        self.keys={}
        for obj in self.references:
            model=[obj['wl_source_native_model'],obj.get('wl_source_skin',0),obj.get('wl_source_body',0)]
            key=runtime_cache.key([model,obj.get('wl_source_revision','')]);self.models[key]=model;self.keys[obj.as_pointer()]=key
        settings=scene.wavelength
        config=dict(engine=settings.engine,game_dir=bpy.path.abspath(settings.game_dir),unit_scale=profiles.unit_meters(settings))
        self.identity=runtime_cache.key(['render-preload-3',config,sorted((m['wl_source_native_material'],m.get('wl_source_cache_key','')) for m in self.materials),self.models])
        root=runtime_cache.root().parent/'render-bundles';root.mkdir(parents=True,exist_ok=True)
        self.bundle=root/(self.identity+'.json')
        self.ready=self.bundle.is_file() and self.bundle.with_suffix('.blend').is_file()
        self._libraries=None;self._materials={};self._meshes={};self._images={}
        self.load_slice_times=[];self.library_loads=0;self.published=False
        self.started=time.monotonic();self.stage='RENDER_PRELOAD';self.phase_done=0;self.phase_total=len(self.materials)+len(self.models)
        self.path=Path(scene.wavelength.map_path or (scene.wavelength.map_name+'.vmf'))
        self._last_redraw=0
        if not self.ready:
            self.directory=tempfile.TemporaryDirectory(prefix='wavelength-render-');self.folder=Path(self.directory.name)
            request=dict(settings=config,materials=sorted({m['wl_source_native_material'] for m in self.materials}),models=self.models,bundle=str(self.bundle),parent_pid=os.getpid())
            (self.folder/'request.json').write_text(json.dumps(request),encoding='utf-8')
            self.log=(self.folder/'worker.log').open('wb')
            self.process=subprocess.Popen([bpy.app.binary_path,'--background','--factory-startup','--python',str(Path(__file__).with_name('render_bundle_worker.py')),'--',str(self.folder)],stdout=self.log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def poll(self):
        if self.ready:return True
        status=worker_status.latest(self.folder/'status.jsonl')
        if status is None:
            if self.process.poll() is not None:raise ValueError('Render preparation worker failed; see '+str(self.folder/'worker.log'))
            return False
        if status['state']=='ERROR':raise ValueError(status['message'])
        self.stage='RENDER_PACK' if status['state']=='PACKING' else 'RENDER_PRELOAD'
        self.phase_done=status.get('done',0);self.phase_total=status.get('total',self.phase_total)
        self.ready=status['state']=='READY'
        if time.monotonic()-self._last_redraw>=.1:
            from .map_import import redraw
            redraw(self.scene);self._last_redraw=time.monotonic()
        if not self.ready and self.process.poll() is not None:raise ValueError('Render preparation worker stopped before completing the preload')
        return self.ready

    def load_all(self,manifest):
        cached=_loaded.get(self.identity)
        try:
            if cached and (any(m.name not in bpy.data.materials for m in cached[0].values()) or any(m.name not in bpy.data.meshes for m in cached[1].values())):cached=None
        except ReferenceError:cached=None
        if cached is None:
            names=list(manifest['materials']);mesh_names=list(dict.fromkeys(manifest['models'].values()))
            started=time.monotonic()
            materials,mesh_by_name=load_library(manifest['library'],names,mesh_names)
            self.library_loads+=1;self.load_slice_times.append(time.monotonic()-started)
            cached=(materials,{key:mesh_by_name[name] for key,name in manifest['models'].items() if name in mesh_by_name})
            _loaded[self.identity]=cached
        return cached

    def publish(self):
        """Append once, stage prop instances, then commit all bindings together."""
        if self.published:return
        self.stage='RENDER_BIND'
        from .map_import import redraw
        redraw(self.scene)
        started=time.monotonic();self.timings={}
        manifest=json.loads(self.bundle.read_text(encoding='utf-8'))
        cached=self.load_all(manifest)
        materials,meshes=cached
        self.timings['library_ms']=round((time.monotonic()-started)*1000,2);started=time.monotonic()
        replaced=[];renames=[]
        replacements={}
        for old in self.materials:
            name=manifest['requests'].get(old['wl_source_native_material']);new=materials.get(name)
            if new is not None and old!=new:
                renames.append((new,old.name));replacements[old]=new
        # user_remap walks all of Main for EACH material. Instead visit each
        # material slot once: linear in the map size rather than materials*IDs.
        for mesh in bpy.data.meshes:
            for index,mat in enumerate(mesh.materials):
                if mat in replacements:mesh.materials[index]=replacements[mat]
        for obj in bpy.data.objects:
            if obj.type=='MESH':
                for slot in obj.material_slots:
                    if slot.link=='OBJECT' and slot.material in replacements:slot.material=replacements[slot.material]
        replaced=[old for old in replacements if old.users==0]
        if replaced:bpy.data.batch_remove(replaced)
        for new,name in renames:new.name=name
        self.timings['materials_ms']=round((time.monotonic()-started)*1000,2);started=time.monotonic()
        staging=bpy.data.collections.new('Source Render References');hidden=[];removed=[]
        from .scene import uid
        # Query view-layer visibility before altering collections. hide_get()
        # otherwise forces a full view-layer resync after every object link.
        hidden_sources={old.as_pointer() for old in self.references if old.hide_get() or (old.parent and old.parent.hide_get())}
        for old in self.references:
            try:
                mesh=meshes.get(self.keys[old.as_pointer()])
                if mesh is None:
                    old['wl_asset_error']='Render asset unavailable; see render preparation status';continue
                ref=bpy.data.objects.new(old.name,mesh);staging.objects.link(ref)
                ref.parent=old.parent;ref.matrix_parent_inverse=old.matrix_parent_inverse.copy();ref.matrix_basis=old.matrix_basis.copy()
                ref['wl_model_reference']=True;ref['wl_exclude']=True;ref['wl_role']='MODEL_REFERENCE';ref['wl_source_model']=old['wl_source_native_model']
                ref['wl_id']=uid()
                ref.hide_render=old.hide_render
                if old.as_pointer() in hidden_sources:hidden.append(ref)
                removed.append(old)
            except ReferenceError:continue
        self.scene.collection.children.link(staging)
        if removed:bpy.data.batch_remove(removed)
        for ref in hidden:ref.hide_set(True)
        errors=manifest.get('errors',[])
        self.scene.wavelength.status='Render assets ready'+(f'; {len(errors)} unavailable' if errors else '')
        if errors:self.scene['wl_render_asset_errors']=json.dumps(errors)
        self.scene['wl_source_blender_rendering']=True
        self.timings['models_ms']=round((time.monotonic()-started)*1000,2)
        self.published=True
        self.timings['library_loads']=self.library_loads
        self.timings['largest_library_slice_ms']=round(max(self.load_slice_times,default=0)*1000,2)
        from . import diagnostics
        diagnostics.logger.info('Source render bundle publication timings: %s',self.timings)

    def close(self):
        if self.process and self.process.poll() is None:self.process.terminate();self.process.wait(timeout=5)
        if self.log:self.log.close()
        if self.directory:self.directory.cleanup()


def clear():
    _loaded.clear()
