"""Native Asset Browser publishers using existing WAD/VPK/FGD backends."""
import json
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from . import asset_index,profiles,textures,workspace,scene,diagnostics

COLLECTION='_WL_ASSET_TEMPLATES'
TEXTURES_CATALOG_ID='a1e2f3c4-1111-4000-8000-000000000001'
ENTITIES_CATALOG_ID='7d3c0fd7-53ef-4b20-9c3b-b6e2f8a7a119'
_BUSY=False
_AUTO_QUEUE=[]
_AUTO_TOTAL=0
_AUTO_PUBLISHED=0
_LAST_TEX_SIG=None
_LAST_ENT_SIG=None
_BRUSH_MAT_SIGS={}


def collection(context):
    scn=getattr(context,'scene',None) or getattr(bpy.context,'scene',None)
    c=bpy.data.collections.get(COLLECTION)
    if c is None:
        c=bpy.data.collections.new(COLLECTION)
        if scn:scn.collection.children.link(c)
    c.hide_render=True;c.hide_viewport=True
    return c


def catalog_id_for(category):
    return TEXTURES_CATALOG_ID if category in {'MATERIAL','DECAL','SKY'} else ENTITIES_CATALOG_ID


def ensure_catalog_file(settings):
    """Write blender_assets.cats.txt when a project directory or saved .blend exists."""
    target_dir=None
    if bpy.data.filepath:
        target_dir=Path(bpy.data.filepath).resolve().parent
    elif getattr(settings,'project_dir',''):
        try:
            p=Path(bpy.path.abspath(settings.project_dir)).resolve()
            if p.is_dir():target_dir=p
        except Exception:
            target_dir=None
    if not target_dir or not target_dir.is_dir():
        return
    cats_file=target_dir/'blender_assets.cats.txt'
    tex_line=f'{TEXTURES_CATALOG_ID}:Wavelength/Textures:Wavelength-Textures'
    ent_line=f'{ENTITIES_CATALOG_ID}:Wavelength/Entities:Wavelength-Entities'
    try:
        if cats_file.is_file():
            existing=cats_file.read_text(errors='replace')
            lines=existing.splitlines()
            changed=False
            if TEXTURES_CATALOG_ID not in existing:
                lines.append(tex_line);changed=True
            if ENTITIES_CATALOG_ID not in existing:
                lines.append(ent_line);changed=True
            if changed:
                cats_file.write_text('\n'.join(lines)+'\n')
        else:
            cats_file.write_text(f'VERSION 1\n\n{tex_line}\n{ent_line}\n')
    except OSError:
        pass


def metadata(block,row):
    block['wl_asset']=json.dumps(row);block['wl_asset_id']=row['id']
    block['wl_asset_profile']=row['engine'];block['wl_asset_category']=row['category']
    block.asset_mark();block.asset_data.description=f"{row['category']} · {row['engine']} · {row['path']}\n{row['validation']}"
    block.asset_data.author='Wavelength local game index'
    cat_id=catalog_id_for(row['category'])
    try:block.asset_data.catalog_id=cat_id
    except Exception:pass
    section_tag='Textures' if row['category'] in {'MATERIAL','DECAL','SKY'} else 'Entities'
    for tag in ('Wavelength',section_tag,row['category'],row['engine']):
        if tag not in block.asset_data.tags:block.asset_data.tags.new(tag)


