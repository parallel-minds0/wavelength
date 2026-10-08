"""Run the installer directly from the source tree without a separate add-on ZIP."""
from contextlib import contextmanager
from pathlib import Path
import json,shutil,tempfile,zipfile,ast
from .core import sha256

@contextmanager
def bundle_from_source(root):
    root=Path(root)
    if (root/'bundle.json').is_file():
        yield root;return
    addon=root/'addon/wavelength'
    if not (addon/'__init__.py').is_file():raise ValueError('Expected Wavelength source tree or installer bundle')
    with tempfile.TemporaryDirectory(prefix='wl-source-bundle-') as directory:
        bundle=Path(directory)
        shutil.copytree(root/'patches',bundle/'patches')
        archive=bundle/'addon.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for file in sorted(addon.rglob('*')):
                parts=file.relative_to(addon).parts
                if file.is_symlink():raise ValueError('Symlinks in source add-on are unsupported')
                if file.is_file() and not any(p.startswith('.') or p in {'__pycache__','dev','third-party'} for p in parts) and (file.suffix in {'.py','.md','.svg','.map','.vmf'} or file.name=='LICENSE'):
                    z.write(file,Path('wavelength')/file.relative_to(addon))
        tree=ast.parse((addon/'__init__.py').read_text())
        info=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bl_info' for t in n.targets))
        (bundle/'bundle.json').write_text(json.dumps({'schema':1,'version':'.'.join(map(str,info['version']))+'-pre.alpha','addon':'addon.zip','addon_sha256':sha256(archive)}))
        yield bundle
