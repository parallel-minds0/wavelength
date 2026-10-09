"""Versioned user profiles with stable IDs and atomic persistence."""
import json,os,uuid,math
from pathlib import Path

SCHEMA=1

def validate(value):
    if not isinstance(value,dict):raise ValueError('Profile must be an object')
    value=dict(value)
    if 'settings' not in value and value.get('schema_version')==1:
        value={'schema':1,'name':value.get('profile_name') or 'Imported project','settings':{k:v for k,v in value.items() if k!='schema_version'}}
    if value.get('schema',1)!=SCHEMA:raise ValueError('Unsupported profile schema')
    if not isinstance(value.get('settings'),dict) or not str(value.get('name','')).strip():raise ValueError('Profile needs name and settings')
    from .profiles import PROFILES
    if value['settings'].get('engine') not in PROFILES:raise ValueError('Unknown base engine')
    value.setdefault('id',str(uuid.uuid4()));uuid.UUID(value['id']);value['schema']=SCHEMA
    scale=float(value['settings'].get('unit_scale',.0254))
    if not math.isfinite(scale) or scale<=0:raise ValueError('Unit scale must be positive')
    for field in ('asset_paths','texture_wads','wrapper','launch_args','qbsp_args','vis_args','light_args','source_vbsp_args','source_vvis_args','source_vrad_args'):
        if field in value['settings']:
            seq=json.loads(value['settings'][field] or '[]')
            if not isinstance(seq,list) or not all(isinstance(x,str) for x in seq):raise ValueError(field+' must be a JSON string list')
    return value


class Store:
    def __init__(self,folder):self.folder=Path(folder)
    def all(self):
        rows=[]
        if self.folder.exists():
            for p in sorted(self.folder.glob('*.json')):
                try:rows.append(validate(json.loads(p.read_text())))
                except (ValueError,OSError,TypeError):continue
        return rows
    def save(self,value):
        value=validate(value);self.folder.mkdir(parents=True,exist_ok=True)
        dest=self.folder/(value['id']+'.json');temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));os.replace(temp,dest);return value
    def get(self,identity):return validate(json.loads((self.folder/(str(uuid.UUID(identity))+'.json')).read_text()))
    def remove(self,identity):(self.folder/(str(uuid.UUID(identity))+'.json')).unlink()
