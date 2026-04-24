"""One-off initializer: creates SQLite tables and seeds the admin user.

Idempotent — safe to re-run. Existing data is left alone.

Admin password sources (first match wins):
  1. $KIOSK_ADMIN_PASSWORD environment variable
  2. Interactive prompt (hidden input)

If an admin row already exists, the password is NOT touched.
Use `scripts/set_admin_password.py` to rotate an existing admin password.
"""
import json
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


def _create_tables(cur: sqlite3.Cursor) -> None:
    cur.connection.execute("PRAGMA journal_mode=WAL")
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE,
            password_hash   TEXT
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            building    TEXT,
            floor       TEXT,
            room        TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            image        TEXT,
            desc         TEXT,
            date         TEXT,
            time         TEXT,
            details      TEXT,
            published_at TEXT DEFAULT (datetime('now')),
            expires_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            thumbnail    TEXT,
            file         TEXT,
            published_at TEXT DEFAULT (datetime('now')),
            expires_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS offices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            key          TEXT UNIQUE NOT NULL,
            name         TEXT NOT NULL,
            image        TEXT,
            location     TEXT,
            hours        TEXT,
            desc         TEXT,
            files        TEXT DEFAULT '[]',
            building_url TEXT,
            published_at TEXT DEFAULT (datetime('now')),
            expires_at   TEXT
        );

        CREATE TABLE IF NOT EXISTS building_floors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            building     TEXT NOT NULL,
            floor_number INTEGER NOT NULL,
            floor_label  TEXT NOT NULL,
            floor_image  TEXT,
            UNIQUE(building, floor_number)
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            department     TEXT,
            position       TEXT,
            photo          TEXT,
            schedule_image TEXT,
            room           TEXT,
            building       TEXT,
            office_key     TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid   TEXT UNIQUE NOT NULL,
            name       TEXT NOT NULL,
            role       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )


