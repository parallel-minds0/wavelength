"""Generator-independent definitions, evaluation and profile validation.

No Blender data mutation belongs in this module. Adapters return local-space
mesh parts; Blender owns committing them and baking evaluated objects.
"""
import copy,json
from dataclasses import dataclass,asdict
from . import primitives,profiles

SCHEMA_VERSION=1
PYTHON_GENERATOR='wavelength.python_primitives'
GENERATOR_VERSION=1

@dataclass(frozen=True)
class Definition:
    kind:str
    owner:str
    parameters:dict
    unit_meters:float
    grid_step:float|None=None
    convex_brushes:bool=False
    owner_profile_id:str=""
    owner_profile_name:str=""
    generator:str=PYTHON_GENERATOR
    generator_version:int=GENERATOR_VERSION
    schema_version:int=SCHEMA_VERSION

    def dumps(self):return json.dumps(asdict(self),sort_keys=True,allow_nan=False)

    @classmethod
    def loads(cls,text):
        definition=cls(**json.loads(text))
        if definition.schema_version!=SCHEMA_VERSION:raise ValueError('Unsupported procedural definition version')
        return definition


def define(kind,owner,parameters,unit_meters,grid_step=None,profile_id="",profile_name=""):
    if unit_meters<=0:raise ValueError('Procedural units must be positive')
    return Definition(kind,owner,copy.deepcopy(parameters),float(unit_meters),grid_step,profiles.requires_convex_brushes(owner),profile_id,profile_name)


def evaluate(definition):
    if definition.generator=='wavelength.geometry_nodes.primitives' and definition.generator_version==1:
        from . import node_primitives
        return node_primitives.evaluate(definition)
    if definition.generator=='wavelength.geometry_nodes.straight_stairs' and definition.generator_version==1:
        from . import node_stairs
        return node_stairs.evaluate(definition)
    if definition.generator!=PYTHON_GENERATOR or definition.generator_version!=GENERATOR_VERSION:
        raise ValueError('Unsupported procedural generator; preserve the current mesh')
    # The legacy generator currently performs its own BSP validation too. This
    # adapter preserves that implementation while exposing independent validation.
    return primitives.generate(definition.kind,copy.deepcopy(definition.parameters),validate_bsp=definition.convex_brushes,grid_step=definition.grid_step)


def validate(definition,parts):
    if not parts:raise ValueError('Generator returned no geometry')
    from math import isfinite
    from .geometry import validate as validate_brush
    for vertices,faces in parts:
        if not vertices or not faces or any(len(v)!=3 or not all(isfinite(c) for c in v) for v in vertices):raise ValueError('Generator returned invalid vertices')
        if any(len(f)<3 or any(i<0 or i>=len(vertices) for i in f) for f in faces):raise ValueError('Generator returned invalid face indices')
        if definition.convex_brushes:validate_brush(vertices,[list(f) for f in faces])
    return parts


def state(root):return root.get('wl_procedural_state','PROCEDURAL' if root.get('wl_primitive') else 'FINALIZED')


def definition_for(root,kind,values,owner,unit,grid_step):
    text=root.get('wl_definition')
    if text:
        old=Definition.loads(text)
        if old.owner!=owner:raise ValueError('Profile conversion must be explicit')
        # Parameter editing preserves ownership, units and generator identity.
        from dataclasses import replace
        if old.generator.startswith('wavelength.geometry_nodes.') and kind=='STAIRS':
            generator='wavelength.geometry_nodes.primitives' if values.get('curved') else 'wavelength.geometry_nodes.straight_stairs'
            return replace(old,kind=kind,parameters=copy.deepcopy(values),generator=generator)
        return replace(old,kind=kind,parameters=copy.deepcopy(values))
    definition=define(kind,owner,values,unit,grid_step)
    if not root.get('wl_primitive') and kind=='STAIRS' and not values.get('curved',False):
        from dataclasses import replace
        definition=replace(definition,generator='wavelength.geometry_nodes.straight_stairs')
    elif not root.get('wl_primitive') and kind in {'ARCH','STAIRS','SPHERE','CUBE','CYLINDER','CONE'}:
        from dataclasses import replace
        definition=replace(definition,generator='wavelength.geometry_nodes.primitives')
    return definition
