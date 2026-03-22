import sqlite3
import random
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime

DB_PATH = "shuttlego.db"

# ══════════════════════════════════════════════
#  Name Pools — Gender Aware
# ══════════════════════════════════════════════

MALE_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh",
    "Ayaan", "Krishna", "Ishaan", "Shaurya", "Atharv", "Advik", "Pranav",
    "Advait", "Rahul", "Rohit", "Amit", "Vikram", "Nikhil", "Karan",
    "Raj", "Suresh", "Ramesh", "Dinesh", "Manish", "Girish", "Lokesh",
    "Mahesh", "Naresh", "Paresh", "Rakesh", "Satish", "Umesh", "Harish",
    "Jignesh", "Kamlesh", "Nilesh", "Rajesh", "Parth", "Devraj",
    "Bhavesh", "Chirag", "Darshan", "Falgun", "Gaurav", "Hemant",
    "Ishan", "Jayesh", "Kalpesh", "Lalit", "Maulik", "Neel", "Omkar"
]

FEMALE_FIRST_NAMES = [
    "Divya", "Ananya", "Priya", "Sneha", "Pooja", "Riya", "Shruti",
    "Kavya", "Meera", "Neha", "Simran", "Tanvi", "Isha", "Anjali",
    "Deepika", "Aarti", "Bhavna", "Chitra", "Geeta", "Hema",
    "Indira", "Jyoti", "Komal", "Lata", "Madhuri", "Nisha",
    "Poonam", "Rekha", "Seema", "Uma", "Varsha", "Sunita",
    "Radha", "Parul", "Namrata", "Mansi", "Kinjal", "Hiral",
    "Foram", "Dhara", "Chandni", "Bhumika", "Avni", "Asmita"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Shah", "Mehta",
    "Joshi", "Desai", "Verma", "Malhotra", "Kapoor", "Reddy", "Nair",
    "Iyer", "Pillai", "Menon", "Rao", "Shetty", "Bhat", "Kulkarni",
    "Jain", "Agarwal", "Saxena", "Mishra", "Tiwari", "Pandey", "Dubey",
    "Chauhan", "Bansal", "Bhatt", "Chaudhary", "Dixit", "Gandhi",
    "Trivedi", "Parikh", "Modi", "Thakur", "Yadav", "Naik",
    "Parekh", "Dalal", "Kothari", "Shukla", "Rastogi", "Mathur"
]


# ══════════════════════════════════════════════
#  Utility Functions
# ══════════════════════════════════════════════

def random_date(start_year=2024, end_year=2026):
    start = date(start_year, 1, 1)
    end   = date(end_year, 3, 19)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def random_phone():
    prefix = random.choice(['6', '7', '8', '9'])
    rest   = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"+91{prefix}{rest}"

def random_departure_time():
    hour   = random.randint(6, 21)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}:{minute:02d}:00"

def arrival_from_departure(dep_time_str, duration_minutes):
    h, m, s = map(int, dep_time_str.split(':'))
    dep = datetime(2000, 1, 1, h, m, s)
    arr = dep + timedelta(minutes=int(duration_minutes))
    if arr.day > 1:
        arr = datetime(2000, 1, 1, 23, 59, 0)
    return arr.strftime("%H:%M:%S")

def time_to_minutes(t_str):
    h, m, s = map(int, t_str.split(':'))
    return h * 60 + m

def is_busy(schedule, date_str, entity_id, dep, arr):
    if date_str not in schedule:
        return False
    if entity_id not in schedule[date_str]:
        return False
    dep_m = time_to_minutes(dep)
    arr_m = time_to_minutes(arr)
    for (existing_dep, existing_arr) in schedule[date_str][entity_id]:
        ed = time_to_minutes(existing_dep)
        ea = time_to_minutes(existing_arr)
        if not (arr_m + 15 <= ed or dep_m >= ea + 15):
            return True
    return False

def mark_busy(schedule, date_str, entity_id, dep, arr):
    if date_str not in schedule:
        schedule[date_str] = {}
    if entity_id not in schedule[date_str]:
        schedule[date_str][entity_id] = []
    schedule[date_str][entity_id].append((dep, arr))


# ══════════════════════════════════════════════
#  PART 1 — Generate Members, Users, Group Mappings
# ══════════════════════════════════════════════

