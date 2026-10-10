"""Lifecycle coordination layered over the validated installer transaction engine."""
from contextlib import contextmanager,ExitStack
from pathlib import Path
import json,os,re,shutil,tempfile,uuid
from . import lifecycle as life
from .core import sha256
from .forced import fingerprint


def backup_edits(state,addon):
    if not addon.exists():return None
    destination=state/'backups'/('addon-edits-'+uuid.uuid4().hex)
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(addon,destination,symlinks=True)
    return str(destination)


def check_replace(state,old,blender,addon,force,repair_mode=False):
    if old['phase']=='corrupt':
        if not force:raise life.StateError('Corrupt receipt; use install --force to quarantine it and keep backups')
        return
    if old['phase'] in {'not-installed','removed'}:return
    if old.get('blender')!=str(blender) or old.get('addon')!=str(addon):
        if not force:raise life.StateError('Receipt belongs to another target; use --existing side-by-side or --force to archive it')
        return
    actual=life.inventory(addon)
    if actual not in (None,old['addon_inventory'],old['previous_addon_inventory']) and not force:
        raise life.StateError('Add-on changed; refusing to discard edits. Use --force to back up edits before replacement')
    backup=state/'original-blender'
    if old.get('native_ownership','owned')=='owned' and (not backup.is_file() or fingerprint(backup)!=old['original_sha256']) and not force:
        raise life.StateError('Original Blender backup is damaged; preserve the files or use --force to archive stale state')
    if old.get('previous_addon_inventory') is not None and life.inventory(state/'original-addon')!=old['previous_addon_inventory'] and not force:
        raise life.StateError('Original add-on backup is damaged; use --force to archive stale state')
    if blender.exists() and fingerprint(blender) not in {old.get('original_sha256'),old.get('patched_sha256')} and not force and not repair_mode:
        raise life.StateError('Blender changed; use --force to reconcile the replacement without discarding backups')


@contextmanager
def native_plan(bundle,blender,state,old,*,force,allow_unverified,confirmed,require_native,repair_mode=False):
    from .deployment import prepare
    from .binary_patch import validate_recipe
    if allow_unverified and not confirmed and not force:raise ValueError('Experimental installation requires explicit risk confirmation')
    if force:
        # Runtime-backed launchers must be prepared from the original container.
        base=state/'original-blender' if old.get('runtime_dir') and fingerprint(state/'original-blender')==old.get('original_sha256') else blender
        with prepare(base,strict=False) as prepared:yield prepared
        return
    base=blender
    backup=state/'original-blender'
    if (old.get('phase') not in {'not-installed','removed','corrupt'} and old.get('blender')==str(blender)
        and (repair_mode or fingerprint(blender) in {old.get('patched_sha256'),old.get('original_sha256')})
        and backup.is_file() and fingerprint(backup)==old.get('original_sha256')):base=backup
    if not base.is_file():raise life.NativeRequiredError('Blender is missing; use --force for a Python-only installation')
    recipe_path=life.select_recipe(bundle,base,allow_unverified=allow_unverified)
    if recipe_path:
        recipe=json.loads(recipe_path.read_text());patched=validate_recipe(recipe,base.read_bytes())
        yield {'recipe':recipe,'patched':patched,'native_state':'available','runtime':None,
               'action':'keep' if fingerprint(blender)==recipe['output_sha256'] else 'patch','limitations':''}
    else:
        # Probe beside the installed executable so resource/library lookup stays valid.
        with prepare(base if old.get("runtime_dir") else blender,strict=not repair_mode) as prepared:yield prepared


