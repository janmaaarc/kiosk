# MPC Kiosk — Marikina Polytechnic College

A touch-screen campus kiosk built on Flask. It runs on a TV or display at a
physical kiosk stand and gives students, visitors, and staff self-service access
to campus wayfinding, office information, events, digital announcements, and a
faculty directory. All content is managed by admin staff through a built-in
dashboard — no coding required.

---

## Table of Contents

1. [What the kiosk does](#1-what-the-kiosk-does)
2. [Public screens walkthrough](#2-public-screens-walkthrough)
3. [Admin dashboard — managing content](#3-admin-dashboard--managing-content)
4. [Floor plan system — how rooms and buildings work](#4-floor-plan-system--how-rooms-and-buildings-work)
5. [Local development setup](#5-local-development-setup)
6. [Production deployment](#6-production-deployment)
7. [Docker deployment](#7-docker-deployment)
8. [Free cloud hosting options](#8-free-cloud-hosting-options)
9. [Environment variables](#9-environment-variables)
10. [Admin password management](#10-admin-password-management)
11. [CSV bulk room import](#11-csv-bulk-room-import)
12. [File uploads](#12-file-uploads)
13. [Offline / service worker](#13-offline--service-worker)
14. [RFID entry capture](#14-rfid-entry-capture)
15. [Display scaling](#15-display-scaling)
16. [Security overview](#16-security-overview)
17. [Running the test suite](#17-running-the-test-suite)
18. [Project layout](#18-project-layout)

---

## 1. What the kiosk does

| Feature | Description |
|---|---|
| **Interactive campus map** | 20+ buildings with A* routing from the main gate. Click a building to open a slide-in panel with photo, **ENTER BUILDING**, **SHOW DIRECTION**, and **CANCEL**. Route line animates along the roads with a "YOU ARE HERE" pin at the gate. OUTSIDE / INSIDE toggle switches between the campus route and the building's floor plan. |
| **Floor plans** | Every building supports multi-floor plans. The Academic Building ships with 5 hand-drawn SVG floors (Ground, 2nd, 3rd, 4th, 5th), the New Admin Building with 1 SVG floor. Each room is clickable and draws an indoor route line from the building entrance to the room. |
| **In-building search** | Every floor plan has a live search bar that finds rooms across all floors of that building. Match jumps to the correct floor and draws the route automatically. |
| **Full route (outdoor → indoor)** | Click a room → **SHOW FULL ROUTE** → campus map draws the outdoor route, then after 3.5 seconds automatically navigates to the floor plan and draws the indoor route to the specific room. |
| **Office directory** | Offices with location, hours, a live open/closed badge, downloadable forms/memos, an inline PDF viewer, and a **GET DIRECTIONS** link on each office. |
| **Faculty directory** | Browse faculty by department. Each card has a photo, name, department, and a **FIND ON MAP** button when a room and building are assigned. Profiles show a weekly schedule grid fetched live from the database. |
| **Events** | Upcoming and ongoing campus events with images, dates, times, and full details. Client-side pagination (9 per page). |
| **Announcements** | Digital notices and memos with PDF downloads. |
| **RFID personalized entry** | Scanning an RFID card shows the user's name, role badge, and a personalized welcome. The main menu displays a greeting for the scanned user. All scans are logged and viewable in the admin dashboard. |
| **Drag-to-scroll** | IR touch frames that act as a mouse can drag any scrollable area (faculty grid, floor plan sidebar, etc.). Text and image selection are disabled globally on kiosk pages. |
| **Virtual keyboard** | An on-screen QWERTY keyboard appears when any search input is focused — no physical keyboard needed. |
| **Idle timeout** | After 60 seconds of inactivity on public pages, the kiosk clears the session and returns to the lock screen. Admin pages show a 10-second countdown warning before redirecting to the menu. |
| **QR codes** | Every route has a **GENERATE QR CODE** button. QR images are generated server-side at `/qr?data=…&size=…` — works offline. |
| **Offline fallback** | A service worker caches static assets and shows a branded `/offline` page when the network drops. |

---

## 2. Public screens walkthrough

### Lock screen — `/`

The entry screen. A rotating slideshow plays in the background behind a dark
overlay. "WELCOME" is displayed in large text with a blinking "SCAN YOUR RFID
TO ACCESS THE KIOSK" instruction.

- Tap or click anywhere to go directly to the main menu.
- An RFID reader connected via USB auto-redirects to `/rfid?uid=<scanned-uid>`
  when a card is scanned.
- After 60 seconds of inactivity on any public page, the session is cleared
  and the kiosk returns here automatically.

---

### Main menu — `/menu`

A 3×2 grid of large buttons leading to every major section: Faculty, Campus Map,
Office Information, Digital Announcements, Events and Activities, and About Us.

If a user was identified by RFID scan, a personalized greeting and role badge
(FACULTY / STUDENT / VISITOR) are shown at the top of the menu. The role badge
is color-coded: maroon for faculty, blue for students, gray for visitors.

---

### Faculty directory — `/faculty`

Shows all faculty members stored in the database.

- The left sidebar lists department categories. Tap a department to filter.
- The main area shows cards with a circular photo, name, and department.
- Tap a card to open the faculty member's full profile page.
- If the faculty member has a **room and building** assigned, a **FIND ON MAP**
  button appears on their card and navigates directly to that room on the
  floor plan.

---

### Faculty profile — `/profile?…`

Opened by tapping a faculty card. Shows:

- Portrait photo, name, position, and department badge.
- Weekly schedule grid (Monday–Saturday × time slots) if a schedule has been
  configured in the admin.
- A **FIND ON MAP** button linking to the faculty member's building floor plan.
- Left sidebar with department filter buttons (dynamically loaded from the DB).
- Home and Back navigation icons (fixed position, never overlapped by content).

---

### Office directory — `/office-selection` and `/office?name=<key>`

- `/office-selection` lists all active offices as a scrollable sidebar on the
  left. Tap any office to load its detail view on the right.
- The detail view shows:
  - Office name and a photo
  - Location chip (e.g. "New Admin Building, 2nd Floor") — tapping it navigates
    to the building's floor plan
  - Hours chip with a live **OPEN / CLOSED** badge calculated from device time
  - A **GET DIRECTIONS** button that links to the building's floor plan
  - Attached forms and memos as downloadable PDFs
  - An inline PDF preview that opens when a file is tapped

The sidebar search box filters offices by name in real time.

---

### Campus map — `/campus`

The full-campus interactive map.

- Tap any building label to open a slide-in panel on the right with the
  building's photo, **ENTER BUILDING**, **SHOW DIRECTION**, and **CANCEL**.
- **ENTER BUILDING** → jumps directly to that building's floor plan.
- **SHOW DIRECTION** → draws a route line from the main gate to the building.
  A collapsible directions panel slides in from the left with step-by-step
  directions and a "YOU ARE HERE" pin at the gate. The panel can be collapsed
  to a slim **DIR** tab on the left edge and re-expanded by tapping it.
- The top-right of the map shows an **OUTSIDE / INSIDE** toggle and a
  **GENERATE QR CODE** button when directions are active.
- **OUTSIDE / INSIDE** toggle — INSIDE jumps to the building's floor plan
  (carrying the specific room if one was selected).
- **GENERATE QR CODE** → pops up a floating white card with a QR of the
  current directions URL (server-generated, no internet required). Click
  anywhere outside the card to dismiss it.
- `?location=<building>` in the URL automatically draws the route on load.
- `?location=<building> room <room>` draws the outdoor route, then after
  3.5 seconds automatically navigates to the floor plan at the right floor
  with the specific room highlighted and the indoor route drawn.

Buildings without a floor plan are shown at reduced opacity. Buildings with
a working floor plan (Academic, New Admin, IT) are shown at full opacity and
their labels pulse when selected.

---

### Building floor plans — e.g. `/academic_building`, `/it_building`

Each building has its own URL. The floor plan page has:

- A left sidebar with **floor selector buttons** (e.g. `1ST FLOOR`,
  `2ND FLOOR`, etc.). Switching floors fades the current plan before loading.
- A top bar with home / back icons, the building title, a **room search bar**,
  and a **SHOW DIRECTION** link.
- A main area showing the floor plan image with **room rectangles** overlaid
  at their exact positions. Each room is clickable.
- **Room search bar** — live search across every room on every floor of the
  current building. Matches display with a floor label badge. Clicking a match
  on a different floor navigates there automatically.
- Clicking a room opens a slide-up info panel with:
  - Room name + description
  - **DIRECTIONS** list — step-by-step wayfinding text
  - **SHOW FULL ROUTE** button → outdoor route + auto-navigation back to
    this floor plan with the specific room highlighted
  - **OPEN OFFICE PAGE →** button (for rooms linked to an office)
- Clicking a room also draws a **dashed indoor route line** from the
  building entrance up the hallway to the room, with a "YOU ARE HERE" pin at
  the entrance.
- If the page loads with `?location=<room>`, that room is auto-highlighted
  and the indoor route draws on load.

#### Academic Building — 5 hand-drawn SVG floors

| Floor | Rooms |
|---|---|
| 1st (Ground) | Medical & Dental Services, Record & Information Center, MPC Cares, Faculty Room, CR, Quality Assurance Office, Conference Room, Repair & Maintenance, Function Hall |
| 2nd | Director for Student Affairs, Guidance Scholarship & Admission, Placement and Follow-Up, Faculty Room, CR, Classroom, Command Centers |
| 3rd | VP for Admin & Finance, VP for Academic Affairs, Program Chair's Office, Dean for Technology and Instruction, Dean for Graduate School, Classroom, Command Centers |
| 4th | Library, Computer Library, Educational Technology Room, CR |
| 5th | Staff Room, Control Room, CR |

#### New Admin Building — 1 SVG floor

Ground floor rooms with office linkage.

#### IT Building — 3 JPG floors

Client-supplied JPG floor plans for floors 1–3.

All other buildings fall back to an empty placeholder until rooms are added
via the admin dashboard.

Full list of building URLs:

| Building | URL |
|---|---|
| Rodriguez Building | `/rodriguez_building` |
| MIST-NCESTD Dorm | `/mist_ncestd_dorm` |
| MIST-NCESTD Building | `/mist_ncestd_building` |
| Multi-Purpose Building | `/multi_purpose_building` |
| Power Room | `/power_room` |
| Ylagan Hall | `/ylagan_hall` |
| Automotive Building | `/automotive_building` |
| Academic Building | `/academic_building` |
| WAF & RAC Building | `/waf_&_rac_building` |
| New Admin Building | `/new_admin_building` |
| Old Admin Building | `/old_admin_building` |
| FSM Building | `/fsm_building` |
| Civil Tech Building | `/civil_tech_building` |
| WAF & FSM Building | `/waf_&_fsm_building` |
| Tech Building | `/tech_building` |
| Graduate School Building | `/graduate_school_building` |
| Mechanical Building | `/mechanical_building` |
| TE Building | `/te_building` |
| Science Building | `/science_building` |
| IT Building | `/it_building` |

---

### Events — `/events`

Lists all non-expired events. Each event shows an image, title, date range, and
time. Tapping opens the full event detail. Client-side pagination shows 9 events
per page.

### Announcements — `/announcements`

Lists all non-expired digital notices. Tapping an announcement opens its PDF
in a full-screen PDF viewer.

### Room search — `/search`

A form field where visitors type a room number. On submit the page displays the
matching room's building, floor, and description.

### Health check — `/healthz`

Returns `{"status": "ok"}` when the database is reachable.

---

## 3. Admin dashboard — managing content

### Logging in

Go to `/admin`. Default credentials: **username:** `admin` **password:** `kiosk2025`.

After five failed attempts the login form is locked for 15 minutes per IP
address. Change the password immediately after first login in production (see
[Section 10](#10-admin-password-management)).

---

### Dashboard — `/dashboard`

After login the dashboard shows cards for every content section.

---

### Managing Events — `/admin/events`

| Field | Notes |
|---|---|
| Title | Required. Displayed on the events page. |
| Image | Path to an image under `static/`. Use the upload button to fill this automatically. |
| Short description | One-line summary shown in the events list. |
| Date | Free text, e.g. `April 1 – April 30, 2026`. |
| Time | Free text, e.g. `8:00 AM – 12:00 PM`. |
| Details | Full multi-line description shown on the event detail page. |
| Published at | Auto-fills to the current date and time. |
| Expires at | Leave blank to never expire. |

Paginated at 20 items per page.

---

### Managing Announcements — `/admin/announcements`

| Field | Notes |
|---|---|
| Title | Required. |
| Thumbnail | Image shown in the list view. |
| PDF file | The announcement document. Visitors tap to open or download. |
| Published at | Auto-fills to now. |
| Expires at | Leave blank to keep forever. |

---

### Managing Offices — `/admin/offices`

| Field | Notes |
|---|---|
| Key | Unique slug, lowercase, no spaces (e.g. `registrar`). Used in URLs. |
| Display name | The office name shown to visitors. |
| Image | Photo of the office. |
| Location | Short description shown as a chip (e.g. `New Admin Building, 2nd Floor`). |
| Building URL | Select the building this office is in. |
| Office hours | Format `8:00 AM - 5:00 PM` to enable the live open/closed badge. |
| Description | Paragraph shown on the office detail page. |
| Published at / Expires at | Same as events. |

After creating an office, open **Edit** and use the "Files" section to attach
PDF documents (forms, memos).

---

### Managing Rooms — `/admin/rooms`

| Field | Notes |
|---|---|
| Building | Must exactly match the building name in `building_floors`. |
| Floor | Floor number as text (e.g. `1`, `2`). |
| Room | Room name shown on the overlay label. |
| Description | Short description shown in the room info panel. |
| Pos Left / Top / Width / Height | Position as percentages of the floor plan image dimensions. |
| Office Key | If this room belongs to an office, paste the office's Key here. |
| Room Color | Optional CSS color to tint the room rectangle. |

> **Tip:** Open the floor plan image in any image editor, note the pixel
> coordinates of the room rectangle corners, then divide by image dimensions to
> get percentages. For a 1000×800 image, a room at pixel (100, 80) with size
> 150×100 → left=10, top=10, width=15, height=12.5.

---

### Managing Building Floors — `/admin/building-floors`

| Field | Notes |
|---|---|
| Building | Exact building name (e.g. `Rodriguez Building`). |
| Floor Number | Integer. `1` is the ground floor, `2` is the second, etc. |
| Floor Label | Human-readable name on the floor selector button. |
| Floor Plan Image | Path to the floor plan image under `static/`. |

---

### Managing Faculty — `/admin/faculty`

| Field | Notes |
|---|---|
| Name | Required. |
| Department | Used to build the department filter sidebar. |
| Position | Displayed on the profile page (e.g. `Instructor I`). |
| Photo | Portrait photo. |
| Schedule Image | Optional image of the class schedule (legacy). |
| Room | Room name or number (e.g. `IT 202`). Enables the Find on Map button. |
| Building | Building name (e.g. `IT Building`). Required together with Room for map navigation. |
| Office Key | Links the profile to a specific office page. |

**Schedule editor** — at the bottom of the faculty form, add rows to build a
weekly schedule grid. Each row has:

| Field | Notes |
|---|---|
| Day | MON, TUE, WED, THU, FRI, or SAT |
| Time | e.g. `7:30 AM – 9:00 AM` |
| Subject | Subject code or name |
| Section | Class section |
| Room | Room where the class is held |
| Color | Background color for the schedule cell (Yellow, Green, Blue, Cyan, Red, Purple) |

The schedule is stored as JSON and rendered as a grid table on the faculty
profile page. Use **+ Add Row** and the row delete button to manage entries.

---

### RFID Entry Logs — `/admin/rfid-logs`

Shows a paginated table of all RFID scan events: user name, role badge, UID,
and timestamp. Use **Clear All** to wipe the log. Useful for tracking who has
accessed the kiosk and when.

---

## 4. Floor plan system — how rooms and buildings work

The floor plan system is fully database-driven. Here is the complete workflow
to add a new building or update an existing one:

### Step 1 — Prepare the floor plan image

Export the floor plan as a JPEG, PNG, or SVG. Store the file under `static/`
(e.g. `static/images/rodriguez_ground.jpg`).

### Step 2 — Add a building floor row

Go to **Admin → Building Floors → Add**. Fill in:
- Building: `Rodriguez Building`
- Floor Number: `1`
- Floor Label: `Ground Floor`
- Floor Plan Image: `images/rodriguez_ground.jpg`

Repeat for each floor.

### Step 3 — Add rooms for that floor

Go to **Admin → Rooms → Add**. For each room:
- Building: `Rodriguez Building`
- Floor: `1`
- Room: `Room 101`
- Pos Left / Top / Width / Height: percentage coordinates on the image

### Step 4 — Visit the floor plan

Open `/rodriguez_building`. The Ground Floor image appears with room rectangles
at the configured positions.

### Linking a room to an office

Set the **Office Key** field on the room to match the **Key** of an existing
office. The room's info panel will show an **OPEN OFFICE PAGE →** button.

---

## 5. Local development setup

```bash
git clone <repo-url>
cd kiosk

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# First time: create tables and seed admin
.venv/bin/python init_db.py

# Start dev server
.venv/bin/python app.py
# → http://127.0.0.1:5000/
```

Default admin credentials: `admin` / `kiosk2025`

The development server auto-reloads on file changes. Do not use it in
production.

---

## 6. Production deployment

```bash
# 1. Create a system user and copy the project
sudo useradd --system --home /opt/kiosk kiosk
sudo git clone <repo-url> /opt/kiosk
sudo chown -R kiosk:kiosk /opt/kiosk

# 2. Create the virtualenv and install dependencies
sudo -u kiosk python3 -m venv /opt/kiosk/.venv
sudo -u kiosk /opt/kiosk/.venv/bin/pip install -r /opt/kiosk/requirements.txt

# 3. Write the environment file (chmod 600)
sudo cp /opt/kiosk/deploy/kiosk.env.example /etc/kiosk.env
sudo chmod 600 /etc/kiosk.env
# Set KIOSK_SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_hex(32))"

# 4. Initialise the database
sudo -u kiosk KIOSK_ADMIN_PASSWORD='your-strong-password' \
    /opt/kiosk/.venv/bin/python /opt/kiosk/init_db.py

# 5. Install and start the systemd service
sudo cp /opt/kiosk/deploy/kiosk.service /etc/systemd/system/kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiosk
sudo systemctl status kiosk

# 6. Schedule nightly database backups
sudo crontab -u kiosk -e
# Add: 0 3 * * * /opt/kiosk/scripts/backup_db.sh >> /opt/kiosk/logs/backup.log 2>&1
```

The service listens on port 8000. Point the kiosk browser at
`http://127.0.0.1:8000/`. Change the default admin password before going live.

---

## 7. Docker deployment

```bash
cp deploy/kiosk.env.example .env
# Edit .env and set KIOSK_SECRET_KEY

docker compose up -d
# → http://localhost:8000/
```

Volumes mounted from the host:

| Volume | Contents |
|---|---|
| `./database.db` | All content: rooms, events, announcements, offices, faculty, RFID users and logs |
| `./static/uploads/` | Uploaded images and PDFs |
| `./logs/` | Application logs |

Health check: `curl http://localhost:8000/healthz` → `{"status":"ok"}`.

---

## 8. Free cloud hosting options

### Render — `render.com`

1. Create a free account at [render.com](https://render.com).
2. Click **New → Web Service** and connect this GitHub repo.
3. Set:

   | Setting | Value |
   |---|---|
   | **Runtime** | Python 3 |
   | **Build command** | `pip install -r requirements.txt && python init_db.py` |
   | **Start command** | `gunicorn app:app --bind 0.0.0.0:$PORT` |

4. Under **Environment**, add:

   | Key | Value |
   |---|---|
   | `KIOSK_SECRET_KEY` | Any long random string |
   | `FLASK_ENV` | `production` |
   | `KIOSK_ADMIN_PASSWORD` | Your chosen admin password |

**Free tier limits:** Spins down after 15 minutes of inactivity (~30s wake
time). SQLite resets on every redeploy (no persistent disk on the free tier).

---

### Railway — `railway.app`

Railway gives $5 of free credit per month (enough for low-traffic continuous
uptime).

1. Create a free account at [railway.app](https://railway.app).
2. **New Project → Deploy from GitHub repo**.
3. Add environment variables: `KIOSK_SECRET_KEY`, `FLASK_ENV=production`,
   `KIOSK_ADMIN_PASSWORD`.
4. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add a **Volume** mounted at `/app` to persist the SQLite database.

---

### Which one to choose

| | Render | Railway |
|---|---|---|
| Easiest setup | Yes | Yes |
| Always-on | No (free sleeps) | Yes (within credit) |
| Persistent storage | Paid add-on | Volume (included in credit) |
| Custom domain | Yes (free) | Yes (free) |

For a production kiosk on a physical display, the self-hosted deployment
(Section 6) is recommended so the app runs locally without depending on
internet.

---

## 9. Environment variables

| Variable | Required in prod | Purpose |
|---|---|---|
| `KIOSK_SECRET_KEY` | Yes | Flask session signing key. |
| `FLASK_ENV` | Recommended | Set to `production` — app refuses to start if `KIOSK_SECRET_KEY` is missing. |
| `KIOSK_ADMIN_PASSWORD` | Optional | Non-interactive password source for `init_db.py`. |
| `KIOSK_ENABLE_RFID` | Optional | Set to `1` on Raspberry Pi to enable the mfrc522 background watcher. |
| `KIOSK_INTERNAL_URL` | Optional | Base URL for the Pi watcher to call back (default `http://127.0.0.1:8000`). |
| `KIOSK_BACKUP_RETENTION_DAYS` | Optional | Days of backup files to keep (default 30). |

---

## 10. Admin password management

```bash
# First-time setup
.venv/bin/python init_db.py

# Change an existing admin password
.venv/bin/python scripts/set_admin_password.py
```

Default username is `admin`, default password is `kiosk2025`. The password is
hashed with bcrypt — the plain-text is never written to disk. Change it before
going live.

---

## 11. CSV bulk room import

Go to **Admin → Rooms** and click **Import CSV**.

```
building,floor,room,description,pos_left,pos_top,pos_width,pos_height,office_key
Rodriguez Building,1,Room 101,General Classroom,5,10,15,12,
IT Building,2,Lab 201,Computer Laboratory,20,15,25,20,it_lab
```

| Column | Required | Notes |
|---|---|---|
| `building` | Yes | Must match `building_floors` exactly. |
| `floor` | Yes | Floor number as text. |
| `room` | Yes | Room name shown on the overlay. |
| `description` | No | Info panel text. |
| `pos_left/top/width/height` | No | Percentages (default 0/0/10/10). |
| `office_key` | No | Office key to link to. |

Rows with an existing `(building, floor, room)` combination are updated in place.

---

## 12. File uploads

Accepted types:
- Images: JPEG, PNG, WebP, GIF (max 5 MB) → saved to `static/uploads/images/`
- Documents: PDF (max 10 MB) → saved to `static/files/uploads/`

Files are renamed to random UUID filenames. The database stores paths relative
to `static/` (e.g. `uploads/images/3f8a….jpg`).

---

## 13. Offline / service worker

A service worker caches static assets on first visit. When the device loses
internet:

- Failed page navigation requests show the branded `/offline` fallback page.
- Already-cached CSS, fonts, and images continue to load normally.

Cache is versioned (`kiosk-v1`). Stale entries are cleared automatically when
the version changes.

---

## 14. RFID entry capture

### Keyboard-emulation (default, any device)

The lock screen silently captures keystrokes from a USB HID RFID reader:

- Characters accumulate into a buffer.
- On Enter key (or 100 ms timeout with > 4 chars), the browser redirects to
  `/rfid?uid=<scanned-uid>`.

### Raspberry Pi watcher (optional)

```bash
sudo pip install mfrc522 RPi.GPIO spidev

# In /etc/kiosk.env:
KIOSK_ENABLE_RFID=1
KIOSK_INTERNAL_URL=http://127.0.0.1:8000
```

When `KIOSK_ENABLE_RFID=1` is set, `create_app()` starts the hardware watcher
on boot. Without the flag (on a laptop) the watcher stays dormant.

### Server lookup — `/rfid?uid=` and `/check_rfid`

| Route | Method | Purpose |
|---|---|---|
| `/rfid?uid=<uid>` | GET | Looks up UID in `users` table. If found, shows personalized welcome page and saves user to localStorage before redirecting to `/menu`. Unknown UIDs redirect to `/menu` as visitor. All scans are logged to `rfid_logs`. Rate-limited to 30/min. |
| `/check_rfid` | POST (JSON) | Machine-to-machine lookup: `{"uid":"…"}` → `{"status":"authorized","user":{…}}` or `{"status":"unauthorized"}`. Localhost-only. Rate-limited to 60/min. |

### Managing users

```sql
INSERT INTO users (rfid_uid, name, role) VALUES ('AB12CD34', 'Juan dela Cruz', 'student');
```

Roles: `faculty`, `student`, `visitor`. Role determines the badge color
displayed on the welcome screen and menu.

---

## 14a. Server-side QR code generation — `/qr?data=…&size=…`

| Parameter | Required | Notes |
|---|---|---|
| `data` | Yes | String to encode (usually a URL). |
| `size` | No | Pixel size 64–512 (default 200). |

Rate-limited to 60 requests/min. Returns a PNG image. Works offline.

---

## 15. Display scaling

Designed for a **1360 × 768** display. `static/js/kiosk-scale.js` applies a
CSS `transform: scale()` so the layout fills any viewport while preserving the
exact 1360 × 768 frame.

To change the target resolution, update `DESIGN_W` and `DESIGN_H` in
[static/js/kiosk-scale.js](static/js/kiosk-scale.js).

---

## 16. Security overview

| Area | Implementation |
|---|---|
| Password storage | bcrypt hashing via Flask-Bcrypt. Plain text never stored. |
| Admin login rate limit | 5 POST attempts per 15 minutes per IP. |
| CSRF protection | Flask-WTF globally enabled. Every form has a hidden `csrf_token`. |
| SQL injection | All queries use parameterized placeholders. `LIKE` patterns escape `%`, `_`, `\`. |
| Open redirect | `from_building` parameter validated against a fixed allowlist. |
| File uploads | MIME-type whitelist enforced server-side. Files renamed to random UUIDs. |
| Session fixation | Session cleared before writing new admin credentials on login. |
| Search API rate limiting | `/api/search` and `/api/rooms` limited to 60 req/min. |
| Upload rate limiting | `/admin/upload` limited to 30 req/min. |
| Error handling | 404, 429, and 500 errors render branded HTML pages. 500 errors logged with full tracebacks. |
| Logging | Admin logins written to `logs/kiosk.log` (rotating, 10 MB × 5 files). |

---

## 17. Running the test suite

```bash
.venv/bin/pytest tests/ -q
```

Tests cover:
- All major public routes return HTTP 200
- Health check endpoint returns correct JSON
- Menu page injects kiosk scripts
- Search endpoint (GET and POST, empty and matching queries)
- Admin login, logout, and session protection
- Admin CRUD for rooms, events, announcements, offices
- 404 error page
- `/rfid?uid=` redirect and user profile rendering
- `/check_rfid` JSON endpoint (authorised / unauthorised / missing UID)
- `/qr?data=` PNG generation + missing-data rejection

Each test run uses an isolated temporary database. No test touches `database.db`.

---

## 18. Project layout

```
kiosk/
├── app.py                        Entry point — dev server
├── init_db.py                    First-time DB setup, schema migrations, admin seed
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── database.db                   SQLite store (tracked in git with seed data)
│
├── kiosk_app/
│   ├── __init__.py               create_app() factory; auto-creates default admin
│   │                             on startup if none exists; injects kiosk scripts
│   ├── extensions.py             bcrypt, CSRFProtect, Limiter singletons
│   ├── db.py                     db_connection() context manager
│   ├── auth.py                   login_required decorator
│   ├── rfid.py                   Optional Pi-only mfrc522 watcher
│   └── blueprints/
│       ├── main.py               /, /menu, /faculty, /profile, /search,
│       │                         /api/search, /api/rooms, /api/departments,
│       │                         /api/faculty/<id>/schedule,
│       │                         /rfid, /check_rfid, /qr, /offline, /healthz
│       ├── campus.py             /campus, all /building_name routes,
│       │                         _floor_plan() helper, _ACADEMIC_FLOORS,
│       │                         _NEW_ADMIN_FLOORS, _ENTRANCE_BY_FLOOR
│       ├── offices.py            /office-selection, /office
│       ├── announcements.py      /announcements, /announcement-view
│       ├── events.py             /events, /event/<id>
│       ├── admin.py              /admin login, /dashboard, /rooms CRUD,
│       │                         /rooms/import-csv
│       └── content.py            /admin/events|announcements|offices|
│                                 building-floors|faculty CRUD,
│                                 /admin/rfid-logs, /admin/rfid-logs/clear,
│                                 /admin/upload
│
├── templates/
│   ├── _breadcrumb.html
│   ├── floor_plan.html           Generic floor plan renderer (all buildings)
│   ├── index.html                Lock screen with RFID capture + slideshow
│   ├── menu.html                 Main menu grid + personalized greeting
│   ├── faculty.html              Faculty directory with department sidebar
│   ├── profile.html              Faculty profile with schedule grid + map link
│   ├── rfid_scan.html            RFID welcome screen (role-coded, auto-redirect)
│   ├── office.html               Office detail + file list + PDF viewer
│   ├── office_selection.html     Office list sidebar
│   ├── campus.html               Interactive campus map + A* routing
│   ├── events.html               Events list + client-side pagination
│   ├── rooms.html                Admin rooms list + CSV import
│   ├── offline.html              Offline fallback page
│   ├── 404.html / 429.html / 500.html
│   └── admin/
│       ├── base.html             Admin layout with sidebar nav
│       ├── building_floors.html
│       ├── building_floor_form.html
│       ├── faculty_list.html
│       ├── faculty_form.html     Faculty editor with schedule row builder
│       ├── rfid_logs.html        RFID scan log table + clear button
│       └── …                    Event, announcement, office forms
│
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── kiosk-scale.js        Auto-scales every page to 1360×768
│   │   ├── kiosk-idle.js         60s idle → lock screen; admin countdown modal
│   │   ├── drag-scroll.js        Drag-to-scroll for IR touch frames
│   │   ├── keyboard.js           On-screen QWERTY keyboard for search inputs
│   │   ├── toast.js              window.toast() notification utility
│   │   ├── kiosk.js              Shared utilities
│   │   └── slideshow.js          Lock screen slide rotation
│   ├── sw.js                     Service worker (cache-first assets,
│   │                             network-first navigation, offline fallback)
│   ├── font/                     LeagueSpartan variable font
│   ├── images/
│   │   ├── icon/                 Home / back / menu icons
│   │   ├── building/             Campus map building photos
│   │   ├── floor_plans/          Hand-drawn SVGs + client JPGs
│   │   │   ├── academic_ground.svg … academic_5th.svg
│   │   │   ├── new_admin_f1.svg  New Admin Building ground floor
│   │   │   └── IT_1ST.JPG / IT_2ND.JPG / IT_3RD.JPG
│   │   ├── offices/              Office cover photos
│   │   ├── screensaver/          Lock screen slideshow images (slide1–4.png)
│   │   └── KIOSK BACKGROUND.png  Menu and faculty page background
│   ├── files/
│   │   └── uploads/              Admin-uploaded PDF documents
│   └── uploads/
│       └── images/               Admin-uploaded photos
│
├── logs/                         Rotating app logs (auto-created)
├── tests/                        pytest suite
├── scripts/
│   ├── backup_db.sh
│   └── set_admin_password.py
└── deploy/
    ├── kiosk.service
    └── kiosk.env.example
```

---

## Database tables reference

| Table | Purpose |
|---|---|
| `admins` | Admin login credentials (username + bcrypt hash) |
| `rooms` | Individual rooms with building, floor, position, and optional office link |
| `offices` | Office directory entries with hours, location, files, and building link |
| `events` | Campus events with image, date, time, and expiry |
| `announcements` | Digital notices with thumbnail and PDF attachment |
| `building_floors` | Floor plan images and labels for each building floor |
| `faculty` | Faculty members with department, photo, room, schedule JSON, and office link |
| `users` | RFID UID → name + role (used by `/rfid?uid=` for personalized entry) |
| `rfid_logs` | Timestamped record of every RFID scan: uid, name, role |

All content tables have `published_at` and `expires_at` columns. Records with
a past `expires_at` are automatically excluded from all public-facing queries.