def preview(block):
    # Use actual decoded texture pixels, not a separate custom gallery widget.
    if isinstance(block,bpy.types.Material) and block.use_nodes:
        image=next((n.image for n in block.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
        if image and image.size[0] and image.size[1]:
            image_pixels=list(image.pixels);w,h=image.size;size=64;pixels=[]
            for y in range(size):
                for x in range(size):
                    i=4*(min(h-1,y*h//size)*w+min(w-1,x*w//size));pixels.extend(image_pixels[i:i+4])
            p=block.preview_ensure();p.image_size=(size,size);p.image_pixels_float=pixels
            block['wl_preview_ready']=True
            return
    # Deterministic icon for metadata/proxy assets, saved into the .blend.
    import hashlib
    key=str(block.get('wl_asset_id',block.name));seed=hashlib.sha256(key.encode()).digest()
    color=tuple(.3+v/510 for v in seed[:3]);pixels=[];size=64
    for y in range(size):
        for x in range(size):
            border=(12<=x<=51 and 12<=y<=51 and (x<16 or x>47 or y<16 or y>47))
            cross=(abs(x-32)<2 and 22<y<42) or (abs(y-32)<2 and 22<x<42)
            pixels.extend((*color,1.) if border or cross else (.08,.08,.08,1.))
    p=block.preview_ensure();p.image_size=(size,size);p.image_pixels_float=pixels
    block['wl_preview_ready']=True


def publish_material_fast(settings,name,existing_by_id=None):
    """Create or reuse a Current File Material asset with a fast 64x64 preview.

    Full-resolution shader nodes are realized on demand when the material is
    applied or dragged onto a brush, keeping profile texture loading instant.
    """
    row=asset_index.record(settings.engine,name,'MATERIAL',source=settings.wad_path or settings.game_dir)
    existing=(existing_by_id or {}).get(row['id'])
    if existing is None:
        existing=next((m for m in bpy.data.materials if m.get('wl_asset_id')==row['id'] or (m.get('wl_asset_profile')==settings.engine and str(m.get('wl_texture','')).casefold()==name.casefold())),None)
    if existing is not None:
        if existing.asset_data is None:
            saved_row=json.loads(existing['wl_asset']) if existing.get('wl_asset') else row
            metadata(existing,saved_row)
        else:
            try:existing.asset_data.catalog_id=TEXTURES_CATALOG_ID
            except Exception:pass
        if existing.get('wl_preview_ready') and existing.preview and existing.preview.image_size[0]>0:
            return existing
    if profiles.is_source(settings.engine):
        from . import source_assets
        assets=source_assets.library(bpy.path.abspath(settings.game_dir))
        norm=source_assets.asset_path(name)
        if norm.startswith('materials/'):norm=norm[10:]
        if norm.endswith('.vmt'):norm=norm[:-4]
        props=assets.material(norm)
        base=props.get('$basetexture') or props.get('%tooltexture')
        if not base:raise ValueError('Material has no supported base/tool texture: '+name)
        base_path=source_assets.asset_path(base)
        if not base_path.startswith('materials/'):base_path='materials/'+base_path
        if not base_path.endswith('.vtf'):base_path+='.vtf'
        width,height,pw,ph,rgba=source_assets.decode_vtf(assets.read(base_path),max_dimension=64)
        pixels=[v/255.0 for v in rgba]
        row['source']=settings.game_dir
        row['validation']='decoded'
        row['dependencies']=[v for k,v in props.items() if k in {'$basetexture','$bumpmap','$detail','$envmapmask','%tooltexture'} and isinstance(v,str)]
        mat=existing or bpy.data.materials.new(norm);mat.use_nodes=True;mat.name=norm
        mat['wl_texture']=norm;mat['wl_width']=width;mat['wl_height']=height
        mat['wl_asset_profile']=settings.engine
        if 'wl_realized' not in mat:mat['wl_realized']=False
        mat['wl_asset_origin']='User-installed Source game; private preview'
    else:
        wad,item=textures.find(settings,name)
        pal=textures.palette(settings) if not item.wad3 else None
        pw,ph,pixels=item.rgba(pal,64)
        row['source']=str(wad.path)
        row['validation']='decoded'
        row['dependencies']=[str(wad.path)]
        mat=existing or bpy.data.materials.new(item.name);mat.use_nodes=True;mat.name=item.name
        mat['wl_texture']=item.name;mat['wl_wad']=str(wad.path);mat['wl_width']=item.width;mat['wl_height']=item.height
        mat['wl_asset_profile']=settings.engine
        if 'wl_realized' not in mat:mat['wl_realized']=False
        mat['wl_asset_origin']='User-installed game/WAD; local use, not bundled'
    metadata(mat,row)
    p=mat.preview_ensure();p.image_size=(pw,ph);p.image_pixels_float=pixels
    mat['wl_preview_ready']=True
    if existing_by_id is not None:
        existing_by_id[row['id']]=mat
    return mat


def publish_material(context,name):
    s=context.scene.wavelength
    mat=publish_material_fast(s,name)
    textures.realize_material(s,mat)
    if mat.get('wl_asset'):
        row=json.loads(mat['wl_asset'])
        deps=[n.image.filepath for n in (mat.node_tree.nodes if mat.use_nodes else []) if n.type=='TEX_IMAGE' and n.image and n.image.filepath]
        if deps and not profiles.is_source(s.engine):
            row['dependencies']=deps
            mat['wl_asset']=json.dumps(row)
    return mat


def publish_proxy(context,row):
    old=next((o for o in bpy.data.objects if o.get('wl_asset_id')==row['id'] and o.get('wl_asset_template')),None)
    if old:
        if old.asset_data is None:metadata(old,row)
        return old
    s=context.scene.wavelength
    obj=bpy.data.objects.new(Path(row['path']).name,None);collection(context).objects.link(obj)
    obj.empty_display_type='CUBE' if row['category']=='MODEL' else 'ARROWS'
    obj.empty_display_size=profiles.engine_to_world(s,16)
    row=dict(row)
    if row['category']=='MODEL' and row['path'].lower().endswith('.mdl'):
        try:
            if profiles.is_source(s.engine):
                from .source_assets import library
                data=library(s.game_dir).read(row['path'])
            else:data=(Path(row['source'])/row['path']).read_bytes()
            lo,hi=asset_index.model_bounds(data);row['bounds']=[lo,hi]
            obj.empty_display_size=1.;obj.scale=[(b-a)*profiles.unit_meters(s)/2 for a,b in zip(lo,hi)]
            row['validation']='Header bounds verified; geometry preview is a placement proxy'
        except (OSError,ValueError) as exc:row['validation']=str(exc)
    obj['wl_asset_template']=True;obj['wl_exclude']=True;metadata(obj,row);preview(obj)
    return obj


def _tag_asset_browsers_redraw(section=None):
    try:
        from .entity import browser as entity_browser
        wm=getattr(bpy.context,'window_manager',None)
        if not wm:return
        for window in wm.windows:
            if not window.screen:continue
            for area in window.screen.areas:
                if area.type=='FILE_BROWSER' and area.ui_type=='ASSETS':
                    if section:
                        entity_browser._configure_asset_area(area,section=section)
                    else:
                        area.tag_redraw()
    except Exception:
        pass


def _publish_batch(settings,limit,existing_by_id=None):
    global _AUTO_PUBLISHED
    if existing_by_id is None:
        existing_by_id={m.get('wl_asset_id'):m for m in bpy.data.materials if m.get('wl_asset_profile')==settings.engine and m.get('wl_asset_id')}
    processed=0
    while _AUTO_QUEUE and processed<limit:
        name=_AUTO_QUEUE.pop(0)
        try:
            publish_material_fast(settings,name,existing_by_id=existing_by_id)
            _AUTO_PUBLISHED+=1
        except (ValueError,OSError,RuntimeError,UnicodeError):
            pass
        processed+=1
    return processed


def _auto_publish_tick():
    try:
        scn=getattr(bpy.context,'scene',None)
        if scn is None or not hasattr(scn,'wavelength'):
            return None
        s=scn.wavelength
        if s.engine=='blender' or not _AUTO_QUEUE:
            _tag_asset_browsers_redraw()
            return None
        batch=24 if profiles.is_source(s.engine) else 64
        _publish_batch(s,batch)
        _tag_asset_browsers_redraw()
        return 0.02 if _AUTO_QUEUE else None
    except Exception:
        return None


def flush_auto_publish(settings=None,max_items=None):
    """Synchronously publish remaining queued profile textures (or up to max_items)."""
    scn=getattr(bpy.context,'scene',None)
    s=settings or (scn.wavelength if scn and hasattr(scn,'wavelength') else None)
    if s is None or s.engine=='blender' or not _AUTO_QUEUE:
        return 0
    limit=len(_AUTO_QUEUE) if max_items is None else max_items
    count=_publish_batch(s,limit)
    _tag_asset_browsers_redraw()
    return count


def sync_status(settings=None):
    """Return (published_count, total_count, is_loading) for active profile textures."""
    scn=getattr(bpy.context,'scene',None)
    s=settings or (scn.wavelength if scn and hasattr(scn,'wavelength') else None)
    if s is None or s.engine=='blender':
        return 0,0,False
    total=_AUTO_TOTAL or s.texture_count
    published=min(total,_AUTO_PUBLISHED) if total else _AUTO_PUBLISHED
    return published,total,bool(_AUTO_QUEUE)


def schedule_profile_sync(context=None,settings=None,force=False):
    """Automatically sync Asset Browser textures and entities for the active profile."""
    global _AUTO_QUEUE,_AUTO_TOTAL,_AUTO_PUBLISHED,_LAST_TEX_SIG,_LAST_ENT_SIG
    scn=getattr(context,'scene',None) if context else None
    if scn is None:
        scn=getattr(bpy.context,'scene',None)
    s=settings or (scn.wavelength if scn and hasattr(scn,'wavelength') else None)
    if s is None:
        return
    if s.engine=='blender':
        _AUTO_QUEUE=[];_AUTO_TOTAL=0;_AUTO_PUBLISHED=0;_LAST_TEX_SIG=None;_LAST_ENT_SIG=None
        for m in bpy.data.materials:
            if (m.get('wl_asset_id') or m.get('wl_asset_profile')) and m.asset_data is not None:
                try:m.asset_clear()
                except Exception:pass
        for o in bpy.data.objects:
            if (o.get('wl_asset_id') or o.get('wl_entity_browser_template')) and o.asset_data is not None:
                try:o.asset_clear()
                except Exception:pass
        _tag_asset_browsers_redraw()
        return

    ensure_catalog_file(s)
    from .entity import browser as entity_browser
    ent_sig=(s.engine,str(s.fgd_path or ''))
    has_entities=any(o.get('wl_entity_browser_profile')==s.engine and o.asset_data is not None for o in bpy.data.objects)
    if force or _LAST_ENT_SIG!=ent_sig or not has_entities:
        try:
            entity_browser.rebuild_for_scene(scn,context,quiet=True)
            _LAST_ENT_SIG=ent_sig
        except Exception:
            pass

    try:
        valid_wads={str(Path(bpy.path.abspath(p)).resolve()) for p in textures.sources(s) if p} if not profiles.is_source(s.engine) else set()
    except Exception:
        valid_wads=set()

    tex_sig=(s.engine,str(s.wad_path or ''),str(s.texture_wads or ''),str(s.palette_path or ''),str(s.game_dir or ''))
    if not force and _LAST_TEX_SIG==tex_sig and not _AUTO_QUEUE and _AUTO_TOTAL>0:
        _tag_asset_browsers_redraw(section=getattr(s,'asset_browser_section','TEXTURES'))
        return

    existing_by_id={}
    ready_names=set()
    for m in bpy.data.materials:
        prof=m.get('wl_asset_profile')
        if not prof and not m.get('wl_asset_id'):
            continue
        match=(prof==s.engine)
        if match and not profiles.is_source(s.engine) and m.get('wl_wad'):
            try:
                match=str(Path(m['wl_wad']).resolve()) in valid_wads
            except Exception:
                match=False
        if not match:
            if m.asset_data is not None:
                try:m.asset_clear()
                except Exception:pass
        else:
            if m.asset_data is None:
                try:
                    row=json.loads(m['wl_asset']) if m.get('wl_asset') else asset_index.record(s.engine,str(m.get('wl_texture',m.name)),'MATERIAL',source=m.get('wl_wad',s.game_dir))
                    metadata(m,row)
                except Exception:
                    pass
            else:
                try:m.asset_data.catalog_id=TEXTURES_CATALOG_ID
                except Exception:pass
            if m.get('wl_asset_id'):
                existing_by_id[m['wl_asset_id']]=m
            if m.asset_data is not None and m.get('wl_preview_ready') and m.get('wl_texture'):
                ready_names.add(str(m['wl_texture']).casefold())

    try:
        all_names=textures.all_names(s,'')
    except Exception:
        all_names=[]
    all_set={n.casefold() for n in all_names}
    _AUTO_TOTAL=len(all_names)
    _AUTO_PUBLISHED=len(ready_names & all_set)
    _AUTO_QUEUE=[n for n in all_names if n.casefold() not in ready_names]
    _LAST_TEX_SIG=tex_sig

    initial_batch=24 if profiles.is_source(s.engine) else (32 if bpy.app.background else 64)
    if _AUTO_QUEUE:
        _publish_batch(s,initial_batch,existing_by_id=existing_by_id)
    if _AUTO_QUEUE and not bpy.app.background:
        if not bpy.app.timers.is_registered(_auto_publish_tick):
            bpy.app.timers.register(_auto_publish_tick,first_interval=0.02)
    _tag_asset_browsers_redraw(section=getattr(s,'asset_browser_section','TEXTURES'))


def place(context,row,location=None):
    from .ui import _spawn_point_entity
    s=context.scene.wavelength
    if row['engine']!=s.engine:raise ValueError('Asset belongs to another engine profile')
    category=row['category'];path=row['path']
    if category=='MODEL':classname='prop_static' if profiles.is_source(s.engine) else 'cycler' if profiles.is_goldsrc(s.engine) else None;key='model'
    elif category=='SOUND':classname='ambient_generic' if profiles.is_source(s.engine) or profiles.is_goldsrc(s.engine) else None;key='message'
    elif category=='PARTICLE':classname='info_particle_system' if profiles.is_source(s.engine) else None;key='effect_name'
    else:classname='env_sprite' if profiles.is_goldsrc(s.engine) or profiles.is_source(s.engine) else None;key='model'
    if not classname:raise ValueError(f'{category} placement is not supported by this engine; indexed metadata is available')
    if category=='PARTICLE':
        if not row.get('effect_name'):raise ValueError('Enter a named effect from this particle collection')
        path=row['effect_name']
    if category=='MODEL' and not path.lower().endswith('.mdl'):raise ValueError('This source model must be compiled to MDL before engine placement (prop pipeline milestone)')
    obj=_spawn_point_entity(context,classname)
    pairs=json.loads(obj['wl_pairs']);pairs.append([key,path[6:] if category=='SOUND' and path.startswith('sound/') else path]);obj['wl_pairs']=json.dumps(pairs)
    obj['wl_asset']=json.dumps(row)
    if location is not None:obj.location=location
    if category=='MODEL' and 'bounds' in row:
        # Parent is the engine origin, preview box has its real header offset/size.
        lo,hi=row['bounds'];child=bpy.data.objects.new('Model bounds (proxy)',None);context.collection.objects.link(child);child.parent=obj;child.empty_display_type='CUBE';child.empty_display_size=1
        unit=profiles.unit_meters(s);child.location=[(a+b)*unit/2 for a,b in zip(lo,hi)];child.scale=[(b-a)*unit/2 for a,b in zip(lo,hi)];child['wl_exclude']=True
    return obj


def _brush_mat_signature(obj):
    if obj is None or obj.type!='MESH' or not obj.data:
        return ''
    mats=obj.data.materials
    return '|'.join(
        f"{p.material_index}:{mats[p.material_index].get('wl_texture','') if p.material_index<len(mats) and mats[p.material_index] else ''}"
        for p in obj.data.polygons
    )


@persistent
def dropped(owner, depsgraph=None):
    global _BUSY
    if _BUSY or not workspace.active() or owner!=bpy.context.scene:return
    _BUSY=True
    try:
        s=owner.wavelength
        for obj in list(owner.objects):
            if obj.get('wl_asset_template') and not any(c.name==COLLECTION for c in obj.users_collection):
                try:
                    placed=place(bpy.context,json.loads(obj['wl_asset']),obj.matrix_world.translation)
                    placed.rotation_euler=obj.rotation_euler
                    bpy.data.objects.remove(obj,do_unlink=True)
                except ValueError as exc:s.status=str(exc)
                continue
            if obj.type!='MESH' or obj.get('wl_role')!='BRUSH' or obj.get('wl_exclude') or not obj.data:
                continue
            for mat in obj.data.materials:
                if mat and mat.get('wl_texture') and not mat.get('wl_realized'):
                    try:textures.realize_material(s,mat)
                    except Exception:pass
            ptr=obj.as_pointer()
            sig=_brush_mat_signature(obj)
            prev=_BRUSH_MAT_SIGS.get(ptr)
            if prev is None:
                _BRUSH_MAT_SIGS[ptr]=sig
                continue
            if sig!=prev:
                _BRUSH_MAT_SIGS[ptr]=sig
                if textures.sync_faces_from_materials(obj):
                    from . import editor,primitive_ui
                    try:editor.apply_uv(obj,s.engine)
                    except Exception:pass
                    dropped_mat=next((obj.data.materials[p.material_index] for p in obj.data.polygons if p.material_index<len(obj.data.materials) and obj.data.materials[p.material_index] and obj.data.materials[p.material_index].get('wl_texture')),None)
                    if dropped_mat and dropped_mat.get('wl_texture'):
                        s.texture=str(dropped_mat['wl_texture'])
                    root=primitive_ui.root_for(obj)
                    if root and root.get('wl_assembly_locked',True) and obj.mode=='OBJECT' and dropped_mat:
                        for part in primitive_ui.parts_for(root):
                            if part is not obj and part.type=='MESH' and part.data:
                                textures.assign(part,range(len(part.data.polygons)),dropped_mat)
                                try:editor.apply_uv(part,s.engine)
                                except Exception:pass
                                _BRUSH_MAT_SIGS[part.as_pointer()]=_brush_mat_signature(part)
    finally:_BUSY=False


class WL_OT_assets(bpy.types.Operator):
    bl_idname='wavelength.index_assets';bl_label='Publish Native Assets'
    category:bpy.props.EnumProperty(items=[(c,c.title(),'') for c in ('MATERIAL','MODEL','ENTITY','DECAL','SKY','SOUND','PARTICLE','EFFECT')])
    search:bpy.props.StringProperty(name='Filter')
    limit:bpy.props.IntProperty(name='Maximum assets this batch',default=64,min=1,max=512)
    def invoke(self,context,event):return context.window_manager.invoke_props_dialog(self)
    def draw(self,context):
        for field in ('category','search','limit'):self.layout.prop(self,field)
        self.layout.label(text='Existing assets are reused; filter to narrow large libraries.')
    def execute(self,context):
        s=context.scene.wavelength;count=0;errors=[]
        try:
            if self.category=='ENTITY':
                from .entity import browser
                count=browser.rebuild(context)
            elif self.category in {'MATERIAL','DECAL','SKY'}:
                names=textures.all_names(s,self.search)
                for name in names:
                    row=asset_index.record(s.engine,name,'MATERIAL')
                    if self.category!='MATERIAL' and row['category']!=self.category:continue
                    if count>=self.limit:break
                    try:publish_material_fast(s,name);count+=1
                    except (ValueError,OSError,RuntimeError) as exc:errors.append(str(exc))
            else:
                rows=asset_index.discover(s)
                cache=Path(bpy.utils.user_resource('CONFIG'))/'wavelength'/'assets'/f'{s.engine}.json';asset_index.write_index(cache,rows)
                for row in rows:
                    if row['category']==self.category and self.search.casefold() in row['path'].casefold():
                        publish_proxy(context,row);count+=1
                        if count>=self.limit:break
            s.status=f'{count} native assets ready; {len(errors)} skipped'
            if errors:self.report({'WARNING'},errors[0])
            return {'FINISHED'}
        except (OSError,ValueError,RuntimeError) as exc:self.report({'ERROR'},diagnostics.error(self.bl_idname, exc));return {'CANCELLED'}


class WL_OT_use_asset(bpy.types.Operator):
    bl_idname='wavelength.use_asset';bl_label='Use Selected Wavelength Asset';bl_options={'UNDO'}
    effect_name:bpy.props.StringProperty(name='Named particle effect')
    def invoke(self,context,event):
        asset=getattr(context,'asset',None);block=asset.local_id if asset else None
        if block and block.get('wl_asset') and json.loads(block['wl_asset'])['category']=='PARTICLE':return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)
    def execute(self,context):
        asset=getattr(context,'asset',None);block=asset.local_id if asset else None
        if block is None:self.report({'ERROR'},'Select a Current File Wavelength asset');return {'CANCELLED'}
        try:
            if isinstance(block,bpy.types.Material):
                s=context.scene.wavelength;s.texture=block.get('wl_texture','')
                textures.realize_material(s,block)
                from . import editor,primitive_ui
                targets=[]
                seen=set()
                for obj in context.selected_objects:
                    root=primitive_ui.root_for(obj)
                    if root and root.get('wl_assembly_locked',True) and obj.mode=='OBJECT':
                        for part in primitive_ui.parts_for(root):
                            if part.as_pointer() not in seen:
                                seen.add(part.as_pointer());targets.append(part)
                    elif obj.type=='MESH' and obj.get('wl_role')=='BRUSH' and obj.as_pointer() not in seen:
                        seen.add(obj.as_pointer());targets.append(obj)
                for obj in targets:
                    if obj.mode=='EDIT':
                        import bmesh
                        bm=bmesh.from_edit_mesh(obj.data)
                        slot=next((i for i,m in enumerate(obj.data.materials) if m==block),None)
                        if slot is None:slot=len(obj.data.materials);obj.data.materials.append(block)
                        for f in bm.faces:
                            if f.select:f.material_index=slot
                        bmesh.update_edit_mesh(obj.data)
                    else:
                        textures.assign(obj,range(len(obj.data.polygons)),block);editor.apply_uv(obj,s.engine)
                        _BRUSH_MAT_SIGS[obj.as_pointer()]=_brush_mat_signature(obj)
            elif block.get('wl_entity_browser_template'):
                from .ui import _spawn_point_entity
                _spawn_point_entity(context,block['wl_entity_browser_template'])
            elif block.get('wl_asset'):
                row=json.loads(block['wl_asset']);row['effect_name']=self.effect_name;place(context,row)
            else:raise ValueError('Not a Wavelength asset')
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},diagnostics.error(self.bl_idname, exc));return {'CANCELLED'}


class WL_PT_assets(bpy.types.Panel):
    bl_label='Wavelength Assets';bl_idname='WL_PT_assets';bl_space_type='FILE_BROWSER';bl_region_type='TOOLS'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.area.ui_type=='ASSETS'
    def draw(self,context):
        s=context.scene.wavelength
        l=self.layout
        row=l.row(align=True)
        row.prop(s,'asset_browser_section',expand=True)
        if s.asset_browser_section=='TEXTURES':
            pub,total,loading=sync_status(s)
            l.label(text=f'Textures: {pub}/{total}' + (' (loading…)' if loading else ' ready'),icon='TEXTURE')
            l.operator('wavelength.refresh_textures',text='Reload Profile Textures',icon='FILE_REFRESH')
        else:
            ent_count=sum(1 for o in bpy.data.objects if o.get('wl_entity_browser_profile')==s.engine and o.asset_data is not None)
            l.label(text=f'Entities: {ent_count} ready',icon='EMPTY_ARROWS')
            l.operator('wavelength.entity_browser_refresh',text='Reload Profile Entities',icon='FILE_REFRESH')
        l.operator('wavelength.use_asset',icon='CHECKMARK')
        asset=getattr(context,'asset',None);block=asset.local_id if asset else None
        if block and block.get('wl_asset'):
            row_data=json.loads(block['wl_asset']);l.label(text=row_data['category']);l.label(text=row_data['validation'])


def header(self,context):
    if workspace.active(context) and context.area.ui_type=='ASSETS':
        s=context.scene.wavelength
        row=self.layout.row(align=True)
        row.prop(s,'asset_browser_section',expand=True)
        if s.asset_browser_section=='TEXTURES':
            pub,total,loading=sync_status(s)
            self.layout.label(text=f'{pub}/{total} textures' + ('…' if loading else ''))
        self.layout.operator('wavelength.entity_browser_refresh',text='',icon='FILE_REFRESH')
        self.layout.operator('wavelength.use_asset',text='Use Asset',icon='CHECKMARK')


def register():
    for cls in (WL_OT_assets,WL_OT_use_asset,WL_PT_assets):bpy.utils.register_class(cls)
    bpy.types.FILEBROWSER_HT_header.append(header)
    if dropped not in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.append(dropped)


def unregister():
    if bpy.app.timers.is_registered(_auto_publish_tick):
        bpy.app.timers.unregister(_auto_publish_tick)
    bpy.types.FILEBROWSER_HT_header.remove(header)
    if dropped in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(dropped)
    for cls in (WL_PT_assets,WL_OT_use_asset,WL_OT_assets):bpy.utils.unregister_class(cls)