def _perform_install(bundle,blender,addons,state,*,allow_unverified,confirm_experimental,force,
                     require_native,addon_name='wavelength',metadata=None,repair_mode=False):
    from .forced import install_forced
    bundle=Path(bundle).resolve();blender=Path(blender).expanduser().resolve();addons=Path(addons).expanduser().resolve();state=Path(state).expanduser().resolve()
    old=life.read_receipt(state);addon=addons/addon_name
    check_replace(state,old,blender,addon,force,repair_mode)
    if old.get('phase')=='removing' and old.get('removal_journal'):
        recover_instance(state);old=life.read_receipt(state)
    # Preserve the established fresh-install path and its verified recipe checks.
    fresh=old['phase'] in {'not-installed','removed'} and addon_name=='wavelength' and not metadata
    if fresh:
        return life._install_legacy(bundle,blender,addons,state,allow_unverified=allow_unverified,
                                    confirm_experimental=confirm_experimental,force=force,require_native=require_native)
    expected=fingerprint(blender)
    # All native preparation precedes any instance/add-on modifications.
    with native_plan(bundle,blender,state,old,force=force,allow_unverified=allow_unverified,
                     confirmed=confirm_experimental,require_native=require_native,repair_mode=repair_mode) as prepared:
        if repair_mode and not require_native and prepared.get("native_state")=="unavailable" and blender.is_file():
            from .experimental import analyze,revert_binary
            if analyze(blender.read_bytes())["state"] in {"patched","partial"}:
                prepared={**prepared,"patched":revert_binary(blender.read_bytes()),"restore_only":True,"action":"restore"}
        if (require_native or (not force and not repair_mode)) and prepared.get('native_state')=='unavailable':
            raise life.NativeRequiredError(prepared.get('reason','Native support unavailable'))
        edits=None
        if force and addon.exists() and old.get('addon_inventory')!=life.inventory(addon):edits=backup_edits(state,addon)
        @contextmanager
        def prepared_factory(_):yield prepared
        from .experimental import analyze
        recognized_repair=repair_mode and blender.is_file() and analyze(blender.read_bytes())["state"] in {"pristine","patched","partial"}
        result=install_forced(bundle,blender,addons,state,require_native=require_native or (not force and not repair_mode),
                              prepared_factory=prepared_factory,addon_name=addon_name,reconcile=False,expected_fingerprint=expected,repair_native=recognized_repair,metadata=metadata or {k:old[k] for k in ("instance_id","source_blender","managed_copy") if k in old})
    receipt=life.read_receipt(state)
    receipt.update(installation_mode='forced' if force else 'experimental' if allow_unverified else 'verified',
                   allow_unverified=allow_unverified,addon_name=addon_name)
    if edits:receipt['edited_addon_backup']=edits
    for key in ('instance_id','source_blender','managed_copy'):
        if key in old:receipt[key]=old[key]
    receipt.update(metadata or {})
    life.write_json(state/'receipt.json',receipt)
    return life.status(state)


def install_instance(bundle,blender,addons,state,*,allow_unverified=False,confirm_experimental=False,
                     force=False,require_native=False,existing='replace',instance=None):
    from .instances import select,list_instances
    if existing not in {'replace','side-by-side','abort'}:raise ValueError('Invalid existing-install policy')
    root=Path(state).expanduser().resolve()
    state=select(root,instance)
    blender=Path(blender).expanduser().resolve();addons=Path(addons).expanduser().resolve()
    old=life.read_receipt(state)
    detected=old['phase'] not in {'not-installed','removed'} or (addons/'wavelength').exists()
    if not detected and blender.is_file():
        from .experimental import analyze
        detected=analyze(blender.read_bytes())['state'] in {'patched','partial'}
    if detected and existing=='abort':return {'phase':'cancelled','reason':'Existing installation was left unchanged'}
    if existing!='side-by-side':
        return _perform_install(bundle,blender,addons,state,allow_unverified=allow_unverified,
                                confirm_experimental=confirm_experimental,force=force,require_native=require_native,
                                addon_name=old.get('addon_name',Path(old['addon']).name if old.get('addon') else 'wavelength'))
    version=json.loads((Path(bundle)/'bundle.json').read_text())['version']
    instance_id=re.sub('[^a-zA-Z0-9_-]','_',version)[:50]+'-'+uuid.uuid4().hex[:8]
    child=root/instance_id;copy=blender.with_name(blender.name+'-wavelength-'+instance_id)
    source=blender
    if old.get('blender')==str(blender) and fingerprint(state/'original-blender')==old.get('original_sha256') and (state/'original-blender').is_file():source=state/'original-blender'
    # Side-by-side never bypasses the verified-build policy.
    if not force:life.select_recipe(Path(bundle),source,allow_unverified=allow_unverified)
    created=False;reason=''
    try:
        data=source.read_bytes()
        if data[8:11] in (b'AI\x01',b'AI\x02') or data.startswith(b'#!/'):
            raise OSError('AppImage/launcher layout cannot be independently copied')
        with copy.open('xb') as stream:
            created=True;stream.write(data)
        shutil.copymode(blender,copy)
    except OSError as exc:
        if copy.exists() and not created:
            # An exclusive-create collision is foreign: never remove it.
            raise life.StateError('Cannot create independent Blender copy: '+str(exc)) from exc
        if created:copy.unlink(missing_ok=True);created=False
        reason='Independent native copy unavailable: '+str(exc)
        if require_native or not force:raise life.NativeRequiredError(reason) from exc
    try:
        result=_perform_install(bundle,copy,addons,child,allow_unverified=allow_unverified,
            confirm_experimental=confirm_experimental,force=force,require_native=require_native,
            addon_name='wavelength_'+instance_id.replace('-','_'),
            metadata={'instance_id':instance_id,'source_blender':str(blender),'managed_copy':created})
    except BaseException:
        if created:copy.unlink(missing_ok=True)
        raise
    if reason:
        receipt=life.read_receipt(child);receipt['native_reason']=reason;life.write_json(child/'receipt.json',receipt)
        result=life.status(child)
    result['instance_id']=instance_id;result['state']=str(child)
    result['notice']='Enable only one wavelength add-on at a time; their registered Blender classes would clash.'
    return result


