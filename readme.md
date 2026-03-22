# CS 432 – Databases | Track 1 | Assignment 2
## ShuttleGo – Shuttle Management and Booking System

**Course:** CS 432 – Databases | Semester II (2025–2026)  
**Instructor:** Dr. Yogesh K. Meena  
**Institution:** Indian Institute of Technology, Gandhinagar

| Name | Roll No. |
|------|----------|
| Niyati Siju | 23110312 |
| K R Tanvi | 23110149 |
| Makkena Lakshmi Manasa | 23110193 |
| Aeshaa Nehal Shah | 23110018 |
| Suhani | 24110358 |

**Module A Video Demo:** [Watch here](https://iitgnacin-my.sharepoint.com/:v:/g/personal/23110312_iitgn_ac_in/IQA7oXDkT-AuQI-TG58IFU2jAUJTH7oVLLXuJiZf0O1WBD0?e=7zOhbg)  
**Module B Video Demo:** *(link to be added)*  

---

## Project Overview

This assignment is divided into two independent modules:

- **Module A** — A lightweight DBMS indexing engine built from scratch using a **B+ Tree**, benchmarked against a brute-force linear approach.
- **Module B** — A secure full-stack web application (Flask + SQLite) with REST APIs, JWT-based session management, Role-Based Access Control (RBAC), SQL indexing, and live performance benchmarking for the ShuttleGo shuttle management system.

---

## Repository Structure

```
CS432_Track1_Submission/
│
├── Module_A/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── bplustree.py              # B+ Tree implementation
│   │   ├── bruteforce.py             # BruteForceDB baseline
│   │   └── performance_analyzer.py   # Benchmarking utilities
│   ├── report.ipynb                  # Full report with benchmarks & visualizations
│   └── requirements.txt
│
└── Module_B/
    ├── app.py                        # Main Flask application (SubTasks 3, 4, 5)
    ├── init_db.py                    # One-command DB initializer + data seeder
    ├── generate_random_data.py       # Realistic data generator (members, trips, bookings)
    ├── benchmark.py                  # Standalone CLI benchmarking script (SubTask 5)
    ├── shuttlego.db                  # SQLite database (auto-created by init_db.py)
    ├── requirements.txt
    ├── logs/
    │   └── audit.log                 # Security audit log (auto-generated)
    ├── sql/
    │   ├── schema.sql                # Table definitions + infrastructure seed data
    │   └── add_indexes.sql           # All SQL indexes (SubTask 4)
    └── templates/
        ├── base.html                 # Shared dark-theme layout with RBAC-aware sidebar
        ├── login.html                # Sign in / Sign up with 3-step registration wizard
        ├── dashboard.html            # Role-aware home dashboard
        ├── members.html              # Member portfolio (admin) / own profile (user)
        ├── trips.html                # Trip browser with live GPS location
        ├── bookings.html             # Booking management + no-show penalties
        ├── schedule.html             # Driver shift assignments + vehicle maintenance
        ├── admin.html                # Control panel — users, RBAC, index management
        ├── benchmark.html            # Live SQL performance benchmark (SubTask 5)
        ├── logs.html                 # Audit log viewer (admin-only)
        └── error.html                # 403 / access denied page
```

---

## Module A – Lightweight DBMS with B+ Tree Index

### Overview

Module A implements a B+ Tree–based indexing engine and compares it against a `BruteForceDB` (plain Python list) approach. Performance is measured across insertion, search, deletion, range queries, and memory usage for dataset sizes from 1,000 to 100,000 elements.

### File Descriptions

| File | Description |
|------|-------------|
| `database/bplustree.py` | Full B+ Tree with insert, delete, search, range query, update, get_all, and Graphviz visualization |
| `database/bruteforce.py` | `BruteForceDB` baseline using a Python list |
| `database/performance_analyzer.py` | `PerformanceAnalyzer` class for timing and deep memory measurement |
| `report.ipynb` | Jupyter notebook — implementation walkthrough, benchmarking plots, tree visualizations, conclusions |
| `requirements.txt` | Python dependencies |

### Setup & Installation

```bash
cd CS432_Track1_Submission/Module_A

pip install -r requirements.txt
# Also install Graphviz at system level:
# Ubuntu: sudo apt install graphviz
# macOS:  brew install graphviz

jupyter notebook report.ipynb
```

### B+ Tree — Implementation Details

The `BPlusTree` class uses a configurable minimum degree `t` (default `t=3`):

| Method | Description |
|--------|-------------|
| `insert(key, value)` | Inserts a key-value pair; splits nodes automatically when full |
| `search(key)` | Traverses root → leaf; returns value or `None` |
| `delete(key)` | Removes key; rebalances via borrowing or merging |
| `range_query(start, end)` | Scans linked leaf nodes sequentially — no repeated root traversal |
| `update(key, new_value)` | Locates key in leaf and updates value in-place |
| `get_all()` | Returns all key-value pairs in sorted order via leaf-chain traversal |
| `visualize_tree()` | Returns a `graphviz.Digraph` rendering the full tree |

**`BPlusTreeNode` fields:**

| Field | Used In | Description |
|-------|---------|-------------|
| `keys` | All nodes | Sorted list of keys |
| `children` | Internal nodes | Pointers to child nodes |
| `values` | Leaf nodes | Values associated with each key |
| `next` | Leaf nodes | Pointer to next leaf (linked list for range scans) |

### BruteForceDB — Baseline

`BruteForceDB` stores `(key, value)` pairs in a flat Python list for baseline comparison.

| Operation | Complexity |
|-----------|------------|
| Insert | O(1) |
| Search | O(n) |
| Delete | O(n) |
| Range Query | O(n) |

### Performance Analysis

Benchmarks run across dataset sizes: `1,000 | 5,000 | 10,000 | 50,000 | 100,000`

| Operation | B+ Tree | BruteForceDB |
|-----------|---------|--------------|
| Search | O(log n) | O(n) |
| Insertion | O(log n) | O(1) |
| Deletion | O(log n) | O(n) |
| Range Query | O(log n + k) | O(n) |

**Key findings:**
- **Insertion:** BruteForceDB wins — simple `append()` vs. B+ Tree's traversal and node splits.
- **Search & Deletion:** B+ Tree dominates at scale — logarithmic vs. linear growth.
- **Range Query:** B+ Tree excels via linked leaf nodes — sequential traversal, no backtracking to root.
- **Memory:** B+ Tree uses ~2× more memory due to node pointers and leaf linkage overhead.

#### Memory Usage

| Dataset Size | B+ Tree (bytes) | BruteForce (bytes) |
|-------------|-----------------|-------------------|
| 1,000 | 273,880 | 150,419 |
| 5,000 | 1,287,645 | 707,024 |
| 10,000 | 2,569,783 | 1,404,706 |
| 50,000 | 12,746,397 | 6,999,400 |
| 100,000 | 25,479,148 | 13,900,583 |

### Tree Visualization

`visualize_tree()` uses `graphviz.Digraph` to render internal nodes (light blue), leaf nodes (light green), and leaf linkage (dashed green edges). Run cell 24 in `report.ipynb` or view `bptree.png`.

---

## Module B – Local API Development, RBAC & Database Optimization

### Overview

Module B is a full-stack Flask web application for the ShuttleGo shuttle management system. It uses a local SQLite database, exposes a REST API with Flask session + JWT authentication, enforces Role-Based Access Control, logs every API action to `audit.log`, and includes live SQL benchmarking before and after index application.

### Setup & Installation

```bash
cd CS432_Track1_Submission/Module_B

# Install dependencies
pip install -r requirements.txt
# flask>=3.0.0  |  bcrypt>=4.0.0  |  PyJWT>=2.8.0  |  werkzeug>=3.0.0

# Initialize database + seed all data (run once)
python init_db.py

# Start the server
python app.py
# Open http://127.0.0.1:5050
```

`init_db.py` drops and recreates all tables from `sql/schema.sql`, seeds infrastructure data (vehicles, routes, maintenance), creates the admin user, then calls `generate_random_data.py` to populate ~150 members, ~500 trips, and all associated bookings, transactions, cancellations, and driver assignments automatically.

### Demo Credentials

| Username | Password | Role | Group |
|----------|----------|------|-------|
| `admin` | `admin123` | admin | admin_group |
| *(generated)* | `user123` | user | passenger_group or driver_group |

> Regular user credentials are generated by `generate_random_data.py`. After running `init_db.py`, check the printed output for sample usernames, or log in as admin and visit the Control Panel to see all users.

### Database Schema

`shuttlego.db` contains 15 tables across two layers. Infrastructure seed data (vehicles, routes, maintenance records) is loaded from `sql/schema.sql`. All people-dependent data is generated by `generate_random_data.py`.

**Core system tables:**

| Table | Purpose |
|-------|---------|
| `users` | Login credentials, role (`admin`/`user`), linked `MemberID` |
| `group_mappings` | Maps each user to a named RBAC group |

**Project-specific tables:**

| Table | Purpose |
|-------|---------|
| `Member` | All system members (passengers and drivers) |
| `Passenger` | Payment preference, emergency contact, assistance needs |
| `Driver` | License, rating, experience years, status |
| `Vehicle` | Fleet info — model, capacity, GPS device ID |
| `VehicleLiveLocation` | Real-time GPS coordinates per vehicle |
| `VehicleMaintenance` | Service records and scheduled maintenance |
| `Route` | Named routes with source, destination, fares, intermediate stops |
| `Trip` | Scheduled trips linking route, vehicle, and driver |
| `TripOccupancyLog` | Seat occupancy snapshots per trip |
| `DriverAssignment` | Driver–vehicle–trip assignments per shift |
| `Booking` | Passenger bookings with QR codes and verification status |
| `Transaction` | Payments, refunds, and penalties per booking |
| `BookingCancellation` | Cancellation records with refund/penalty breakdown |
| `NoShowPenalty` | Auto-generated penalties for no-show bookings |

Foreign key cascade deletes are enforced: deleting a `Member` propagates correctly to `Passenger`/`Driver`, `users`, and `group_mappings` — no orphan records.

### SubTask 3 — RBAC Implementation

Two decorators enforce access control on every route:

```python
@login_required   # Any authenticated user (checks Flask session)
@admin_required   # Admin role only — returns 403 otherwise and logs the attempt
```

Authentication uses both **Flask sessions** (for browser UI) and **JWT tokens** (returned on login, validated via `/isAuth`).

#### Role Permissions

| Action | Admin | Regular User |
|--------|-------|--------------|
| View all member profiles | ✅ | ❌ own profile only |
| View full contact details | ✅ | ❌ own only |
| Create / delete members | ✅ | ❌ |
| Update member fields | ✅ all fields | ❌ `ContactNumber` / `Image` only |
| View all bookings | ✅ | ❌ own only |
| Cancel any booking | ✅ | ❌ own only |
| View no-show penalties | ✅ all | ❌ own only |
| View vehicle live location | ✅ all | ❌ own active trips only |
| View driver assignments | ✅ all | ❌ own assignments only |
| View vehicle maintenance | ✅ all + cost | ❌ own vehicles, no cost |
| Manage users and roles | ✅ | ❌ |
| Apply / drop SQL indexes | ✅ | ❌ |
| Run benchmark | ✅ | ❌ |
| View audit logs | ✅ | ❌ |
| Change own password | ✅ | ✅ |
| Register new account | public | public |

#### RBAC Groups

| Group | Access Level |
|-------|--------------|
| `admin_group` | Full CRUD, user management, index control, audit log, benchmark |
| `driver_group` | Own profile, own shift assignments, vehicle maintenance (no cost), trip list |
| `passenger_group` | Own bookings, own penalties, own profile, vehicle location for active trips |

#### Security Audit Logging

Every API call is written to `logs/audit.log`:

```
TIMESTAMP | LEVEL | USER=<username> ROLE=<role> IP=<ip> VIA=API ACTION=<action> STATUS=<OK|FAIL|FORBIDDEN> DETAIL=<detail>
```

Logged actions include: `LOGIN`, `LOGIN_FAILED`, `LOGOUT`, `REGISTER`, `PASSWORD_CHANGED`, `READ_MEMBERS`, `READ_MEMBER_DENIED`, `ADMIN_ACTION_DENIED`, `CREATE_MEMBER`, `DELETE_MEMBER`, `UPDATE_MEMBER`, `CREATE_BOOKING`, `CANCEL_BOOKING`, `CANCEL_BOOKING_DENIED`, `READ_VEHICLE_LOCATION_DENIED`, `APPLY_INDEXES`, `DROP_INDEXES`, `BENCHMARK_RUN`, `READ_LOGS`.

Any database modification made **without** going through the session-validated API (e.g. directly via DB Browser for SQLite) will be absent from the log — making unauthorized changes immediately identifiable.

### SubTask 4 — SQL Indexing

Indexes are defined in two places: `sql/add_indexes.sql` (applied at init time) and `app.py`'s `INDEXES` list (applied/dropped live from the Admin UI). The full set targets `WHERE`, `JOIN`, and `ORDER BY` clauses across the most-used API queries:

| Index | Table | Column(s) | Query Pattern |
|-------|-------|-----------|---------------|
| `idx_users_username` | users | username | `WHERE username = ?` — every login |
| `idx_users_member_id` | users | MemberID | JWT → MemberID resolution |
| `idx_booking_passenger_id` | Booking | PassengerID | `WHERE PassengerID = ?` |
| `idx_booking_trip_id` | Booking | TripID | `JOIN Trip ON b.TripID` |
| `idx_booking_time` | Booking | BookingTime DESC | `ORDER BY BookingTime DESC` |
| `idx_trip_date` | Trip | TripDate DESC | `ORDER BY TripDate DESC` |
| `idx_trip_route_id` | Trip | RouteID | `JOIN Route ON t.RouteID` |
| `idx_trip_driver_id` | Trip | DriverID | `JOIN Driver ON t.DriverID` |
| `idx_trip_vehicle_id` | Trip | VehicleID | `JOIN Vehicle ON t.VehicleID` |
| `idx_transaction_booking_id` | Transaction | BookingID | `WHERE BookingID = ?` |
| `idx_transaction_date` | Transaction | TransactionDate DESC | `ORDER BY TransactionDate DESC` |
| `idx_driver_member_id` | Driver | MemberID | `WHERE MemberID = ?` — RBAC self-check |
| `idx_passenger_member_id` | Passenger | MemberID | `WHERE MemberID = ?` — RBAC self-check |
| `idx_assignment_driver_id` | DriverAssignment | DriverID | `WHERE DriverID = ?` |
| `idx_assignment_trip_id` | DriverAssignment | TripID | `WHERE TripID = ?` |
| `idx_cancellation_booking_id` | BookingCancellation | BookingID | `WHERE BookingID = ?` |

### SubTask 5 — Performance Benchmarking

Two benchmarking paths are available:

**Live UI benchmark** (`/benchmark`, admin only): `POST /api/benchmark/run` runs 5 queries × 200 iterations each, recording avg/min/max execution time. `EXPLAIN QUERY PLAN` detects `FULL TABLE SCAN` vs `INDEX SEEK`. A before/after comparison table appears when run twice.

**CLI benchmark** (`python benchmark.py`): Runs 12 queries × 500 iterations each, drops all indexes, measures baseline, applies indexes, measures again, and writes a full report to `benchmark_report.txt` including median/mean/min/max and `EXPLAIN QUERY PLAN` output for every query.

#### Benchmark Results (from `benchmark.py`, 500 runs, medians)

| Query | Before (µs) | After (µs) | Speedup |
|-------|-------------|------------|---------|
| Login lookup by username | ~320 | ~85 | ~3.8× |
| Passenger bookings (WHERE PassengerID) | ~280 | ~70 | ~4× |
| Recent bookings (ORDER BY BookingTime DESC) | ~410 | ~95 | ~4.3× |
| List trips with JOINs (ORDER BY TripDate) | ~520 | ~140 | ~3.7× |
| Passenger transactions via JOIN | ~350 | ~90 | ~3.9× |
| Driver profile by MemberID | ~190 | ~55 | ~3.5× |

Access plans shift from `SCAN` (full table scan) to `SEARCH … USING INDEX` after index application, confirmed via `EXPLAIN QUERY PLAN`.

### API Endpoints

#### Auth & Registration
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/login` | Public | Authenticate; returns Flask session + JWT token |
| POST | `/api/logout` | Any | Clear session |
| POST | `/api/register` | Public | Self-registration (creates Member + Passenger/Driver stub + user) |
| GET | `/isAuth` | Any | Validate JWT token; returns username, role, expiry |
| GET | `/api/me` | Auth | Current user info from session |
| PUT | `/api/me/password` | Auth | Change own password |

#### Members
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/members` | Auth | All members (admin) or own profile (user) |
| GET | `/api/members/<id>` | Auth | Full detail — own profile or admin only |
| POST | `/api/members` | Admin | Create new member |
| PUT | `/api/members/<id>` | Auth | Admin: all fields; user: `ContactNumber`/`Image` only |
| DELETE | `/api/members/<id>` | Admin | Delete member (cascades to all linked tables) |

#### Trips & Vehicles
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/trips` | Auth | List with optional `?status=` / `?date=` filters |
| GET | `/api/trips/<id>` | Auth | Full trip detail with driver and vehicle info |
| GET | `/api/vehicles/locations` | Auth | All latest GPS locations (admin) or own active trips (user) |
| GET | `/api/vehicles/<id>/location` | Auth | Single vehicle GPS — enforces booking/assignment check for non-admin |

#### Bookings & Penalties
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/bookings` | Auth | All bookings (admin) or own bookings (user) |
| POST | `/api/bookings` | Auth | Create booking (PassengerID auto-resolved from session) |
| DELETE | `/api/bookings/<id>` | Auth | Cancel booking (own only unless admin) |
| GET | `/api/my/penalties` | Auth | No-show penalties (all for admin, own for passenger) |

#### Driver Schedule
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/my/assignments` | Auth | All assignments (admin) or own shift assignments (driver) |
| GET | `/api/my/maintenance` | Auth | All maintenance (admin) or own vehicles' records (driver) |

#### Admin
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/admin/users` | Admin | All users with roles and groups |
| PUT | `/api/admin/users/<id>/role` | Admin | Change user role |
| DELETE | `/api/admin/users/<id>` | Admin | Delete user |
| POST | `/api/indexes/apply` | Admin | Apply all indexes |
| POST | `/api/indexes/drop` | Admin | Drop all indexes |
| GET | `/api/indexes/status` | Auth | List active indexes |
| POST | `/api/benchmark/run` | Admin | Run 200×5 live benchmark |
| GET | `/api/logs` | Admin | Last 200 audit log entries |

---
