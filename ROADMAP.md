# Kiosk Roadmap

Grouped by delivery phase. Each phase is independently shippable.

---

## Phase 1 — Production readiness ✅ DONE (2026-04-21)

**Goal:** make the app safe to deploy to the actual TV without late-night surprises.

| Item | Status | Where |
|---|---|---|
| `KIOSK_SECRET_KEY` env var + prod guard (`FLASK_ENV=production` rejects missing key) | ✅ | [kiosk_app/\_\_init\_\_.py](kiosk_app/__init__.py) |
| Admin password prompt (or `KIOSK_ADMIN_PASSWORD` env var) on first-time `init_db.py` | ✅ | [init_db.py](init_db.py) |
| Separate rotation script for existing admin | ✅ | [scripts/set_admin_password.py](scripts/set_admin_password.py) |
| Rate-limit `/admin` login to 5 POSTs / 15 min per IP (Flask-Limiter) | ✅ verified (6th returns 429) | [kiosk_app/extensions.py](kiosk_app/extensions.py), [blueprints/admin.py](kiosk_app/blueprints/admin.py) |
| Custom 404 / 429 / 500 error pages | ✅ | [templates/404.html](templates/404.html), [templates/429.html](templates/429.html), [templates/500.html](templates/500.html) |
| Rotating file logger (10 MB × 5, INFO level) | ✅ verified (logs/kiosk.log writing) | factory `_configure_logging` |
| Login success/failure logged at INFO/WARNING | ✅ | [blueprints/admin.py](kiosk_app/blueprints/admin.py) |
| Gunicorn + systemd unit with hardened sandboxing | ✅ verified (gunicorn boots factory) | [deploy/kiosk.service](deploy/kiosk.service), [deploy/kiosk.env.example](deploy/kiosk.env.example) |
| Python-based online SQLite backup with retention pruning | ✅ verified (produces `.db.gz`) | [scripts/backup_db.sh](scripts/backup_db.sh) |
| Fix malformed CSS `width: 15px 25 px` | ✅ | [templates/search.html:25](templates/search.html#L25) |
| Dependency manifest | ✅ | [requirements.txt](requirements.txt) |
| Updated README with production deploy walkthrough and env-var table | ✅ | [README.md](README.md) |

**Notes:**
- Flask-Limiter warns about in-memory storage. Fine for a single-worker kiosk; if we go multi-worker, point `RATELIMIT_STORAGE_URI` at Redis.
- `admin.py` at the repo root is now a deprecation shim pointing at `init_db.py` / `scripts/set_admin_password.py`.

---

## Phase 2 — Kiosk UX ✅ DONE (2026-04-21)

**Goal:** make it feel like a real public kiosk, not a web page.

| Item | Status | Where |
|---|---|---|
| **Idle-to-menu timeout** (60 s no touch → redirect `/menu`) | ✅ | [static/js/kiosk-idle.js](static/js/kiosk-idle.js) |
| **Idle screensaver** (120 s → fullscreen slideshow of screensaver images) | ✅ | [static/js/kiosk-idle.js](static/js/kiosk-idle.js) |
| Bigger touch targets (min 60 × 60 px), `:active` mirrors `:hover` | ✅ | [static/css/style.css](static/css/style.css) |
| Tap feedback (ripple wave) | ✅ | [static/js/kiosk-idle.js](static/js/kiosk-idle.js) |
| Language toggle EN / FIL | ✅ | [kiosk_app/i18n.py](kiosk_app/i18n.py), `/set_lang/<lang>` in [blueprints/main.py](kiosk_app/blueprints/main.py) |
| Room search autocomplete | ✅ | `/api/rooms?q=` in [blueprints/main.py](kiosk_app/blueprints/main.py), [templates/search.html](templates/search.html) |

**Notes:**
- `kiosk-idle.js` is auto-injected into every HTML response by the after_request middleware (same pattern as `kiosk-scale.js`).
- Screensaver appends its overlay to `<html>` (not `<body>`) so `position:fixed` isn't trapped inside the body's CSS transform.
- Language preference is stored in `session["lang"]`; menu.html and search.html use `{{ t("key") }}` — extend to other templates as content is translated.

**Ship when:** a first-time visitor can walk up, use it, and walk away without orphaning the last screen.

---

## Phase 3 — Content management

**Goal:** staff update announcements / events / office info without touching code.

| Item | Files |
|---|---|
| Migrate `ANNOUNCEMENTS`, `EVENTS_LIST`, `EVENT_DETAILS`, `OFFICES_*` from [kiosk_app/data/](kiosk_app/data/) to SQLite tables | [init_db.py](init_db.py) — add tables + seed from existing data |
| Admin CRUD routes for each: list / add / edit / delete | new blueprint [blueprints/content.py](kiosk_app/blueprints/content.py) |
| Image upload endpoint with size + MIME check, store under `static/uploads/` | same blueprint |
| `published_at` / `expires_at` columns — expired items auto-hide | schema + query filter |
| Data audit: fix duplicate placeholder dates (many events say "Feb 7, 14, 21") | one-time SQL update after migration |

**Ship when:** staff can publish a new event through `/dashboard` and it appears on `/events` without a redeploy.

---

## Phase 4 — Polish

**Goal:** long-term maintainability and operational insight.

| Item | Notes |
|---|---|
| Base template + `{% extends "base.html" %}` refactor | ~30 templates currently repeat boilerplate |
| Pytest suite — smoke test every route returns 200, basic auth flow | new `tests/`, aim for route coverage first |
| Usage analytics table: log `(path, timestamp)` per request, admin report page | cheap SQLite insert in `after_request` |
| Dockerfile + `docker-compose.yml` for reproducible deploy | new `Dockerfile` |
| Health check endpoint `/healthz` | [blueprints/main.py](kiosk_app/blueprints/main.py) |
| Alt text audit on `<img>` tags | accessibility |

**Ship when:** you can rebuild the kiosk from scratch in under 10 minutes.

---

## Verification (applies to every phase)

- `python3 -m compileall kiosk_app app.py` — syntax clean
- Manual: open http://127.0.0.1:5000/menu on the TV, walk through every top-level nav button
- After Phase 4: `pytest` must pass; `docker compose up` boots a working kiosk

## Notes

- **Top-3 if only three land:** idle-timeout (P2), DB-backed content + admin CRUD (P3), secrets-in-env (P1).
- Phases are ordered by deployment blocker severity, not by interestingness.
- Each phase is scoped so it can be merged without the next one — no flag-day rollouts.
