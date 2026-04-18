"""
ShuttleGo – Flask Backend
SubTask 3 : RBAC (admin / user roles, group-based access)
SubTask 4 : SQL Indexing
SubTask 5 : Performance Benchmarking
"""

import re
import os, time, logging, uuid
from datetime import datetime, timezone, timedelta, date
from functools import wraps

import jwt, bcrypt as _bcrypt
import mysql.connector
from flask import Flask, request, session, jsonify, redirect, url_for, render_template, g
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "shuttlego_secret_key_2024"

JWT_SECRET    = os.environ.get("JWT_SECRET", "shuttlego_jwt_secret_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_H  = 8

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG = os.path.join(BASE_DIR, "logs", "audit.log")
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

logging.basicConfig(
    filename=AUDIT_LOG,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# =========================
# SHARD CONFIG
# =========================
HOST = "10.0.116.184"
USER = "Infobase"
PASSWORD = "password@123"
DATABASE = "Infobase"

SHARD_PORTS = [3307, 3308, 3309]


def get_connection(port):
    return mysql.connector.connect(
        host=HOST,
        port=port,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )


# persistent shard connections
shards = [get_connection(p) for p in SHARD_PORTS]


# =========================
# SHARD ROUTING
# =========================
def get_shard(member_id):
    return shards[member_id % 3]


def get_shard_by_passenger(pid):
    return shards[pid % 3]


# =========================
# DEFAULT DB (GLOBAL TABLES)
# =========================
def get_db():
    return shards[0]


# =========================
# TEARDOWN (keep connections alive)
# =========================
@app.teardown_appcontext
def close_db(exc):
    pass


# =========================
# AUDIT LOGGING (UNCHANGED)
# =========================
def audit(action, detail="", status="OK"):
    logging.info(
        f"USER={session.get('username','ANONYMOUS')} "
        f"ROLE={session.get('role','none')} "
        f"IP={request.remote_addr} VIA=API "
        f"ACTION={action} STATUS={status} DETAIL={detail}"
    )


# =========================
# AUTH HELPERS (UNCHANGED)
# =========================
def _issue_jwt(user_id, username, role):
    now = datetime.now(tz=timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRY_H)
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def _decode_jwt(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _verify_password(plain, stored_hash):
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return _bcrypt.checkpw(plain.encode(), stored_hash.encode())
    return check_password_hash(stored_hash, plain)

# =========================
# TEARDOWN (FIXED FOR SHARDS)
# =========================
@app.teardown_appcontext
def close_db(exc):
    pass  # do NOT close shard connections


# =========================
# AUTH DECORATORS (UNCHANGED)
# =========================
def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            else:
                return redirect(url_for("login_page"))
        return f(*a, **kw)
    return w


def admin_required(f):
    @wraps(f)
    def w(*a, **kw):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "Authentication required"}), 401
            else:
                return redirect(url_for("login_page"))

        if session.get("role") != "admin":
            audit("ADMIN_ACTION_DENIED", f"endpoint={request.path}", "FORBIDDEN")
            if request.is_json:
                return jsonify({"error": "Admin access required"}), 403
            else:
                return render_template(
                    "error.html",
                    message="Admin access required"
                ), 403

        return f(*a, **kw)
    return w


# =========================
# CONTEXT HELPER (UNCHANGED)
# =========================
def _ctx():
    return {
        "username": session.get("username", ""),
        "role": session.get("role", ""),
        "group": session.get("group", "")
    }
# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(
        url_for("dashboard") if "user_id" in session else url_for("login_page")
    )


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", **_ctx())


@app.route("/members")
@login_required
def members_page():
    return render_template("members.html", **_ctx())


@app.route("/trips")
@login_required
def trips_page():
    return render_template("trips.html", **_ctx())


@app.route("/bookings")
@login_required
def bookings_page():
    return render_template("bookings.html", **_ctx())


@app.route("/schedule")
@login_required
def schedule_page():
    return render_template("schedule.html", **_ctx())


@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html", **_ctx())


@app.route("/benchmark")
@admin_required
def benchmark_page():
    return render_template("benchmark.html", **_ctx())


@app.route("/logs")
@admin_required
def logs_page():
    return render_template("logs.html", **_ctx())
# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = (data or {}).get("username", "").strip()
    password = (data or {}).get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = None

    # =========================
    # SEARCH ACROSS ALL SHARDS
    # =========================
    for conn in shards:
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT u.UserID, u.username, u.password_hash, u.role, u.MemberID, gm.group_name
            FROM users u
            LEFT JOIN group_mappings gm ON u.UserID = gm.UserID
            WHERE u.username = %s
        """, (username,))

        result = cur.fetchone()

        if result:
            user = result
            break

    # =========================
    # AUTH CHECK
    # =========================
    if not user or not _verify_password(password, user["password_hash"]):
        audit("LOGIN_FAILED", f"username={username}", "FAIL")
        return jsonify({"error": "Invalid credentials"}), 401

    # =========================
    # SESSION SETUP (UNCHANGED)
    # =========================
    session.clear()
    session.update({
        "user_id": user["UserID"],
        "username": user["username"],
        "role": user["role"],
        "member_id": user["MemberID"],
        "group": user["group_name"]
    })

    # =========================
    # JWT
    # =========================
    token = _issue_jwt(user["UserID"], user["username"], user["role"])

    audit("LOGIN", f"username={username} role={user['role']}")

    return jsonify({
        "message": "Login successful",
        "session_token": token,
        "role": user["role"],
        "username": user["username"],
        "group": user["group_name"]
    })
# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/api/logout", methods=["POST"])
def api_logout():
    audit("LOGOUT")
    session.clear()
    return jsonify({"message": "Logged out"})


@app.route("/api/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    first    = data.get("first_name", "").strip()
    last     = data.get("last_name", "").strip()
    role_req = data.get("role_request", "passenger")

    # ── Validation (UNCHANGED) ────────────────────────────────────────────────
    if not username or not email or not password or not first or not last:
        return jsonify({"error": "All fields are required"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return jsonify({"error": "Invalid email address"}), 400

    if role_req not in ("passenger", "driver"):
        role_req = "passenger"

    # =========================
    # DUPLICATE CHECKS (ALL SHARDS)
    # =========================
    for conn in shards:
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM users WHERE username=%s LIMIT 1", (username,))
        if cur.fetchone():
            return jsonify({"error": "Username is already taken — please choose another"}), 409

        cur.execute("SELECT 1 FROM Member WHERE Email=%s LIMIT 1", (email,))
        if cur.fetchone():
            return jsonify({"error": "An account with this email already exists"}), 409

    # =========================
    # GLOBAL MAX IDS (ALL SHARDS)
    # =========================
    max_mid = max_pid = max_did = max_uid = max_gid = 0

    for conn in shards:
        cur = conn.cursor()

        cur.execute("SELECT MAX(MemberID) FROM Member")
        max_mid = max(max_mid, cur.fetchone()[0] or 0)

        cur.execute("SELECT MAX(PassengerID) FROM Passenger")
        max_pid = max(max_pid, cur.fetchone()[0] or 0)

        cur.execute("SELECT MAX(DriverID) FROM Driver")
        max_did = max(max_did, cur.fetchone()[0] or 0)

        cur.execute("SELECT MAX(UserID) FROM users")
        max_uid = max(max_uid, cur.fetchone()[0] or 0)

        cur.execute("SELECT MAX(MappingID) FROM group_mappings")
        max_gid = max(max_gid, cur.fetchone()[0] or 0)

    new_mid = max_mid + 1

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    conn = get_shard(new_mid)
    cur  = conn.cursor()

    member_type = "Passenger" if role_req == "passenger" else "Driver"

    # =========================
    # INSERT MEMBER
    # =========================
    cur.execute("""
        INSERT INTO Member
        (MemberID, Name, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        new_mid,
        f"{first} {last}",
        0,
        "Other",
        email,
        "",
        member_type,
        str(date.today())
    ))

    # =========================
    # INSERT SUB PROFILE
    # =========================
    if member_type == "Passenger":
        new_pid = max_pid + 1

        cur.execute("""
            INSERT INTO Passenger
            (PassengerID, MemberID, EmergencyContact, PreferredPaymentMethod,
             SpecialAssistance, NotificationPreference, Status_)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            new_pid,
            new_mid,
            None,
            "UPI",
            None,
            "App",
            "Active"
        ))

        group = "passenger_group"

    else:
        new_did = max_did + 1
        fake_license = f"DL{new_mid:06d}"

        cur.execute("""
            INSERT INTO Driver
            (DriverID, MemberID, LicenseNumber, LicenseExpiryDate,
             ExperienceYears, Rating, Status_)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            new_did,
            new_mid,
            fake_license,
            "2030-01-01",
            0,
            0.0,
            "Off-Duty"
        ))

        group = "driver_group"

    # =========================
    # INSERT USER
    # =========================
    new_uid = max_uid + 1
    pw_hash = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users (UserID, username, password_hash, role, MemberID)
        VALUES (%s,%s,%s,%s,%s)
    """, (new_uid, username, pw_hash, "user", new_mid))

    # =========================
    # INSERT GROUP MAPPING
    # =========================
    new_gid = max_gid + 1

    cur.execute("""
        INSERT INTO group_mappings (MappingID, UserID, group_name)
        VALUES (%s,%s,%s)
    """, (new_gid, new_uid, group))

    conn.commit()

    audit("REGISTER", f"username={username} role={group} member_id={new_mid}")

    return jsonify({
        "message": "Account created successfully",
        "username": username,
        "role": "user",
        "group": group
    }), 201

# ── Auth Info ─────────────────────────────────────────────────────────────────
@app.route("/api/me")
@login_required
def api_me():

    member_id = session.get("member_id")

    gm = None

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    if member_id is not None:
        conn = get_shard(member_id)
        cur  = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT group_name FROM group_mappings WHERE UserID=%s",
            (session["user_id"],)
        )
        gm = cur.fetchone()

    else:
        # fallback (admin or edge case)
        for conn in shards:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT group_name FROM group_mappings WHERE UserID=%s",
                (session["user_id"],)
            )
            gm = cur.fetchone()
            if gm:
                break

    return jsonify({
        "user_id": session["user_id"],
        "username": session["username"],
        "role": session["role"],
        "member_id": member_id,
        "group": gm["group_name"] if gm else None
    })


# ── Auth Check ────────────────────────────────────────────────────────────────
@app.route("/isAuth", methods=["GET"])
def is_auth():
    token = request.headers.get("Authorization", "")[7:].strip() or request.args.get("token", "")

    if not token:
        return jsonify({"error": "No session found"}), 401

    try:
        payload = _decode_jwt(token)

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401

    except jwt.PyJWTError:
        return jsonify({"error": "Invalid session token"}), 401

    return jsonify({
        "message": "User is authenticated",
        "username": payload["username"],
        "role": payload["role"],
        "expiry": datetime.fromtimestamp(
            payload["exp"],
            tz=timezone.utc
        ).isoformat()
    })
@app.route("/api/me/password", methods=["PUT"])
@login_required
def api_change_password():

    data = request.get_json() or {}
    cur  = data.get("current_password", "")
    new_ = data.get("new_password", "")
    con  = data.get("confirm_password", "")

    if not cur or not new_:
        return jsonify({"error": "Current and new password are required"}), 400

    if new_ != con:
        return jsonify({"error": "New passwords do not match"}), 400

    if len(new_) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    if new_ == cur:
        return jsonify({"error": "New password must differ from current password"}), 400

    user_id   = session["user_id"]
    member_id = session.get("member_id")

    user = None
    conn = None

    # =========================
    # FIND USER (CORRECT SHARD)
    # =========================
    if member_id is not None:
        conn = get_shard(member_id)
        cur_db = conn.cursor(dictionary=True)

        cur_db.execute(
            "SELECT password_hash FROM users WHERE UserID=%s",
            (user_id,)
        )
        user = cur_db.fetchone()

    else:
        # fallback (admin)
        for sconn in shards:
            cur_db = sconn.cursor(dictionary=True)
            cur_db.execute(
                "SELECT password_hash FROM users WHERE UserID=%s",
                (user_id,)
            )
            res = cur_db.fetchone()
            if res:
                user = res
                conn = sconn
                break

    if not user or not _verify_password(cur, user["password_hash"]):
        audit("PASSWORD_CHANGE_FAILED", "incorrect current password", "FAIL")
        return jsonify({"error": "Current password is incorrect"}), 401

    # =========================
    # UPDATE PASSWORD
    # =========================
    cur_db = conn.cursor()
    cur_db.execute(
        "UPDATE users SET password_hash=%s WHERE UserID=%s",
        (generate_password_hash(new_), user_id)
    )

    conn.commit()

    audit("PASSWORD_CHANGED", f"user_id={user_id}")

    return jsonify({"message": "Password changed successfully"})


# ── Members ───────────────────────────────────────────────────────────────────
@app.route("/api/members", methods=["GET"])
@login_required
def api_members():

    role = session.get("role")
    mid  = session.get("member_id")

    query = """
        SELECT m.*,
               CASE WHEN m.MemberType='Driver' THEN d.Status_ ELSE p.Status_ END AS Status_,
               d.Rating, d.ExperienceYears, d.LicenseNumber
        FROM Member m
        LEFT JOIN Driver d ON m.MemberID = d.MemberID
        LEFT JOIN Passenger p ON m.MemberID = p.MemberID
    """

    results = []

    # =========================
    # ADMIN → ALL SHARDS
    # =========================
    if role == "admin":

        for conn in shards:
            cur = conn.cursor(dictionary=True)
            cur.execute(query + " ORDER BY m.MemberID")
            results.extend(cur.fetchall())

    # =========================
    # USER → OWN SHARD ONLY
    # =========================
    else:
        conn = get_shard(mid)
        cur  = conn.cursor(dictionary=True)

        cur.execute(query + " WHERE m.MemberID=%s", (mid,))
        results = cur.fetchall()

    audit("READ_MEMBERS", f"count={len(results)}")

    return jsonify(results)

@app.route("/api/members/<int:mid>", methods=["GET"])
@login_required
def api_member_detail(mid):

    role   = session.get("role")
    my_mid = session.get("member_id")

    if role != "admin" and my_mid != mid:
        audit("READ_MEMBER_DENIED", f"target_member={mid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403

    row = None

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    if role == "admin":
        # search across shards (safe)
        for conn in shards:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT m.*, d.DriverID, d.LicenseNumber, d.LicenseExpiryDate,
                       d.ExperienceYears, d.Rating, d.Status_ AS DriverStatus,
                       p.PassengerID, p.EmergencyContact, p.PreferredPaymentMethod,
                       p.SpecialAssistance, p.NotificationPreference,
                       p.Status_ AS PassengerStatus
                FROM Member m
                LEFT JOIN Driver d ON m.MemberID = d.MemberID
                LEFT JOIN Passenger p ON m.MemberID = p.MemberID
                WHERE m.MemberID = %s
            """, (mid,))
            row = cur.fetchone()
            if row:
                break
    else:
        conn = get_shard(mid)
        cur  = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT m.*, d.DriverID, d.LicenseNumber, d.LicenseExpiryDate,
                   d.ExperienceYears, d.Rating, d.Status_ AS DriverStatus,
                   p.PassengerID, p.EmergencyContact, p.PreferredPaymentMethod,
                   p.SpecialAssistance, p.NotificationPreference,
                   p.Status_ AS PassengerStatus
            FROM Member m
            LEFT JOIN Driver d ON m.MemberID = d.MemberID
            LEFT JOIN Passenger p ON m.MemberID = p.MemberID
            WHERE m.MemberID = %s
        """, (mid,))
        row = cur.fetchone()

    if not row:
        return jsonify({"error": "Member not found"}), 404

    audit("READ_MEMBER_DETAIL", f"member_id={mid}")

    return jsonify(row)


@app.route("/api/members/<int:mid>", methods=["PUT"])
@login_required
def api_update_member(mid):

    role   = session.get("role")
    my_mid = session.get("member_id")

    if role != "admin" and my_mid != mid:
        audit("UPDATE_MEMBER_DENIED", f"target={mid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json() or {}

    allowed = (
        ["Name","Age","Gender","Email","ContactNumber","MemberType","Image"]
        if role == "admin"
        else ["ContactNumber","Image"]
    )

    updates = {k: v for k, v in data.items() if k in allowed}

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    conn = get_shard(mid)
    cur  = conn.cursor()

    set_clause = ", ".join(f"{k}=%s" for k in updates)

    cur.execute(
        f"UPDATE Member SET {set_clause} WHERE MemberID=%s",
        list(updates.values()) + [mid]
    )

    conn.commit()

    audit("UPDATE_MEMBER", f"member_id={mid} fields={list(updates.keys())}")

    return jsonify({"message": "Member updated", "updated": updates})

# ── Members (Admin Create/Delete) ─────────────────────────────────────────────
@app.route("/api/members", methods=["POST"])
@admin_required
def api_create_member():

    data = request.get_json() or {}

    required = [
        "MemberID", "Name", "Age", "Gender",
        "Email", "ContactNumber", "MemberType", "RegistrationDate"
    ]

    missing = [f for f in required if f not in data]

    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    member_id = data["MemberID"]

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    conn = get_shard(member_id)
    cur  = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Member
            (MemberID, Name, Image, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["MemberID"],
            data["Name"],
            data.get("Image", ""),
            data["Age"],
            data["Gender"],
            data["Email"],
            data["ContactNumber"],
            data["MemberType"],
            data["RegistrationDate"]
        ))

        conn.commit()

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 409

    audit("CREATE_MEMBER", f"member_id={member_id}")

    return jsonify({
        "message": "Member created",
        "MemberID": member_id
    }), 201


@app.route("/api/members/<int:mid>", methods=["DELETE"])
@admin_required
def api_delete_member(mid):

    # =========================
    # ROUTE TO CORRECT SHARD
    # =========================
    conn = get_shard(mid)
    cur  = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT Name FROM Member WHERE MemberID=%s",
        (mid,)
    )
    row = cur.fetchone()

    if not row:
        return jsonify({"error": "Member not found"}), 404

    cur = conn.cursor()
    cur.execute(
        "DELETE FROM Member WHERE MemberID=%s",
        (mid,)
    )

    conn.commit()

    audit("DELETE_MEMBER", f"member_id={mid}")

    return jsonify({"message": f"Member {mid} deleted"})
# ── Trips ─────────────────────────────────────────────────────────────────────
# ── Trips ─────────────────────────────────────────────────────────────────────
@app.route("/api/trips", methods=["GET"])
@login_required
def api_trips():

    conn = get_db()  # shard 0 (global tables)
    cur  = conn.cursor(dictionary=True)

    status = request.args.get("status")
    trip_date = request.args.get("date")

    query = """
        SELECT t.*, r.RouteName, r.Source, r.Destination,
               v.VehicleNumber, v.Model,
               m.Name AS DriverName
        FROM Trip t
        JOIN Route r ON t.RouteID = r.RouteID
        JOIN Vehicle v ON t.VehicleID = v.VehicleID
        JOIN Driver d ON t.DriverID = d.DriverID
        JOIN Member m ON d.MemberID = m.MemberID
    """

    filters = []
    params  = []

    if status:
        filters.append("t.Status_ = %s")
        params.append(status)

    if trip_date:
        filters.append("t.TripDate = %s")
        params.append(trip_date)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY t.TripDate, t.ScheduledDepartureTime"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    audit("READ_TRIPS", f"count={len(rows)}")

    return jsonify(rows)


@app.route("/api/trips/<int:tid>", methods=["GET"])
@login_required
def api_trip_detail(tid):

    conn = get_db()  # shard 0
    cur  = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT t.*, r.RouteName, r.Source, r.Destination, r.BaseFare,
               v.VehicleNumber, v.Model, v.Capacity, v.VehicleID,
               m.Name AS DriverName, d.Rating AS DriverRating
        FROM Trip t
        JOIN Route r ON t.RouteID = r.RouteID
        JOIN Vehicle v ON t.VehicleID = v.VehicleID
        JOIN Driver d ON t.DriverID = d.DriverID
        JOIN Member m ON d.MemberID = m.MemberID
        WHERE t.TripID = %s
    """, (tid,))

    row = cur.fetchone()

    if not row:
        return jsonify({"error": "Trip not found"}), 404

    audit("READ_TRIP_DETAIL", f"trip_id={tid}")

    return jsonify(row)

