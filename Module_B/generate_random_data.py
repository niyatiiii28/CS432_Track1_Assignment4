import random
from werkzeug.security import generate_password_hash
from datetime import date, timedelta, datetime
import mysql.connector

# =========================
# SHARD CONFIG
# =========================
HOST = "10.0.116.184"
USER = "Infobase"
PASSWORD = "password@123"
DATABASE = "Infobase"

SHARD_PORTS = [3307, 3308, 3309]

# =========================
# CONNECTION HELPERS
# =========================
def get_connection(port):
    return mysql.connector.connect(
        host=HOST,
        port=port,
        user=USER,
        password=PASSWORD,
        database=DATABASE
    )

# Create persistent connections (IMPORTANT)
shards = [get_connection(p) for p in SHARD_PORTS]

def get_shard(member_id):
    return shards[member_id % 3]

def get_shard_by_passenger(pid):
    return shards[pid % 3]


# ══════════════════════════════════════════════
#  Name Pools — Gender Aware (UNCHANGED)
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

def random_date(start_year=2024, end_year=2026):
    start = date(start_year, 1, 1)
    end   = date(end_year, 3, 19)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_phone():
    prefix = random.choice(['6', '7', '8', '9'])
    rest   = ''.join(str(random.randint(0, 9)) for _ in range(9))
    return f"+91{prefix}{rest}"


def random_departure_time():
    hour   = random.randint(6, 21)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}:{minute:02d}:00"


