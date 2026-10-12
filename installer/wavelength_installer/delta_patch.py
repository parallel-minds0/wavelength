"""Apply checksum-bound BSDIFF40 patches using the bundled Python standard library.

Release payloads contain differences, never a Blender runtime. Every patch is
bound to both the original and resulting executable; --force cannot waive either.
"""
import bz2
import hashlib
import json
import platform
import tempfile
import shutil
import urllib.request
from pathlib import Path

MAX_BINARY = 1024 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def integer(data):
    if len(data) != 8:
        raise ValueError('Truncated binary patch integer')
    value = int.from_bytes(data, 'little') & ((1 << 63) - 1)
    return -value if data[7] & 128 else value


def unpack(data, limit):
    decoder = bz2.BZ2Decompressor()
    result = decoder.decompress(data, max_length=limit + 1)
    if len(result) > limit or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid or oversized compressed patch stream')
    return result


def apply(original, patch, entry):
    if digest(original) != entry['input_sha256']:
        raise ValueError('Native patch does not match this Blender executable')
    if digest(patch) != entry['patch_sha256']:
        raise ValueError('Native patch checksum mismatch')
    if patch[:8] != b'BSDIFF40' or len(patch) < 32:
        raise ValueError('Unsupported binary patch format')
    control_size, diff_size, size = (integer(patch[i:i+8]) for i in (8, 16, 24))
    if (control_size < 0 or diff_size < 0 or not 0 < size <= MAX_BINARY
            or size != entry['output_size'] or 32 + control_size + diff_size > len(patch)):
        raise ValueError('Invalid binary patch header')
    controls = unpack(patch[32:32+control_size], min(MAX_BINARY, 24 * (size + 1)))
    differences = unpack(patch[32+control_size:32+control_size+diff_size], size)
    extras = unpack(patch[32+control_size+diff_size:], size)
    result = bytearray()
    old = d = e = 0
    if len(controls) % 24:
        raise ValueError('Truncated patch control stream')
    for i in range(0, len(controls), 24):
        count, extra, seek = (integer(controls[j:j+8]) for j in (i, i+8, i+16))
        if count < 0 or extra < 0 or len(result) + count + extra > size or d+count > len(differences) or e+extra > len(extras):
            raise ValueError('Patch operation exceeds declared bounds')
        block = bytearray(differences[d:d+count])
        # BSDIFF permits reads beyond the original file, treating those bytes as zero.
        start, end = max(0, -old), min(count, len(original)-old)
        for at in range(start, end):
            block[at] = (block[at] + original[old+at]) & 255
        result.extend(block)
        result.extend(extras[e:e+extra])
        d += count
        e += extra
        old += count + seek
    if len(result) != size or d != len(differences) or e != len(extras) or digest(result) != entry['output_sha256']:
        raise ValueError('Patched Blender checksum mismatch')
    return bytes(result)


def host_platform():
    system = platform.system()
    if platform.machine().lower() not in {'amd64', 'x86_64'} or system not in {'Windows', 'Linux'}:
        raise ValueError('Native patches currently target Windows and Linux x86_64')
    return ('windows' if system == 'Windows' else 'linux') + '-x86_64'


def prepare_bytes(original, directory):
    directory = Path(directory).resolve()
    manifest = directory/'manifest.json'
    if not manifest.is_file():
        raise ValueError('This package contains no native binary patches for your Blender. Nothing installed.')
    data = json.loads(manifest.read_text())
    if data.get('schema') != 1:
        raise ValueError('Unsupported native patch manifest')
    sha = digest(original)
    candidates = [entry for entry in data['patches'] if entry['platform'] == host_platform() and entry['input_sha256'] == sha]
    if len(candidates) != 1:
        raise ValueError('No native patch matches this exact Blender executable. --force does not bypass binary compatibility. Nothing installed.')
    entry = candidates[0]
    patch = (directory/entry['file']).resolve()
    if not patch.is_relative_to(directory):
        raise ValueError('Native patch path escapes its package')
    if patch.is_file():
        payload = patch.read_bytes()
    else:
        url = entry.get('url', '')
        if not url.startswith('https://github.com/parallel-minds0/wavelength/releases/download/'):
            raise ValueError('Native patch file is missing and has no trusted download URL')
        with tempfile.TemporaryFile() as staging:
            with urllib.request.urlopen(url, timeout=120) as incoming:
                total = 0
                while block := incoming.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_BINARY: raise ValueError('Native patch download exceeds size limit')
                    staging.write(block)
            staging.seek(0); payload = staging.read()
    return apply(original, payload, entry), entry


def diagnose(binary, directory):
    """Read-only exact-build diagnosis; never execute or modify Blender."""
    path = Path(binary).expanduser().resolve(strict=True)
    value = digest(path.read_bytes())
    manifest = Path(directory)/'manifest.json'
    entries = json.loads(manifest.read_text()).get('patches', []) if manifest.is_file() else []
    for entry in entries:
        if value in {entry['input_sha256'], entry['output_sha256']}:
            installed = value == entry['output_sha256']
            return {'action': 'keep' if installed else 'patch', 'state': 'patched' if installed else 'pristine',
                    'sha256': value, 'platform': entry['platform'],
                    'native_state': 'available' if installed else 'patch-available',
                    'reason': 'Exact native patch fingerprint; startup is checked during installation',
                    'runtime_verified': False}
    return {'action': 'unavailable', 'state': 'unsupported', 'sha256': value,
            'native_state': 'unavailable', 'reason': 'No exact native patch fingerprint in this package'}
