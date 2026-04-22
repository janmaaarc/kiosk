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
| **Interactive campus map** | 20+ buildings with A* routing from the main gate. Click a building to see a slide-in panel with photo, **ENTER BUILDING**, **SHOW DIRECTION**, and **CANCEL**. Route line animates along the roads with a "YOU ARE HERE" pin at the gate. OUTSIDE / INSIDE toggle switches between the campus route and the building's floor plan. |
| **Floor plans** | Every building supports multi-floor plans. The Academic Building ships with 5 hand-drawn SVG floors (Ground, 2nd, 3rd, 4th, 5th). Each room is clickable and draws an indoor route line from the building entrance to the room with a "YOU ARE HERE" pin. |
| **In-building search** | Every floor plan has a live search bar in the top right that finds rooms across all floors of that building. Match jumps to the correct floor and draws the route automatically. |
| **Full route (outdoor → indoor)** | Click a room → **SHOW FULL ROUTE** → campus map draws the outdoor route with stakeholder-provided campus directions, then after 3.5 seconds automatically navigates to the floor plan and draws the indoor route to the specific room. |
| **Office directory** | Offices with location, hours, a live open/closed badge calculated from device time, downloadable forms/memos, an inline PDF viewer, and **ENTER BUILDING** + **SHOW DIRECTION** buttons on each office. Offices without a configured building still get a SHOW DIRECTION fallback to the campus map. |
| **Faculty directory** | Browse faculty by department. Each card has a photo, name, department, and a **FIND ON MAP** button when a room and building are assigned. |
| **Events** | Upcoming and ongoing campus events with images, dates, times, and full details. |
| **Announcements** | Digital notices and memos with PDF downloads. |
| **Global search (admin / public)** | `/api/search` covers rooms, offices, and faculty in one request. |
| **QR codes** | Every route has a **GENERATE QR CODE** button that pops up a floating card. QR images are generated server-side at `/qr?data=…&size=…` so the kiosk works offline (no third-party API). |
| **RFID entry** | The splash screen captures RFID keystrokes (works with any USB HID reader on a laptop). On a Raspberry Pi, set `KIOSK_ENABLE_RFID=1` to also spin up an `mfrc522`-based background watcher. Scanned UIDs are looked up in the `users` table and matched users land on their personalised profile. |
| **Offline fallback** | A service worker caches static assets and shows a branded `/offline` page when the network drops. |

---

## 2. Public screens walkthrough

### Splash screen — `/`

The entry screen. A rotating slideshow plays in the background. The instruction
"SCAN YOUR RFID TO ACCESS THE KIOSK" is displayed in the center. Tapping or
clicking anywhere navigates to the main menu. An RFID reader connected to the
device's USB port automatically redirects when a card is scanned.

### Main menu — `/menu`

A grid of large buttons leading to every major section: Faculty, Campus Map,
Offices, Events, Announcements, and Room Search.

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

### Office directory — `/office-selection` and `/office?name=<key>`

- `/office-selection` lists all active offices as a scrollable sidebar on the
  left. Tap any office to load its detail view on the right.
- The detail view shows:
  - Office name and a photo
  - Location chip (e.g. "New Admin Building, 2nd Floor")
  - Hours chip with a live **OPEN / CLOSED** badge calculated from the current
    device time
  - A **GET DIRECTIONS** button that links to the building's floor plan
  - Attached forms and memos as downloadable PDFs
  - An inline PDF preview that opens when a file is tapped

The sidebar search box filters offices by name in real time.

---

### Campus map — `/campus_map`

The full-campus interactive map.

- Tap any building label to open a slide-in panel on the right with the
  building's photo, **ENTER BUILDING**, **SHOW DIRECTION**, and **CANCEL**.
- **ENTER BUILDING** → jumps directly to that building's floor plan.
- **SHOW DIRECTION** → draws a route line from the main gate to the building
  without leaving the page. A red sidebar slides in from the left with
  step-by-step directions and a "YOU ARE HERE" pin appears at the gate.
- The top-right of the map shows an **OUTSIDE / INSIDE** toggle and a
  **GENERATE QR CODE** button when directions are active.
