-- ============================================================
-- ShuttleGo — FINAL SCHEMA (ALL TABLES PRESERVED)
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS NoShowPenalty;
DROP TABLE IF EXISTS BookingCancellation;
DROP TABLE IF EXISTS `Transaction`;
DROP TABLE IF EXISTS Booking;
DROP TABLE IF EXISTS DriverAssignment;
DROP TABLE IF EXISTS TripOccupancyLog;
DROP TABLE IF EXISTS Trip;
DROP TABLE IF EXISTS Route;
DROP TABLE IF EXISTS VehicleMaintenance;
DROP TABLE IF EXISTS VehicleLiveLocation;
DROP TABLE IF EXISTS Vehicle;
DROP TABLE IF EXISTS Driver;
DROP TABLE IF EXISTS Passenger;
DROP TABLE IF EXISTS group_mappings;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS Member;

SET FOREIGN_KEY_CHECKS = 1;

-- =========================
-- MEMBER
-- =========================
CREATE TABLE Member (
    MemberID INT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Image VARCHAR(255),
    Age INT NOT NULL,
    Gender VARCHAR(10),
    Email VARCHAR(100) NOT NULL UNIQUE,
    ContactNumber VARCHAR(15) NOT NULL,
    MemberType ENUM('Passenger','Driver') NOT NULL,
    RegistrationDate DATE NOT NULL
) ENGINE=InnoDB;

