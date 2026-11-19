"""Persistent feature surface guard. Static presence is not behavioral proof."""
import argparse,ast,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def docs_root(root):
    config=root/'.documentation-source'
    return (root/config.read_text(encoding='utf-8-sig').strip()).resolve() if config.exists() else root/'documentation'


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def capture(root):
    """Do not import bpy or run addon code while discovering its interfaces."""
    entries={}
    def add(kind,path,name,**extra):
        entries[f'{kind}|{path}|{name}']={'kind':kind,'path':path,'name':name,**extra}
    paths=set()
    for folder in ('addon/wavelength/source','installer/wavelength_installer','tools'):
        paths.update(p for p in (root/folder).rglob('*.py') if '__pycache__' not in p.parts)
    paths.update((root/'addon/wavelength').glob('*.py'))
    for path in sorted(paths):
        relative=path.relative_to(root).as_posix();tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        add('module',relative,path.stem,description=ast.get_docstring(tree) or '',digest=digest(ast.dump(tree,include_attributes=False)))
        def walk(body,parent=''):
            for node in body:
                if not isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                    for field,value in ast.iter_fields(node):
                        if isinstance(value,list):walk([v for v in value if isinstance(v,(ast.stmt,ast.ExceptHandler))],parent)
                    continue
                qualified=parent+'.'+node.name if parent else node.name
                kind='class' if isinstance(node,ast.ClassDef) else 'function'
                signature=', '.join(ast.unparse(b) for b in node.bases) if kind=='class' else ast.unparse(node.args)
                add(kind,relative,qualified,signature=signature,digest=digest(ast.dump(node,include_attributes=False)))
                for child in node.body:
                    if isinstance(child,ast.Assign):
                        for target in child.targets:
                            if isinstance(target,ast.Name) and target.id in {'bl_idname','bl_label','bl_space_type','bl_context','bl_keymap'}:
                                add('ui',relative,qualified+'.'+target.id,value=ast.unparse(child.value))
                    if isinstance(child,ast.AnnAssign) and isinstance(child.target,ast.Name):
                        declaration=child.annotation if isinstance(child.annotation,ast.Call) else child.value
                        if isinstance(declaration,ast.Call) and ast.unparse(declaration.func).endswith('Property'):
                            add('setting',relative,qualified+'.'+child.target.id,declaration=ast.unparse(declaration))
                walk(node.body,qualified)
        walk(tree.body)
        for call in (n for n in ast.walk(tree) if isinstance(n,ast.Call)):
            function=ast.unparse(call.func)
            kind='keymap' if function.endswith('.keymap_items.new') else 'gizmo' if function.endswith('.gizmos.new') else 'hook' if ('.handlers.' in function or '.timers.register' in function or function.endswith(('register_class','register_tool'))) else None
            if kind:
                declaration=ast.unparse(call)
                add(kind,relative,declaration)
    for path in sorted((root/'tests').rglob('*.py')):
        if '__pycache__' not in path.parts:
            relative=path.relative_to(root).as_posix()
            add('test',relative,path.stem,digest=digest(ast.dump(ast.parse(path.read_text(encoding='utf-8-sig')),include_attributes=False)))
    for path in sorted((root/'native/blender').glob('*.patch')):
        relative=path.relative_to(root).as_posix();text=path.read_text(encoding='utf-8-sig')
        add('native-patch',relative,path.name,digest=digest(text))
        for name in sorted(set(re.findall(r'^\+\+\+ b/(.+)$',text,re.M))):add('native-file',relative,name)
        added='\n'.join(line[1:] for line in text.splitlines() if line.startswith('+') and not line.startswith('+++'))
        for name in sorted(set(re.findall(r'\bwavelength_[a-zA-Z0-9_]+',added))):add('native-symbol',relative,name)
        for name in sorted(set(re.findall(r'["\']((?:wavelength|wl_|WAVELENGTH_)[a-zA-Z0-9_./]*)["\']',added))):add('native-binding',relative,name)
    for path in sorted((root/'addon/wavelength/environment').rglob('*.json')):
        relative=path.relative_to(root).as_posix()
        value=json.dumps(json.loads(path.read_text(encoding='utf-8-sig')),sort_keys=True)
        add('configuration',relative,path.name,digest=digest(value))
    for path in sorted((root/'addon/wavelength/environment').rglob('*')):
        if path.is_file() and path.suffix.lower() not in {'.json','.py','.pyc'}:
            relative=path.relative_to(root).as_posix()
            add('asset',relative,path.name,digest=hashlib.sha256(path.read_bytes()).hexdigest())
    for folder,pattern in (('native/blender','*.json'),('.github/workflows','*.yml'),('.github/workflows','*.yaml'),('','AGENTS.md')):
        for path in sorted((root/folder).glob(pattern)):
            relative=path.relative_to(root).as_posix();add('build-contract',relative,path.name,digest=digest(path.read_text(encoding='utf-8-sig')))
    ledger=docs_root(root)/'FEATURES.md'
    if ledger.exists():add('ledger','documentation/FEATURES.md','behavioral-contracts',digest=digest(ledger.read_text(encoding='utf-8')))
    return dict(sorted(entries.items()))


