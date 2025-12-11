-- Student Accommodation Scheduling Database
-- CompSci IA Project

-- Create the main students table
CREATE TABLE students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    student_name VARCHAR(100) NOT NULL,
    grade INT NOT NULL CHECK (grade BETWEEN 9 AND 12),
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create the classes table
CREATE TABLE classes (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_name VARCHAR(100) NOT NULL,
    class_code VARCHAR(20),
    subject_area VARCHAR(50),
    level VARCHAR(10) -- e.g., 'HL', 'SL', 'AP', 'Honors'
);

-- Create the accommodation types table
CREATE TABLE accommodation_types (
    accommodation_id INT PRIMARY KEY AUTO_INCREMENT,
    accommodation_name VARCHAR(100) NOT NULL,
    description TEXT,
    requires_separate_room BOOLEAN DEFAULT FALSE,
    time_multiplier DECIMAL(3,2) DEFAULT 1.00 -- e.g., 1.25 for 25% extra time
);

-- Junction table for students and classes (many-to-many relationship)
CREATE TABLE student_classes (
    student_class_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    enrollment_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
    UNIQUE KEY unique_enrollment (student_id, class_id)
);

-- Junction table for students and accommodations (many-to-many relationship)
CREATE TABLE student_accommodations (
    student_accommodation_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    accommodation_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    notes TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (accommodation_id) REFERENCES accommodation_types(accommodation_id) ON DELETE CASCADE
);

-- Insert sample accommodation types
INSERT INTO accommodation_types (accommodation_name, description, requires_separate_room, time_multiplier) VALUES
('Extended Time (25%)', 'Student receives 25% additional time on assessments', FALSE, 1.25),
('Extended Time (50%)', 'Student receives 50% additional time on assessments', FALSE, 1.50),
('Extended Time (100%)', 'Student receives double time on assessments', FALSE, 2.00),
('Separate Room', 'Student takes tests in a separate, quiet room', TRUE, 1.00),
('Computer for Writing', 'Student uses computer/laptop for written responses', FALSE, 1.00),
('Reader/Scribe', 'Student receives reading or writing assistance', TRUE, 1.00),
('Frequent Breaks', 'Student may take breaks during assessments', FALSE, 1.00),
('Preferential Seating', 'Student sits in designated area of classroom', FALSE, 1.00),
('Other', 'Other accommodation as specified in notes', FALSE, 1.00);

-- Insert sample classes
INSERT INTO classes (class_name, class_code, subject_area, level) VALUES
('Mathematics Analysis and Approaches', 'MAA', 'Mathematics', 'HL'),
('Mathematics Analysis and Approaches', 'MAA', 'Mathematics', 'SL'),
('Physics', 'PHY', 'Science', 'HL'),
('Biology', 'BIO', 'Science', 'HL'),
('Chemistry', 'CHEM', 'Science', 'HL'),
('English A: Language and Literature', 'ENG-A', 'Language', 'HL'),
('Spanish B', 'SPA-B', 'Language', 'SL'),
('History', 'HIST', 'Humanities', 'HL'),
('Computer Science', 'CS', 'Technology', 'HL');

-- Insert sample students
INSERT INTO students (student_name, grade) VALUES
('Alex Johnson', 11),
('Maria Garcia', 12),
('James Chen', 11),
('Sofia Rodriguez', 10);

-- Assign classes to students (sample data)
INSERT INTO student_classes (student_id, class_id, enrollment_date) VALUES
(1, 1, '2024-09-01'), -- Alex: Math HL
(1, 3, '2024-09-01'), -- Alex: Physics HL
(1, 6, '2024-09-01'), -- Alex: English HL
(1, 7, '2024-09-01'), -- Alex: Spanish SL
(2, 4, '2024-09-01'), -- Maria: Biology HL
(2, 5, '2024-09-01'), -- Maria: Chemistry HL
(2, 2, '2024-09-01'), -- Maria: Math SL
(2, 8, '2024-09-01'); -- Maria: History HL

-- Assign accommodations to students (sample data)
INSERT INTO student_accommodations (student_id, accommodation_id, start_date, notes) VALUES
(1, 2, '2024-09-01', 'Approved for all assessments due to processing disorder'),
(2, 4, '2024-09-01', 'Requires quiet environment due to ADHD');

-- Useful queries for the application:

-- View all students with their accommodations
CREATE VIEW student_accommodation_summary AS
SELECT 
    s.student_id,
    s.student_name,
    s.grade,
    GROUP_CONCAT(DISTINCT at.accommodation_name SEPARATOR '; ') AS accommodations
FROM students s
LEFT JOIN student_accommodations sa ON s.student_id = sa.student_id
LEFT JOIN accommodation_types at ON sa.accommodation_id = at.accommodation_id
WHERE sa.end_date IS NULL OR sa.end_date >= CURDATE()
GROUP BY s.student_id, s.student_name, s.grade;

-- View all students with their classes
CREATE VIEW student_class_summary AS
SELECT 
    s.student_id,
    s.student_name,
    s.grade,
    GROUP_CONCAT(DISTINCT CONCAT(c.class_name, ' (', c.level, ')') SEPARATOR ', ') AS classes
FROM students s
LEFT JOIN student_classes sc ON s.student_id = sc.student_id
LEFT JOIN classes c ON sc.class_id = c.class_id
GROUP BY s.student_id, s.student_name, s.grade;

-- Complete student overview
CREATE VIEW complete_student_overview AS
SELECT 
    s.student_id,
    s.student_name,
    s.grade,
    scs.classes,
    sas.accommodations
FROM students s
LEFT JOIN student_class_summary scs ON s.student_id = scs.student_id
LEFT JOIN student_accommodation_summary sas ON s.student_id = sas.student_id;

-- Query to find scheduling conflicts (students needing separate rooms at same time)
-- This would be useful for your scheduling algorithm
SELECT * FROM complete_student_overview;