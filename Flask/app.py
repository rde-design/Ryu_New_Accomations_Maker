
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

def init_db():
    conn = sqlite3.connect('accommodation.db')
    c = conn.cursor()
    
    # Drop old tables
    c.execute('DROP TABLE IF EXISTS student_accommodations')
    c.execute('DROP TABLE IF EXISTS student_classes')
    c.execute('DROP TABLE IF EXISTS students')
    c.execute('DROP TABLE IF EXISTS classes')
    c.execute('DROP TABLE IF EXISTS accommodation_types')
    c.execute('DROP TABLE IF EXISTS test_schedule')
    
    # Create tables
    c.execute('''CREATE TABLE students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        grade INTEGER NOT NULL CHECK (grade BETWEEN 9 AND 12),
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE classes (
        class_id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_name TEXT NOT NULL UNIQUE,
        class_code TEXT,
        subject_area TEXT
    )''')
    
    c.execute('''CREATE TABLE accommodation_types (
        accommodation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        accommodation_name TEXT NOT NULL,
        description TEXT,
        time_multiplier REAL DEFAULT 1.00
    )''')
    
    c.execute('''CREATE TABLE student_classes (
        student_class_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        class_id INTEGER NOT NULL,
        section TEXT CHECK (section IN ('.1', '.2', '.3')),
        level TEXT CHECK (level IN ('HL', 'SL')),
        enrollment_date DATE,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
    )''')
    
    c.execute('''CREATE TABLE student_accommodations (
        student_accommodation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        accommodation_id INTEGER NOT NULL,
        start_date DATE NOT NULL,
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (accommodation_id) REFERENCES accommodation_types(accommodation_id)
    )''')
    
    c.execute('''CREATE TABLE test_schedule (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_date DATE NOT NULL,
        period TEXT CHECK (period IN ('1st', '2nd', '3rd', '4th')),
        class_id INTEGER NOT NULL,
        test_name TEXT,
        notes TEXT,
        FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
    )''')
    
    # Insert accommodations
    accommodations = [
        ('Extended Time (25%)', '25% additional time', 1.25),
        ('Extended Time (50%)', '50% additional time', 1.50),
        ('Computer for Writing', 'Laptop/computer use', 1.00),
        ('Preferential Seating', 'Designated seating', 1.00)
    ]
    c.executemany('''INSERT INTO accommodation_types 
        (accommodation_name, description, time_multiplier) 
        VALUES (?, ?, ?)''', accommodations)
    
    # Insert classes
    classes = [
        ('Math Analysis & Approaches', 'MAA', 'Mathematics'),
        ('Physics', 'PHY', 'Science'),
        ('Biology', 'BIO', 'Science'),
        ('Chemistry', 'CHEM', 'Science'),
        ('English A', 'ENG-A', 'Language'),
        ('Spanish B', 'SPA-B', 'Language'),
        ('History', 'HIST', 'Humanities'),
        ('Computer Science', 'CS', 'Technology')
    ]
    c.executemany('''INSERT INTO classes 
        (class_name, class_code, subject_area) 
        VALUES (?, ?, ?)''', classes)
    
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
    
    c.execute('''
        SELECT s.student_id, s.student_name, s.grade,
               GROUP_CONCAT(DISTINCT c.class_name || ' (' || sc.level || ' ' || sc.section || ')') as classes,
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
        accommodation_ids = request.form.getlist('accommodations')
        notes = request.form.get('notes', '')
        
        # Insert student
        c.execute('INSERT INTO students (student_name, grade) VALUES (?, ?)', (name, grade))
        student_id = c.lastrowid
        
        # Get all classes and check selections
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT class_id FROM classes')
        all_classes = c.fetchall()
        
        for class_row in all_classes:
            class_id = class_row['class_id']
            class_enrolled = request.form.get(f'class_{class_id}')
            
            if class_enrolled == 'yes':
                level = request.form.get(f'level_{class_id}')
                section = request.form.get(f'section_{class_id}')
                
                if level and section:
                    c.execute('''INSERT INTO student_classes 
                                (student_id, class_id, section, level, enrollment_date) 
                                VALUES (?, ?, ?, ?, ?)''',
                             (student_id, class_id, section, level, today))
        
        # Insert accommodations
        for acc_id in accommodation_ids:
            c.execute('''INSERT INTO student_accommodations 
                        (student_id, accommodation_id, start_date, notes) 
                        VALUES (?, ?, ?, ?)''',
                     (student_id, acc_id, today, notes))
        
        conn.commit()
        conn.close()
        flash('Student added successfully!', 'success')
        return redirect(url_for('index'))
    
    c.execute('SELECT * FROM classes ORDER BY subject_area, class_name')
    classes = c.fetchall()
    
    c.execute('SELECT * FROM accommodation_types ORDER BY accommodation_name')
    accommodations = c.fetchall()
    
    conn.close()
    return render_template('add_student.html', classes=classes, accommodations=accommodations)

@app.route('/manage_classes', methods=['GET', 'POST'])
def manage_classes():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        class_name = request.form['class_name']
        class_code = request.form['class_code']
        subject_area = request.form['subject_area']
        
        c.execute('''INSERT INTO classes (class_name, class_code, subject_area) 
                     VALUES (?, ?, ?)''', (class_name, class_code, subject_area))
        conn.commit()
        flash('Class added successfully!', 'success')
        return redirect(url_for('manage_classes'))
    
    c.execute('SELECT * FROM classes ORDER BY subject_area, class_name')
    classes = c.fetchall()
    conn.close()
    
    return render_template('manage_classes.html', classes=classes)

@app.route('/delete_class/<int:class_id>')
def delete_class(class_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM classes WHERE class_id = ?', (class_id,))
    conn.commit()
    conn.close()
    flash('Class deleted successfully!', 'success')
    return redirect(url_for('manage_classes'))

@app.route('/calendar')
def calendar():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT t.test_id, t.test_date, t.period, t.test_name, t.notes,
               c.class_name, c.class_code
        FROM test_schedule t
        JOIN classes c ON t.class_id = c.class_id
        ORDER BY t.test_date DESC, t.period
    ''')
    tests = c.fetchall()
    
    conn.close()
    return render_template('calendar.html', tests=tests)

