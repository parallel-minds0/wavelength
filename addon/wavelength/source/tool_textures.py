"""Profile-specific names for equivalent compiler surfaces."""
from . import profiles

def canonical(engine,name):
    name=str(name).strip()
    if name.casefold() in {'nodraw','null','tools/toolsnodraw','null (nodraw)'}:
        if profiles.is_goldsrc(engine):return 'NULL'
        if profiles.is_source(engine):return 'tools/toolsnodraw'
    return name
