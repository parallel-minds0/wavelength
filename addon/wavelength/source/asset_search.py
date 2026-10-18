"""Debounce the native texture filter without replacing Blender's browser."""
import time
import bpy
from . import workspace

DELAY=.25
_pending={}
_syncing=False
_original=None


def changed(self,context):
    if _syncing:return
    area=getattr(context,'area',None)
    if not area or str(area.as_pointer())!=self.area_key:return
    _pending[self.area_key]=(area,self.query,time.monotonic()+DELAY)
    if not bpy.app.timers.is_registered(apply_pending):
        bpy.app.timers.register(apply_pending,first_interval=DELAY)


class WLAssetSearch(bpy.types.PropertyGroup):
    area_key:bpy.props.StringProperty()
    query:bpy.props.StringProperty(name='Search Textures',description='Filter native assets after a short typing pause',
                                  options={'TEXTEDIT_UPDATE','SKIP_SAVE'},update=changed)


def ensure(area):
    global _syncing
    items=bpy.context.window_manager.wl_asset_search
    key=str(area.as_pointer())
    item=next((item for item in items if item.area_key==key),None)
    if item is None:
        item=items.add();item.area_key=key
    if key not in _pending:
        value=area.spaces.active.params.filter_search
        if item.query!=value:
            _syncing=True
            try:item.query=value
            finally:_syncing=False
    return item


def apply_pending():
    now=time.monotonic();delay=None
    for key,(area,query,deadline) in list(_pending.items()):
        if deadline>now:
            delay=min(delay or DELAY,deadline-now)
            continue
        _pending.pop(key,None)
        try:
            if area.type=='FILE_BROWSER' and area.ui_type=='ASSETS':
                params=area.spaces.active.params
                if params.filter_search!=query:params.filter_search=query
        except (ReferenceError,AttributeError):pass
    return max(.01,delay or DELAY) if _pending else None


def draw_buttons(self,context):
    settings=getattr(context.scene,'wavelength',None)
    if not workspace.active(context) or not settings or settings.asset_browser_section!='TEXTURES':
        return _original(self,context)
    params=context.space_data.params
    if params is None:return
    l=self.layout;l.separator_spacer()
    if params.asset_library_reference not in {'LOCAL','ESSENTIALS'}:
        l.popover('ASSETBROWSER_PT_import_settings',text='Import Settings')
    l.separator_spacer()
    l.prop_with_popover(params,'display_type',panel='ASSETBROWSER_PT_display',text='',icon_only=True)
    row=l.row();row.ui_units_x=8
    row.prop(ensure(context.area),'query',text='',icon='VIEWZOOM')
    l.popover('ASSETBROWSER_PT_filter',text='',icon='FILTER')
    from bl_ui.space_filebrowser import is_option_region_visible
    l.operator('screen.region_toggle',text='',icon='PREFERENCES',
               depress=is_option_region_visible(context,context.space_data)).region_type='TOOL_PROPS'


def register():
    global _original
    bpy.utils.register_class(WLAssetSearch)
    bpy.types.WindowManager.wl_asset_search=bpy.props.CollectionProperty(type=WLAssetSearch)
    header=bpy.types.FILEBROWSER_HT_header
    _original=header.draw_asset_browser_buttons
    header.draw_asset_browser_buttons=draw_buttons


def unregister():
    global _original
    if _original is not None:
        bpy.types.FILEBROWSER_HT_header.draw_asset_browser_buttons=_original
        _original=None
    if bpy.app.timers.is_registered(apply_pending):bpy.app.timers.unregister(apply_pending)
    _pending.clear()
    if hasattr(bpy.types.WindowManager,'wl_asset_search'):del bpy.types.WindowManager.wl_asset_search
    if WLAssetSearch.is_registered:bpy.utils.unregister_class(WLAssetSearch)
