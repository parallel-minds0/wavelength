"""ctypes bridge for the compiled native prototype; no Blender internals accessed."""
import ctypes
from pathlib import Path

EXPECTED_ABI = 1

class NativeGrid:
    def __init__(self, library_path):
        path = Path(library_path).expanduser().resolve(strict=True)
        self._library = ctypes.CDLL(str(path))
        version = self._library.wl_native_abi_version
        version.argtypes = []
        version.restype = ctypes.c_uint
        actual = version()
        if actual != EXPECTED_ABI:
            raise RuntimeError(f'Native ABI mismatch: expected {EXPECTED_ABI}, got {actual}')
        self._check = self._library.wl_grid_is_highlight_line
        self._check.argtypes = [ctypes.c_double] * 4 + [ctypes.c_int]
        self._check.restype = ctypes.c_int

    def is_highlight_line(self, coordinate_meters, step_meters, *, origin_meters=0.0,
                          tolerance_meters=1e-7, enabled=True):
        return bool(self._check(coordinate_meters, origin_meters, step_meters,
                                tolerance_meters, int(enabled)))
