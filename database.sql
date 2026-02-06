-- ===============================
-- DATABASE
-- ===============================
CREATE DATABASE IF NOT EXISTS nexovate26;
USE nexovate26;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) UNIQUE NOT NULL,     -- NXAB12
    team_name VARCHAR(100),                  -- NULL for workshop-only
    leader_email VARCHAR(100) NOT NULL,

    registration_type ENUM(
        'technical',
        'technical_nontech',
        'technical_nontech_workshop',
        'workshop_only'
    ) NOT NULL,

    member_count INT NOT NULL,
    amount_paid INT DEFAULT 0,

    payment_status ENUM(
        'PENDING',
        'WAITING',
        'APPROVED'
    ) DEFAULT 'PENDING',

    transaction_id VARCHAR(50),

    certificate_enabled TINYINT DEFAULT 0,
    event_completed TINYINT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX (team_id),
    INDEX (leader_email)
);

CREATE TABLE members (
    id INT AUTO_INCREMENT PRIMARY KEY,

    team_id VARCHAR(20) NOT NULL,
    student_id VARCHAR(25) UNIQUE NOT NULL,   -- NXAB12-01

    member_name VARCHAR(100) NOT NULL,
    study_year VARCHAR(10) NOT NULL,
    department VARCHAR(100) NOT NULL,
    college_name VARCHAR(150) NOT NULL,

    phone VARCHAR(15) UNIQUE NOT NULL,
    college_email VARCHAR(100) UNIQUE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON DELETE CASCADE
);

CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(100) UNIQUE NOT NULL,
    category ENUM('technical','non_technical','workshop') NOT NULL,
    max_participants INT DEFAULT NULL   -- NULL = unlimited
);

INSERT INTO events (event_name, category, max_participants) VALUES
('Code Combat', 'technical', NULL),
('Design It Right', 'technical', NULL),
('Paper Presentation', 'technical', NULL),

('IPL Auction', 'non_technical', NULL),
('Cleverquest', 'non_technical', NULL),
('Bluff The Brain', 'non_technical', NULL),

('Figma Workshop', 'workshop', 30),
('AR / VR Workshop', 'workshop', 30);

CREATE TABLE team_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id VARCHAR(20) NOT NULL,
    event_name VARCHAR(100) NOT NULL,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON DELETE CASCADE,

    FOREIGN KEY (event_name)
        REFERENCES events(event_name)
        ON DELETE CASCADE
);

CREATE TABLE workshop_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,

    member_id INT NOT NULL,
    workshop_name VARCHAR(100) NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (member_id)
        REFERENCES members(id)
        ON DELETE CASCADE,

    FOREIGN KEY (workshop_name)
        REFERENCES events(event_name)
        ON DELETE CASCADE,

    UNIQUE (member_id)  -- one workshop per member
);

CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

INSERT INTO admin (username, password)
VALUES ('admin', 'admin123');
