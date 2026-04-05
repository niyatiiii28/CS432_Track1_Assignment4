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

**Video Demo:** [Watch here](https://iitgnacin-my.sharepoint.com/personal/23110312_iitgn_ac_in/_layouts/15/stream.aspx?id=%2Fpersonal%2F23110312%5Fiitgn%5Fac%5Fin%2FDocuments%2Ftrack1%5Fassignment3%5Fvideo%2Emp4&ga=1&referrer=StreamWebApp%2EWeb&referrerScenario=AddressBarCopied%2Eview%2Ebd990b13%2D8d1b%2D4373%2Daead%2Da423da0f6078)  


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



# Module B: Concurrent Workload & Stress Testing

## Overview

This module evaluates the behavior of the ShuttleGo system under concurrent user activity, high request load, and failure scenarios.

The objective is to ensure that the system maintains correct behavior and satisfies ACID properties when multiple users interact with the system simultaneously.

The module uses a custom multi-threaded testing script to simulate real-world usage conditions.

---

## Architecture

Client Simulation (Stress Test Script)
↓
Flask API (app.py)
↓
Database (SQLite)
↓
Disk (Persistent Storage + WAL)

---

## Components

### 1. Backend API (app.py)

Responsible for:

Handling user requests (booking, trips, authentication)
Processing concurrent API calls
Ensuring correct database operations
Maintaining system state under load

---

### 2. Database (SQLite)

Responsible for:

Storing application data (Trips, Bookings, Users)
Handling concurrent read/write operations
Ensuring data integrity using constraints and WAL

---

### 3. Stress Testing Script (moduleB_stress_test.py)

Responsible for:

Simulating multiple users using threading
Sending concurrent API requests
Measuring response times and throughput
Validating correctness under load and failures

---

## Experiments Performed

### 1. Race Condition Test

Simulates multiple users attempting to access the same resource simultaneously.

Scenario:
20 users attempt to book the same seat at the same time

Expected Behavior:
Only one booking should succeed

Observed Behavior:
One request succeeds
Remaining requests are rejected due to conflict

Result:
System prevents double-booking and ensures isolation

Bonus Scenario:
Each user books a different seat

Observation:
Some requests fail due to database write contention

Conclusion:
No logical errors; failures are due to SQLite write limitations

---

### 2. Stress Test

Simulates high system load using concurrent requests

Scenario:
300 rapid API requests across multiple endpoints

Metrics Measured:
Response time
Throughput
Error rate

Observed Behavior:
All requests return valid responses
No errors observed
Response time increases under load

Result:
System remains stable and consistent under heavy traffic

---

### 3. Failure Simulation

Simulates abrupt client-side failures during execution

Scenario:
Requests terminated before completion (timeout-based)

Expected Behavior:
Incomplete transactions should not be committed

Observed Behavior:
No partial data stored
System remains functional after failures

Result:
Atomicity is maintained

---

### 4. Durability Test

Verifies persistence of committed data

Scenario:
Create booking and immediately read it back

Expected Behavior:
Committed data should persist

Observed Behavior:
Data is successfully stored and retrieved

Result:
Durability is ensured

---

## ACID Properties Validation

### 1. Atomicity

Incomplete transactions are rolled back during failures
No partial updates are stored

---

### 2. Consistency

All operations maintain valid database state
No corrupted or invalid data observed under load

---

### 3. Isolation

Concurrent users do not interfere with each other
Race condition test confirms prevention of duplicate bookings

---

### 4. Durability

Committed data persists across requests and sessions
Verified through read-after-write operations

---

## Test Coverage

The module includes tests for:

Race conditions under concurrent access
High-load stress testing
Failure scenarios (client crashes)
Data persistence verification

---

## File Structure

├── Module_B/
├── app.py                     # Flask backend
├── init_db.py                # Database initialization
├── moduleB_stress_test.py    # Stress testing script
├── moduleB_report.txt        # Test output report
├── logs/
│   └── audit.log             # Server logs
└── README.md

---

## How to Run

### 1. Initialize Database

```bash
python init_db.py
```

### 2. Start Server

```bash
python app.py
```

### 3. Run Stress Tests

```bash
python moduleB_stress_test.py
```

---

## Example Flow

Before Stress Test:
System idle, no concurrent load

During Stress Test:
Multiple users send requests simultaneously
Database handles concurrent operations

After Test Completion:
System remains consistent
No data corruption observed

---

## Key Design Decisions

Use of multi-threading to simulate real users
Batch-based request execution for controlled load
Use of SQLite WAL for safe concurrent writes
Separation of testing logic from application logic

---

## Limitations

SQLite allows only one write at a time, limiting concurrency
Increased response time under heavy load
No advanced concurrency control mechanisms (e.g., MVCC)
Single-node architecture without distributed support

---

## Conclusion

This module successfully validates the system’s behavior under concurrent workloads and failure scenarios.

The system ensures:
Correct handling of simultaneous user requests
Prevention of race conditions
Safe rollback of incomplete transactions
Reliable persistence of committed data

Overall, the system demonstrates strong adherence to ACID properties and maintains correctness under real-world usage conditions.