def generate_members(n=500):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur  = conn.cursor()

    max_member    = cur.execute("SELECT MAX(MemberID) FROM Member").fetchone()[0] or 0
    max_passenger = cur.execute("SELECT MAX(PassengerID) FROM Passenger").fetchone()[0] or 0
    max_driver    = cur.execute("SELECT MAX(DriverID) FROM Driver").fetchone()[0] or 0
    max_user      = cur.execute("SELECT MAX(UserID) FROM users").fetchone()[0] or 0
    max_mapping   = cur.execute("SELECT MAX(MappingID) FROM group_mappings").fetchone()[0] or 0

    existing_emails    = set(r[0] for r in cur.execute("SELECT Email FROM Member").fetchall())
    existing_usernames = set(r[0] for r in cur.execute("SELECT username FROM users").fetchall())

    # FIX #3 — use werkzeug so all hashes are consistent with init_db.py and app.py login
    default_pass = generate_password_hash('user123')

    member_id    = max_member    + 1
    passenger_id = max_passenger + 1
    driver_id    = max_driver    + 1
    user_id      = max_user      + 1
    mapping_id   = max_mapping   + 1
    inserted     = 0

    print(f"\nGenerating {n} realistic members...")

    for i in range(n):

        member_type = 'Passenger' if random.random() < 0.8 else 'Driver'

        if member_type == 'Driver':
            gender = random.choices(['Male', 'Female'], weights=[90, 10])[0]
        else:
            gender = random.choices(['Male', 'Female'], weights=[55, 45])[0]

        if gender == 'Male':
            first = random.choice(MALE_FIRST_NAMES)
        else:
            first = random.choice(FEMALE_FIRST_NAMES)

        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"

        age      = random.randint(21, 58) if member_type == 'Driver' else random.randint(18, 65)
        email    = f"{first.lower()}.{last.lower()}{member_id}@email.com"
        while email in existing_emails:
            email = f"{first.lower()}.{last.lower()}{member_id}_{random.randint(1, 999)}@email.com"
        existing_emails.add(email)

        contact  = random_phone()
        reg_date = str(random_date(2022, 2026))

        cur.execute("""
            INSERT OR IGNORE INTO Member
            (MemberID, Name, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate)
            VALUES (?,?,?,?,?,?,?,?)
        """, (member_id, name, age, gender, email, contact, member_type, reg_date))

        if member_type == 'Passenger':
            payment    = random.choice(['UPI', 'UPI', 'Card', 'Wallet', 'Cash'])
            notif      = random.choice(['SMS', 'Email', 'App', 'All'])
            assistance = random.choice([None, None, None, None, 'Wheelchair', 'Elderly'])
            emergency  = random_phone()

            cur.execute("""
                INSERT OR IGNORE INTO Passenger
                (PassengerID, MemberID, EmergencyContact, PreferredPaymentMethod,
                 SpecialAssistance, NotificationPreference, Status_)
                VALUES (?,?,?,?,?,?,?)
            """, (passenger_id, member_id, emergency, payment, assistance, notif, 'Active'))

            group = 'passenger_group'
            passenger_id += 1

        else:
            license_no = f"DL{random.randint(10,99)}{random.randint(2015,2023)}{member_id:04d}"
            expiry     = str(random_date(2026, 2032))
            experience = random.randint(2, 25)
            rating     = round(max(3.0, min(5.0, random.gauss(4.3, 0.4))), 2)
            drv_status = random.choices(
                ['Available', 'On-Trip', 'Off-Duty'], weights=[60, 30, 10]
            )[0]

            cur.execute("""
                INSERT OR IGNORE INTO Driver
                (DriverID, MemberID, LicenseNumber, LicenseExpiryDate,
                 ExperienceYears, Rating, Status_)
                VALUES (?,?,?,?,?,?,?)
            """, (driver_id, member_id, license_no, expiry, experience, rating, drv_status))

            group = 'driver_group'
            driver_id += 1

        username = f"{first.lower()}_{member_id}"
        while username in existing_usernames:
            username = f"{first.lower()}_{member_id}_{random.randint(1, 99)}"
        existing_usernames.add(username)

        cur.execute("""
            INSERT OR IGNORE INTO users (UserID, username, password_hash, role, MemberID)
            VALUES (?,?,?,?,?)
        """, (user_id, username, default_pass, 'user', member_id))

        cur.execute("""
            INSERT OR IGNORE INTO group_mappings (MappingID, UserID, group_name)
            VALUES (?,?,?)
        """, (mapping_id, user_id, group))

        member_id  += 1
        user_id    += 1
        mapping_id += 1
        inserted   += 1

        if inserted % 50 == 0:
            conn.commit()
            print(f"  {inserted} members inserted...")

    conn.commit()
    conn.close()

    print(f"  Members done — {inserted} inserted.")
    print(f"  Approx passengers added : {int(inserted * 0.8)}")
    print(f"  Approx drivers added    : {int(inserted * 0.2)}")
    print(f"  Users added             : {inserted}")


