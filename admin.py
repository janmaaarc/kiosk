"""Deprecated. Use one of:

    python init_db.py                      # first-time setup (creates admin)
    python scripts/set_admin_password.py   # rotate existing admin password
"""
import sys

print(__doc__, file=sys.stderr)
sys.exit(1)
