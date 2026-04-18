"""
ShuttleGo — Database Initialiser (SHARDED VERSION) [FINAL FIXED]
"""

import os
import mysql.connector
from werkzeug.security import generate_password_hash

# ✅ IMPORT ADDED
from generate_noshow_penalties_patch import generate_noshow_penalties

# Import generator functions
from generate_random_data import (
    generate_members,
    generate_trips_and_bookings,
    generate_cancellations,
    generate_driver_assignments,
    print_summary,
)

# =========================
# SHARD CONFIG
# =========================
HOST = "10.0.116.184"
USER = "Infobase"
PASSWORD = "password@123"
DATABASE = "Infobase"

SHARD_PORTS = [3307, 3308, 3309]

SCHEMA_PATH = "sql/schema.sql"
INDEX_PATH  = "sql/add_indexes.sql"


def get_connection(port):
    return mysql.connector.connect(
        host=HOST,
        port=port,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )


# =========================
# SAFE SQL EXECUTION
# =========================
def execute_sql_file(cursor, path):
    with open(path, "r") as f:
        sql_script = f.read()

    lines = []
    for line in sql_script.splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.startswith("/*"):
            continue
        lines.append(line)

    sql_clean = " ".join(lines)
    statements = sql_clean.split(";")

    for stmt in statements:
        stmt = stmt.strip()
        if stmt and stmt != ")":   # ✅ safety fix
            try:
                print("Executing:", stmt[:100])
                cursor.execute(stmt)
            except Exception as e:
                print("\n❌ Failed Query:")
                print(stmt)
                raise e


# =========================
# INIT DB
# =========================
def init_db():

    print("\nInitializing SHARDED database...")

    # =========================
    # CONNECT TO ALL SHARDS
    # =========================
    shards = [get_connection(p) for p in SHARD_PORTS]

    # =========================
    # APPLY SCHEMA
    # =========================
    for i, conn in enumerate(shards):
        cursor = conn.cursor()

        try:
            execute_sql_file(cursor, SCHEMA_PATH)
            conn.commit()
            print(f"  Schema applied on shard {i} (port {SHARD_PORTS[i]})")
        except Exception as e:
            print(f"\n❌ Error in schema on shard {i}:")
            print(e)
            conn.rollback()
            return

    # =========================
    # APPLY INDEXES
    # =========================
    if os.path.exists(INDEX_PATH):
        for i, conn in enumerate(shards):
            cursor = conn.cursor()

            try:
                execute_sql_file(cursor, INDEX_PATH)
                conn.commit()
                print(f"  Indexes applied on shard {i}")
            except Exception as e:
                print(f"\n❌ Error in indexes on shard {i}:")
                print(e)
                conn.rollback()
                return

    # =========================
    # CREATE ADMIN
    # =========================
    admin_conn = shards[0]
    cursor     = admin_conn.cursor()

    admin_hash = generate_password_hash("admin123")

    cursor.execute("""
        INSERT IGNORE INTO users
        (UserID, username, password_hash, role, MemberID)
        VALUES (%s,%s,%s,%s,%s)
    """, (1, 'admin', admin_hash, 'admin', None))

    cursor.execute("""
        INSERT IGNORE INTO group_mappings
        (MappingID, UserID, group_name)
        VALUES (%s,%s,%s)
    """, (1, 1, 'admin_group'))

    admin_conn.commit()

    print("Admin created → username: admin | password: admin123")

    # =========================
    # GENERATE DATA
    # =========================
    print("\nSeeding data via generator...")

    generate_members(n=150)
    generate_trips_and_bookings(n_trips=500, max_bookings_per_trip=12)
    generate_cancellations()

    # 🔥 CRITICAL FIX (THIS WAS MISSING)
    generate_noshow_penalties(shards)

    generate_driver_assignments()

    print_summary()

    print("\nDone. Run python app.py to start server.")


if __name__ == "__main__":
    init_db()