# ShuttleGo – Module B Implementation

## Project Structure

```
shuttlego/
├── app.py              ← Main Flask application (SubTasks 3, 4, 5)
├── shuttlego.db        ← SQLite database (from SubTask 1)
├── logs/
│   └── audit.log       ← Security audit log (auto-generated)
└── templates/
    ├── base.html       ← Shared layout with sidebar + RBAC-aware nav
    ├── login.html      ← Login page
    ├── dashboard.html  ← Home dashboard
    ├── members.html    ← Member portfolio (RBAC-restricted)
    ├── trips.html      ← Trip browser
    ├── bookings.html   ← Booking management
    ├── admin.html      ← Admin panel (admin only)
    ├── benchmark.html  ← SQL performance benchmark (SubTask 5)
    ├── logs.html       ← Audit log viewer (admin only)
    └── error.html      ← 403/error page
```

---

## How to Run

```bash
pip install flask
python app.py
# Open http://localhost:5050
```

**Demo Credentials:**
| Username | Password  | Role  | Group            |
|----------|-----------|-------|------------------|
| admin    | admin123  | admin | admin_group      |
| rajesh_1 | user123   | user  | passenger_group  |
| suresh_3 | user123   | user  | driver_group     |       
user names are generated new everytime, so first register as admin > go to contol panel tab > check the list of all members > pick one as user login.
---

## SubTask 3 – RBAC Implementation

### Roles & Permissions

| Action                          | Admin | Regular User         |
|---------------------------------|-------|----------------------|
| View all member profiles        | ✅    | ❌ (own only)        |
| View full contact details       | ✅    | ❌ (redacted)        |
| Create members                  | ✅    | ❌                   |
| Delete members                  | ✅    | ❌                   |
| Update any member               | ✅    | ❌ (own fields only) |
| View all bookings               | ✅    | ❌ (own only)        |
| Cancel any booking              | ✅    | ❌ (own only)        |
| Manage users & roles            | ✅    | ❌                   |
| Apply/drop SQL indexes          | ✅    | ❌                   |
| Run benchmarks                  | ✅    | ✅ (read-only)       |
| View audit logs                 | ✅    | ❌                   |

### RBAC Groups (group_mappings table)
- **admin_group** – Full access, administrative actions
- **driver_group** – Driver members, read own profile + trip assignments
- **passenger_group** – Passenger members, own bookings only

### Decorators Used
```python
@login_required   # Any authenticated user
@admin_required   # Admin role only (role = 'admin')
```

### Security Logging (audit.log)
Every API call is logged with:
```
TIMESTAMP | LEVEL | USER=<username> ROLE=<role> IP=<ip> VIA=API ACTION=<action> STATUS=<OK|FAIL|FORBIDDEN> DETAIL=<detail>
```

**Logged events include:**
- `LOGIN` / `LOGIN_FAILED`
- `READ_MEMBERS`, `READ_MEMBER_DETAIL`
- `ADMIN_ACTION_DENIED` – when a user attempts an admin endpoint
- `READ_MEMBER_DENIED` – when user tries to view another member's profile
- `UPDATE_MEMBER_DENIED`, `CANCEL_BOOKING_DENIED`
- `CREATE_MEMBER`, `DELETE_MEMBER`, `UPDATE_MEMBER`
- `APPLY_INDEXES`, `DROP_INDEXES`
- `BENCHMARK_RUN`

**Unauthorised direct DB modifications** (e.g., using DB Browser for SQLite directly) will be absent from the log, making them immediately identifiable as bypassing the API security layer.

---

## SubTask 4 – SQL Indexing

10 indexes applied targeting `WHERE`, `JOIN`, and `ORDER BY` clauses:

| Index Name               | Table       | Column(s)          | Targets                          |
|--------------------------|-------------|--------------------|----------------------------------|
| idx_booking_passenger    | Booking     | PassengerID        | WHERE PassengerID = ?            |
| idx_booking_trip         | Booking     | TripID             | JOIN Trip ON b.TripID            |
| idx_booking_status       | Booking     | BookingStatus      | WHERE BookingStatus = 'Confirmed'|
| idx_trip_date_status     | Trip        | TripDate, Status_  | WHERE TripDate=? AND Status_=?   |
| idx_trip_route           | Trip        | RouteID            | JOIN Route ON t.RouteID          |
| idx_trip_driver          | Trip        | DriverID           | JOIN Driver ON t.DriverID        |
| idx_driver_member        | Driver      | MemberID           | JOIN Member ON d.MemberID        |
| idx_passenger_member     | Passenger   | MemberID           | JOIN Member ON p.MemberID        |
| idx_member_type          | Member      | MemberType         | WHERE MemberType = ?             |
| idx_transaction_booking  | Transaction | BookingID          | WHERE BookingID = ?              |

---

## SubTask 5 – Performance Benchmarking

### Benchmark Results (200 runs, SQLite in-process)

| Query                        | Before (ms) | After (ms) | Plan Change              |
|------------------------------|-------------|------------|--------------------------|
| Bookings by PassengerID      | 0.333       | 0.156      | Scan → Index Seek        |
| Bookings JOIN Trip JOIN Route| 0.273       | 0.142      | Improved join traversal  |
| Driver detail by MemberID    | 0.396       | 0.126      | Scan → Index Seek        |
| Transactions by BookingID    | 0.371       | 0.367      | Scan → Index Seek        |
| Trips by Date + Status       | 0.454       | 0.394      | Scan → Composite Index   |

**Access plan confirmed via `EXPLAIN QUERY PLAN`** – results shift from `SCAN` (full table scan) to `SEARCH … USING INDEX` after index application.

---

## API Endpoints Summary

### Auth
- `POST /api/login`  – Authenticate, start session
- `POST /api/logout` – End session
- `GET  /api/me`     – Current user info

### Members (SubTask 2 + 3)
- `GET    /api/members`           – List (redacted for non-admin)
- `GET    /api/members/<id>`      – Detail (own profile or admin)
- `POST   /api/members`           – Create (admin only)
- `PUT    /api/members/<id>`      – Update (own limited fields or admin)
- `DELETE /api/members/<id>`      – Delete (admin only)

### Trips
- `GET /api/trips`         – List with filters (status, date)
- `GET /api/trips/<id>`    – Detail

### Bookings
- `GET    /api/bookings`       – List (own for users, all for admin)
- `POST   /api/bookings`       – Create booking
- `DELETE /api/bookings/<id>`  – Cancel booking

### Admin (admin only)
- `GET  /api/admin/users`              – All users
- `PUT  /api/admin/users/<id>/role`    – Change role
- `DELETE /api/admin/users/<id>`       – Delete user

### Indexing (admin only)
- `POST /api/indexes/apply`  – Apply all 10 indexes
- `POST /api/indexes/drop`   – Drop all indexes
- `GET  /api/indexes/status` – List active indexes

### Benchmarking
- `POST /api/benchmark/run`  – Run 200×5 benchmark queries

### Logs (admin only)
- `GET /api/logs` – Last 200 audit log entries
