"""Windows backup capture and manifest-scoped expiry. No Django startup imports.

Capture does not stop writers and never claims atomic database/file consistency.
Expiry is preview-only unless --apply is explicitly supplied.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid

FORMAT = 'ratrace-host-artifact-v1'
MANIFEST = 'artifact.json'


def utcnow():
    return datetime.now(timezone.utc)


def checked(path):
    path = Path(os.path.abspath(path))
    for part in [*reversed(path.parents), path]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Symlinks and reparse points are not permitted.')
    return path


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    root = checked(root)
    result = {}
    for path in sorted(root.rglob('*')):
        checked(path)
        key = path.relative_to(root).as_posix()
        if path.is_dir():
            result[key + '/'] = None
        elif path.is_file():
            result[key] = digest(path)
        else:
            raise ValueError('Unsupported file type in artifact.')
    return result


def protect(root):
    if os.name != 'nt':
        raise ValueError('Capture requires the Windows ACL helper.')
    helper = Path(__file__).resolve().parents[1] / 'deployment/windows/Protect-RatRaceArtifact.ps1'
    # PowerShell 7's module path can prevent Windows PowerShell 5 loading Set-Acl.
    helper_env = {key: value for key, value in os.environ.items() if key.lower() != 'psmodulepath'}
    subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(helper), '-Path', str(root)],
                   check=True, capture_output=True, env=helper_env)
    checked(root)


def read_environment(path):
    values = {}
    for line in checked(path).read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        name, value = name.strip(), value.strip()
        if not separator or not re.fullmatch('[A-Z][A-Z0-9_]*', name) or name in values:
            raise ValueError('Invalid or duplicate environment entry.')
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


def capture(root, environment, pg_bin, sources, release):
    root, environment, pg_bin = checked(root), checked(environment), checked(pg_bin)
    if not root.is_dir():
        raise ValueError('Backup parent must already exist and be reviewed.')
    source_paths = [checked(source) for source in sources]
    for source in source_paths:
        if not source.is_dir() or root == source or root.is_relative_to(source) or source.is_relative_to(root):
            raise ValueError('Backup and source directories must be separate.')
    values = read_environment(environment)
    required = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    if any(not values.get(key) for key in required):
        raise ValueError('Database configuration incomplete.')
    if any('\n' in values[key] or '\r' in values[key] for key in required):
        raise ValueError('Invalid database connection field.')
    if values['POSTGRES_HOST'] != '127.0.0.1' or not values['POSTGRES_PORT'].isdigit():
        raise ValueError('Only explicit loopback PostgreSQL sources are supported.')
    target = root / ('backup-' + utcnow().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    target.mkdir()
    protect(target)
    # Incomplete captures stay unmarked and cannot be pruned automatically.
    config_hash = digest(environment)
    before = [inventory(source) for source in source_paths]
    passfile = target / '.pgpass'
    escape = lambda text: text.replace('\\', '\\\\').replace(':', '\\:')
    passfile.write_text(':'.join(escape(values[key]) for key in required) + '\n', encoding='utf-8')
    child_env = {key: value for key, value in os.environ.items() if not key.upper().startswith('PG')}
    child_env.update(PGPASSFILE=str(passfile), PGCONNECT_TIMEOUT='15', PGAPPNAME='ratrace-backup',
                     PGSSLMODE=values.get('POSTGRES_SSLMODE', 'prefer'))
    args = ['--host=127.0.0.1', '--port=' + values['POSTGRES_PORT'],
            '--username=' + values['POSTGRES_USER'], '--dbname=' + values['POSTGRES_DB'], '--no-password']
    try:
        subprocess.run([str(pg_bin / 'pg_dump.exe'), *args, '--format=custom',
                        '--file=' + str(target / 'database.dump')], env=child_env,
                       check=True, capture_output=True, timeout=3600)
        with (target / 'archive-toc.txt').open('wb') as output:
            subprocess.run([str(pg_bin / 'pg_restore.exe'), '--list', str(target / 'database.dump')],
                           env=child_env, stdout=output, stderr=subprocess.PIPE, check=True, timeout=60)
    finally:
        passfile.unlink(missing_ok=True)
    shutil.copyfile(environment, target / 'protected.env')
    for index, source in enumerate(source_paths):
        shutil.copytree(source, target / ('files-' + str(index)), symlinks=True)
    after = [inventory(source) for source in source_paths]
    copies = [inventory(target / ('files-' + str(index))) for index in range(len(source_paths))]
    if before != after or before != copies or digest(environment) != config_hash or digest(target / 'protected.env') != config_hash:
        raise ValueError('Files changed during capture; artifact remains incomplete.')
    files = inventory(target)
    manifest = dict(format=FORMAT, kind='backup', completed_at=utcnow().isoformat(),
                    release=release, consistency='database-snapshot-and-stable-files-not-coordinated',
                    files=files)
    (target / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return target


def eligible(root, now=None):
    root, now = checked(root), now or utcnow()
    result = []
    if (root / '.hold').exists():
        return result
    for target in sorted(root.iterdir()):
        checked(target)
        if not target.is_dir() or (target / '.hold').exists():
            continue
        marker = target / MANIFEST
        if not marker.is_file():
            continue
        checked(marker)
        data = json.loads(marker.read_text(encoding='utf-8'))
        if data.get('format') != FORMAT or data.get('kind') not in ('backup', 'closed-routine-log'):
            continue
        stamp = datetime.fromisoformat(data['completed_at'])
        if stamp.tzinfo is None:
            raise ValueError('Artifact timestamp must have a timezone.')
        days = 30 if data['kind'] == 'backup' else 90
        if stamp > now - timedelta(days=days):
            continue
        expected = data.get('files')
        if not isinstance(expected, dict) or not expected:
            raise ValueError('Empty or invalid artifact manifest.')
        actual = inventory(target)
        actual.pop(MANIFEST, None)
        if actual != expected:
            raise ValueError('Artifact contents changed; expiry refused.')
        result.append(target)
    return result


def expire(root, apply=False, now=None):
    targets = eligible(root, now)
    if apply:
        # Revalidate the full tree and hold markers immediately before each delete.
        for target in targets:
            if target not in eligible(root, now):
                raise ValueError('Expiry plan changed.')
            checked(target)
            shutil.rmtree(target)
    return targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    backup = commands.add_parser('capture')
    backup.add_argument('--root', required=True)
    backup.add_argument('--environment', required=True)
    backup.add_argument('--pg-bin', required=True)
    backup.add_argument('--source', action='append', default=[])
    backup.add_argument('--release', required=True)
    prune = commands.add_parser('expire')
    prune.add_argument('--root', required=True)
    prune.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'capture':
            print(capture(args.root, args.environment, args.pg_bin, args.source, args.release))
        else:
            for target in expire(args.root, args.apply):
                print(('Deleted: ' if args.apply else 'Would delete: ') + str(target))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # Child stderr or config parse values may contain credentials: never echo them.
        print('Operation failed; retained artifacts require review. Error type: ' + type(exc).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