# ── Bookings ──────────────────────────────────────────────────────────────────
# ── Bookings ──────────────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
@login_required
def api_bookings():

    role = session.get("role")
    mid  = session.get("member_id")

    results = []

    # =========================
    # ADMIN → ALL SHARDS
    # =========================
    if role == "admin":
        for conn in shards:
            cur = conn.cursor(dictionary=True)

            cur.execute("""
                SELECT b.*, m.Name AS PassengerName
                FROM Booking b
                JOIN Passenger p ON b.PassengerID = p.PassengerID
                JOIN Member m ON p.MemberID = m.MemberID
                ORDER BY b.BookingTime DESC
            """)

            results.extend(cur.fetchall())

    # =========================
    # USER → OWN SHARD
    # =========================
    else:
        conn = get_shard(mid)
        cur  = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT b.*, m.Name AS PassengerName
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Member m ON p.MemberID = m.MemberID
            WHERE p.MemberID = %s
            ORDER BY b.BookingTime DESC
        """, (mid,))

        results = cur.fetchall()

    # =========================
    # ENRICH WITH TRIP DATA (GLOBAL)
    # =========================
    gconn = get_db()
    gcur  = gconn.cursor(dictionary=True)

    for r in results:
        gcur.execute("""
            SELECT t.TripDate, r.RouteName
            FROM Trip t
            JOIN Route r ON t.RouteID = r.RouteID
            WHERE t.TripID = %s
        """, (r["TripID"],))
        info = gcur.fetchone()

        if info:
            r["TripDate"] = info["TripDate"]
            r["RouteName"] = info["RouteName"]

    audit("READ_BOOKINGS", f"count={len(results)}")

    return jsonify(results)


@app.route("/api/bookings", methods=["POST"])
@login_required
def api_create_booking():

    data = request.get_json() or {}

    role = session.get("role")
    mid  = session.get("member_id")

    # =========================
    # FIND PASSENGER
    # =========================
    conn_user = get_shard(mid)
    cur_user  = conn_user.cursor(dictionary=True)

    cur_user.execute(
        "SELECT PassengerID FROM Passenger WHERE MemberID=%s",
        (mid,)
    )
    passenger = cur_user.fetchone()

    if not passenger and role != "admin":
        return jsonify({"error": "Only passengers can create bookings"}), 403

    missing = [f for f in ["TripID", "SeatNumber"] if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    pid  = data.get("PassengerID") if role == "admin" else passenger["PassengerID"]
    tid  = data["TripID"]
    seat = data["SeatNumber"]

    # =========================
    # FETCH TRIP (GLOBAL)
    # =========================
    gconn = get_db()
    gcur  = gconn.cursor(dictionary=True)

    gcur.execute("""
        SELECT r.BaseFare
        FROM Trip t
        JOIN Route r ON t.RouteID = r.RouteID
        WHERE t.TripID = %s
    """, (tid,))
    fare_row = gcur.fetchone()

    if not fare_row:
        return jsonify({"error": "Trip not found"}), 404

    # =========================
    # ROUTE BOOKING TO SHARD
    # =========================
    conn = get_shard_by_passenger(pid)
    cur  = conn.cursor()

    # global booking id
    max_id = 0
    for s in shards:
        scur = s.cursor()
        scur.execute("SELECT MAX(BookingID) FROM Booking")
        max_id = max(max_id, scur.fetchone()[0] or 0)

    new_id = max_id + 1

    qr = f"QR-TRIP{tid}-SEAT{seat}-PASS{pid}-{uuid.uuid4().hex[:6].upper()}"

    try:
        cur.execute("""
            INSERT INTO Booking
            (BookingID, PassengerID, TripID, SeatNumber,
             BookingTime, BookingStatus, FareAmount,
             QRCode, QRCodeURL, VerificationStatus)
            VALUES (%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s)
        """, (
            new_id, pid, tid, seat,
            "Confirmed", fare_row["BaseFare"],
            qr, f"https://shuttle.qr/{new_id}", "Pending"
        ))

        conn.commit()

        # update seats in global shard
        gcur.execute(
            "UPDATE Trip SET AvailableSeats=AvailableSeats-1 WHERE TripID=%s AND AvailableSeats>0",
            (tid,)
        )
        gconn.commit()

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 409

    audit("CREATE_BOOKING", f"booking_id={new_id} trip={tid} seat={seat}")

    return jsonify({
        "message": "Booking created",
        "BookingID": new_id,
        "QRCode": qr
    }), 201


@app.route("/api/bookings/<int:bid>", methods=["DELETE"])
@login_required
def api_cancel_booking(bid):

    role = session.get("role")
    mid  = session.get("member_id")

    booking = None
    conn    = None

    # =========================
    # FIND BOOKING (ALL SHARDS)
    # =========================
    for sconn in shards:
        cur = sconn.cursor(dictionary=True)

        cur.execute("""
            SELECT b.*, p.MemberID
            FROM Booking b
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            WHERE b.BookingID = %s
        """, (bid,))

        res = cur.fetchone()

        if res:
            booking = res
            conn    = sconn
            break

    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    if role != "admin" and booking["MemberID"] != mid:
        audit("CANCEL_BOOKING_DENIED", f"booking_id={bid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403

    # =========================
    # UPDATE BOOKING
    # =========================
    cur = conn.cursor()
    cur.execute(
        "UPDATE Booking SET BookingStatus='Cancelled' WHERE BookingID=%s",
        (bid,)
    )
    conn.commit()

    # =========================
    # UPDATE GLOBAL TRIP
    # =========================
    gconn = get_db()
    gcur  = gconn.cursor()

    gcur.execute(
        "UPDATE Trip SET AvailableSeats=AvailableSeats+1 WHERE TripID=%s",
        (booking["TripID"],)
    )
    gconn.commit()

    audit("CANCEL_BOOKING", f"booking_id={bid}")

    return jsonify({"message": f"Booking {bid} cancelled"})

# ── Admin users ───────────────────────────────────────────────────────────────
# ── Admin Users ───────────────────────────────────────────────────────────────
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():

    results = []

    # =========================
    # SCAN ALL SHARDS
    # =========================
    for conn in shards:
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT u.UserID, u.username, u.role, u.MemberID, gm.group_name
            FROM users u
            LEFT JOIN group_mappings gm ON u.UserID = gm.UserID
        """)

        results.extend(cur.fetchall())

    # sort globally
    results.sort(key=lambda x: x["UserID"])

    audit("ADMIN_READ_USERS", f"count={len(results)}")

    return jsonify(results)


