-- ============================================================
--  ShuttleGo — SQL Indexing Strategy (SubTask 4)
--  Apply AFTER schema.sql has been run and data is seeded.
-- ============================================================

-- ──────────────────────────────────────────────
--  1. Users table
--  Used in: every /login call and every RBAC lookup
--  Query:  WHERE username = ?          → login
--          WHERE UserID = ?            → token-to-MemberID resolution
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_username  ON Users(username);
CREATE INDEX IF NOT EXISTS idx_users_member_id ON Users(MemberID);

-- ──────────────────────────────────────────────
--  2. Booking table
--  Used in: /bookings, /transactions (passenger scoping)
--  Query:  WHERE PassengerID = ?       → passenger's own bookings
--          WHERE TripID = ?            → trip's booking list
--          ORDER BY BookingTime DESC   → recent bookings first
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_booking_passenger_id ON Booking(PassengerID);
CREATE INDEX IF NOT EXISTS idx_booking_trip_id       ON Booking(TripID);
CREATE INDEX IF NOT EXISTS idx_booking_time          ON Booking(BookingTime DESC);

-- ──────────────────────────────────────────────
--  3. Trip table
--  Used in: /trips (most-hit public endpoint)
--  Query:  ORDER BY TripDate DESC, ScheduledDepartureTime
--          JOIN Route, Vehicle, Driver  → RouteID, VehicleID, DriverID used
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_trip_date        ON Trip(TripDate DESC);
CREATE INDEX IF NOT EXISTS idx_trip_route_id    ON Trip(RouteID);
CREATE INDEX IF NOT EXISTS idx_trip_driver_id   ON Trip(DriverID);
CREATE INDEX IF NOT EXISTS idx_trip_vehicle_id  ON Trip(VehicleID);

-- ──────────────────────────────────────────────
--  4. Transaction table
--  Used in: /transactions (admin: ORDER BY date; passenger: JOIN Booking)
--  Query:  ORDER BY TransactionDate DESC
--          JOIN Booking ON t.BookingID = b.BookingID WHERE b.PassengerID = ?
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_transaction_booking_id ON "Transaction"(BookingID);
CREATE INDEX IF NOT EXISTS idx_transaction_date       ON "Transaction"(TransactionDate DESC);

-- ──────────────────────────────────────────────
--  5. Driver table
--  Used in: /drivers, trip JOINs, RBAC self-check
--  Query:  WHERE MemberID = ?    → driver's own profile lookup
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_driver_member_id ON Driver(MemberID);

-- ──────────────────────────────────────────────
--  6. Passenger table
--  Used in: /passengers, booking JOINs, RBAC self-check
--  Query:  WHERE MemberID = ?    → passenger's own profile lookup
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_passenger_member_id ON Passenger(MemberID);

-- ──────────────────────────────────────────────
--  7. DriverAssignment table
--  Used in: trip scheduling, driver workload queries
--  Query:  WHERE DriverID = ?  /  WHERE TripID = ?
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_assignment_driver_id ON DriverAssignment(DriverID);
CREATE INDEX IF NOT EXISTS idx_assignment_trip_id   ON DriverAssignment(TripID);

-- ──────────────────────────────────────────────
--  8. BookingCancellation table
--  Used in: cancellation lookups by BookingID
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cancellation_booking_id ON BookingCancellation(BookingID);
