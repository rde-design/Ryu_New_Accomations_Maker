# app.py - Flask Application for Student Accommodation Scheduler

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = '67'  

# Database initialization
def init_db():
    conn = sqlite3.connect('accommodation.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        grade INTEGER NOT NULL CHECK (grade BETWEEN 9 AND 12),
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS classes (
        class_id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL,
        class_code TEXT,
        subject_area TEXT,
        level TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS accommodation_types (
        accommodation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        accommodation_name TEXT NOT NULL,
        description TEXT,
        requires_separate_room INTEGER DEFAULT 0,
        time_multiplier REAL DEFAULT 1.00
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS student_classes (
        student_class_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        enrollment_date DATE,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS student_accommodations (
        student_accommodation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        accommodation_id INTEGER NOT NULL,
        start_date DATE NOT NULL,
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (accommodation_id) REFERENCES accommodation_types(accommodation_id)
    )''')
    
    # Insert sample accommodation types if table is empty
    c.execute('SELECT COUNT(*) FROM accommodation_types')
    if c.fetchone()[0] == 0:
        accommodations = [
            ('Extended Time (25%)', '25% additional time', 0, 1.25),
            ('Extended Time (50%)', '50% additional time', 0, 1.50),
            ('Extended Time (100%)', 'Double time', 0, 2.00),
            ('Separate Room', 'Quiet room for testing', 1, 1.00),
            ('Computer for Writing', 'Laptop/computer use', 0, 1.00),
            ('Reader/Scribe', 'Reading/writing assistance', 1, 1.00),
            ('Frequent Breaks', 'Break allowance', 0, 1.00),
            ('Preferential Seating', 'Designated seating', 0, 1.00)
        ]
        c.executemany('''INSERT INTO accommodation_types 
            (accommodation_name, description, requires_separate_room, time_multiplier) 
            VALUES (?, ?, ?, ?)''', accommodations)
    
    # Insert sample classes if table is empty
    c.execute('SELECT COUNT(*) FROM classes')
    if c.fetchone()[0] == 0:
        classes = [
            ('Math Analysis & Approaches', 'MAA', 'Mathematics', 'HL'),
            ('Math Analysis & Approaches', 'MAA', 'Mathematics', 'SL'),
            ('Physics', 'PHY', 'Science', 'HL'),
            ('Biology', 'BIO', 'Science', 'HL'),
            ('Chemistry', 'CHEM', 'Science', 'HL'),
            ('English A', 'ENG-A', 'Language', 'HL'),
            ('Spanish B', 'SPA-B', 'Language', 'SL'),
            ('History', 'HIST', 'Humanities', 'HL'),
            ('Computer Science', 'CS', 'Technology', 'HL')
        ]
        c.executemany('''INSERT INTO classes 
            (class_name, class_code, subject_area, level) 
            VALUES (?, ?, ?, ?)''', classes)
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('accommodation.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    
    # Get all students with their info
    c.execute('''
        SELECT s.student_id, s.student_name, s.grade,
               GROUP_CONCAT(DISTINCT c.class_name || ' (' || c.level || ')') as classes,
               GROUP_CONCAT(DISTINCT at.accommodation_name) as accommodations
        FROM students s
        LEFT JOIN student_classes sc ON s.student_id = sc.student_id
        LEFT JOIN classes c ON sc.class_id = c.class_id
        LEFT JOIN student_accommodations sa ON s.student_id = sa.student_id
        LEFT JOIN accommodation_types at ON sa.accommodation_id = at.accommodation_id
        GROUP BY s.student_id
    ''')
    students = c.fetchall()
    conn.close()
    
    return render_template('index.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        grade = request.form['grade']
        class_ids = request.form.getlist('classes')
        accommodation_ids = request.form.getlist('accommodations')
        notes = request.form.get('notes', '')
        
        # Insert student
        c.execute('INSERT INTO students (student_name, grade) VALUES (?, ?)', (name, grade))
        student_id = c.lastrowid
        
        # Insert student classes
        today = datetime.now().strftime('%Y-%m-%d')
        for class_id in class_ids:
            c.execute('INSERT INTO student_classes (student_id, class_id, enrollment_date) VALUES (?, ?, ?)',
                     (student_id, class_id, today))
        
        # Insert student accommodations
        for acc_id in accommodation_ids:
            c.execute('INSERT INTO student_accommodations (student_id, accommodation_id, start_date, notes) VALUES (?, ?, ?, ?)',
                     (student_id, acc_id, today, notes))
        
        conn.commit()
        conn.close()
        flash('Student added successfully!', 'success')
        return redirect(url_for('index'))
    
    # GET request - show form
    c.execute('SELECT * FROM classes ORDER BY subject_area, class_name')
    classes = c.fetchall()
    
    c.execute('SELECT * FROM accommodation_types ORDER BY accommodation_name')
    accommodations = c.fetchall()
    
    conn.close()
    return render_template('add_student.html', classes=classes, accommodations=accommodations)

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
    conn.commit()
    conn.close()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/view_student/<int:student_id>')
def view_student(student_id):
    conn = get_db()
    c = conn.cursor()
    
    # Get student info
    c.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = c.fetchone()
    
    # Get student's classes
    c.execute('''
        SELECT c.class_name, c.class_code, c.subject_area, c.level
        FROM classes c
        JOIN student_classes sc ON c.class_id = sc.class_id
        WHERE sc.student_id = ?
    ''', (student_id,))
    classes = c.fetchall()
    
    # Get student's accommodations
    c.execute('''
        SELECT at.accommodation_name, at.description, at.time_multiplier, 
               at.requires_separate_room, sa.notes, sa.start_date
        FROM accommodation_types at
        JOIN student_accommodations sa ON at.accommodation_id = sa.accommodation_id
        WHERE sa.student_id = ?
    ''', (student_id,))
    accommodations = c.fetchall()
    
    conn.close()
    return render_template('view_student.html', student=student, classes=classes, accommodations=accommodations)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)