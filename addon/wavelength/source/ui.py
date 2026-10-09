"""wavelength: Blender-native Quake and GoldSrc level authoring."""
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import uuid
import bpy
import bmesh
from bpy.props import StringProperty,EnumProperty,IntProperty,BoolProperty,CollectionProperty,PointerProperty,FloatProperty
from bpy_extras.io_utils import ImportHelper,ExportHelper
from . import workspace,precision_move,primitive_ui,asset_browser,profile_ui,grid,formats,scene,profiles,textures,identity,editor,resize_gizmo,brush_create,transform_sync,system_tree,authoring
from .entity import models as entity_models, browser as entity_browser
from .geometry import BrushError
from .build.pipeline import Pipeline

_JOB=None
_JOB_SCENE=None
_JOB_PATH=None
_JOB_ENGINE=None
_JOB_MAP_NAME="level"
_JOB_OUTPUT=None



def _entity_catalog_items(settings, context, custom_class=''):
    # One catalog feeds the sidebar, Shift+A browser and search popup.
    from .entity import catalog as entities
    items=list(entities.items(settings,context))
    if custom_class and custom_class not in {item[0] for item in items}:
        items.insert(0,(custom_class,custom_class,'Custom class entered directly'))
    return items or [('info_player_start','info_player_start','Default entity')]

def entity_items(self,context):
    return _entity_catalog_items(self,context,self.entity_class)

def entity_search_items(self,context):
    settings=context.scene.wavelength if context and context.scene else None
    return _entity_catalog_items(settings,context) if settings else [('info_player_start','info_player_start','Default entity')]

def entity_class_search(self, context, edit_text):
    """StringProperty search callback used by Shift+A entity search.

    Returning class names as strings avoids Blender's fragile dynamic-Enum search
    confirmation path while still searching the exact active engine/FGD catalog.
    """
    settings=context.scene.wavelength if context and context.scene else None
    if not settings:
        return ['info_player_start']
    needle=(edit_text or '').casefold()
    names=[item[0] for item in _entity_catalog_items(settings,context)]
    if needle:
        names=[name for name in names if needle in name.casefold()]
    return names

def entity_choice_changed(self,context):
    if self.entity_choice:self.entity_class=self.entity_choice

_ENGINE_FIELDS=('build_output','compiler_dir','qbsp_path','vis_path','light_path','qbsp_args','vis_args','light_args','source_vbsp_args','source_vvis_args','source_vrad_args','game_executable','game_dir','wad_path','palette_path','quake_pak_dir','texture_wads','fgd_path','wrapper','environment','launch_args','map_name')

def local_root(settings):
    candidates=[Path(__file__).resolve().parents[3],Path.cwd()]
    for value in (settings.project_dir,settings.compiler_dir,bpy.data.filepath):
        if value:candidates.extend(Path(bpy.path.abspath(value)).resolve().parents)
    for candidate in candidates:
        if (candidate/'bin/play-quake').is_file() and (candidate/'wavelength/dist').is_dir():return candidate
    return None

def _hl1_linux_defaults():
    """Return native Steam HL1 Linux defaults and validated stock WAD3 sources.

    Do not merely glob *.wad: GoldSrc installs can contain cache/auxiliary files
    that are poor choices for the texture browser.  Validate each candidate as
    WAD3 with at least one texture entry, then choose a useful stock library as
    the active browser source.
    """
    from .wad import Wad
    home=Path.home()
    candidates=[
        home/'.steam/steam/steamapps/common/Half-Life',
        home/'.local/share/Steam/steamapps/common/Half-Life',
        home/'.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Half-Life',
    ]
    install=next((p for p in candidates if p.is_dir()),candidates[0])
    valve=install/'valve'
    valid=[]
    if valve.is_dir():
        for path in sorted(valve.glob('*.wad'),key=lambda p:p.name.casefold()):
            if not path.is_file():
                continue
            try:
                wad=Wad(path)
                if wad.kind==b'WAD3' and wad.entries:
                    valid.append(str(path.resolve()))
            except (OSError,ValueError,UnicodeError,struct.error):
                continue
    # halflife.wad is the most useful default browser source. Keep every valid
    # WAD registered so texture lookup/export can resolve across the full game.
    preferred=('halflife.wad','liquids.wad','xeno.wad','decals.wad')
    by_name={Path(path).name.casefold():path for path in valid}
    active=next((by_name[name] for name in preferred if name in by_name),valid[0] if valid else '')
    exe=install/'hl_linux'
    return {
        'game_dir':str(valve),
        'game_executable':str(exe),
        'texture_wads':json.dumps(valid),
        'wad_path':active,
        'map_name':'wavelength_hl1_linux',
        'launch_args':json.dumps(['-game','{game_dir}','+map','{map}']),
    }

def engine_changed(self,context):
    previous=self.get('_wl_active_engine','blender')
    if previous!=self.engine:
        configurations=json.loads(self.get('_wl_engine_configs','{}'))
        configurations[previous]={key:getattr(self,key) for key in _ENGINE_FIELDS}
        values=configurations.get(self.engine)
        if values is None:
            root=local_root(self)
            preset=(root/'wavelength/dist'/('goldsrc-project.json' if profiles.is_goldsrc(self.engine) else 'quake-project.json')) if root and self.engine in {'quake','goldsrc','goldsrc_linux','goldsrc_linux_steam'} else None
            values=json.loads(preset.read_text()) if preset and preset.is_file() else {}
            if self.engine in {'goldsrc_linux','goldsrc_linux_steam'}:
                values.update(_hl1_linux_defaults())
                if self.engine=='goldsrc_linux_steam':
                    values['launch_args']=json.dumps(['-console','-dev','+map','{map}'])
        if values is not None and profiles.is_source(self.engine) and not values:
            from .source_tools import defaults
            values=defaults(profiles.get(self.engine)['platform'])
        self.unit_scale=profiles.get(self.engine).get('unit_meters',1.0)
        self['_wl_active_engine']=self.engine
        self['_wl_engine_configs']=json.dumps(configurations)
        for key in _ENGINE_FIELDS:setattr(self,key,values.get(key,'[]' if key in {'texture_wads','wrapper','launch_args','qbsp_args','vis_args','light_args','source_vbsp_args','source_vvis_args','source_vrad_args'} else '{}' if key=='environment' else 'wavelength_'+self.engine if key=='map_name' else ''))
        if _JOB and _JOB_SCENE==context.scene:_JOB.cancel()
    self.last_build=''
    grid.update(self,context)
    # Toolbar registration is static; the profile controls creation behavior.
    # Refresh only after every profile field has been installed, so automatic
    # WAD discovery is immediately reflected in the texture enum/browser.
    self.texture_page=0
    textures.refresh(self,context)
    if self.engine in {'goldsrc_linux','goldsrc_linux_steam'} and self.wad_path:
        self.status=f'HL1 Linux profile loaded · {len(json.loads(self.texture_wads or "[]"))} WADs · {self.texture_count} textures in {Path(self.wad_path).name}'
    elif not self.status:
        self.status='Profile selected; tool paths updated. Rebuild before launching.'

def _wl_key_choice_items(self,context):
    try:
        raw=json.loads(self.choices or '[]')
    except (TypeError,ValueError,json.JSONDecodeError):
        raw=[]
    items=[];seen=set()
    for choice in raw:
        if not isinstance(choice,(list,tuple)) or len(choice)<2:continue
        code=str(choice[0]);label=str(choice[1])
        if not code or code in seen:continue
        seen.add(code);items.append((code,label,f'{self.key} = {code}'))
    # Preserve an unknown/mod-specific value instead of coercing it to a preset.
    if self.value and self.value not in seen:
        items.append((self.value,f'Custom: {self.value}',f'Current raw value for {self.key}'))
    return items or [('__NONE__','No choices','No choices are defined for this property')]

def _wl_key_choice_update(self,context):
    if not self.choice or self.choice=='__NONE__':
        return
    self.value=self.choice

    # func_door direction is immediate: write the selected literal `angles`
    # vector straight onto the brush entity.  No conversion/deferred Apply.
    door_angles={'0 0 0','0 90 0','0 180 0','0 270 0','-90 0 0','90 0 0'}
    if self.key!='angles' or self.choice not in door_angles:
        return
    obj=getattr(context,'object',None) if context else None
    if not obj or obj.get('wl_role')!='BRUSH' or not obj.get('wl_entity_id'):
        return
    try:
        pairs=json.loads(obj.get('wl_entity_pairs','[]'))
    except (TypeError,ValueError,json.JSONDecodeError):
        return
    if dict(pairs).get('classname')!='func_door':
        return
    pairs=[[k,v] for k,v in pairs if k not in {'angle','angles'}]
    pairs.append(['angles',self.choice])
    encoded=json.dumps(pairs)
    identity=obj.get('wl_entity_id')
    for other in context.scene.objects:
        if other.get('wl_entity_id')==identity:
            other['wl_entity_pairs']=encoded

class WLKey(bpy.types.PropertyGroup):
    key:StringProperty(name='Key')
    label:StringProperty(name='Label')
    kind:StringProperty(default='string')
    value:StringProperty(name='Value')
    integer:IntProperty(name='Value')
    number:FloatProperty(name='Value')
    choices:StringProperty(default='[]')
    choice:EnumProperty(name='Value',items=_wl_key_choice_items,update=_wl_key_choice_update)

class WLTextureBrowserItem(bpy.types.PropertyGroup):
    name:StringProperty()

class WLTextureGalleryRow(bpy.types.PropertyGroup):
    name0:StringProperty()
    name1:StringProperty()
    name2:StringProperty()