def _seed_events(cur: sqlite3.Cursor) -> None:
    from kiosk_app.data.events import EVENT_DETAILS, EVENTS_LIST

    existing = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if existing:
        return

    for ev in EVENTS_LIST:
        detail = EVENT_DETAILS.get(ev["id"], {})
        details = detail.get("content", ev.get("details", ""))
        cur.execute(
            """
            INSERT INTO events (title, image, desc, date, time, details, published_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (ev["title"], ev["image"], ev.get("desc", ""), ev.get("date", ""),
             ev.get("time", ""), details),
        )


def _seed_announcements(cur: sqlite3.Cursor) -> None:
    from kiosk_app.data.announcements import ANNOUNCEMENTS

    existing = cur.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    if existing:
        return

    for a in ANNOUNCEMENTS:
        cur.execute(
            """
            INSERT INTO announcements (title, thumbnail, file, published_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (a["title"], a["thumbnail"], a["file"]),
        )


def _seed_offices(cur: sqlite3.Cursor) -> None:
    from kiosk_app.data.offices import OFFICE_DETAILS, OFFICE_SUMMARIES

    existing = cur.execute("SELECT COUNT(*) FROM offices").fetchone()[0]
    if existing:
        return

    detail_map = {d["key"]: d for d in OFFICE_DETAILS}
    for s in OFFICE_SUMMARIES:
        d = detail_map.get(s["key"], {})
        cur.execute(
            """
            INSERT OR IGNORE INTO offices
                (key, name, image, location, hours, desc, files, building_url, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                s["key"], s["name"], s.get("image", ""),
                d.get("location", ""), d.get("hours", ""), d.get("desc", ""),
                json.dumps(d.get("files", [])),
                s.get("building_url", ""),
            ),
        )


def _seed_faculty(cur: sqlite3.Cursor) -> None:
    from kiosk_app.data.faculty import FACULTY

    existing = cur.execute("SELECT COUNT(*) FROM faculty").fetchone()[0]
    if existing:
        return

    for f in FACULTY:
        cur.execute(
            """
            INSERT INTO faculty (name, department, position, photo,
                                 schedule_image, room, building, office_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f["name"],
                f.get("department", ""),
                f.get("position", ""),
                f.get("photo", ""),
                f.get("schedule_image", ""),
                f.get("room", ""),
                f.get("building", ""),
                f.get("office_key", ""),
            ),
        )


def _migrate(conn: sqlite3.Connection) -> None:
    """Non-destructive migrations for existing databases."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(offices)").fetchall()}
    if "building_url" not in cols:
        conn.execute("ALTER TABLE offices ADD COLUMN building_url TEXT")

    faculty_cols = {r[1] for r in conn.execute("PRAGMA table_info(faculty)").fetchall()}
    if "schedule" not in faculty_cols:
        conn.execute("ALTER TABLE faculty ADD COLUMN schedule TEXT DEFAULT '[]'")

    room_cols = {r[1] for r in conn.execute("PRAGMA table_info(rooms)").fetchall()}
    for col, defn in [
        ("pos_left",   "INTEGER DEFAULT 0"),
        ("pos_top",    "INTEGER DEFAULT 0"),
        ("pos_width",  "INTEGER DEFAULT 10"),
        ("pos_height", "INTEGER DEFAULT 10"),
        ("office_key", "TEXT"),
        ("room_color", "TEXT"),
    ]:
        if col not in room_cols:
            conn.execute(f"ALTER TABLE rooms ADD COLUMN {col} {defn}")

    conn.execute(
        """CREATE TABLE IF NOT EXISTS building_floors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            building     TEXT NOT NULL,
            floor_number INTEGER NOT NULL,
            floor_label  TEXT NOT NULL,
            floor_image  TEXT,
            UNIQUE(building, floor_number)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS faculty (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            department     TEXT,
            position       TEXT,
            photo          TEXT,
            schedule_image TEXT,
            room           TEXT,
            building       TEXT,
            office_key     TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid   TEXT UNIQUE NOT NULL,
            name       TEXT NOT NULL,
            role       TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )"""
    )

    _OFFICE_BUILDING_URLS = {
        "Registrar": "/new_admin_building?floor=1",
        "CASHIER":   "/new_admin_building?floor=1",
        "PLACEMENT": "/academic_building?floor=2",
        "Clinic":    "/academic_building?floor=1",
        "LIBRARY":   "/academic_building?floor=4",
        "OSA":       "/academic_building?floor=2",
        "Guidance":  "/academic_building?floor=2",
        "IRGO":      "/tech_building?floor=1",
    }
    _OFFICE_LOCATIONS = {
        "Registrar": "Admin Building, Ground Floor",
        "CASHIER":   "Admin Building, Ground Floor",
        "PLACEMENT": "Academic Building, 2nd Floor",
        "Clinic":    "Academic Building, 1st Floor",
        "LIBRARY":   "Academic Building, 4th Floor",
        "OSA":       "Academic Building, 2nd Floor",
        "Guidance":  "Academic Building, 2nd Floor",
        "IRGO":      "Technology Building",
    }
    for key, url in _OFFICE_BUILDING_URLS.items():
        conn.execute(
            "UPDATE offices SET building_url = ? WHERE key = ?", (url, key)
        )
    for key, loc in _OFFICE_LOCATIONS.items():
        conn.execute(
            "UPDATE offices SET location = ? WHERE key = ?", (loc, key)
        )


def _ensure_rfid_logs(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rfid_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_uid TEXT NOT NULL,
            name TEXT DEFAULT 'Unknown',
            role TEXT DEFAULT 'visitor',
            scanned_at TEXT
        )
    """)


def _seed_rfid_users(cur: sqlite3.Cursor) -> None:
    _RFID_USERS = [
        ("0609475703", "Group 1",       "student"),
        ("0609393591", "Racelis",        "faculty"),
        ("0609057607", "Cesarcris",      "student"),
        ("1226934023", "Ms. Bonifacio",  "faculty"),
        ("1227038391", "Ms. Dilag",      "faculty"),
    ]
    for uid, name, role in _RFID_USERS:
        cur.execute(
            "INSERT OR IGNORE INTO users (rfid_uid, name, role) VALUES (?, ?, ?)",
            (uid, name, role),
        )


def main() -> None:
    bcrypt = Bcrypt()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        _create_tables(cur)
        _migrate(conn)
        _ensure_rfid_logs(conn)
        conn.commit()

        _seed_events(cur)
        _seed_announcements(cur)
        _seed_offices(cur)
        _seed_faculty(cur)
        _seed_rfid_users(cur)
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
