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


Overview

This project extends the ShuttleGo system to a distributed database using MySQL sharding.

Data is partitioned across 3 shards using hash-based routing:

shard_id = MemberID % 3

The system ensures:

Balanced data distribution
Efficient query routing
Scalable architecture
🗂️ Project Structure
Module_B/
│
├── app.py                     # Flask backend (API + routing)
├── init_db.py                # Initializes all shards (schema + data)
├── generate_random_data.py   # Data generation (sharded)
├── generate_noshow_penalties.py
│
├── sql/
│   ├── schema.sql
│   ├── add_indexes.sql
│
├── moduleB_stress_test.py    # Testing (optional)
└── logs/
🧠 Sharding Design
Shard Key: MemberID
Strategy: Hash-based partitioning
Shards: 3 MySQL instances (ports 3307, 3308, 3309)
Sharded Tables
Member, Passenger, Driver
Booking, Transaction
BookingCancellation, NoShowPenalty
users, group_mappings
Global Tables (Shard 0)
Vehicle, Route, Trip, DriverAssignment
⚙️ Setup & Run
1. Activate environment
source .venv/bin/activate
2. Initialize database (ALL shards)
python init_db.py

This will:

Create schema on all shards
Insert admin
Generate full dataset
3. Run server
python app.py

Server runs at:

http://127.0.0.1:5050
4. (Optional) Run tests
python moduleB_stress_test.py
🔀 Query Routing
Point queries: routed using MemberID % 3
Inserts: stored in one shard only
Range queries: fan-out → merge results
📊 Notes
All related data is stored in the same shard
Global tables are stored in shard 0
No cross-shard joins are used