- **OUTSIDE / INSIDE** toggle — INSIDE jumps to the building's floor plan
  (carrying the specific room if one was selected).
- **GENERATE QR CODE** → pops up a floating white card with a QR of the
  current directions URL (server-generated, no internet required). Click
  anywhere outside the card to dismiss it.
- `?location=<building>` in the URL automatically draws the route on load.
- `?location=<building> room <room>` draws the outdoor route, then **after
  3.5 seconds automatically navigates to the floor plan** at the right floor
  with the specific room highlighted and the indoor route drawn.

---

### Building floor plans — e.g. `/academic_building`, `/it_building`

Each building has its own URL. The floor plan page has:

- A left sidebar with **floor selector buttons** (e.g. `1ST FLOOR`,
  `2ND FLOOR`, etc.). Switching floors fades the current plan before loading.
- A top bar with home / back icons, the building title, a **room search bar**,
  and a **SHOW DIRECTION** link.
- A main area showing the floor plan image with **room rectangles** overlaid
  at their exact positions. Each room is clickable.
- **Room search bar** (top right) — live search across every room on every
  floor of the current building. Matches display with the floor label badge
  (`2ND FLOOR`). Clicking a match on the current floor highlights and routes
  in place; clicking a match on a different floor navigates there.
- **SHOW DIRECTION** (top right) → jumps to `/campus_map?location=<BUILDING>`
  so the visitor can see the outdoor route.
- Clicking a room opens a slide-up info panel with:
  - Room name + description
  - **DIRECTIONS** list — stakeholder-provided step-by-step wayfinding text
  - **SHOW FULL ROUTE** button → outdoor route + auto-navigation back to
    this floor plan with the specific room highlighted
  - **OPEN OFFICE PAGE →** button (for rooms linked to an office)
  - A QR code to the linked office page
- Clicking a room also draws a **dashed indoor route line** from the
  building entrance up the hallway to the room, with a "YOU ARE HERE" pin at
  the entrance.
- If the page loads with `?location=<room>`, that room is auto-highlighted
  and the indoor route draws on load.

#### Academic Building — 5 hand-drawn floors

The Academic Building ships with complete SVG floor plans for all 5 floors,
plus stakeholder-provided wayfinding text for every known room.

| Floor | Rooms |
|---|---|
| 1st | Medical & Dental Services, Record & Information Center, MPC Cares, Faculty Room, CR, Quality Assurance Office, Conference Room, Repair & Maintenance, Function Hall |
| 2nd | Director for Student Affairs, Guidance Scholarship & Admission, Placement and Follow-Up, Faculty Room, CR, Classroom, Command Centers |
| 3rd | VP for Admin & Finance, VP for Academic Affairs, Program Chair's Office, Dean for Technology and Instruction, Dean for Graduate School, Classroom, Command Centers |
| 4th | Library, Computer Library, Educational Technology Room, CR |
| 5th | Staff Room, Control Room, CR |

IT Building uses the client-supplied JPG floor plans for floors 1-3. Other
buildings fall back to an empty placeholder until rooms are added via the
admin dashboard.

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
| Engineering Building | `/engineering-floor1` |

---

### Events — `/events`

Lists all non-expired events. Each event shows an image, title, date range, and
time. Tapping opens the full event detail.

### Announcements — `/announcements`

Lists all non-expired digital notices. Tapping an announcement opens its PDF
in a full-screen PDF viewer.

### Room search — `/search`

A form field where visitors type a room number. On submit the page displays the
matching room's building, floor, and description.

### Health check — `/healthz`

Returns `{"status": "ok"}` when the database is reachable. Used by monitoring
tools and Docker health checks.

---

## 3. Admin dashboard — managing content

### Logging in

Go to `/admin`. Enter your username and password. After five failed attempts
the login form is locked for 15 minutes per IP address.

To log out, click the **Logout** link in the admin navigation bar.

---

### Dashboard — `/dashboard`

After login the dashboard shows cards for every content section. Click a card
to manage that section.

---

### Managing Events — `/admin/events`

Lists all events in a table. Each row shows the title, date, and expiry.

**Adding an event** — click **+ Add Event**:

