"""Engine-neutral model backend registry. No Blender or engine dependencies."""
from dataclasses import dataclass,field
from pathlib import Path

@dataclass
class ImportedModel:
    objects:list
    warnings:list=field(default_factory=list)

_BACKENDS={}

def register(backend):
    if backend.id in _BACKENDS:raise ValueError('Model backend already registered: '+backend.id)
    _BACKENDS[backend.id]=backend

def unregister(identifier):_BACKENDS.pop(identifier,None)

def backend_for(engine,filename=None):
    suffix=Path(filename).suffix.lower() if filename else None
    matches=[b for b in _BACKENDS.values() if b.supports(engine) and (suffix is None or suffix in b.extensions)]
    if len(matches)!=1:raise ValueError('No unique model backend for this profile/format')
    return matches[0]

def get(identifier):
    try:return _BACKENDS[identifier]
    except KeyError:raise ValueError('Model backend is unavailable: '+identifier) from None

def extensions(engine):return sorted({e for b in _BACKENDS.values() if b.supports(engine) for e in b.extensions})

def all_extensions():return sorted({e for b in _BACKENDS.values() for e in b.extensions})
