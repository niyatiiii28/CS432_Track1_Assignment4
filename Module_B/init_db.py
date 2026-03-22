"""
ShuttleGo — Database Initialiser
Drops and recreates all tables, seeds infrastructure data from schema.sql,
creates the admin user, then delegates all member/trip/booking generation
to generate_random_data.py so there is a single source of truth.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

# Import the generator functions so init is a one-command operation
from generate_random_data import (
    generate_members,
    generate_trips_and_bookings,
    generate_cancellations,
    generate_driver_assignments,
    print_summary,
)

DB_PATH     = "shuttlego.db"
SCHEMA_PATH = "sql/schema.sql"
INDEX_PATH  = "sql/add_indexes.sql"


def init_db():
    # ── 1. Fresh database ────────────────────────────────────────────────────
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Old database removed.")

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # ── 2. Schema + infrastructure seed data ────────────────────────────────
    with open(SCHEMA_PATH, "r") as f:
        cursor.executescript(f.read())
    print("Tables created and infrastructure data inserted.")

    # ── 3. Indexes (optional — can also be applied from the admin UI) ────────
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r") as f:
            cursor.executescript(f.read())
        print("Indexes applied.")

    # ── 4. Admin user (no MemberID — admin is not a member of the fleet) ────
    admin_hash = generate_password_hash("admin123")
    cursor.execute(
        "INSERT OR IGNORE INTO users (UserID, username, password_hash, role, MemberID) "
        "VALUES (1, 'admin', ?, 'admin', NULL)",
        (admin_hash,),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO group_mappings (UserID, group_name) VALUES (1, 'admin_group')"
    )
    print("Admin created  →  username: admin  |  password: admin123")

    conn.commit()
    conn.close()

    # ── 5. Generate all member/trip/booking data ─────────────────────────────
    # 150 members = ~120 passengers + ~30 drivers
    print("\nSeeding member data via generate_random_data…")
    generate_members(n=150)
    generate_trips_and_bookings(n_trips=500, max_bookings_per_trip=12)
    generate_cancellations()
    generate_driver_assignments()

    print_summary()
    print("\nDone. Run  python app.py  to start the server.")


if __name__ == "__main__":
    init_db()
