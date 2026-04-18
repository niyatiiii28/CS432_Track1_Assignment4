"""
ShuttleGo — SQL Indexing Performance Benchmark (SubTask 5)
Run from the Module_B directory:  python benchmark.py
Produces: benchmark_report.txt

All benchmark queries that need a specific row ID now resolve a real ID
from the database first, so results are never silently empty after a
fresh data generation run.
"""

import sqlite3
import time
import os
import statistics

DB_PATH     = "shuttlego.db"
REPORT_PATH = "benchmark_report.txt"

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_username       ON users(username);",
    "CREATE INDEX IF NOT EXISTS idx_users_member_id      ON users(MemberID);",
    "CREATE INDEX IF NOT EXISTS idx_booking_passenger_id ON Booking(PassengerID);",
    "CREATE INDEX IF NOT EXISTS idx_booking_trip_id      ON Booking(TripID);",
    "CREATE INDEX IF NOT EXISTS idx_booking_time         ON Booking(BookingTime DESC);",
    "CREATE INDEX IF NOT EXISTS idx_trip_date            ON Trip(TripDate DESC);",
    "CREATE INDEX IF NOT EXISTS idx_trip_route_id        ON Trip(RouteID);",
    "CREATE INDEX IF NOT EXISTS idx_trip_driver_id       ON Trip(DriverID);",
    "CREATE INDEX IF NOT EXISTS idx_trip_vehicle_id      ON Trip(VehicleID);",
    "CREATE INDEX IF NOT EXISTS idx_transaction_booking  ON \"Transaction\"(BookingID);",
    "CREATE INDEX IF NOT EXISTS idx_transaction_date     ON \"Transaction\"(TransactionDate DESC);",
    "CREATE INDEX IF NOT EXISTS idx_driver_member_id     ON Driver(MemberID);",
    "CREATE INDEX IF NOT EXISTS idx_passenger_member_id  ON Passenger(MemberID);",
    "CREATE INDEX IF NOT EXISTS idx_assignment_driver_id ON DriverAssignment(DriverID);",
    "CREATE INDEX IF NOT EXISTS idx_assignment_trip_id   ON DriverAssignment(TripID);",
    "CREATE INDEX IF NOT EXISTS idx_cancellation_booking ON BookingCancellation(BookingID);",
]

DROP_INDEXES = [
    "DROP INDEX IF EXISTS idx_users_username;",
    "DROP INDEX IF EXISTS idx_users_member_id;",
    "DROP INDEX IF EXISTS idx_booking_passenger_id;",
    "DROP INDEX IF EXISTS idx_booking_trip_id;",
    "DROP INDEX IF EXISTS idx_booking_time;",
    "DROP INDEX IF EXISTS idx_trip_date;",
    "DROP INDEX IF EXISTS idx_trip_route_id;",
    "DROP INDEX IF EXISTS idx_trip_driver_id;",
    "DROP INDEX IF EXISTS idx_trip_vehicle_id;",
    "DROP INDEX IF EXISTS idx_transaction_booking;",
    "DROP INDEX IF EXISTS idx_transaction_date;",
    "DROP INDEX IF EXISTS idx_driver_member_id;",
    "DROP INDEX IF EXISTS idx_passenger_member_id;",
    "DROP INDEX IF EXISTS idx_assignment_driver_id;",
    "DROP INDEX IF EXISTS idx_assignment_trip_id;",
    "DROP INDEX IF EXISTS idx_cancellation_booking;",
]

# ── Query templates (? placeholders) ──────────────────────────────────────────
# Each entry has:
#   sql          — the query to benchmark
#   param_query  — a cheap SELECT that resolves real param values from the DB
#                  (None means the query needs no parameters)
QUERY_TEMPLATES = [
    (
        "Login lookup (WHERE username = ?)",
        "SELECT UserID, username, password_hash, role FROM users WHERE username = ?",
        "SELECT username FROM users LIMIT 1",
    ),
    (
        "Token → MemberID (WHERE UserID = ?)",
        "SELECT MemberID FROM users WHERE UserID = ?",
        "SELECT UserID FROM users LIMIT 1",
    ),
    (
        "Passenger bookings (WHERE PassengerID = ?)",
        "SELECT * FROM Booking WHERE PassengerID = ?",
        "SELECT PassengerID FROM Passenger LIMIT 1",
    ),
    (
        "Bookings for a trip (WHERE TripID = ?)",
        "SELECT * FROM Booking WHERE TripID = ?",
        "SELECT TripID FROM Trip LIMIT 1",
    ),
    (
        "Recent bookings (ORDER BY BookingTime DESC)",
        "SELECT * FROM Booking ORDER BY BookingTime DESC",
        None,
    ),
    (
        "List trips with JOINs (ORDER BY TripDate DESC)",
        """SELECT t.*, r.RouteName, r.Source, r.Destination,
                  v.VehicleNumber, v.Model, m.Name AS DriverName
           FROM Trip t
           JOIN Route   r ON t.RouteID   = r.RouteID
           JOIN Vehicle v ON t.VehicleID = v.VehicleID
           JOIN Driver  d ON t.DriverID  = d.DriverID
           JOIN Member  m ON d.MemberID  = m.MemberID
           ORDER BY t.TripDate DESC, t.ScheduledDepartureTime""",
        None,
    ),
    (
        "Passenger transactions via Booking JOIN",
        """SELECT t.* FROM "Transaction" t
           JOIN Booking b ON t.BookingID = b.BookingID
           WHERE b.PassengerID = ?
           ORDER BY t.TransactionDate DESC""",
        "SELECT PassengerID FROM Passenger LIMIT 1",
    ),
    (
        "All transactions (ORDER BY TransactionDate DESC)",
        'SELECT * FROM "Transaction" ORDER BY TransactionDate DESC',
        None,
    ),
    (
        "Driver profile by MemberID",
        "SELECT * FROM Driver WHERE MemberID = ?",
        "SELECT MemberID FROM Driver LIMIT 1",
    ),
    (
        "Passenger profile by MemberID",
        "SELECT * FROM Passenger WHERE MemberID = ?",
        "SELECT MemberID FROM Passenger LIMIT 1",
    ),
    (
        "Driver assignments for a trip",
        "SELECT * FROM DriverAssignment WHERE TripID = ?",
        "SELECT TripID FROM DriverAssignment LIMIT 1",
    ),
    (
        "Cancellations for a booking",
        "SELECT * FROM BookingCancellation WHERE BookingID = ?",
        "SELECT BookingID FROM BookingCancellation LIMIT 1",
    ),
]

