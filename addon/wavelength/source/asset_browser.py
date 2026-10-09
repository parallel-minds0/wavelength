"""Native Asset Browser publishers using existing WAD/VPK/FGD backends."""
import json
from pathlib import Path
import bpy
from bpy.app.handlers import persistent
from . import asset_index,profiles,textures,workspace,scene

COLLECTION='_WL_ASSET_TEMPLATES'
_BUSY=False


def collection(context):
    c=bpy.data.collections.get(COLLECTION)
    if c is None:
        c=bpy.data.collections.new(COLLECTION);context.scene.collection.children.link(c)
    c.hide_render=True;c.hide_viewport=True
    return c


def metadata(block,row):
    block['wl_asset']=json.dumps(row);block['wl_asset_id']=row['id']
    block.asset_mark();block.asset_data.description=f"{row['category']} · {row['engine']} · {row['path']}\n{row['validation']}"
    block.asset_data.author='Wavelength local game index'
    for tag in ('Wavelength',row['category'],row['engine']):
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


def publish_material(context,name):
    s=context.scene.wavelength
    row=asset_index.record(s.engine,name,'MATERIAL',source=s.game_dir)
    existing=next((m for m in bpy.data.materials if m.get('wl_asset_id')==row['id']),None)
    if existing:return existing
    mat=textures.material(s,name);row['source']=mat.get('wl_wad',s.game_dir)
    row['validation']='decoded';row['dependencies']=[n.image.filepath for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.filepath]
    if profiles.is_source(s.engine):
        from .source_assets import library
        props=library(s.game_dir).material(name)
        row['dependencies']=[v for k,v in props.items() if k in {'$basetexture','$bumpmap','$detail','$envmapmask','%tooltexture'} and isinstance(v,str)]
    metadata(mat,row);mat.name=name;preview(mat);return mat


def publish_proxy(context,row):
    old=next((o for o in bpy.data.objects if o.get('wl_asset_id')==row['id'] and o.get('wl_asset_template')),None)
    if old:return old
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


@persistent
def dropped(owner, depsgraph=None):
    global _BUSY
    if _BUSY or not workspace.active() or owner!=bpy.context.scene:return
    _BUSY=True
    try:
        for obj in list(owner.objects):
            if not obj.get('wl_asset_template') or any(c.name==COLLECTION for c in obj.users_collection):continue
            try:
                placed=place(bpy.context,json.loads(obj['wl_asset']),obj.matrix_world.translation)
                placed.rotation_euler=obj.rotation_euler
                bpy.data.objects.remove(obj,do_unlink=True)
            except ValueError as exc:owner.wavelength.status=str(exc)
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
                    try:publish_material(context,name);count+=1
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
        except (OSError,ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}


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
                from . import editor
                objects=context.selected_objects
                for obj in objects:
                    if obj.type!='MESH' or obj.get('wl_role')!='BRUSH':continue
                    if obj.mode=='EDIT':
                        import bmesh
                        bm=bmesh.from_edit_mesh(obj.data);indices=[f.index for f in bm.faces if f.select]
                        slot=next((i for i,m in enumerate(obj.data.materials) if m==block),None)
                        if slot is None:slot=len(obj.data.materials);obj.data.materials.append(block)
                        for f in bm.faces:
                            if f.select:f.material_index=slot
                        bmesh.update_edit_mesh(obj.data)
                    else:textures.assign(obj,range(len(obj.data.polygons)),block);editor.apply_uv(obj,s.engine)
            elif block.get('wl_entity_browser_template'):
                from .ui import _spawn_point_entity
                _spawn_point_entity(context,block['wl_entity_browser_template'])
            elif block.get('wl_asset'):
                row=json.loads(block['wl_asset']);row['effect_name']=self.effect_name;place(context,row)
            else:raise ValueError('Not a Wavelength asset')
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}


class WL_PT_assets(bpy.types.Panel):
    bl_label='Wavelength Assets';bl_idname='WL_PT_assets';bl_space_type='FILE_BROWSER';bl_region_type='TOOLS'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.area.ui_type=='ASSETS'
    def draw(self,context):
        self.layout.operator('wavelength.index_assets',icon='FILE_REFRESH')
        self.layout.operator('wavelength.use_asset',icon='CHECKMARK')
        asset=getattr(context,'asset',None);block=asset.local_id if asset else None
        if block and block.get('wl_asset'):
            row=json.loads(block['wl_asset']);self.layout.label(text=row['category']);self.layout.label(text=row['validation'])


def header(self,context):
    if workspace.active(context) and context.area.ui_type=='ASSETS':
        self.layout.operator('wavelength.index_assets',text='Publish Game Assets',icon='FILE_REFRESH')
        self.layout.operator('wavelength.use_asset',text='Use Asset',icon='CHECKMARK')


def register():
    for cls in (WL_OT_assets,WL_OT_use_asset,WL_PT_assets):bpy.utils.register_class(cls)
    bpy.types.FILEBROWSER_HT_header.append(header)
    if dropped not in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.append(dropped)


def unregister():
    bpy.types.FILEBROWSER_HT_header.remove(header)
    if dropped in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(dropped)
    for cls in (WL_PT_assets,WL_OT_use_asset,WL_OT_assets):bpy.utils.unregister_class(cls)