-- =========================
-- USERS
-- =========================
CREATE TABLE users (
    UserID INT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role ENUM('admin','user') NOT NULL,
    MemberID INT UNIQUE,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- GROUP MAPPINGS
-- =========================
CREATE TABLE group_mappings (
    MappingID INT PRIMARY KEY,
    UserID INT NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (UserID) REFERENCES users(UserID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- PASSENGER
-- =========================
CREATE TABLE Passenger (
    PassengerID INT PRIMARY KEY,
    MemberID INT NOT NULL UNIQUE,
    EmergencyContact VARCHAR(15),
    PreferredPaymentMethod VARCHAR(20) NOT NULL,
    SpecialAssistance VARCHAR(100),
    NotificationPreference ENUM('SMS','Email','App','All') NOT NULL,
    Status_ ENUM('Active','Inactive','Suspended') NOT NULL,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- DRIVER
-- =========================
CREATE TABLE Driver (
    DriverID INT PRIMARY KEY,
    MemberID INT NOT NULL UNIQUE,
    LicenseNumber VARCHAR(30) NOT NULL UNIQUE,
    LicenseExpiryDate DATE NOT NULL,
    ExperienceYears INT NOT NULL,
    Rating DECIMAL(3,2) DEFAULT 0.00,
    Status_ ENUM('Off-Duty','Available','On-Trip') NOT NULL,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- VEHICLE
-- =========================
CREATE TABLE Vehicle (
    VehicleID INT PRIMARY KEY,
    VehicleNumber VARCHAR(20) NOT NULL UNIQUE,
    Model VARCHAR(50) NOT NULL,
    Capacity INT NOT NULL,
    CurrentStatus ENUM('Active','Maintenance','OutOfService') NOT NULL,
    GPSDeviceID VARCHAR(50),
    RegistrationDate DATE NOT NULL
) ENGINE=InnoDB;

-- =========================
-- VEHICLE LIVE LOCATION
-- =========================
CREATE TABLE VehicleLiveLocation (
    LocationID INT PRIMARY KEY,
    VehicleID INT NOT NULL,
    Latitude DECIMAL(9,6) NOT NULL,
    Longitude DECIMAL(9,6) NOT NULL,
    Timestamp TIMESTAMP NOT NULL,
    Speed DECIMAL(5,2),
    FOREIGN KEY (VehicleID) REFERENCES Vehicle(VehicleID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- VEHICLE MAINTENANCE
-- =========================
CREATE TABLE VehicleMaintenance (
    MaintenanceID INT PRIMARY KEY,
    VehicleID INT NOT NULL,
    ServiceDate DATE NOT NULL,
    ServiceType VARCHAR(50) NOT NULL,
    Cost DECIMAL(8,2) NOT NULL,
    NextServiceDue DATE NOT NULL,
    Status_ ENUM('Scheduled','Completed','Pending') NOT NULL,
    FOREIGN KEY (VehicleID) REFERENCES Vehicle(VehicleID) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =========================
-- ROUTE
-- =========================
CREATE TABLE Route (
    RouteID INT PRIMARY KEY,
    RouteName VARCHAR(100) NOT NULL,
    Source VARCHAR(50) NOT NULL,
    Destination VARCHAR(50) NOT NULL,
    IntermediateStops TEXT,
    EstimatedDuration INT NOT NULL,
    DistanceKM DECIMAL(6,2) NOT NULL,
    BaseFare DECIMAL(8,2) NOT NULL,
    Status_ ENUM('Active','Inactive') NOT NULL
) ENGINE=InnoDB;

-- =========================
-- TRIP
-- =========================
CREATE TABLE Trip (
    TripID INT PRIMARY KEY,
    RouteID INT NOT NULL,
    VehicleID INT NOT NULL,
    DriverID INT NOT NULL,
    TripDate DATE NOT NULL,
    ScheduledDepartureTime TIME NOT NULL,
    ScheduledArrivalTime TIME NOT NULL,
    ActualDepartureTime TIME,
    ActualArrivalTime TIME,
    Status_ ENUM('Scheduled','InProgress','Completed','Cancelled') NOT NULL,
    TotalSeats INT NOT NULL,
    AvailableSeats INT NOT NULL,
    FOREIGN KEY (RouteID) REFERENCES Route(RouteID),
    FOREIGN KEY (VehicleID) REFERENCES Vehicle(VehicleID),
    FOREIGN KEY (DriverID) REFERENCES Driver(DriverID)
) ENGINE=InnoDB;

-- =========================
-- TRIP OCCUPANCY LOG
-- =========================
CREATE TABLE TripOccupancyLog (
    LogID INT PRIMARY KEY,
    TripID INT NOT NULL,
    LogTimestamp TIMESTAMP NOT NULL,
    OccupiedSeats INT NOT NULL,
    AvailableSeats INT NOT NULL,
    FOREIGN KEY (TripID) REFERENCES Trip(TripID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =========================
-- DRIVER ASSIGNMENT
-- =========================
CREATE TABLE DriverAssignment (
    AssignmentID INT PRIMARY KEY,
    DriverID INT NOT NULL,
    VehicleID INT NOT NULL,
    TripID INT NOT NULL,
    AssignedDate DATE NOT NULL,
    ShiftStart TIME NOT NULL,
    ShiftEnd TIME NOT NULL,
    Status_ ENUM('Assigned','Completed','Cancelled') NOT NULL,
    FOREIGN KEY (DriverID) REFERENCES Driver(DriverID),
    FOREIGN KEY (VehicleID) REFERENCES Vehicle(VehicleID),
    FOREIGN KEY (TripID) REFERENCES Trip(TripID)
) ENGINE=InnoDB;

-- =========================
-- BOOKING
-- =========================
CREATE TABLE Booking (
    BookingID INT PRIMARY KEY,
    PassengerID INT NOT NULL,
    TripID INT NOT NULL,
    SeatNumber INT NOT NULL,
    BookingTime TIMESTAMP NOT NULL,
    BookingStatus ENUM('Confirmed','Cancelled','NoShow','Completed') NOT NULL,
    FareAmount DECIMAL(8,2) NOT NULL,
    QRCode TEXT NOT NULL,
    QRCodeURL VARCHAR(255),
    VerificationStatus ENUM('Pending','Verified','Invalid') NOT NULL,
    VerifiedAt TIMESTAMP,
    VerifiedBy INT,
    UNIQUE (TripID, SeatNumber),
    FOREIGN KEY (PassengerID) REFERENCES Passenger(PassengerID),
    FOREIGN KEY (TripID) REFERENCES Trip(TripID),
    FOREIGN KEY (VerifiedBy) REFERENCES Driver(DriverID)
) ENGINE=InnoDB;

-- =========================
-- TRANSACTION
-- =========================
CREATE TABLE `Transaction` (
    TransactionID INT PRIMARY KEY,
    BookingID INT NOT NULL,
    TransactionType ENUM('Payment','Refund','Penalty') NOT NULL,
    Amount DECIMAL(8,2) NOT NULL,
    TransactionDate TIMESTAMP NOT NULL,
    PaymentMethod ENUM('Card','UPI','Wallet','Cash') NOT NULL,
    PaymentStatus ENUM('Pending','Success','Failed') NOT NULL,
    GatewayReference VARCHAR(100),
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID)
) ENGINE=InnoDB;

-- =========================
-- BOOKING CANCELLATION
-- =========================
CREATE TABLE BookingCancellation (
    CancellationID INT PRIMARY KEY,
    BookingID INT NOT NULL,
    CancellationTime TIMESTAMP NOT NULL,
    CancellationReason VARCHAR(200) NOT NULL,
    RefundAmount DECIMAL(8,2) NOT NULL,
    PenaltyAmount DECIMAL(8,2) NOT NULL,
    ProcessedAt TIMESTAMP,
    Status_ ENUM('Pending','Processed','Rejected') NOT NULL,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID)
) ENGINE=InnoDB;

-- =========================
-- NO SHOW PENALTY
-- =========================
CREATE TABLE NoShowPenalty (
    PenaltyID INT PRIMARY KEY,
    BookingID INT NOT NULL,
    DetectionTime TIMESTAMP NOT NULL,
    PenaltyAmount DECIMAL(8,2) NOT NULL,
    Reason VARCHAR(200) NOT NULL,
    AutoGenerated TINYINT(1) NOT NULL,
    PaymentStatus ENUM('Pending','Paid','Waived') NOT NULL,
    WaivedBy INT,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID)
) ENGINE=InnoDB;


-- ── Infrastructure seed data (not people-dependent) ────────────────────────

INSERT INTO Vehicle (VehicleID, VehicleNumber, Model, Capacity, CurrentStatus, GPSDeviceID, RegistrationDate) VALUES
(1,  'GJ01AB1234', 'Tata Starbus',         40, 'Active',      'GPS001', '2022-03-15'),
(2,  'GJ01AB1235', 'Ashok Leyland Viking', 45, 'Active',      'GPS002', '2022-04-20'),
(3,  'GJ01AB1236', 'Tata Starbus',         40, 'Active',      'GPS003', '2022-05-10'),
(4,  'GJ01AB1237', 'Mercedes-Benz',        50, 'Active',      'GPS004', '2022-06-15'),
(5,  'GJ01AB1238', 'Tata Starbus',         40, 'Maintenance', 'GPS005', '2022-07-20'),
(6,  'GJ01AB1239', 'Ashok Leyland Viking', 45, 'Active',      'GPS006', '2022-08-25'),
(7,  'GJ01AB1240', 'Tata Starbus',         40, 'Active',      'GPS007', '2022-09-30'),
(8,  'GJ01AB1241', 'Mercedes-Benz',        50, 'Active',      'GPS008', '2022-10-15'),
(9,  'GJ01AB1242', 'Tata Starbus',         40, 'Active',      'GPS009', '2022-11-20'),
(10, 'GJ01AB1243', 'Ashok Leyland Viking', 45, 'Active',      'GPS010', '2022-12-10'),
(11, 'GJ01AB1244', 'Tata Starbus',         40, 'Active',      'GPS011', '2023-01-15'),
(12, 'GJ01AB1245', 'Mercedes-Benz',        50, 'Active',      'GPS012', '2023-02-20');

INSERT INTO VehicleLiveLocation (LocationID, VehicleID, Latitude, Longitude, Timestamp, Speed) VALUES
(1,  1,  23.0225, 72.5714, '2026-02-15 08:30:00', 45.5),
(2,  2,  23.0330, 72.5820, '2026-02-15 08:30:15', 50.2),
(3,  3,  23.0125, 72.5614, '2026-02-15 08:30:30', 42.8),
(4,  4,  23.0425, 72.5920, '2026-02-15 08:30:45', 48.3),
(5,  6,  23.0525, 72.6020, '2026-02-15 08:31:00', 51.7),
(6,  7,  23.0225, 72.5714, '2026-02-15 08:31:15', 44.9),
(7,  8,  23.0625, 72.6120, '2026-02-15 08:31:30', 47.6),
(8,  9,  23.0325, 72.5814, '2026-02-15 08:31:45', 49.1),
(9,  10, 23.0725, 72.6220, '2026-02-15 08:32:00', 46.4),
(10, 11, 23.0425, 72.5914, '2026-02-15 08:32:15', 43.2),
(11, 12, 23.0825, 72.6320, '2026-02-15 08:32:30', 52.8),
(12, 1,  23.0250, 72.5730, '2026-02-15 08:35:00', 46.2),
(13, 2,  23.0360, 72.5850, '2026-02-15 08:35:15', 51.0),
(14, 3,  23.0140, 72.5630, '2026-02-15 08:35:30', 43.5);

INSERT INTO VehicleMaintenance (MaintenanceID, VehicleID, ServiceDate, ServiceType, Cost, NextServiceDue, Status_) VALUES
(1,  1,  '2026-01-15', 'Oil Change & Filter Replacement', 3500.00,  '2026-04-15', 'Completed'),
(2,  2,  '2026-01-20', 'Brake System Check',              5200.00,  '2026-04-20', 'Completed'),
(3,  3,  '2026-02-01', 'Tire Rotation & Alignment',       4100.00,  '2026-05-01', 'Completed'),
(4,  4,  '2026-02-05', 'AC System Service',               6800.00,  '2026-05-05', 'Completed'),
(5,  5,  '2026-02-10', 'Engine Overhaul',                 45000.00, '2026-05-10', 'Completed'),
(6,  6,  '2026-01-25', 'Suspension Check',                3900.00,  '2026-04-25', 'Completed'),
(7,  7,  '2026-01-30', 'Battery Replacement',             8500.00,  '2026-04-30', 'Completed'),
(8,  8,  '2026-02-02', 'Transmission Service',            12000.00, '2026-05-02', 'Completed'),
(9,  9,  '2026-02-08', 'General Inspection',              2500.00,  '2026-05-08', 'Completed'),
(10, 10, '2026-02-12', 'Oil Change & Filter Replacement', 3500.00,  '2026-05-12', 'Completed'),
(11, 11, '2026-01-28', 'Brake Pad Replacement',           7200.00,  '2026-04-28', 'Completed'),
(12, 12, '2026-02-03', 'AC System Service',               6800.00,  '2026-05-03', 'Completed'),
(13, 1,  '2026-04-15', 'Scheduled Maintenance',           4000.00,  '2026-07-15', 'Scheduled'),
(14, 2,  '2026-04-20', 'Scheduled Maintenance',           4500.00,  '2026-07-20', 'Scheduled');

INSERT INTO Route (RouteID, RouteName, Source, Destination, IntermediateStops, EstimatedDuration, DistanceKM, BaseFare, Status_) VALUES
(1,  'City Center Express',    'Gandhinagar Central', 'GIFT City',          'Sector 7, Kudasan Circle',            45, 18.5, 40.00,  'Active'),
(2,  'Tech Park Shuttle',      'Gandhinagar Bus Stand','Infocity',           'Sector 12, Koba Circle',              35, 12.3, 30.00,  'Active'),
(3,  'Heritage Route',         'Akshardham Temple',   'Adalaj Stepwell',    'Sector 20, Raysan',                   60, 25.7, 55.00,  'Active'),
(4,  'Airport Connector',      'Gandhinagar Central', 'Ahmedabad Airport',  'Koba, Adalaj',                        90, 42.5, 120.00, 'Active'),
(5,  'University Loop',        'Gujarat University',  'PDPU Campus',        'Sector 15, Raysan Village',           40, 15.8, 35.00,  'Active'),
(6,  'Industrial Zone',        'Sector 28',           'Vatva GIDC',         'Odhav, Narol',                        75, 32.4, 65.00,  'Active'),
(7,  'Metro Feeder',           'Gandhinagar Metro',   'Sector 21',          'Sector 11, Sector 16',                25,  8.9, 20.00,  'Active'),
(8,  'Shopping District',      'Alpha One Mall',      'Pakwan Circle',      'Sector 4, Kudasan',                   30, 11.2, 25.00,  'Active'),
(9,  'Hospital Express',       'Civil Hospital',      'Apollo Hospital',    'Sector 8, GMDC Ground',               50, 19.6, 45.00,  'Active'),
(10, 'Residential Connector',  'Sector 1',            'Sector 30',          'Sector 10, Sector 20, Sector 25',     55, 22.3, 50.00,  'Active');
