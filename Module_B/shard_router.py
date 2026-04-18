"""
shard_router.py
---------------
Query Routing Layer for ShuttleGo Sharded Database (Assignment 4 - SubTask 3)

Strategy : Hash-based  →  shard_id = MemberID % NUM_SHARDS
Shards   : 3 separate SQLite databases (shard_0.db, shard_1.db, shard_2.db)

Sharded tables  : Member, users, group_mappings, Passenger, Driver,
                  Booking, Transaction, BookingCancellation, NoShowPenalty
Unsharded tables: Vehicle, VehicleLiveLocation, VehicleMaintenance,
                  Route, Trip, TripOccupancyLog, DriverAssignment
                  (these live in shuttlego.db unchanged)
"""

import sqlite3
import os

# ── Configuration ────────────────────────────────────────────────────────────

NUM_SHARDS = 3

# Paths to the three shard databases (adjust if your db files live elsewhere)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHARD_DB_PATHS = {
    0: os.path.join(BASE_DIR, "shard_0.db"),
    1: os.path.join(BASE_DIR, "shard_1.db"),
    2: os.path.join(BASE_DIR, "shard_2.db"),
}

# Central DB that holds the unsharded (replicated) tables
CENTRAL_DB_PATH = os.path.join(BASE_DIR, "shuttlego.db")

# Tables that are sharded (rows distributed across shard DBs)
SHARDED_TABLES = {
    "Member",
    "users",
    "group_mappings",
    "Passenger",
    "Driver",
    "Booking",
    "Transaction",
    "BookingCancellation",
    "NoShowPenalty",
}

# Tables that are replicated / unsharded (always in central DB)
UNSHARDED_TABLES = {
    "Vehicle",
    "VehicleLiveLocation",
    "VehicleMaintenance",
    "Route",
    "Trip",
    "TripOccupancyLog",
    "DriverAssignment",
}


# ── Core Routing Logic ────────────────────────────────────────────────────────

def get_shard_id(member_id: int) -> int:
    """Return the shard index for a given MemberID."""
    return int(member_id) % NUM_SHARDS


def get_shard_connection(member_id: int) -> sqlite3.Connection:
    """
    Return a SQLite connection to the correct shard database
    for the given MemberID.
    """
    shard_id = get_shard_id(member_id)
    db_path = SHARD_DB_PATHS[shard_id]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL") # keep WAL mode from Assignment 3
    return conn


def get_all_shard_connections() -> list:
    """
    Return a list of connections to ALL shard databases.
    Used for range queries / full-table scans that must touch every shard.
    Returns list of (shard_id, connection) tuples.
    """
    conns = []
    for shard_id, db_path in SHARD_DB_PATHS.items():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conns.append((shard_id, conn))
    return conns


