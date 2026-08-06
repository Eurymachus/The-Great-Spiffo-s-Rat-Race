#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    if (
        len(sys.argv) > 1
        and sys.argv[1] == "runserver"
        and os.environ.get("RAT_RACE_CANONICAL_DEV_LAUNCHER") != "1"
    ):
        raise SystemExit(
            "Use the canonical local launcher from the repository root: "
            'powershell.exe -NoProfile -ExecutionPolicy Bypass -File '
            '".\\scripts\\start_website_dev.ps1" -Port 8001 -Background'
        )
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
