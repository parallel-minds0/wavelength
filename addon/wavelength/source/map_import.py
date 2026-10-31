"""Cancelable UI import: isolated parsing, validated records, staged scene batches."""
import json,os,subprocess,tempfile,time
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from . import formats,scene,profiles,worker_status

_active=set()
STAGES={'READING':'Reading file','PARSING':'Parsing map','VALIDATING':'Validating brushes',
        'BRUSHES':'Building brushes','ENTITIES':'Placing entities','COMMIT':'Finalizing scene',
        'RENDER_PRELOAD':'Preloading map assets','RENDER_PACK':'Preparing shared asset library','RENDER_BIND':'Binding preloaded assets'}


def progress(scene):
    return next((session for session in _active if session.scene==scene and not session.closed),None)


def draw_progress(layout,scene,compact=False):
    job=progress(scene)
    importing=job is not None
    if job is None:
        from . import render_support
        job=render_support.progress(scene)
    if job is None:return
    title=f'Loading {job.path.name}'
    if not compact:layout.label(text=title,icon='IMPORT')
    stage=STAGES.get(job.stage,job.stage.title())
    count=f'{job.phase_done:,} / {job.phase_total:,}' if job.phase_total is not None else 'Please wait'
    factor=job.phase_done/max(1,job.phase_total) if job.phase_total is not None else 0.0
    if compact:
        row=layout.row(align=True);row.ui_units_x=26
        row.progress(factor=factor,type='BAR',text=f'{title} · {stage}')
        row.popover(panel='WL_PT_map_import_progress',text='',icon='INFO')
    else:
        layout.label(text=stage,icon='TIME')
        layout.progress(factor=factor,type='BAR',text=count)
        elapsed=int(time.monotonic()-job.started)
        layout.label(text=f'Elapsed: {elapsed//60}:{elapsed%60:02d}')
        if importing:layout.operator('wavelength.cancel_map_import',text='Cancel Import',icon='CANCEL')


def draw_header(self,context):
    draw_progress(self.layout,context.scene,compact=True)


def redraw(scene):
    for window in bpy.context.window_manager.windows:
        if window.scene!=scene:continue
        for area in window.screen.areas:
            if area.type=='VIEW_3D':
                for region in area.regions:
                    if region.type in {'HEADER','UI'}:region.tag_redraw()
            elif area.type=='PROPERTIES':area.tag_redraw()


class WL_PT_map_import_progress(bpy.types.Panel):
    bl_label='Map Loading';bl_space_type='VIEW_3D';bl_region_type='HEADER';bl_ui_units_x=26
    @classmethod
    def poll(cls,context):
        from . import render_support
        return progress(context.scene) is not None or render_support.progress(context.scene) is not None
    def draw(self,context):draw_progress(self.layout,context.scene)


class WL_OT_cancel_map_import(bpy.types.Operator):
    bl_idname='wavelength.cancel_map_import';bl_label='Cancel Map Import'
    def execute(self,context):
        job=progress(context.scene)
        if job:job.close();context.scene.wavelength.status='Map import canceled'
        return {'FINISHED'}


