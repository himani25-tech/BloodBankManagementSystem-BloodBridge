-- ============================================================
--  BLOOD BANK MANAGEMENT SYSTEM  –  MySQL Schema & Seed Data
-- ============================================================

CREATE DATABASE IF NOT EXISTS blood_bank_db;
USE blood_bank_db;

-- ── Users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(100)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,
    phone       VARCHAR(15),
    blood_group VARCHAR(5),
    role        ENUM('admin','user') DEFAULT 'user',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Donors ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS donors (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    age           INT,
    gender        ENUM('Male','Female','Other'),
    blood_group   VARCHAR(5)   NOT NULL,
    phone         VARCHAR(15),
    email         VARCHAR(100),
    address       TEXT,
    city          VARCHAR(100),
    last_donation DATE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Blood Inventory ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blood_inventory (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    blood_group VARCHAR(5) NOT NULL UNIQUE,
    units       INT DEFAULT 0,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ── Inventory Log ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    blood_group  VARCHAR(5),
    units        INT,
    action       ENUM('add','remove'),
    performed_by VARCHAR(100),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Blood Requests ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS blood_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    patient_name  VARCHAR(100),
    blood_group   VARCHAR(5)   NOT NULL,
    units         INT          NOT NULL,
    hospital      VARCHAR(200),
    required_date DATE,
    urgency       ENUM('normal','urgent','critical') DEFAULT 'normal',
    notes         TEXT,
    status        ENUM('pending','approved','rejected') DEFAULT 'pending',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
--  SEED DATA
-- ============================================================

-- Admin user  (password: admin123)
INSERT IGNORE INTO users (name, email, password, phone, blood_group, role) VALUES
('Admin User',    'admin@bloodbank.com', SHA2('admin123', 256),  '9876543210', 'O+', 'admin'),
('Rahul Sharma',  'rahul@email.com',     SHA2('user123',  256),  '9123456780', 'A+', 'user'),
('Priya Patel',   'priya@email.com',     SHA2('user123',  256),  '9234567891', 'B+', 'user');

-- Blood inventory
INSERT IGNORE INTO blood_inventory (blood_group, units) VALUES
('A+',  45), ('A-',  12), ('B+',  38), ('B-',  8),
('AB+', 20), ('AB-',  5), ('O+',  55), ('O-', 15);

-- Sample donors
INSERT INTO donors (name, age, gender, blood_group, phone, email, address, city, last_donation) VALUES
('Amit Kumar',      28, 'Male',   'O+',  '9811223344', 'amit@email.com',   '12 MG Road',       'Indore',  '2024-10-15'),
('Sneha Joshi',     24, 'Female', 'A+',  '9922334455', 'sneha@email.com',  '45 Vijay Nagar',   'Indore',  '2024-09-20'),
('Rohit Singh',     35, 'Male',   'B+',  '9733445566', 'rohit@email.com',  '78 Palasia',       'Indore',  '2024-11-01'),
('Anjali Verma',    30, 'Female', 'AB+', '9644556677', 'anjali@email.com', '23 Rajwada',       'Bhopal',  '2024-08-10'),
('Vikram Gupta',    42, 'Male',   'O-',  '9555667788', 'vikram@email.com', '56 Scheme 54',     'Indore',  '2024-07-25'),
('Pooja Meena',     26, 'Female', 'B-',  '9466778899', 'pooja@email.com',  '90 Sukhliya',      'Indore',  '2024-10-30'),
('Suresh Yadav',    38, 'Male',   'A-',  '9377889900', 'suresh@email.com', '34 Bhawarkua',     'Ujjain',  '2024-06-15'),
('Kavita Sharma',   29, 'Female', 'AB-', '9288990011', 'kavita@email.com', '67 Rau',           'Indore',  '2024-09-05');

-- Sample blood requests
INSERT INTO blood_requests (user_id, patient_name, blood_group, units, hospital, required_date, urgency, notes, status) VALUES
(2, 'Ramesh Kumar',   'O+',  2, 'MY Hospital Indore',        '2025-04-30', 'urgent',   'Post-surgery requirement',   'pending'),
(3, 'Sita Patel',     'A+',  1, 'Bombay Hospital Indore',    '2025-05-01', 'normal',   'Scheduled transfusion',      'approved'),
(2, 'Gopal Sharma',   'B+',  3, 'CHL Hospital Indore',       '2025-04-28', 'critical', 'Accident case',              'pending'),
(3, 'Meena Verma',    'AB+', 1, 'Vishesh Hospital Indore',   '2025-05-05', 'normal',   '',                           'rejected');