def changes(previous,current):
    return {'added':sorted(current.keys()-previous.keys()),'removed':sorted(previous.keys()-current.keys()),
            'changed':sorted(k for k in previous.keys() & current.keys() if previous[k]!=current[k])}


def verify_history(document,path):
    if not path.is_file():raise ValueError('Feature review history is missing; restore it rather than deleting previous decisions')
    if 'history_prefix_sha256' in document:
        data=path.read_bytes();length=document['history_prefix_bytes']
        if len(data)<length or hashlib.sha256(data[:length]).hexdigest()!=document['history_prefix_sha256']:
            raise ValueError('Feature review history was rewritten or truncated; restore its reviewed prefix and append new decisions')


def render(entries):
    lines=['# Complete implementation surface','',
           'Generated by `tools/feature_inventory.py`. Do not edit this snapshot by hand.',
           'See [the feature ledger](../FEATURES.md) for behavioral contracts and limitations.',
           'This lists source presence, not successful registration or passing behavior. Private helpers are included.',
           'Function bodies, settings, test bodies, native patches and configuration are fingerprinted in the adjacent JSON.',
           'A checked-in test is evidence of a regression check, not evidence that it passed in this session.','']
    kinds={}
    for entry in entries.values():kinds[entry['kind']]=kinds.get(entry['kind'],0)+1
    lines+=[' | '.join(f'{key}: {value}' for key,value in sorted(kinds.items())),'']
    for kind in sorted(kinds):
        lines+=['## '+kind.replace('-',' ').title(),'']
        for entry in entries.values():
            if entry['kind']!=kind:continue
            detail=entry.get('declaration',entry.get('value',entry.get('signature',''))).replace('|','\\|').replace('\n',' ')
            lines.append(f"- `{entry['path']}` — `{entry['name']}`"+(f' — `{detail}`' if detail else ''))
        lines.append('')
    return '\n'.join(lines)


