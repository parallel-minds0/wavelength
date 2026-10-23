#!/usr/bin/env python3
"""Validate Markdown/source contracts; build HTML/PDF; sync packaged Markdown."""
import argparse,ast,hashlib,html,json,os,re,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE_CONFIG=ROOT/'.documentation-source'
DOCS=(ROOT/SOURCE_CONFIG.read_text(encoding='utf-8-sig').strip()).resolve() if SOURCE_CONFIG.is_file() else ROOT/'documentation'
OUT=ROOT/'build/docs'
API=(
 'addon/wavelength/source/profiles.py','addon/wavelength/source/context_policy.py',
 'addon/wavelength/source/procedural.py','addon/wavelength/source/formats.py',
 'addon/wavelength/source/asset_placement.py','addon/wavelength/source/pencil.py',
 'addon/wavelength/source/node_primitives.py','addon/wavelength/source/node_pencil.py',
 'addon/wavelength/source/cutter_solid.py','addon/wavelength/source/build/pipeline.py',
 'installer/wavelength_installer/source_bundle.py',
)
EXTRAS={'TODO.md':'archive/repository-todo.md','native/blender/README.md':'archive/native-build.md',
        'native/blender/VALIDATION.md':'archive/native-validation.md'}

def version():
    tree=ast.parse((ROOT/'addon/wavelength/__init__.py').read_text(encoding='utf-8'))
    value=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bl_info' for t in n.targets))
    return '.'.join(map(str,value['version']))

def sources():
    return sorted(path for base in ('addon/wavelength/source','installer/wavelength_installer','tools') for path in (ROOT/base).rglob('*.py') if '__pycache__' not in path.parts)

def region(text,name):
    lines=text.splitlines();start=[i for i,line in enumerate(lines) if line.strip()==f'# docs:begin {name}'];end=[i for i,line in enumerate(lines) if line.strip()==f'# docs:end {name}']
    if len(start)!=1 or len(end)!=1 or start[0]>=end[0]:raise ValueError(f'Missing or ambiguous source region: {name}')
    return '\n'.join(lines[start[0]+1:end[0]])

