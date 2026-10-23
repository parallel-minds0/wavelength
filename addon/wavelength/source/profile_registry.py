"""Protected shipped template inheritance; no Blender dependency or executable JSON."""
import copy,json
from pathlib import Path

class Templates:
    def __init__(self,path=None):
        self.path=Path(path or Path(__file__).resolve().parents[1]/'environment/profiles/templates.json')
        document=json.loads(self.path.read_text(encoding='utf-8'))
        if document.get('schema')!=1:raise ValueError('Unsupported template registry schema')
        self.definitions=document['templates'];self._resolved={}
        for identity in self.definitions:self.resolve(identity)

    def resolve(self,identity,trail=()):
        if identity in trail:raise ValueError('Template inheritance cycle: '+' → '.join((*trail,identity)))
        if identity in self._resolved:return copy.deepcopy(self._resolved[identity])
        if identity not in self.definitions:raise ValueError('Unknown shipped template: '+identity)
        own=copy.deepcopy(self.definitions[identity]);parent=own.get('parent')
        inherited=self.resolve(parent,(*trail,identity)) if parent else {}
        # Abstractness and backend aliases belong to this node, not its children.
        inherited.pop('abstract',None);inherited.pop('backend',None)
        inherited.update(own);inherited['id']=identity;inherited['builtin']=True
        self._resolved[identity]=inherited
        return copy.deepcopy(inherited)

    def selectable(self):return {key:self.resolve(key) for key,value in self.definitions.items() if not value.get('abstract')}

    def settings(self,identity):
        template=self.resolve(identity)
        backend=template.get('backend',identity)
        if backend not in self.selectable():raise ValueError('This abstract template needs a concrete backend parent')
        return {'engine':backend,'unit_scale':template.get('unit_meters',1.),
                'grid_mode':'ENGINE' if template.get('grid') is not None else 'BLENDER',
                'grid_step':str(template.get('grid') or 16),'metric_grid_step':1.,'grid_subdivisions':0,
                **template.get('settings',{})}

    def lineage(self,identity):
        result=[]
        while identity:
            result.append(identity);identity=self.definitions[identity].get('parent')
        return list(reversed(result))

TEMPLATES=Templates()
