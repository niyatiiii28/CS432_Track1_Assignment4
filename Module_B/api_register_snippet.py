# ── Add this route to app.py, right after the /api/logout route ──────────────
#
#   @app.route("/api/logout", methods=["POST"])
#   def api_logout(): ...
#
#   <-- paste here -->
#
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    first    = data.get("first_name", "").strip()
    last     = data.get("last_name", "").strip()
    role_req = data.get("role_request", "passenger")   # "passenger" or "driver"

    # ── Basic validation ──────────────────────────────────────────────────────
    if not username or not email or not password or not first or not last:
        return jsonify({"error": "All fields are required"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    import re
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
    from datetime import date
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
        import uuid as _uuid
        max_did = db.execute("SELECT MAX(DriverID) FROM Driver").fetchone()[0] or 0
        fake_license = f"DL{new_mid:06d}"
        db.execute(
            "INSERT INTO Driver (DriverID, MemberID, LicenseNumber, LicenseExpiryDate, "
            "ExperienceYears, Rating, Status_) VALUES (?,?,?,?,?,?,?)",
            (max_did + 1, new_mid, fake_license, "2030-01-01", 0, 0.0, "Off-Duty")
        )
        group = "driver_group"

    # ── Create users row ──────────────────────────────────────────────────────
    max_uid  = db.execute("SELECT MAX(UserID) FROM users").fetchone()[0] or 0
    new_uid  = max_uid + 1
    pw_hash  = generate_password_hash(password)

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
