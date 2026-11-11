"""ZIP-executable jwDaily Hydration Log installer (stdlib only).

Usage: python3 '/config/20261108 jwDaily Hydration Log v1.1.0.zip' --preflight
       python3 '/config/20261108 jwDaily Hydration Log v1.1.0.zip' --apply
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

COMPONENT='custom_components/jw_daily_hydration_log'
BLUEPRINTS='blueprints/automation/jw_daily_hydration_log'
ROOTS=(COMPONENT,BLUEPRINTS)
PACKAGE_NAME='jwDaily Hydration Log v1.1.0'


def stamp():return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
def sha(payload):return hashlib.sha256(payload).hexdigest()

def manifest_check(archive):
    bad=archive.testzip()
    if bad:raise RuntimeError('ZIP CRC FAILED: '+bad)
    raw=archive.read('PACKAGE_MANIFEST.json')
    manifest=json.loads(raw)
    listed=manifest['files']
    actual=set(archive.namelist())-{'PACKAGE_MANIFEST.json'}
    if set(listed)!=actual:
        raise RuntimeError(f'Unexpected/missing archive member(s): {sorted(set(listed)^actual)}')
    for name, expected in listed.items():
        if name.startswith('/') or '..' in Path(name).parts or '\\' in name:
            raise RuntimeError('Unsafe path in ZIP: '+name)
        if not (name=='__main__.py' or name.startswith(ROOTS) or name.startswith('tests/') or name in ('README.md','CHANGELOG.md','LICENSE','LICENSE-UPSTREAM-MIT','hacs.json')):
            raise RuntimeError('Unapproved archive member: '+name)
        data=archive.read(name)
        if sha(data)!=expected['sha256'] or len(data)!=expected['size']:
            raise RuntimeError('Checksum or size mismatch: '+name)
    return manifest


def paths(config):return [config/COMPONENT,config/BLUEPRINTS]

def verify_root(config):
    if not config.is_dir():raise RuntimeError(f'Config directory not present: {config}')
    if not (config/'custom_components').is_dir():
        raise RuntimeError('Not a Home Assistant config directory (missing custom_components).')


def preflight(config,archive,version):
    verify_root(config)
    manifest=manifest_check(archive)
    existing=[str(p) for p in paths(config) if p.exists()]
    original=(config/'custom_components/personal_hydration_manager').exists()
    old_fork=(config/'custom_components/daily_hydration_log').exists()
    print('jwDaily Hydration Log - STRICT READ-ONLY PREFLIGHT')
    print('Package:',PACKAGE_NAME)
    print('Package files:',len(manifest['files']))
    print('Package SHA-256:',sha(Path(sys.argv[0]).read_bytes()))
    print('ZIP CRC: PASS | FILE HASHES: PASS')
    print('Config directory:',config)
    print('Upstream Personal Hydration Manager present:',original)
    print('Previously named Daily Hydration Log v1.0.0 fork present:',old_fork)
    if old_fork:print('WARNING: old fork history/config is NOT imported. Do not remove it before migration review.')
    print('Existing fork paths:',existing or 'none')
    print('Will NOT modify upstream PHM or any dashboard YAML.')
    next_flag = '--upgrade' if existing else '--apply'
    print('Next action only after approval:', f'python3 {sys.argv[0]!r} {next_flag}')
    return existing


def backup(config, backup_dir, prior):
    if not backup_dir.is_dir():
        raise RuntimeError(f'Backup directory is absent: {backup_dir} (set --backup-dir)')
    filename=f'{stamp()} jwDaily Hydration Log Backup v1.1.0.zip'
    output=backup_dir/filename
    if output.exists():raise RuntimeError('Backup target exists; refusing overwrite: '+str(output))
    inventory=[]
    store_files = sorted((config/'.storage').glob('jw_daily_hydration_log.*')) if (config/'.storage').is_dir() else []
    # Save backing ledgers too. Original PHM and other HA storage is not modified.
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=6) as z:
        for root in prior:
            for f in sorted(root.rglob('*')):
                if f.is_file():
                    rel=str(f.relative_to(config)).replace(os.sep,'/')
                    z.write(f,rel)
                    inventory.append(rel)
        for f in store_files:
            if f.is_file():
                rel = str(f.relative_to(config)).replace(os.sep, '/')
                z.write(f,rel)
                inventory.append(rel)
        z.writestr('backup_metadata.json',json.dumps({'package':PACKAGE_NAME,'prior_roots':[str(p.relative_to(config)) for p in prior],
            'files':inventory,'created_utc':datetime.now(timezone.utc).isoformat()}))
    with ZipFile(output) as z:
        if z.testzip():raise RuntimeError('Backup CRC invalid')
    return output


def restore(config, backup_path, restore_storage=False):
    with ZipFile(backup_path) as z:
        if z.testzip():raise RuntimeError('Rollback backup ZIP CRC FAILED')
        meta=json.loads(z.read('backup_metadata.json'))
        names=set(z.namelist())-{'backup_metadata.json'}
        if set(meta['files'])!=names:raise RuntimeError('Backup inventory mismatch')
        for name in names:
            if not (name.startswith(ROOTS) or name.startswith('.storage/jw_daily_hydration_log.')) or '..' in Path(name).parts or name.startswith('/'):
                raise RuntimeError('Unsafe backup path: '+name)
        for root in paths(config):
            if root.exists():shutil.rmtree(root)
        # Live history is NEVER overwritten or deleted by a normal code rollback.
        # The original ledger is in the backup if an explicit storage rollback is desired.
        if restore_storage:
            for store_file in (config/'.storage').glob('jw_daily_hydration_log.*') if (config/'.storage').is_dir() else []:
                if store_file.is_file():store_file.unlink()
        for name in sorted(names):
            if name.startswith('.storage/') and not restore_storage:
                continue
            dest=config/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(z.read(name))


def install(config, backup_dir, archive, upgrade):
    before=preflight(config,archive,'1.1.0')
    if before and not upgrade:
        raise RuntimeError('Fork already present. No overwrite: review preflight then explicitly use --upgrade.')
    required=[x for x in archive.namelist() if x.startswith(ROOTS) and not x.endswith('/')]
    if not required:raise RuntimeError('No installable files')
    old_roots=[p for p in paths(config) if p.exists()]
    backup_path=backup(config,backup_dir,old_roots)
    print('Backup created:',backup_path,'SHA-256:',sha(backup_path.read_bytes()))
    with tempfile.TemporaryDirectory(prefix='dhl-stage-',dir=config) as workspace:
        staging=Path(workspace)
        for name in required:
            dest=staging/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(archive.read(name))
        for name in required:
            if sha((staging/name).read_bytes())!=sha(archive.read(name)):
                raise RuntimeError('Staging checksum mismatch: '+name)
        try:
            for root in ROOTS:
                dest=config/root
                if dest.exists():shutil.rmtree(dest)
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copytree(staging/root,dest)
            for name in required:
                if sha((config/name).read_bytes())!=sha(archive.read(name)):
                    raise RuntimeError('Installed checksum mismatch: '+name)
            ha=shutil.which('ha')
            if ha:
                checked=subprocess.run([ha,'core','check'],capture_output=True,text=True,timeout=240)
                print('ha core check exit:',checked.returncode)
                print((checked.stdout+'\n'+checked.stderr)[-3500:])
                if checked.returncode!=0:
                    raise RuntimeError(f'ha core check FAILED, exit code {checked.returncode}')
                checker='PASS'
            else:
                checker='NOT_RUN (HA CLI not available; run ha core check before restart)'
            msg=(f'{PACKAGE_NAME}\nDATE UTC: {datetime.now(timezone.utc).isoformat()}\n'
                 f'APPLY: PASS\nZIP CRC: PASS\nFILE HASHES: PASS\n'
                 f'HA CORE CHECK: {checker}\nBACKUP: {backup_path}\n'
                 f'BACKUP SHA256: {sha(backup_path.read_bytes())}\n'
                 f'UPSTREAM MODIFIED: NO\nRESTART AUTOMATICALLY PERFORMED: NO\n'
                 f'Next: restart Home Assistant after confirming check PASS; keep existing profile if already configured.\n')
            report=config/f'{stamp()} jwDaily Hydration Log Install Result v1.1.0.txt'
            report.write_text(msg,encoding='utf8')
            print(msg,'REPORT:',report)
        except Exception:
            print('INSTALL ERROR - restoring the new fork files from the pre-install backup')
            restore(config,backup_path)
            print('ROLLBACK OF NEW DOMAIN: DONE; original PHM not touched')
            raise


def main():
    parser=argparse.ArgumentParser(description=PACKAGE_NAME+' self-contained HA installer')
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--preflight',action='store_true')
    g.add_argument('--apply',action='store_true')
    g.add_argument('--upgrade',action='store_true',help='Explicitly replace existing fork after backup')
    g.add_argument('--rollback',action='store_true',help='Requires --backup PATH')
    parser.add_argument('--backup',type=Path)
    parser.add_argument('--restore-storage',action='store_true',help='DANGEROUS: restore stored ledger too, replacing current history')
    parser.add_argument('--config-dir',type=Path,default=Path('/config'))
    parser.add_argument('--backup-dir',type=Path,default=Path('/backup'))
    args=parser.parse_args()
    with ZipFile(sys.argv[0]) as archive:
        manifest_check(archive)
        if args.rollback:
            if not args.backup:raise RuntimeError('Explicit --backup PATH required for rollback')
            restore(args.config_dir,args.backup,args.restore_storage)
            print('ROLLBACK COMPLETE:',args.backup)
        elif args.preflight:
            preflight(args.config_dir,archive,'1.1.0')
        else:
            install(args.config_dir,args.backup_dir,archive,args.upgrade)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR:',type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(1)
