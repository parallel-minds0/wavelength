"""Read-only probe for Blender 5.2.x overlay grid shader source.

No binary patch is produced. A source match is not a compatible executable patch.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

GRID_FILES = {
    "cpp": "source/blender/draw/engines/overlay/overlay_grid.hh",
    "vertex": "source/blender/draw/engines/overlay/shaders/overlay_grid_vert.glsl",
    "fragment": "source/blender/draw/engines/overlay/shaders/overlay_grid_frag.glsl",
    "shared": "source/blender/draw/engines/overlay/overlay_shader_shared.hh",
}
ANCHORS = {
    "cpp": ("grid_ubo_", "grid_ps_", "grid_flag"),
    "vertex": ("grid_iter", "level"),
    "fragment": ("theme.colors.grid", "out_color"),
    "shared": ("OVERLAY_GridData", "steps"),
}

def probe_source(root: str | Path) -> dict:
    root = Path(root)
    report = {"source_root": str(root.resolve()), "files": {}, "complete": True,
              "renderer_patch_verified": False}
    for kind, rel in GRID_FILES.items():
        path = root / rel
        if not path.is_file():
            report["files"][kind] = {"path": rel, "found": False}
            report["complete"] = False
            continue
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        anchors = {needle: [i for i, line in enumerate(text.splitlines(), 1)
                            if needle in line][:12] for needle in ANCHORS[kind]}
        report["files"][kind] = {"path": rel, "found": True,
                                  "sha256": hashlib.sha256(data).hexdigest(),
                                  "anchors": anchors}
        if any(not hits for hits in anchors.values()):
            report["complete"] = False
    return report

def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("blender_source", help="Unmodified Blender source checkout root")
    p.add_argument("--report", help="Write JSON report")
    args = p.parse_args(argv)
    result = probe_source(args.blender_source)
    rendered = json.dumps(result, indent=2)
    if args.report:
        Path(args.report).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["complete"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
