"""
ShuttleGo – Flask Backend
SubTask 3 : RBAC (admin / user roles, group-based access)
SubTask 4 : SQL Indexing
SubTask 5 : Performance Benchmarking
"""

import sqlite3
import os
import json
import time
import logging
from datetime import datetime
from functools import wraps

from flask import (Flask, request, session, jsonify, redirect,
                   url_for, render_template, g, abort)
from werkzeug.security import check_password_hash

# ── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "shuttlego_secret_key_2024"  # in prod, use env var

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "shuttlego.db")
AUDIT_LOG  = os.path.join(BASE_DIR, "logs", "audit.log")

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

# ── Audit Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=AUDIT_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def audit(action: str, detail: str = "", status: str = "OK"):
    user = session.get("username", "ANONYMOUS")
    role = session.get("role", "none")
    ip   = request.remote_addr
    via  = "API"
    logging.info(f"USER={user} ROLE={role} IP={ip} VIA={via} ACTION={action} STATUS={status} DETAIL={detail}")


# ── DB Helper ─────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


# ── RBAC Decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login_page"))
        if session.get("role") != "admin":
            audit("ADMIN_ACTION_DENIED", f"endpoint={request.path}", "FORBIDDEN")
            if request.is_json:
                return jsonify({"error": "Admin access required"}), 403
            return render_template("error.html", message="Admin access required"), 403
        return f(*args, **kwargs)
    return wrapper


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return redirect(url_for("dashboard"))

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",
                           username=session["username"],
                           role=session["role"])

@app.route("/members")
@login_required
def members_page():
    return render_template("members.html",
                           username=session["username"],
                           role=session["role"])

@app.route("/trips")
@login_required
def trips_page():
    return render_template("trips.html",
                           username=session["username"],
                           role=session["role"])

@app.route("/bookings")
@login_required
def bookings_page():
    return render_template("bookings.html",
                           username=session["username"],
                           role=session["role"])

@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html",
                           username=session["username"])

@app.route("/benchmark")
@login_required
def benchmark_page():
    return render_template("benchmark.html",
                           username=session["username"],
                           role=session["role"])

@app.route("/logs")
@admin_required
def logs_page():
    return render_template("logs.html", username=session["username"])


# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = (data or {}).get("username", "").strip()
    password = (data or {}).get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    db = get_db()
    user = db.execute(
        "SELECT u.UserID, u.username, u.password_hash, u.role, u.MemberID, "
        "       gm.group_name "
        "FROM users u LEFT JOIN group_mappings gm ON u.UserID = gm.UserID "
        "WHERE u.username = ?", (username,)
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        audit("LOGIN_FAILED", f"username={username}", "FAIL")
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["user_id"]   = user["UserID"]
    session["username"]  = user["username"]
    session["role"]      = user["role"]
    session["member_id"] = user["MemberID"]
    session["group"]     = user["group_name"]

    audit("LOGIN", f"username={username} role={user['role']}")
    return jsonify({
        "message": "Login successful",
        "role": user["role"],
        "username": user["username"],
        "group": user["group_name"]
    })

@app.route("/api/logout", methods=["POST"])
def api_logout():
    audit("LOGOUT")
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/me")
@login_required
def api_me():
    db = get_db()
    gm = db.execute("SELECT group_name FROM group_mappings WHERE UserID=?",
                    (session["user_id"],)).fetchone()
    return jsonify({
        "user_id":   session["user_id"],
        "username":  session["username"],
        "role":      session["role"],
        "member_id": session.get("member_id"),
        "group":     gm["group_name"] if gm else None
    })


# ── Member API (portfolio) ────────────────────────────────────────────────────
@app.route("/api/members", methods=["GET"])
@login_required
def api_members():
    db   = get_db()
    role = session.get("role")
    mid  = session.get("member_id")

    if role == "admin":
        rows = db.execute(
            "SELECT m.*, "
            "  CASE WHEN m.MemberType='Driver' THEN d.Status_ ELSE p.Status_ END AS Status_, "
            "  d.Rating, d.ExperienceYears, d.LicenseNumber "
            "FROM Member m "
            "LEFT JOIN Driver d ON m.MemberID=d.MemberID "
            "LEFT JOIN Passenger p ON m.MemberID=p.MemberID "
            "ORDER BY m.MemberID"
        ).fetchall()
    else:
        # Regular users can only see their own profile + basic list
        rows = db.execute(
            "SELECT m.*, "
            "  CASE WHEN m.MemberType='Driver' THEN d.Status_ ELSE p.Status_ END AS Status_, "
            "  d.Rating, d.ExperienceYears, d.LicenseNumber "
            "FROM Member m "
            "LEFT JOIN Driver d ON m.MemberID=d.MemberID "
            "LEFT JOIN Passenger p ON m.MemberID=p.MemberID "
            "WHERE m.MemberID=? OR 1=1 "  # basic list allowed; full detail only own
            "ORDER BY m.MemberID", (mid,)
        ).fetchall()

    members = []
    for r in rows:
        d = dict(r)
        # Non-admins get redacted contact info for OTHER members
        if role != "admin" and d.get("MemberID") != mid:
            d["Email"] = "***@***.com"
            d["ContactNumber"] = "+91*****"
        members.append(d)

    audit("READ_MEMBERS", f"count={len(members)}")
    return jsonify(members)

@app.route("/api/members/<int:member_id>", methods=["GET"])
@login_required
def api_member_detail(member_id):
    db   = get_db()
    role = session.get("role")
    mid  = session.get("member_id")

    if role != "admin" and mid != member_id:
        audit("READ_MEMBER_DENIED", f"target_member={member_id}", "FORBIDDEN")
        return jsonify({"error": "Access denied – you can only view your own profile"}), 403

    row = db.execute(
        "SELECT m.*, "
        "  d.DriverID, d.LicenseNumber, d.LicenseExpiryDate, d.ExperienceYears, d.Rating, d.Status_ AS DriverStatus, "
        "  p.PassengerID, p.EmergencyContact, p.PreferredPaymentMethod, p.SpecialAssistance, "
        "  p.NotificationPreference, p.Status_ AS PassengerStatus "
        "FROM Member m "
        "LEFT JOIN Driver d ON m.MemberID=d.MemberID "
        "LEFT JOIN Passenger p ON m.MemberID=p.MemberID "
        "WHERE m.MemberID=?", (member_id,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Member not found"}), 404

    audit("READ_MEMBER_DETAIL", f"member_id={member_id}")
    return jsonify(dict(row))

@app.route("/api/members/<int:member_id>", methods=["PUT"])
@login_required
def api_update_member(member_id):
    role = session.get("role")
    mid  = session.get("member_id")

    # Users can only update their own record; admins can update any
    if role != "admin" and mid != member_id:
        audit("UPDATE_MEMBER_DENIED", f"target={member_id}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}
    db   = get_db()

    # Fields users can update (restricted set); admins can update more
    if role == "admin":
        allowed = ["Name", "Age", "Gender", "Email", "ContactNumber", "MemberType", "Image"]
    else:
        allowed = ["ContactNumber", "Image"]  # users can only update contact + avatar

    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [member_id]
    db.execute(f"UPDATE Member SET {set_clause} WHERE MemberID=?", values)
    db.commit()

    audit("UPDATE_MEMBER", f"member_id={member_id} fields={list(updates.keys())}")
    return jsonify({"message": "Member updated", "updated": updates})

@app.route("/api/members", methods=["POST"])
@admin_required
def api_create_member():
    data = request.get_json() or {}
    db   = get_db()
    required = ["MemberID","Name","Age","Gender","Email","ContactNumber","MemberType","RegistrationDate"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    try:
        db.execute(
            "INSERT INTO Member (MemberID,Name,Image,Age,Gender,Email,ContactNumber,MemberType,RegistrationDate) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (data["MemberID"], data["Name"], data.get("Image",""), data["Age"],
             data["Gender"], data["Email"], data["ContactNumber"],
             data["MemberType"], data["RegistrationDate"])
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409

    audit("CREATE_MEMBER", f"member_id={data['MemberID']} name={data['Name']}")
    return jsonify({"message": "Member created", "MemberID": data["MemberID"]}), 201

@app.route("/api/members/<int:member_id>", methods=["DELETE"])
@admin_required
def api_delete_member(member_id):
    db = get_db()
    row = db.execute("SELECT Name FROM Member WHERE MemberID=?", (member_id,)).fetchone()
    if not row:
        return jsonify({"error": "Member not found"}), 404

    db.execute("DELETE FROM Member WHERE MemberID=?", (member_id,))
    db.commit()
    audit("DELETE_MEMBER", f"member_id={member_id} name={row['Name']}")
    return jsonify({"message": f"Member {member_id} deleted"})


# ── Trip API ──────────────────────────────────────────────────────────────────
@app.route("/api/trips", methods=["GET"])
@login_required
def api_trips():
    db     = get_db()
    status = request.args.get("status")
    date   = request.args.get("date")

    query  = ("SELECT t.*, r.RouteName, r.Source, r.Destination, "
              "  v.VehicleNumber, v.Model, "
              "  m.Name AS DriverName "
              "FROM Trip t "
              "JOIN Route r ON t.RouteID=r.RouteID "
              "JOIN Vehicle v ON t.VehicleID=v.VehicleID "
              "JOIN Driver d ON t.DriverID=d.DriverID "
              "JOIN Member m ON d.MemberID=m.MemberID")
    params = []
    filters = []
    if status:
        filters.append("t.Status_=?"); params.append(status)
    if date:
        filters.append("t.TripDate=?");  params.append(date)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY t.TripDate, t.ScheduledDepartureTime"

    rows = db.execute(query, params).fetchall()
    audit("READ_TRIPS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/trips/<int:trip_id>", methods=["GET"])
@login_required
def api_trip_detail(trip_id):
    db  = get_db()
    row = db.execute(
        "SELECT t.*, r.RouteName, r.Source, r.Destination, r.BaseFare, "
        "  v.VehicleNumber, v.Model, v.Capacity, "
        "  m.Name AS DriverName, d.Rating AS DriverRating "
        "FROM Trip t "
        "JOIN Route r ON t.RouteID=r.RouteID "
        "JOIN Vehicle v ON t.VehicleID=v.VehicleID "
        "JOIN Driver d ON t.DriverID=d.DriverID "
        "JOIN Member m ON d.MemberID=m.MemberID "
        "WHERE t.TripID=?", (trip_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "Trip not found"}), 404
    audit("READ_TRIP_DETAIL", f"trip_id={trip_id}")
    return jsonify(dict(row))


# ── Booking API ───────────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
@login_required
def api_bookings():
    db   = get_db()
    role = session.get("role")
    mid  = session.get("member_id")

    if role == "admin":
        rows = db.execute(
            "SELECT b.*, m.Name AS PassengerName, r.RouteName, t.TripDate "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID "
            "JOIN Member m ON p.MemberID=m.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID "
            "JOIN Route r ON t.RouteID=r.RouteID "
            "ORDER BY b.BookingTime DESC"
        ).fetchall()
    else:
        # Passengers see only their own bookings
        rows = db.execute(
            "SELECT b.*, m.Name AS PassengerName, r.RouteName, t.TripDate "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID "
            "JOIN Member m ON p.MemberID=m.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID "
            "JOIN Route r ON t.RouteID=r.RouteID "
            "WHERE p.MemberID=? "
            "ORDER BY b.BookingTime DESC", (mid,)
        ).fetchall()

    audit("READ_BOOKINGS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/bookings", methods=["POST"])
@login_required
def api_create_booking():
    data = request.get_json() or {}
    db   = get_db()
    role = session.get("role")
    mid  = session.get("member_id")

    # Passengers can only book for themselves
    # First resolve PassengerID from MemberID
    passenger = db.execute("SELECT PassengerID FROM Passenger WHERE MemberID=?", (mid,)).fetchone()
    if not passenger and role != "admin":
        return jsonify({"error": "Only passengers can create bookings"}), 403

    required = ["TripID", "SeatNumber"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    passenger_id = data.get("PassengerID") if role == "admin" else passenger["PassengerID"]
    trip_id      = data["TripID"]
    seat_number  = data["SeatNumber"]

    # Get fare from route
    fare_row = db.execute(
        "SELECT r.BaseFare FROM Trip t JOIN Route r ON t.RouteID=r.RouteID WHERE t.TripID=?",
        (trip_id,)
    ).fetchone()
    if not fare_row:
        return jsonify({"error": "Trip not found"}), 404

    import uuid
    qr = f"QR-TRIP{trip_id}-SEAT{seat_number}-PASS{passenger_id}-{uuid.uuid4().hex[:6].upper()}"

    # Get next BookingID
    max_id = db.execute("SELECT MAX(BookingID) FROM Booking").fetchone()[0] or 0

    try:
        db.execute(
            "INSERT INTO Booking (BookingID,PassengerID,TripID,SeatNumber,BookingTime,"
            "  BookingStatus,FareAmount,QRCode,QRCodeURL,VerificationStatus) "
            "VALUES (?,?,?,?,datetime('now'),?,?,?,?,?)",
            (max_id+1, passenger_id, trip_id, seat_number, "Confirmed",
             fare_row["BaseFare"], qr, f"https://shuttle.qr/{max_id+1}", "Pending")
        )
        # Decrement available seats
        db.execute("UPDATE Trip SET AvailableSeats=AvailableSeats-1 WHERE TripID=? AND AvailableSeats>0",
                   (trip_id,))
        db.commit()
    except sqlite3.IntegrityError as e:
        return jsonify({"error": str(e)}), 409

    audit("CREATE_BOOKING", f"booking_id={max_id+1} trip={trip_id} seat={seat_number}")
    return jsonify({"message": "Booking created", "BookingID": max_id+1, "QRCode": qr}), 201

@app.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
@login_required
def api_cancel_booking(booking_id):
    db   = get_db()
    role = session.get("role")
    mid  = session.get("member_id")

    bk = db.execute(
        "SELECT b.*, p.MemberID FROM Booking b "
        "JOIN Passenger p ON b.PassengerID=p.PassengerID "
        "WHERE b.BookingID=?", (booking_id,)
    ).fetchone()
    if not bk:
        return jsonify({"error": "Booking not found"}), 404

    # Users can only cancel their own bookings
    if role != "admin" and bk["MemberID"] != mid:
        audit("CANCEL_BOOKING_DENIED", f"booking_id={booking_id}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403

    db.execute("UPDATE Booking SET BookingStatus='Cancelled' WHERE BookingID=?", (booking_id,))
    db.execute("UPDATE Trip SET AvailableSeats=AvailableSeats+1 WHERE TripID=?", (bk["TripID"],))
    db.commit()

    audit("CANCEL_BOOKING", f"booking_id={booking_id}")
    return jsonify({"message": f"Booking {booking_id} cancelled"})


# ── Admin: Users & Groups ─────────────────────────────────────────────────────
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    db   = get_db()
    rows = db.execute(
        "SELECT u.UserID, u.username, u.role, u.MemberID, gm.group_name "
        "FROM users u LEFT JOIN group_mappings gm ON u.UserID=gm.UserID "
        "ORDER BY u.UserID"
    ).fetchall()
    audit("ADMIN_READ_USERS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/users/<int:user_id>/role", methods=["PUT"])
@admin_required
def api_update_role(user_id):
    data = request.get_json() or {}
    new_role = data.get("role")
    if new_role not in ("admin", "user"):
        return jsonify({"error": "Role must be 'admin' or 'user'"}), 400

    db = get_db()
    db.execute("UPDATE users SET role=? WHERE UserID=?", (new_role, user_id))
    db.commit()
    audit("UPDATE_USER_ROLE", f"user_id={user_id} new_role={new_role}")
    return jsonify({"message": f"User {user_id} role updated to {new_role}"})

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def api_delete_user(user_id):
    db  = get_db()
    row = db.execute("SELECT username FROM users WHERE UserID=?", (user_id,)).fetchone()
    if not row:
        return jsonify({"error": "User not found"}), 404
    db.execute("DELETE FROM users WHERE UserID=?", (user_id,))
    db.commit()
    audit("DELETE_USER", f"user_id={user_id} username={row['username']}")
    return jsonify({"message": f"User {user_id} deleted"})


# ── SubTask 4: Indexing ───────────────────────────────────────────────────────
INDEXES = [
    ("idx_booking_passenger",   "CREATE INDEX IF NOT EXISTS idx_booking_passenger   ON Booking(PassengerID)"),
    ("idx_booking_trip",        "CREATE INDEX IF NOT EXISTS idx_booking_trip         ON Booking(TripID)"),
    ("idx_booking_status",      "CREATE INDEX IF NOT EXISTS idx_booking_status       ON Booking(BookingStatus)"),
    ("idx_trip_date_status",    "CREATE INDEX IF NOT EXISTS idx_trip_date_status     ON Trip(TripDate, Status_)"),
    ("idx_trip_route",          "CREATE INDEX IF NOT EXISTS idx_trip_route           ON Trip(RouteID)"),
    ("idx_trip_driver",         "CREATE INDEX IF NOT EXISTS idx_trip_driver          ON Trip(DriverID)"),
    ("idx_driver_member",       "CREATE INDEX IF NOT EXISTS idx_driver_member        ON Driver(MemberID)"),
    ("idx_passenger_member",    "CREATE INDEX IF NOT EXISTS idx_passenger_member     ON Passenger(MemberID)"),
    ("idx_member_type",         "CREATE INDEX IF NOT EXISTS idx_member_type          ON Member(MemberType)"),
    ("idx_transaction_booking", "CREATE INDEX IF NOT EXISTS idx_transaction_booking  ON [Transaction](BookingID)"),
]

@app.route("/api/indexes/apply", methods=["POST"])
@admin_required
def api_apply_indexes():
    db = get_db()
    for name, sql in INDEXES:
        db.execute(sql)
    db.commit()
    audit("APPLY_INDEXES", f"count={len(INDEXES)}")
    return jsonify({"message": f"{len(INDEXES)} indexes applied", "indexes": [i[0] for i in INDEXES]})

@app.route("/api/indexes/drop", methods=["POST"])
@admin_required
def api_drop_indexes():
    db = get_db()
    for name, _ in INDEXES:
        db.execute(f"DROP INDEX IF EXISTS {name}")
    db.commit()
    audit("DROP_INDEXES", f"count={len(INDEXES)}")
    return jsonify({"message": f"{len(INDEXES)} indexes dropped"})

@app.route("/api/indexes/status", methods=["GET"])
@login_required
def api_index_status():
    db   = get_db()
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
    return jsonify({"indexes": [r["name"] for r in rows]})


# ── SubTask 5: Benchmarking ───────────────────────────────────────────────────
BENCHMARK_QUERIES = {
    "bookings_by_passenger": {
        "label": "Bookings by PassengerID (WHERE clause)",
        "sql": "SELECT * FROM Booking WHERE PassengerID = 1",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM Booking WHERE PassengerID = 1"
    },
    "trips_by_date_status": {
        "label": "Trips filtered by Date + Status (composite index)",
        "sql": "SELECT * FROM Trip WHERE TripDate='2026-02-15' AND Status_='InProgress'",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM Trip WHERE TripDate='2026-02-15' AND Status_='InProgress'"
    },
    "bookings_join_trip": {
        "label": "Bookings JOIN Trip JOIN Route (JOIN clause)",
        "sql": (
            "SELECT b.BookingID, m.Name, r.RouteName, t.TripDate, b.FareAmount "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID "
            "JOIN Member m ON p.MemberID=m.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID "
            "JOIN Route r ON t.RouteID=r.RouteID "
            "WHERE b.BookingStatus='Confirmed'"
        ),
        "explain_sql": (
            "EXPLAIN QUERY PLAN "
            "SELECT b.BookingID, m.Name, r.RouteName, t.TripDate, b.FareAmount "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID "
            "JOIN Member m ON p.MemberID=m.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID "
            "JOIN Route r ON t.RouteID=r.RouteID "
            "WHERE b.BookingStatus='Confirmed'"
        )
    },
    "transactions_by_booking": {
        "label": "Transactions by BookingID (FK lookup)",
        "sql": "SELECT * FROM [Transaction] WHERE BookingID=3",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM [Transaction] WHERE BookingID=3"
    },
    "drivers_by_member": {
        "label": "Driver detail by MemberID (JOIN lookup)",
        "sql": "SELECT d.*, m.Name FROM Driver d JOIN Member m ON d.MemberID=m.MemberID WHERE d.MemberID=22",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT d.*, m.Name FROM Driver d JOIN Member m ON d.MemberID=m.MemberID WHERE d.MemberID=22"
    },
}

def _run_benchmark_single(db, key, runs=200):
    q   = BENCHMARK_QUERIES[key]
    sql = q["sql"]

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        db.execute(sql).fetchall()
        times.append((time.perf_counter() - t0) * 1000)  # ms

    avg_ms = sum(times) / len(times)
    min_ms = min(times)
    max_ms = max(times)

    plan_rows = db.execute(q["explain_sql"]).fetchall()
    plan = [dict(r) for r in plan_rows]
    # Detect scan type
    plan_text = " ".join(str(r) for r in plan)
    if "USING INDEX" in plan_text or "SEARCH" in plan_text:
        scan_type = "INDEX SEEK"
    elif "SCAN" in plan_text:
        scan_type = "FULL TABLE SCAN"
    else:
        scan_type = "COVERING/OTHER"

    return {
        "label":     q["label"],
        "avg_ms":    round(avg_ms, 4),
        "min_ms":    round(min_ms, 4),
        "max_ms":    round(max_ms, 4),
        "runs":      runs,
        "scan_type": scan_type,
        "plan":      plan,
    }

@app.route("/api/benchmark/run", methods=["POST"])
@login_required
def api_benchmark_run():
    db      = get_db()
    results = {}

    # Check which indexes exist
    idx_rows = db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
    indexes_active = bool(idx_rows)

    for key in BENCHMARK_QUERIES:
        results[key] = _run_benchmark_single(db, key)

    audit("BENCHMARK_RUN", f"indexes_active={indexes_active}")
    return jsonify({
        "indexes_active": indexes_active,
        "active_indexes": [r["name"] for r in idx_rows],
        "results":        results
    })


# ── Audit Log API ─────────────────────────────────────────────────────────────
@app.route("/api/logs", methods=["GET"])
@admin_required
def api_logs():
    lines = []
    if os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG) as f:
            lines = f.readlines()[-200:]  # last 200 entries
    audit("READ_LOGS")
    return jsonify({"logs": [l.strip() for l in lines]})


if __name__ == "__main__":
    app.run(debug=True, port=5050)