class WLSettings(bpy.types.PropertyGroup):
    profile_id:StringProperty()
    profile_name:StringProperty(name='Profile name',default='My project')
    saved_profile:EnumProperty(name='Saved profiles',items=profile_ui.items)
    unit_scale:FloatProperty(name='Meters per engine unit',default=.0254,min=.000001,update=lambda s,c:grid.update(s,c))
    asset_paths:StringProperty(name='Additional asset roots (JSON)',default='[]')
    engine:EnumProperty(name='Profile',items=[('blender','Blender — No Engine — Any Platform','Neutral Blender authoring; Wavelength does not impose engine rules'),('quake','Quake — Quake — Custom Platform','Classic Quake MAP; user-configured platform/toolchain'),('goldsrc','Half-Life — GoldSrc — Custom Platform','Valve 220 MAP; user-configured platform/toolchain'),('goldsrc_linux','Half-Life — GoldSrc — Linux','Native Half-Life 1 for Linux; discovers and indexes stock WAD3 libraries'),('goldsrc_linux_steam','Half Life 1, GoldSrc, Linux, Steam','Launch Half-Life 1 through Steam App ID 70; discovers stock WAD3 libraries'),('source_hl2_linux','Half-Life 2 — Source 1 — Linux','VMF and native Linux game runtime'),('source_hl2_windows','Half-Life 2 — Source 1 — Windows','VMF and Windows game runtime; configure Steam Proton on Linux')],default='blender',update=engine_changed)
    grid_mode:EnumProperty(name='Grid',items=[('BLENDER','Blender','Use your original Blender grid'),('ENGINE','Engine','Fixed engine-unit grid overlay')],default='BLENDER',update=grid.update)
    grid_step:EnumProperty(name='Step',items=[(str(x),str(x),'Engine units') for x in (1,2,4,8,16,32,64,128,256)],default='16',update=grid.update)
    project_dir:StringProperty(name='Project directory',subtype='DIR_PATH')
    map_name:StringProperty(name='Map name',default='wavelength_test')
    map_path:StringProperty(name='MAP file',subtype='FILE_PATH')
    build_error:StringProperty(name='Build error')
    build_log_dir:StringProperty(name='Build logs',subtype='DIR_PATH')
    build_output:StringProperty(name='Build output',subtype='FILE_PATH',description='Destination BSP; updated only after successful compilation')
    compiler_dir:StringProperty(name='Compiler directory',subtype='DIR_PATH',description='Legacy/shared compiler directory; Quake can use the explicit QBSP/VIS/LIGHT paths below')
    qbsp_path:StringProperty(name='QBSP',subtype='FILE_PATH')
    vis_path:StringProperty(name='VIS',subtype='FILE_PATH')
    light_path:StringProperty(name='LIGHT',subtype='FILE_PATH')
    qbsp_args:StringProperty(name='QBSP arguments JSON',default='[]')
    vis_args:StringProperty(name='VIS arguments JSON',default='[]')
    light_args:StringProperty(name='LIGHT arguments JSON',default='[]')
    source_vbsp_args:StringProperty(name='VBSP arguments JSON',default='[]')
    source_vvis_args:StringProperty(name='VVIS arguments JSON',default='[]')
    source_vrad_args:StringProperty(name='VRAD arguments JSON',default='[]')
    game_executable:StringProperty(name='Game executable',subtype='FILE_PATH')
    game_dir:StringProperty(name='Game directory',subtype='DIR_PATH')
    wad_path:StringProperty(name='Active WAD',subtype='FILE_PATH',update=textures.refresh)
    texture_wads:StringProperty(default='[]')
    palette_path:StringProperty(name='Quake palette',subtype='FILE_PATH')
    quake_pak_dir:StringProperty(name='Quake id1 directory',subtype='DIR_PATH')
    texture_search:StringProperty(name='Search',update=textures.refresh)
    texture_page:IntProperty(default=0,min=0)
    texture_count:IntProperty(default=0)
    texture_choice:EnumProperty(name='Texture',items=textures.enum_items,update=textures.select)
    fgd_path:StringProperty(name='Entity definitions',subtype='FILE_PATH')
    wrapper:StringProperty(name='Compiler wrapper JSON',default='[]',description='Argument array prepended to each compiler, e.g. ["wine"]')
    environment:StringProperty(name='Environment JSON',default='{}',description='Explicit environment overrides for Wine or Proton')
    launch_args:StringProperty(name='Launch arguments JSON',default='[]',description='Use {map}, {game_dir}, {build_dir} placeholders')
    timeout:FloatProperty(name='Stage timeout',default=120,min=1,max=36000)
    status:StringProperty(default='Choose a project and engine')
    diagnostics:StringProperty(default='[]')
    last_build:StringProperty(subtype='FILE_PATH')
    brush_size:FloatProperty(name='Brush size',default=64,min=0.125,max=8192)
    hollow_thickness:FloatProperty(name='Hollow thickness',default=16,min=0.125,max=4096,description='Wall thickness in engine units; positive values hollow inward and preserve the outer bounds')
    brush_type:EnumProperty(name='Brush type',items=[('CUBE','Cube','Rectangular prototype'),('CYLINDER','Cylinder','Convex cylinder prototype'),('CONE','Cone','Convex cone prototype'),('SPHERE','Sphere','Low-poly sphere prototype'),('ARCH','Arch','Editable convex arch'),('STAIRS','Stairs','Editable staircase')],default='CUBE')
    brush_sides:IntProperty(name='Segments',default=8,min=3,max=64,description='Radial segment count for Cylinder, Cone and Sphere')
    brush_rings:IntProperty(name='Rings',default=6,min=2,max=32,description='Latitude rings for Sphere')
    brush_height_steps:IntProperty(name='Height Steps',default=1,min=1,max=256,description='Primitive height in active grid increments')
    arch_segments:IntProperty(name='Arch Segments',default=8,min=3,max=32,description='Number of convex wedge brushes forming an Arch')
    arch_angle:FloatProperty(name='Arch Angle',default=180.0,min=15.0,max=360.0,description='Arc sweep in degrees')
    arch_thickness_steps:IntProperty(name='Arch Thickness Steps',default=1,min=1,max=64,description='Arch radial thickness in active grid increments')
    entity_class:StringProperty(name='Class',default='info_player_start')
    entity_choice:EnumProperty(name='Browse',items=entity_items,update=entity_choice_changed)
    live_texture_reproject:BoolProperty(name='Live reprojection',default=True,description='Recalculate preview UV projection when brush geometry or transforms change instead of stretching existing UVs')
    texture:StringProperty(name='Texture',default='')
    shift_u:FloatProperty(name='U shift',default=0)
    shift_v:FloatProperty(name='V shift',default=0)
    texture_rotation:FloatProperty(name='Rotation',default=0)
    texture_scale_u:FloatProperty(name='U scale',default=1,min=0.001)
    texture_scale_v:FloatProperty(name='V scale',default=1,min=0.001)
    fields:CollectionProperty(type=WLKey)
    field_index:IntProperty(default=0)
    clip_axis:EnumProperty(name='Clip axis',items=[('X','X',''),('Y','Y',''),('Z','Z','')])
    clip_distance:FloatProperty(name='Plane coordinate',default=0)
    clip_flip:BoolProperty(name='Keep positive side',default=False)
    worldspawn_json:StringProperty(name='Worldspawn JSON',default='[]',description='Map-level worldspawn properties except classname')
    entity_json:StringProperty(name='Properties JSON',default='[]',description='Ordered key/value pairs, preserving duplicate and unknown properties')
    entity_editor_binding:StringProperty(default='',options={'HIDDEN'},description='Internal binding for the entity property editor')
    entity_add_key:StringProperty(default='',options={'HIDDEN'},description='Key selected by the Add Property dialog')

class SafeOperator:
    def execute(self,context):
        try:
            self.run(context)
            return {'FINISHED'}
        except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
            context.scene.wavelength.status=str(exc)
            if self.bl_idname=='wavelength.build':context.scene.wavelength.build_error=str(exc)
            self.report({'ERROR'},str(exc));return {'CANCELLED'}