| Field | Notes |
|---|---|
| Title | Required. Displayed on the events page. |
| Image | Path to an image under `static/`. Use the upload button to upload a file and fill this automatically. |
| Short description | One-line summary shown in the events list. |
| Date | Free text, e.g. `April 1 – April 30, 2026`. |
| Time | Free text, e.g. `8:00 AM – 12:00 PM`. |
| Details | Full multi-line description shown on the event detail page. |
| Published at | Auto-fills to the current date and time. |
| Expires at | Leave blank to never expire. Set a date to hide the event automatically after that time. |

Click **Save** to publish immediately, or set a future **Published at** value to
schedule it.

---

### Managing Announcements — `/admin/announcements`

| Field | Notes |
|---|---|
| Title | Required. Shown in the announcements list. |
| Thumbnail | Image shown in the list view. |
| PDF file | The announcement document. Visitors tap to open or download. |
| Published at | Auto-fills to now. |
| Expires at | Leave blank to keep forever. |

---

### Managing Offices — `/admin/offices`

| Field | Notes |
|---|---|
| Key | Unique slug, lowercase, no spaces (e.g. `registrar`). Used in URLs. Must be unique. |
| Display name | The office name shown to visitors (e.g. `Office of the Registrar`). |
| Image | Photo of the office or its sign. |
| Location | Short description shown as a chip (e.g. `New Admin Building, 2nd Floor`). |
| Building URL | Select the building this office is in. When visitors tap **Get Directions**, this is where they are sent. |
| Office hours | Displayed as a chip next to the location. Format `8:00 AM - 5:00 PM` to enable the live open/closed badge. |
| Description | Paragraph shown on the office detail page. |
| Published at / Expires at | Same as events. |

**Attaching forms and memos** — after creating an office, open **Edit** and use
the "Files" section to attach PDF documents. Visitors see them as a list under
"FORMS & MEMOS" and can open each one inline.

---

### Managing Rooms — `/admin/rooms`

Rooms are what appear as clickable rectangles on the floor plan images. Every
room belongs to a building and a floor.

**Adding a room** — click **+ Add Room**:

| Field | Notes |
|---|---|
| Building | Must exactly match the building name used in `building_floors` (e.g. `Rodriguez Building`). Case-insensitive match is used at render time. |
| Floor | Floor number as text (e.g. `1`, `2`). Must match the `floor_number` in `building_floors`. |
| Room | Room name or number shown on the overlay label. |
| Description | Short description shown in the room info panel. |
| **Floor plan position** | |
| Pos Left | Left edge of the room rectangle as a percentage (0–100) of the floor plan image width. |
| Pos Top | Top edge as a percentage of the image height. |
| Pos Width | Rectangle width as a percentage of the image width. |
| Pos Height | Rectangle height as a percentage of the image height. |
| Office Key | If this room belongs to an office, paste the office's **Key** here. The floor plan info panel will show a QR code linking to that office. |
| Room Color | Optional CSS color (e.g. `#e3c766`) to tint the room rectangle. |

> **Tip — positioning rooms**: Open the floor plan image in any image editor,
> note the pixel coordinates of the room rectangle corners, then divide by the
> image dimensions to get percentages. For a 1000×800 image, a room at pixel
> (100, 80) with size 150×100 would be: left=10, top=10, width=15, height=12.5.

---

### Managing Building Floors — `/admin/building-floors`

Before rooms appear on a floor plan the floor itself must exist in the database.
This is where you add floor plan images and give each floor a label.

| Field | Notes |
|---|---|
| Building | Exact building name (e.g. `Rodriguez Building`). Must match the `building` column in `rooms`. |
| Floor Number | Integer. `1` is the ground floor, `2` is the second, etc. |
| Floor Label | Human-readable name shown on the floor selector button (e.g. `Ground Floor`, `2nd Floor`). |
| Floor Plan Image | Path to the floor plan image stored under `static/`. Upload with the button to fill this automatically. |

> **Note**: The `(building, floor_number)` pair must be unique. Saving a
> duplicate replaces the existing row.

Once a floor row exists and rooms have been added for that building and floor
number, they will appear as overlays on the floor plan image automatically.

---

### Managing Faculty — `/admin/faculty`