@app.route("/api/admin/users/<int:uid>/role", methods=["PUT"])
@admin_required
def api_update_role(uid):

    data = request.get_json() or {}
    new_role = data.get("role")

    if new_role not in ("admin", "user"):
        return jsonify({"error": "Role must be 'admin' or 'user'"}), 400

    updated = False

    # =========================
    # FIND USER SHARD
    # =========================
    for conn in shards:
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM users WHERE UserID=%s", (uid,))
        if cur.fetchone():
            cur.execute(
                "UPDATE users SET role=%s WHERE UserID=%s",
                (new_role, uid)
            )
            conn.commit()
            updated = True
            break

    if not updated:
        return jsonify({"error": "User not found"}), 404

    audit("UPDATE_USER_ROLE", f"user_id={uid} new_role={new_role}")

    return jsonify({"message": f"User {uid} role updated to {new_role}"})


@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def api_delete_user(uid):

    found_user = None
    conn       = None

    # =========================
    # FIND USER SHARD
    # =========================
    for sconn in shards:
        cur = sconn.cursor(dictionary=True)

        cur.execute(
            "SELECT username FROM users WHERE UserID=%s",
            (uid,)
        )
        res = cur.fetchone()

        if res:
            found_user = res
            conn       = sconn
            break

    if not found_user:
        return jsonify({"error": "User not found"}), 404

    # =========================
    # DELETE USER
    # =========================
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM users WHERE UserID=%s",
        (uid,)
    )
    conn.commit()

    audit("DELETE_USER", f"user_id={uid} username={found_user['username']}")

    return jsonify({"message": f"User {uid} deleted"})
