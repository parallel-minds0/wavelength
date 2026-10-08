"""Filesystem locations inside the installed Wavelength package."""
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PACKAGE_ROOT / "source"
ENVIRONMENT_ROOT = PACKAGE_ROOT / "environment"
MODEL_ROOT = ENVIRONMENT_ROOT / "models"
MAP_ROOT = ENVIRONMENT_ROOT / "maps"
SPRITE_ROOT = ENVIRONMENT_ROOT / "sprites"
DOCUMENTATION_ROOT = PACKAGE_ROOT / "documentation"
THIRD_PARTY_ROOT = PACKAGE_ROOT / "third-party"
DEV_ROOT = PACKAGE_ROOT / "dev"