def _native_removal(state,data,force):
    """Plan every native change before mutating either installed component."""
    from .experimental import analyze,revert_binary
    target=Path(data['blender']);notes=[]
    if not target.exists():return None,'missing',['Blender is missing or relocated; its old path was not recreated.']
    current=target.read_bytes();digest=fingerprint(target)
    if data.get('managed_copy'):
        if digest!=data.get('patched_sha256'):
            if not force:raise life.StateError('Managed Blender copy changed; use --force to retain a backup before removal')
            notes.append('Modified managed Blender copy will be backed up before removal.')
        return 'delete','copy-removed',notes
    owned=data.get('native_ownership','owned')=='owned'
    if owned:
        backup=state/'original-blender'
        valid=backup.is_file() and fingerprint(backup)==data.get('original_sha256')
        if not valid and not force:raise life.StateError('Original Blender backup is damaged; use --force for a structural removal attempt')
        if digest not in {data.get('patched_sha256'),data.get('original_sha256')}:
            if not force:raise life.StateError('Blender changed since installation; use --force to preserve the external update')
            return None,'left-unchanged',['Externally replaced Blender was left unchanged.']
        if valid:
            original=backup.read_bytes();inspection=analyze(original)
            if inspection['state'] in {'patched','partial'}:
                return revert_binary(original),'structural',['Restored original shader behavior; formatting may differ from a pristine Blender build.']
            return original,'byte-exact',notes
    inspection=analyze(current)
    if inspection['state'] in {'patched','partial'}:
        return revert_binary(current),'structural',['Adopted native patch removed structurally; restoration is not guaranteed byte-identical.']
    if inspection['state']=='pristine':return None,'already-pristine',notes
    if data.get('native_state')=='available' and not force:
        raise life.StateError('Native shader layout cannot be safely reverted. Use --force to remove Python while leaving unknown native bytes intact.')
    return None,'left-unchanged',['No safely identifiable native patch; executable left unchanged.']


def tree_snapshot(root):
    """Include internal links without traversing them when tracking owned runtimes."""
    root=Path(root)
    if not root.is_dir() or root.is_symlink():return None
    result={}
    for p in sorted(root.rglob('*')):
        key=str(p.relative_to(root))
        if p.is_symlink():result[key]='link:'+os.readlink(p)
        elif p.is_file():result[key]=sha256(p)
    return result


def _rollback_removal(state,data):
    relative=Path(data['removal_journal'])
    if relative.name!=str(relative) or not relative.name.startswith('removal-'):
        raise life.StateError('Invalid removal journal path')
    folder=state/relative;prior=json.loads((folder/'receipt.json').read_text())
    target=Path(data['blender']);addon=Path(data['addon'])
    if (folder/'blender').is_file():
        before=fingerprint(folder/'blender')
        if target.exists() and fingerprint(target) not in {before,data.get('removal_output_sha256')}:
            raise life.StateError('Blender changed during interrupted uninstall; files were retained')
        if not target.exists() or fingerprint(target)!=before:life.replace_file(folder/'blender',target)
    actual=life.inventory(addon)
    if actual not in (None,data.get('removal_addon_before'),data.get('previous_addon_inventory')):
        raise life.StateError('Add-on changed during interrupted uninstall; files were retained')
    if actual!=data.get('removal_addon_before'):
        if addon.exists():shutil.rmtree(addon)
        if (folder/'addon').exists():shutil.copytree(folder/'addon',addon)
    life.write_json(state/'receipt.json',prior)
    shutil.rmtree(folder)
    return life.status(state)


