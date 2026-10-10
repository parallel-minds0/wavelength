"""Forced installation with explicit ownership and retained reconciliation backups."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import tempfile
import uuid
from .core import sha256, install_addon
from .lifecycle import (locked, inventory, write_json, replace_file, read_receipt,
                        status, StateError, NativeRequiredError)


def fingerprint(path):
    try:return sha256(path) if path.is_file() else None
    except OSError:return None


def archive(state, reason):
    destination=state/'stale'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+reason+'-'+uuid.uuid4().hex[:8])
    entries=[p for p in state.iterdir() if p.name not in {'lock','stale','backups'} and not p.name.startswith('runtime-') and not (p.is_dir() and (p/'receipt.json').is_file())]
    if not entries:return None
    destination.mkdir(parents=True)
    for entry in entries:shutil.move(str(entry),destination/entry.name)
    return destination


def restore(state, data):
    """Restore owned changes only. External changes are preserved, never guessed."""
    target=Path(data['blender']);addon=Path(data['addon'])
    actual=inventory(addon)
    if actual not in (None,data['addon_inventory'],data['previous_addon_inventory']):
        raise StateError('Add-on changed; refusing to discard edits')
    previous=data['previous_addon_inventory']
    if previous is not None and inventory(state/'original-addon')!=previous:
        raise StateError('Original add-on backup is damaged')
    owned=data.get('native_ownership')=='owned'
    if owned:
        backup=state/'original-blender'
        if not backup.is_file() or sha256(backup)!=data['original_sha256']:
            raise StateError('Original Blender backup is damaged')
        if target.exists() and sha256(target) not in {data['original_sha256'],data['patched_sha256']}:
            raise StateError('Blender changed; refusing to overwrite an external update')
    addon.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.wl-restore-',dir=addon.parent) as folder:
        folder=Path(folder)
        if previous is not None:shutil.copytree(state/'original-addon',folder/'restored')
        # Missing Blender stays missing: uninstall must not recreate a removed application.
        if owned and target.exists() and sha256(target)!=data['original_sha256']:
            replace_file(state/'original-blender',target)
        if actual==data['addon_inventory'] and addon.exists():os.replace(addon,folder/'discarded')
        if previous is not None and not addon.exists():os.replace(folder/'restored',addon)
        data['phase']='removed';write_json(state/'receipt.json',data)


def install_forced(bundle, blender, addons, state, *, require_native=False, prepared_factory=None, addon_name="wavelength", reconcile=True, expected_fingerprint=None, repair_native=False, metadata=None):
    from .deployment import prepare, stage_runtime
    bundle=Path(bundle).resolve();blender=Path(blender).expanduser().resolve()
    addons=Path(addons).expanduser().resolve();state=Path(state).expanduser().resolve();addon=addons/addon_name
    if state==addon or state.is_relative_to(addon) or addon.is_relative_to(state):
        raise ValueError('Installer state and add-on directories must be separate')
    if blender.is_relative_to(state) or blender.is_relative_to(addon):
        raise ValueError('Blender executable must be outside installer state and add-on directories')
    manifest=json.loads((bundle/'bundle.json').read_text());source=(bundle/manifest['addon']).resolve()
    if not source.is_relative_to(bundle) or sha256(source)!=manifest['addon_sha256']:
        raise ValueError('Bundled Python add-on checksum mismatch')
    with locked(state):
        old=read_receipt(state)
        if reconcile and old['phase']=='prepared':
            # Finish a safe rollback first; incompatible/interrupted remnants are retained.
            try:
                from .lifecycle import _restore
                _restore(state,old)
                old=read_receipt(state)
            except (OSError,ValueError,RuntimeError):pass
        initial=fingerprint(blender)
        if expected_fingerprint is not None and initial!=expected_fingerprint:
            raise StateError("Blender changed after native preparation; retry with Blender closed")
        # A killed reconciliation can leave the previous journal in stale/ before
        # the new journal is committed. Recover ownership only from matching bytes.
        if old['phase']!='removed' and not (state/'original-blender').is_file():
            for snapshot in sorted((state/'stale').glob('*'),reverse=True):
                prior=read_receipt(snapshot);backup=snapshot/'original-blender'
                if (prior.get('phase') in {'installed','prepared'} and prior.get('blender')==str(blender)
                    and initial is not None and prior.get('patched_sha256')==initial
                    and prior.get('native_ownership','owned')=='owned' and backup.is_file()
                    and sha256(backup)==prior.get('original_sha256')):
                    old=prior;shutil.copy2(backup,state/'original-blender')
                    if not (state/'original-addon').exists() and (snapshot/'original-addon').is_dir():
                        shutil.copytree(snapshot/'original-addon',state/'original-addon')
                    break
        same=old.get('blender')==str(blender)
        owned=(same and old.get('phase') in {'installed','prepared','removing'} and
               old.get('native_ownership','owned')=='owned' and
               (repair_native or initial in {old.get('patched_sha256'),old.get('original_sha256')}) and (state/'original-blender').is_file() and
               sha256(state/'original-blender')==old.get('original_sha256'))
        previous=inventory(addon)
        try:backup_inventory=inventory(state/'original-addon')
        except (OSError,ValueError):backup_inventory='invalid'
        chain=(old.get('addon')==str(addon) and old.get('phase') in {'installed','prepared','removing'} and
               previous in (None,old.get('addon_inventory'),old.get('previous_addon_inventory')) and
               backup_inventory==old.get('previous_addon_inventory'))
        saved=archive(state,old['phase'])
        try:
            native_target=saved/'original-blender' if owned and old.get('runtime_dir') else blender
            with (prepared_factory(native_target) if prepared_factory else prepare(native_target,strict=False)) as prepared:
                available=prepared.get('native_state')!='unavailable'
                if require_native and not available:raise NativeRequiredError(prepared.get('reason','Native support unavailable'))
                if (fingerprint(blender))!=initial:
                    raise StateError('Blender changed during preparation; retry with Blender closed')
                addons.mkdir(parents=True,exist_ok=True)
                with tempfile.TemporaryDirectory(prefix='.wl-stage-',dir=addons) as folder:
                    folder=Path(folder);staged=install_addon(source,folder)
                    previous_inventory=old['previous_addon_inventory'] if chain else previous
                    if previous_inventory is not None:
                        shutil.copytree(saved/'original-addon' if chain else addon,state/'original-addon')
                    if initial is not None:shutil.copy2(blender,folder/'transaction-blender')
                    if owned:shutil.copy2(saved/'original-blender',state/'original-blender')
                    elif initial is not None:shutil.copy2(blender,state/'original-blender')
                    action=prepared.get('action','patch')
                    changed=(available or prepared.get('restore_only',False)) and action!='keep'
                    runtime_info={}
                    retained=list(old.get('managed_runtimes',[]))
                    if old.get('runtime_dir'):
                        retained.append({'runtime_dir':old['runtime_dir'],'runtime_inventory':old.get('runtime_inventory')})
                    patched=prepared.get('patched')
                    if changed and prepared.get('runtime'):
                        patched,runtime_info=stage_runtime(prepared,state)
                    candidate=state/'patched-blender'
                    if changed:
                        candidate.write_bytes(patched);shutil.copymode(blender,candidate)
                    if available:
                        (staged/'experimental-grid.json').write_text(json.dumps({'native_component':'embedded-grid-shader-prototype','limitations':prepared.get('limitations','')}))
                    data={'schema':2,'version':manifest['version'],'phase':'prepared','blender':str(blender),
                          'addon':str(addon),'original_sha256':old['original_sha256'] if owned else initial,
                          'patched_sha256':sha256(candidate) if changed else initial,
                          'addon_inventory':inventory(staged),'previous_addon_inventory':previous_inventory,
                          'installation_mode':'forced','native_state':'available' if available else 'unavailable',
                          'native_action':action,'native_changed':False,
                          'native_ownership':'owned' if owned else ('adopted' if available and not changed else 'none'),
                          'native_reason':prepared.get('reason',prepared.get('analysis',{}).get('reason','')),
                          'stale_archive':str(saved) if saved else None,'managed_runtimes':retained,**runtime_info}
                    data.update(metadata or {})
                    if prepared.get('recipe'):write_json(state/'experimental-recipe.json',prepared['recipe'])
                    # Record ownership before writing: recovery after a process kill can restore bytes.
                    if changed:data['native_ownership']='owned'
                    write_json(state/'receipt.json',data)
                    swapped=False
                    try:
                        if addon.exists():os.replace(addon,folder/'previous')
                        os.replace(staged,addon);swapped=True
                        if changed:
                            if sha256(blender)!=initial:raise StateError('Blender changed before native deployment')
                            try:replace_file(candidate,blender)
                            except OSError as exc:
                                if require_native:raise NativeRequiredError(str(exc)) from exc
                                if sha256(blender)!=initial:raise StateError('Native write failed after unexpected binary change') from exc
                                data.update(native_state='unavailable',native_action='unavailable',native_reason=str(exc),
                                            patched_sha256=initial,native_ownership='owned' if owned else 'none')
                                (addon/'experimental-grid.json').unlink(missing_ok=True)
                                data['addon_inventory']=inventory(addon)
                            else:data['native_changed']=True
                        data['phase']='installed';write_json(state/'receipt.json',data)
                    except BaseException:
                        if data['native_changed']:replace_file(folder/'transaction-blender',blender)
                        if swapped and addon.exists():shutil.rmtree(addon)
                        if (folder/'previous').exists():os.replace(folder/'previous',addon)
                        raise
                    finally:candidate.unlink(missing_ok=True)
            return status(state)
        except BaseException:
            # Retain failed state too, and restore the previous receipt/backup chain.
            archive(state,'failed')
            if saved:
                for entry in saved.iterdir():
                    if entry.is_dir():shutil.copytree(entry,state/entry.name,dirs_exist_ok=True)
                    else:shutil.copy2(entry,state/entry.name)
            raise
