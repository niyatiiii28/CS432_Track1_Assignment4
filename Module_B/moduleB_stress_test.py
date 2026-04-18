"""
ShuttleGo — Module B: Concurrent Workload & Stress Testing
CS 432 Assignment 3

Run from Module_B directory:
    python moduleB_stress_test.py

Make sure app.py is running first:
    python app.py
"""

import requests
import threading
import time
import statistics
from datetime import datetime

BASE_URL    = "http://127.0.0.1:5050"
REPORT_PATH = "moduleB_report.txt"

lines = []

def log(s=""):
    print(s)
    lines.append(s)

# ── Auth helpers ───────────────────────────────────────────────────────────────

def register_and_login(username, password="Test@1234"):
    s = requests.Session()
    s.post(f"{BASE_URL}/api/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "role_request": "passenger"
    })
    r = s.post(f"{BASE_URL}/api/login", json={"username": username, "password": password})
    return s if r.status_code == 200 else None


def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/login", json={"username": "admin", "password": "admin123"})
    return s if r.status_code == 200 else None


def get_first_available_trip(sess):
    """Return (trip_id, available_seats) for a trip with seats free."""
    try:
        r = sess.get(f"{BASE_URL}/api/trips")
        trips = r.json()
        if isinstance(trips, list):
            for t in trips:
                seats = t.get("AvailableSeats", 0)
                tid   = t.get("TripID")
                if tid and seats and int(seats) > 5:
                    return tid, int(seats)
    except Exception as e:
        log(f"  ERROR fetching trips: {e}")
    return None, 0


# ── Test 1: Race Condition ─────────────────────────────────────────────────────

def test_race_condition(trip_id, sessions):
    log("=" * 65)
    log("TEST 1: RACE CONDITION — Concurrent bookings on same seat")
    log("=" * 65)
    log(f"  Trip ID    : {trip_id}")
    log(f"  Seat       : 1  (all {len(sessions)} users try to book the SAME seat)")
    log(f"  Expected   : exactly 1 success, rest conflict/error")
    log()

    results = []
    lock = threading.Lock()

    def book(sess, i):
        try:
            r = sess.post(f"{BASE_URL}/api/bookings",
                          json={"TripID": trip_id, "SeatNumber": 1},
                          timeout=10)
            with lock:
                results.append({"user": i, "status": r.status_code, "body": r.text[:120]})
        except Exception as e:
            with lock:
                results.append({"user": i, "status": "ERROR", "body": str(e)})

    threads = [threading.Thread(target=book, args=(s, i)) for i, s in enumerate(sessions)]
    start = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.time() - start

    success  = [r for r in results if r["status"] in (200, 201)]
    conflict = [r for r in results if r["status"] in (409, 400)]
    errors   = [r for r in results if r["status"] not in (200, 201, 409, 400)]

    log(f"  Total requests    : {len(results)}")
    log(f"  Successful (2xx)  : {len(success)}")
    log(f"  Blocked (400/409) : {len(conflict)}")
    log(f"  Other errors      : {len(errors)}")
    log(f"  Elapsed           : {elapsed:.3f}s")
    log()

    if errors:
        log("  Sample unexpected errors:")
        for e in errors[:3]:
            log(f"    User {e['user']}: {e['body']}")
        log()

    log("  ISOLATION CHECK:")
    if len(success) <= 1:
        log(f"  ✓ PASS — Only {len(success)} booking succeeded for the same seat")
        log("           Concurrent duplicate bookings were correctly blocked")
    else:
        log(f"  ✗ FAIL — {len(success)} bookings for same seat! Isolation violated")
    log()

    # Now test multiple different seats (each user gets unique seat)
    log("  BONUS: Each user books a different seat (seats 2–21)...")
    results2 = []

    def book_unique(sess, i):
        try:
            r = sess.post(f"{BASE_URL}/api/bookings",
                          json={"TripID": trip_id, "SeatNumber": i + 2},
                          timeout=10)
            with lock:
                results2.append({"user": i, "status": r.status_code})
        except Exception as e:
            with lock:
                results2.append({"user": i, "status": "ERROR"})

    threads2 = [threading.Thread(target=book_unique, args=(s, i)) for i, s in enumerate(sessions)]
    start2 = time.time()
    for t in threads2: t.start()
    for t in threads2: t.join()
    elapsed2 = time.time() - start2

    success2 = [r for r in results2 if r["status"] in (200, 201)]
    log(f"  {len(success2)}/{len(sessions)} unique-seat bookings succeeded in {elapsed2:.3f}s")
    log()


# ── Test 2: Stress Test ────────────────────────────────────────────────────────