class Session:
    def __init__(self,context,path):
        self.scene=context.scene;self.path=Path(path);self.iterator=None;self.stream=None;self.done=False;self.closed=False
        self.count=0;self.worst_slice=0.;self.slice_times=[]
        self.started=time.monotonic();self.stage='READING';self.phase_done=0;self.phase_total=None;self._last_progress=0
        self.brush_count=0;self.entity_count=0
        if any(o.get('wl_role') for o in self.scene.objects):raise ValueError('Import into an empty wavelength scene')
        self.directory=tempfile.TemporaryDirectory(prefix='wavelength-map-import-');self.folder=Path(self.directory.name)
        (self.folder/'request.json').write_text(json.dumps(dict(path=str(self.path))),encoding='utf-8')
        self.log=(self.folder/'worker.log').open('wb')
        self.process=subprocess.Popen([bpy.app.binary_path,'--background','--factory-startup','--python',str(Path(__file__).with_name('map_import_worker.py')),'--',str(self.folder)],
            stdout=self.log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.scene['wl_importing']=True
        self.scene.wavelength.status='Parsing map in background; Esc cancels'
        _active.add(self)
        redraw(self.scene)

    def update_progress(self,stage,done=0,total=None):
        changed=stage!=self.stage
        self.stage=stage;self.phase_done=done;self.phase_total=total
        now=time.monotonic()
        if changed or now-self._last_progress>=.1:
            count=f' {done:,}/{total:,}' if total is not None else ''
            self.scene.wavelength.status=f'Loading {self.path.name}: {STAGES.get(stage,stage.title())}{count}'
            self._last_progress=now;redraw(self.scene)

    def records(self,document):
        for line in self.stream:
            index,faces,vertices,polygons=json.loads(line)
            yield document.entities[index],[formats.Face(**face) for face in faces],vertices,polygons

    def advance(self):
        if self.closed:raise ValueError('Map import canceled')
        if self.iterator is None:
            state=worker_status.latest(self.folder/'status.jsonl')
            if state is None:
                if self.process.poll() is not None:raise ValueError('Map preparation worker failed: '+(self.folder/'worker.log').read_text(errors='replace')[-2000:])
                return False
            if state['state']=='ERROR':raise ValueError(state['message'])
            if state['state']!='READY':
                if self.process.poll() is not None:raise ValueError('Map preparation worker stopped: '+(self.folder/'worker.log').read_text(errors='replace')[-2000:])
                self.update_progress(state['state'],state.get('done',0),state.get('total'));return False
            metadata=json.loads((self.folder/'metadata.json').read_text(encoding='utf-8'))
            document=formats.Map([formats.Entity(e['pairs'],[None]*e['brushes'],vmf_hidden=e['hidden']) for e in metadata['entities']])
            settings=self.scene.wavelength
            if self.path.suffix.lower()=='.vmf':
                if not profiles.is_source(settings.engine):settings.engine='source_hl2_windows' if os.name=='nt' else 'source_hl2_linux'
            elif metadata['valve_axes']:settings.engine='goldsrc'
            self.brush_total=metadata['brush_count']
            self.entity_total=sum(not e['brushes'] and dict(e['pairs']).get('classname')!='worldspawn' for e in metadata['entities'])
            self.total=self.brush_total+self.entity_total
            self.stream=(self.folder/'brushes.jsonl').open(encoding='utf-8')
            self.iterator=scene.import_map_iter(self.scene,document,defer_assets=True,prepared=self.records(document))
        start=time.monotonic()
        while time.monotonic()-start<.012:
            try:
                kind,_obj=next(self.iterator)
                if kind=='BRUSH':
                    self.brush_count+=1;self.count+=1;self.update_progress('BRUSHES',self.brush_count,self.brush_total)
                elif kind=='ENTITY':
                    self.entity_count+=1;self.count+=1;self.update_progress('ENTITIES',self.entity_count,self.entity_total)
                else:self.update_progress('COMMIT')
            except StopIteration:
                self.done=True;self.scene.wavelength.map_path=str(self.path)
                self.scene.wavelength.status=f'Map imported: {self.count} objects; comments/formatting are normalized on export'
                break
        duration=time.monotonic()-start;self.slice_times.append(duration);self.worst_slice=max(self.worst_slice,duration)
        return self.done

    def close(self):
        # Closing the generator rolls back its entire staged collection on cancel.
        if self.closed:return
        self.closed=True;_active.discard(self)
        if self.iterator is not None and not self.done:self.iterator.close()
        if self.stream:self.stream.close()
        if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=5)
        self.log.close();self.directory.cleanup()
        try:self.scene.pop('wl_importing',None)
        except ReferenceError:pass
        if self.done:
            from . import render_support
            render_support.prepare(self.scene)
        redraw(self.scene)


@persistent
def cancel_all(*args):
    for session in tuple(_active):session.close()


@persistent
def loaded(*args):
    for item in bpy.data.scenes:item.pop('wl_importing',None)


def register():
    for cls in (WL_PT_map_import_progress,WL_OT_cancel_map_import):bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(draw_header)
    if cancel_all not in bpy.app.handlers.load_pre:bpy.app.handlers.load_pre.append(cancel_all)
    if loaded not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(loaded)


def unregister():
    cancel_all()
    if cancel_all in bpy.app.handlers.load_pre:bpy.app.handlers.load_pre.remove(cancel_all)
    if loaded in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(loaded)
    bpy.types.VIEW3D_HT_header.remove(draw_header)
    for cls in (WL_OT_cancel_map_import,WL_PT_map_import_progress):bpy.utils.unregister_class(cls)