def _cleanup_uninstall(state,data,keep_state):
    notes=[];preserved=[]
    # User edit backups and stale journals may be the only surviving copies of
    # other installs. Move them out of the removed instance, never erase them.
    archive_root=None
    for name in ('backups','stale'):
        source=state/name
        if source.exists():
            if archive_root is None:
                archive_root=state.parent/(state.name+'-uninstalled-'+uuid.uuid4().hex[:8]);archive_root.mkdir()
            shutil.move(str(source),archive_root/name);preserved.append(str(archive_root/name))
    runtimes=list(data.get('managed_runtimes',[]))
    if data.get('runtime_dir'):runtimes.append(data)
    seen=set()
    for runtime in runtimes:
        path=Path(runtime['runtime_dir'])
        if str(path) in seen:continue
        seen.add(str(path))
        if path.parent==state and path.name.startswith('runtime-') and not path.is_symlink():
            expected=runtime.get('runtime_inventory')
            if expected is not None and tree_snapshot(path)==expected:shutil.rmtree(path)
            elif path.exists():notes.append('Runtime retained because its full inventory is unknown or changed: '+str(path))
        else:notes.append('Runtime outside this instance was left unchanged: '+str(path))
    for name in ('original-blender','original-addon','patched-blender','experimental-recipe.json'):
        path=state/name
        if path.is_symlink():path.unlink()
        elif path.is_dir():shutil.rmtree(path)
        else:path.unlink(missing_ok=True)
    if keep_state:life.write_json(state/'receipt.json',data)
    else:(state/'receipt.json').unlink(missing_ok=True)
    return notes,preserved


def uninstall_instance(state,*,force=False,keep_state=False):
    state=Path(state).expanduser().resolve()
    if not state.exists():return {'phase':'removed','summary':'Nothing remains to uninstall.','removed':[],'restored':[],'left':[]}
    with life.locked(state):
        data=life.read_receipt(state)
        if data['phase']=='corrupt':raise life.StateError('Corrupt receipt; repair --force with --blender and --addons before uninstalling')
        if data['phase']=='removing' and data.get('removal_journal'):
            _rollback_removal(state,data);data=life.read_receipt(state)
        if data['phase'] in {'not-installed','removed'}:
            if data['phase']=='removed':_cleanup_uninstall(state,data,keep_state)
            elif not keep_state:(state/'receipt.json').unlink(missing_ok=True)
            result={'phase':'removed','summary':'Nothing remains to uninstall.','removed':[],'restored':[],'left':[]}
        else:
            addon=Path(data['addon']);target=Path(data['blender']);actual=life.inventory(addon)
            edited=actual not in (None,data['addon_inventory'],data['previous_addon_inventory'])
            if edited and not force:raise life.StateError('Add-on changed; refusing to discard edits. Use uninstall --force to back up edits')
            previous=data['previous_addon_inventory']
            if previous is not None and life.inventory(state/'original-addon')!=previous:
                raise life.StateError('Original add-on backup is damaged; restore a valid backup before uninstalling')
            native,restoration,notes=_native_removal(state,data,force)
            if edited:backup_edits(state,addon)
            if data.get('managed_copy') and target.exists() and fingerprint(target)!=data.get('patched_sha256'):
                folder=state/'backups';folder.mkdir(exist_ok=True);shutil.copy2(target,folder/('blender-edits-'+uuid.uuid4().hex))
            journal=state/('removal-'+uuid.uuid4().hex);journal.mkdir()
            life.write_json(journal/'receipt.json',data)
            if target.is_file() and native is not None:shutil.copy2(target,journal/'blender')
            if addon.exists():shutil.copytree(addon,journal/'addon')
            from .binary_patch import digest
            transaction={**data,'phase':'removing','removal_journal':journal.name,'removal_addon_before':actual,
                         'removal_output_sha256':digest(native) if isinstance(native,bytes) else None}
            life.write_json(state/'receipt.json',transaction)
            addon.parent.mkdir(parents=True,exist_ok=True)
            try:
                if native=='delete':target.unlink(missing_ok=True)
                elif isinstance(native,bytes) and native!=target.read_bytes():
                    candidate=journal/'candidate';candidate.write_bytes(native);shutil.copymode(target,candidate);life.replace_file(candidate,target)
                with tempfile.TemporaryDirectory(prefix='.wl-remove-',dir=addon.parent) as temporary:
                    temp=Path(temporary)
                    if previous is not None:shutil.copytree(state/'original-addon',temp/'restored')
                    if addon.exists():os.replace(addon,temp/'removed')
                    if previous is not None:os.replace(temp/'restored',addon)
                data.update(phase='removed',native_restoration=restoration)
                life.write_json(state/'receipt.json',data)
            except BaseException:
                _rollback_removal(state,transaction)
                raise
            shutil.rmtree(journal)
            cleanup_notes,preserved=_cleanup_uninstall(state,data,keep_state)
            result={**data,'removed':['Python add-on']+(['managed Blender copy'] if native=='delete' else []),
                    'restored':(['previous add-on'] if previous is not None else [])+([restoration+' native restoration'] if restoration in {'byte-exact','structural'} else []),
                    'left':notes+cleanup_notes,'preserved_backups':preserved,'summary':'wavelength instance uninstalled.'}
    # Release the flock before removing its inode. Retain other instances/files.
    remaining=[p for p in state.iterdir() if p.name!='lock'] if state.exists() else []
    if not remaining:
        (state/'lock').unlink(missing_ok=True)
        try:state.rmdir()
        except OSError:pass
    return result


