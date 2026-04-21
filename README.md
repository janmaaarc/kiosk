# MPC Kiosk

Flask-based campus kiosk for Marikina Polytechnic College: wayfinding, office
directory, events, digital announcements, and an admin area for managing the
rooms database.

## Project layout

```
kiosk/
├── app.py                   # entry point — create_app() + dev server
├── init_db.py               # first-time setup: create tables, seed admin user
├── admin.py                 # deprecated shim (points at init_db.py + scripts)
├── database.db              # SQLite store (rooms, admins)
├── requirements.txt
├── kiosk_app/               # application package
│   ├── __init__.py          # create_app() factory, blueprint registration,
│   │                        # logging, error handlers, kiosk-scale injection
│   ├── extensions.py        # bcrypt, CSRFProtect, Limiter instances
│   ├── db.py                # get_db_connection(), db_connection() ctxmgr
│   ├── auth.py              # login_required decorator
│   ├── blueprints/
│   │   ├── main.py          # /, /menu, /about, /profile, /faculty, /search, /api/rooms
│   │   ├── campus.py        # /campus/*, /floor/*, per-building pages
│   │   ├── announcements.py # /announcements, /announcement-view
│   │   ├── events.py        # /events, /event/<id>
│   │   ├── offices.py       # /office-selection, /office
│   │   ├── admin.py         # /admin (rate-limited), /dashboard, /rooms, etc.
│   │   └── content.py       # /admin/events|announcements|offices CRUD, /admin/upload
│   ├── i18n.py              # EN / FIL string table + get_translator()
│   └── data/                # legacy hardcoded data (superseded by DB in Phase 3)
├── templates/               # Jinja templates (shared, incl. 404/429/500)
├── static/                  # css/, js/, font/, images/, announcements/,
│                            # events/, files/, js/kiosk-scale.js
├── logs/                    # RotatingFileHandler output (auto-created)
├── scripts/
│   ├── backup_db.sh         # SQLite online backup + retention
│   └── set_admin_password.py
├── deploy/
│   ├── kiosk.service        # systemd unit (gunicorn)
│   └── kiosk.env.example    # env var template for production
├── REFERENCE/               # design references + kiosk_s/ archive
└── ROADMAP.md
```

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# First time only: create tables and set admin password
.venv/bin/python init_db.py
# → prompts for password (or set KIOSK_ADMIN_PASSWORD in env)

.venv/bin/python app.py
# → http://127.0.0.1:5000/
```

## Production deployment

The dev server (`app.run`) is for local use only. On the TV host:

```bash
# 1. Install on the device
sudo useradd --system --home /opt/kiosk kiosk
sudo git clone <repo> /opt/kiosk   # or rsync
sudo chown -R kiosk:kiosk /opt/kiosk
sudo -u kiosk python3 -m venv /opt/kiosk/.venv
sudo -u kiosk /opt/kiosk/.venv/bin/pip install -r /opt/kiosk/requirements.txt

# 2. Write /etc/kiosk.env from the template (chmod 600)
sudo cp /opt/kiosk/deploy/kiosk.env.example /etc/kiosk.env
sudo chmod 600 /etc/kiosk.env
# ... edit and set KIOSK_SECRET_KEY ...

# 3. Seed admin and start the service
sudo -u kiosk KIOSK_ADMIN_PASSWORD='...' /opt/kiosk/.venv/bin/python /opt/kiosk/init_db.py
sudo cp /opt/kiosk/deploy/kiosk.service /etc/systemd/system/kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiosk
sudo systemctl status kiosk

# 4. Schedule nightly DB backups
sudo crontab -u kiosk -e
# add: 0 3 * * * /opt/kiosk/scripts/backup_db.sh >> /opt/kiosk/logs/backup.log 2>&1
```

Point the TV's browser at http://127.0.0.1:8000/ (or run nginx in front on
port 80 if you prefer). Reach the app over LAN for admin access.

## Environment variables

| Var | Required? | Purpose |
|---|---|---|
| `KIOSK_SECRET_KEY` | prod | Flask session signing key. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `FLASK_ENV` | prod | Set to `production` to make `create_app()` reject a missing `KIOSK_SECRET_KEY`. |
| `KIOSK_ADMIN_PASSWORD` | optional | Non-interactive password source for `init_db.py` / `set_admin_password.py`. |
| `KIOSK_BACKUP_RETENTION_DAYS` | optional | Days of backups to keep (default 30). |

## Admin password management

```bash
# First-time seed (init_db.py refuses to overwrite existing admin)
.venv/bin/python init_db.py

# Rotate an existing password
.venv/bin/python scripts/set_admin_password.py
```

## Kiosk display scaling

The kiosk is designed for a 1360×768 TV. `static/js/kiosk-scale.js`
auto-injects a scaling transform so every page renders as a fixed 1360×768
stage, then scales uniformly to fit any window. Editors working on a laptop
see the same frame the TV renders — no more "looks good on my laptop, broken
on the TV."

Change `DESIGN_W` / `DESIGN_H` in
[static/js/kiosk-scale.js](static/js/kiosk-scale.js) if the target display
changes.

## Security posture

- CSRF protection is globally enabled (Flask-WTF). Every form template renders
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- `/delete_room/<id>` is POST-only, triggered from a form with a CSRF token on
  `/rooms`.
- `/announcement-view?file=…` looks up `file` in the DB — the response renders
  the DB-stored value, never the raw query parameter.
- `/search` escapes `%` / `_` / `\` before building the `LIKE` prefix.
- `/admin` login is rate-limited to 5 attempts per 15 minutes per IP.
- DB connections use a `db_connection()` context manager so they always close
  on exceptions.
- On successful login, the session is cleared before being re-populated
  (fixation defense).
- Admin login successes and failures are logged at INFO / WARNING level to
  `logs/kiosk.log` (rotating, 10 MB × 5).

## Admin content management

Staff can manage events, announcements, and offices at `/dashboard` after
logging in. Each section supports create, edit, and delete. Images and PDFs
are uploaded via the drag-drop fields (stored under `static/uploads/`).

Setting `expires_at` on any record hides it automatically on the public-facing
pages once the timestamp passes — no redeploy required.

## Known limitations

- No automated test suite yet (Phase 4).
- `kiosk_app/data/*.py` files are kept as a reference but are no longer read
  at runtime; the DB is the source of truth after `init_db.py` has run.