def get_central_connection() -> sqlite3.Connection:
    """Return a connection to the central (unsharded) database."""
    conn = sqlite3.connect(CENTRAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── Lookup Queries (single MemberID) ─────────────────────────────────────────

def lookup_by_member_id(table: str, member_id: int,
                        member_col: str = "MemberID") -> list:
    """
    Fetch all rows from `table` where `member_col` = member_id.
    Routes to exactly ONE shard.

    Example:
        rows = lookup_by_member_id("Booking", 42)
    """
    if table not in SHARDED_TABLES:
        raise ValueError(f"Table '{table}' is not a sharded table. "
                         f"Use get_central_connection() for unsharded tables.")

    conn = get_shard_connection(member_id)
    try:
        cursor = conn.execute(
            f"SELECT * FROM {table} WHERE {member_col} = ?", (member_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def lookup_single_member(member_id: int) -> dict | None:
    """
    Fetch a single Member row by MemberID.
    Returns a dict or None if not found.
    """
    rows = lookup_by_member_id("Member", member_id)
    return rows[0] if rows else None


# ── Insert Operations ─────────────────────────────────────────────────────────

def insert_into_shard(table: str, data: dict, member_id: int) -> int:
    """
    Insert a row into the correct shard for `member_id`.
    `data` is a dict of {column: value}.
    Returns the lastrowid of the inserted row.

    Example:
        insert_into_shard("Booking", {
            "MemberID": 42, "TripID": 5, "SeatNumber": 3,
            "BookingStatus": "Confirmed"
        }, member_id=42)
    """
    if table not in SHARDED_TABLES:
        raise ValueError(f"Table '{table}' is not a sharded table.")

    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    values = list(data.values())

    conn = get_shard_connection(member_id)
    try:
        cursor = conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_member(member_data: dict) -> int:
    """
    Insert a new member. Routes to correct shard based on MemberID.
    `member_data` must contain 'MemberID'.

    Example:
        insert_member({"MemberID": 7, "Name": "Alice", "Email": "a@b.com", ...})
    """
    member_id = member_data["MemberID"]
    return insert_into_shard("Member", member_data, member_id)


# ── Range / Cross-Shard Queries ───────────────────────────────────────────────

def range_query_all_shards(table: str, where_clause: str = "",
                            params: tuple = ()) -> list:
    """
    Execute a SELECT across ALL shards and merge the results.
    Use this for queries that do NOT filter by MemberID,
    or for range queries spanning multiple MemberIDs.

    Example:
        # All bookings for TripID = 5 (members could be on any shard)
        rows = range_query_all_shards(
            "Booking",
            where_clause="WHERE TripID = ?",
            params=(5,)
        )
    """
    if table not in SHARDED_TABLES:
        raise ValueError(f"Table '{table}' is not a sharded table.")

    query = f"SELECT * FROM {table}"
    if where_clause:
        query += f" {where_clause}"

    all_rows = []
    shard_conns = get_all_shard_connections()
    for shard_id, conn in shard_conns:
        try:
            cursor = conn.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            # Optionally tag each row with its source shard (useful for debugging)
            for row in rows:
                row["_shard_id"] = shard_id
            all_rows.extend(rows)
        finally:
            conn.close()

    return all_rows


def range_query_member_id_range(table: str, min_id: int, max_id: int,
                                member_col: str = "MemberID") -> list:
    """
    Fetch all rows where member_col is between min_id and max_id (inclusive).
    Automatically fans out to all shards that could hold records in that range.

    Example:
        rows = range_query_member_id_range("Booking", min_id=1, max_id=100)
    """
    # Determine which shards to query
    relevant_shards = set()
    for mid in range(min_id, max_id + 1):
        relevant_shards.add(get_shard_id(mid))

    all_rows = []
    for shard_id in relevant_shards:
        db_path = SHARD_DB_PATHS[shard_id]
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                f"SELECT * FROM {table} "
                f"WHERE {member_col} BETWEEN ? AND ?",
                (min_id, max_id)
            )
            rows = [dict(row) for row in cursor.fetchall()]
            for row in rows:
                row["_shard_id"] = shard_id
            all_rows.extend(rows)
        finally:
            conn.close()

    return all_rows


# ── Update / Delete Helpers ───────────────────────────────────────────────────

def update_in_shard(table: str, member_id: int,
                    set_clause: str, params: tuple) -> int:
    """
    Run an UPDATE on the correct shard for member_id.
    `set_clause` is the SQL after SET, e.g. "BookingStatus = ?"
    Returns number of rows affected.

    Example:
        update_in_shard("Booking", 42,
                        "BookingStatus = ?", ("Cancelled",))
    """
    conn = get_shard_connection(member_id)
    try:
        cursor = conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE MemberID = ?",
            (*params, member_id)
        )
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_from_shard(table: str, member_id: int,
                      extra_where: str = "", extra_params: tuple = ()) -> int:
    """
    Delete rows from the correct shard.
    Returns number of rows deleted.
    """
    where = f"MemberID = ?"
    params = [member_id]
    if extra_where:
        where += f" AND {extra_where}"
        params.extend(extra_params)

    conn = get_shard_connection(member_id)
    try:
        cursor = conn.execute(
            f"DELETE FROM {table} WHERE {where}", params
        )
        conn.commit()
        return cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Utility: Verify Shard Distribution ───────────────────────────────────────

def print_shard_distribution(table: str = "Member",
                              member_col: str = "MemberID"):
    """
    Print how many rows live in each shard for a given table.
    Useful for verifying that data migration went correctly.
    """
    print(f"\n📊 Shard Distribution for table: {table}")
    print("-" * 40)
    total = 0
    for shard_id, db_path in SHARD_DB_PATHS.items():
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM {table}"
            ).fetchone()
            count = row[0] if row else 0
            total += count
            print(f"  Shard {shard_id} ({os.path.basename(db_path)}): {count} rows")
        except sqlite3.OperationalError:
            print(f"  Shard {shard_id}: table not found")
        finally:
            conn.close()
    print(f"  TOTAL: {total} rows")
    print("-" * 40)
