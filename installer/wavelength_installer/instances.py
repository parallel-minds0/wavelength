"""Instance addresses. The historical root receipt remains the default instance."""
from pathlib import Path
import re
from .lifecycle import read_receipt,StateError


def validate_id(value):
    if value!='default' and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',value):
        raise ValueError('Invalid instance id; use letters, numbers, underscores or hyphens')
    return value


def list_instances(root):
    root=Path(root).expanduser().resolve();result=[]
    paths=[('default',root)]
    if root.is_dir():
        paths += [(p.name,p) for p in sorted(root.iterdir()) if p.is_dir() and not p.is_symlink()
                  and p.name not in {'stale','backups'} and (p/'receipt.json').is_file()]
    for name,path in paths:
        data=read_receipt(path)
        if data['phase'] not in {'not-installed','removed'}:
            result.append({'id':name,'state':str(path),'phase':data['phase'],'version':data.get('version'),'blender':data.get('blender')})
    return result


def select(root,instance=None,choose=None):
    root=Path(root).expanduser().resolve()
    if instance is not None:
        validate_id(instance)
        target=root if instance=='default' else root/instance
        if target.is_symlink():raise StateError('Instance directory must not be a symlink')
        return target
    choices=list_instances(root)
    if len(choices)<=1:return Path(choices[0]['state']) if choices else root
    listing=', '.join(x['id'] for x in choices)
    if choose:
        answer=choose([x['id'] for x in choices]).strip()
        if answer in {x['id'] for x in choices}:return select(root,answer)
    raise StateError('Several wavelength instances exist; use --instance <id>: '+listing)
