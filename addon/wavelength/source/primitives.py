"""Editable BSP primitives. Dimensions are engine units; each part is convex."""
from math import sin, cos, pi
from .geometry import validate

BOX_FACES=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))

def box(x0,y0,z0,x1,y1,z1):
    return [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],list(BOX_FACES)


def _rot_cs(deg):
    d = float(deg) % 360.0
    if abs(d - 0.0) < 1e-7 or abs(d - 360.0) < 1e-7:
        return 1.0, 0.0
    if abs(d - 90.0) < 1e-7:
        return 0.0, 1.0
    if abs(d - 180.0) < 1e-7:
        return -1.0, 0.0
    if abs(d - 270.0) < 1e-7:
        return 0.0, -1.0
    r = d * pi / 180.0
    return cos(r), sin(r)


def _quad_convex_ccw(q):
    for k in range(4):
        x0, y0 = q[k]
        x1, y1 = q[(k + 1) % 4]
        x2, y2 = q[(k + 2) % 4]
        if (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1) <= 1e-4:
            return False
    return True


def _curved_stair_bases(count, sweep, inner, outer, cx, left, landing, c_rot, s_rot, snap_step):
    def xform(x, y):
        rx = x * c_rot - y * s_rot
        ry = x * s_rot + y * c_rot
        if snap_step > 0.0:
            rx = round(rx / snap_step) * snap_step
            ry = round(ry / snap_step) * snap_step
        return (rx, ry)

    pts_in = []
    pts_out = []
    for i in range(count + 1):
        t = sweep * i / count
        ct, st = _rot_cs(t * 180.0 / pi)
        if left:
            pts_in.append(xform(cx + inner * ct, inner * st))
            pts_out.append(xform(cx + outer * ct, outer * st))
        else:
            pts_in.append(xform(cx - inner * ct, inner * st))
            pts_out.append(xform(cx - outer * ct, outer * st))

    bases = []
    for i in range(count):
        if left:
            base = [pts_in[i], pts_out[i], pts_out[i + 1], pts_in[i + 1]]
        else:
            base = [pts_out[i], pts_in[i], pts_in[i + 1], pts_out[i + 1]]
        if not _quad_convex_ccw(base):
            return None
        bases.append(base)

    if landing > 0:
        ct, st = _rot_cs(sweep * 180.0 / pi)
        if left:
            p0_raw = (cx + inner * ct, inner * st)
            p1_raw = (cx + outer * ct, outer * st)
            tx, ty = -st, ct
            p0, p1 = pts_in[count], pts_out[count]
        else:
            p0_raw = (cx - outer * ct, outer * st)
            p1_raw = (cx - inner * ct, inner * st)
            tx, ty = st, ct
            p0, p1 = pts_out[count], pts_in[count]
        p2 = xform(p1_raw[0] + landing * tx, p1_raw[1] + landing * ty)
        p3 = xform(p0_raw[0] + landing * tx, p0_raw[1] + landing * ty)
        lbase = [p0, p1, p2, p3]
        if not _quad_convex_ccw(lbase):
            return None
        bases.append(lbase)
    return bases


