-- ============================================================
-- ShuttleGo — MySQL Indexing (FIXED)
-- ============================================================

-- 1. USERS
CREATE INDEX idx_users_username  ON users(username);
CREATE INDEX idx_users_member_id ON users(MemberID);

-- 2. BOOKING
CREATE INDEX idx_booking_passenger_id ON Booking(PassengerID);
CREATE INDEX idx_booking_trip_id      ON Booking(TripID);
CREATE INDEX idx_booking_time         ON Booking(BookingTime);

-- 3. TRIP
CREATE INDEX idx_trip_date        ON Trip(TripDate);
CREATE INDEX idx_trip_route_id    ON Trip(RouteID);
CREATE INDEX idx_trip_driver_id   ON Trip(DriverID);
CREATE INDEX idx_trip_vehicle_id  ON Trip(VehicleID);

-- 4. TRANSACTION
CREATE INDEX idx_transaction_booking_id ON `Transaction`(BookingID);
CREATE INDEX idx_transaction_date       ON `Transaction`(TransactionDate);

-- 5. DRIVER
CREATE INDEX idx_driver_member_id ON Driver(MemberID);

-- 6. PASSENGER
CREATE INDEX idx_passenger_member_id ON Passenger(MemberID);

-- 7. DRIVER ASSIGNMENT
CREATE INDEX idx_assignment_driver_id ON DriverAssignment(DriverID);
CREATE INDEX idx_assignment_trip_id   ON DriverAssignment(TripID);

-- 8. BOOKING CANCELLATION
CREATE INDEX idx_cancellation_booking_id ON BookingCancellation(BookingID);