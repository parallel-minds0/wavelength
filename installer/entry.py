"""Launched with the bundled Python in isolated mode, never system Python."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from wavelength_installer.app import main
main()