def safe_source(value):
    path=(ROOT/value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError(f'Invalid source path: {value}')
    return path

def check():
    screenshots=[];ids=set();samples=0;trees=[]
    for path in sources():trees.append((path,ast.parse(path.read_text(encoding='utf-8'),filename=str(path))))
    for path in DOCS.rglob('*.md'):
        text=path.read_text(encoding='utf-8')
        for source,name in re.findall(r'^```\{code-sample\}\s+(\S+)\s+(\S+)\s*$',text,re.M):
            region(safe_source(source).read_text(encoding='utf-8'),name);samples+=1
        for value in re.findall(r'\{source\}`([^`]+)`',text):
            match=re.fullmatch(r'(.+?)(?::(\d+))?',value);file=safe_source(match[1])
            if match[2] and int(match[2])>len(file.read_text(encoding='utf-8').splitlines()):raise ValueError(f'Invalid source line: {value}')
        for match in re.finditer(r'^```\{screenshot\}\s+(\S+)\n(.*?)^```',text,re.M|re.S):
            key,body=match.groups()
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',key) or key in ids:raise ValueError(f'Invalid/duplicate screenshot ID: {key}')
            ids.add(key);alt=re.search(r'^:alt:\s*(.+)$',body,re.M)
            if not alt:raise ValueError(f'Missing screenshot alt text: {key}')
            screenshots.append(dict(id=key,page=path.relative_to(DOCS).as_posix(),file=f'documentation/screenshots/{key}.png',alt=alt[1],instructions=' '.join(line for line in body.splitlines() if line and not line.startswith(':')),captured=(DOCS/'screenshots'/f'{key}.png').is_file()))
    print(f'Docs checked: {len(trees)} Python modules, {samples} live excerpts, {len(screenshots)} screenshot declarations')
    return screenshots,trees

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')

def signature(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
        args=ast.unparse(node.args)
        return f'{node.name}({args})'+(' -> '+ast.unparse(node.returns) if node.returns else '')
    bases=', '.join(ast.unparse(base) for base in node.bases)
    return 'class '+node.name+('('+bases+')' if bases else '')

def generate_reference(stage,trees):
    inventory=['# Module inventory','','Generated from the current checkout. Source links open local line-anchored viewers.','']
    api=['# Core API contracts','','Signatures/docstrings below are read statically. Undocumented callables are explicitly marked; they are not inferred contracts.','']
    coverage=[]
    for path,tree in trees:
        relative=path.relative_to(ROOT).as_posix();doc=ast.get_docstring(tree) or 'No module docstring yet.'
        inventory += [f'## {relative}', '',doc,'',f'{{source}}`{relative}`','']
        viewer=stage/'_static/code'/(relative+'.html')
        lines='\n'.join(f'<span id="L{i}"><a href="#L{i}">{i:4}</a> {html.escape(line)}</span>' for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1))
        write(viewer,f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{html.escape(relative)}</title><style>body{{font:14px monospace; margin:24px;background:#fafcfb;color:#26343b}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}span:target{{background:#d8f2df}}a{{color:#517e71}}</style><h1>{html.escape(relative)}</h1><pre>{lines}</pre></html>')
        shutil.copyfile(path,viewer.with_suffix(''))
        public=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and not node.name.startswith('_')]
        coverage.append(dict(path=relative,public_symbols=len(public),documented=sum(bool(ast.get_docstring(node)) for node in public),missing=[node.name for node in public if not ast.get_docstring(node)]))
        if relative not in API:continue
        api += [f'## {relative}','',doc,'']
        for node in public:
            api += [f'### {node.name}','','```python',signature(node),'```','',ast.get_docstring(node) or 'No callable docstring yet. Read the source and the Developer Guide before using this internal interface.','',f'{{source}}`{relative}:{node.lineno}`','']
            if isinstance(node,ast.ClassDef):
                for child in node.body:
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)) and (not child.name.startswith('_') or child.name=='__init__'):
                        api += ['```python',signature(child),'```','',ast.get_docstring(child) or 'Implementation method; refer to its source for current behavior.','',f'{{source}}`{relative}:{child.lineno}`','']
    write(stage/'reference/modules.md','\n'.join(inventory));write(stage/'reference/api.md','\n'.join(api))
    write(OUT/'code-coverage.json',json.dumps(coverage,indent=2))

def prepare(stage=None):
    screenshots,trees=check();stage=stage or OUT/'source';stage.mkdir(parents=True,exist_ok=True)
    # Replace only this generated source snapshot, never authored docs or outputs.
    for file in stage.rglob('*'):
        if file.is_file():file.unlink()
    shutil.copytree(DOCS,stage,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    mapping={(DOCS/path.relative_to(DOCS)).resolve():path.relative_to(DOCS).as_posix() for path in DOCS.rglob('*.md')}
    for source,target in EXTRAS.items():
        original=ROOT/source
        if original.is_file():mapping[original.resolve()]=target;write(stage/target,original.read_text(encoding='utf-8'))
    # Rewrite repository Markdown links when an included note lives outside docs/.
    for original,target in mapping.items():
        text=original.read_text(encoding='utf-8').replace('Wavelength','wavelength')
        def rewrite(match):
            label,url=match.groups()
            if re.match(r'[a-z]+:|#',url):return match[0]
            url,sep,anchor=url.partition('#');destination=(original.parent/url).resolve()
            legacy=ROOT/'docs'
            if destination.is_relative_to(legacy):
                destination=(DOCS/destination.relative_to(legacy)).resolve()
            if destination not in mapping and url.startswith('../'):
                destination=(ROOT/url[3:]).resolve()
            if destination in mapping:
                relative=os.path.relpath(mapping[destination],str(Path(target).parent)).replace('\\','/')
                return f'[{label}]({relative}'+('#'+anchor if sep else '')+')'
            return match[0]
        write(stage/target,re.sub(r'\[([^\]]+)\]\(([^)]+)\)',rewrite,text))
    with (stage/'archive/index.md').open('a',encoding='utf-8') as stream:
        stream.write('\n```{toctree}\n:maxdepth: 1\n\nrepository-todo\nnative-build\nnative-validation\n```\n')
    generate_reference(stage,trees)
    metadata=dict(version=version(),source_sha256=hashlib.sha256(''.join(path.read_text(encoding='utf-8') for path,_ in trees).encode()).hexdigest())
    write(stage/'book-metadata.json',json.dumps(metadata,indent=2))
    write(OUT/'screenshots.json',json.dumps(screenshots,indent=2))
    return stage

def sync(stage):
    # A local authoring folder may live beside this working checkout. Keep a
    # generated source mirror so source archives/CI remain self-contained.
    mirror=ROOT/'documentation'
    if DOCS.resolve()!=mirror.resolve():
        for source in DOCS.rglob('*'):
            relative=source.relative_to(DOCS)
            if source.is_file() and not any(part.startswith('.') or part=='__pycache__' for part in relative.parts):
                target=mirror/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    destination=ROOT/'addon/wavelength/documentation/handbook';manifest=destination/'.generated.json'
    previous=json.loads(manifest.read_text()) if manifest.is_file() else []
    files=[path for path in stage.rglob('*') if path.is_file() and (path.suffix=='.md' or 'screenshots' in path.relative_to(stage).parts and path.suffix.lower() in {'.png','.jpg','.jpeg'})]
    current=[path.relative_to(stage).as_posix() for path in files]
    for relative in set(previous)-set(current):
        stale=(destination/relative).resolve()
        if not stale.is_relative_to(destination.resolve()):raise ValueError('Unsafe generated documentation manifest')
        if stale.is_file():stale.unlink()
    for path,relative in zip(files,current):
        target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    write(manifest,json.dumps(current,indent=2))
    print(f'Synced {len(current)} generated Markdown/assets under {destination}')

def main():
    global DOCS
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['check','build','sync'])
    parser.add_argument('--format',choices=['html','pdf','all'],default='all')
    parser.add_argument('--source',type=Path,help='Canonical Markdown source directory (default: documentation/ or local .documentation-source)')
    args=parser.parse_args()
    if args.source:DOCS=args.source.resolve()
    if args.command=='check':check();return
    # Installer packaging may sync while a separate documentation build is reading.
    # Keep their generated source snapshots independent.
    stage=prepare(OUT/'sync-source' if args.command=='sync' else None)
    if args.command=='sync':sync(stage);return
    env=dict(os.environ,WAVELENGTH_DOCS_ROOT=str(ROOT))
    for builder in (['html','pdf'] if args.format=='all' else [args.format]):
        product=OUT/builder/('wavelength-handbook.pdf' if builder=='pdf' else 'index.html')
        if product.is_file():product.unlink()
        result=subprocess.run([sys.executable,'-m','sphinx','-W','--keep-going','-b',builder,'-d',str(OUT/'doctrees'/builder),str(stage),str(OUT/builder)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
        print(result.stdout)
        # rst2pdf can log a fatal rendering error while Sphinx exits successfully.
        if result.returncode or re.search(r'\[ERROR\]|^FAILED$',result.stdout,re.M) or not product.is_file():raise RuntimeError(f'{builder} handbook build failed; inspect the log above')
        if builder=='pdf' and not (product.read_bytes().startswith(b'%PDF-') and b'%%EOF' in product.read_bytes()[-1024:]):raise RuntimeError('Incomplete PDF output')
    print(f'Handbook {version()} built in {OUT}')

if __name__=='__main__':main()
