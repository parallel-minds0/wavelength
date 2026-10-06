"""Convex-brush geometry, independent of Blender.

All coordinates in this experiment use one Blender unit per engine unit.
This is not an engine profile or a complete MAP importer.
"""
from itertools import combinations
import math

TOLERANCE = 1e-5


class BrushError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def length(v):
    return math.sqrt(dot(v, v))


def face_plane(vertices, face):
    """Return a non-collinear triplet and normalized plane."""
    for ids in combinations(face, 3):
        a, b, c = [vertices[i] for i in ids]
        normal = cross(sub(b, a), sub(c, a))
        size = length(normal)
        if size > TOLERANCE * TOLERANCE:
            normal = tuple(x / size for x in normal)
            return ids, normal, dot(normal, a)
    raise BrushError("DEGENERATE_FACE", "Face has no non-collinear triplet")


def validate(vertices, faces):
    if len(vertices) < 4 or len(faces) < 4:
        raise BrushError("EMPTY_OR_DEGENERATE", "A solid needs at least four vertices and faces")
    if any(not math.isfinite(x) for v in vertices for x in v):
        raise BrushError("NONFINITE_COORDINATE", "Coordinates must be finite")
    if len({tuple(v) for v in vertices}) != len(vertices):
        raise BrushError("DUPLICATE_VERTEX", "Coincident vertices need merging")
    edges = {}
    used = set()
    for face in faces:
        if len(face) < 3 or len(set(face)) != len(face):
            raise BrushError("DEGENERATE_FACE", "Invalid face vertex sequence")
        if any(i < 0 or i >= len(vertices) for i in face):
            raise BrushError("INVALID_INDEX", "Face index outside vertex array")
        used.update(face)
        for a, b in zip(face, face[1:] + face[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
    if used != set(range(len(vertices))):
        raise BrushError("LOOSE_VERTEX", "Solid contains unused vertices")
    if any(len(directions) != 2 or directions[0] != directions[1][::-1]
           for directions in edges.values()):
        raise BrushError("NONMANIFOLD", "Edges must have two oppositely oriented faces")
    center = tuple(sum(v[i] for v in vertices)/len(vertices) for i in range(3))
    planes = []
    for face in faces:
        ids, n, d = face_plane(vertices, face)
        if any(abs(dot(n, vertices[i]) - d) > TOLERANCE for i in face):
            raise BrushError("NONPLANAR_FACE", "Face vertices are not planar")
        # Accept globally reversed winding (e.g. a mirrored object).
        if dot(n, center) > d:
            n, d = tuple(-x for x in n), -d
            ids = ids[::-1]
        if any(dot(n, v) - d > TOLERANCE for v in vertices):
            raise BrushError("NONCONVEX", "A face plane cuts through the solid")
        if any(length(sub(n, prior[1])) < TOLERANCE and abs(d-prior[2]) < TOLERANCE
               for prior in planes):
            raise BrushError("DUPLICATE_PLANE", "Coplanar faces must be merged")
        if d - dot(n, center) <= TOLERANCE:
            raise BrushError("ZERO_VOLUME", "Solid is flat or too thin")
        planes.append((ids, n, d))
    return planes


def from_planes(planes):
    """Intersect halfspaces, then reconstruct planar polygons."""
    vertices = []
    for (a, da), (b, db), (c, dc) in combinations(planes, 3):
        bc, ca, ab = cross(b, c), cross(c, a), cross(a, b)
        determinant = dot(a, bc)
        if abs(determinant) < 1e-10:
            continue
        point = tuple((da*bc[i]+db*ca[i]+dc*ab[i])/determinant for i in range(3))
        if all(dot(n, point)-d <= TOLERANCE for n, d in planes):
            if not any(length(sub(point, existing)) < TOLERANCE for existing in vertices):
                vertices.append(point)
    faces = []
    for normal, distance in planes:
        ids = [i for i, v in enumerate(vertices) if abs(dot(normal, v)-distance) <= TOLERANCE]
        if len(ids) < 3:
            raise BrushError("REDUNDANT_PLANE", "Plane does not bound a polygon")
        center = tuple(sum(vertices[i][j] for i in ids)/len(ids) for j in range(3))
        axis = (1, 0, 0) if abs(normal[0]) < 0.9 else (0, 1, 0)
        u = cross(axis, normal)
        v = cross(normal, u)
        ids.sort(key=lambda i: math.atan2(dot(sub(vertices[i], center), v),
                                          dot(sub(vertices[i], center), u)))
        faces.append(ids)
    validate(vertices, faces)
    return vertices, faces


def number(value):
    if not math.isfinite(value):
        raise BrushError("NONFINITE_COORDINATE", "Cannot serialize a non-finite number")
    if abs(value) < 0.0000005:
        return "0"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def brush_text(vertices, faces, textures):
    planes = validate(vertices, faces)
    lines = []
    for (ids, normal, distance), texture in zip(planes, textures, strict=True):
        name = texture["name"]
        if not name or any(c.isspace() or c in '{}()"' for c in name):
            raise BrushError("INVALID_TEXTURE", "Texture token contains unsupported characters")
        values = texture["projection"]
        if len(values) != 5 or any(not math.isfinite(x) for x in values) or 0 in values[3:]:
            raise BrushError("INVALID_PROJECTION", "Expected finite shifts, rotation, nonzero scales")
        points = [vertices[i] for i in ids[::-1]]
        rounded = [tuple(float(number(x)) for x in p) for p in points]
        _, rn, rd = face_plane(rounded, [0, 2, 1])
        if length(sub(rn, normal)) > TOLERANCE or abs(rd-distance) > TOLERANCE:
            raise BrushError("PRECISION_LOSS", "Export rounding changes the face plane")
        line = " ".join("( " + " ".join(number(x) for x in p) + " )" for p in points)
        lines.append(line + " " + name + " " + " ".join(number(x) for x in values))
    return "{\n" + "\n".join(sorted(lines)) + "\n}"
