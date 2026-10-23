"""Registered profiles: inherited overrides, legacy migration and dependency safety."""
import copy,json,os,uuid,math
from pathlib import Path
from .profile_registry import TEMPLATES
SCHEMA=2

def validate(value):
    if not isinstance(value,dict):raise ValueError('Profile must be an object')
    value=copy.deepcopy(value)
    if 'settings' not in value and value.get('schema_version')==1:
        value={'schema':1,'name':value.get('profile_name') or 'Imported project','settings':{k:v for k,v in value.items() if k!='schema_version'}}
    if value.get('schema',1) not in (1,2):raise ValueError('Unsupported profile schema')
    if not isinstance(value.get('settings'),dict) or not str(value.get('name','')).strip():raise ValueError('Profile needs name and settings')
    from .profiles import PROFILES
    if value.get('schema',1)==1:
        engine=value['settings'].get('engine')
        if engine not in PROFILES:raise ValueError('Unknown base engine')
        value['parent']=engine
    parent=value.get('parent')
    if not isinstance(parent,str) or not parent:raise ValueError('Profile needs a parent')
    if parent not in TEMPLATES.definitions:uuid.UUID(parent)
    value.setdefault('id',str(uuid.uuid4()))
    if value['id'] in TEMPLATES.definitions:raise ValueError('Shipped templates are protected; register a derived profile')
    value['id']=str(uuid.UUID(value['id']));value['schema']=2
    value.setdefault('enum_number',4096+(uuid.UUID(value['id']).int & 0x3fffffff))
    if not isinstance(value['enum_number'],int) or not 4096<=value['enum_number']<2**31:raise ValueError('Invalid registered profile enum number')
    value['settings'].pop('profile_id',None);value['settings'].pop('profile_name',None)
    for key in ('overrides','builtin','lineage'):value.pop(key,None)
    if 'unit_scale' in value['settings']:
        scale=float(value['settings']['unit_scale'])
        if not math.isfinite(scale) or scale<=0:raise ValueError('Unit scale must be positive')
    if value['settings'].get('custom_model_deployment','BSP') not in {'BSP','GAME'}:raise ValueError('Custom model deployment must be BSP or GAME')
    for field in ('asset_paths','texture_wads','wrapper','launch_args','qbsp_args','vis_args','light_args','source_vbsp_args','source_vvis_args','source_vrad_args'):
        if field in value['settings']:
            seq=json.loads(value['settings'][field] or '[]')
            if not isinstance(seq,list) or not all(isinstance(x,str) for x in seq):raise ValueError(field+' must be a JSON string list')
    json.dumps(value,allow_nan=False)
    return value

class Store:
    def __init__(self,folder):self.folder=Path(folder);self.errors=[]
    def _records(self):
        records={};self.errors=[]
        if self.folder.exists():
            for path in sorted(self.folder.glob('*.json')):
                try:
                    value=validate(json.loads(path.read_text(encoding='utf-8-sig')))
                    if path.stem!=value['id']:raise ValueError('Profile ID differs from filename')
                    records[value['id']]=value
                except (ValueError,OSError,TypeError) as exc:self.errors.append(path.name+': '+str(exc))
        return records
    def _resolve(self,identity,records,trail=()):
        if identity in trail:raise ValueError('Profile inheritance cycle')
        if identity in TEMPLATES.definitions:
            definition=TEMPLATES.resolve(identity)
            return {'id':identity,'name':definition['label'],'builtin':True,'parent':definition.get('parent'),'settings':TEMPLATES.settings(identity),'lineage':TEMPLATES.lineage(identity)}
        if identity not in records:raise ValueError('Missing parent or unregistered profile: '+str(identity))
        value=records[identity];parent=self._resolve(value['parent'],records,(*trail,identity))
        settings=dict(parent['settings']);overrides=copy.deepcopy(value['settings'])
        if overrides.get('engine',settings['engine'])!=settings['engine']:raise ValueError('Choose a different parent to change backend')
        settings.update(overrides)
        return {**value,'settings':settings,'overrides':overrides,'builtin':False,'lineage':parent['lineage']+[identity]}
    def all(self):
        records=self._records();rows=[]
        for identity in records:
            try:rows.append(self._resolve(identity,records))
            except ValueError as exc:self.errors.append(records[identity]['name']+': '+str(exc))
        return rows
    def get(self,identity):return self._resolve(identity,self._records())
    def raw(self,identity):
        if identity in TEMPLATES.definitions:raise ValueError('Shipped templates are read-only')
        records=self._records()
        if identity not in records:raise ValueError('Profile is not registered')
        return copy.deepcopy(records[identity])
    def _write(self,value):
        self.folder.mkdir(parents=True,exist_ok=True)
        destination=self.folder/(value['id']+'.json');temporary=destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8');os.replace(temporary,destination)
    def save(self,value):
        value=validate(value);records=self._records();records[value['id']]=value
        if len({v['enum_number'] for v in records.values()})!=len(records):raise ValueError('Profile enum number collision; register with a new UUID')
        for identity in records:self._resolve(identity,records)
        inherited=self._resolve(value['parent'],records)['settings']
        value['settings']={key:val for key,val in value['settings'].items() if key not in inherited or inherited[key]!=val}
        self._write(value);return self._resolve(value['id'],records)
    def remove(self,identity):
        if identity in TEMPLATES.definitions:raise ValueError('Shipped templates cannot be removed')
        identity=str(uuid.UUID(identity));records=self._records()
        children=[v['name'] for v in records.values() if v['parent']==identity]
        if children:raise ValueError('Remove or reparent dependent profiles first: '+', '.join(children))
        (self.folder/(identity+'.json')).unlink()
    def bundle(self,identity):
        records=self._records();profile=self._resolve(identity,records)
        if profile['builtin']:
            value=validate({'schema':2,'name':profile['name']+' Custom','parent':identity,'settings':{}})
            return {'schema':2,'profiles':[value],'active':value['id']}
        return {'schema':2,'profiles':[records[key] for key in profile['lineage'] if key in records],'active':identity}
    def register(self,document):
        if not isinstance(document,dict) or 'profiles' not in document:return self.save(document)
        if document.get('schema')!=2 or not isinstance(document['profiles'],list):raise ValueError('Invalid profile bundle')
        values=[validate(value) for value in document['profiles']]
        if len({v['id'] for v in values})!=len(values):raise ValueError('Duplicate profile IDs in bundle')
        records=self._records();records.update({v['id']:v for v in values});active=document.get('active')
        if len({v['enum_number'] for v in records.values()})!=len(records):raise ValueError('Profile enum number collision; register with a new UUID')
        if active not in {v['id'] for v in values}:raise ValueError('Bundle needs an active profile')
        for identity in records:self._resolve(identity,records)
        for value in values:self._write(value)
        return self._resolve(active,records)