def recover_instance(state):
    state=Path(state).expanduser().resolve()
    if not state.exists():return life.status(state)
    with life.locked(state):
        data=life.read_receipt(state)
        if data['phase']=='removing' and data.get('removal_journal'):return _rollback_removal(state,data)
        if data['phase'] in {'installed','removed','not-installed'}:return life.status(state)
        if data['phase']=='corrupt':raise life.StateError('Corrupt receipt; use repair --force with explicit target paths')
        life._restore(state,data)
        return life.status(state)


def repair_instance(bundle,state,*,blender=None,addons=None,force=False,require_native=False):
    state=Path(state).expanduser().resolve();data=life.status(state)
    if data['phase'] in {'not-installed','removed'}:return {**data,'summary':'Nothing to repair; use install.'}
    if data['phase'] in {'prepared','removing'}:
        recover_instance(state);data=life.read_receipt(state)
    if data['phase']=='corrupt' and not force:raise life.StateError('Corrupt receipt; use repair --force --blender PATH --addons PATH')
    target=Path(blender or data.get('blender','')).expanduser().resolve()
    destination=Path(addons or (Path(data['addon']).parent if data.get('addon') else '')).expanduser().resolve()
    if data['phase']=='corrupt' and (blender is None or addons is None):
        raise life.StateError('Corrupt receipt needs explicit --blender and --addons paths for repair')
    if data.get('managed_copy') and not target.exists() and str(target)==data.get('blender'):
        backup=state/'original-blender'
        if backup.is_file() and fingerprint(backup)==data.get('original_sha256'):
            created=False
            try:
                with target.open('xb') as stream:
                    created=True;stream.write(backup.read_bytes())
                shutil.copymode(backup,target)
                return repair_instance(bundle,state,blender=blender,addons=addons,force=force,require_native=require_native)
            except BaseException:
                if created:target.unlink(missing_ok=True)
                raise
    from .experimental import analyze
    native=analyze(target.read_bytes()) if target.is_file() else {'state':'incompatible'}
    healthy=(data['phase']=='installed' and data.get('addon_matches') and data.get('native_matches') and
             (native['state']=='patched' or data.get('installation_mode')=='verified'))
    if healthy:return {**data,'summary':'wavelength is healthy; nothing changed.'}
    # Repair authorizes restoring modified add-on files, but always retains edits.
    if data.get('addon') and Path(data['addon']).exists() and life.inventory(Path(data['addon']))!=data.get('addon_inventory'):
        backup_edits(state,Path(data['addon']))
    if not force and data['phase']!='corrupt':
        # Reapplying the original installation policy is allowed by repair, but
        # external executable replacements still need explicit force.
        actual=fingerprint(target)
        if actual not in {data.get('original_sha256'),data.get('patched_sha256')} and native['state'] not in {'pristine','patched','partial'}:
            raise life.StateError('Blender was replaced with an unknown executable; use repair --force')
    policy_force=force or data.get('installation_mode')=='forced'
    # An edited add-on has already been safely backed up. Reconcile through the
    # existing transaction while preserving the prior true-original add-on chain.
    prior_inventory=data.get('addon_inventory')
    if data.get('addon') and prior_inventory is not None:
        current=life.inventory(Path(data['addon']))
        receipt=life.read_receipt(state)
        if receipt['phase'] not in {'corrupt','not-installed'}:
            receipt['addon_inventory']=current if current is not None else prior_inventory;life.write_json(state/'receipt.json',receipt)
    try:
        result=_perform_install(bundle,target,destination,state,allow_unverified=data.get('installation_mode')=='experimental' or data.get('allow_unverified',False),
                                confirm_experimental=True,force=policy_force,require_native=require_native,
                                addon_name=data.get('addon_name',Path(data['addon']).name if data.get('addon') else 'wavelength'),repair_mode=True)
    except BaseException:
        if prior_inventory is not None and (state/'receipt.json').exists():
            receipt=life.read_receipt(state)
            if receipt['phase']!='corrupt':receipt['addon_inventory']=prior_inventory;life.write_json(state/'receipt.json',receipt)
        raise
    result['summary']='Repaired by replacing the instance; previous files were backed up.'
    return result
