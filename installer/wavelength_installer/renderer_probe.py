"""Read-only Blender binary reconnaissance. No injection or modification.

An ELF binary fingerprint is NOT a verified renderer hook. Grid shader strings
may be absent because Blender embeds or transforms shader sources at build time.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct

GRID_MARKERS = (b"grid_frag", b"grid_vert", b"grid_shader", b"grid_flag", b"gridScale", b"gridSteps", b"grid_buf", b"grid_resolve")


def probe_renderer(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Expected a regular executable file")
    digest = hashlib.sha256()
    matches = {token.decode(): [] for token in GRID_MARKERS}
    offset = 0
    tail = b""
    with path.open("rb") as stream:
        header = stream.read(64)
        stream.seek(0)
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk: break
            digest.update(chunk)
            scan = tail + chunk
            base = offset - len(tail)
            for marker in GRID_MARKERS:
                start = 0
                while len(matches[marker.decode()]) < 16:
                    found = scan.find(marker, start)
                    if found < 0: break
                    absolute = base + found
                    if absolute >= offset - len(tail) and absolute >= 0 and absolute not in matches[marker.decode()]:
                        matches[marker.decode()].append(absolute)
                    start = found + 1
            tail = chunk[-64:]
            offset += len(chunk)
    kind = "unknown"
    architecture = "unknown"
    if header[:4] == b"\x7fELF" and len(header) >= 20:
        kind = "ELF64" if header[4] == 2 else "ELF32" if header[4] == 1 else "ELF-unknown"
        endian = "<" if header[5] == 1 else ">" if header[5] == 2 else None
        if endian:
            machine = struct.unpack_from(endian + "H", header, 18)[0]
            architecture = {62: "x86_64", 183: "aarch64", 3: "x86"}.get(machine, f"machine-{machine}")
    elif header[:2] == b"MZ": kind = "PE candidate"
    elif header[:4] in (b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe"): kind = "Mach-O candidate"
    return {"path": str(path), "sha256": digest.hexdigest(), "size": offset,
            "container": kind, "architecture": architecture,
            "grid_marker_offsets": {key: values for key, values in matches.items() if values},
            "verified_renderer_hook": False,
            "note": "Markers are only reconnaissance clues, not patch offsets or proof of a hook."}


def write_probe(path, report_path):
    report = probe_renderer(path)
    target = Path(report_path)
    if target.exists(): raise FileExistsError(f"Refusing to overwrite existing report: {target}")
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return target
