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
- **Module B** — A secure local web application (Flask + SQLite) with REST APIs, Role-Based Access Control (RBAC), SQL indexing, and live performance benchmarking for the ShuttleGo shuttle management system.

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
    ├── app.py                        # Main Flask application
    ├── shuttlego.db                  # SQLite database (auto-created)
    ├── logs/
    │   └── audit.log                 # Security audit log (auto-generated)
    ├── sql/
    │   └── schema.sql                # Database schema + seed data
    ├── templates/
    │   ├── base.html                 # Shared layout with RBAC-aware sidebar
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── members.html              # Member portfolio (RBAC-restricted)
    │   ├── trips.html
    │   ├── bookings.html
    │   ├── admin.html                # Admin-only panel
    │   ├── benchmark.html            # SQL performance benchmark
    │   ├── logs.html                 # Audit log viewer (admin-only)
    │   └── error.html
    ├── report.pdf                    # Optimization report
    └── requirements.txt
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
| `report.ipynb` | Jupyter notebook — implementation walkthrough, benchmarking plots, tree visualizations, and conclusions |
| `requirements.txt` | Python dependencies |

### Setup & Installation

```bash
# Clone the repository
git clone https://github.com/niyatiiii28/CS432_Track1_submission
cd CS432_Track1_submission/Module_A

# Install Python dependencies
pip install -r requirements.txt

# Launch the report notebook
jupyter notebook report.ipynb
```