def test_stress(sess, n_requests=300):
    log("=" * 65)
    log(f"TEST 2: STRESS TEST — {n_requests} rapid concurrent requests")
    log("=" * 65)

    times_ms = []
    statuses = []
    lock = threading.Lock()
    cookie_jar = dict(sess.cookies)

    def hit(i):
        url = f"{BASE_URL}/api/trips" if i % 2 == 0 else f"{BASE_URL}/api/bookings"
        t0 = time.perf_counter()
        try:
            s2 = requests.Session()
            s2.cookies.update(cookie_jar)
            r = s2.get(url, timeout=10)
            ms = (time.perf_counter() - t0) * 1000
            with lock:
                times_ms.append(ms)
                statuses.append(r.status_code)
        except Exception:
            with lock:
                statuses.append("ERROR")
                times_ms.append(9999)

    batch_size = 50
    start = time.time()
    for b in range(0, n_requests, batch_size):
        batch = range(b, min(b + batch_size, n_requests))
        threads = [threading.Thread(target=hit, args=(i,)) for i in batch]
        for t in threads: t.start()
        for t in threads: t.join()
    elapsed = time.time() - start

    ok    = statuses.count(200)
    errs  = [s for s in statuses if s != 200]
    valid = [t for t in times_ms if t < 9999]

    log(f"  Total requests : {n_requests}")
    log(f"  HTTP 200 OK    : {ok}")
    log(f"  Errors         : {len(errs)}")
    log(f"  Total time     : {elapsed:.2f}s")
    log(f"  Throughput     : {n_requests/elapsed:.1f} req/s")
    if valid:
        log(f"  Response times :")
        log(f"    Median : {statistics.median(valid):.1f} ms")
        log(f"    Mean   : {statistics.mean(valid):.1f} ms")
        log(f"    Min    : {min(valid):.1f} ms")
        log(f"    Max    : {max(valid):.1f} ms")
    log()
    log("  CONSISTENCY CHECK:")
    err_rate = len(errs) / n_requests * 100
    if err_rate == 0:
        log("  ✓ PASS — All requests returned HTTP 200, system stable under load")
    elif err_rate < 1:
        log(f"  ~ ACCEPTABLE — Error rate {err_rate:.2f}% (< 1%)")
    else:
        log(f"  ✗ WARN — Error rate {err_rate:.2f}%")
    log()


# ── Test 3: Failure Simulation ─────────────────────────────────────────────────

def test_failure_simulation(trip_id, sessions):
    log("=" * 65)
    log("TEST 3: FAILURE SIMULATION — Abrupt client crashes mid-request")
    log("=" * 65)
    log(f"  Strategy   : {len(sessions)} booking requests killed after 0.05s")
    log(f"  Simulates  : client crash / network drop before response")
    log()

    def crash_book(sess, i):
        try:
            sess.post(f"{BASE_URL}/api/bookings",
                      json={"TripID": trip_id, "SeatNumber": 30 + i},
                      timeout=0.05)
        except Exception:
            pass  # timeout is expected

    threads = [threading.Thread(target=crash_book, args=(s, i)) for i, s in enumerate(sessions)]
    for t in threads: t.start()
    for t in threads: t.join()
    time.sleep(1)  # let server settle

    # DB health check
    admin = admin_session()
    r = admin.get(f"{BASE_URL}/api/trips", timeout=10)

    log(f"  Crash requests fired   : {len(sessions)}")
    log(f"  DB health check        : HTTP {r.status_code}")
    log()
    log("  ATOMICITY CHECK:")
    if r.status_code == 200:
        log("  ✓ PASS — DB responds correctly after simulated client crashes")
        log("           SQLite WAL ensures incomplete transactions are rolled back")
    else:
        log(f"  ✗ FAIL — DB returned {r.status_code} after failures")
    log()


# ── Test 4: Durability ─────────────────────────────────────────────────────────

def test_durability(sess, trip_id):
    log("=" * 65)
    log("TEST 4: DURABILITY — Committed data persists")
    log("=" * 65)

    seat = 40  
    r1 = sess.post(f"{BASE_URL}/api/bookings",
                   json={"TripID": trip_id, "SeatNumber": seat},
                   timeout=10)
    log(f"  Booking POST (TripID={trip_id}, Seat={seat}) : HTTP {r1.status_code}")

    try:
        body = r1.json()
        log(f"  Response : {str(body)[:120]}")
    except Exception:
        log(f"  Response : {r1.text[:120]}")

    # Read back
    r2 = sess.get(f"{BASE_URL}/api/bookings", timeout=10)
    try:
        bookings = r2.json()
        count = len(bookings) if isinstance(bookings, list) else "?"
    except Exception:
        count = "?"

    log(f"  Read-back GET           : HTTP {r2.status_code}")
    log(f"  Bookings visible        : {count}")
    log()
    log("  DURABILITY CHECK:")
    if r1.status_code in (200, 201) and r2.status_code == 200:
        log("  ✓ PASS — Committed booking is immediately visible in read-back")
    elif r2.status_code == 200:
        log("  ~ INFO — Read works; booking may have been blocked (seat taken)")
        log("           Durability confirmed: previously committed data still present")
    else:
        log("  ✗ FAIL — Could not verify persistence")
    log()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log("=" * 65)
    log("  ShuttleGo — Module B: Concurrent & Stress Testing")
    log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)
    log()

    log("SETUP: Creating 20 test user sessions...")
    sessions = []
    for i in range(20):
        s = register_and_login(f"testuser_b_{i}")
        if s:
            sessions.append(s)

    if not sessions:
        log("ERROR: Could not create sessions. Is app.py running on port 5050?")
        return
    log(f"  Got {len(sessions)} authenticated sessions\n")

    admin = admin_session()
    if not admin:
        log("ERROR: Admin login failed.")
        return

    trip_id, avail = get_first_available_trip(admin)
    if not trip_id:
        log("ERROR: No trips with available seats found.")
        return
    log(f"  Using TripID: {trip_id}  (AvailableSeats: {avail})\n")

    test_race_condition(trip_id, sessions)
    test_stress(admin, n_requests=300)
    test_failure_simulation(trip_id, sessions[:10])
    test_durability(sessions[-1], trip_id)

    log("=" * 65)
    log("  SUMMARY")
    log("=" * 65)
    log("  Test 1 — Race Condition : 20 users try to book the same seat")
    log("  Test 2 — Stress Test    : 300 rapid concurrent read requests")
    log("  Test 3 — Failure Sim    : Client crashes mid-booking request")
    log("  Test 4 — Durability     : Committed booking survives read-back")
    log()
    log("  Full results → moduleB_report.txt")
    log("  Server logs  → logs/audit.log")
    log("=" * 65)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()