# ── Driver Assignments ────────────────────────────────────────────────────────
@app.route("/api/my/assignments", methods=["GET"])
@login_required
def api_my_assignments():

    conn = get_db()  # shard 0 (global tables)
    cur  = conn.cursor(dictionary=True)

    role = session.get("role")
    mid  = session.get("member_id")

    # =========================
    # ADMIN → ALL ASSIGNMENTS
    # =========================
    if role == "admin":

        cur.execute("""
            SELECT da.*, mn.Name AS DriverName,
                   v.VehicleNumber, v.Model,
                   r.RouteName, r.Source, r.Destination,
                   t.TripDate, t.ScheduledDepartureTime,
                   t.ScheduledArrivalTime, t.Status_ AS TripStatus
            FROM DriverAssignment da
            JOIN Driver d ON da.DriverID = d.DriverID
            JOIN Member mn ON d.MemberID = mn.MemberID
            JOIN Vehicle v ON da.VehicleID = v.VehicleID
            JOIN Trip t ON da.TripID = t.TripID
            JOIN Route r ON t.RouteID = r.RouteID
            ORDER BY da.AssignedDate DESC, da.ShiftStart
        """)

        rows = cur.fetchall()

    # =========================
    # DRIVER → OWN ASSIGNMENTS
    # =========================
    else:

        # find driver profile
        cur.execute(
            "SELECT DriverID FROM Driver WHERE MemberID = %s",
            (mid,)
        )
        driver = cur.fetchone()

        if not driver:
            audit("READ_MY_ASSIGNMENTS_DENIED", "not a driver", "FORBIDDEN")
            return jsonify({"error": "No driver profile found for this account"}), 403

        cur.execute("""
            SELECT da.*, v.VehicleNumber, v.Model, v.Capacity,
                   r.RouteName, r.Source, r.Destination,
                   t.TripDate, t.ScheduledDepartureTime,
                   t.ScheduledArrivalTime, t.Status_ AS TripStatus
            FROM DriverAssignment da
            JOIN Vehicle v ON da.VehicleID = v.VehicleID
            JOIN Trip t ON da.TripID = t.TripID
            JOIN Route r ON t.RouteID = r.RouteID
            WHERE da.DriverID = %s
            ORDER BY da.AssignedDate DESC, da.ShiftStart
        """, (driver["DriverID"],))

        rows = cur.fetchall()

    audit("READ_MY_ASSIGNMENTS", f"count={len(rows)}")

    return jsonify(rows)
