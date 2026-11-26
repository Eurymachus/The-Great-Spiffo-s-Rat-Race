"""Staging-only backup checks. Never starts Django or applies retention."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from host_artifacts import FORMAT, MANIFEST, capture, checked, inventory, read_environment


def verify_latest(root, now=None, max_age_hours=30):
    now = now or datetime.now(timezone.utc)
    candidates = []
    for directory in checked(root).glob('backup-*'):
        marker = checked(directory / MANIFEST)
        if not marker.is_file():
            continue
        data = json.loads(marker.read_text(encoding='utf-8'))
        if data.get('format') != FORMAT or data.get('kind') != 'backup':
            raise ValueError('Invalid backup marker')
        stamp = datetime.fromisoformat(data['completed_at'])
        if stamp.tzinfo is None or stamp > now:
            raise ValueError('Invalid backup time')
        candidates.append((stamp, directory, data))
    if not candidates:
        raise ValueError('No complete backup')
    stamp, directory, data = max(candidates, key=lambda item: item[0])
    if now - stamp > timedelta(hours=max_age_hours):
        raise ValueError('Backup is stale')
    actual = inventory(directory)
    actual.pop(MANIFEST)
    if not data.get('files') or actual != data['files']:
        raise ValueError('Backup integrity mismatch')
    return directory


def database_check(values, stopped=False):
    import psycopg
    if values.get('POSTGRES_HOST') != '127.0.0.1' or values.get('POSTGRES_PORT') != '5433':
        raise ValueError('Staging database required')
    with psycopg.connect(host='127.0.0.1', port=5433, dbname=values['POSTGRES_DB'],
                         user=values['POSTGRES_USER'], password=values['POSTGRES_PASSWORD'],
                         connect_timeout=10, options='-c default_transaction_read_only=on') as conn:
        with conn.cursor() as cursor:
            for table in ('operations_referenceupdatejob', 'operations_pzwikiartworksyncjob',
                          'operations_dailyleaderboardjob'):
                # Fixed internal identifiers, never operator input.
                cursor.execute(f"SELECT count(*) FROM {table} WHERE status IN ('queued','running','uncertain')")
                if cursor.fetchone()[0]:
                    raise ValueError('Background queue is not idle')
            if stopped:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                               "AND pid<>pg_backend_pid() AND backend_type='client backend'")
                if cursor.fetchone()[0]:
                    raise ValueError('Other staging database clients remain')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preflight', 'capture', 'check'])
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    try:
        root = checked(args.root)
        if str(root).lower() != r'g:\ratrace_staging':
            raise ValueError('Only the staging installation is supported')
        if args.command == 'check':
            print(verify_latest(root / 'backups'))
        else:
            environment = root / 'config/staging.env'
            values = read_environment(environment)
            database_check(values, stopped=args.command == 'capture')
            if args.command == 'capture':
                print(capture(root / 'backups', environment, root / 'postgres/runtime/pgsql/bin',
                              [root / 'media', root / 'private'], values['RELEASE_ID']))
    except Exception as exc:
        # Never expose connection strings, child stderr or protected configuration.
        print('Staging backup check failed: ' + type(exc).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
