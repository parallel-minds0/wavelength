"""Deterministic Source terrain blend recipes and bounded asset staging."""
import hashlib,os,tempfile
from pathlib import Path
from .source_assets import asset_path


def texture_reference(value):
    value=asset_path(value)
    if any(c in value for c in '\r\n\0"{}'):raise ValueError('Invalid terrain texture reference')
    if value.startswith('materials/'):value=value[10:]
    if value.endswith('.vtf'):value=value[:-4]
    if not value:raise ValueError('Empty terrain texture reference')
    return value


def asset_name(text):return 'wavelength/generated/terrain_'+hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]


def recipe(base,paint):
    if not base.get('$basetexture') or not paint.get('$basetexture'):raise ValueError('Both terrain layers need a base texture')
    values={'$basetexture':texture_reference(base['$basetexture']),'$basetexture2':texture_reference(paint['$basetexture'])}
    for source,key in [(base,'$bumpmap'),(paint,'$bumpmap2')]:
        if source.get('$bumpmap'):values[key]=texture_reference(source['$bumpmap'])
    surface=str(base.get('$surfaceprop','dirt')).strip()
    if not surface or any(c in surface for c in '\r\n\0"{}\\'):raise ValueError('Invalid terrain surface property')
    values['$surfaceprop']=surface
    text='WorldVertexTransition\n{\n'+''.join(f'    "{key}" "{value}"\n' for key,value in values.items())+'}\n'
    return asset_name(text),text


def _write_generated(root,name,text):
    root=Path(root).resolve();target=(root/'materials'/(name+'.vmt')).resolve()
    if not target.is_relative_to(root):raise ValueError('Generated material escapes its asset directory')
    payload=text.encode('utf-8')
    if target.exists():
        if target.read_bytes()!=payload:raise ValueError('Generated material path contains different content; existing file preserved')
        return target
    target.parent.mkdir(parents=True,exist_ok=True)
    # Recheck after mkdir so a redirected namespace cannot escape its root.
    if not target.resolve().is_relative_to(root):raise ValueError('Generated material namespace is redirected outside its asset directory')
    fd,temporary=tempfile.mkstemp(prefix='.terrain-',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(payload)
        if target.exists() and target.read_bytes()!=payload:raise ValueError('Generated material collision; existing file preserved')
        os.replace(temporary,target)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
    return target


def stage(game,project,name,text):
    if name!=asset_name(text):raise ValueError('Generated terrain material identity does not match its recipe')
    game=Path(game).resolve();project=Path(project).resolve()
    if not (game/'gameinfo.txt').is_file():raise ValueError('Choose a Source game directory containing gameinfo.txt')
    generated=(project/'.wavelength'/'generated-assets').resolve()
    if not generated.is_relative_to(project):raise ValueError('Generated asset directory escapes the project')
    project_file=_write_generated(generated,name,text)
    game_file=_write_generated(game,name,text)
    return project_file,game_file