# ── NoShow Penalties ──────────────────────────────────────────────────────────
@app.route("/api/my/penalties", methods=["GET"])
@login_required
def api_my_penalties():

    conn = get_db()  # global tables
    cur  = conn.cursor(dictionary=True)

    role = session.get("role")
    mid  = session.get("member_id")

    if role == "admin":

        cur.execute("""
            SELECT nsp.*, b.BookingID, mn.Name AS PassengerName,
                   r.RouteName, t.TripDate
            FROM NoShowPenalty nsp
            JOIN Booking b ON nsp.BookingID = b.BookingID
            JOIN Passenger p ON b.PassengerID = p.PassengerID
            JOIN Member mn ON p.MemberID = mn.MemberID
            JOIN Trip t ON b.TripID = t.TripID
            JOIN Route r ON t.RouteID = r.RouteID
            ORDER BY nsp.DetectionTime DESC
        """)
        rows = cur.fetchall()

    else:
        # find passenger (sharded)
        passenger = None
        for sconn in shards:
            scur = sconn.cursor(dictionary=True)
            scur.execute(
                "SELECT PassengerID FROM Passenger WHERE MemberID=%s",
                (mid,)
            )
            res = scur.fetchone()
            if res:
                passenger = res
                break

        if not passenger:
            return jsonify([])

        cur.execute("""
            SELECT nsp.*, r.RouteName, t.TripDate
            FROM NoShowPenalty nsp
            JOIN Booking b ON nsp.BookingID = b.BookingID
            JOIN Trip t ON b.TripID = t.TripID
            JOIN Route r ON t.RouteID = r.RouteID
            WHERE b.PassengerID = %s
            ORDER BY nsp.DetectionTime DESC
        """, (passenger["PassengerID"],))
        rows = cur.fetchall()

    audit("READ_MY_PENALTIES", f"count={len(rows)}")

    return jsonify(rows)


# ── Vehicle Live Location ─────────────────────────────────────────────────────
@app.route("/api/vehicles/locations", methods=["GET"])
@login_required
def api_vehicle_locations():

    conn = get_db()
    cur  = conn.cursor(dictionary=True)

    role = session.get("role")
    mid  = session.get("member_id")

    latest = "SELECT MAX(LocationID) FROM VehicleLiveLocation GROUP BY VehicleID"

    if role == "admin":

        cur.execute(f"""
            SELECT vll.*, v.VehicleNumber, v.Model, v.CurrentStatus
            FROM VehicleLiveLocation vll
            JOIN Vehicle v ON vll.VehicleID = v.VehicleID
            WHERE vll.LocationID IN ({latest})
            ORDER BY vll.Timestamp DESC
        """)
        rows = cur.fetchall()

    else:
        # get passenger id (sharded)
        passenger = None
        for sconn in shards:
            scur = sconn.cursor(dictionary=True)
            scur.execute(
                "SELECT PassengerID FROM Passenger WHERE MemberID=%s",
                (mid,)
            )
            res = scur.fetchone()
            if res:
                passenger = res
                break

        if not passenger:
            return jsonify([])

        cur.execute(f"""
            SELECT vll.*, v.VehicleNumber, v.Model
            FROM VehicleLiveLocation vll
            JOIN Vehicle v ON vll.VehicleID = v.VehicleID
            WHERE vll.LocationID IN ({latest})
              AND vll.VehicleID IN (
                SELECT t.VehicleID
                FROM Trip t
                JOIN Booking b ON t.TripID = b.TripID
                WHERE b.PassengerID = %s
                  AND b.BookingStatus = 'Confirmed'
                  AND t.Status_ IN ('Scheduled','InProgress')
              )
            ORDER BY vll.Timestamp DESC
        """, (passenger["PassengerID"],))
        rows = cur.fetchall()

    audit("READ_VEHICLE_LOCATIONS", f"count={len(rows)}")

    return jsonify(rows)


@app.route("/api/vehicles/<int:vid>/location", methods=["GET"])
@login_required
def api_vehicle_location(vid):

    conn = get_db()
    cur  = conn.cursor(dictionary=True)

    role = session.get("role")
    mid  = session.get("member_id")

    if role != "admin":

        allowed = 0

        # =========================
        # CHECK BOOKINGS (ALL SHARDS)
        # =========================
        for sconn in shards:
            scur = sconn.cursor()
            scur.execute("""
                SELECT COUNT(*)
                FROM Booking b
                JOIN Passenger p ON b.PassengerID = p.PassengerID
                JOIN Trip t ON b.TripID = t.TripID
                WHERE t.VehicleID = %s
                  AND p.MemberID = %s
                  AND b.BookingStatus = 'Confirmed'
                  AND t.Status_ IN ('Scheduled','InProgress')
            """, (vid, mid))
            if scur.fetchone()[0] > 0:
                allowed = 1
                break

        # =========================
        # CHECK DRIVER ASSIGNMENT
        # =========================
        if not allowed:
            cur.execute(
                "SELECT DriverID FROM Driver WHERE MemberID=%s",
                (mid,)
            )
            driver = cur.fetchone()

            if driver:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM DriverAssignment
                    WHERE VehicleID = %s
                      AND DriverID = %s
                      AND Status_ = 'Assigned'
                """, (vid, driver["DriverID"]))
                allowed = cur.fetchone()[0]

        if not allowed:
            audit("READ_VEHICLE_LOCATION_DENIED", f"vehicle_id={vid}", "FORBIDDEN")
            return jsonify({"error": "Access denied to this vehicle's location"}), 403

    # =========================
    # FETCH LOCATION
    # =========================
    cur.execute("""
        SELECT vll.*, v.VehicleNumber, v.Model
        FROM VehicleLiveLocation vll
        JOIN Vehicle v ON vll.VehicleID = v.VehicleID
        WHERE vll.VehicleID = %s
        ORDER BY vll.Timestamp DESC
        LIMIT 1
    """, (vid,))
    row = cur.fetchone()

    if not row:
        return jsonify({"error": "No location data available for this vehicle"}), 404

    audit("READ_VEHICLE_LOCATION", f"vehicle_id={vid}")

    return jsonify(row)
# ── Indexing ──────────────────────────────────────────────────────────────────
INDEXES = [
    ("idx_booking_passenger",   "CREATE INDEX idx_booking_passenger   ON Booking(PassengerID)"),
    ("idx_booking_trip",        "CREATE INDEX idx_booking_trip        ON Booking(TripID)"),
    ("idx_booking_status",      "CREATE INDEX idx_booking_status      ON Booking(BookingStatus)"),
    ("idx_trip_date_status",    "CREATE INDEX idx_trip_date_status    ON Trip(TripDate, Status_)"),
    ("idx_trip_route",          "CREATE INDEX idx_trip_route          ON Trip(RouteID)"),
    ("idx_trip_driver",         "CREATE INDEX idx_trip_driver         ON Trip(DriverID)"),
    ("idx_driver_member",       "CREATE INDEX idx_driver_member       ON Driver(MemberID)"),
    ("idx_passenger_member",    "CREATE INDEX idx_passenger_member    ON Passenger(MemberID)"),
    ("idx_member_type",         "CREATE INDEX idx_member_type         ON Member(MemberType)"),
    ("idx_transaction_booking", "CREATE INDEX idx_transaction_booking ON `Transaction`(BookingID)"),
]


@app.route("/api/indexes/apply", methods=["POST"])
@admin_required
def api_apply_indexes():

    applied = []

    for conn in shards:
        cur = conn.cursor()

        for name, sql in INDEXES:
            try:
                cur.execute(sql)
                applied.append(name)
            except mysql.connector.Error:
                pass  # already exists

        conn.commit()

    audit("APPLY_INDEXES", f"count={len(set(applied))}")

    return jsonify({
        "message": f"{len(set(applied))} indexes applied",
        "indexes": list(set(applied))
    })


@app.route("/api/indexes/drop", methods=["POST"])
@admin_required
def api_drop_indexes():

    dropped = []

    for conn in shards:
        cur = conn.cursor()

        for name, _ in INDEXES:
            try:
                cur.execute(f"DROP INDEX {name} ON Booking")  # MySQL requires table
                dropped.append(name)
            except mysql.connector.Error:
                pass

        conn.commit()

    audit("DROP_INDEXES", f"count={len(set(dropped))}")

    return jsonify({
        "message": f"{len(set(dropped))} indexes dropped"
    })


@app.route("/api/indexes/status", methods=["GET"])
@login_required
def api_index_status():

    index_set = set()

    for conn in shards:
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s
              AND INDEX_NAME LIKE 'idx_%%'
        """, (DATABASE,))

        for row in cur.fetchall():
            index_set.add(row["INDEX_NAME"])

    return jsonify({"indexes": sorted(index_set)})