| Field | Notes |
|---|---|
| Name | Required. Displayed on the faculty card and profile. |
| Department | Used to build the department filter sidebar (e.g. `College of Engineering`). |
| Position | Displayed on the profile page (e.g. `Instructor I`). |
| Photo | Portrait photo. Upload with the button. |
| Schedule Image | Optional image of the faculty member's class schedule. |
| Room | Room name or number (e.g. `IT 202`). Enables the **Find on Map** button on the faculty card. |
| Building | Building name (e.g. `IT Building`). Required together with Room for map navigation. |
| Office Key | Optional. Links the faculty member's profile to a specific office page. |

---

## 4. Floor plan system — how rooms and buildings work

The floor plan system is fully database-driven. Here is the complete workflow
to add a new building or update an existing one:

### Step 1 — Prepare the floor plan image

Export the floor plan as a JPEG or PNG. There is no required resolution but
wider images give more room precision. Store the file under `static/` (e.g.
`static/images/rodriguez_ground.jpg`).

### Step 2 — Add a building floor row

Go to **Admin → Building Floors → Add**. Fill in:
- Building: `Rodriguez Building`
- Floor Number: `1`
- Floor Label: `Ground Floor`
- Floor Plan Image: `images/rodriguez_ground.jpg`

Repeat for each floor of the building.

### Step 3 — Add rooms for that floor

Go to **Admin → Rooms → Add**. For each room on the Ground Floor:
- Building: `Rodriguez Building`
- Floor: `1`
- Room: `Room 101`
- Description: `General Purpose Classroom`
- Pos Left / Top / Width / Height: percentage coordinates on the image

### Step 4 — Visit the floor plan

Open `/rodriguez_building` on the kiosk. The Ground Floor image appears with
room rectangles at the configured positions. Switch floors using the sidebar
buttons. Hover or tap a room to see its info panel.

### Linking a room to an office

Set the **Office Key** field on the room to match the **Key** field of an
existing office. The room's info panel will then show a QR code that links
directly to that office's detail page.

### Buildings with hardcoded floors

The **Academic Building** and **IT Building** have partial room sets hardcoded
in the application for the ground floor. All other floors still read from the
database. You can add database rows for any floor including the ground floor —
database rows take priority over hardcoded ones once any `building_floors` row
exists for that building.

---

## 5. Local development setup

```bash
# Clone and enter the project
git clone <repo-url>
cd kiosk

# Create a Python virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# First time only: create tables and seed the admin user
.venv/bin/python init_db.py
# → prompts for admin password, or reads from KIOSK_ADMIN_PASSWORD env var

# Start the development server
.venv/bin/python app.py
# → http://127.0.0.1:5000/
```

Log in to the admin at `http://127.0.0.1:5000/admin`.

The development server auto-reloads on file changes. Do not use it in
production.

---

## 6. Production deployment

The dev server is for local use only. On the display PC or Raspberry Pi:

```bash
# 1. Create a system user and copy the project
sudo useradd --system --home /opt/kiosk kiosk
sudo git clone <repo-url> /opt/kiosk
sudo chown -R kiosk:kiosk /opt/kiosk

# 2. Create the virtualenv and install dependencies
sudo -u kiosk python3 -m venv /opt/kiosk/.venv
sudo -u kiosk /opt/kiosk/.venv/bin/pip install -r /opt/kiosk/requirements.txt

# 3. Write the environment file (keep it private — chmod 600)
sudo cp /opt/kiosk/deploy/kiosk.env.example /etc/kiosk.env
sudo chmod 600 /etc/kiosk.env
# Open /etc/kiosk.env and set KIOSK_SECRET_KEY to a long random string:
#   python3 -c "import secrets; print(secrets.token_hex(32))"

# 4. Initialise the database and seed the admin user
sudo -u kiosk KIOSK_ADMIN_PASSWORD='your-strong-password' \
    /opt/kiosk/.venv/bin/python /opt/kiosk/init_db.py

# 5. Install and start the systemd service
sudo cp /opt/kiosk/deploy/kiosk.service /etc/systemd/system/kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable --now kiosk
sudo systemctl status kiosk

# 6. Schedule nightly database backups
sudo crontab -u kiosk -e
# Add this line:
# 0 3 * * * /opt/kiosk/scripts/backup_db.sh >> /opt/kiosk/logs/backup.log 2>&1
```

