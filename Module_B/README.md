# ShuttleGo – Module B
## Project Structure

```
shuttlego/
├── app.py                      ← Main Flask application (SubTasks 3, 4, 5)
├── benchmark.py                ← Script for performance benchmarking
├── generate_random_data.py     ← Script to populate dummy data
├── init_db.py                  ← Script to initialize the database
├── README.md                   ← Project documentation
├── requirements.txt            ← Python dependencies
├── shuttlego.db                ← SQLite database (from SubTask 1)
├── logs/
│   └── audit.log               ← Security audit log (auto-generated)
├── sql/                        ← SQL schema and related scripts
└── templates/
    ├── base.html               ← Shared layout with sidebar + RBAC-aware nav
    ├── login.html              ← Login page
    ├── dashboard.html          ← Home dashboard
    ├── members.html            ← Member portfolio (RBAC-restricted)
    ├── trips.html              ← Trip browser
    ├── bookings.html           ← Booking management
    ├── admin.html              ← Admin panel (admin only)
    ├── benchmark.html          ← SQL performance benchmark (SubTask 5)
    ├── logs.html               ← Audit log viewer (admin only)
    └── error.html              ← 403/error page
```

---

## How to Run

```bash
git clone https://github.com/pandasuwu/CS432_Track1_Submission
cd CS432_Track1_Submission

# (optional) create and activate virtual environment
python -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# run the project
python init_db.py
python app.py

#opens in: http://127.0.0.1:5050/dashboard
```

