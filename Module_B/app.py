"""
ShuttleGo – Flask Backend
SubTask 3 : RBAC (admin / user roles, group-based access)
SubTask 4 : SQL Indexing
SubTask 5 : Performance Benchmarking
"""

import re
import sqlite3, os, time, logging, uuid
from datetime import datetime, timezone, timedelta, date
from functools import wraps

import jwt, bcrypt as _bcrypt
from flask import Flask, request, session, jsonify, redirect, url_for, render_template, g
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "shuttlego_secret_key_2024"

JWT_SECRET    = os.environ.get("JWT_SECRET", "shuttlego_jwt_secret_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_H  = 8

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "shuttlego.db")
AUDIT_LOG = os.path.join(BASE_DIR, "logs", "audit.log")
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

logging.basicConfig(filename=AUDIT_LOG, level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

def audit(action, detail="", status="OK"):
    logging.info(f"USER={session.get('username','ANONYMOUS')} ROLE={session.get('role','none')} "
                 f"IP={request.remote_addr} VIA=API ACTION={action} STATUS={status} DETAIL={detail}")

def _issue_jwt(user_id, username, role):
    now = datetime.now(tz=timezone.utc)
    return jwt.encode({"sub": user_id, "username": username, "role": role,
                       "iat": now, "exp": now + timedelta(hours=JWT_EXPIRY_H)},
                      JWT_SECRET, algorithm=JWT_ALGORITHM)

def _decode_jwt(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

def _verify_password(plain, stored_hash):
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        return _bcrypt.checkpw(plain.encode(), stored_hash.encode())
    return check_password_hash(stored_hash, plain)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db: db.close()

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
                return render_template("error.html", message="Admin access required"), 403
        return f(*a, **kw)
    return w

def _ctx():
    return {"username": session.get("username",""), "role": session.get("role",""), "group": session.get("group","")}

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login_page"))

@app.route("/login")
def login_page(): return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard(): return render_template("dashboard.html", **_ctx())

@app.route("/members")
@login_required
def members_page(): return render_template("members.html", **_ctx())

@app.route("/trips")
@login_required
def trips_page(): return render_template("trips.html", **_ctx())

@app.route("/bookings")
@login_required
def bookings_page(): return render_template("bookings.html", **_ctx())

@app.route("/schedule")
@login_required
def schedule_page(): return render_template("schedule.html", **_ctx())

@app.route("/admin")
@admin_required
def admin_page(): return render_template("admin.html", **_ctx())

@app.route("/benchmark")
@admin_required
def benchmark_page(): return render_template("benchmark.html", **_ctx())

@app.route("/logs")
@admin_required
def logs_page(): return render_template("logs.html", **_ctx())

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = (data or {}).get("username","").strip()
    password = (data or {}).get("password","")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    db = get_db()
    user = db.execute(
        "SELECT u.UserID, u.username, u.password_hash, u.role, u.MemberID, gm.group_name "
        "FROM users u LEFT JOIN group_mappings gm ON u.UserID=gm.UserID WHERE u.username=?",
        (username,)).fetchone()
    if not user or not _verify_password(password, user["password_hash"]):
        audit("LOGIN_FAILED", f"username={username}", "FAIL")
        return jsonify({"error": "Invalid credentials"}), 401
    session.clear()
    session.update({"user_id": user["UserID"], "username": user["username"],
                    "role": user["role"], "member_id": user["MemberID"], "group": user["group_name"]})
    token = _issue_jwt(user["UserID"], user["username"], user["role"])
    audit("LOGIN", f"username={username} role={user['role']}")
    return jsonify({"message": "Login successful", "session_token": token,
                    "role": user["role"], "username": user["username"], "group": user["group_name"]})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    audit("LOGOUT"); session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    first    = data.get("first_name", "").strip()
    last     = data.get("last_name", "").strip()
    role_req = data.get("role_request", "passenger")  # "passenger" or "driver"

    # ── Basic validation ──────────────────────────────────────────────────────
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

    db = get_db()

    # ── Duplicate checks ──────────────────────────────────────────────────────
    if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return jsonify({"error": "Username is already taken — please choose another"}), 409

    if db.execute("SELECT 1 FROM Member WHERE Email = ?", (email,)).fetchone():
        return jsonify({"error": "An account with this email already exists"}), 409

    # ── Create Member row ─────────────────────────────────────────────────────
    member_type = "Passenger" if role_req == "passenger" else "Driver"
    max_mid     = db.execute("SELECT MAX(MemberID) FROM Member").fetchone()[0] or 0
    new_mid     = max_mid + 1

    db.execute(
        "INSERT INTO Member (MemberID, Name, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_mid, f"{first} {last}", 0, "Other", email, "", member_type, str(date.today()))
    )

    # ── Create sub-profile (Passenger or Driver stub) ─────────────────────────
    if member_type == "Passenger":
        max_pid = db.execute("SELECT MAX(PassengerID) FROM Passenger").fetchone()[0] or 0
        db.execute(
            "INSERT INTO Passenger (PassengerID, MemberID, EmergencyContact, PreferredPaymentMethod, "
            "SpecialAssistance, NotificationPreference, Status_) VALUES (?,?,?,?,?,?,?)",
            (max_pid + 1, new_mid, None, "UPI", None, "App", "Active")
        )
        group = "passenger_group"
    else:
        max_did = db.execute("SELECT MAX(DriverID) FROM Driver").fetchone()[0] or 0
        fake_license = f"DL{new_mid:06d}"
        db.execute(
            "INSERT INTO Driver (DriverID, MemberID, LicenseNumber, LicenseExpiryDate, "
            "ExperienceYears, Rating, Status_) VALUES (?,?,?,?,?,?,?)",
            (max_did + 1, new_mid, fake_license, "2030-01-01", 0, 0.0, "Off-Duty")
        )
        group = "driver_group"

    # ── Create users row ──────────────────────────────────────────────────────
    max_uid = db.execute("SELECT MAX(UserID) FROM users").fetchone()[0] or 0
    new_uid = max_uid + 1
    pw_hash = generate_password_hash(password)

    db.execute(
        "INSERT INTO users (UserID, username, password_hash, role, MemberID) VALUES (?,?,?,?,?)",
        (new_uid, username, pw_hash, "user", new_mid)
    )

    # ── Create group mapping ──────────────────────────────────────────────────
    max_gid = db.execute("SELECT MAX(MappingID) FROM group_mappings").fetchone()[0] or 0
    db.execute(
        "INSERT INTO group_mappings (MappingID, UserID, group_name) VALUES (?,?,?)",
        (max_gid + 1, new_uid, group)
    )

    db.commit()
    audit("REGISTER", f"username={username} role={group} member_id={new_mid}")

    return jsonify({
        "message": "Account created successfully",
        "username": username,
        "role": "user",
        "group": group
    }), 201

@app.route("/api/me")
@login_required
def api_me():
    db = get_db()
    gm = db.execute("SELECT group_name FROM group_mappings WHERE UserID=?", (session["user_id"],)).fetchone()
    return jsonify({"user_id": session["user_id"], "username": session["username"],
                    "role": session["role"], "member_id": session.get("member_id"),
                    "group": gm["group_name"] if gm else None})

@app.route("/isAuth", methods=["GET"])
def is_auth():
    token = request.headers.get("Authorization","")[7:].strip() or request.args.get("token","")
    if not token: return jsonify({"error": "No session found"}), 401
    try:
        payload = _decode_jwt(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401
    except jwt.PyJWTError:
        return jsonify({"error": "Invalid session token"}), 401
    return jsonify({"message": "User is authenticated", "username": payload["username"],
                    "role": payload["role"],
                    "expiry": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat()})

@app.route("/api/me/password", methods=["PUT"])
@login_required
def api_change_password():
    data = request.get_json() or {}
    cur, new_, con = data.get("current_password",""), data.get("new_password",""), data.get("confirm_password","")
    if not cur or not new_: return jsonify({"error": "Current and new password are required"}), 400
    if new_ != con: return jsonify({"error": "New passwords do not match"}), 400
    if len(new_) < 6: return jsonify({"error": "New password must be at least 6 characters"}), 400
    if new_ == cur: return jsonify({"error": "New password must differ from current password"}), 400
    db = get_db()
    user = db.execute("SELECT password_hash FROM users WHERE UserID=?", (session["user_id"],)).fetchone()
    if not _verify_password(cur, user["password_hash"]):
        audit("PASSWORD_CHANGE_FAILED", "incorrect current password", "FAIL")
        return jsonify({"error": "Current password is incorrect"}), 401
    db.execute("UPDATE users SET password_hash=? WHERE UserID=?",
               (generate_password_hash(new_), session["user_id"]))
    db.commit()
    audit("PASSWORD_CHANGED", f"user_id={session['user_id']}")
    return jsonify({"message": "Password changed successfully"})

# ── Members ───────────────────────────────────────────────────────────────────
@app.route("/api/members", methods=["GET"])
@login_required
def api_members():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    q = ("SELECT m.*, CASE WHEN m.MemberType='Driver' THEN d.Status_ ELSE p.Status_ END AS Status_, "
         "d.Rating, d.ExperienceYears, d.LicenseNumber FROM Member m "
         "LEFT JOIN Driver d ON m.MemberID=d.MemberID LEFT JOIN Passenger p ON m.MemberID=p.MemberID")
    rows = db.execute(q + " ORDER BY m.MemberID").fetchall() if role == "admin" else \
           db.execute(q + " WHERE m.MemberID=?", (mid,)).fetchall()
    audit("READ_MEMBERS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/members/<int:mid>", methods=["GET"])
@login_required
def api_member_detail(mid):
    db = get_db(); role = session.get("role"); my_mid = session.get("member_id")
    if role != "admin" and my_mid != mid:
        audit("READ_MEMBER_DENIED", f"target_member={mid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403
    row = db.execute(
        "SELECT m.*, d.DriverID, d.LicenseNumber, d.LicenseExpiryDate, d.ExperienceYears, "
        "d.Rating, d.Status_ AS DriverStatus, p.PassengerID, p.EmergencyContact, "
        "p.PreferredPaymentMethod, p.SpecialAssistance, p.NotificationPreference, p.Status_ AS PassengerStatus "
        "FROM Member m LEFT JOIN Driver d ON m.MemberID=d.MemberID "
        "LEFT JOIN Passenger p ON m.MemberID=p.MemberID WHERE m.MemberID=?", (mid,)).fetchone()
    if not row: return jsonify({"error": "Member not found"}), 404
    audit("READ_MEMBER_DETAIL", f"member_id={mid}")
    return jsonify(dict(row))

@app.route("/api/members/<int:mid>", methods=["PUT"])
@login_required
def api_update_member(mid):
    role = session.get("role"); my_mid = session.get("member_id")
    if role != "admin" and my_mid != mid:
        audit("UPDATE_MEMBER_DENIED", f"target={mid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403
    data = request.get_json() or {}; db = get_db()
    allowed = ["Name","Age","Gender","Email","ContactNumber","MemberType","Image"] if role=="admin" else ["ContactNumber","Image"]
    updates = {k:v for k,v in data.items() if k in allowed}
    if not updates: return jsonify({"error": "No valid fields to update"}), 400
    db.execute(f"UPDATE Member SET {', '.join(f'{k}=?' for k in updates)} WHERE MemberID=?",
               list(updates.values())+[mid]); db.commit()
    audit("UPDATE_MEMBER", f"member_id={mid} fields={list(updates.keys())}")
    return jsonify({"message": "Member updated", "updated": updates})

@app.route("/api/members", methods=["POST"])
@admin_required
def api_create_member():
    data = request.get_json() or {}; db = get_db()
    required = ["MemberID","Name","Age","Gender","Email","ContactNumber","MemberType","RegistrationDate"]
    missing = [f for f in required if f not in data]
    if missing: return jsonify({"error": f"Missing fields: {missing}"}), 400
    try:
        db.execute("INSERT INTO Member (MemberID,Name,Image,Age,Gender,Email,ContactNumber,MemberType,RegistrationDate) VALUES (?,?,?,?,?,?,?,?,?)",
                   (data["MemberID"],data["Name"],data.get("Image",""),data["Age"],data["Gender"],
                    data["Email"],data["ContactNumber"],data["MemberType"],data["RegistrationDate"]))
        db.commit()
    except sqlite3.IntegrityError as e: return jsonify({"error": str(e)}), 409
    audit("CREATE_MEMBER", f"member_id={data['MemberID']}")
    return jsonify({"message": "Member created", "MemberID": data["MemberID"]}), 201

@app.route("/api/members/<int:mid>", methods=["DELETE"])
@admin_required
def api_delete_member(mid):
    db = get_db(); row = db.execute("SELECT Name FROM Member WHERE MemberID=?", (mid,)).fetchone()
    if not row: return jsonify({"error": "Member not found"}), 404
    db.execute("DELETE FROM Member WHERE MemberID=?", (mid,)); db.commit()
    audit("DELETE_MEMBER", f"member_id={mid}")
    return jsonify({"message": f"Member {mid} deleted"})

# ── Trips ─────────────────────────────────────────────────────────────────────
@app.route("/api/trips", methods=["GET"])
@login_required
def api_trips():
    db = get_db(); status = request.args.get("status"); date = request.args.get("date")
    q = ("SELECT t.*, r.RouteName, r.Source, r.Destination, v.VehicleNumber, v.Model, m.Name AS DriverName "
         "FROM Trip t JOIN Route r ON t.RouteID=r.RouteID JOIN Vehicle v ON t.VehicleID=v.VehicleID "
         "JOIN Driver d ON t.DriverID=d.DriverID JOIN Member m ON d.MemberID=m.MemberID")
    params=[]; filters=[]
    if status: filters.append("t.Status_=?"); params.append(status)
    if date:   filters.append("t.TripDate=?"); params.append(date)
    if filters: q += " WHERE " + " AND ".join(filters)
    rows = db.execute(q + " ORDER BY t.TripDate, t.ScheduledDepartureTime", params).fetchall()
    audit("READ_TRIPS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/trips/<int:tid>", methods=["GET"])
@login_required
def api_trip_detail(tid):
    db = get_db()
    row = db.execute(
        "SELECT t.*, r.RouteName, r.Source, r.Destination, r.BaseFare, "
        "v.VehicleNumber, v.Model, v.Capacity, v.VehicleID, "
        "m.Name AS DriverName, d.Rating AS DriverRating "
        "FROM Trip t JOIN Route r ON t.RouteID=r.RouteID JOIN Vehicle v ON t.VehicleID=v.VehicleID "
        "JOIN Driver d ON t.DriverID=d.DriverID JOIN Member m ON d.MemberID=m.MemberID "
        "WHERE t.TripID=?", (tid,)).fetchone()
    if not row: return jsonify({"error": "Trip not found"}), 404
    audit("READ_TRIP_DETAIL", f"trip_id={tid}")
    return jsonify(dict(row))

# ── Bookings ──────────────────────────────────────────────────────────────────
@app.route("/api/bookings", methods=["GET"])
@login_required
def api_bookings():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    base = ("SELECT b.*, m.Name AS PassengerName, r.RouteName, t.TripDate FROM Booking b "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID JOIN Member m ON p.MemberID=m.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID JOIN Route r ON t.RouteID=r.RouteID")
    rows = db.execute(base+" ORDER BY b.BookingTime DESC").fetchall() if role=="admin" else \
           db.execute(base+" WHERE p.MemberID=? ORDER BY b.BookingTime DESC", (mid,)).fetchall()
    audit("READ_BOOKINGS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/bookings", methods=["POST"])
@login_required
def api_create_booking():
    data = request.get_json() or {}; db = get_db()
    role = session.get("role"); mid = session.get("member_id")
    passenger = db.execute("SELECT PassengerID FROM Passenger WHERE MemberID=?", (mid,)).fetchone()
    if not passenger and role != "admin": return jsonify({"error": "Only passengers can create bookings"}), 403
    missing = [f for f in ["TripID","SeatNumber"] if f not in data]
    if missing: return jsonify({"error": f"Missing fields: {missing}"}), 400
    pid = data.get("PassengerID") if role=="admin" else passenger["PassengerID"]
    tid = data["TripID"]; seat = data["SeatNumber"]
    fare_row = db.execute("SELECT r.BaseFare FROM Trip t JOIN Route r ON t.RouteID=r.RouteID WHERE t.TripID=?", (tid,)).fetchone()
    if not fare_row: return jsonify({"error": "Trip not found"}), 404
    qr = f"QR-TRIP{tid}-SEAT{seat}-PASS{pid}-{uuid.uuid4().hex[:6].upper()}"
    max_id = db.execute("SELECT MAX(BookingID) FROM Booking").fetchone()[0] or 0
    try:
        db.execute("INSERT INTO Booking (BookingID,PassengerID,TripID,SeatNumber,BookingTime,BookingStatus,FareAmount,QRCode,QRCodeURL,VerificationStatus) VALUES (?,?,?,?,datetime('now'),?,?,?,?,?)",
                   (max_id+1,pid,tid,seat,"Confirmed",fare_row["BaseFare"],qr,f"https://shuttle.qr/{max_id+1}","Pending"))
        db.execute("UPDATE Trip SET AvailableSeats=AvailableSeats-1 WHERE TripID=? AND AvailableSeats>0", (tid,))
        db.commit()
    except sqlite3.IntegrityError as e: return jsonify({"error": str(e)}), 409
    audit("CREATE_BOOKING", f"booking_id={max_id+1} trip={tid} seat={seat}")
    return jsonify({"message": "Booking created", "BookingID": max_id+1, "QRCode": qr}), 201

@app.route("/api/bookings/<int:bid>", methods=["DELETE"])
@login_required
def api_cancel_booking(bid):
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    bk = db.execute("SELECT b.*, p.MemberID FROM Booking b JOIN Passenger p ON b.PassengerID=p.PassengerID WHERE b.BookingID=?", (bid,)).fetchone()
    if not bk: return jsonify({"error": "Booking not found"}), 404
    if role != "admin" and bk["MemberID"] != mid:
        audit("CANCEL_BOOKING_DENIED", f"booking_id={bid}", "FORBIDDEN")
        return jsonify({"error": "Access denied"}), 403
    db.execute("UPDATE Booking SET BookingStatus='Cancelled' WHERE BookingID=?", (bid,))
    db.execute("UPDATE Trip SET AvailableSeats=AvailableSeats+1 WHERE TripID=?", (bk["TripID"],))
    db.commit(); audit("CANCEL_BOOKING", f"booking_id={bid}")
    return jsonify({"message": f"Booking {bid} cancelled"})

# ── Admin users ───────────────────────────────────────────────────────────────
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    db = get_db()
    rows = db.execute("SELECT u.UserID, u.username, u.role, u.MemberID, gm.group_name FROM users u LEFT JOIN group_mappings gm ON u.UserID=gm.UserID ORDER BY u.UserID").fetchall()
    audit("ADMIN_READ_USERS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/users/<int:uid>/role", methods=["PUT"])
@admin_required
def api_update_role(uid):
    data = request.get_json() or {}; new_role = data.get("role")
    if new_role not in ("admin","user"): return jsonify({"error": "Role must be 'admin' or 'user'"}), 400
    db = get_db(); db.execute("UPDATE users SET role=? WHERE UserID=?", (new_role, uid)); db.commit()
    audit("UPDATE_USER_ROLE", f"user_id={uid} new_role={new_role}")
    return jsonify({"message": f"User {uid} role updated to {new_role}"})

@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def api_delete_user(uid):
    db = get_db(); row = db.execute("SELECT username FROM users WHERE UserID=?", (uid,)).fetchone()
    if not row: return jsonify({"error": "User not found"}), 404
    db.execute("DELETE FROM users WHERE UserID=?", (uid,)); db.commit()
    audit("DELETE_USER", f"user_id={uid} username={row['username']}")
    return jsonify({"message": f"User {uid} deleted"})

# ── Driver Assignments ────────────────────────────────────────────────────────
@app.route("/api/my/assignments", methods=["GET"])
@login_required
def api_my_assignments():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    if role == "admin":
        rows = db.execute(
            "SELECT da.*, mn.Name AS DriverName, v.VehicleNumber, v.Model, "
            "r.RouteName, r.Source, r.Destination, "
            "t.TripDate, t.ScheduledDepartureTime, t.ScheduledArrivalTime, t.Status_ AS TripStatus "
            "FROM DriverAssignment da "
            "JOIN Driver d ON da.DriverID=d.DriverID JOIN Member mn ON d.MemberID=mn.MemberID "
            "JOIN Vehicle v ON da.VehicleID=v.VehicleID "
            "JOIN Trip t ON da.TripID=t.TripID JOIN Route r ON t.RouteID=r.RouteID "
            "ORDER BY da.AssignedDate DESC, da.ShiftStart").fetchall()
    else:
        driver = db.execute("SELECT DriverID FROM Driver WHERE MemberID=?", (mid,)).fetchone()
        if not driver:
            audit("READ_MY_ASSIGNMENTS_DENIED", "not a driver", "FORBIDDEN")
            return jsonify({"error": "No driver profile found for this account"}), 403
        rows = db.execute(
            "SELECT da.*, v.VehicleNumber, v.Model, v.Capacity, "
            "r.RouteName, r.Source, r.Destination, "
            "t.TripDate, t.ScheduledDepartureTime, t.ScheduledArrivalTime, t.Status_ AS TripStatus "
            "FROM DriverAssignment da "
            "JOIN Vehicle v ON da.VehicleID=v.VehicleID "
            "JOIN Trip t ON da.TripID=t.TripID JOIN Route r ON t.RouteID=r.RouteID "
            "WHERE da.DriverID=? ORDER BY da.AssignedDate DESC, da.ShiftStart",
            (driver["DriverID"],)).fetchall()
    audit("READ_MY_ASSIGNMENTS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

# ── Vehicle Maintenance ───────────────────────────────────────────────────────
@app.route("/api/my/maintenance", methods=["GET"])
@login_required
def api_my_maintenance():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    if role == "admin":
        rows = db.execute(
            "SELECT vm.*, v.VehicleNumber, v.Model FROM VehicleMaintenance vm "
            "JOIN Vehicle v ON vm.VehicleID=v.VehicleID ORDER BY vm.ServiceDate DESC").fetchall()
        return jsonify([dict(r) for r in rows])
    driver = db.execute("SELECT DriverID FROM Driver WHERE MemberID=?", (mid,)).fetchone()
    if not driver:
        audit("READ_MY_MAINTENANCE_DENIED", "not a driver", "FORBIDDEN")
        return jsonify({"error": "No driver profile found for this account"}), 403
    rows = db.execute(
        "SELECT vm.MaintenanceID, vm.VehicleID, vm.ServiceDate, vm.ServiceType, "
        "vm.NextServiceDue, vm.Status_, v.VehicleNumber, v.Model "
        "FROM VehicleMaintenance vm JOIN Vehicle v ON vm.VehicleID=v.VehicleID "
        "WHERE vm.VehicleID IN (SELECT DISTINCT VehicleID FROM DriverAssignment WHERE DriverID=?) "
        "ORDER BY vm.ServiceDate DESC", (driver["DriverID"],)).fetchall()
    audit("READ_MY_MAINTENANCE", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

# ── NoShow Penalties ──────────────────────────────────────────────────────────
@app.route("/api/my/penalties", methods=["GET"])
@login_required
def api_my_penalties():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    if role == "admin":
        rows = db.execute(
            "SELECT nsp.*, b.BookingID, mn.Name AS PassengerName, r.RouteName, t.TripDate "
            "FROM NoShowPenalty nsp JOIN Booking b ON nsp.BookingID=b.BookingID "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID JOIN Member mn ON p.MemberID=mn.MemberID "
            "JOIN Trip t ON b.TripID=t.TripID JOIN Route r ON t.RouteID=r.RouteID "
            "ORDER BY nsp.DetectionTime DESC").fetchall()
    else:
        passenger = db.execute("SELECT PassengerID FROM Passenger WHERE MemberID=?", (mid,)).fetchone()
        if not passenger: return jsonify([])
        rows = db.execute(
            "SELECT nsp.*, r.RouteName, t.TripDate "
            "FROM NoShowPenalty nsp JOIN Booking b ON nsp.BookingID=b.BookingID "
            "JOIN Trip t ON b.TripID=t.TripID JOIN Route r ON t.RouteID=r.RouteID "
            "WHERE b.PassengerID=? ORDER BY nsp.DetectionTime DESC",
            (passenger["PassengerID"],)).fetchall()
    audit("READ_MY_PENALTIES", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

# ── Vehicle Live Location ─────────────────────────────────────────────────────
@app.route("/api/vehicles/locations", methods=["GET"])
@login_required
def api_vehicle_locations():
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    latest = "SELECT MAX(LocationID) AS lid FROM VehicleLiveLocation GROUP BY VehicleID"
    if role == "admin":
        rows = db.execute(
            f"SELECT vll.*, v.VehicleNumber, v.Model, v.CurrentStatus "
            f"FROM VehicleLiveLocation vll JOIN Vehicle v ON vll.VehicleID=v.VehicleID "
            f"WHERE vll.LocationID IN ({latest}) ORDER BY vll.Timestamp DESC").fetchall()
    else:
        rows = db.execute(
            f"SELECT vll.*, v.VehicleNumber, v.Model "
            f"FROM VehicleLiveLocation vll JOIN Vehicle v ON vll.VehicleID=v.VehicleID "
            f"WHERE vll.LocationID IN ({latest}) "
            f"AND vll.VehicleID IN ("
            f"  SELECT t.VehicleID FROM Trip t "
            f"  JOIN Booking b ON t.TripID=b.TripID "
            f"  JOIN Passenger p ON b.PassengerID=p.PassengerID "
            f"  WHERE p.MemberID=? AND b.BookingStatus='Confirmed' "
            f"  AND t.Status_ IN ('Scheduled','InProgress')) "
            f"ORDER BY vll.Timestamp DESC", (mid,)).fetchall()
    audit("READ_VEHICLE_LOCATIONS", f"count={len(rows)}")
    return jsonify([dict(r) for r in rows])

@app.route("/api/vehicles/<int:vid>/location", methods=["GET"])
@login_required
def api_vehicle_location(vid):
    db = get_db(); role = session.get("role"); mid = session.get("member_id")
    if role != "admin":
        allowed = db.execute(
            "SELECT COUNT(*) FROM Trip t JOIN Booking b ON t.TripID=b.TripID "
            "JOIN Passenger p ON b.PassengerID=p.PassengerID "
            "WHERE t.VehicleID=? AND p.MemberID=? AND b.BookingStatus='Confirmed' "
            "AND t.Status_ IN ('Scheduled','InProgress')", (vid, mid)).fetchone()[0]
        if not allowed:
            driver = db.execute("SELECT DriverID FROM Driver WHERE MemberID=?", (mid,)).fetchone()
            if driver:
                allowed = db.execute(
                    "SELECT COUNT(*) FROM DriverAssignment "
                    "WHERE VehicleID=? AND DriverID=? AND Status_='Assigned'",
                    (vid, driver["DriverID"])).fetchone()[0]
        if not allowed:
            audit("READ_VEHICLE_LOCATION_DENIED", f"vehicle_id={vid}", "FORBIDDEN")
            return jsonify({"error": "Access denied to this vehicle's location"}), 403
    row = db.execute(
        "SELECT vll.*, v.VehicleNumber, v.Model FROM VehicleLiveLocation vll "
        "JOIN Vehicle v ON vll.VehicleID=v.VehicleID "
        "WHERE vll.VehicleID=? ORDER BY vll.Timestamp DESC LIMIT 1", (vid,)).fetchone()
    if not row: return jsonify({"error": "No location data available for this vehicle"}), 404
    audit("READ_VEHICLE_LOCATION", f"vehicle_id={vid}")
    return jsonify(dict(row))

# ── Indexing ──────────────────────────────────────────────────────────────────
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
    for _, sql in INDEXES: db.execute(sql)
    db.commit(); audit("APPLY_INDEXES", f"count={len(INDEXES)}")
    return jsonify({"message": f"{len(INDEXES)} indexes applied", "indexes": [i[0] for i in INDEXES]})

@app.route("/api/indexes/drop", methods=["POST"])
@admin_required
def api_drop_indexes():
    db = get_db()
    for name, _ in INDEXES: db.execute(f"DROP INDEX IF EXISTS {name}")
    db.commit(); audit("DROP_INDEXES", f"count={len(INDEXES)}")
    return jsonify({"message": f"{len(INDEXES)} indexes dropped"})

@app.route("/api/indexes/status", methods=["GET"])
@login_required
def api_index_status():
    db = get_db()
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'").fetchall()
    return jsonify({"indexes": [r["name"] for r in rows]})

# ── Benchmarking ──────────────────────────────────────────────────────────────
BENCHMARK_QUERIES = {
    "bookings_by_passenger": {
        "label": "Bookings by PassengerID (WHERE clause)",
        "sql":         "SELECT * FROM Booking WHERE PassengerID = ?",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM Booking WHERE PassengerID = ?",
        "param_query": "SELECT PassengerID FROM Passenger LIMIT 1",
    },
    "trips_by_date_status": {
        "label": "Trips filtered by Date + Status (composite index)",
        "sql":         "SELECT * FROM Trip WHERE TripDate=? AND Status_=?",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM Trip WHERE TripDate=? AND Status_=?",
        "param_query": "SELECT TripDate, Status_ FROM Trip LIMIT 1",
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
        ),
        "param_query": None,
    },
    "transactions_by_booking": {
        "label": "Transactions by BookingID (FK lookup)",
        "sql":         "SELECT * FROM [Transaction] WHERE BookingID=?",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT * FROM [Transaction] WHERE BookingID=?",
        "param_query": "SELECT BookingID FROM Booking LIMIT 1",
    },
    "drivers_by_member": {
        "label": "Driver detail by MemberID (JOIN lookup)",
        "sql":         "SELECT d.*, m.Name FROM Driver d JOIN Member m ON d.MemberID=m.MemberID WHERE d.MemberID=?",
        "explain_sql": "EXPLAIN QUERY PLAN SELECT d.*, m.Name FROM Driver d JOIN Member m ON d.MemberID=m.MemberID WHERE d.MemberID=?",
        "param_query": "SELECT MemberID FROM Driver LIMIT 1",
    },
}

def _resolve_params(db, key):
    pq = BENCHMARK_QUERIES[key].get("param_query")
    if pq is None:
        return ()
    row = db.execute(pq).fetchone()
    if row is None:
        return ()
    return tuple(row)

def _run_benchmark_single(db, key, runs=200):
    q      = BENCHMARK_QUERIES[key]
    params = _resolve_params(db, key)
    times  = []
    for _ in range(runs):
        t0 = time.perf_counter()
        db.execute(q["sql"], params).fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    plan_rows = db.execute(q["explain_sql"], params).fetchall()
    plan      = [dict(r) for r in plan_rows]
    plan_text = " ".join(str(r) for r in plan)
    scan_type = ("INDEX SEEK"     if ("USING INDEX" in plan_text or "SEARCH" in plan_text)
                 else "FULL TABLE SCAN" if "SCAN" in plan_text
                 else "COVERING/OTHER")
    return {
        "label":     q["label"],
        "avg_ms":    round(sum(times) / len(times), 4),
        "min_ms":    round(min(times), 4),
        "max_ms":    round(max(times), 4),
        "runs":      runs,
        "scan_type": scan_type,
        "plan":      plan,
        "params_used": list(params),
    }

@app.route("/api/benchmark/run", methods=["POST"])
@admin_required
def api_benchmark_run():
    db       = get_db()
    idx_rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()
    results = {key: _run_benchmark_single(db, key) for key in BENCHMARK_QUERIES}
    audit("BENCHMARK_RUN", f"indexes_active={bool(idx_rows)}")
    return jsonify({
        "indexes_active": bool(idx_rows),
        "active_indexes": [r["name"] for r in idx_rows],
        "results":        results,
    })

@app.route("/api/logs", methods=["GET"])
@admin_required
def api_logs():
    lines = []
    if os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG) as f: lines = f.readlines()[-200:]
    audit("READ_LOGS")
    return jsonify({"logs": [l.strip() for l in lines]})

if __name__ == "__main__":
    app.run(debug=True, port=5050)
