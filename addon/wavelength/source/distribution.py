"""Deterministic distribution candidates. No Blender or engine dependencies.

Stable cell addresses make paint/density edits local. Mesh surface projection,
mask evaluation and preview are adapters, not sources of placement identity.
"""
import hashlib
import math


def random_value(seed, address, channel):
    data = f'{seed}:{address}:{channel}'.encode('utf-8')
    return int.from_bytes(hashlib.blake2b(data, digest_size=8).digest(), 'little') / 2**64


def candidates(bounds, cell_size, density, seed):
    """Yield stable ID, XY and acceptance variate for density in items/m².

    One square cell may contain several candidate slots. Lowering density removes
    slots without repositioning survivors. No process-randomized hash or global RNG.
    Bounds and spacing are physical world meters, independent of scene units.
    """
    if not all(math.isfinite(v) for v in (*bounds, cell_size, density)):
        raise ValueError('Distribution bounds and settings must be finite')
    if cell_size <= 0 or density < 0:
        raise ValueError('Cell size must be positive and density nonnegative')
    x0, y0, x1, y1 = bounds
    budget = density * cell_size * cell_size
    for y in range(math.floor(y0 / cell_size), math.ceil(y1 / cell_size)):
        for x in range(math.floor(x0 / cell_size), math.ceil(x1 / cell_size)):
            for slot in range(math.ceil(budget)):
                address = f'{x}:{y}:{slot}'
                px = (x + random_value(seed, address, 'x')) * cell_size
                py = (y + random_value(seed, address, 'y')) * cell_size
                if not (x0 <= px < x1 and y0 <= py < y1):
                    continue
                probability = min(1., budget - slot)
                if random_value(seed, address, 'density') < probability:
                    yield address, px, py, random_value(seed, address, 'coverage')


def choose(seed, address, weights):
    if not weights or any(not math.isfinite(w) or w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError('A palette needs positive total prototype weight')
    target = random_value(seed, address, 'prototype') * sum(weights)
    for index, weight in enumerate(weights):
        target -= weight
        if target < 0:
            return index
    return len(weights) - 1