def arrival_from_departure(dep_time_str, duration_minutes):
    h, m, s = map(int, dep_time_str.split(':'))
    dep = datetime(2000, 1, 1, h, m, s)
    arr = dep + timedelta(minutes=int(duration_minutes))

    # prevent overflow to next day (your original logic preserved)
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

        # ensure 15 min buffer between trips (your original logic preserved)
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

    print(f"\nGenerating {n} realistic members (SHARDED)...")

    # =========================
    # GLOBAL MAX ID FETCH (ALL SHARDS)
    # =========================
    max_member = max_passenger = max_driver = max_user = max_mapping = 0
    existing_emails = set()
    existing_usernames = set()

    for conn in shards:
        cur = conn.cursor()

        # ---- SAFE MAX FETCH ----
        cur.execute("SELECT MAX(MemberID) FROM Member")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_member = max(max_member, res[0])

        cur.execute("SELECT MAX(PassengerID) FROM Passenger")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_passenger = max(max_passenger, res[0])

        cur.execute("SELECT MAX(DriverID) FROM Driver")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_driver = max(max_driver, res[0])

        cur.execute("SELECT MAX(UserID) FROM users")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_user = max(max_user, res[0])

        cur.execute("SELECT MAX(MappingID) FROM group_mappings")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_mapping = max(max_mapping, res[0])

        # ---- EXISTING DATA ----
        cur.execute("SELECT Email FROM Member")
        rows = cur.fetchall()
        existing_emails.update(r[0] for r in rows)

        cur.execute("SELECT username FROM users")
        rows = cur.fetchall()
        existing_usernames.update(r[0] for r in rows)

    # =========================
    # INITIAL IDS
    # =========================
    member_id    = max_member + 1
    passenger_id = max_passenger + 1
    driver_id    = max_driver + 1
    user_id      = max_user + 1
    mapping_id   = max_mapping + 1

    inserted = 0
    default_pass = generate_password_hash('user123')

    # =========================
    # MAIN LOOP
    # =========================
    for _ in range(n):

        member_type = 'Passenger' if random.random() < 0.8 else 'Driver'

        # ---- GENDER LOGIC ----
        if member_type == 'Driver':
            gender = random.choices(['Male', 'Female'], weights=[90, 10])[0]
        else:
            gender = random.choices(['Male', 'Female'], weights=[55, 45])[0]

        first = random.choice(MALE_FIRST_NAMES if gender == 'Male' else FEMALE_FIRST_NAMES)
        last  = random.choice(LAST_NAMES)
        name  = f"{first} {last}"

        age = random.randint(21, 58) if member_type == 'Driver' else random.randint(18, 65)

        # =========================
        # UNIQUE EMAIL
        # =========================
        email = f"{first.lower()}.{last.lower()}{member_id}@email.com"
        while email in existing_emails:
            email = f"{first.lower()}.{last.lower()}{member_id}_{random.randint(1,999)}@email.com"
        existing_emails.add(email)

        contact  = random_phone()
        reg_date = str(random_date(2022, 2026))

        # =========================
        # SHARD ROUTING
        # =========================
        conn = get_shard(member_id)
        cur  = conn.cursor()

        # =========================
        # MEMBER INSERT
        # =========================
        cur.execute("""
            INSERT IGNORE INTO Member
            (MemberID, Name, Age, Gender, Email, ContactNumber, MemberType, RegistrationDate)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (member_id, name, age, gender, email, contact, member_type, reg_date))

        # =========================
        # PASSENGER / DRIVER
        # =========================
        if member_type == 'Passenger':
            payment    = random.choice(['UPI','UPI','Card','Wallet','Cash'])
            notif      = random.choice(['SMS','Email','App','All'])
            assistance = random.choice([None,None,None,None,'Wheelchair','Elderly'])
            emergency  = random_phone()

            cur.execute("""
                INSERT IGNORE INTO Passenger
                (PassengerID, MemberID, EmergencyContact, PreferredPaymentMethod,
                 SpecialAssistance, NotificationPreference, Status_)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (passenger_id, member_id, emergency, payment, assistance, notif, 'Active'))

            group = 'passenger_group'
            passenger_id += 1

        else:
            license_no = f"DL{random.randint(10,99)}{random.randint(2015,2023)}{member_id:04d}"
            expiry     = str(random_date(2026, 2032))
            experience = random.randint(2, 25)
            rating     = round(max(3.0, min(5.0, random.gauss(4.3, 0.4))), 2)
            drv_status = random.choices(['Available','On-Trip','Off-Duty'], weights=[60,30,10])[0]

            cur.execute("""
                INSERT IGNORE INTO Driver
                (DriverID, MemberID, LicenseNumber, LicenseExpiryDate,
                 ExperienceYears, Rating, Status_)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (driver_id, member_id, license_no, expiry, experience, rating, drv_status))

            group = 'driver_group'
            driver_id += 1

        # =========================
        # UNIQUE USERNAME
        # =========================
        username = f"{first.lower()}_{member_id}"
        while username in existing_usernames:
            username = f"{first.lower()}_{member_id}_{random.randint(1,99)}"
        existing_usernames.add(username)

        cur.execute("""
            INSERT IGNORE INTO users (UserID, username, password_hash, role, MemberID)
            VALUES (%s,%s,%s,%s,%s)
        """, (user_id, username, default_pass, 'user', member_id))

        cur.execute("""
            INSERT IGNORE INTO group_mappings (MappingID, UserID, group_name)
            VALUES (%s,%s,%s)
        """, (mapping_id, user_id, group))

        conn.commit()

        member_id  += 1
        user_id    += 1
        mapping_id += 1
        inserted   += 1

        if inserted % 50 == 0:
            print(f"  {inserted} members inserted...")

    print(f"  Members done — {inserted} inserted.")
    print(f"  Approx passengers added : {int(inserted * 0.8)}")
    print(f"  Approx drivers added    : {int(inserted * 0.2)}")
    print(f"  Users added             : {inserted}")

# ══════════════════════════════════════════════
#  PART 2 — Generate Trips, Bookings, Transactions
# ══════════════════════════════════════════════

def generate_trips_and_bookings(n_trips=1000, max_bookings_per_trip=12):

    # =========================
    # GLOBAL TABLES → shard 0
    # =========================
    conn = shards[0]
    cur  = conn.cursor()

    cur.execute("SELECT RouteID, EstimatedDuration, BaseFare FROM Route")
    routes = cur.fetchall()
    route_info = {r[0]: {"duration": r[1], "base_fare": float(r[2])} for r in routes}
    route_ids  = list(route_info.keys())

    cur.execute("SELECT VehicleID, Capacity FROM Vehicle WHERE CurrentStatus='Active'")
    vehicles = cur.fetchall()
    vehicle_info = {v[0]: v[1] for v in vehicles}
    vehicle_ids  = list(vehicle_info.keys())

    # =========================
    # DRIVERS + PASSENGERS FROM ALL SHARDS
    # =========================
    driver_ids = []
    passenger_ids = []

    max_booking = 0
    max_trans   = 0

    for sconn in shards:
        scur = sconn.cursor()

        # =========================
        # FETCH DRIVERS
        # =========================
        scur.execute("SELECT DriverID FROM Driver")
        driver_rows = scur.fetchall()
        driver_ids.extend([r[0] for r in driver_rows])

        # =========================
        # FETCH PASSENGERS
        # =========================
        scur.execute("SELECT PassengerID FROM Passenger")
        passenger_rows = scur.fetchall()
        passenger_ids.extend([r[0] for r in passenger_rows])

        # =========================
        # MAX BOOKING ID
        # =========================
        scur.execute("SELECT MAX(BookingID) FROM Booking")
        result = scur.fetchone()
        if result and result[0] is not None:
            max_booking = max(max_booking, result[0])

        # =========================
        # MAX TRANSACTION ID
        # =========================
        scur.execute("SELECT MAX(TransactionID) FROM `Transaction`")
        result = scur.fetchone()
        if result and result[0] is not None:
            max_trans = max(max_trans, result[0])
    # =========================
    # TRIP IDs (global)
    # =========================
    cur.execute("SELECT MAX(TripID) FROM Trip")
    result = cur.fetchone()
    max_trip = result[0] if result and result[0] is not None else 0

    trip_id    = max_trip + 1
    booking_id = max_booking + 1
    trans_id   = max_trans + 1

    driver_schedule  = {}
    vehicle_schedule = {}

    trips_inserted    = 0
    bookings_inserted = 0
    today             = date.today()

    print(f"\nGenerating {n_trips} realistic trips with bookings (SHARDED)...")

    # =========================
    # MAIN LOOP
    # =========================
    for _ in range(n_trips):

        trip_date = str(random_date(2024, 2026))
        route_id  = random.choice(route_ids)

        duration  = route_info[route_id]["duration"]
        base_fare = route_info[route_id]["base_fare"]

        dep_time = random_departure_time()
        arr_time = arrival_from_departure(dep_time, duration)

        # =========================
        # VEHICLE SELECTION
        # =========================
        random.shuffle(vehicle_ids)
        vehicle_id = None
        capacity   = 0

        for v in vehicle_ids:
            if not is_busy(vehicle_schedule, trip_date, v, dep_time, arr_time):
                vehicle_id = v
                capacity   = vehicle_info[v]
                break

        if vehicle_id is None:
            vehicle_id = random.choice(vehicle_ids)
            capacity   = vehicle_info[vehicle_id]

        # =========================
        # DRIVER SELECTION
        # =========================
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

        # =========================
        # STATUS LOGIC (UNCHANGED)
        # =========================
        td = date.fromisoformat(trip_date)

        if td < today:
            status = random.choices(['Completed', 'Cancelled'], weights=[85, 15])[0]
        elif td == today:
            status = random.choices(['InProgress', 'Scheduled'], weights=[60, 40])[0]
        else:
            status = random.choices(['Scheduled', 'Cancelled'], weights=[95, 5])[0]

        total_seats     = capacity
        available_seats = random.randint(0, total_seats)

        # =========================
        # INSERT TRIP (GLOBAL)
        # =========================
        cur.execute("""
            INSERT IGNORE INTO Trip
            (TripID, RouteID, VehicleID, DriverID, TripDate,
             ScheduledDepartureTime, ScheduledArrivalTime,
             Status_, TotalSeats, AvailableSeats)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (trip_id, route_id, vehicle_id, driver_id, trip_date,
              dep_time, arr_time, status, total_seats, available_seats))

        trips_inserted += 1

        # =========================
        # BOOKINGS (SHARDED)
        # =========================
        seats_taken = set()
        n_bookings  = random.randint(3, min(max_bookings_per_trip, total_seats))
        sampled_passengers = random.sample(passenger_ids, min(n_bookings, len(passenger_ids)))

        for passenger_id in sampled_passengers:

            conn_b = get_shard_by_passenger(passenger_id)
            cur_b  = conn_b.cursor()

            seat = random.randint(1, total_seats)
            attempts = 0

            while seat in seats_taken and attempts < 20:
                seat = random.randint(1, total_seats)
                attempts += 1

            if seat in seats_taken:
                continue

            seats_taken.add(seat)

            # STATUS LOGIC SAME
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

            # =========================
            # INSERT BOOKING (CORRECT SHARD)
            # =========================
            cur_b.execute("""
                INSERT IGNORE INTO Booking
                (BookingID, PassengerID, TripID, SeatNumber, BookingTime,
                 BookingStatus, FareAmount, QRCode, QRCodeURL, VerificationStatus)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (booking_id, passenger_id, trip_id, seat, bk_time,
                  bk_status, fare, qr_code, f"https://shuttle.qr/{qr_code}", "Pending"))

            # =========================
            # TRANSACTION (SAME SHARD)
            # =========================
            if bk_status == 'Cancelled':
                trans_type, pay_status, trans_amount = 'Refund', 'Success', round(fare * 0.8, 2)
            elif bk_status == 'NoShow':
                trans_type, pay_status, trans_amount = 'Penalty', random.choice(['Pending','Paid']), round(fare * 0.2, 2)
            else:
                trans_type, pay_status, trans_amount = 'Payment', 'Success', fare

            payment_method = random.choices(['UPI','Card','Wallet','Cash'], weights=[50,25,15,10])[0]

            cur_b.execute("""
                INSERT IGNORE INTO `Transaction`
                (TransactionID, BookingID, TransactionType, Amount,
                 TransactionDate, PaymentMethod, PaymentStatus)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (trans_id, booking_id, trans_type, trans_amount,
                  bk_time, payment_method, pay_status))

            conn_b.commit()

            booking_id += 1
            trans_id   += 1
            bookings_inserted += 1

        trip_id += 1

        if trips_inserted % 100 == 0:
            conn.commit()
            print(f"  {trips_inserted} trips, {bookings_inserted} bookings inserted...")

    conn.commit()

    print(f"  Trips done.")
    print(f"  Trips inserted        : {trips_inserted}")
    print(f"  Bookings inserted     : {bookings_inserted}")
    print(f"  Transactions inserted : {bookings_inserted}")

