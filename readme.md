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
**Module B Video Demo:** [Watch here](https://www.youtube.com/playlist?list=PL-6oo6aPMMVtFdn1hKZg39qWfB-8Lqe0f)  


---

## Project Overview

This assignment is divided into two independent modules:

- **Module A** — Implements a transaction management system on a custom B+ Tree–based database, ensuring ACID properties through buffering, logging, and crash recovery. Focuses on correctness of operations, rollback handling, and maintaining consistency between database records and index structures.
- **Module B** — Simulates concurrent user workloads on the system to evaluate behavior under multi-user access, failures, and high load conditions. Focuses on ensuring isolation, preventing race conditions, and validating system robustness through stress testing.

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

#  Module A: Transaction Management & ACID Compliance

##  Overview

This module implements a **transaction management system** on top of a custom database with a **B+ Tree index**, ensuring full **ACID compliance**.

The system is designed with a clear separation of concerns:

* **Database Layer** → Handles storage, indexing, and persistence
* **Transaction Engine** → Handles transactions, logging, recovery, and ACID guarantees

---

##  Architecture

```
Application (Tests)
        ↓
Transaction Engine
        ↓
Database (Tables + B+ Tree Index)
        ↓
Disk (WAL + DB State)
```

---

## ⚙️ Components

### 1. Database (`database.py`)

Responsible for:

* Managing tables (`Booking`, `Trip`, `Transaction`)
* Maintaining B+ Tree indexes
* Applying changes (insert/update/delete)
* Persisting data to disk (`db_state.json`)

---

### 2. Transaction Engine (`transaction_engine.py`)

Responsible for:

* Transaction lifecycle (`begin`, `commit`, `rollback`)
* Write-Ahead Logging (WAL)
* Transaction buffer (for isolation)
* Crash recovery (REDO + UNDO)

---

### 3. Write-Ahead Log (`wal.log`)

Stores all operations before they are applied:

* `START` → Transaction begins
* `UPDATE` → Data modification
* `COMMIT` → Transaction success

---

##  ACID Properties Implementation

###  1. Atomicity (All-or-Nothing)

* Changes are first stored in a **transaction buffer**
* On failure → `rollback()` restores previous state using logs
* On success → `commit()` applies all changes

**Result:** No partial updates occur

---

###  2. Consistency (Valid State)

* Each operation maintains valid database structure
* Duplicate keys are handled as **updates**
* B+ Tree index is always synchronized with tables

**Result:** Database always remains valid

---

###  3. Isolation (No Dirty Reads)

* Each transaction has its own **private buffer**
* Uncommitted changes are **not visible** to other transactions

```
txn1 → writes in buffer
txn2 → cannot see txn1 data
```

**Result:** No dirty reads

---

### 4. Durability (Survives Crashes)

* All operations are written to **WAL before execution**
* On crash → recovery process:

  * **REDO** committed transactions
  * **UNDO** uncommitted transactions

**Result:** Committed data is never lost

---

## Recovery Process

When the system restarts:

1. Read WAL (`wal.log`)
2. Identify committed transactions
3. Apply:

   * **REDO** → Reapply committed updates
   * **UNDO** → Revert incomplete transactions
4. Persist final state

---

##  Test Coverage

The module includes tests for:

###  Atomicity

* Single transaction rollback
* Multiple transactions with mixed success/failure

###  Consistency

* Duplicate key update behavior

###  Durability

* Crash simulation using `os._exit(1)`
* Recovery using WAL replay

###  Isolation

* Verifies that uncommitted data is not visible across transactions

---

##  Files Structure

```
├── Module_A/
    ├── database/
        ├── database.py              # Storage + B+ Tree
        ├── transaction_engine.py   # Transaction logic
        ├── acid_test.py           # ACID property tests
        ├── wal.log                # Write-Ahead Log
        ├── db_state.json          # Persistent database
        ├── recovery.log           # Recovery tracing
        └── README.md
        ```

---

##  How to Run

### 1. Run ACID Tests

```bash
python acid_test.py
```

### 2. Choose test:

```
1 → Atomicity
2 → Atomicity (Multiple)
3 → Consistency
4 → Crash
5 → Recovery
6 → Isolation
```

---

## Example Flow

### Before Commit:

```
Buffer: contains data
Database: unchanged
```

### After Commit:

```
Buffer: cleared
Database: updated
```

### After Rollback:

```
Buffer: cleared
Database: unchanged
```

---

## Key Design Decisions

* Separation of **Database vs Transaction Engine**
* Use of **Write-Ahead Logging**
* Use of **transaction-local buffers** for isolation
* Implementation of **REDO + UNDO recovery**

---

## Conclusion

This module successfully implements a **mini database transaction system** with:

* Full ACID compliance
* Crash recovery
* Logging
* Isolation via buffering
* Clean modular architecture


Module B: Concurrent Workload & Stress Testing

Overview
This module evaluates the ShuttleGo backend under concurrent usage, high load, and failure scenarios. The objective is to ensure that the system maintains ACID properties when multiple users interact with it simultaneously.

The system simulates real-world conditions using a multi-threaded testing script that generates concurrent API requests to the Flask backend connected to a SQLite database.

Architecture

Client Simulation (Stress Test Script)
↓
Flask API (app.py)
↓
Database (SQLite)
↓
Disk (Persistent Storage + WAL)

Components

1. Backend Server (app.py)
   Responsible for:

* Handling API requests (bookings, trips, users)
* Managing business logic (seat booking, validation)
* Ensuring correct responses under concurrent access

2. Database (SQLite)
   Responsible for:

* Storing all application data (Trips, Bookings, Users)
* Enforcing constraints (e.g., unique seat booking)
* Handling concurrent read/write operations

3. Stress Testing Script (moduleB_stress_test.py)
   Responsible for:

* Simulating multiple users using threading
* Sending concurrent API requests
* Measuring system performance and correctness
* Generating reports (moduleB_report.txt)

ACID Properties Validation

1. Atomicity (All-or-Nothing)
   Simulated using failure scenarios where requests are terminated mid-execution.
   Incomplete operations are not committed to the database.

Result: No partial or corrupted data is stored

2. Consistency (Valid State)
   Tested using high-load stress testing with hundreds of requests.
   All responses return valid results without data corruption.

Result: Database remains in a consistent state

3. Isolation (No Interference Between Users)
   Tested using race condition scenarios where multiple users attempt to book the same seat simultaneously.
   Only one booking is allowed, and others are rejected.

Result: No duplicate bookings occur

4. Durability (Persistence of Data)
   Tested by creating a booking and immediately reading it back.
   Committed data is stored in the database and persists across operations.

Result: Data remains permanently stored after commit

Experiments Performed

1. Race Condition Test

* 20 users attempt to book the same seat simultaneously
* Verifies isolation and conflict handling

2. Stress Test

* 300 concurrent API requests
* Evaluates system stability and performance

3. Failure Simulation

* Requests terminated using timeouts
* Simulates client crashes and network failures
* Verifies rollback and system stability

4. Durability Test

* Write followed by immediate read
* Confirms persistence of committed data

Observations

* The system prevents race conditions and duplicate bookings
* All requests under stress testing return valid responses
* Failure scenarios do not leave partial data
* Committed data is immediately visible and persistent

Limitations

* SQLite allows only one write operation at a time, limiting concurrency
* Response times increase under heavy load
* No advanced concurrency control (e.g., MVCC or fine-grained locking)
* System operates on a single-node architecture

Files Structure

├── Module_B/
├── app.py                      # Flask backend
├── init_db.py                 # Database initialization
├── moduleB_stress_test.py     # Stress testing script
├── moduleB_report.txt         # Test results
├── logs/
└── audit.log              # Server logs
└── README.md

How to Run

1. Initialize Database

python init_db.py

2. Start Backend Server

python app.py

3. Run Stress Tests

python moduleB_stress_test.py

Example Flow

Race Condition:
Multiple users request same seat → only one succeeds

Stress Test:
Hundreds of requests → system processes all correctly

Failure Simulation:
Requests interrupted → no partial data stored

Durability:
Booking created → immediately visible on read

Key Design Decisions

* Use of multi-threading to simulate concurrent users
* Use of HTTP-based API testing to mimic real-world usage
* Separation between client simulation and backend system
* Focus on correctness over performance

Conclusion

This module successfully demonstrates that the ShuttleGo system can handle concurrent workloads while maintaining correctness and reliability.

The system ensures:

* Safe handling of simultaneous user operations
* Proper rollback during failures
* Consistent system state under load
* Persistent storage of committed data

Overall, the system achieves ACID compliance in a real-world application setting, with some limitations in scalability due to the use of SQLite.