The service listens on port 8000. Point the kiosk browser at
`http://127.0.0.1:8000/`. For remote admin access over LAN use the machine's
local IP address.

---

## 7. Docker deployment

```bash
# Copy and edit the environment file
cp deploy/kiosk.env.example .env
# Edit .env and set KIOSK_SECRET_KEY

# Start in the background
docker compose up -d

# The kiosk is available at http://localhost:8000/
```

The container runs as a non-root `kiosk` user. The following paths are mounted
as host volumes so data survives restarts and image upgrades:

| Volume | Contents |
|---|---|
| `./database.db` | All content: rooms, events, announcements, offices, faculty |
| `./static/uploads/` | Uploaded images and PDFs |
| `./logs/` | Application logs |

Health check: `curl http://localhost:8000/healthz` → `{"status":"ok"}`.

---

## 8. Free cloud hosting options

If you want to make the kiosk accessible online (e.g. for the client to preview
or manage content remotely), both options below have a free tier and connect
directly to this GitHub repo.

---

### Render — `render.com`

1. Create a free account at [render.com](https://render.com).
2. Click **New → Web Service** and connect this GitHub repo.
3. Set the following in the Render dashboard:

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

5. Click **Deploy**. Render builds and starts the app. Your URL will be
   `https://your-app-name.onrender.com`.

**Free tier limits:**
- The instance **spins down after 15 minutes of inactivity** and takes ~30
  seconds to wake on the next request. This is fine for demos and admin access
  but not ideal for an always-on kiosk display.
- The SQLite database file **resets on every redeploy** because the free tier
  has no persistent disk. Uploaded images and added content will be lost on the
  next deploy. For persistent storage, add a Render PostgreSQL database (free
  for 90 days, then $7/mo) or upgrade to a paid plan with a disk.

---

### Railway — `railway.app`

Railway gives $5 of free credit per month, which is enough to run this app
continuously at low traffic.

1. Create a free account at [railway.app](https://railway.app).
2. Click **New Project → Deploy from GitHub repo** and select this repo.
3. Railway auto-detects Python and sets up the build. Add the following
   environment variables under **Variables**:

   | Key | Value |
   |---|---|
   | `KIOSK_SECRET_KEY` | Any long random string |
   | `FLASK_ENV` | `production` |
   | `KIOSK_ADMIN_PASSWORD` | Your chosen admin password |

4. Set the **Start command** (under Settings → Deploy):
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```

5. Add a **Volume** (under the service → Volumes) mounted at `/app` to persist
   the SQLite database across deploys. Railway supports persistent volumes on
   all plans including the free credit tier.

**Free tier limits:**
- $5 of credit per month. A single low-traffic service uses roughly $0.50–$2
  per month, so the free credit covers it most of the time.
- No persistent volume on the absolute free hobby plan — add one from the
  Railway dashboard to keep your data across deploys.

---

### Which one to choose

| | Render | Railway |
|---|---|---|
| Easiest setup | Yes | Yes |
| Always-on (no sleep) | No (free tier sleeps) | Yes (within credit) |
| Persistent storage | Paid add-on | Volume add-on (included in credit) |
| Custom domain | Yes (free) | Yes (free) |

For a **demo or client preview**, either works. For a **production kiosk**
running on a physical display on campus, the self-hosted deployment (Section 6)
is recommended so the app runs locally on the device without depending on
internet connectivity.

---

## 9. Environment variables

| Variable | Required in prod | Purpose |
|---|---|---|
| `KIOSK_SECRET_KEY` | Yes | Flask session signing key. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. |
| `FLASK_ENV` | Recommended | Set to `production` — causes the app to refuse to start if `KIOSK_SECRET_KEY` is missing. |
| `KIOSK_ADMIN_PASSWORD` | Optional | Non-interactive password source for `init_db.py`. If unset, the script prompts for input. |
| `KIOSK_BACKUP_RETENTION_DAYS` | Optional | How many days of backup files to keep (default 30). |

---

## 10. Admin password management

```bash
# First-time setup — seeds the admin account (will not overwrite an existing one)
.venv/bin/python init_db.py

# Change an existing admin password
.venv/bin/python scripts/set_admin_password.py
# → prompts for new password, or reads from KIOSK_ADMIN_PASSWORD
```

The default username is `admin`. The password is hashed with bcrypt and stored
in the `admins` table. The plain-text password is never written to disk.

---

## 11. CSV bulk room import

Instead of adding rooms one by one, you can import them in bulk from a CSV file.

Go to **Admin → Rooms** and use the **Import CSV** button at the top of the page.

### CSV format

The file must be UTF-8 encoded with a header row:

```
building,floor,room,description,pos_left,pos_top,pos_width,pos_height,office_key
Rodriguez Building,1,Room 101,General Classroom,5,10,15,12,
Rodriguez Building,1,Faculty Room,Department Office,5,30,15,12,registrar
IT Building,2,Lab 201,Computer Laboratory,20,15,25,20,it_lab
```

| Column | Required | Notes |
|---|---|---|
| `building` | Yes | Must match the `building` name in `building_floors` exactly. |
| `floor` | Yes | Floor number as text (e.g. `1`, `2`). |
| `room` | Yes | Room name shown on the overlay. |
| `description` | No | Short description for the info panel. |
| `pos_left` | No | Left position as a percentage (default 0). |
| `pos_top` | No | Top position as a percentage (default 0). |
| `pos_width` | No | Width as a percentage (default 10). |
| `pos_height` | No | Height as a percentage (default 10). |
| `office_key` | No | Office key to link to. Leave blank if none. |

Rows that have an existing `(building, floor, room)` combination are updated in
place. Invalid rows are skipped and reported in the flash message.

---

## 12. File uploads

The upload endpoint is available from any admin form that has an image or PDF
field. Click the upload button next to the field, select a file, and the path
is automatically inserted into the text field.

**Accepted file types:**
- Images: JPEG, PNG, WebP, GIF (max 5 MB)
- Documents: PDF (max 10 MB)

Files are saved to `static/uploads/images/` or `static/uploads/files/` with
a random UUID filename. The path stored in the database is relative to `static/`
(e.g. `uploads/images/3f8a…jpg`).

---

## 13. Offline / service worker

A service worker is registered automatically on every page. It caches static
assets (CSS, fonts) on first visit and serves them from cache on subsequent
visits.

**When the device loses internet connection:**
- Page navigation requests that fail will show the `/offline` branded fallback
  page instead of a browser error.
- Static assets (CSS, images, fonts) that are already cached continue to load
  normally.

The cache is versioned (`kiosk-v1`). When the application is updated and the
cache version changes, stale entries are cleared automatically on the next visit.

---

## 14. RFID entry capture

The kiosk supports two RFID flows — keyboard emulation (works on any device)
and a dedicated Raspberry Pi background watcher using `mfrc522` / `RPi.GPIO`.

### Keyboard-emulation (default)

The splash screen (`/`) silently captures keystrokes from an RFID reader that
appears as a USB HID keyboard.

- Characters accumulate into a buffer as they arrive.
- If the Enter key is pressed and the buffer has more than 4 characters, the
  browser redirects to `/rfid?uid=<scanned-uid>`.
- If no key is pressed for 100 ms and the buffer has more than 4 characters,
  the same redirect fires automatically (handles readers that do not send Enter).
- Keystrokes from the RFID reader are not displayed visibly on screen.

### Raspberry Pi watcher (optional)

For deployments on a Pi with a physical RC522 module, the kiosk ships a
background thread that polls the reader and notifies the Flask app directly.

```bash
# Install the Pi-only extras on the device
sudo pip install mfrc522 RPi.GPIO spidev

# Enable the watcher via the env file
KIOSK_ENABLE_RFID=1
KIOSK_INTERNAL_URL=http://127.0.0.1:8000
```

When `KIOSK_ENABLE_RFID=1` is set, `create_app()` starts the watcher on boot.
Without the flag (e.g. on a laptop) the watcher stays dormant — nothing breaks.

### Server lookup — `/rfid?uid=` and `/check_rfid`

Both the keyboard-emulation flow and the Pi watcher hit the same endpoints:

| Route | Method | Purpose |
|---|---|---|
| `/rfid?uid=<uid>` | GET | If the UID is in the `users` table, render `profile.html` with the person's name and role. Otherwise redirect to `/menu`. Rate-limited to 30/min. |
| `/check_rfid` | POST (JSON) | Machine-to-machine lookup: `{"uid": "..."}` → `{"status":"authorized","user":{...}}` or `{"status":"unauthorized"}`. Localhost-only (remote calls get 403). Rate-limited to 60/min. CSRF-exempt because it's called by the watcher thread. |

### Managing users

The `users` table is populated manually for now:

```sql
INSERT INTO users (rfid_uid, name, role) VALUES ('AB12CD34', 'Juan dela Cruz', 'student');
```

---

## 14a. Server-side QR code generation — `/qr?data=…&size=…`

Every QR surface in the kiosk (directions QR, office QR, room QR) is
generated server-side using the `qrcode` library. Works completely offline.

**Parameters:**

| Parameter | Required | Notes |
|---|---|---|
| `data` | Yes | The string to encode. Usually a URL. |
| `size` | No | Pixel size (64–512, default 200). |

**Examples:**
```
/qr?data=https://example.com&size=260
/qr?data=/campus_map?location=ACADEMIC+BUILDING
```

Rate-limited to 60 requests/min. Returns a PNG image.

---

## 15. Display scaling

The kiosk is designed for a **1360 × 768** display (standard HD TV). The file
`static/js/kiosk-scale.js` is injected into every HTML page automatically. It
applies a CSS `transform: scale()` so the 1360 × 768 design fills any viewport
while preserving the exact layout. Editors working on a laptop see the same
frame the TV renders.

If the target display changes, update `DESIGN_W` and `DESIGN_H` in
[static/js/kiosk-scale.js](static/js/kiosk-scale.js).

---

## 16. Security overview

| Area | Implementation |
|---|---|
| Password storage | bcrypt hashing via Flask-Bcrypt. Plain text never stored. |
| Admin login rate limit | 5 POST attempts per 15 minutes per IP address. |
| CSRF protection | Flask-WTF globally enabled. Every form renders a hidden `csrf_token` field. |
| SQL injection | All queries use parameterized placeholders. `LIKE` patterns escape `%`, `_`, `\`. |
| Open redirect | The `from_building` parameter on the office page is validated against a fixed allowlist of building URLs. |
| File uploads | MIME-type whitelist enforced server-side. Files are renamed to random UUIDs before storage. |
| Session fixation | Session is cleared before writing new admin credentials on login. |
| Search API rate limiting | `/api/search` and `/api/rooms` are limited to 60 requests per minute. |
| Upload rate limiting | `/admin/upload` is limited to 30 requests per minute. |
| Error handling | 404, 429, and 500 errors render branded HTML pages. 500 errors are logged with full tracebacks. |
| Logging | Admin logins (success and failure) are written to `logs/kiosk.log` (rotating, 10 MB × 5 files). |

---

## 17. Running the test suite

```bash
.venv/bin/pytest tests/ -q
```

38 tests cover:
- All major public routes return HTTP 200
- Health check endpoint returns correct JSON
- Menu page injects kiosk scripts
- Search endpoint (GET and POST, empty and matching queries)
- Admin login, logout, and session protection
- Admin CRUD for rooms, events, announcements, offices
- 404 error page
- `/rfid?uid=` redirect and user profile rendering (6 tests)
- `/check_rfid` JSON endpoint (authorised / unauthorised / missing UID)
- `/qr?data=` PNG generation + missing-data rejection

Each test run uses an isolated temporary database seeded by the `conftest.py`
fixture. No test touches the `database.db` file.

---

## 18. Project layout

```
kiosk/
├── app.py                        Entry point — dev server
├── init_db.py                    First-time DB setup, schema migrations, admin seed
├── requirements.txt
├── Dockerfile                    Production container (non-root kiosk user)
├── docker-compose.yml
├── database.db                   SQLite store (created by init_db.py)
│
├── kiosk_app/
│   ├── __init__.py               create_app() factory, blueprint registration,
│   │                             logging, error handlers, kiosk-script injection
│   ├── extensions.py             bcrypt, CSRFProtect, Limiter singletons
│   ├── db.py                     db_connection() context manager
│   ├── auth.py                   login_required decorator
│   ├── rfid.py                   Optional Pi-only mfrc522 + GPIO watcher
│   │                             (no-op on laptops; enable with KIOSK_ENABLE_RFID)
│   └── blueprints/
│       ├── main.py               /, /menu, /faculty, /search, /api/search,
│       │                         /api/rooms, /rfid, /check_rfid, /qr,
│       │                         /offline, /sw.js, /healthz
│       ├── campus.py             /campus_map, all /building_name routes,
│       │                         _floor_plan() helper, _ACADEMIC_FLOORS
│       ├── offices.py            /office-selection, /office (with ENTER
│       │                         BUILDING + SHOW DIRECTION buttons)
│       ├── announcements.py      /announcements, /announcement-view
│       ├── events.py             /events, /event/<id>
│       ├── admin.py              /admin login, /dashboard, /rooms CRUD,
│       │                         /rooms/import-csv
│       └── content.py            /admin/events|announcements|offices|
│                                 building-floors|faculty CRUD, /admin/upload
│
├── templates/
│   ├── _breadcrumb.html          Reusable breadcrumb partial
│   ├── floor_plan.html           Generic floor plan renderer
│   ├── index.html                Splash screen with RFID capture
│   ├── menu.html                 Main menu grid
│   ├── faculty.html              Faculty directory
│   ├── office.html               Office detail + sidebar
│   ├── office_selection.html     Office list
│   ├── campus.html               Interactive campus map
│   ├── events.html               Events list
│   ├── rooms.html                Admin rooms list + CSV import
│   ├── offline.html              Offline fallback page
│   ├── 404.html / 429.html / 500.html
│   └── admin/
│       ├── base.html             Admin layout with sidebar nav
│       ├── building_floors.html  Floor list
│       ├── building_floor_form.html
│       ├── faculty_list.html     Faculty list
│       ├── faculty_form.html
│       └── …                    Event, announcement, office forms
│
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── kiosk-scale.js        Auto-scales every page to 1360×768
│   │   └── kiosk-idle.js         Idle timeout → returns to splash
│   ├── sw.js                     Service worker (cache-first assets,
│   │                             network-first navigation, offline fallback)
│   ├── font/                     LeagueSpartan and other typefaces
│   ├── images/
│   │   ├── icon/                 Home / back icons
│   │   ├── building/             Campus map building photos
│   │   ├── floor_plans/          Hand-drawn SVGs + client JPGs
│   │   │   ├── academic_ground.svg
│   │   │   ├── academic_2nd.svg
│   │   │   ├── academic_3rd.svg
│   │   │   ├── academic_4th.svg
│   │   │   ├── academic_5th.svg
│   │   │   └── IT_1ST.JPG / IT_2ND.JPG / IT_3RD.JPG
│   │   ├── offices/              Office cover photos
│   │   ├── qr/                   Pre-generated QR codes (fallback)
│   │   └── screensaver/          Splash slideshow images
│   └── uploads/                  Admin-uploaded images and PDFs
│
├── logs/                         Rotating app logs (auto-created)
├── tests/                        pytest suite (38 tests)
├── scripts/
│   ├── backup_db.sh              SQLite online backup + retention
│   └── set_admin_password.py     Rotate admin password
└── deploy/
    ├── kiosk.service             systemd unit (gunicorn)
    └── kiosk.env.example         Environment variable template
```

---

## Database tables reference

| Table | Purpose |
|---|---|
| `admins` | Admin login credentials (username + bcrypt hash) |
| `rooms` | Individual rooms with building, floor, position coordinates, and optional office link |
| `offices` | Office directory entries with hours, location, files, and building link |
| `events` | Campus events with image, date, time, and expiry |
| `announcements` | Digital notices with thumbnail and PDF attachment |
| `building_floors` | Floor plan images and labels for each building floor |
| `faculty` | Faculty members with department, photo, room, and office link |
| `users` | RFID UID → name + role (used by `/rfid?uid=` and `/check_rfid` for personalised entry) |

All content tables have `published_at` and `expires_at` columns. Records with
a past `expires_at` are automatically excluded from all public-facing queries.
