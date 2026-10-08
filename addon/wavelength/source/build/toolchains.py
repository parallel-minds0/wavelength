"""Resolve supported compiler names without assuming Windows executable suffixes."""
import os
from pathlib import Path

GOLDSRC = {
    'hlcsg': ('sdHLCSG', 'hlcsg'),
    'hlbsp': ('sdHLBSP', 'hlbsp'),
    'hlvis': ('sdHLVIS', 'hlvis'),
    'hlrad': ('sdHLRAD', 'hlrad'),
}


def resolve_compiler(directory, stage, wrapper=False):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f'Compiler directory does not exist: {directory}')
    bases = GOLDSRC.get(stage, (stage,))
    names = list(bases) + [b + '_x64' for b in bases]
    windows = [b + '.exe' for b in names]
    candidates = windows + names if os.name == 'nt' else names + windows
    # Match actual filesystem spelling, including mixed-case SDHLT releases.
    files = {p.name.casefold(): p for p in directory.iterdir() if p.is_file()}
    for name in candidates:
        path = files.get(name.casefold())
        if path is None:
            continue
        if path.suffix.lower() == '.exe' and os.name != 'nt' and not wrapper:
            raise ValueError(f'{path.name} is a Windows compiler. Select native Linux tools or configure a Wine/Proton wrapper.')
        if path.suffix.lower() != '.exe' and not wrapper and not os.access(path, os.X_OK):
            raise ValueError(f'Compiler is not executable: {path}')
        return path
    raise ValueError(f'Missing {stage} compiler in {directory}. Accepted names: {", ".join(candidates)}')