@app.route('/add_test', methods=['GET', 'POST'])
def add_test():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        test_date = request.form['test_date']
        period = request.form['period']
        class_id = request.form['class_id']
        test_name = request.form['test_name']
        notes = request.form.get('notes', '')
        
        c.execute('''INSERT INTO test_schedule 
                    (test_date, period, class_id, test_name, notes) 
                    VALUES (?, ?, ?, ?, ?)''',
                 (test_date, period, class_id, test_name, notes))
        conn.commit()
        conn.close()
        flash('Test added successfully!', 'success')
        return redirect(url_for('calendar'))
    
    c.execute('SELECT * FROM classes ORDER BY class_name')
    classes = c.fetchall()
    conn.close()
    
    return render_template('add_test.html', classes=classes)

@app.route('/view_test/<int:test_id>')
def view_test(test_id):
    conn = get_db()
    c = conn.cursor()
    
    # Get test info
    c.execute('''
        SELECT t.*, c.class_name, c.class_code
        FROM test_schedule t
        JOIN classes c ON t.class_id = c.class_id
        WHERE t.test_id = ?
    ''', (test_id,))
    test = c.fetchone()
    
    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('calendar'))
    
    # Get affected students
    c.execute('''
        SELECT DISTINCT
            s.student_id,
            s.student_name,
            s.grade,
            sc.section,
            sc.level,
            GROUP_CONCAT(DISTINCT at.accommodation_name, ', ') as accommodations,
            MAX(at.time_multiplier) as max_time_multiplier
        FROM students s
        JOIN student_classes sc ON s.student_id = sc.student_id
        JOIN student_accommodations sa ON s.student_id = sa.student_id
        JOIN accommodation_types at ON sa.accommodation_id = at.accommodation_id
        WHERE sc.class_id = ?
        GROUP BY s.student_id, sc.section, sc.level
        ORDER BY sc.section, s.student_name
    ''', (test['class_id'],))
    
    affected_students = c.fetchall()
    
    warning = None
    if test['period'] == '4th':
        warning = "⚠️ NOTICE: Extra time is BEFORE class for this test"
    
    conn.close()
    return render_template('view_test.html', test=test, affected_students=affected_students, warning=warning)

@app.route('/delete_test/<int:test_id>')
def delete_test(test_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM test_schedule WHERE test_id = ?', (test_id,))
    conn.commit()
    conn.close()
    flash('Test deleted successfully!', 'success')
    return redirect(url_for('calendar'))

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
    
    c.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
    student = c.fetchone()
    
    c.execute('''
        SELECT c.class_name, c.class_code, c.subject_area, sc.level, sc.section
        FROM classes c
        JOIN student_classes sc ON c.class_id = sc.class_id
        WHERE sc.student_id = ?
    ''', (student_id,))
    classes = c.fetchall()
    
    c.execute('''
        SELECT at.accommodation_name, at.description, at.time_multiplier, 
               sa.notes, sa.start_date
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