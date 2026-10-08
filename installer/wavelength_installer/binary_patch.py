"""Offline, exact-build binary patch engine.

Never modifies the original executable. Recipes must be explicitly verified and
match the exact SHA-256 of the input. A patch recipe is not a renderer hook.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_hex(value: str) -> bytes:
    if not isinstance(value, str) or len(value) % 2:
        raise ValueError('Patch bytes must be even-length hexadecimal strings')
    return bytes.fromhex(value)


def validate_recipe(recipe: dict, original: bytes, *, allow_unverified=False) -> bytes:
    if recipe.get('schema') != 1 or not (recipe.get('verified') is True or (allow_unverified and recipe.get('experimental') is True)):
        raise ValueError('Unverified or unsupported patch recipe')
    if recipe.get('input_sha256') != digest(original):
        raise ValueError('Blender executable SHA-256 mismatch')
    changes = recipe.get('changes')
    if not isinstance(changes, list) or not changes:
        raise ValueError('Recipe must contain verified changes')
    patched = bytearray(original)
    touched = set()
    for change in changes:
        offset = change.get('offset')
        before, after = _decode_hex(change.get('before')), _decode_hex(change.get('after'))
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError('Invalid patch offset')
        if not before or len(before) != len(after) or offset + len(before) > len(original):
            raise ValueError('Invalid patch span; resizing binaries is not supported')
        span = set(range(offset, offset + len(before)))
        if touched.intersection(span):
            raise ValueError('Overlapping patch changes')
        touched.update(span)
        if original[offset:offset + len(before)] != before:
            raise ValueError('Patch precondition bytes do not match')
        patched[offset:offset + len(before)] = after
    result = bytes(patched)
    if digest(result) != recipe.get('output_sha256'):
        raise ValueError('Patched binary checksum does not match verified output')
    if result == original:raise ValueError('Native patch makes no changes')
    return result


def apply_recipe(binary_path, recipe_path, output_path):
    """Produce a patched *copy*, never mutate Blender's installation in place."""
    source = Path(binary_path).resolve(strict=True)
    destination = Path(output_path).absolute()
    if source == destination:
        raise ValueError('Output must not overwrite the original executable')
    if destination.exists():
        raise FileExistsError('Output already exists; refusing overwrite')
    recipe = json.loads(Path(recipe_path).read_text(encoding='utf-8'))
    original = source.read_bytes()
    patched = validate_recipe(recipe, original)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.wavelength-', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(patched)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copymode(source, tmp_path)
        if digest(tmp_path.read_bytes()) != recipe['output_sha256']:
            raise ValueError('Staged binary verification failed')
        os.replace(tmp_path, destination)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    return destination


def restore_copy(original_path, patched_path, restored_path, *, expected_original_sha256):
    """Restore from a verified original into a new path; no in-place mutation."""
    original = Path(original_path).resolve(strict=True)
    if digest(original.read_bytes()) != expected_original_sha256:
        raise ValueError('Original backup checksum mismatch')
    restored = Path(restored_path).absolute()
    if restored.exists() or restored == original or restored == Path(patched_path).resolve():
        raise ValueError('Restore destination must be new and separate')
    restored.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, restored)
    return restored