> **Note:** Graphviz must also be installed at the system level for tree visualization to work.  
> Ubuntu/Debian: `sudo apt install graphviz`  
> macOS: `brew install graphviz`  
> Windows: [graphviz.org/download](https://graphviz.org/download/)

### B+ Tree — Implementation Details

The `BPlusTree` class supports a configurable minimum degree `t` (default `t=3`):

| Method | Description |
|--------|-------------|
| `insert(key, value)` | Inserts a key-value pair; splits nodes automatically when full |
| `search(key)` | Traverses root → leaf; returns associated value or `None` |
| `delete(key)` | Removes key; rebalances via borrowing from siblings or merging |
| `range_query(start, end)` | Scans linked leaf nodes sequentially — no repeated root traversal |
| `update(key, new_value)` | Locates key in leaf and updates its value in-place |
| `get_all()` | Returns all key-value pairs in sorted order via leaf-chain traversal |
| `visualize_tree()` | Returns a `graphviz.Digraph` object of the full tree |

**Node fields (`BPlusTreeNode`):**

| Field | Used In | Description |
|-------|---------|-------------|
| `keys` | All nodes | Sorted list of keys |
| `children` | Internal nodes | Pointers to child nodes |
| `values` | Leaf nodes | Values associated with each key |
| `next` | Leaf nodes | Pointer to next leaf (linked list for range scans) |

### BruteForceDB — Baseline

`BruteForceDB` stores `(key, value)` pairs in a flat Python list. All operations are linear and serve purely as a performance baseline.

| Operation | Complexity |
|-----------|------------|
| Insert | O(1) |
| Search | O(n) |
| Delete | O(n) |
| Range Query | O(n) |

### Performance Analysis

Benchmarks run across dataset sizes: `1,000 | 5,000 | 10,000 | 50,000 | 100,000`

#### Complexity Comparison

| Operation | B+ Tree | BruteForceDB |
|-----------|---------|--------------|
| Search | O(log n) | O(n) |
| Insertion | O(log n) | O(1) |
| Deletion | O(log n) | O(n) |
| Range Query | O(log n + k) | O(n) |

#### Key Findings

- **Insertion:** BruteForceDB wins — simple `append()` has no overhead. B+ Tree must traverse and potentially split nodes.
- **Search:** B+ Tree dominates at scale — logarithmic vs. linear growth.
- **Deletion:** B+ Tree scales far better; BruteForceDB needs a full scan per delete.
- **Range Query:** B+ Tree excels due to linked leaf nodes — sequential traversal with no backtracking to root.
- **Memory:** B+ Tree uses ~2× more memory than BruteForceDB due to node pointers, child arrays, and leaf linkage.

#### Memory Usage

| Dataset Size | B+ Tree (bytes) | BruteForce (bytes) |
|-------------|-----------------|-------------------|
| 1,000 | 273,880 | 150,419 |
| 5,000 | 1,287,645 | 707,024 |
| 10,000 | 2,569,783 | 1,404,706 |
| 50,000 | 12,746,397 | 6,999,400 |
| 100,000 | 25,479,148 | 13,900,583 |

### Tree Visualization

`visualize_tree()` uses `graphviz.Digraph` to render:
- **Internal nodes** — light blue fill
- **Leaf nodes** — light green fill
- **Leaf linkage** — dashed green edges (the linked list)

Run cell 24 in `report.ipynb` to generate a live visualization, or view the exported `bptree.png`.

---

## Module B – Local API Development, RBAC & Database Optimization

### Overview

Module B is a full-stack Flask web application for the ShuttleGo shuttle management system. It connects to a local SQLite database, exposes a REST API with session-based authentication, enforces Role-Based Access Control (RBAC), logs every API action to `audit.log`, and includes live SQL benchmarking before and after index application.

### Setup & Installation

```bash
cd CS432_Track1_Submission/Module_B

pip install flask

# Initialize the database (run once)
sqlite3 shuttlego.db < sql/schema.sql

# Start the server
python app.py
# Open http://localhost:5050
```

### Demo Credentials

| Username | Password | Role | Group |
|----------|----------|------|-------|
| `admin` | `admin123` | admin | admin_group |
| `rajesh` | `user123` | user | passenger_group |
| `suresh` | `user123` | user | driver_group |

### Database Schema

The SQLite database (`shuttlego.db`) contains 15 tables across two layers:

**Core system tables** (authentication and access control):

| Table | Purpose |
|-------|---------|
| `users` | Login credentials, role (`admin`/`user`), linked `MemberID` |
| `group_mappings` | Maps each user to a named RBAC group |

**Project-specific tables** (shuttle domain):

| Table | Purpose |
|-------|---------|
| `Member` | All system members (passengers and drivers) |
| `Passenger` | Passenger-specific details — payment preference, assistance needs |
| `Driver` | Driver-specific details — license, rating, experience |
| `Vehicle` | Fleet info — model, capacity, GPS device |
| `VehicleLiveLocation` | Real-time GPS coordinates per vehicle |
| `VehicleMaintenance` | Service records and scheduled maintenance |
| `Route` | Named routes with source, destination, fare, and stops |
| `Trip` | Scheduled trips linking route, vehicle, and driver |
| `TripOccupancyLog` | Seat occupancy snapshots per trip |
| `DriverAssignment` | Driver–vehicle–trip assignments per shift |
| `Booking` | Passenger bookings with QR codes and verification status |
| `Transaction` | Payments, refunds, and penalties per booking |
| `BookingCancellation` | Cancellation records with refund/penalty details |

Cascade deletes are enforced via foreign keys: deleting a `Member` propagates correctly to `Passenger`/`Driver`, `users`, and `group_mappings` — no orphan records.

### SubTask 3 — RBAC Implementation

Two decorators enforce access control on every route:

```python
@login_required   # Any authenticated user
@admin_required   # Admin role only
```

#### Role Permissions

| Action | Admin | Regular User |
|--------|-------|--------------|
| View all member profiles | ✅ | ❌ own only |
| View full contact details | ✅ | ❌ redacted for others |
| Create / delete members | ✅ | ❌ |
| Update any member | ✅ | ❌ own `ContactNumber` / `Image` only |
| View all bookings | ✅ | ❌ own only |
| Cancel any booking | ✅ | ❌ own only |
| Manage users and roles | ✅ | ❌ |
| Apply / drop SQL indexes | ✅ | ❌ |
| Run benchmark | ✅ | ✅ read-only |
| View audit logs | ✅ | ❌ |

#### RBAC Groups

| Group | Members | Access Level |
|-------|---------|--------------|
| `admin_group` | Admin users | Full CRUD, user management, index control, audit log |
| `driver_group` | Drivers | Own profile, assigned trips |
| `passenger_group` | Passengers | Own bookings, own profile |

#### Security Audit Logging

Every API call is written to `logs/audit.log`:

```
TIMESTAMP | LEVEL | USER=<username> ROLE=<role> IP=<ip> VIA=API ACTION=<action> STATUS=<OK|FAIL|FORBIDDEN> DETAIL=<detail>
```

Logged events include: `LOGIN`, `LOGIN_FAILED`, `READ_MEMBERS`, `READ_MEMBER_DENIED`, `ADMIN_ACTION_DENIED`, `CREATE_MEMBER`, `DELETE_MEMBER`, `UPDATE_MEMBER`, `CANCEL_BOOKING_DENIED`, `APPLY_INDEXES`, `DROP_INDEXES`, `BENCHMARK_RUN`, and more.

Any database modification made **without** going through the session-validated API (e.g. directly via DB Browser for SQLite) will be absent from the log — making unauthorized changes immediately identifiable.

### SubTask 4 — SQL Indexing

10 indexes targeting `WHERE`, `JOIN`, and `ORDER BY` clauses in the most-used API queries:

| Index | Table | Column(s) | Targets |
|-------|-------|-----------|---------|
| `idx_booking_passenger` | Booking | PassengerID | `WHERE PassengerID = ?` |
| `idx_booking_trip` | Booking | TripID | `JOIN Trip ON b.TripID` |
| `idx_booking_status` | Booking | BookingStatus | `WHERE BookingStatus = 'Confirmed'` |
| `idx_trip_date_status` | Trip | TripDate, Status_ | `WHERE TripDate=? AND Status_=?` |
| `idx_trip_route` | Trip | RouteID | `JOIN Route ON t.RouteID` |
| `idx_trip_driver` | Trip | DriverID | `JOIN Driver ON t.DriverID` |
| `idx_driver_member` | Driver | MemberID | `JOIN Member ON d.MemberID` |
| `idx_passenger_member` | Passenger | MemberID | `JOIN Member ON p.MemberID` |
| `idx_member_type` | Member | MemberType | `WHERE MemberType = ?` |
| `idx_transaction_booking` | Transaction | BookingID | `WHERE BookingID = ?` |

Indexes can be applied or dropped live from the Admin Panel UI (`/admin`), and their status reflects instantly on the Benchmark page.

### SubTask 5 — Performance Benchmarking

`POST /api/benchmark/run` runs each of 5 queries **200 times**, recording average, min, and max execution time. `EXPLAIN QUERY PLAN` is run alongside each query to detect the access plan (`FULL TABLE SCAN` vs `INDEX SEEK`).

#### Benchmark Results

| Query | Before (ms) | After (ms) | Plan Change |
|-------|-------------|------------|-------------|
| Bookings by PassengerID | 0.333 | 0.156 | Scan → Index Seek |
| Bookings JOIN Trip JOIN Route | 0.273 | 0.142 | Improved join traversal |
| Driver detail by MemberID | 0.396 | 0.126 | Scan → Index Seek |
| Transactions by BookingID | 0.371 | 0.367 | Scan → Index Seek |
| Trips by Date + Status | 0.454 | 0.394 | Scan → Composite Index |

The Benchmark page also renders a **before vs. after comparison table** when run twice (once with indexes off, once on).

### API Endpoints

#### Auth
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/login` | Public | Authenticate, start session |
| POST | `/api/logout` | Any | End session |
| GET | `/api/me` | Auth | Current user info |

#### Members
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/members` | Auth | List all (contact redacted for non-admin viewing others) |
| GET | `/api/members/<id>` | Auth | Full detail (own profile or admin) |
| POST | `/api/members` | Admin | Create new member |
| PUT | `/api/members/<id>` | Auth | Update (admin: all fields; user: contact + image only) |
| DELETE | `/api/members/<id>` | Admin | Delete member (cascades to linked tables) |

#### Trips
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/trips` | Auth | List with optional `?status=` and `?date=` filters |
| GET | `/api/trips/<id>` | Auth | Full trip detail with driver and vehicle info |

#### Bookings
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/bookings` | Auth | All bookings (admin) or own bookings (user) |
| POST | `/api/bookings` | Auth | Create booking (PassengerID auto-resolved from session) |
| DELETE | `/api/bookings/<id>` | Auth | Cancel booking (own only, unless admin) |

#### Admin
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/api/admin/users` | Admin | List all users with roles and groups |
| PUT | `/api/admin/users/<id>/role` | Admin | Change user role |
| DELETE | `/api/admin/users/<id>` | Admin | Delete user |

#### Indexing
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/indexes/apply` | Admin | Apply all 10 indexes |
| POST | `/api/indexes/drop` | Admin | Drop all indexes |
| GET | `/api/indexes/status` | Auth | List currently active indexes |

#### Benchmarking & Logs
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/benchmark/run` | Auth | Run 200×5 benchmark queries with EXPLAIN plan |
| GET | `/api/logs` | Admin | Last 200 audit log entries |

---

