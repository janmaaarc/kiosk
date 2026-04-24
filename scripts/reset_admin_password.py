"""Reset admin password. Run: python scripts/reset_admin_password.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from flask_bcrypt import Bcrypt

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")
USERNAME = "admin"
PASSWORD = "kiosk2025"

b = Bcrypt()
h = b.generate_password_hash(PASSWORD).decode("utf-8")

conn = sqlite3.connect(DB)
existing = conn.execute("SELECT id FROM admins WHERE username=?", (USERNAME,)).fetchone()
if existing:
    conn.execute("UPDATE admins SET password_hash=? WHERE username=?", (h, USERNAME))
    print(f"Password updated for '{USERNAME}'")
else:
    conn.execute("INSERT INTO admins (username, password_hash) VALUES (?,?)", (USERNAME, h))
    print(f"Admin user '{USERNAME}' created")
conn.commit()
conn.close()
print("Done. Login: admin / kiosk2025")