# ── Benchmarking ──────────────────────────────────────────────────────────────

BENCHMARK_QUERIES = {

    "bookings_by_passenger": {
        "label": "Bookings by PassengerID (WHERE clause)",
        "sql":         "SELECT * FROM Booking WHERE PassengerID = %s",
        "explain_sql": "EXPLAIN SELECT * FROM Booking WHERE PassengerID = %s",
        "param_query": "SELECT PassengerID FROM Passenger LIMIT 1",
        "type": "sharded"
    },

    "trips_by_date_status": {
        "label": "Trips filtered by Date + Status (composite index)",
        "sql":         "SELECT * FROM Trip WHERE TripDate=%s AND Status_=%s",
        "explain_sql": "EXPLAIN SELECT * FROM Trip WHERE TripDate=%s AND Status_=%s",
        "param_query": "SELECT TripDate, Status_ FROM Trip LIMIT 1",
        "type": "global"
    },

    "bookings_join_trip": {
        "label": "Bookings JOIN Trip JOIN Route (JOIN clause)",
        "sql": (
            "SELECT b.BookingID, m.Name, r.RouteName, t.TripDate, b.FareAmount "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID = p.PassengerID "
            "JOIN Member m ON p.MemberID = m.MemberID "
            "JOIN Trip t ON b.TripID = t.TripID "
            "JOIN Route r ON t.RouteID = r.RouteID "
            "WHERE b.BookingStatus = 'Confirmed'"
        ),
        "explain_sql": (
            "EXPLAIN "
            "SELECT b.BookingID, m.Name, r.RouteName, t.TripDate, b.FareAmount "
            "FROM Booking b "
            "JOIN Passenger p ON b.PassengerID = p.PassengerID "
            "JOIN Member m ON p.MemberID = m.MemberID "
            "JOIN Trip t ON b.TripID = t.TripID "
            "JOIN Route r ON t.RouteID = r.RouteID "
            "WHERE b.BookingStatus = 'Confirmed'"
        ),
        "param_query": None,
        "type": "hybrid"
    },

    "transactions_by_booking": {
        "label": "Transactions by BookingID (FK lookup)",
        "sql":         "SELECT * FROM `Transaction` WHERE BookingID = %s",
        "explain_sql": "EXPLAIN SELECT * FROM `Transaction` WHERE BookingID = %s",
        "param_query": "SELECT BookingID FROM Booking LIMIT 1",
        "type": "global"
    },

    "drivers_by_member": {
        "label": "Driver detail by MemberID (JOIN lookup)",
        "sql": (
            "SELECT d.*, m.Name "
            "FROM Driver d "
            "JOIN Member m ON d.MemberID = m.MemberID "
            "WHERE d.MemberID = %s"
        ),
        "explain_sql": (
            "EXPLAIN "
            "SELECT d.*, m.Name "
            "FROM Driver d "
            "JOIN Member m ON d.MemberID = m.MemberID "
            "WHERE d.MemberID = %s"
        ),
        "param_query": "SELECT MemberID FROM Driver LIMIT 1",
        "type": "sharded"
    },
}

def _resolve_params(conn, key):
    pq = BENCHMARK_QUERIES[key].get("param_query")

    if pq is None:
        return ()

    cur = conn.cursor()
    cur.execute(pq)
    row = cur.fetchone()

    if row is None:
        return ()

    return tuple(row)


def _run_benchmark_single(conn, key, runs=200):

    q = BENCHMARK_QUERIES[key]

    # =========================
    # PARAM RESOLUTION
    # =========================
    params = _resolve_params(conn, key)

    times = []

    cur = conn.cursor()

    # =========================
    # RUN QUERY MULTIPLE TIMES
    # =========================
    for _ in range(runs):
        t0 = time.perf_counter()

        cur.execute(q["sql"], params)
        cur.fetchall()

        times.append((time.perf_counter() - t0) * 1000)

    # =========================
    # EXPLAIN PLAN (MySQL)
    # =========================
    cur = conn.cursor(dictionary=True)
    cur.execute(q["explain_sql"], params)
    plan_rows = cur.fetchall()

    plan_text = " ".join(str(r) for r in plan_rows).upper()

    # =========================
    # SCAN TYPE DETECTION (MySQL)
    # =========================
    if "INDEX" in plan_text or "REF" in plan_text or "CONST" in plan_text:
        scan_type = "INDEX SEEK"
    elif "ALL" in plan_text:
        scan_type = "FULL TABLE SCAN"
    else:
        scan_type = "COVERING/OTHER"

    return {
        "label": q["label"],
        "avg_ms": round(sum(times) / len(times), 4),
        "min_ms": round(min(times), 4),
        "max_ms": round(max(times), 4),
        "runs": runs,
        "scan_type": scan_type,
        "plan": plan_rows,
        "params_used": list(params),
    }