class WL_OT_setup(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.setup';bl_label='Use Local Toolchain';bl_description='Configure this checkout’s installed tools and test game'
    def run(self,context):
        s=context.scene.wavelength
        if s.engine=='blender':raise ValueError('Select an engine before configuring an engine toolchain')
        if profiles.is_source(s.engine):
            from .source_tools import defaults
            data=defaults(profiles.get(s.engine)['platform'])
            for key,value in data.items():setattr(s,key,value)
            s.status='HL2 paths refreshed; configure SDK compilers separately'
            return
        root=local_root(s)
        if root is None:raise ValueError('Local checkout not found; use Load Project with the engine preset')
        preset=root/'wavelength/dist'/('goldsrc-project.json' if profiles.is_goldsrc(s.engine) else 'quake-project.json')
        data=json.loads(preset.read_text())
        for key in _PROJECT_FIELDS:
            if key in data and key!='engine':setattr(s,key,data[key])
        textures.refresh(s,context);s.last_build='';s.status=f'{profiles.PROFILES[s.engine]["label"]} local toolchain configured'

class WL_OT_brush(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.add_brush';bl_label='Add Brush';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        if context.mode!='OBJECT':raise ValueError('Leave Edit Mode first')
        s=context.scene.wavelength
        if s.engine=='blender':raise ValueError('Select an engine before creating BSP brushes')
        if s.brush_type in {'ARCH','SPHERE','STAIRS'}:
            bpy.ops.wavelength.primitive('INVOKE_DEFAULT',kind=s.brush_type);return
        size=profiles.engine_to_world(s, s.brush_size);location=context.scene.cursor.location
        if s.brush_type=='CYLINDER': bpy.ops.mesh.primitive_cylinder_add(vertices=s.brush_sides,radius=size/2,depth=size,location=location)
        elif s.brush_type=='CONE': bpy.ops.mesh.primitive_cone_add(vertices=s.brush_sides,radius1=size/2,radius2=0,depth=size,location=location)
        elif s.brush_type=='SPHERE': bpy.ops.mesh.primitive_uv_sphere_add(segments=s.brush_sides,ring_count=s.brush_rings,radius=size/2,location=location)
        elif s.brush_type=='ARCH': raise ValueError('Use the viewport Arch Brush tool so the arch is built from convex segments')
        else: bpy.ops.mesh.primitive_cube_add(size=size,location=location)
        scene.mark_brush(context.object);context.object.name='Brush'

class WL_OT_hollow(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.make_hollow';bl_label='Make Hollow';bl_options={'REGISTER','UNDO'}
    bl_description='Replace the selected rectangular brush with six solid wall brushes'
    def run(self,context):
        if context.mode!='OBJECT':raise ValueError('Leave Edit Mode first')
        obj=context.active_object
        if obj is None or obj.type!='MESH' or obj.get('wl_role')!='BRUSH':raise ValueError('Select one rectangular brush')
        if len(obj.data.vertices)!=8 or len(obj.data.polygons)!=6 or any(len(p.vertices)!=4 for p in obj.data.polygons):
            raise ValueError('Make Hollow currently requires a rectangular six-sided brush')
        coords=[v.co.copy() for v in obj.data.vertices]
        mins=[min(v[i] for v in coords) for i in range(3)];maxs=[max(v[i] for v in coords) for i in range(3)]
        eps=1e-6
        if any(any(abs(v[i]-mins[i])>eps and abs(v[i]-maxs[i])>eps for i in range(3)) for v in coords):
            raise ValueError('Make Hollow currently requires an axis-aligned rectangular brush mesh')
        settings=context.scene.wavelength;unit=profiles.unit_meters(settings);t=profiles.engine_to_world(settings, settings.hollow_thickness)
        size=[maxs[i]-mins[i] for i in range(3)]
        if any(2*t>=d-eps for d in size):raise ValueError('Hollow thickness must be less than half of every brush dimension')
        x0,y0,z0=mins;x1,y1,z1=maxs;ix0,iy0,iz0=x0+t,y0+t,z0+t;ix1,iy1,iz1=x1-t,y1-t,z1-t
        boxes=[('Left',(x0,y0,z0),(ix0,y1,z1)),('Right',(ix1,y0,z0),(x1,y1,z1)),
               ('Front',(ix0,y0,z0),(ix1,iy0,z1)),('Back',(ix0,iy1,z0),(ix1,y1,z1)),
               ('Bottom',(ix0,iy0,z0),(ix1,iy1,iz0)),('Top',(ix0,iy0,iz1),(ix1,iy1,z1))]
        collection=obj.users_collection[0] if obj.users_collection else context.collection
        matrix=obj.matrix_world.copy();materials=list(obj.data.materials)
        copied={k:obj[k] for k in obj.keys() if k not in {'wl_id','wl_faces','wl_role'}}
        created=[]
        try:
            for label,lo,hi in boxes:
                xa,ya,za=lo;xb,yb,zb=hi
                verts=[(xa,ya,za),(xb,ya,za),(xb,yb,za),(xa,yb,za),(xa,ya,zb),(xb,ya,zb),(xb,yb,zb),(xa,yb,zb)]
                faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
                mesh=bpy.data.meshes.new(obj.name+' '+label);mesh.from_pydata(verts,[],faces);mesh.update()
                wall=bpy.data.objects.new(obj.name+' '+label,mesh);collection.objects.link(wall);wall.matrix_world=matrix
                for k,v in copied.items():wall[k]=v
                for material in materials:mesh.materials.append(material)
                # Preserve the source's dominant material on every generated face.
                if materials:
                    dominant=max((p.material_index for p in obj.data.polygons),key=lambda i:sum(1 for p in obj.data.polygons if p.material_index==i))
                    for poly in mesh.polygons:poly.material_index=min(dominant,len(materials)-1)
                scene.mark_brush(wall)
                try:editor.apply_uv(wall,context.scene.wavelength.engine)
                except (ValueError,BrushError,KeyError):pass
                created.append(wall)
        except Exception:
            for wall in created:bpy.data.objects.remove(wall,do_unlink=True)
            raise
        bpy.data.objects.remove(obj,do_unlink=True)
        for wall in created:wall.select_set(True)
        context.view_layer.objects.active=created[0]
        context.scene.wavelength.status=f'Made hollow brush: {len(created)} walls, {context.scene.wavelength.hollow_thickness:g} unit thickness'

class WL_OT_mark(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.mark_brush';bl_label='Use Selected Meshes';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        for obj in context.selected_objects:
            if obj.type=='MESH':scene.mark_brush(obj)

class WL_OT_ids(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.repair_ids';bl_label='Repair Object / Face IDs';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        seen=set()
        for obj in context.scene.objects:
            if not obj.get('wl_role'):continue
            if not obj.get('wl_id') or obj['wl_id'] in seen:obj['wl_id']=scene.uid()
            seen.add(obj['wl_id'])
            if obj.type=='MESH':scene.mark_brush(obj)
        context.scene.wavelength.status='IDs repaired; new faces use default projection'

class WL_OT_snap(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.snap_grid';bl_label='Snap Selection to Grid';bl_options={'REGISTER','UNDO'}
    bl_description='Snap selected vertices or object origins to exact world-space engine increments'
    def run(self,context):
        s=context.scene.wavelength
        if s.engine=='blender':raise ValueError('Blender / No Engine uses Blender snapping')
        step=profiles.active_grid_step_meters(s)
        def snap(v):return profiles.snap_world_value(s, v)
        if context.mode=='EDIT_MESH':
            for obj in context.objects_in_mode_unique_data:
                bm=bmesh.from_edit_mesh(obj.data);inverse=obj.matrix_world.inverted()
                for v in bm.verts:
                    if v.select:
                        p=obj.matrix_world@v.co;v.co=inverse@type(p)([snap(x) for x in p])
                bmesh.update_edit_mesh(obj.data)
        elif context.mode=='OBJECT':
            for obj in context.selected_objects:
                matrix=obj.matrix_world.copy();matrix.translation=[snap(x) for x in matrix.translation];obj.matrix_world=matrix
        else:raise ValueError('Snap works in Object or Mesh Edit Mode')

class WL_OT_grid_step(bpy.types.Operator):
    bl_idname='wavelength.grid_step';bl_label='Change Grid Step';bl_options={'UNDO'}
    direction:IntProperty(default=1)
    def execute(self,context):
        s=context.scene.wavelength;steps=[1,2,4,8,16,32,64,128,256]
        index=steps.index(int(s.grid_step));s.grid_step=str(steps[max(0,min(len(steps)-1,index+self.direction))]);return {'FINISHED'}

def _spawn_point_entity(context, classname):
    s=context.scene.wavelength
    classname=(classname or '').strip()
    if not classname:raise ValueError('Choose an engine entity class first')
    if s.engine=='blender':raise ValueError('Choose Quake or Half-Life / GoldSrc before adding an engine entity')
    s.entity_class=classname
    # Keep the sidebar selector synchronized when the class exists in its enum.
    try:s.entity_choice=classname
    except (TypeError,ValueError):pass
    obj=bpy.data.objects.new(classname,None);context.collection.objects.link(obj)
    unit=profiles.unit_meters(s);obj.empty_display_type='ARROWS';obj.empty_display_size=profiles.engine_to_world(s,16);obj['wl_unit_meters']=unit;obj.location=context.scene.cursor.location
    pairs=_entity_creation_defaults(s,classname)
    obj['wl_role']='ENTITY';obj['wl_id']=scene.uid();obj['wl_pairs']=json.dumps(pairs)
    if profiles.is_goldsrc(s.engine):entity_models.attach_reference(obj,pairs)
    for old in context.selected_objects:old.select_set(False)
    obj.select_set(True);context.view_layer.objects.active=obj
    s.status=f'Created point entity {classname} at 3D cursor'
    return obj

class WL_OT_entity(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.add_entity';bl_label='Create Point Entity';bl_options={'REGISTER','UNDO'}

    def run(self,context):
        s=context.scene.wavelength
        _spawn_point_entity(context,(s.entity_choice or s.entity_class or '').strip())

class WL_OT_entity_search(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.add_entity_search';bl_label='Search Wavelength Entities';bl_options={'REGISTER','UNDO'}
    bl_description='Search the active engine/FGD entity catalog and create the selected point entity at the 3D cursor'
    classname:StringProperty(name='Entity Class',default='',search=entity_class_search)

    @classmethod
    def poll(cls,context):
        return bool(context.scene and hasattr(context.scene,'wavelength') and context.scene.wavelength.engine!='blender')

    def invoke(self,context,event):
        # A searchable StringProperty is the path invoke_search_popup is designed
        # for.  Confirmation calls execute(), which spawns the selected class.
        self.classname=''
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

    def execute(self,context):
        try:
            classname=(self.classname or '').strip()
            if not classname:
                raise ValueError('Choose an entity class from the search results')
            valid={item[0] for item in _entity_catalog_items(context.scene.wavelength,context)}
            if classname not in valid:
                raise ValueError(f'Entity class not found in active catalog: {classname}')
            _spawn_point_entity(context,classname)
            return {'FINISHED'}
        except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
            context.scene.wavelength.status=str(exc)
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}

class WL_OT_entity_browse(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.add_entity_browse';bl_label='Add Wavelength Entity';bl_options={'REGISTER','UNDO'}
    bl_description='Create the selected entity from the complete active engine/FGD catalog'
    classname:EnumProperty(name='Entity Class',items=entity_search_items)

    @classmethod
    def poll(cls,context):
        return bool(context.scene and hasattr(context.scene,'wavelength') and context.scene.wavelength.engine!='blender')

    def run(self,context):
        _spawn_point_entity(context,self.classname)

class WL_MT_add_entity(bpy.types.Menu):
    bl_idname='WL_MT_add_entity';bl_label='Entity'
    def draw(self,context):
        layout=self.layout
        layout.operator('wavelength.add_entity_search',text='Search Entities…',icon='VIEWZOOM')
        layout.separator()
        layout.operator_menu_enum('wavelength.add_entity_browse','classname',text='Browse All Entities',icon='EMPTY_ARROWS')

class WL_MT_add(bpy.types.Menu):
    bl_idname='WL_MT_add';bl_label='Wavelength'
    def draw(self,context):
        layout=self.layout
        if context.scene.wavelength.engine=='blender':
            layout.label(text='Choose Quake or Half-Life / GoldSrc',icon='INFO')
        else:
            layout.menu('WL_MT_add_entity',icon='EMPTY_ARROWS')

def _draw_view3d_add_menu(self,context):
    if not workspace.active(context):return
    self.layout.menu('WL_MT_add',icon='MOD_BUILD')

def _entity_creation_defaults(settings, classname):
    """Materialize meaningful engine defaults when an entity is created.

    Project/mod FGD definitions take precedence. Stock GoldSrc definitions fill
    missing inherited/default fields. Empty defaults are deliberately omitted:
    target, targetname, message, model paths and similar mapper-authored values
    must remain intentional rather than becoming empty exported keys.
    """
    primary=[]
    if settings.fgd_path:
        try:
            from .entity import fgd
            primary=fgd.properties(fgd.load(bpy.path.abspath(settings.fgd_path)),classname)
        except (OSError,ValueError,RuntimeError,KeyError,TypeError):
            primary=[]
    definitions=primary
    if profiles.is_goldsrc(settings.engine):
        from .entity import goldsrc as goldsrc_entities
        definitions=goldsrc_entities.merge_properties(classname,primary)
    pairs=[('classname',classname)]
    present={'classname'}
    for prop in definitions:
        key=str(prop.get('key','')).strip();default=str(prop.get('default',''))
        if key and key not in present and default!='':
            pairs.append((key,default));present.add(key)
    if profiles.is_source(settings.engine) and classname in {'light','light_spot','light_environment'} and '_light' not in present:
        pairs.append(('_light','255 255 255 200'))
    # Quake has no built-in schema yet; retain the established useful light default.
    if settings.engine=='quake' and classname=='light' and 'light' not in present:
        pairs.append(('light','300'))
    return pairs

def _brush_entity_defaults(settings, classname):
    return _entity_creation_defaults(settings,classname)

def _brush_entity_members(scene_data, identity):
    return [o for o in scene_data.objects if o.get('wl_role')=='BRUSH' and o.get('wl_entity_id')==identity]

class WL_OT_brush_entity(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.brush_entity';bl_label='Make Brush Entity';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        s=context.scene.wavelength
        selected=[o for o in context.selected_objects if o.get('wl_role')=='BRUSH']
        if not selected:raise ValueError('Select one or more brushes')
        # Creating a new brush entity is intentionally explicit. Existing entity
        # members are rejected so two logical entities cannot be merged by accident.
        if any(o.get('wl_entity_id') for o in selected):
            raise ValueError('Selection already contains brush-entity members; use Add Solids instead')
        identity=scene.uid();pairs=json.dumps(_brush_entity_defaults(s,s.entity_class))
        for obj in selected:
            obj['wl_entity_id']=identity;obj['wl_entity_pairs']=pairs
        s.status=f'Created {s.entity_class} from {len(selected)} brush(es)'

class WL_OT_brush_entity_add(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.brush_entity_add';bl_label='Add Solids to Brush Entity';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        active=context.object
        if not active or active.get('wl_role')!='BRUSH' or not active.get('wl_entity_id'):
            raise ValueError('Make a brush-entity member active, then select world brushes to add')
        identity=active['wl_entity_id'];pairs=active.get('wl_entity_pairs','[]')
        candidates=[o for o in context.selected_objects if o is not active and o.get('wl_role')=='BRUSH']
        if not candidates:raise ValueError('Select world brushes in addition to the active brush entity')
        if any(o.get('wl_entity_id') and o.get('wl_entity_id')!=identity for o in candidates):
            raise ValueError('Selection contains solids from another brush entity')
        added=0
        for obj in candidates:
            if obj.get('wl_entity_id')==identity:continue
            obj['wl_entity_id']=identity;obj['wl_entity_pairs']=pairs;added+=1
        context.scene.wavelength.status=f'Added {added} solid(s) to brush entity'

class WL_OT_brush_entity_remove(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.brush_entity_remove';bl_label='Remove Solids from Brush Entity';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        selected=[o for o in context.selected_objects if o.get('wl_role')=='BRUSH' and o.get('wl_entity_id')]
        if not selected:raise ValueError('Select brush-entity solids to return to world')
        groups={o.get('wl_entity_id') for o in selected}
        for obj in selected:
            obj.pop('wl_entity_id',None);obj.pop('wl_entity_pairs',None)
        # A one-solid brush entity is valid, but an empty entity has no object to
        # carry it and therefore naturally ceases to exist.
        context.scene.wavelength.status=f'Returned {len(selected)} solid(s) to world geometry'

class WL_OT_brush_entity_to_world(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.brush_entity_to_world';bl_label='Convert Brush Entity to World';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        active=context.object
        if not active or active.get('wl_role')!='BRUSH' or not active.get('wl_entity_id'):
            raise ValueError('Select a brush-entity member')
        identity=active['wl_entity_id'];members=_brush_entity_members(context.scene,identity)
        for obj in members:
            obj.pop('wl_entity_id',None);obj.pop('wl_entity_pairs',None)
        context.scene.wavelength.status=f'Converted {len(members)} solid(s) to world geometry'

def _entity_property_target(obj):
    if obj is None:return None,None,''
    if obj.get('wl_role')=='ENTITY':
        key='wl_pairs';identity='point:'+str(obj.get('wl_id') or obj.name_full)
    elif obj.get('wl_role')=='BRUSH' and obj.get('wl_entity_id'):
        key='wl_entity_pairs';identity='brush:'+str(obj.get('wl_entity_id'))
    else:return None,None,''
    try:pairs=json.loads(obj.get(key,'[]'))
    except (TypeError,ValueError,json.JSONDecodeError):pairs=[]
    classname=dict(pairs).get('classname','')
    return key,pairs,identity+'|'+classname

class WL_OT_properties(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.entity_properties';bl_label='Entity Properties';bl_options={'REGISTER','UNDO'}
    apply:BoolProperty(default=False)
    def run(self,context):
        obj=context.object;s=context.scene.wavelength
        key,current_pairs,binding=_entity_property_target(obj)
        if key is None:raise ValueError('Select a point entity or brush entity')
        if not self.apply:
            # Clean up the bad 0.10.15/0.10.16 singular `angle` key once,
            # converting it back to the literal `angles` vector used by func_door.
            pair_dict=dict(current_pairs)
            if pair_dict.get('classname')=='func_door' and 'angle' in pair_dict:
                legacy={'0':'0 0 0','90':'0 90 0','180':'0 180 0','270':'0 270 0','-1':'-90 0 0','-2':'90 0 0'}
                converted=legacy.get(str(pair_dict.get('angle','')).strip())
                if converted is not None:
                    current_pairs=[[k,v] for k,v in current_pairs if k not in {'angle','angles'}]
                    current_pairs.append(['angles',converted])
                    if key=='wl_entity_pairs':
                        identity=obj.get('wl_entity_id')
                        for other in context.scene.objects:
                            if other.get('wl_entity_id')==identity:other[key]=json.dumps(current_pairs)
                    else:
                        obj[key]=json.dumps(current_pairs)
                    _,_,binding=_entity_property_target(obj)
            s.entity_json=json.dumps(current_pairs);s.fields.clear();s.entity_editor_binding=binding
            definitions={p['key']:p for p in _entity_definitions(context,current_pairs)}
            for k,v in current_pairs:
                item=s.fields.add();item.key=k;item.value=v;definition=definitions.get(k,{})
                item.label=definition.get('label',k);item.kind=definition.get('type','string');item.choices=json.dumps(definition.get('choices',[]))
                if item.kind=='choices' and definition.get('choices'):
                    codes={str(c[0]) for c in definition.get('choices',[]) if isinstance(c,(list,tuple)) and c}
                    if v in codes:item.choice=v
                try:
                    if item.kind in {'integer','flags'}:item.integer=int(v)
                    elif item.kind=='float':item.number=float(v)
                except ValueError:item.kind='string'
            return
        if s.entity_editor_binding!=binding:
            raise ValueError('Selection changed. Read this entity before applying properties.')
        pairs=[[f.key,str(f.integer) if f.kind in {'integer','flags'} else str(f.number) if f.kind=='float' else f.value] for f in s.fields]
        if not isinstance(pairs,list) or any(not isinstance(p,list) or len(p)!=2 or not all(isinstance(x,str) for x in p) for p in pairs):raise ValueError('Expected a list of string key/value pairs')
        if not any(k=='classname' for k,v in pairs):raise ValueError('classname is required')
        if key=='wl_entity_pairs':
            identity=obj.get('wl_entity_id')
            if not identity:raise ValueError('Object is not a brush entity')
            for other in context.scene.objects:
                if other.get('wl_entity_id')==identity:other[key]=json.dumps(pairs)
        else:
            obj[key]=json.dumps(pairs)
            if profiles.is_goldsrc(s.engine):entity_models.attach_reference(obj,pairs)
        # Refresh the binding after apply in case classname was intentionally edited.
        _,_,s.entity_editor_binding=_entity_property_target(obj)

class WL_OT_read_face_texture(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.read_face_texture';bl_label='Read Selected Face Texture'
    def run(self,context):
        s=context.scene.wavelength;obj=context.object
        if not obj or obj.get('wl_role')!='BRUSH':raise ValueError('Select a brush')
        edit=obj.mode=='EDIT'
        if edit:bpy.ops.object.mode_set(mode='OBJECT')
        try:
            selected=[p for p in obj.data.polygons if p.select]
            if not selected:raise ValueError('Select a face in Edit Mode')
            polygon=selected[0];attr=obj.data.attributes.get('wl_face_id')
            if attr is None:raise ValueError('Brush has no face IDs')
            fid=attr.data[polygon.index].value
            records=json.loads(obj.data.get('wl_faces','{}'));record=records.get(str(fid))
            if record is None:
                faces=scene.brush_from_object(obj,s.engine)
                by_id={datum.value:face for datum,face in zip(sorted(attr.data,key=lambda d:d.value),faces)}
                face=by_id[fid];texture=face.texture;projection=face.projection
            else:
                texture=record.get('texture','');projection=record.get('projection',[0,0,0,1,1])
            if len(projection)!=5:raise ValueError('Invalid face texture projection')
            s.texture=str(texture);s.shift_u=float(projection[0]);s.shift_v=float(projection[1])
            s.texture_rotation=float(projection[2]);s.texture_scale_u=float(projection[3]);s.texture_scale_v=float(projection[4])
        finally:
            if edit:bpy.ops.object.mode_set(mode='EDIT')

class WL_OT_texture(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.apply_texture';bl_label='Apply Face Texture';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        s=context.scene.wavelength;obj=context.object
        if not obj or obj.get('wl_role')!='BRUSH':raise ValueError('Select a brush')
        # Edit mode synchronizes selected faces before writing metadata.
        if not str(s.texture or '').strip():raise ValueError('Choose an engine texture before applying')
        if profiles.is_source(s.engine):
            from . import source_assets
            mat=source_assets.material(s,s.texture)
        else:mat=textures.material(s,s.texture)
        edit=obj.mode=='EDIT'
        if edit:bpy.ops.object.mode_set(mode='OBJECT')
        try:
            faces=scene.brush_from_object(obj,s.engine);attr=obj.data.attributes['wl_face_id']
            by_id={datum.value:face for datum,face in zip(sorted(attr.data,key=lambda d:d.value),faces)}
            records=json.loads(obj.data.get('wl_faces','{}'))
            from dataclasses import asdict
            from .geometry import validate
            planes=validate([tuple(x/obj.get('wl_unit_meters',1.0) for x in (obj.matrix_world@v.co)) for v in obj.data.vertices],[list(p.vertices) for p in obj.data.polygons])
            selected=[]
            for index,polygon in enumerate(obj.data.polygons):
                if edit and not polygon.select:continue
                selected.append(index)
                fid=attr.data[index].value;face=by_id[fid];face.texture=s.texture
                face.projection=[s.shift_u,s.shift_v,s.texture_rotation,s.texture_scale_u,s.texture_scale_v]
                if profiles.uses_valve_axes(s.engine):face.axes=formats.quake_axes(planes[index][1],face.projection)
                records[str(fid)]=asdict(face)
            obj.data['wl_faces']=json.dumps(records)
            if mat:textures.assign(obj,selected,mat)
            from .editor import apply_uv
            apply_uv(obj,s.engine)
        finally:
            if edit:bpy.ops.object.mode_set(mode='EDIT')

class WL_OT_import(SafeOperator,bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.import_map';bl_label='Import MAP';bl_options={'REGISTER','UNDO'}
    filename_ext='.map';filter_glob:StringProperty(default='*.map;*.vmf',options={'HIDDEN'})
    def run(self,context):
        path=Path(self.filepath)
        if path.stat().st_size>formats.MAX_BYTES:raise ValueError('MAP exceeds 16 MiB limit')
        from . import vmf
        is_vmf=path.suffix.lower()=='.vmf'
        document=(vmf.parse if is_vmf else formats.parse)(path.read_text(encoding='utf-8-sig'))
        # Import into a fresh scene to avoid replacing existing world metadata.
        if any(o.get('wl_role') for o in context.scene.objects):raise ValueError('Import into an empty wavelength scene')
        scene.import_map(context.scene,document);s=context.scene.wavelength;s.map_path=self.filepath
        if is_vmf:
            if not profiles.is_source(s.engine):s.engine='source_hl2_windows' if os.name=='nt' else 'source_hl2_linux'
        elif any(f.axes for e in document.entities for b in e.brushes for f in b):s.engine='goldsrc'
        s.status='MAP imported; comments/formatting are normalized on export'

class WL_OT_export(SafeOperator,bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.export_map';bl_label='Export MAP';filename_ext='.map'
    filter_glob:StringProperty(default='*.map;*.vmf',options={'HIDDEN'})
    def invoke(self,context,event):
        self.filename_ext='.vmf' if profiles.is_source(context.scene.wavelength.engine) else '.map'
        self.filepath=str(Path(bpy.path.abspath(context.scene.wavelength.project_dir or '//'))/(context.scene.wavelength.map_name+self.filename_ext))
        return ExportHelper.invoke(self,context,event)
    def run(self,context):
        if context.scene.wavelength.engine=='blender':raise ValueError('Select an engine before exporting MAP')
        from . import vmf
        source=profiles.is_source(context.scene.wavelength.engine)
        if source and Path(self.filepath).suffix.lower()!='.vmf':raise ValueError('Choose a .vmf filename for Source 1')
        text=(vmf.write if source else formats.write)(scene.export_map(context.scene));Path(self.filepath).write_text(text);context.scene.wavelength.map_path=self.filepath
        context.scene.wavelength.status='VMF exported' if source else 'MAP exported'

class WL_OT_validate(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.validate';bl_label='Validate Map'
    def run(self,context):
        s=context.scene.wavelength;diagnostics=scene.validate_scene(context.scene);s.diagnostics=json.dumps(diagnostics)
        s.status=f'{len(diagnostics)} diagnostics' if diagnostics else 'Validation passed'


def redraw_build():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type=='VIEW_3D':area.tag_redraw()

def build_tick():
    global _JOB
    if _JOB is None:return None
    try:
        s=_JOB_SCENE.wavelength;state=_JOB.poll();s.status=f'{state}: stage {_JOB.index}/{len(_JOB.commands)}'
        if state in {'FAILED','CANCELLED'}:
            s.status=_JOB.message
            if state=='FAILED':
                errors=[]
                for file in sorted(_JOB_PATH.glob('*.log')):
                    errors.extend(line.strip() for line in file.read_text(errors='replace').splitlines() if 'error' in line.lower())
                s.build_error='\n'.join(dict.fromkeys(errors)) or _JOB.message
                s.status='Build failed — see error below'
            _JOB=None;return None
        if state=='DONE':
            output=_JOB_PATH/(_JOB_MAP_NAME+'.bsp')
            if not output.exists():raise ValueError('Compiler returned success without a BSP')
            data=output.read_bytes()
            if profiles.is_source(_JOB_ENGINE):
                from .source_tools import validate_bsp
                validate_bsp(data)
            elif len(data)<124 or struct.unpack_from('<i',data)[0]!=profiles.PROFILES[_JOB_ENGINE]['bsp_version']:raise ValueError('Unexpected BSP version')
            from .build.pipeline import publish_bsp
            published=publish_bsp(output,_JOB_OUTPUT) if _JOB_OUTPUT else output
            s.last_build=str(published)
            if profiles.is_source(_JOB_ENGINE):s.map_name=_JOB_MAP_NAME
            s.status=f'Build complete: {published.name}';_JOB=None;return None
        return 0.1
    except Exception as exc:
        if _JOB:_JOB.cancel()
        if _JOB_SCENE:
            _JOB_SCENE.wavelength.status='Build failed'
            _JOB_SCENE.wavelength.build_error=str(exc)
        _JOB=None;return None
    finally:
        redraw_build()

class WL_OT_build(SafeOperator,bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.build';bl_label='Build Map'
    filename_ext='.bsp'
    filter_glob:StringProperty(default='*.bsp',options={'HIDDEN'})
    def invoke(self,context,event):
        s=context.scene.wavelength
        self.filepath=s.build_output or str(Path(bpy.path.abspath(s.project_dir or '//'))/(s.map_name+'.bsp'))
        return ExportHelper.invoke(self,context,event)
    def run(self,context):
        global _JOB,_JOB_SCENE,_JOB_PATH,_JOB_ENGINE,_JOB_OUTPUT,_JOB_MAP_NAME
        if _JOB:raise ValueError('A build is already running')
        s=context.scene.wavelength
        if s.engine=='blender':raise ValueError('Select an engine before building')
        s.last_build='';s.build_error=''
        requested=self.filepath or s.build_output
        destination=Path(bpy.path.abspath(requested)).resolve() if requested else None
        if destination:
            if destination.suffix.lower()!='.bsp':raise ValueError('Build output must have a .bsp extension')
            if destination.is_dir():raise ValueError('Choose a BSP filename, not a directory')
            s.build_output=str(destination)
        map_stem=(destination.stem if destination else s.map_name) if profiles.is_source(s.engine) else 'level'
        if profiles.is_source(s.engine):
            from .source_tools import compiler_args
            compiler_args('vbsp',bpy.path.abspath(s.game_dir),map_stem)
        document=scene.export_map(context.scene)
        if not s.project_dir:raise ValueError('Configure a project directory')
        if s.engine!='quake' and not s.compiler_dir:raise ValueError('Configure the compiler directory')
        root=Path(bpy.path.abspath(s.project_dir));root.mkdir(parents=True,exist_ok=True)
        work=Path(tempfile.mkdtemp(prefix='build-',dir=root))
        _JOB_PATH=work;s.build_log_dir=str(work)
        if profiles.is_source(s.engine):
            from . import vmf
            (work/(map_stem+'.vmf')).write_text(vmf.write(document))
        else:
            if textures.sources(s):textures.build_wad(s,document,work,context.scene.objects)
            (work/'level.map').write_text(formats.write(document))
        wrapper=json.loads(s.wrapper);environment=json.loads(s.environment)
        if not isinstance(wrapper,list) or not all(isinstance(x,str) for x in wrapper):raise ValueError('Wrapper must be an argument array')
        if not isinstance(environment,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in environment.items()):raise ValueError('Environment must map strings to strings')
        commands=[]
        quake_paths={'qbsp':s.qbsp_path,'vis':s.vis_path,'light':s.light_path}
        quake_args={'qbsp':s.qbsp_args,'vis':s.vis_args,'light':s.light_args}
        for stage in profiles.PROFILES[s.engine]['stages']:
            from .build.toolchains import resolve_compiler
            if s.engine=='quake' and quake_paths.get(stage):
                exe=Path(bpy.path.abspath(quake_paths[stage]))
                if not exe.is_file():raise ValueError(f'{stage.upper()} does not exist: {exe}')
                if exe.suffix.lower()=='.exe' and os.name!='nt' and not wrapper:raise ValueError(f'{exe.name} is a Windows compiler. Configure a wrapper or use a native executable.')
                if exe.suffix.lower()!='.exe' and not wrapper and not os.access(exe,os.X_OK):raise ValueError(f'{stage.upper()} is not executable: {exe}')
            else:
                if not s.compiler_dir:raise ValueError(f'Configure {stage.upper()} or the compiler directory')
                exe=resolve_compiler(bpy.path.abspath(s.compiler_dir),stage,bool(wrapper))
            args=['level.map'] if stage in {'qbsp','hlcsg'} else ['level.bsp']
            if s.engine=='quake':
                try: extra=json.loads(quake_args.get(stage) or '[]')
                except Exception as exc: raise ValueError(f'{stage.upper()} arguments must be a JSON array') from exc
                if not isinstance(extra,list) or not all(isinstance(x,str) for x in extra):raise ValueError(f'{stage.upper()} arguments must be a JSON string array')
                args=[*extra,*args]
            if profiles.is_source(s.engine):
                from .source_tools import compiler_args
                args=compiler_args(stage,bpy.path.abspath(s.game_dir),map_stem)
                if exe.suffix.lower()=='.exe' and os.name!='nt':
                    args[1]='Z:'+args[1].replace('/',chr(92))
                extra=json.loads(getattr(s,'source_'+stage+'_args') or '[]')
                if not isinstance(extra,list) or not all(isinstance(v,str) for v in extra):raise ValueError(stage.upper()+' arguments must be a JSON string array')
                if '++' in exe.name and stage=='vbsp' and '-singleplayer' not in extra:extra=['-singleplayer',*extra]
                args=[*extra,*args]
            if stage=='hlcsg':args.insert(0,'-nowadtextures')
            commands.append([*wrapper,str(exe),*args])
        _JOB=Pipeline(commands,work,s.timeout,dict(os.environ,**environment));_JOB_SCENE=context.scene;_JOB_PATH=work;_JOB_ENGINE=s.engine;_JOB_OUTPUT=destination;_JOB_MAP_NAME=map_stem
        s.status='Build started';bpy.app.timers.register(build_tick,first_interval=0.1)

class WL_OT_cancel(bpy.types.Operator):
    bl_idname='wavelength.cancel_build';bl_label='Cancel Build'
    def execute(self,context):
        if _JOB:_JOB.cancel()
        return {'FINISHED'}

class WL_OT_logs(bpy.types.Operator):
    bl_idname='wavelength.build_logs';bl_label='Load Build Log'
    def execute(self,context):
        directory=context.scene.wavelength.build_log_dir
        log_path=Path(directory) if directory else _JOB_PATH
        if log_path:
            text=bpy.data.texts.get('wavelength Build Log') or bpy.data.texts.new('wavelength Build Log');text.clear()
            for file in sorted(log_path.glob('*.log')):text.write(file.name+'\n'+file.read_text(errors='replace')+'\n')
            context.scene.wavelength.status='Log available in Text Editor: wavelength Build Log'
        return {'FINISHED'}

class WL_OT_launch(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.launch';bl_label='Launch Game'
    def run(self,context):
        s=context.scene.wavelength
        if not s.last_build or not Path(s.last_build).is_file():raise ValueError('Build successfully before launching')
        if not s.map_name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in s.map_name):raise ValueError('Use lowercase letters, numbers, underscores or hyphens for map name')
        steam_profile=profiles.get(s.engine).get('launch_method')=='steam'
        directory=Path(bpy.path.abspath(s.game_dir))
        if profiles.is_source(s.engine):
            from .source_tools import runtime_game
            directory=runtime_game(directory)
        if not directory.is_dir():raise ValueError('Configure an existing game directory')
        if steam_profile:
            import shutil as _shutil
            steam_exe=_shutil.which('steam')
            if not steam_exe:raise ValueError('Steam launcher not found on PATH; install Steam or make the steam command available')
        else:
            exe=Path(bpy.path.abspath(s.game_executable))
            if not exe.is_file():raise ValueError('Configure an existing game executable')
        if profiles.is_source(s.engine):s.map_name=Path(s.last_build).stem
        arguments=json.loads(s.launch_args)
        if not isinstance(arguments,list) or not all(isinstance(x,str) for x in arguments):raise ValueError('Launch arguments must be an array')
        if profiles.is_source(s.engine) and '-game' in arguments:
            at=arguments.index('-game')
            if at+1<len(arguments):arguments[at+1]=str(directory)
        args=[x.replace('{map}',s.map_name).replace('{game_dir}',str(directory)).replace('{build_dir}',str(Path(s.last_build).parent)) for x in arguments]
        destination=directory/'maps';destination.mkdir(exist_ok=True)
        target=destination/(s.map_name+'.bsp')
        if Path(s.last_build).resolve()!=target.resolve():shutil.copyfile(s.last_build,target)
        if steam_profile:
            # Steam supplies its own runtime; do not start hl_linux directly.
            # Use the game directory only for copying the compiled BSP.
            # Steam HL1 uses the default valve game directory unless the user
            # explicitly configures a different -game option.
            if args==['-game',str(directory),'+map',s.map_name]:
                args=['-console','-dev','+map',s.map_name]
            appid=profiles.get(s.engine)['steam_app_id']
            subprocess.Popen([steam_exe,'-applaunch',appid,*args],start_new_session=True)
            s.status=f'Launch requested through Steam (App ID {appid})'
        else:
            subprocess.Popen([str(exe),*args],cwd=exe.parent,start_new_session=True)
            s.status='Game launched'

class WL_OT_leak(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.show_leak';bl_label='Show Leak Path';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        if not _JOB_PATH:raise ValueError('Run a build first')
        paths=list(_JOB_PATH.glob('*.pts'))+list(_JOB_PATH.glob('*.lin'))
        if not paths:raise ValueError('No compiler pointfile found')
        points=[]
        for line in paths[0].read_text().splitlines():
            values=line.split()
            if len(values)==3:points.append(tuple(float(x) for x in values))
        if not points:raise ValueError('Empty pointfile')
        curve=bpy.data.curves.new('Leak Path','CURVE');curve.dimensions='3D';curve.bevel_depth=0.5
        spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
        for point,values in zip(spline.points,points):point.co=(*values,1)
        obj=bpy.data.objects.new('Leak Path',curve);context.collection.objects.link(obj);obj.show_in_front=True;obj['wl_exclude']=True

class WL_PT_main(bpy.types.Panel):
    bl_label='wavelength';bl_idname='WL_PT_main';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    def draw(self,context):
        s=context.scene.wavelength;l=self.layout;l.use_property_split=True
        if not workspace.draw_controls(l,context):return
        l.prop(s,'engine');l.label(text=s.status[:65],icon='INFO')
        box=l.box();box.label(text='Grid & Units',icon='GRID');box.prop(s,'grid_mode',expand=True)
        row=box.row(align=True);row.enabled=s.engine!='blender' and s.grid_mode=='ENGINE';row.operator('wavelength.grid_step',text='−').direction=-1;row.prop(s,'grid_step',text='');row.operator('wavelength.grid_step',text='+').direction=1
        box.label(text=('Blender units / native grid' if s.engine=='blender' else '1 engine unit ≈ 2.54 cm'));box.operator('wavelength.snap_grid')
        row=l.row(align=True)
        for kind in ('STAIRS','ARCH','SPHERE'):row.operator('wavelength.primitive',text=kind.title()).kind=kind
        l.operator('wavelength.index_assets',text='Publish to Native Asset Browser',icon='ASSET_MANAGER')
        box=l.box();box.label(text='Create & Edit',icon='MESH_CUBE');box.enabled=s.engine!='blender';box.prop(s,'brush_type');box.prop(s,'brush_size');box.prop(s,'brush_height_steps');
        if s.brush_type in {'CYLINDER','CONE','SPHERE'}: box.prop(s,'brush_sides')
        if s.brush_type=='SPHERE': box.prop(s,'brush_rings')
        if s.brush_type=='ARCH': box.prop(s,'arch_segments');box.prop(s,'arch_angle');box.prop(s,'arch_thickness_steps')
        row=box.row(align=True);row.operator('wavelength.add_brush');row.operator('wavelength.mark_brush',text='Use Mesh')
        row=box.row(align=True);row.prop(s,'hollow_thickness');row.operator('wavelength.make_hollow',text='Make Hollow')
        box.label(text='Entities',icon='EMPTY_ARROWS');box.prop(s,'entity_choice',text='Class');row=box.row(align=True);row.operator('wavelength.add_entity',text='Create Point Entity',icon='ADD');row.operator('wavelength.brush_entity',text='Make Brush Entity')
        row=box.row(align=True);row.operator('wavelength.entity_browser',text='Wavelength Asset Browser',icon='ASSET_MANAGER');row.operator('wavelength.entity_browser_refresh',text='',icon='FILE_REFRESH')
        active=context.object
        if active and active.get('wl_role')=='BRUSH' and active.get('wl_entity_id'):
            entity_box=box.box();pairs=dict(json.loads(active.get('wl_entity_pairs','[]')));members=_brush_entity_members(context.scene,active.get('wl_entity_id'))
            entity_box.label(text=f"Brush Entity: {pairs.get('classname','<missing>')} ({len(members)} solids)",icon='OUTLINER_OB_MESH')
            row=entity_box.row(align=True);row.operator('wavelength.brush_entity_add',text='Add Selected');row.operator('wavelength.brush_entity_remove',text='Remove Selected')
            entity_box.operator('wavelength.brush_entity_to_world',text='Convert Entire Entity to World')
        box=l.box();box.enabled=s.engine!='blender';box.label(text='Brush Tools',icon='MOD_BOOLEAN');box.prop(s,'clip_axis',expand=True);box.prop(s,'clip_distance');box.prop(s,'clip_flip');box.operator('wavelength.clip')
        box.operator('wavelength.duplicate_assembly');box.operator('wavelength.bake_static')
        box=l.box();box.enabled=s.engine!='blender';box.label(text='Map Workflow',icon='FILE_FOLDER');row=box.row(align=True);row.operator('wavelength.import_map');row.operator('wavelength.export_map')
        row=box.row(align=True);row.operator('wavelength.validate');row.operator('wavelength.build')
        box.prop(s,'build_output')
        if s.build_error:
            import textwrap
            error=box.box();error.alert=True;error.label(text='Build failed',icon='ERROR')
            for line in s.build_error.splitlines():
                for part in textwrap.wrap(line,width=max(24,int(context.region.width/7)-8)):
                    error.label(text=part)
        if s.build_log_dir:
            box.prop(s,'build_log_dir');box.operator('wavelength.build_logs')
        row=box.row(align=True);row.operator('wavelength.launch');row.operator('wavelength.cancel_build',text='Cancel')


class WL_OT_system_select(bpy.types.Operator):
    bl_idname='wavelength.system_select';bl_label='Select System Object'
    object_name:StringProperty()
    extend:BoolProperty(default=False)
    def execute(self,context):
        obj=context.scene.objects.get(self.object_name)
        if obj is None:return {'CANCELLED'}
        if not self.extend:
            for old in context.selected_objects:old.select_set(False)
        try:obj.hide_set(False)
        except Exception:pass
        obj.select_set(True);context.view_layer.objects.active=obj
        return {'FINISHED'}

class WL_OT_system_select_category(bpy.types.Operator):
    bl_idname='wavelength.system_select_category';bl_label='Select System Category'
    category:StringProperty()
    def execute(self,context):
        objects=system_tree.groups(context.scene).get(self.category,[])
        for old in context.selected_objects:old.select_set(False)
        active=None
        for obj in objects:
            try:obj.hide_set(False)
            except Exception:pass
            try:obj.select_set(True);active=active or obj
            except RuntimeError:pass
        if active:context.view_layer.objects.active=active
        return {'FINISHED'}

class WL_OT_system_visibility(bpy.types.Operator):
    bl_idname='wavelength.system_visibility';bl_label='Toggle System Object Visibility'
    object_name:StringProperty()
    def execute(self,context):
        obj=context.scene.objects.get(self.object_name)
        if obj is None:return {'CANCELLED'}
        key=system_tree.category(obj,context.scene.wavelength.engine)
        hidden=system_tree.object_hidden(obj,context.view_layer)
        if hidden and key and system_tree.category_explicitly_hidden(context.scene,key):
            # Revealing one member of an explicitly hidden category means the
            # user reopened the category: reveal every member.
            system_tree.set_category_hidden(context.scene,key,False,context.view_layer)
        else:
            system_tree.set_object_hidden(obj,not hidden,context.view_layer)
        return {'FINISHED'}

class WL_OT_system_category_visibility(bpy.types.Operator):
    bl_idname='wavelength.system_category_visibility';bl_label='Toggle System Category Visibility'
    category:StringProperty()
    def execute(self,context):
        explicit=system_tree.category_explicitly_hidden(context.scene,self.category)
        # Clicking a visible/mixed category hides all; clicking an explicitly
        # hidden category reveals all.
        system_tree.set_category_hidden(context.scene,self.category,not explicit,context.view_layer)
        return {'FINISHED'}

class WL_PT_system_tree(bpy.types.Panel):
    bl_label='System Tree';bl_idname='WL_PT_system_tree';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        layout=self.layout;s=context.scene.wavelength
        if s.engine=='blender':
            layout.label(text='Choose an engine profile',icon='INFO');return
        grouped=system_tree.groups(context.scene)
        layout.label(text=f'{profiles.PROFILES[s.engine]["label"]} engine view',icon='OUTLINER')
        for key,label,icon in system_tree.CATEGORIES:
            objects=grouped[key]
            box=layout.box();head=box.row(align=True);head.label(text=f'{label} ({len(objects)})',icon=icon)
            state=system_tree.category_visibility(context.scene,key,context.view_layer)
            explicit=system_tree.category_explicitly_hidden(context.scene,key)
            vis_icon='HIDE_ON' if explicit else ('REMOVE' if state=='MIXED' else 'HIDE_OFF')
            op=head.operator('wavelength.system_category_visibility',text='',icon=vis_icon);op.category=key
            op=head.operator('wavelength.system_select_category',text='',icon='RESTRICT_SELECT_OFF');op.category=key
            for obj in objects:
                row=box.row(align=True);op=row.operator('wavelength.system_select',text=obj.name,icon='OBJECT_DATA');op.object_name=obj.name
                cls=system_tree.classname(obj)
                if cls:row.label(text=cls)
                hidden=system_tree.object_hidden(obj,context.view_layer)
                op=row.operator('wavelength.system_visibility',text='',icon='HIDE_ON' if hidden else 'HIDE_OFF');op.object_name=obj.name

class WL_PT_project(bpy.types.Panel):
    bl_label='Project & Tools';bl_idname='WL_PT_project';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength;l.use_property_split=True
        l.operator('wavelength.setup')
        row=l.row(align=True);row.operator('wavelength.save_project');row.operator('wavelength.load_project')
        l.prop(s,'project_dir');l.prop(s,'map_name')
        if profiles.is_source(s.engine):
            for field in ('source_vbsp_args','source_vvis_args','source_vrad_args'):l.prop(s,field)
        if s.engine=='quake':
            l.label(text='Quake Runtime',icon='PLAY')
            l.prop(s,'game_executable');l.prop(s,'game_dir');l.prop(s,'quake_pak_dir')
            l.prop(s,'launch_args')
            l.label(text='Quake Compiler Toolchain',icon='TOOL_SETTINGS')
            l.prop(s,'qbsp_path');l.prop(s,'qbsp_args')
            l.prop(s,'vis_path');l.prop(s,'vis_args')
            l.prop(s,'light_path');l.prop(s,'light_args')
            l.prop(s,'compiler_dir')
            l.label(text='Texture WADs are managed under Face Textures.',icon='TEXTURE')
        else:
            for name in ('compiler_dir','wad_path','game_executable','game_dir','launch_args'):l.prop(s,name)
        for name in ('fgd_path','wrapper','environment','timeout'):l.prop(s,name)


class WL_PT_worldspawn(bpy.types.Panel):
    bl_label='Worldspawn';bl_idname='WL_PT_worldspawn';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength;l.prop(s,'worldspawn_json');l.operator('wavelength.worldspawn')
        l.label(text='classname is always worldspawn')

class WL_PT_relationships(bpy.types.Panel):
    bl_label='Entity Relationships';bl_idname='WL_PT_relationships';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;row=l.row(align=True);a=row.operator('wavelength.select_target',text='Select Targets');a.direction='TARGET';a=row.operator('wavelength.select_target',text='Select Sources');a.direction='SOURCE'

class WL_PT_entity(bpy.types.Panel):
    bl_label='Entity Properties';bl_idname='WL_PT_entity';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength
        key,pairs,binding=_entity_property_target(context.object)
        if key is None:
            l.label(text='Select a point entity or brush entity',icon='INFO');return
        classname=dict(pairs).get('classname','<missing>')
        l.label(text=f'Editing: {classname}',icon='OUTLINER_OB_EMPTY' if key=='wl_pairs' else 'OUTLINER_OB_MESH')
        bound=s.entity_editor_binding==binding
        if not bound:
            l.label(text='Selection differs from loaded properties',icon='ERROR')
        l.operator('wavelength.entity_properties',text='Read This Entity',icon='FILE_REFRESH').apply=False
        fields=l.column();fields.enabled=bound
        for index,item in enumerate(s.fields):
            row=fields.row(align=True);display=item.label or item.key;row.label(text=f'{display} [{item.key}]' if display!=item.key else item.key)
            if item.kind=='choices' and item.choices!='[]':row.prop(item,'choice',text='')
            else:row.prop(item,'integer' if item.kind in {'integer','flags'} else 'number' if item.kind=='float' else 'value',text='')
            row.operator('wavelength.property_remove',text='',icon='X').index=index
            if item.choices!='[]' and item.kind=='flags':
                choices=json.loads(item.choices)
                flagrow=fields.row(align=True)
                for choice in choices[:8]:
                    try:mask=int(choice[0])
                    except (ValueError,TypeError):continue
                    op=flagrow.operator('wavelength.flag_toggle',text=str(choice[1]),depress=bool(item.integer & mask));op.field_index=index;op.mask=mask
        row=fields.row(align=True);row.operator_menu_enum('wavelength.property_add','property_key',text='Add Property',icon='ADD');row.operator('wavelength.property_custom_add',text='Custom Key…')
        apply=fields.operator('wavelength.entity_properties',text='Apply to This Entity',icon='CHECKMARK');apply.apply=True

class WL_PT_texture(bpy.types.Panel):
    bl_label='Face Textures';bl_idname='WL_PT_texture';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength
        if profiles.is_source(s.engine):
            l.label(text='Source material path (without materials/ or .vmt)')
            l.operator('wavelength.index_assets',text='Publish Materials to Asset Browser',icon='ASSET_MANAGER').category='MATERIAL'
            l.operator('wavelength.resolve_textures');l.operator('wavelength.preview_textures')
            for name in ('texture','shift_u','shift_v','texture_rotation','texture_scale_u','texture_scale_v'):l.prop(s,name)
            l.operator('wavelength.apply_texture');l.prop(s,'live_texture_reproject')
            return
        l.prop(s,'wad_path');row=l.row(align=True);row.operator('wavelength.add_wad',text='Add WAD',icon='FILE_FOLDER');row.operator('wavelength.refresh_textures',text='Reload',icon='FILE_REFRESH')
        for path in json.loads(s.texture_wads):
            row=l.row(align=True);op=row.operator('wavelength.select_wad',text=Path(path).name);op.filepath=path
            op=row.operator('wavelength.remove_wad',text='',icon='X');op.filepath=path
        if s.engine=='quake':
            l.prop(s,'palette_path');l.prop(s,'quake_pak_dir');l.operator('wavelength.quake_textures')
        l.operator('wavelength.index_assets',text='Publish Materials to Asset Browser',icon='ASSET_MANAGER').category='MATERIAL'
        l.operator('wavelength.resolve_textures');l.operator('wavelength.preview_textures')
        l.prop(s,'live_texture_reproject')
        l.use_property_split=True
        for name in ('texture','shift_u','shift_v','texture_rotation','texture_scale_u','texture_scale_v'):l.prop(s,name)
        row=l.row(align=True);row.operator('wavelength.read_face_texture',text='Read Selected Face',icon='EYEDROPPER');row.operator('wavelength.apply_texture',text='Apply to Selected')
        row=l.row(align=True)
        for action,label in [('RESET','Reset'),('ROT90','+90°'),('FLIP_U','Flip U'),('FLIP_V','Flip V')]:
            op=row.operator('wavelength.texture_nudge',text=label);op.action=action
        l.operator('wavelength.select_by_texture',text='Select Brushes Using Texture')


class WL_OT_validate_alpha(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.validate_alpha';bl_label='Run Map Problems';bl_options={'REGISTER'}
    def run(self,context):
        from . import validation
        items=validation.validate(context.scene)
        # retain format/export validation too
        items.extend(scene.validate_scene(context.scene))
        seen=set();unique=[]
        for d in items:
            key=(d.get('code'),d.get('message'),d.get('object'))
            if key not in seen:seen.add(key);unique.append(d)
        context.scene.wavelength.diagnostics=json.dumps(unique);context.scene.wavelength.status=f'{len(unique)} map problem(s)'

class WL_OT_select_problem(bpy.types.Operator):
    bl_idname='wavelength.select_problem';bl_label='Select Problem Object'
    object_name:StringProperty()
    def execute(self,context):
        obj=bpy.data.objects.get(self.object_name)
        if obj:
            bpy.ops.object.mode_set(mode='OBJECT') if context.object and context.object.mode!='OBJECT' else None
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);context.view_layer.objects.active=obj
        return {'FINISHED'}

class WL_OT_worldspawn(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.worldspawn';bl_label='Apply Worldspawn';bl_options={'UNDO'}
    def run(self,context):
        pairs=json.loads(context.scene.wavelength.worldspawn_json or '[]')
        pairs=[(str(k),str(v)) for k,v in pairs if str(k)!='classname']
        context.scene['wl_world_pairs']=json.dumps([('classname','worldspawn'),*pairs])

class WL_OT_texture_nudge(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.texture_nudge';bl_label='Texture Mapping Tool';bl_options={'UNDO'}
    action:StringProperty()
    def run(self,context):
        s=context.scene.wavelength
        if self.action=='RESET':s.shift_u=s.shift_v=s.texture_rotation=0;s.texture_scale_u=s.texture_scale_v=1
        elif self.action=='ROT90':s.texture_rotation=(s.texture_rotation+90)%360
        elif self.action=='FLIP_U':s.texture_scale_u=-s.texture_scale_u
        elif self.action=='FLIP_V':s.texture_scale_v=-s.texture_scale_v
        elif self.action=='JUSTIFY_U':s.shift_u=0
        elif self.action=='JUSTIFY_V':s.shift_v=0
        bpy.ops.wavelength.apply_texture()

class WL_OT_select_by_texture(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.select_by_texture';bl_label='Select Brushes Using Texture'
    def run(self,context):
        needle=context.scene.wavelength.texture.casefold();bpy.ops.object.mode_set(mode='OBJECT') if context.object and context.object.mode!='OBJECT' else None
        bpy.ops.object.select_all(action='DESELECT')
        for obj in context.scene.objects:
            if obj.get('wl_role')=='BRUSH' and needle in system_tree.brush_textures(obj):obj.select_set(True)

class WL_OT_select_target(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.select_target';bl_label='Select Target Relationships'
    direction:EnumProperty(items=[('TARGET','Targets',''),('SOURCE','Sources','')],default='TARGET')
    def run(self,context):
        active=context.active_object
        if not active:raise ValueError('Select an entity')
        pairs=dict(json.loads(active.get('wl_pairs',active.get('wl_entity_pairs','[]'))));key=pairs.get('target' if self.direction=='TARGET' else 'targetname','')
        if not key:raise ValueError('Selected entity has no matching target field')
        bpy.ops.object.select_all(action='DESELECT')
        for obj in context.scene.objects:
            vals=dict(json.loads(obj.get('wl_pairs',obj.get('wl_entity_pairs','[]'))))
            if vals.get('targetname' if self.direction=='TARGET' else 'target')==key:obj.select_set(True)

class WL_PT_diagnostics(bpy.types.Panel):
    bl_label='Diagnostics';bl_idname='WL_PT_diagnostics';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;row=l.row(align=True);row.operator('wavelength.validate_alpha',text='Map Problems',icon='CHECKMARK');row.operator('wavelength.repair_ids',text='Repair IDs');l.operator('wavelength.build_logs');l.operator('wavelength.show_leak')
        for diagnostic in json.loads(context.scene.wavelength.diagnostics):
            box=l.box();box.label(text=diagnostic['code'],icon='ERROR');box.label(text=diagnostic['message'][:65]);
            if diagnostic.get('object'):
                op=box.operator('wavelength.select_problem',text=diagnostic['object'],icon='RESTRICT_SELECT_OFF');op.object_name=diagnostic['object']

def _entity_definitions(context, pairs):
    """Resolved entity properties: project FGD first, stock GoldSrc fallback second."""
    s=context.scene.wavelength;classname=dict(pairs).get('classname','');primary=[]
    if s.fgd_path:
        try:
            from .entity import fgd
            primary=fgd.properties(fgd.load(bpy.path.abspath(s.fgd_path)),classname)
        except (ValueError,OSError,RuntimeError,KeyError,TypeError):
            primary=[]
    if profiles.is_goldsrc(s.engine):
        from .entity import goldsrc as goldsrc_entities
        return goldsrc_entities.merge_properties(classname,primary)
    return primary

def _available_entity_property_items(self,context):
    if context is None or getattr(context,'scene',None) is None:return [('__NONE__','No engine properties available','Load an FGD/entity definition first')]
    s=context.scene.wavelength
    present={item.key for item in s.fields}
    result=[]
    obj=context.object
    key,pairs,binding=_entity_property_target(obj)
    if key is not None and binding==s.entity_editor_binding:
        for prop in _entity_definitions(context,pairs):
            prop_key=str(prop.get('key',''))
            if prop_key and prop_key not in present:
                label=str(prop.get('label') or prop_key)
                result.append((prop_key,label,f'{prop_key} ({prop.get("type","string")})'))
    result.sort(key=lambda item:item[1].casefold())
    return result or [('__NONE__','No additional engine properties','All known properties are already present')]

class WL_OT_property_add(bpy.types.Operator):
    bl_idname='wavelength.property_add';bl_label='Add Engine Property';bl_options={'REGISTER','UNDO'}
    property_key:EnumProperty(name='Engine Property',items=_available_entity_property_items)
    def execute(self,context):
        s=context.scene.wavelength
        key=self.property_key.strip()
        if not key or key=='__NONE__':return {'CANCELLED'}
        if any(item.key==key for item in s.fields):self.report({'ERROR'},f'{key} is already present');return {'CANCELLED'}
        _,pairs,binding=_entity_property_target(context.object)
        if binding!=s.entity_editor_binding:self.report({'ERROR'},'Read this entity before adding properties');return {'CANCELLED'}
        definition={p['key']:p for p in _entity_definitions(context,pairs)}.get(key,{})
        item=s.fields.add();item.key=key;item.label=definition.get('label',key);item.kind=definition.get('type','string');item.choices=json.dumps(definition.get('choices',[]))
        default=str(definition.get('default',''));item.value=default
        if item.kind=='choices' and definition.get('choices'):
            codes={str(c[0]) for c in definition.get('choices',[]) if isinstance(c,(list,tuple)) and c}
            if default in codes:item.choice=default
        try:
            if item.kind in {'integer','flags'}:item.integer=int(default or 0)
            elif item.kind=='float':item.number=float(default or 0)
        except ValueError:item.kind='string'
        s.field_index=len(s.fields)-1
        return {'FINISHED'}

class WL_OT_property_custom_add(bpy.types.Operator):
    bl_idname='wavelength.property_custom_add';bl_label='Add Custom Engine Key';bl_options={'REGISTER','UNDO'}
    key:StringProperty(name='Key')
    def invoke(self,context,event):
        return context.window_manager.invoke_props_dialog(self,width=360)
    def draw(self,context):
        self.layout.prop(self,'key',text='Engine Key')
    def execute(self,context):
        s=context.scene.wavelength;key=self.key.strip()
        _,_,binding=_entity_property_target(context.object)
        if binding!=s.entity_editor_binding:self.report({'ERROR'},'Read this entity before adding properties');return {'CANCELLED'}
        if not key:self.report({'ERROR'},'Key cannot be empty');return {'CANCELLED'}
        if any(item.key==key for item in s.fields):self.report({'ERROR'},f'{key} is already present');return {'CANCELLED'}
        item=s.fields.add();item.key=key;item.label=key;item.kind='string';item.value='';s.field_index=len(s.fields)-1
        return {'FINISHED'}

class WL_OT_property_remove(bpy.types.Operator):
    bl_idname='wavelength.property_remove';bl_label='Remove Property';bl_options={'UNDO'}
    index:IntProperty()
    def execute(self,context):context.scene.wavelength.fields.remove(self.index);return {'FINISHED'}

class WL_OT_clip(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.clip';bl_label='Clip Selected Brushes';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        from .editor import clipped_mesh,clip
        s=context.scene.wavelength;normal=[0.,0.,0.];normal['XYZ'.index(s.clip_axis)]=-1 if s.clip_flip else 1
        distance=s.clip_distance*(-1 if s.clip_flip else 1)
        objects=[o for o in context.selected_objects if o.get('wl_role')=='BRUSH']
        if not objects:raise ValueError('Select brushes to clip')
        for obj in objects:clipped_mesh(obj,normal,distance,s.engine)
        for obj in objects:clip(obj,normal,distance,s.engine)

class WL_OT_duplicate(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.duplicate_assembly';bl_label='Duplicate Assembly';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        selected=[o for o in context.selected_objects if o.get('wl_role')]
        suffix='_'+uuid.uuid4().hex[:8];mapping={};groups={}
        for obj in selected:
            for key,value in json.loads(obj.get('wl_pairs',obj.get('wl_entity_pairs','[]'))):
                if key=='targetname':mapping[value]=value+suffix
        for obj in selected:
            copy=obj.copy();copy['wl_id']=scene.uid()
            if obj.type=='MESH':copy.data=obj.data.copy()
            copy.location.x+=profiles.active_grid_step_meters(context.scene.wavelength)
            if obj.get('wl_entity_id'):copy['wl_entity_id']=groups.setdefault(obj['wl_entity_id'],scene.uid())
            for field in ('wl_pairs','wl_entity_pairs'):
                if obj.get(field):copy[field]=json.dumps([(k,mapping.get(v,v) if k in {'target','targetname','killtarget'} else v) for k,v in json.loads(obj[field])])
            context.collection.objects.link(copy)

class WL_OT_bake(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.bake_static';bl_label='Bake Current Poses to Copies';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        graph=context.evaluated_depsgraph_get()
        for obj in list(context.selected_objects):
            if obj.type!='MESH':continue
            copy=obj.copy();copy.data=obj.data.copy();copy.matrix_world=obj.evaluated_get(graph).matrix_world.copy()
            copy.animation_data_clear();copy['wl_id']=scene.uid();context.collection.objects.link(copy)
            for constraint in list(copy.constraints):copy.constraints.remove(constraint)
            if copy.rigid_body:
                with context.temp_override(object=copy,active_object=copy,selected_objects=[copy],selected_editable_objects=[copy]):bpy.ops.rigidbody.object_remove()
            copy.name=obj.name+' settled';obj['wl_exclude']=True

_PROJECT_FIELDS=('engine','unit_scale','asset_paths','profile_id','profile_name','grid_mode','grid_step','project_dir','build_output','map_name','compiler_dir','qbsp_path','vis_path','light_path','qbsp_args','vis_args','light_args','source_vbsp_args','source_vvis_args','source_vrad_args','game_executable','game_dir','wad_path','palette_path','quake_pak_dir','texture_wads','fgd_path','wrapper','environment','launch_args','timeout')
class WL_OT_save_project(SafeOperator,bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.save_project';bl_label='Save Project';filename_ext='.json'
    def run(self,context):
        data={k:getattr(context.scene.wavelength,k) for k in _PROJECT_FIELDS};data['schema_version']=1
        Path(self.filepath).write_text(json.dumps(data,indent=2)+'\n')
class WL_OT_load_project(SafeOperator,bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.load_project';bl_label='Load Project';filename_ext='.json'
    def run(self,context):
        data=json.loads(Path(self.filepath).read_text())
        if data.get('schema_version')!=1:raise ValueError('Unsupported project schema')
        if data.get('engine') not in profiles.PROFILES:raise ValueError('Unsupported engine')
        if data.get('grid_mode') not in {'BLENDER','ENGINE'} or data.get('grid_step') not in {str(2**i) for i in range(9)}:raise ValueError('Invalid grid settings')
        for k in _PROJECT_FIELDS:
            if k in data and not isinstance(data[k],(float,int) if k in {'timeout','unit_scale'} else str):raise ValueError(f'Invalid project field {k}')
        s=context.scene.wavelength
        for k in _PROJECT_FIELDS:
            if k in data:setattr(s,k,data[k])
        s.last_build='';textures.refresh(s,context);s.status='Project loaded'


class WL_OT_add_wad(SafeOperator,bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.add_wad';bl_label='Add Texture WAD';filename_ext='.wad'
    filter_glob:StringProperty(default='*.wad',options={'HIDDEN'})
    def run(self,context):
        wad=textures.library(self.filepath);s=context.scene.wavelength
        if wad.kind!=(b'WAD3' if profiles.is_goldsrc(s.engine) else b'WAD2'):raise ValueError('Choose a WAD for the active engine')
        paths=json.loads(s.texture_wads);path=str(wad.path)
        if path not in paths:paths.append(path)
        s.texture_wads=json.dumps(paths);s.texture_page=0;s.wad_path=path

class WL_OT_select_wad(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.select_wad';bl_label='Browse WAD'
    filepath:StringProperty()
    def run(self,context):context.scene.wavelength.texture_page=0;context.scene.wavelength.wad_path=self.filepath

class WL_OT_remove_wad(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.remove_wad';bl_label='Remove WAD Source'
    filepath:StringProperty()
    def run(self,context):
        s=context.scene.wavelength;paths=[p for p in json.loads(s.texture_wads) if p!=self.filepath];s.texture_wads=json.dumps(paths)
        if s.wad_path==self.filepath:s.wad_path=paths[0] if paths else ''

class WL_UL_texture_browser(bpy.types.UIList):
    bl_idname='WL_UL_texture_browser'
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        s=context.scene.wavelength
        try: icon_value=textures.preview_icon(s,item.name)
        except (ValueError,OSError,UnicodeError): icon_value=0
        layout.label(text=item.name,icon_value=icon_value)

class WL_UL_texture_gallery(bpy.types.UIList):
    bl_idname='WL_UL_texture_gallery'
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        # A UIList supplies Blender's native vertical scrollbar.  Each list item
        # is one catalogue row containing three genuinely large preview images.
        s=context.scene.wavelength
        # UIList needs a seven-unit row; cancel inherited scaling inside cards.
        layout.scale_y=1.0/7.0
        row=layout.row(align=False)
        for name in (item.name0,item.name1,item.name2):
            card=row.column(align=True)
            if not name:
                card.label(text='')
                continue
            try: icon_value=textures.preview_icon(s,name)
            except (ValueError,OSError,UnicodeError): icon_value=0
            preview=card.row(align=True)
            preview.alignment='CENTER'
            preview.template_icon(icon_value=icon_value,scale=5.5)
            pick=card.row(align=True)
            pick.alignment='CENTER'
            op=pick.operator('wavelength.texture_browser_pick',text=name)
            op.texture_name=name


def _texture_browser_search(self,context):
    self.items.clear()
    self.gallery_rows.clear()
    s=context.scene.wavelength
    try:names=textures.all_names(s,self.search)
    except (ValueError,OSError,UnicodeError):names=[]
    for name in names:self.items.add().name=name
    for base in range(0,len(names),3):
        r=self.gallery_rows.add()
        chunk=names[base:base+3]
        if len(chunk)>0:r.name0=chunk[0]
        if len(chunk)>1:r.name1=chunk[1]
        if len(chunk)>2:r.name2=chunk[2]
    self.active_index=min(self.active_index,max(0,len(self.items)-1))
    self.gallery_row_index=min(self.gallery_row_index,max(0,len(self.gallery_rows)-1))

class WL_OT_texture_browser_pick(bpy.types.Operator):
    bl_idname='wavelength.texture_browser_pick';bl_label='Select Texture';bl_options={'INTERNAL'}
    texture_name:StringProperty()
    def execute(self,context):
        context.scene.wavelength.texture=self.texture_name
        context.scene.wavelength.status=f'Selected texture {self.texture_name}'
        return {'FINISHED'}

class WL_OT_texture_browser(bpy.types.Operator):
    bl_idname='wavelength.texture_browser';bl_label='Texture Browser'
    search:StringProperty(name='Search',update=_texture_browser_search)
    view_mode:EnumProperty(name='View',items=[('GALLERY','Gallery','Texture catalogue','IMAGE_DATA',0),('LIST','List','Compact texture list','LINENUMBERS_ON',1)],default='GALLERY')
    items:CollectionProperty(type=WLTextureBrowserItem)
    gallery_rows:CollectionProperty(type=WLTextureGalleryRow)
    active_index:IntProperty(default=0,min=0)
    gallery_row_index:IntProperty(default=0,min=0)
    def invoke(self,context,event):
        self.search=''
        _texture_browser_search(self,context)
        current=context.scene.wavelength.texture
        for i,item in enumerate(self.items):
            if item.name==current:
                self.active_index=i
                self.gallery_row_index=i//3
                break
        return context.window_manager.invoke_props_dialog(self,width=760)
    def draw(self,context):
        col=self.layout.column()
        top=col.row(align=True)
        top.prop(self,'search',text='',icon='VIEWZOOM')
        top.prop(self,'view_mode',text='',expand=True)
        if self.view_mode=='GALLERY':
            # Real continuously scrollable catalogue: the UIList owns the native
            # scrollbar, while each row renders three large preview cards.
            gallery=col.column();gallery.scale_y=7.0
            gallery.template_list('WL_UL_texture_gallery','catalog',self,'gallery_rows',self,'gallery_row_index',rows=3,maxrows=3,type='DEFAULT')
            if context.scene.wavelength.texture:
                selected=col.row();selected.alignment='CENTER'
                selected.label(text=context.scene.wavelength.texture,icon='TEXTURE')
        else:
            col.template_list('WL_UL_texture_browser','list',self,'items',self,'active_index',rows=12,maxrows=12,type='DEFAULT')
        col.label(text=f'{len(self.items)} matching textures')
    def execute(self,context):
        if not self.items:return {'CANCELLED'}
        s=context.scene.wavelength
        if self.view_mode=='LIST':
            item=self.items[min(self.active_index,len(self.items)-1)]
            s.texture=item.name
        elif not s.texture and self.items:
            s.texture=self.items[0].name
        s.status=f'Selected texture {s.texture}'
        return {'FINISHED'}

class WL_OT_refresh_textures(bpy.types.Operator):
    bl_idname='wavelength.refresh_textures';bl_label='Refresh Texture Browser'
    def execute(self,context):textures.refresh(context.scene.wavelength,context);return {'FINISHED'}

class WL_OT_texture_page(bpy.types.Operator):
    bl_idname='wavelength.texture_page';bl_label='Texture Page'
    direction:IntProperty(default=1)
    def execute(self,context):
        s=context.scene.wavelength;s.texture_page=max(0,min(max(0,(s.texture_count-1)//textures.PAGE_SIZE),s.texture_page+self.direction));textures.refresh(s,context);return {'FINISHED'}

class WL_OT_quake_textures(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.quake_textures';bl_label='Create Local Quake Texture WAD'
    def run(self,context):
        from .wad import quake_library,write_wad
        s=context.scene.wavelength
        if s.engine!='quake':raise ValueError('Select Quake mode')
        folder=Path(bpy.path.abspath(s.quake_pak_dir));paks=sorted(p for p in folder.iterdir() if p.suffix.lower()=='.pak')
        if not paks:raise ValueError('No Quake PAK files found')
        items,palette,conflicts=quake_library(paks);cache=textures.cache_directory(s)
        path=cache/'quake-game.wad';path.write_bytes(write_wad(items));pal=cache/'palette.lmp';pal.write_bytes(palette)
        (cache/'quake-game-origin.json').write_text(json.dumps({'sources':[str(p) for p in paks],'textures':len(items),'conflicts_first_wins':conflicts,'distribution':'Private game-derived assets; do not distribute'},indent=2))
        s.palette_path=str(pal);paths=json.loads(s.texture_wads)
        if str(path) not in paths:paths.append(str(path))
        s.texture_wads=json.dumps(paths);s.texture_page=0;s.wad_path=str(path);s.status=f'{len(items)} local Quake textures ({conflicts} duplicate variants; first used)'

class WL_OT_resolve_textures(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.resolve_textures';bl_label='Load Map Texture Previews';bl_options={'REGISTER','UNDO'}
    def run(self,context):
        from .editor import apply_uv
        s=context.scene.wavelength;missing=set();loaded=0
        objects=[o for o in context.scene.objects if o.get('wl_role')=='BRUSH' and not o.get('wl_exclude')]
        if any(o.mode!='OBJECT' for o in objects):raise ValueError('Leave Edit Mode to load all map textures')
        for obj in objects:
            faces=scene.brush_from_object(obj,s.engine);ids=sorted(d.value for d in obj.data.attributes['wl_face_id'].data);by_id=dict(zip(ids,faces))
            for polygon in obj.data.polygons:
                name=by_id[obj.data.attributes['wl_face_id'].data[polygon.index].value].texture
                try:mat=textures.material(s,name)
                except ValueError:missing.add(name);continue
                textures.assign(obj,[polygon.index],mat);loaded+=1
            apply_uv(obj,s.engine)
        s.status=f'{loaded} face previews loaded; {len(missing)} missing textures'
        s.diagnostics=json.dumps([{'code':'TEXTURE_NOT_FOUND','severity':'warning','message':name} for name in sorted(missing)])

class WL_OT_preview_textures(bpy.types.Operator):
    bl_idname='wavelength.preview_textures';bl_label='Show Textures in Viewport'
    def execute(self,context):
        for area in context.screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL'
        return {'FINISHED'}


_SOURCE_MATERIAL_ITEMS=[]
def source_material_items(self,context):
    return _SOURCE_MATERIAL_ITEMS

class WL_OT_source_material(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.source_material';bl_label='Browse Source Materials';bl_property='choice'
    choice:EnumProperty(items=source_material_items)
    def invoke(self,context,event):
        global _SOURCE_MATERIAL_ITEMS
        from . import source_assets
        try:
            names=source_assets.library(bpy.path.abspath(context.scene.wavelength.game_dir)).materials()
            _SOURCE_MATERIAL_ITEMS=[(name,name,'Material from installed game') for name in names]
            if not names:raise ValueError('No Source materials found in the configured game directory')
            context.window_manager.invoke_search_popup(self)
            return {'RUNNING_MODAL'}
        except (OSError,ValueError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
    def run(self,context):context.scene.wavelength.texture=self.choice

class WL_OT_source_output(SafeOperator,bpy.types.Operator):
    bl_idname='wavelength.source_output';bl_label='Entity Output';bl_options={'REGISTER','UNDO'}
    index:IntProperty(default=-1)
    remove:BoolProperty(default=False)
    event:StringProperty(name='Output',default='OnTrigger')
    target:StringProperty(name='Target',default='!self')
    input_name:StringProperty(name='Input',default='Trigger')
    parameter:StringProperty(name='Parameter')
    delay:FloatProperty(name='Delay',min=0,default=0)
    once:BoolProperty(name='Fire once',default=False)
    def invoke(self,context,event):
        if self.remove:return self.execute(context)
        from .vmf import OUTPUT
        obj=context.object;key='wl_entity_pairs' if obj and obj.get('wl_entity_id') else 'wl_pairs'
        pairs=json.loads(obj.get(key,'[]')) if obj else []
        if self.index>=0:
            name,value=pairs[self.index];parts=value.split('\x1b' if '\x1b' in value else ',')
            if len(parts)!=5:self.report({'ERROR'},'Output has unsupported syntax');return {'CANCELLED'}
            self.event=name[len(OUTPUT):];self.target,self.input_name,self.parameter=parts[:3];self.delay=float(parts[3]);self.once=parts[4]=='1'
        return context.window_manager.invoke_props_dialog(self)
    def draw(self,context):
        for field in ('event','target','input_name','parameter','delay','once'):self.layout.prop(self,field)
    def run(self,context):
        from .vmf import OUTPUT
        obj=context.object
        if not obj or not (obj.get('wl_role')=='ENTITY' or obj.get('wl_entity_id')):raise ValueError('Select a point or brush entity')
        key='wl_entity_pairs' if obj.get('wl_entity_id') else 'wl_pairs';pairs=json.loads(obj.get(key,'[]'))
        if self.index>=len(pairs):raise ValueError('Output changed; reopen the editor')
        if self.index>=0 and not pairs[self.index][0].startswith(OUTPUT):raise ValueError('Selected property is not an output')
        if self.remove:
            if self.index<0:raise ValueError('Choose an output to remove')
            pairs.pop(self.index)
        else:
            if not self.event.strip() or not self.target.strip() or not self.input_name.strip():raise ValueError('Output, target and input are required')
            if any(',' in x or '\x1b' in x or '\n' in x for x in (self.target,self.input_name,self.parameter)):raise ValueError('HL2 output fields cannot contain commas, escape separators or newlines')
            item=(OUTPUT+self.event,','.join([self.target,self.input_name,self.parameter,str(self.delay),'1' if self.once else '-1']))
            if self.index<0:pairs.append(item)
            else:pairs[self.index]=item
        members=_brush_entity_members(context.scene,obj['wl_entity_id']) if obj.get('wl_entity_id') else [obj]
        for member in members:member[key]=json.dumps(pairs)

class WL_PT_source_outputs(bpy.types.Panel):
    bl_label='Source Entity Outputs';bl_idname='WL_PT_source_outputs';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    @classmethod
    def poll(cls,context):return profiles.is_source(context.scene.wavelength.engine)
    def draw(self,context):
        from .vmf import OUTPUT
        l=self.layout;obj=context.object
        if not obj or not (obj.get('wl_role')=='ENTITY' or obj.get('wl_entity_id')):l.label(text='Select an entity');return
        pairs=json.loads(obj.get('wl_entity_pairs' if obj.get('wl_entity_id') else 'wl_pairs','[]'))
        for i,(key,value) in enumerate(pairs):
            if not key.startswith(OUTPUT):continue
            row=l.row(align=True);op=row.operator('wavelength.source_output',text=key[len(OUTPUT):]+' → '+value.split(',')[0]);op.index=i
            op=row.operator('wavelength.source_output',text='',icon='X');op.index=i;op.remove=True
        l.operator('wavelength.source_output',text='Add Output',icon='ADD')


_CLASSES=[WL_OT_source_material,WL_OT_source_output,brush_create.WL_OT_brush_hover,brush_create.WL_OT_cube_brush,brush_create.WL_OT_cylinder_brush,brush_create.WL_OT_cone_brush,brush_create.WL_OT_sphere_brush,brush_create.WL_OT_arch_brush,WLTextureBrowserItem,WLTextureGalleryRow,WL_UL_texture_browser,WL_UL_texture_gallery,WL_OT_texture_browser_pick,WL_OT_texture_browser,WL_OT_add_wad,WL_OT_select_wad,WL_OT_remove_wad,WL_OT_refresh_textures,WL_OT_texture_page,WL_OT_quake_textures,WL_OT_resolve_textures,WL_OT_preview_textures,WLKey,WLSettings,WL_OT_property_add,WL_OT_property_custom_add,WL_OT_property_remove,WL_OT_clip,WL_OT_duplicate,WL_OT_bake,WL_OT_save_project,WL_OT_load_project,WL_OT_setup,WL_OT_brush,WL_OT_hollow,WL_OT_mark,WL_OT_ids,WL_OT_snap,WL_OT_grid_step,WL_OT_entity,WL_OT_entity_search,WL_OT_entity_browse,WL_MT_add_entity,WL_MT_add,WL_OT_brush_entity,WL_OT_brush_entity_add,WL_OT_brush_entity_remove,WL_OT_brush_entity_to_world,WL_OT_properties,WL_OT_read_face_texture,WL_OT_texture,WL_OT_validate_alpha,WL_OT_select_problem,WL_OT_worldspawn,WL_OT_texture_nudge,WL_OT_select_by_texture,WL_OT_select_target,WL_OT_import,WL_OT_export,WL_OT_validate,WL_OT_build,WL_OT_cancel,WL_OT_logs,WL_OT_launch,WL_OT_leak,WL_OT_system_select,WL_OT_system_select_category,WL_OT_system_visibility,WL_OT_system_category_visibility,WL_PT_main,WL_PT_source_outputs,WL_PT_system_tree,WL_PT_project,WL_PT_worldspawn,WL_PT_relationships,WL_PT_entity,WL_PT_texture,WL_PT_diagnostics]

def _safe_unregister_class(cls):
    # A failed/reloaded add-on can leave the *old module instance* of an RNA class
    # registered.  In that case bpy.types.<name> is not the same Python object as
    # the freshly imported cls, but Blender still rejects the new class by name.
    # Unregister whichever class object Blender currently owns for this RNA name.
    try:
        registered = getattr(bpy.types, cls.__name__, None)
        if registered is not None:
            bpy.utils.unregister_class(registered)
    except (RuntimeError, ValueError, TypeError):
        pass

def register():
    # RNA operator/property classes belong to the add-on lifecycle only.  Do not
    # unregister/re-register them when an engine profile changes.
    registered=[]
    try:
        for cls in _CLASSES:
            bpy.utils.register_class(cls);registered.append(cls)
        bpy.types.VIEW3D_MT_add.append(_draw_view3d_add_menu)
        bpy.types.Scene.wavelength=PointerProperty(type=WLSettings)
        workspace.register();precision_move.register();primitive_ui.register();asset_browser.register();profile_ui.register();grid.register();identity.register();editor.register();resize_gizmo.register();system_tree.register();authoring.register();entity_browser.register()
        # WorkSpaceTool registration itself is context-free. Keep it registered
        # for the add-on lifetime so Blender's toolbar can discover it reliably.
        brush_create.register_tool()
        # Tool-system changes may not repaint an already-open toolbar immediately.
        # Defer redraw until normal runtime context is restored after add-on register().
        def _redraw_view3d_once():
            try:
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            except Exception:
                pass
            return None
        bpy.app.timers.register(_redraw_view3d_once, first_interval=0.05)
    except Exception:
        try:bpy.types.VIEW3D_MT_add.remove(_draw_view3d_add_menu)
        except Exception:pass
        # Make registration transactional: never strand classes after a later failure.
        try: brush_create.unregister_tool()
        except Exception: pass
        try: entity_browser.unregister()
        except Exception: pass
        try: authoring.unregister()
        except Exception: pass
        try: system_tree.unregister()
        except Exception: pass
        try: transform_sync.unregister()
        except Exception: pass
        try: resize_gizmo.unregister()
        except Exception: pass
        try: editor.unregister()
        except Exception: pass
        try: identity.unregister()
        except Exception: pass
        for module in (profile_ui,asset_browser,primitive_ui,precision_move,workspace,grid):
            try:module.unregister()
            except Exception:pass
        if hasattr(bpy.types.Scene,'wavelength'):
            try: del bpy.types.Scene.wavelength
            except Exception: pass
        for cls in reversed(registered):
            _safe_unregister_class(cls)
        raise

def unregister():
    global _JOB
    try:bpy.types.VIEW3D_MT_add.remove(_draw_view3d_add_menu)
    except Exception:pass
    if _JOB:_JOB.cancel();_JOB=None
    if bpy.app.timers.is_registered(build_tick):bpy.app.timers.unregister(build_tick)
    try: brush_create.unregister_tool()
    except Exception: pass
    try: entity_browser.unregister()
    except Exception: pass
    try: authoring.unregister()
    except Exception: pass
    try: system_tree.unregister()
    except Exception: pass
    try: transform_sync.unregister()
    except Exception: pass
    try: resize_gizmo.unregister()
    except Exception: pass
    try: editor.unregister()
    except Exception: pass
    try: identity.unregister()
    except Exception: pass
    textures.close()
    for module in (profile_ui,asset_browser,primitive_ui,precision_move):
        try:module.unregister()
        except Exception:pass
    try: workspace.unregister()
    except Exception: pass
    try: grid.unregister()
    except Exception: pass
    if hasattr(bpy.types.Scene,'wavelength'):
        try: del bpy.types.Scene.wavelength
        except Exception: pass
    for cls in reversed(_CLASSES):_safe_unregister_class(cls)