# ══════════════════════════════════════════════
#  PART 2 — Generate Trips, Bookings, Transactions
# ══════════════════════════════════════════════

def generate_trips_and_bookings(n_trips=1000, max_bookings_per_trip=12):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur  = conn.cursor()

    routes     = cur.execute("SELECT RouteID, EstimatedDuration, BaseFare FROM Route").fetchall()
    route_info = {r[0]: {"duration": r[1], "base_fare": float(r[2])} for r in routes}
    route_ids  = list(route_info.keys())

    vehicles     = cur.execute("SELECT VehicleID, Capacity FROM Vehicle WHERE CurrentStatus='Active'").fetchall()
    vehicle_info = {v[0]: v[1] for v in vehicles}
    vehicle_ids  = list(vehicle_info.keys())

    driver_ids    = [r[0] for r in cur.execute("SELECT DriverID FROM Driver").fetchall()]
    passenger_ids = [r[0] for r in cur.execute("SELECT PassengerID FROM Passenger").fetchall()]

    max_trip    = cur.execute("SELECT MAX(TripID) FROM Trip").fetchone()[0] or 0
    max_booking = cur.execute("SELECT MAX(BookingID) FROM Booking").fetchone()[0] or 0
    max_trans   = cur.execute('SELECT MAX(TransactionID) FROM "Transaction"').fetchone()[0] or 0

    trip_id    = max_trip    + 1
    booking_id = max_booking + 1
    trans_id   = max_trans   + 1

    driver_schedule  = {}
    vehicle_schedule = {}

    trips_inserted    = 0
    bookings_inserted = 0
    today             = date.today()

    print(f"\nGenerating {n_trips} realistic trips with bookings...")

    for i in range(n_trips):

        trip_date  = str(random_date(2024, 2026))
        route_id   = random.choice(route_ids)
        duration   = route_info[route_id]["duration"]
        base_fare  = route_info[route_id]["base_fare"]
        dep_time   = random_departure_time()
        arr_time   = arrival_from_departure(dep_time, duration)
        capacity   = 0

        random.shuffle(vehicle_ids)
        vehicle_id = None
        for v in vehicle_ids:
            if not is_busy(vehicle_schedule, trip_date, v, dep_time, arr_time):
                vehicle_id = v
                capacity   = vehicle_info[v]
                break
        if vehicle_id is None:
            vehicle_id = random.choice(vehicle_ids)
            capacity   = vehicle_info[vehicle_id]

        random.shuffle(driver_ids)
        driver_id = None
        for d in driver_ids:
            if not is_busy(driver_schedule, trip_date, d, dep_time, arr_time):
                driver_id = d
                break
        if driver_id is None:
            driver_id = random.choice(driver_ids)

        mark_busy(driver_schedule,  trip_date, driver_id,  dep_time, arr_time)
        mark_busy(vehicle_schedule, trip_date, vehicle_id, dep_time, arr_time)

        td = date.fromisoformat(trip_date)
        if td < today:
            status = random.choices(['Completed', 'Cancelled'], weights=[85, 15])[0]
        elif td == today:
            status = random.choices(['InProgress', 'Scheduled'], weights=[60, 40])[0]
        else:
            status = random.choices(['Scheduled', 'Cancelled'], weights=[95, 5])[0]

        total_seats     = capacity
        available_seats = random.randint(0, total_seats)

        cur.execute("""
            INSERT OR IGNORE INTO Trip
            (TripID, RouteID, VehicleID, DriverID, TripDate,
             ScheduledDepartureTime, ScheduledArrivalTime,
             Status_, TotalSeats, AvailableSeats)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (trip_id, route_id, vehicle_id, driver_id, trip_date,
              dep_time, arr_time, status, total_seats, available_seats))

        trips_inserted += 1
        seats_taken = set()
        n_bookings  = random.randint(3, min(max_bookings_per_trip, total_seats))
        sampled_passengers = random.sample(passenger_ids, min(n_bookings, len(passenger_ids)))

        for passenger_id in sampled_passengers:
            seat     = random.randint(1, total_seats)
            attempts = 0
            while seat in seats_taken and attempts < 20:
                seat = random.randint(1, total_seats)
                attempts += 1
            if seat in seats_taken:
                continue
            seats_taken.add(seat)

            if status == 'Completed':
                bk_status = random.choices(['Completed','NoShow','Cancelled'], weights=[80,10,10])[0]
            elif status == 'Cancelled':
                bk_status = 'Cancelled'
            elif status == 'InProgress':
                bk_status = random.choices(['Confirmed','NoShow'], weights=[90,10])[0]
            else:
                bk_status = random.choices(['Confirmed','Cancelled'], weights=[85,15])[0]

            fare    = round(base_fare * random.uniform(0.9, 1.1), 2)
            bk_time = f"{trip_date} {dep_time[:5]}:00"
            qr_code = f"QR-T{trip_id}-S{seat}-P{passenger_id}-{booking_id}"

            cur.execute("""
                INSERT OR IGNORE INTO Booking
                (BookingID, PassengerID, TripID, SeatNumber, BookingTime,
                 BookingStatus, FareAmount, QRCode, QRCodeURL, VerificationStatus)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (booking_id, passenger_id, trip_id, seat, bk_time,
                  bk_status, fare, qr_code, f"https://shuttle.qr/{qr_code}", "Pending"))

            if bk_status == 'Cancelled':
                trans_type, pay_status, trans_amount = 'Refund', 'Success', round(fare * 0.8, 2)
            elif bk_status == 'NoShow':
                trans_type, pay_status, trans_amount = 'Penalty', random.choice(['Pending','Paid']), round(fare * 0.2, 2)
            else:
                trans_type, pay_status, trans_amount = 'Payment', 'Success', fare

            payment_method = random.choices(['UPI','Card','Wallet','Cash'], weights=[50,25,15,10])[0]

            cur.execute("""
                INSERT OR IGNORE INTO "Transaction"
                (TransactionID, BookingID, TransactionType, Amount,
                 TransactionDate, PaymentMethod, PaymentStatus)
                VALUES (?,?,?,?,?,?,?)
            """, (trans_id, booking_id, trans_type, trans_amount,
                  bk_time, payment_method, pay_status))

            booking_id += 1
            trans_id   += 1
            bookings_inserted += 1

        trip_id += 1

        if trips_inserted % 100 == 0:
            conn.commit()
            print(f"  {trips_inserted} trips, {bookings_inserted} bookings inserted...")

    conn.commit()
    conn.close()

    print(f"  Trips done.")
    print(f"  Trips inserted        : {trips_inserted}")
    print(f"  Bookings inserted     : {bookings_inserted}")
    print(f"  Transactions inserted : {bookings_inserted}")