# ══════════════════════════════════════════════
#  PART 3 — Generate Booking Cancellations
# ══════════════════════════════════════════════

def generate_cancellations():

    print("\nGenerating cancellation records (SHARDED)...")

    # =========================
    # GLOBAL MAX ID (ALL SHARDS)
    # =========================
    max_cancel = 0

    for conn in shards:
        cur = conn.cursor()
        cur.execute("SELECT MAX(CancellationID) FROM BookingCancellation")
        res = cur.fetchone()
        if res and res[0] is not None:
            max_cancel = max(max_cancel, res[0])

    cancel_id = max_cancel + 1
    inserted  = 0

    # =========================
    # COLLECT CANCELLED BOOKINGS FROM ALL SHARDS
    # =========================
    cancelled_records = []

    for conn in shards:
        cur = conn.cursor()

        cur.execute("""
            SELECT b.BookingID, b.FareAmount, b.BookingTime
            FROM Booking b
            LEFT JOIN BookingCancellation bc ON b.BookingID = bc.BookingID
            WHERE b.BookingStatus = 'Cancelled'
              AND bc.CancellationID IS NULL
        """)

        cancelled_records.extend(cur.fetchall())

    # =========================
    # REASONS (UNCHANGED)
    # =========================
    reasons = [
        "Changed travel plans", "Medical emergency", "Work schedule conflict",
        "Found alternative transport", "Duplicate booking", "Personal reasons",
        "Family emergency", "Not feeling well", "Booked wrong date",
        "Trip postponed", "Changed destination", "Weather concerns"
    ]

    print(f"  Found {len(cancelled_records)} cancelled bookings to process...")

    # =========================
    # INSERT LOOP (PER SHARD)
    # =========================
    for booking_id, fare, bk_time in cancelled_records:

        fare    = float(fare)
        penalty = round(fare * random.uniform(0.05, 0.25), 2)
        refund  = round(fare - penalty, 2)
        reason  = random.choice(reasons)

        # 🔥 ROUTE TO CORRECT SHARD
        # (booking lives on one shard → cancellation must go there)
        target_conn = None

        for conn in shards:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM Booking WHERE BookingID=%s LIMIT 1", (booking_id,))
            if cur.fetchone():
                target_conn = conn
                break

        if target_conn is None:
            continue  # safety (should not happen)

        cur = target_conn.cursor()

        cur.execute("""
            INSERT IGNORE INTO BookingCancellation
            (CancellationID, BookingID, CancellationTime, CancellationReason,
             RefundAmount, PenaltyAmount, ProcessedAt, Status_)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            cancel_id,
            booking_id,
            bk_time,
            reason,
            refund,
            penalty,
            bk_time,
            'Processed'
        ))

        target_conn.commit()

        cancel_id += 1
        inserted  += 1

        if inserted % 500 == 0:
            print(f"  {inserted} cancellations inserted...")

    print(f"  Cancellations done — {inserted} inserted.")


# ══════════════════════════════════════════════
#  PART 4 — Generate Driver Assignments
# ══════════════════════════════════════════════

def generate_driver_assignments():

    print("\nGenerating driver assignments (GLOBAL)...")

    # =========================
    # GLOBAL TABLE → shard 0
    # =========================
    conn = shards[0]
    cur  = conn.cursor()

    # =========================
    # GLOBAL MAX ID
    # =========================
    cur.execute("SELECT MAX(AssignmentID) FROM DriverAssignment")
    res = cur.fetchone()
    max_assign = res[0] if res and res[0] is not None else 0

    # =========================
    # FETCH TRIPS WITHOUT ASSIGNMENTS
    # =========================
    cur.execute("""
        SELECT t.TripID, t.DriverID, t.VehicleID,
               t.TripDate, t.ScheduledDepartureTime,
               t.ScheduledArrivalTime, t.Status_
        FROM Trip t
        LEFT JOIN DriverAssignment da ON t.TripID = da.TripID
        WHERE da.AssignmentID IS NULL
    """)

    trips = cur.fetchall()

    assign_id = max_assign + 1
    inserted  = 0

    print(f"  Found {len(trips)} trips needing assignments...")

    # =========================
    # HELPER (DEFINE ONCE)
    # =========================
    def to_time_str(t):
        if isinstance(t, timedelta):
            total_seconds = int(t.total_seconds())
            h = total_seconds // 3600
            m = (total_seconds % 3600) // 60
            s = total_seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        return str(t)

    # =========================
    # MAIN LOOP
    # =========================
    for (trip_id, driver_id, vehicle_id,
         trip_date, dep_time, arr_time, status) in trips:

        # =========================
        # SAFE TIME CONVERSION
        # =========================
        dep_time = to_time_str(dep_time)
        arr_time = to_time_str(arr_time)

        # =========================
        # SHIFT START (-30 min)
        # =========================
        dep_h, dep_m, dep_s = map(int, dep_time.split(':'))
        shift_start_dt = datetime(2000, 1, 1, dep_h, dep_m) - timedelta(minutes=30)
        shift_start = shift_start_dt.strftime("%H:%M:%S")

        # =========================
        # SHIFT END (+30 min)
        # =========================
        arr_h, arr_m, arr_s = map(int, arr_time.split(':'))
        shift_end_dt = datetime(2000, 1, 1, arr_h, arr_m) + timedelta(minutes=30)

        # prevent overflow
        if shift_end_dt.day > 1:
            shift_end_dt = datetime(2000, 1, 1, 23, 59, 0)

        shift_end = shift_end_dt.strftime("%H:%M:%S")

        # =========================
        # STATUS MAPPING
        # =========================
        assign_status = {
            'Completed': 'Completed',
            'Cancelled': 'Cancelled'
        }.get(status, 'Assigned')

        # =========================
        # INSERT
        # =========================
        cur.execute("""
            INSERT IGNORE INTO DriverAssignment
            (AssignmentID, DriverID, VehicleID, TripID,
             AssignedDate, ShiftStart, ShiftEnd, Status_)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            assign_id,
            driver_id,
            vehicle_id,
            trip_id,
            trip_date,
            shift_start,
            shift_end,
            assign_status
        ))

        assign_id += 1
        inserted  += 1

        if inserted % 500 == 0:
            conn.commit()
            print(f"  {inserted} assignments inserted...")

    conn.commit()

    print(f"  Driver assignments done — {inserted} inserted.")
