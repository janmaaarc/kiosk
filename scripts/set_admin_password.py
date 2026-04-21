"""Rotate the 'admin' account password.

Usage:
    python scripts/set_admin_password.py
    KIOSK_ADMIN_PASSWORD=newpw python scripts/set_admin_password.py
"""
import os
import sqlite3
import sys
from getpass import getpass

from flask_bcrypt import Bcrypt

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "database.db",
)


def _read_password() -> str:
    env = os.environ.get("KIOSK_ADMIN_PASSWORD")
    if env:
        return env
    if not sys.stdin.isatty():
        sys.exit("No password available. Set KIOSK_ADMIN_PASSWORD or run interactively.")
    while True:
        pw = getpass("New admin password (min 8 chars): ")
        if len(pw) < 8:
            print("Too short. Try again.")
            continue
        if getpass("Confirm password: ") != pw:
            print("Passwords do not match. Try again.")
            continue
        return pw


def main() -> None:
    bcrypt = Bcrypt()
    password_hash = bcrypt.generate_password_hash(_read_password()).decode("utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE admins SET password_hash = ? WHERE username = ?",
            (password_hash, "admin"),
        )
        if cur.rowcount == 0:
            sys.exit("No admin user found. Run init_db.py first.")
        conn.commit()

    print("Admin password updated.")


if __name__ == "__main__":
    main()
