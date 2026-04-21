"""One-off initializer: creates SQLite tables and seeds the admin user.

Idempotent — safe to re-run. Existing data is left alone.

Admin password sources (first match wins):
  1. $KIOSK_ADMIN_PASSWORD environment variable
  2. Interactive prompt (hidden input)

If an admin row already exists, the password is NOT touched.
Use `scripts/set_admin_password.py` to rotate an existing admin password.
"""
import os
import sqlite3
import sys
from getpass import getpass

from flask_bcrypt import Bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def _read_admin_password() -> str:
    env = os.environ.get("KIOSK_ADMIN_PASSWORD")
    if env:
        return env

    if not sys.stdin.isatty():
        sys.exit(
            "No password available. Set KIOSK_ADMIN_PASSWORD or run interactively."
        )

    while True:
        pw = getpass("New admin password (min 8 chars): ")
        if len(pw) < 8:
            print("Too short. Try again.")
            continue
        confirm = getpass("Confirm password: ")
        if pw != confirm:
            print("Passwords do not match. Try again.")
            continue
        return pw


def main() -> None:
    bcrypt = Bcrypt()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                building TEXT,
                floor TEXT,
                room TEXT,
                description TEXT
            )
            """
        )
        conn.commit()

        existing = cur.execute(
            "SELECT 1 FROM admins WHERE username = ?", ("admin",)
        ).fetchone()

        if existing:
            print("Database ready. Admin user already exists — password unchanged.")
            return

        password = _read_admin_password()
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        cur.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash),
        )
        conn.commit()
        print("Database ready. Admin user 'admin' created.")


if __name__ == "__main__":
    main()
