-- ==========================================================
-- Organ and Blood Donation Management System
-- Complete MySQL Database Schema Script
-- ==========================================================

CREATE DATABASE IF NOT EXISTS `organdonar` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `organdonar`;

-- 1. Admins Table
CREATE TABLE IF NOT EXISTS `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(60) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `phone` VARCHAR(15) NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) DEFAULT 'System Administrator',
    `security_keyword` VARCHAR(100) NOT NULL,
    `role` VARCHAR(20) DEFAULT 'SuperAdmin',
    `last_login` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Cities Autocomplete Table
CREATE TABLE IF NOT EXISTS `cities` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name_en` VARCHAR(100) NOT NULL,
    `name_ta` VARCHAR(100) NOT NULL,
    `state` VARCHAR(100) DEFAULT 'Tamil Nadu',
    `latitude` DECIMAL(10, 6) DEFAULT 0.000000,
    `longitude` DECIMAL(10, 6) DEFAULT 0.000000
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Organ Donors Table
CREATE TABLE IF NOT EXISTS `donors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `donor_id` VARCHAR(30) NOT NULL UNIQUE,
    `full_name` VARCHAR(120) NOT NULL,
    `age` INT NOT NULL,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL,
    `phone` VARCHAR(15) NOT NULL UNIQUE,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `organ_type` VARCHAR(255) NOT NULL,
    `address` TEXT NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `medical_history` TEXT NULL,
    `availability_status` ENUM('Available', 'Unavailable', 'Pledged') DEFAULT 'Available',
    `photo_url` VARCHAR(255) DEFAULT '/static/img/default-avatar.png',
    `qr_code_url` VARCHAR(255) NULL,
    `pdf_url` VARCHAR(255) NULL,
    `status` ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Approved',
    `is_phone_verified` TINYINT(1) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_blood_organ` (`blood_group`, `status`),
    INDEX `idx_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Organ Receivers Table
CREATE TABLE IF NOT EXISTS `receivers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `receiver_id` VARCHAR(30) NOT NULL UNIQUE,
    `name` VARCHAR(120) NOT NULL,
    `age` INT NOT NULL,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL,
    `phone` VARCHAR(15) NOT NULL,
    `email` VARCHAR(120) NOT NULL,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `needed_organ` VARCHAR(100) NOT NULL,
    `address` TEXT NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `emergency_level` ENUM('Low', 'Medium', 'High', 'Critical') DEFAULT 'High',
    `contact_number` VARCHAR(15) NOT NULL,
    `status` ENUM('Pending', 'Approved', 'Matched', 'Closed') DEFAULT 'Pending',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_needed_organ` (`needed_organ`, `blood_group`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Receiver Health Reports Table
CREATE TABLE IF NOT EXISTS `health_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `receiver_id` INT NOT NULL,
    `report_type` ENUM('Blood Test', 'ECG Report', 'Scan Report', 'Medical Certificate', 'Other') NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_size` INT DEFAULT 0,
    `uploaded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_health_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `receivers`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Blood Donors Table
CREATE TABLE IF NOT EXISTS `blood_donors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `blood_donor_id` VARCHAR(30) NOT NULL UNIQUE,
    `full_name` VARCHAR(120) NOT NULL,
    `age` INT NOT NULL,
    `gender` ENUM('Male', 'Female', 'Other') NOT NULL,
    `phone` VARCHAR(15) NOT NULL UNIQUE,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `last_donation_date` DATE NULL,
    `address` TEXT NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `availability_status` ENUM('Available', 'Unavailable') DEFAULT 'Available',
    `photo_url` VARCHAR(255) DEFAULT '/static/img/default-avatar.png',
    `status` ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Approved',
    `is_phone_verified` TINYINT(1) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_bld_group` (`blood_group`, `availability_status`, `status`),
    INDEX `idx_bld_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Blood Requests Table
CREATE TABLE IF NOT EXISTS `blood_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `request_id` VARCHAR(30) NOT NULL UNIQUE,
    `patient_name` VARCHAR(120) NOT NULL,
    `blood_group` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    `units_required` INT NOT NULL DEFAULT 1,
    `hospital_name` VARCHAR(150) NOT NULL,
    `city` VARCHAR(100) NOT NULL,
    `emergency_level` ENUM('Normal', 'Urgent', 'Critical') DEFAULT 'Urgent',
    `contact_number` VARCHAR(15) NOT NULL,
    `status` ENUM('Pending', 'Matched', 'Fulfilled', 'Cancelled') DEFAULT 'Pending',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_req_blood` (`blood_group`, `city`, `emergency_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Matches Table
