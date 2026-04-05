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

**Video Demo:** [Watch here](https://iitgnacin-my.sharepoint.com/:v:/g/personal/23110312_iitgn_ac_in/IQCSNpGj8tufTL_OPGmM-vXzAToJjEt68GKRbbQ8I-7yeP4)  


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



# ShuttleGo — Module B: Concurrent Workload & Stress Testing

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![Database](https://img.shields.io/badge/Database-SQLite-green)
![Status](https://img.shields.io/badge/Status-ACID%20Compliant-success)

---

## Overview

Module B evaluates the behavior of the ShuttleGo system under **concurrent usage**, **high request load**, and **failure scenarios**.

The objective is to ensure that the system maintains **correctness, stability, and ACID properties** when multiple users interact with it simultaneously.

A custom multi-threaded Python script is used to simulate real-world user behavior and stress conditions.

---

## Architecture

The system follows a layered architecture:

* Client Simulation (Stress Test Script)
* Flask API (`app.py`)
* Database (SQLite)
* Disk Storage (Persistent DB + Write-Ahead Logging)

### Flow

Client Simulation
→ Flask API
→ Database
→ Disk (WAL + Persistent Storage)

---

## Components

### Backend API (`app.py`)

* Handles user requests (booking, trips, authentication)
* Processes concurrent API calls
* Ensures correct database operations

### Database (SQLite)

* Stores Trips, Bookings, Users
* Handles concurrent reads and serialized writes
* Uses Write-Ahead Logging (WAL) for safety

### Stress Testing Script (`moduleB_stress_test.py`)

* Simulates multiple users using threading
* Sends concurrent API requests
* Measures performance metrics
* Validates correctness under load and failures

---

## Experiments Performed

### 1. Race Condition Test (Isolation)

* 20 users attempt to book the **same seat simultaneously**

**Expected:**
Only one booking should succeed

**Observed:**

* 1 success
* 19 conflicts

**Conclusion:**
System prevents double-booking and ensures isolation

**Bonus Case:**

* Each user books a different seat
* Some failures occur due to SQLite write locking

This indicates a **performance limitation**, not a correctness issue.

---

### 2. Stress Test (Consistency)

* 300 rapid concurrent API requests
* Includes `/api/trips` and `/api/bookings`

**Observed:**

* 100% successful responses (HTTP 200)
* No errors
* Increased response time under load

**Conclusion:**
System remains stable and consistent under heavy traffic.

---

### 3. Failure Simulation (Atomicity)

* Requests terminated mid-execution (timeout-based)
* Simulates:

  * network failure
  * client crash

**Observed:**

* No partial data stored
* System remains functional

**Conclusion:**
Atomicity is maintained (all-or-nothing execution).

---

### 4. Durability Test

* Booking created and immediately read back

**Observed:**

* Data persists in database
* Visible across sessions

**Conclusion:**
Durability is ensured.

---

## ACID Properties Validation

| Property    | Verification Method |
| ----------- | ------------------- |
| Atomicity   | Failure Simulation  |
| Consistency | Stress Test         |
| Isolation   | Race Condition      |
| Durability  | Read-after-write    |

---

## File Structure

```
Module_B/
│
├── app.py                  # Flask backend
├── init_db.py              # Database initialization
├── moduleB_stress_test.py  # Stress testing script
├── moduleB_report.txt      # Test output report
│
├── logs/
│   └── audit.log           # Server logs
│
└── README.md
```

---

## How to Run

### 1. Navigate to Module_B

```bash
cd Module_B
```

### 2. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 3. Initialize Database

```bash
python init_db.py
```

### 4. Start Server

```bash
python app.py
```

Server runs at:

```
http://127.0.0.1:5050
```

### 5. Run Stress Tests

```bash
python moduleB_stress_test.py
```

---

## Key Observations

* System successfully prevents race conditions
* Maintains correctness under concurrent access
* Remains stable under high load
* Ensures rollback of incomplete transactions
* Prioritizes correctness over performance

---

## Limitations

* SQLite allows only one write at a time (limited concurrency)
* Increased latency under heavy load
* No advanced concurrency control (e.g., MVCC)
* Single-node architecture (no distributed support)

---

## Output Files

* `moduleB_report.txt` → Test results summary
* `logs/audit.log` → Server activity logs

---

## Conclusion

Module B demonstrates that the ShuttleGo system can handle **real-world concurrent workloads** while maintaining correctness and reliability.

The system ensures:

* Safe handling of concurrent user requests
* Prevention of race conditions
* Reliable rollback under failures
* Persistent storage of committed data

Overall, the system satisfies **ACID properties** under concurrent and failure conditions, making it robust for practical use cases.