# ══════════════════════════════════════════════
#  PART 3 — Generate Booking Cancellations
# ══════════════════════════════════════════════

def generate_cancellations():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur  = conn.cursor()

    max_cancel = cur.execute("SELECT MAX(CancellationID) FROM BookingCancellation").fetchone()[0] or 0
    cancelled  = cur.execute("""
        SELECT b.BookingID, b.FareAmount, b.BookingTime
        FROM Booking b
        LEFT JOIN BookingCancellation bc ON b.BookingID = bc.BookingID
        WHERE b.BookingStatus = 'Cancelled' AND bc.CancellationID IS NULL
    """).fetchall()

    cancel_id = max_cancel + 1
    inserted  = 0

    reasons = [
        "Changed travel plans", "Medical emergency", "Work schedule conflict",
        "Found alternative transport", "Duplicate booking", "Personal reasons",
        "Family emergency", "Not feeling well", "Booked wrong date",
        "Trip postponed", "Changed destination", "Weather concerns"
    ]

    print(f"\nGenerating cancellation records for {len(cancelled)} cancelled bookings...")

    for booking_id, fare, bk_time in cancelled:
        fare          = float(fare)
        penalty       = round(fare * random.uniform(0.05, 0.25), 2)
        refund        = round(fare - penalty, 2)
        reason        = random.choice(reasons)

        cur.execute("""
            INSERT OR IGNORE INTO BookingCancellation
            (CancellationID, BookingID, CancellationTime, CancellationReason,
             RefundAmount, PenaltyAmount, ProcessedAt, Status_)
            VALUES (?,?,?,?,?,?,?,?)
        """, (cancel_id, booking_id, bk_time, reason, refund, penalty, bk_time, 'Processed'))

        cancel_id += 1
        inserted  += 1

        if inserted % 500 == 0:
            conn.commit()
            print(f"  {inserted} cancellations inserted...")

    conn.commit()
    conn.close()
    print(f"  Cancellations done — {inserted} inserted.")


