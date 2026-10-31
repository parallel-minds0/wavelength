"""Pure map validation and geometry preparation, safe in an isolated worker."""
import math
from . import formats,displacement


def geometry(document):
    for entity in document.entities:
        for brush in entity.brushes:
            vertices,polygons=formats.brush_mesh(brush)
            for index,face in enumerate(brush):
                if (face.vmf or {}).get('dispinfo'):
                    data=face.vmf['dispinfo']
                    quad=displacement.quad(vertices,polygons[index],data['startposition'])
                    points=displacement.grid(data,quad,face.plane()[0])
                    if any(not math.isfinite(c) or abs(c)>32768 for p in points for c in p):
                        raise ValueError('Displacement exceeds finite Source coordinate bounds')
            yield entity,brush,vertices,polygons
        if not entity.brushes:
            try:
                origin=[float(x) for x in dict(entity.pairs).get('origin','0 0 0').split()]
                if len(origin)!=3 or not all(math.isfinite(x) for x in origin):raise ValueError()
            except ValueError as exc:raise ValueError('Entity origin must be three finite numbers') from exc