@app.route("/api/benchmark/run", methods=["POST"])
@admin_required
def api_benchmark_run():

    # =========================
    # CHECK INDEXES (ALL SHARDS)
    # =========================
    index_set = set()

    for conn in shards:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s
              AND INDEX_NAME LIKE 'idx_%%'
        """, (DATABASE,))

        for row in cur.fetchall():
            index_set.add(row["INDEX_NAME"])

    # =========================
    # RUN BENCHMARKS
    # =========================
    results = {}

    for key, q in BENCHMARK_QUERIES.items():

        # -------------------------
        # ROUTE BASED ON TYPE
        # -------------------------
        if q.get("type") == "global":
            conn = get_db()

        elif q.get("type") == "sharded":
            conn = shards[0]  # use one shard (or random)

        elif q.get("type") == "hybrid":
            conn = shards[0]  # simplified execution

        else:
            conn = get_db()

        results[key] = _run_benchmark_single(conn, key)

    audit("BENCHMARK_RUN", f"indexes_active={bool(index_set)}")

    return jsonify({
        "indexes_active": bool(index_set),
        "active_indexes": sorted(index_set),
        "results": results,
    })


@app.route("/api/logs", methods=["GET"])
@admin_required
def api_logs():

    lines = []

    if os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG) as f:
            lines = f.readlines()[-200:]

    audit("READ_LOGS")

    return jsonify({
        "logs": [l.strip() for l in lines]
    })

@app.route("/api/bookings/range", methods=["GET"])
@login_required
def api_bookings_range():
 
    start_date = request.args.get("start_date", "").strip()
    end_date   = request.args.get("end_date",   "").strip()
    status     = request.args.get("status",      "").strip()
 
    # ── Validate required params ──────────────────────────────────────────────
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required (YYYY-MM-DD)"}), 400
 
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400
 
    if start_date > end_date:
        return jsonify({"error": "start_date must be <= end_date"}), 400
 
    role = session.get("role")
    mid  = session.get("member_id")
 
    # ── Base query (Booking lives in shards; Trip/Route are global) ───────────
    base_sql = """
        SELECT b.BookingID, b.PassengerID, b.TripID, b.SeatNumber,
               b.BookingTime, b.BookingStatus, b.FareAmount, b.QRCode,
               p.MemberID,
               m.Name AS PassengerName,
               t.TripDate, r.RouteName, r.Source, r.Destination
        FROM Booking b
        JOIN Passenger p ON b.PassengerID = p.PassengerID
        JOIN Member    m ON p.MemberID    = m.MemberID
        JOIN Trip      t ON b.TripID      = t.TripID
        JOIN Route     r ON t.RouteID     = r.RouteID
        WHERE t.TripDate BETWEEN %s AND %s
    """
 
    params = [start_date, end_date]
 
    if status:
        base_sql += " AND b.BookingStatus = %s"
        params.append(status)
 
    # Non-admin users can only see their own bookings
    if role != "admin":
        base_sql += " AND p.MemberID = %s"
        params.append(mid)
 
    # ── Fan-out: query every shard, collect rows ───────────────────────────────
    merged   = []
    shard_counts = {}
 
    for idx, conn in enumerate(shards):
        cur = conn.cursor(dictionary=True)
 
        try:
            cur.execute(base_sql, tuple(params))
            rows = cur.fetchall()
        except Exception as e:
            # Shard unavailable – log and continue (partition-tolerance)
            app.logger.error(f"Shard {idx} unavailable during range query: {e}")
            shard_counts[f"shard_{idx}"] = {"error": str(e), "rows": 0}
            continue
 
        shard_counts[f"shard_{idx}"] = {"rows": len(rows), "port": SHARD_PORTS[idx]}
        merged.extend(rows)
 
    # ── Merge: sort globally by TripDate then BookingTime ─────────────────────
    merged.sort(key=lambda r: (str(r.get("TripDate", "")), str(r.get("BookingTime", ""))))
 
    # ── De-duplicate (same BookingID might appear if replicated tables overlap) ─
    seen     = set()
    deduped  = []
    for row in merged:
        if row["BookingID"] not in seen:
            seen.add(row["BookingID"])
            deduped.append(row)
 
    audit(
        "RANGE_QUERY_BOOKINGS",
        f"start={start_date} end={end_date} status={status or 'any'} "
        f"total={len(deduped)} shards={shard_counts}"
    )
 
    return jsonify({
        "query": {
            "start_date":  start_date,
            "end_date":    end_date,
            "status":      status or "any",
            "total_found": len(deduped)
        },
        "shard_breakdown": shard_counts,   # shows which shard contributed how many rows
        "results": deduped
    })
 
 
# ── Shard Info / Debug Endpoint ───────────────────────────────────────────────
#
# Shows the current data distribution across shards.
# Useful for the video demo and for verifying correct partitioning.
#
# Endpoint:  GET /api/shard/info
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/shard/info", methods=["GET"])
@admin_required
def api_shard_info():
 
    info = {}
 
    for idx, conn in enumerate(shards):
        shard_key = f"shard_{idx}"
        port      = SHARD_PORTS[idx]
 
        cur = conn.cursor()
 
        counts = {}
 
        # Tables that are sharded (partitioned by MemberID % 3)
        for table in ("Member", "Passenger", "Driver", "Booking", "Transaction",
                      "users", "group_mappings"):
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                counts[table] = cur.fetchone()[0]
            except Exception:
                counts[table] = "N/A"
 
        # Sample MemberIDs on this shard (to verify hash distribution)
        sample_members = []
        try:
            cur.execute("SELECT MemberID FROM Member ORDER BY MemberID LIMIT 10")
            sample_members = [r[0] for r in cur.fetchall()]
        except Exception:
            pass
 
        # Verify shard key correctness:
        #   every MemberID on shard_idx should satisfy MemberID % 3 == idx
        misrouted = []
        try:
            cur.execute("SELECT MemberID FROM Member")
            for (mid,) in cur.fetchall():
                if mid % 3 != idx:
                    misrouted.append(mid)
        except Exception:
            misrouted = ["check failed"]
 
        info[shard_key] = {
            "port":            port,
            "row_counts":      counts,
            "sample_memberids": sample_members,
            "misrouted_members": misrouted,       # should always be []
            "routing_formula": f"MemberID % 3 == {idx}"
        }
 
    audit("READ_SHARD_INFO")
 
    return jsonify({
        "sharding_strategy": "hash-based  (shard_id = MemberID % 3)",
        "num_shards":        len(shards),
        "shards":            info
    })

if __name__ == "__main__":
    app.run(debug=True, port=5050)