# ══════════════════════════════════════════════
#  PART 4 — Generate Driver Assignments
# ══════════════════════════════════════════════

def generate_driver_assignments():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur  = conn.cursor()

    max_assign = cur.execute("SELECT MAX(AssignmentID) FROM DriverAssignment").fetchone()[0] or 0
    trips      = cur.execute("""
        SELECT t.TripID, t.DriverID, t.VehicleID,
               t.TripDate, t.ScheduledDepartureTime, t.ScheduledArrivalTime, t.Status_
        FROM Trip t
        LEFT JOIN DriverAssignment da ON t.TripID = da.TripID
        WHERE da.AssignmentID IS NULL
    """).fetchall()

    assign_id = max_assign + 1
    inserted  = 0

    print(f"\nGenerating driver assignments for {len(trips)} trips...")

    for (trip_id, driver_id, vehicle_id,
         trip_date, dep_time, arr_time, status) in trips:

        dep_h, dep_m, dep_s = map(int, dep_time.split(':'))
        shift_start_dt = datetime(2000, 1, 1, dep_h, dep_m) - timedelta(minutes=30)
        shift_start    = shift_start_dt.strftime("%H:%M:%S")

        arr_h, arr_m, arr_s = map(int, arr_time.split(':'))
        shift_end_dt = datetime(2000, 1, 1, arr_h, arr_m) + timedelta(minutes=30)
        if shift_end_dt.day > 1:
            shift_end_dt = datetime(2000, 1, 1, 23, 59, 0)
        shift_end = shift_end_dt.strftime("%H:%M:%S")

        assign_status = {
            'Completed': 'Completed', 'Cancelled': 'Cancelled'
        }.get(status, 'Assigned')

        cur.execute("""
            INSERT OR IGNORE INTO DriverAssignment
            (AssignmentID, DriverID, VehicleID, TripID,
             AssignedDate, ShiftStart, ShiftEnd, Status_)
            VALUES (?,?,?,?,?,?,?,?)
        """, (assign_id, driver_id, vehicle_id, trip_id,
              trip_date, shift_start, shift_end, assign_status))

        assign_id += 1
        inserted  += 1

        if inserted % 500 == 0:
            conn.commit()
            print(f"  {inserted} assignments inserted...")

    conn.commit()
    conn.close()
    print(f"  Driver assignments done — {inserted} inserted.")


# ══════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════

def print_summary():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    tables = [
        "Member", "Passenger", "Driver", "Vehicle",
        "Route", "Trip", "Booking", '"Transaction"',
        "BookingCancellation", "DriverAssignment",
        "users", "group_mappings"
    ]

    print("\n" + "=" * 40)
    print("  FINAL ROW COUNTS")
    print("=" * 40)
    for table in tables:
        count   = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        display = table.replace('"', '')
        print(f"  {display:<25} {count:>6} rows")
    print("=" * 40)

    conn.close()


if __name__ == "__main__":
    print("ShuttleGo — Realistic Data Generator")
    print("=" * 40)

    generate_members(n=500)
    generate_trips_and_bookings(n_trips=1000, max_bookings_per_trip=12)
    generate_cancellations()
    generate_driver_assignments()
    print_summary()