# ══════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════

def print_summary():

    print("\n" + "=" * 40)
    print("  FINAL ROW COUNTS (SHARDED)")
    print("=" * 40)

    # =========================
    # TABLE CATEGORIES
    # =========================
    sharded_tables = [
        "Member", "Passenger", "Driver",
        "Booking", "`Transaction`",
        "BookingCancellation",
        "users", "group_mappings"
    ]

    global_tables = [
        "Vehicle", "Route", "Trip", "DriverAssignment"
    ]

    # =========================
    # SHARDED TABLES (SUM)
    # =========================
    for table in sharded_tables:
        total = 0

        for conn in shards:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            total += cur.fetchone()[0]

        display = table.replace("`", "")
        print(f"  {display:<25} {total:>6} rows")

    # =========================
    # GLOBAL TABLES (SHARD 0)
    # =========================
    conn = shards[0]
    cur  = conn.cursor()

    for table in global_tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table:<25} {count:>6} rows")

    print("=" * 40)

if __name__ == "__main__":
    print("ShuttleGo — Realistic Data Generator")
    print("=" * 40)

    generate_members(n=500)
    generate_trips_and_bookings(n_trips=1000, max_bookings_per_trip=12)
    generate_cancellations()
    generate_driver_assignments()
    print_summary()