def generate(kind, p, validate_bsp=True, grid_step=None):
    validate_bsp = bool(p.get('validate_bsp', validate_bsp))
    if grid_step is None:
        grid_step = p.get('grid_step')
    g = float(grid_step) if grid_step is not None and float(grid_step) > 0 else 0.0
    min_dim = 1.0 if validate_bsp else 1e-3
    deg = float(p.get('direction', 0.0))
    c_rot, s_rot = _rot_cs(deg)
    parts = []
    pre_rotated = False

    if kind == 'STAIRS':
        count = int(p['steps'])
        rise = float(p['rise'])
        run = float(p['run'])
        width = float(p['width'])
        landing = float(p.get('landing', 0))
        curved = bool(p.get('curved', False))
        curve_angle = float(p.get('curve_angle', 90.0))
        inner = float(p.get('inner_radius', 64.0))
        if not 1 <= count <= 64 or min(rise, run, width) < min_dim or landing < 0:
            raise ValueError('Stairs require 1–64 steps and positive dimensions')
        if g > 0.0:
            rise = max(g, round(rise / g) * g)
            run = max(g, round(run / g) * g)
            width = max(g, round(width / g) * g)
            if landing > 0:
                landing = max(g, round(landing / g) * g)
        if curved:
            sweep = abs(curve_angle) * pi / 180.0
            if inner < min_dim or not 0 < abs(curve_angle) <= 360 or sweep / count >= pi:
                raise ValueError('Curved stairs require positive inner radius, nonzero curve angle up to 360°, and < 180° per step')
            if g > 0.0:
                inner = max(g, round(inner / g) * g)
            outer = inner + width
            left = curve_angle >= 0
            half_span = round((inner + width / 2.0) / g) * g if g > 0.0 else (inner + width / 2.0)
            cx = -half_span if left else half_span
            bases = None
            if g > 0.0:
                s = g
                for _ in range(9):
                    bases = _curved_stair_bases(count, sweep, inner, outer, cx, left, landing, c_rot, s_rot, s)
                    if bases is not None:
                        break
                    s *= 0.5
            if bases is None:
                bases = _curved_stair_bases(count, sweep, inner, outer, cx, left, landing, c_rot, s_rot, 0.0)
            if bases is None:
                raise ValueError('Curved stairs configuration produces degenerate step geometry')
            pre_rotated = True
            for i in range(count):
                h = (i + 1) * rise
                base = bases[i]
                verts = [(x, y, 0.0) for x, y in base] + [(x, y, h) for x, y in base]
                parts.append((verts, list(BOX_FACES)))
            if landing > 0:
                h = count * rise
                base = bases[count]
                verts = [(x, y, 0.0) for x, y in base] + [(x, y, h) for x, y in base]
                parts.append((verts, list(BOX_FACES)))
        else:
            x0 = -round((width / 2.0) / g) * g if g > 0.0 else -width / 2.0
            x1 = x0 + width
            for i in range(count):
                parts.append(box(x0, i * run, 0.0, x1, (i + 1) * run, (i + 1) * rise))
            if landing > 0:
                parts.append(box(x0, count * run, 0.0, x1, count * run + landing, count * rise))
    elif kind == 'ARCH':
        radius = float(p['radius'])
        thick = float(p['thickness'])
        depth = float(p['depth'])
        angle = float(p['angle']) * pi / 180.0
        segments = int(p['segments'])
        if not 3 <= segments <= 64 or not 0 < thick < radius or depth < min_dim or not 0 < angle <= 2 * pi or angle / segments >= pi:
            raise ValueError('Arch requires positive radius, thickness below radius, depth, and 3–64 segments')
        inner = radius - thick
        for i in range(segments):
            a = pi / 2 - angle / 2 + angle * i / segments
            b = a + angle / segments
            ring = [(r * cos(t), 0.0, r * sin(t)) for r, t in ((inner, a), (radius, a), (radius, b), (inner, b))]
            # Extrusion is -Y so polygon orientation follows the XZ plane.
            verts = ring + [(x, -depth, z) for x, y, z in ring]
            parts.append((verts, list(BOX_FACES)))
    elif kind == 'SPHERE':
        radius = float(p['radius'])
        sphere_type = str(p.get('sphere_type', 'ICO')).upper()
        if radius < min_dim or sphere_type not in {'ICO', 'UV'}:
            raise ValueError('Sphere requires positive radius and ICO or UV type')
        if sphere_type == 'UV':
            segments = int(p.get('segments', 8))
            rings = int(p.get('rings', 6))
            if not 3 <= segments <= 64 or not 2 <= rings <= 32:
                raise ValueError('UV sphere requires 3–64 segments and 2–32 rings')
            verts = [(0.0, 0.0, radius), (0.0, 0.0, -radius)]
            for r in range(1, rings):
                phi = pi * r / rings
                z = radius * cos(phi)
                ring_r = radius * sin(phi)
                for s in range(segments):
                    theta = 2 * pi * s / segments
                    verts.append((ring_r * cos(theta), ring_r * sin(theta), z))
            faces = []
            for s in range(segments):
                sn = (s + 1) % segments
                faces.append((0, 2 + s, 2 + sn))
            for r in range(1, rings - 1):
                top = 2 + (r - 1) * segments
                bot = 2 + r * segments
                for s in range(segments):
                    sn = (s + 1) % segments
                    faces.append((top + s, bot + s, bot + sn, top + sn))
            last = 2 + (rings - 2) * segments
            for s in range(segments):
                sn = (s + 1) % segments
                faces.append((1, last + sn, last + s))
            parts = [(verts, faces)]
        else:
            detail = int(p.get('subdivisions', 1))
            if detail not in (0, 1):
                raise ValueError('Sphere supports 20 or 80 triangular faces (detail 0 or 1)')
            from math import sqrt
            t = (1 + sqrt(5)) / 2
            verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
            def normalized(v):
                d = sqrt(sum(c * c for c in v))
                return tuple(c / d for c in v)
            verts = [normalized(v) for v in verts]
            faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
            if detail:
                cache = {}
                refined = []
                def midpoint(a, b):
                    key = tuple(sorted((a, b)))
                    if key not in cache:
                        cache[key] = len(verts)
                        verts.append(normalized(tuple((x + y) / 2 for x, y in zip(verts[a], verts[b]))))
                    return cache[key]
                for a, b, c in faces:
                    ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
                    refined.extend(((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)))
                faces = refined
            parts = [([tuple(c * radius for c in v) for v in verts], faces)]
    else:
        raise ValueError('Unknown primitive')

    result = []
    for verts, faces in parts:
        if not pre_rotated:
            verts = [(x * c_rot - y * s_rot, x * s_rot + y * c_rot, z) for x, y, z in verts]
        if validate_bsp:
            if any(abs(c) > 32768 for v in verts for c in v):
                raise ValueError('Primitive exceeds the supported map coordinate range')
            validate(verts, [list(f) for f in faces])
        result.append((verts, faces))
    return result