RUNS = 500


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA cache_size = 0")
    return conn


def resolve_params(conn, param_query):
    """Return a tuple of real param values fetched from the DB, or () if none needed."""
    if param_query is None:
        return ()
    row = conn.execute(param_query).fetchone()
    if row is None:
        return ()
    return tuple(row)


def drop_indexes(conn):
    for sql in DROP_INDEXES:
        conn.execute(sql)
    conn.commit()


def apply_indexes(conn):
    for sql in INDEXES:
        conn.execute(sql)
    conn.commit()


def time_query(conn, sql, params, runs=RUNS):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        conn.execute(sql, params).fetchall()
        times.append((time.perf_counter() - start) * 1_000_000)  # µs
    return times


def explain_query(conn, sql, params):
    rows = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return "\n".join(f"    {r}" for r in rows)


def fmt(val):
    return f"{val:>10.2f} µs"


def run_benchmark():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found. Run init_db.py first.")
        return

    conn  = connect()
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    # ── Resolve all parameter values once (same for before and after) ─────────
    queries = []  # list of (label, sql, params)
    for label, sql, param_query in QUERY_TEMPLATES:
        params = resolve_params(conn, param_query)
        queries.append((label, sql, params))
        if params:
            log(f"  Resolved params for '{label}': {params}")

    log()
    log("=" * 70)
    log("  ShuttleGo — SQL Indexing Performance Benchmark (SubTask 5)")
    log("=" * 70)
    log(f"  Database : {DB_PATH}")
    log(f"  Runs/query: {RUNS}")
    log()

    # ── Phase 1: baseline (no indexes) ───────────────────────────────────────
    log("Phase 1: Dropping all custom indexes (baseline — no indexes)...")
    drop_indexes(conn)
    log("  Done.\n")

    before = {}
    for label, sql, params in queries:
        before[label] = time_query(conn, sql, params)

    # ── Phase 2: with indexes ─────────────────────────────────────────────────
    log("Phase 2: Applying indexes...")
    apply_indexes(conn)
    log("  Done.\n")

    after = {}
    for label, sql, params in queries:
        after[label] = time_query(conn, sql, params)

    # ── Phase 3: EXPLAIN QUERY PLAN (with indexes) ───────────────────────────
    log("Phase 3: EXPLAIN QUERY PLAN (after indexes)\n")
    log("-" * 70)
    for label, sql, params in queries:
        log(f"  Query : {label}")
        if params:
            log(f"  Params: {params}")
        log(explain_query(conn, sql, params))
        log()

    # ── Phase 4: Results table ────────────────────────────────────────────────
    log("=" * 70)
    log("  RESULTS SUMMARY")
    log("=" * 70)
    log(f"  {'Query':<45} {'Before':>10} {'After':>10} {'Speedup':>9}")
    log(f"  {'-'*45} {'-'*10} {'-'*10} {'-'*9}")

    total_before = 0
    total_after  = 0

    for label, sql, params in queries:
        b       = statistics.median(before[label])
        a       = statistics.median(after[label])
        speedup = b / a if a > 0 else float("inf")
        total_before += b
        total_after  += a
        log(f"  {label[:45]:<45} {fmt(b)} {fmt(a)} {speedup:>8.2f}x")

    log(f"  {'-'*45} {'-'*10} {'-'*10} {'-'*9}")
    overall = total_before / total_after if total_after > 0 else float("inf")
    log(f"  {'TOTAL (sum of medians)':<45} {fmt(total_before)} {fmt(total_after)} {overall:>8.2f}x")
    log()

    # ── Phase 5: Detailed stats ───────────────────────────────────────────────
    log("=" * 70)
    log("  DETAILED STATS (median / mean / min / max)")
    log("=" * 70)
    for label, sql, params in queries:
        b = before[label]
        a = after[label]
        speedup = statistics.median(b) / statistics.median(a) if statistics.median(a) > 0 else 0
        log(f"\n  {label}")
        if params:
            log(f"    Params used: {params}")
        log(f"    Before → median={statistics.median(b):.2f} µs  "
            f"mean={statistics.mean(b):.2f}  min={min(b):.2f}  max={max(b):.2f}")
        log(f"    After  → median={statistics.median(a):.2f} µs  "
            f"mean={statistics.mean(a):.2f}  min={min(a):.2f}  max={max(a):.2f}")
        log(f"    Speedup: {speedup:.2f}x")

    log()
    log("=" * 70)
    log(f"  Report saved to: {REPORT_PATH}")
    log("=" * 70)

    conn.close()

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))

    print(f"\nDone! Results saved to {REPORT_PATH}")


if __name__ == "__main__":
    run_benchmark()
