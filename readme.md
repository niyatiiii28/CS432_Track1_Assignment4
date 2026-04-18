# CS 432 – Databases | Track 1 | Assignment 3
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



## 📌 Overview

This project extends the **ShuttleGo** system to a distributed architecture using **MySQL sharding**. Data is partitioned across three shards to ensure high availability and scalability.

---

## 🧠 Sharding Logic

We use **Hash-based partitioning** to ensure balanced data distribution.

- **Shard Key:** `MemberID`
- **Routing Logic:**

$$\text{shard\_id} = \text{MemberID} \mod 3$$

- **Shards:** MySQL instances running on ports `3307`, `3308`, and `3309`.

---

## 🗂️ Project Structure

```
Module_B/
├── app.py                       # Main Flask/FastAPI application
├── init_db.py                   # Database initialization script
├── generate_random_data.py      # Seed data generator
├── generate_noshow_penalties.py # Penalty logic processor
├── sql/
│   ├── schema.sql               # Table definitions
│   └── add_indexes.sql          # Performance optimization
├── moduleB_stress_test.py       # Load testing script
└── logs/                        # System logs
```

---

## 🏗️ Architecture Design

### 🔹 Sharded Tables
Distributed across **all shards** based on `MemberID`.

- `Member` / `Passenger` / `Driver`
- `Booking` / `Transaction`
- `BookingCancellation` / `NoShowPenalty`
- `users` / `group_mappings`

### 🔹 Global Tables
Stored exclusively in **Shard 0** *(Primary Reference Shard)*.

- `Vehicle`
- `Route`
- `Trip`
- `DriverAssignment`

---

## ⚙️ Setup & Installation

### 1. Activate Environment

```bash
source .venv/bin/activate
```

### 2. Initialize Databases

This script creates schemas on all shards, inserts the admin user, and generates the initial dataset.

```bash
python init_db.py
```

### 3. Run the Server

```bash
python app.py
```

The API will be available at: **http://127.0.0.1:5050**

### 4. Stress Testing *(Optional)*

```bash
python moduleB_stress_test.py
```

---

## 🔀 Query Routing Rules

| Query Type | Execution Logic |
|---|---|
| **Point Queries** | Routed directly to a specific shard using `MemberID % 3`. |
| **Insertions** | Data is hashed and stored in the designated shard. |
| **Range Queries** | *Scatter-Gather:* Queries all shards and merges results in the app layer. |

> [!TIP]
> **Optimization Note:** All related data for a specific member is co-located in the same shard to avoid expensive cross-shard joins.

---

## 📊 Notes

- **Balanced Distribution:** Hash-based routing prevents "hot shards."
- **Global Table Strategy:** Static reference data is centralized in Shard 0 to maintain referential integrity without complexity.
- **Minimized Latency:** Point queries bypass the need to search multiple databases.
