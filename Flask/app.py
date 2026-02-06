from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta
import calendar

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
        student_email TEXT,
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
        section TEXT CHECK (section IN ('.1', '.2', '.3', 'All')),
        test_name TEXT,
        notes TEXT,
        FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE
    )''')
    
    # Insert accommodations
    accommodations = [
        ('Extended Time (25%)', 'Student receives 25% additional time on assessments (e.g., 60 min test → 75 min)', 1.25),
        ('Extended Time (50%)', 'Student receives 50% additional time on assessments (e.g., 60 min test → 90 min)', 1.50),
        ('Computer for Writing', 'Student uses computer/laptop for written responses and essays', 1.00),
        ('Preferential Seating', 'Student sits in front row or designated quiet area of classroom', 1.00)
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
        SELECT s.student_id, s.student_name, s.student_email, s.grade,
               GROUP_CONCAT(c.class_name || ' (' || sc.level || ' ' || sc.section || ')') as classes,
               GROUP_CONCAT(at.accommodation_name) as accommodations
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
        email = request.form['email']
        grade = request.form['grade']
        accommodation_ids = request.form.getlist('accommodations')
        notes = request.form.get('notes', '')
        
        c.execute('INSERT INTO students (student_name, student_email, grade) VALUES (?, ?, ?)', (name, email, grade))
        student_id = c.lastrowid
        
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
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None or month is None:
        today = datetime.now()
        year = today.year
        month = today.month
    
    conn = get_db()
    c = conn.cursor()
    
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    c.execute('''
        SELECT t.test_id, t.test_date, t.period, t.test_name, t.section,
               c.class_name, c.class_code
        FROM test_schedule t
        JOIN classes c ON t.class_id = c.class_id
        WHERE t.test_date >= ? AND t.test_date <= ?
        ORDER BY t.test_date, t.period
    ''', (first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')))
    
    tests = c.fetchall()
    conn.close()
    
    tests_by_date = {}
    for test in tests:
        date = test['test_date']
        if date not in tests_by_date:
            tests_by_date[date] = []
        tests_by_date[date].append(test)
    
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('calendar.html', 
                         cal=cal, 
                         year=year, 
                         month=month, 
                         month_name=month_name,
                         tests_by_date=tests_by_date,
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month,
                         today=today_str)

@app.route('/add_test', methods=['GET', 'POST'])
def add_test():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        test_date = request.form['test_date']
        period = request.form['period']
        class_id = request.form['class_id']
        section = request.form['section']
        test_name = request.form['test_name']
        notes = request.form.get('notes', '')
        
        c.execute('''INSERT INTO test_schedule 
                    (test_date, period, class_id, section, test_name, notes) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (test_date, period, class_id, section, test_name, notes))
        conn.commit()
        conn.close()
        flash('Test added successfully!', 'success')
        return redirect(url_for('calendar_view'))
    
    c.execute('SELECT * FROM classes ORDER BY class_name')
    classes = c.fetchall()
    conn.close()
    
    return render_template('add_test.html', classes=classes)

@app.route('/view_test/<int:test_id>')
def view_test(test_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT t.*, c.class_name, c.class_code
        FROM test_schedule t
        JOIN classes c ON t.class_id = c.class_id
        WHERE t.test_id = ?
    ''', (test_id,))
    test = c.fetchone()
    
    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('calendar_view'))
    
    if test['section'] == 'All':
        c.execute('''
            SELECT 
                s.student_id,
                s.student_name,
                s.student_email,
                s.grade,
                sc.section,
                sc.level,
                GROUP_CONCAT(at.accommodation_name || '|' || at.description, ';;') as accommodations,
                MAX(at.time_multiplier) as max_time_multiplier
            FROM students s
            JOIN student_classes sc ON s.student_id = sc.student_id
            JOIN student_accommodations sa ON s.student_id = sa.student_id
            JOIN accommodation_types at ON sa.accommodation_id = at.accommodation_id
            WHERE sc.class_id = ?
            GROUP BY s.student_id, sc.section, sc.level
            ORDER BY sc.section, s.student_name
        ''', (test['class_id'],))
    else:
        c.execute('''
            SELECT 
                s.student_id,
                s.student_name,
                s.student_email,
                s.grade,
                sc.section,
                sc.level,
                GROUP_CONCAT(at.accommodation_name || '|' || at.description, ';;') as accommodations,
                MAX(at.time_multiplier) as max_time_multiplier
            FROM students s
            JOIN student_classes sc ON s.student_id = sc.student_id
            JOIN student_accommodations sa ON s.student_id = sa.student_id
            JOIN accommodation_types at ON sa.accommodation_id = at.accommodation_id
            WHERE sc.class_id = ? AND sc.section = ?
            GROUP BY s.student_id, sc.section, sc.level
            ORDER BY s.student_name
        ''', (test['class_id'], test['section']))
    
    affected_students = []
    for row in c.fetchall():
        student_dict = dict(row)
        if student_dict['accommodations']:
            acc_list = []
            for acc in student_dict['accommodations'].split(';;'):
                parts = acc.split('|')
                acc_list.append({'name': parts[0], 'description': parts[1] if len(parts) > 1 else ''})
            student_dict['accommodation_list'] = acc_list
        else:
            student_dict['accommodation_list'] = []
        affected_students.append(student_dict)
    
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
    return redirect(url_for('calendar_view'))

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

