@app.route("/api/register", methods=["POST"])
def api_register():
    data     = request.get_json() or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    first    = data.get("first_name", "").strip()
    last     = data.get("last_name", "").strip()
    role_req = data.get("role_request", "passenger")

    # ── Validation ─────────────────────────────────────────
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

    # ── Helper: check across all shards ────────────────────
    def exists_in_any_shard(query, params):
        for conn in shards:
            cur = conn.cursor()
            cur.execute(query, params)
            if cur.fetchone():
                return True
        return False

    # ── Duplicate checks (GLOBAL) ─────────────────────────
    if exists_in_any_shard("SELECT 1 FROM users WHERE username=%s", (username,)):
        return jsonify({"error": "Username already taken"}), 409

    if exists_in_any_shard("SELECT 1 FROM Member WHERE Email=%s", (email,)):
        return jsonify({"error": "Email already exists"}), 409

    # ── Generate IDs safely ───────────────────────────────
    import random
    from datetime import date
    from werkzeug.security import generate_password_hash

    new_mid = random.randint(100000, 999999)
    shard_id = new_mid % 3

    conn = shards[shard_id]
    cur  = conn.cursor()

    member_type = "Passenger" if role_req == "passenger" else "Driver"

    # ── Insert Member ─────────────────────────────────────
    cur.execute("""
        INSERT INTO Member
        (MemberID, Name, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

    # ── Sub-profile ───────────────────────────────────────
    if member_type == "Passenger":
        cur.execute("SELECT MAX(PassengerID) FROM Passenger")
        max_pid = cur.fetchone()[0] or 0

        cur.execute("""
            INSERT INTO Passenger
            (PassengerID, MemberID, EmergencyContact, PreferredPaymentMethod,
             SpecialAssistance, NotificationPreference, Status_)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            max_pid + 1,
            new_mid,
            None,
            "UPI",
            None,
            "App",
            "Active"
        ))

        group = "passenger_group"

    else:
        cur.execute("SELECT MAX(DriverID) FROM Driver")
        max_did = cur.fetchone()[0] or 0

        fake_license = f"DL{new_mid:06d}"

        cur.execute("""
            INSERT INTO Driver
            (DriverID, MemberID, LicenseNumber, LicenseExpiryDate,
             ExperienceYears, Rating, Status_)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            max_did + 1,
            new_mid,
            fake_license,
            "2030-01-01",
            0,
            0.0,
            "Off-Duty"
        ))

        group = "driver_group"

    # ── Users table ───────────────────────────────────────
    cur.execute("SELECT MAX(UserID) FROM users")
    max_uid = cur.fetchone()[0] or 0
    new_uid = max_uid + 1

    pw_hash = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users (UserID, username, password_hash, role, MemberID)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        new_uid,
        username,
        pw_hash,
        "user",
        new_mid
    ))

    # ── Group mapping ─────────────────────────────────────
    cur.execute("SELECT MAX(MappingID) FROM group_mappings")
    max_gid = cur.fetchone()[0] or 0

    cur.execute("""
        INSERT INTO group_mappings (MappingID, UserID, group_name)
        VALUES (%s, %s, %s)
    """, (
        max_gid + 1,
        new_uid,
        group
    ))

    conn.commit()

    audit("REGISTER", f"username={username} role={group} member_id={new_mid}")

    return jsonify({
        "message": "Account created successfully",
        "username": username,
        "role": "user",
        "group": group,
        "shard": shard_id
    }), 201