def check(root=ROOT,documentation=None):
    root=Path(root);documentation=Path(documentation or docs_root(root))
    baseline=documentation/'reference/feature-surface.json'
    if not baseline.is_file():raise ValueError('Feature inventory baseline is missing; do not rebuild it without reviewing FEATURES.md')
    document=json.loads(baseline.read_text(encoding='utf-8'))
    if document.get('schema')!=1:raise ValueError('Unsupported feature inventory schema')
    verify_history(document,documentation/'developer/feature-changes.md')
    current=capture(root);delta=changes(document['entries'],current)
    if any(delta.values()):
        summary='; '.join(f'{key}: {len(value)}'+(' ('+', '.join(value[:3])+')' if value else '') for key,value in delta.items())
        raise ValueError('Feature inventory changed: '+summary+'. Review FEATURES.md, record affected feature IDs and run tools/feature_inventory.py --update --feature WL-... --reason "...". Removals are not automatically approved.')
    if (documentation/'reference/feature-surface.md').read_text(encoding='utf-8')!=render(current):raise ValueError('Feature surface Markdown is out of sync with its reviewed baseline')
    ledger=(documentation/'FEATURES.md').read_text(encoding='utf-8')
    if not re.search(r'WL-[A-Z0-9]+-\d+',ledger):raise ValueError('Feature ledger must contain stable feature IDs')
    for value in re.findall(r'`((?:source|tests|native|tools|installer)/[^`]+)`',ledger):
        relative='addon/wavelength/'+value if value.startswith('source/') else value
        if not (root/relative).is_file():raise ValueError('Feature ledger evidence path is missing: '+value)
    print(f'Feature inventory checked: {len(current)} tracked entries')
    return current


def update(root,documentation,feature_ids,reason):
    """An explicit review record, never an automatic acceptance in CI."""
    if not reason.strip() or not feature_ids:raise ValueError('Updating the inventory requires --feature and a nonempty --reason')
    ledger=(documentation/'FEATURES.md').read_text(encoding='utf-8')
    for identity in feature_ids:
        if identity not in set(re.findall(r'WL-[A-Z0-9]+-\d+',ledger)):raise ValueError('Unknown feature ID: '+identity)
    baseline=documentation/'reference/feature-surface.json'
    history=documentation/'developer/feature-changes.md'
    if not baseline.exists() and history.exists():raise ValueError('Feature baseline is missing but review history exists; restore the baseline instead of starting over')
    old=json.loads(baseline.read_text(encoding='utf-8')) if baseline.is_file() else {}
    if old:verify_history(old,history)
    ids=sorted(set(re.findall(r'^\|\s*(WL-[A-Z0-9]+-\d+)\s*\|',ledger,re.M)))
    if set(old.get('feature_ids',[]))-set(ids):raise ValueError('Do not delete feature IDs; retain their ledger rows with retired/replaced status and a migration reason')
    previous=old.get('entries',{})
    current=capture(root);delta=changes(previous,current)
    if not any(delta.values()):raise ValueError('No implementation surface changes to record')
    history.parent.mkdir(parents=True,exist_ok=True)
    if not history.exists():history.write_text('# Feature change record\n\nAppend-only review history. A recorded change is not proof of passing behavior.\n',encoding='utf-8')
    lines=['',f'## {datetime.now(timezone.utc).isoformat(timespec="seconds")}','',
           'Features: '+', '.join(feature_ids),'',reason.strip(),'',
           '; '.join(f'{key}: {len(value)}' for key,value in delta.items()),'']
    if previous:
        for key,identities in delta.items():
            if identities:
                lines+=['### '+key.title(),'']
                lines += ['- `'+identity+'`' for identity in identities];lines.append('')
    else:lines+=['Initial reviewed surface; the complete initial inventory is in the reference snapshot.','']
    with history.open('a',encoding='utf-8') as stream:stream.write('\n'.join(lines))
    baseline.parent.mkdir(parents=True,exist_ok=True)
    reviewed_history=history.read_bytes()
    baseline.write_text(json.dumps({'schema':1,'feature_ids':ids,'history_prefix_bytes':len(reviewed_history),'history_prefix_sha256':hashlib.sha256(reviewed_history).hexdigest(),'entries':current},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (documentation/'reference/feature-surface.md').write_text(render(current),encoding='utf-8')
    return delta


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--update',action='store_true')
    parser.add_argument('--feature',action='append',default=[]);parser.add_argument('--reason',default='')
    args=parser.parse_args();documentation=docs_root(ROOT)
    if args.update:print({k:len(v) for k,v in update(ROOT,documentation,args.feature,args.reason).items()})
    else:check(ROOT,documentation)


if __name__=='__main__':main()