CREATE TABLE IF NOT EXISTS `matches` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `match_type` ENUM('organ', 'blood') NOT NULL,
    `receiver_id` INT NULL,
    `donor_id` INT NULL,
    `blood_request_id` INT NULL,
    `blood_donor_id` INT NULL,
    `match_score` DECIMAL(5, 2) NOT NULL,
    `compatibility_details` TEXT NULL,
    `status` ENUM('Suggested', 'Initiated', 'Approved', 'Completed', 'Rejected') DEFAULT 'Suggested',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. OTP Verifications Table
CREATE TABLE IF NOT EXISTS `otp_verifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `phone_or_email` VARCHAR(120) NOT NULL,
    `otp_code` VARCHAR(64) NOT NULL,
    `purpose` VARCHAR(50) DEFAULT 'donor_registration',
    `attempts` INT DEFAULT 0,
    `max_attempts` INT DEFAULT 5,
    `expires_at` DATETIME NOT NULL,
    `is_verified` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_otp_search` (`phone_or_email`, `purpose`, `is_verified`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Password Reset Requests
CREATE TABLE IF NOT EXISTS `password_reset` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `admin_id` INT NOT NULL,
    `token` VARCHAR(100) NOT NULL UNIQUE,
    `otp_code` VARCHAR(64) NOT NULL,
    `expires_at` DATETIME NOT NULL,
    `is_used` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_reset_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. System Notifications Table
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_type` ENUM('admin', 'donor', 'receiver', 'blood_donor', 'public') DEFAULT 'admin',
    `user_identifier` VARCHAR(120) NULL,
    `title_en` VARCHAR(150) NOT NULL,
    `title_ta` VARCHAR(150) NOT NULL,
    `message_en` TEXT NOT NULL,
    `message_ta` TEXT NOT NULL,
    `type` ENUM('info', 'success', 'warning', 'emergency') DEFAULT 'info',
    `is_read` TINYINT(1) DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed Admin Account
INSERT INTO `admins` (`username`, `email`, `phone`, `password_hash`, `full_name`, `security_keyword`, `role`) VALUES
('admin', 'organdonation@gmail.com', '9876543210', 'pbkdf2:sha256:260000$o7Q9P4vV8A2bK1mC$0f171d0bfa85834b6e5944510b0f7aeeb038bc2be2a7b8e5c14cfab6932454f7', 'Chief Medical Administrator', 'LIFESAVER2026', 'SuperAdmin')
ON DUPLICATE KEY UPDATE `username`=`username`;

-- Seed Cities
INSERT INTO `cities` (`name_en`, `name_ta`, `state`, `latitude`, `longitude`) VALUES
('Chennai', 'சென்னை', 'Tamil Nadu', 13.0827, 80.2707),
('Coimbatore', 'கோயம்புத்தூர்', 'Tamil Nadu', 11.0168, 76.9558),
('Madurai', 'மதுரை', 'Tamil Nadu', 9.9252, 78.1198),
('Trichy', 'திருச்சிராப்பள்ளி', 'Tamil Nadu', 10.7905, 78.7047),
('Salem', 'சேலம்', 'Tamil Nadu', 11.6643, 78.1460),
('Erode', 'ஈரோடு', 'Tamil Nadu', 11.3410, 77.7172),
('Tirunelveli', 'திருநெல்வேலி', 'Tamil Nadu', 8.7139, 77.7567),
('Vellore', 'வேலூர்', 'Tamil Nadu', 12.9165, 79.1325),
('Thanjavur', 'தஞ்சாவூர்', 'Tamil Nadu', 10.7870, 79.1378),
('Dindigul', 'திண்டுக்கல்', 'Tamil Nadu', 10.3673, 77.9803),
('Tiruppur', 'திருப்பூர்', 'Tamil Nadu', 11.1085, 77.3411),
('Kanchipuram', 'காஞ்சிபுரம்', 'Tamil Nadu', 12.8342, 79.7036),
('Nagercoil', 'நாகர்கோவில்', 'Tamil Nadu', 8.1833, 77.4119),
('Cuddalore', 'கடலூர்', 'Tamil Nadu', 11.7480, 79.7714),
('Karur', 'கரூர்', 'Tamil Nadu', 10.9601, 78.0766),
('Hosur', 'ஓசூர்', 'Tamil Nadu', 12.7409, 77.8253),
('Bengaluru', 'பெங்களூரு', 'Karnataka', 12.9716, 77.5946),
('Kochi', 'கொச்சி', 'Kerala', 9.9312, 76.2673),
('Hyderabad', 'ஹைதராபாத்', 'Telangana', 17.3850, 78.4867)
ON DUPLICATE KEY UPDATE `name_en`=`name_en`;
