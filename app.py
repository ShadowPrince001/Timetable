from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import schedule
import time
import threading
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration - supports both SQLite (development) and PostgreSQL (production)
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///timetable_attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, faculty, student
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    max_students = db.Column(db.Integer, default=50)
    
    # Relationships
    teacher = db.relationship('User', backref='taught_courses')

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(50), nullable=False)
    equipment = db.Column(db.String(200))

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM format
    end_time = db.Column(db.String(10), nullable=False)  # HH:MM format

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    
    # Relationships
    course = db.relationship('Course', backref='timetable_entries')
    classroom = db.relationship('Classroom', backref='timetable_entries')
    time_slot = db.relationship('TimeSlot', backref='timetable_entries')
    teacher = db.relationship('User', backref='teaching_schedule')

class StudentGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)

class StudentGroupCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # present, absent, late
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    timetable = db.relationship('Timetable', backref='attendance_records')
    marked_by_user = db.relationship('User', foreign_keys=[marked_by], backref='marked_attendance')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # attendance, timetable, general
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'faculty':
        return redirect(url_for('faculty_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get statistics
    total_students = User.query.filter_by(role='student').count()
    total_faculty = User.query.filter_by(role='faculty').count()
    total_courses = Course.query.count()
    total_classrooms = Classroom.query.count()
    
    # Get recent attendance data
    recent_attendance = Attendance.query.order_by(Attendance.marked_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         total_faculty=total_faculty,
                         total_courses=total_courses,
                         total_classrooms=total_classrooms,
                         recent_attendance=recent_attendance)

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get faculty's courses and timetables
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    timetables = Timetable.query.filter_by(teacher_id=current_user.id).all()
    
    # Get today's classes
    today = datetime.now().strftime('%A')
    today_classes = Timetable.query.join(TimeSlot).filter(
        Timetable.teacher_id == current_user.id,
        TimeSlot.day == today
    ).all()
    
    return render_template('faculty/dashboard.html', 
                         courses=courses,
                         timetables=timetables,
                         today_classes=today_classes)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get student's attendance records
    attendance_records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).limit(10).all()
    
    # Get attendance statistics
    total_classes = Attendance.query.filter_by(student_id=current_user.id).count()
    present_classes = Attendance.query.filter_by(student_id=current_user.id, status='present').count()
    late_classes = Attendance.query.filter_by(student_id=current_user.id, status='late').count()
    attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
    
    # Get today's classes (simplified - get sample timetable data)
    today = datetime.now().strftime('%A')
    today_classes = Timetable.query.join(TimeSlot).filter(
        TimeSlot.day == today
    ).limit(5).all()
    
    return render_template('student/dashboard.html',
                         attendance_records=attendance_records,
                         total_classes=total_classes,
                         present_classes=present_classes,
                         late_classes=late_classes,
                         attendance_percentage=attendance_percentage,
                         today_classes=today_classes)

# API Routes for AJAX calls
@app.route('/api/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    data = request.get_json()
    student_id = data.get('student_id')
    timetable_id = data.get('timetable_id')
    status = data.get('status')
    date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
    
    # Check if attendance already exists
    existing = Attendance.query.filter_by(
        student_id=student_id,
        timetable_id=timetable_id,
        date=date
    ).first()
    
    if existing:
        existing.status = status
        existing.marked_by = current_user.id
        existing.marked_at = datetime.utcnow()
    else:
        new_attendance = Attendance(
            student_id=student_id,
            timetable_id=timetable_id,
            date=date,
            status=status,
            marked_by=current_user.id
        )
        db.session.add(new_attendance)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/get-timetable')
@login_required
def get_timetable():
    if current_user.role == 'student':
        # Get student's timetable through their group
        timetables = db.session.query(Timetable).join(
            StudentGroupCourse, Timetable.course_id == StudentGroupCourse.course_id
        ).join(
            StudentGroup, StudentGroupCourse.student_group_id == StudentGroup.id
        ).filter(
            StudentGroup.name == current_user.department
        ).all()
    else:
        timetables = Timetable.query.filter_by(teacher_id=current_user.id).all()
    
    timetable_data = []
    for tt in timetables:
        time_slot = TimeSlot.query.get(tt.time_slot_id)
        course = Course.query.get(tt.course_id)
        classroom = Classroom.query.get(tt.classroom_id)
        
        timetable_data.append({
            'id': tt.id,
            'course': course.name,
            'classroom': classroom.room_number,
            'day': time_slot.day,
            'start_time': time_slot.start_time,
            'end_time': time_slot.end_time
        })
    
    return jsonify(timetable_data)

# Admin Management Routes
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    courses = Course.query.all()
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/courses.html', courses=courses, teachers=teachers)

@app.route('/admin/classrooms')
@login_required
def admin_classrooms():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    classrooms = Classroom.query.all()
    return render_template('admin/classrooms.html', classrooms=classrooms)

@app.route('/admin/timetable')
@login_required
def admin_timetable():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetables = Timetable.query.all()
    courses = Course.query.all()
    classrooms = Classroom.query.all()
    teachers = User.query.filter_by(role='faculty').all()
    time_slots = TimeSlot.query.all()
    
    return render_template('admin/timetable.html', 
                         timetables=timetables,
                         courses=courses,
                         classrooms=classrooms,
                         teachers=teachers,
                         time_slots=time_slots)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']
        department = request.form['department']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('admin_add_user'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            role=role,
            department=department
        )
        db.session.add(user)
        db.session.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/add_user.html')

@app.route('/admin/add_course', methods=['GET', 'POST'])
@login_required
def admin_add_course():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        credits = int(request.form['credits'])
        department = request.form['department']
        teacher_id = int(request.form['teacher_id']) if request.form['teacher_id'] else None
        max_students = int(request.form['max_students'])
        
        if Course.query.filter_by(code=code).first():
            flash('Course code already exists', 'error')
            return redirect(url_for('admin_add_course'))
        
        course = Course(
            code=code,
            name=name,
            credits=credits,
            department=department,
            teacher_id=teacher_id,
            max_students=max_students
        )
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully', 'success')
        return redirect(url_for('admin_courses'))
    
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/add_course.html', teachers=teachers)

@app.route('/admin/add_classroom', methods=['GET', 'POST'])
@login_required
def admin_add_classroom():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        room_number = request.form['room_number']
        capacity = int(request.form['capacity'])
        building = request.form['building']
        equipment = request.form['equipment']
        
        if Classroom.query.filter_by(room_number=room_number).first():
            flash('Room number already exists', 'error')
            return redirect(url_for('admin_add_classroom'))
        
        classroom = Classroom(
            room_number=room_number,
            capacity=capacity,
            building=building,
            equipment=equipment
        )
        db.session.add(classroom)
        db.session.commit()
        flash('Classroom added successfully', 'success')
        return redirect(url_for('admin_classrooms'))
    
    return render_template('admin/add_classroom.html')

# Edit and Delete Routes for Admin
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.role = request.form['role']
        user.department = request.form['department']
        
        # Only update password if provided
        if request.form['password']:
            user.password_hash = generate_password_hash(request.form['password'])
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the current user
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        course.name = request.form['name']
        course.credits = int(request.form['credits'])
        course.department = request.form['department']
        course.teacher_id = int(request.form['teacher_id']) if request.form['teacher_id'] else None
        course.max_students = int(request.form['max_students'])
        
        db.session.commit()
        flash('Course updated successfully', 'success')
        return redirect(url_for('admin_courses'))
    
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/edit_course.html', course=course, teachers=teachers)

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
def admin_delete_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/edit_classroom/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    if request.method == 'POST':
        classroom.room_number = request.form['room_number']
        classroom.capacity = int(request.form['capacity'])
        classroom.building = request.form['building']
        classroom.equipment = request.form['equipment']
        
        db.session.commit()
        flash('Classroom updated successfully', 'success')
        return redirect(url_for('admin_classrooms'))
    
    return render_template('admin/edit_classroom.html', classroom=classroom)

@app.route('/admin/delete_classroom/<int:classroom_id>', methods=['POST'])
@login_required
def admin_delete_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    db.session.delete(classroom)
    db.session.commit()
    flash('Classroom deleted successfully', 'success')
    return redirect(url_for('admin_classrooms'))

# Faculty Routes
@app.route('/faculty/take_attendance/<int:timetable_id>')
@login_required
def take_attendance(timetable_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    # Verify this timetable belongs to the current faculty
    if timetable.teacher_id != current_user.id:
        flash('You can only take attendance for your own classes', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    # Get students enrolled in this course through student groups
    students = db.session.query(User).join(
        StudentGroupCourse, User.department == StudentGroupCourse.student_group_id  # This is simplified
    ).filter(
        StudentGroupCourse.course_id == timetable.course_id,
        User.role == 'student'
    ).all()
    
    # For now, get all students - we'll improve this later
    students = User.query.filter_by(role='student').limit(20).all()
    
    # Get today's attendance records for this class
    today = datetime.now().date()
    attendance_records = {record.student_id: record for record in 
                         Attendance.query.filter_by(timetable_id=timetable_id, date=today).all()}
    
    return render_template('faculty/take_attendance.html', 
                         timetable=timetable, 
                         students=students,
                         attendance_records=attendance_records,
                         today=today)

@app.route('/faculty/save_attendance', methods=['POST'])
@login_required
def save_attendance():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetable_id = request.form.get('timetable_id')
    date_str = request.form.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get all form data for attendance
    for key, value in request.form.items():
        if key.startswith('attendance_'):
            student_id = int(key.replace('attendance_', ''))
            status = value
            
            # Check if attendance already exists
            existing = Attendance.query.filter_by(
                student_id=student_id,
                timetable_id=timetable_id,
                date=date
            ).first()
            
            if existing:
                existing.status = status
                existing.marked_by = current_user.id
                existing.marked_at = datetime.utcnow()
            else:
                new_attendance = Attendance(
                    student_id=student_id,
                    timetable_id=timetable_id,
                    date=date,
                    status=status,
                    marked_by=current_user.id
                )
                db.session.add(new_attendance)
    
    db.session.commit()
    flash('Attendance saved successfully', 'success')
    return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/course_details/<int:course_id>')
@login_required
def course_details(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify this course belongs to the current faculty
    if course.teacher_id != current_user.id:
        flash('You can only view details for your own courses', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    # Get timetable entries for this course
    timetables = Timetable.query.filter_by(course_id=course_id, teacher_id=current_user.id).all()
    
    return render_template('faculty/course_details.html', course=course, timetables=timetables)

@app.route('/faculty/course_attendance/<int:course_id>')
@login_required
def course_attendance(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify this course belongs to the current faculty
    if course.teacher_id != current_user.id:
        flash('You can only view attendance for your own courses', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    # Get attendance records for this course
    attendance_records = db.session.query(Attendance).join(
        Timetable, Attendance.timetable_id == Timetable.id
    ).filter(
        Timetable.course_id == course_id,
        Timetable.teacher_id == current_user.id
    ).order_by(Attendance.date.desc()).all()
    
    return render_template('faculty/course_attendance.html', course=course, attendance_records=attendance_records)

# Student Routes
@app.route('/student/timetable')
@login_required
def student_timetable():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get student's full timetable (simplified - showing all timetables for demo)
    timetables = Timetable.query.join(TimeSlot).order_by(
        db.case(
            (TimeSlot.day == 'Monday', 1),
            (TimeSlot.day == 'Tuesday', 2),
            (TimeSlot.day == 'Wednesday', 3),
            (TimeSlot.day == 'Thursday', 4),
            (TimeSlot.day == 'Friday', 5),
            else_=6
        ),
        TimeSlot.start_time
    ).all()
    
    return render_template('student/timetable.html', timetables=timetables)

@app.route('/student/attendance_history')
@login_required
def student_attendance_history():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all attendance records for the student
    attendance_records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
    
    # Get attendance statistics by course
    course_stats = {}
    for record in attendance_records:
        course = record.timetable.course
        if course.id not in course_stats:
            course_stats[course.id] = {
                'course': course,
                'total': 0,
                'present': 0,
                'absent': 0,
                'late': 0
            }
        
        course_stats[course.id]['total'] += 1
        course_stats[course.id][record.status] += 1
    
    # Calculate percentages
    for course_id in course_stats:
        stats = course_stats[course_id]
        stats['percentage'] = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    return render_template('student/attendance_history.html', 
                         attendance_records=attendance_records,
                         course_stats=course_stats)

@app.route('/student/profile')
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('student/profile.html', user=current_user)

# Timetable Management Routes
@app.route('/admin/add_timetable_entry', methods=['POST'])
@login_required
def add_timetable_entry():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course_id = int(request.form['course_id'])
    teacher_id = int(request.form['teacher_id'])
    classroom_id = int(request.form['classroom_id'])
    time_slot_id = int(request.form['time_slot_id'])
    semester = request.form['semester']
    academic_year = request.form['academic_year']
    
    # Check for conflicts
    existing = Timetable.query.filter_by(
        classroom_id=classroom_id,
        time_slot_id=time_slot_id,
        academic_year=academic_year,
        semester=semester
    ).first()
    
    if existing:
        flash('Classroom is already booked for this time slot', 'error')
        return redirect(url_for('admin_timetable'))
    
    # Check teacher availability
    teacher_conflict = Timetable.query.filter_by(
        teacher_id=teacher_id,
        time_slot_id=time_slot_id,
        academic_year=academic_year,
        semester=semester
    ).first()
    
    if teacher_conflict:
        flash('Teacher is already assigned to another class at this time', 'error')
        return redirect(url_for('admin_timetable'))
    
    new_timetable = Timetable(
        course_id=course_id,
        teacher_id=teacher_id,
        classroom_id=classroom_id,
        time_slot_id=time_slot_id,
        semester=semester,
        academic_year=academic_year
    )
    
    db.session.add(new_timetable)
    db.session.commit()
    flash('Timetable entry added successfully', 'success')
    return redirect(url_for('admin_timetable'))

@app.route('/admin/delete_timetable/<int:timetable_id>', methods=['POST'])
@login_required
def delete_timetable(timetable_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    db.session.delete(timetable)
    db.session.commit()
    flash('Timetable entry deleted successfully', 'success')
    return redirect(url_for('admin_timetable'))

# Missing API and utility routes
@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """API endpoint for real-time dashboard statistics"""
    if current_user.role == 'admin':
        stats = {
            'total_students': User.query.filter_by(role='student').count(),
            'total_faculty': User.query.filter_by(role='faculty').count(),
            'total_courses': Course.query.count(),
            'total_classrooms': Classroom.query.count(),
            'total_attendance': Attendance.query.count()
        }
    elif current_user.role == 'faculty':
        stats = {
            'my_courses': Course.query.filter_by(teacher_id=current_user.id).count(),
            'today_classes': Timetable.query.filter_by(teacher_id=current_user.id).join(TimeSlot).filter(
                TimeSlot.day == datetime.now().strftime('%A')
            ).count(),
            'pending_attendance': 0  # Placeholder
        }
    else:  # student
        total_classes = Attendance.query.filter_by(student_id=current_user.id).count()
        present_classes = Attendance.query.filter_by(student_id=current_user.id, status='present').count()
        stats = {
            'total_classes': total_classes,
            'present_classes': present_classes,
            'attendance_percentage': (present_classes / total_classes * 100) if total_classes > 0 else 0
        }
    
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/notifications')
@login_required
def api_notifications():
    """API endpoint for notifications"""
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).order_by(
        Notification.created_at.desc()
    ).limit(5).all()
    
    notification_data = []
    for notif in notifications:
        notification_data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'type': notif.type,
            'created_at': notif.created_at.strftime('%H:%M')
        })
    
    return jsonify({'success': True, 'notifications': notification_data})

@app.route('/api/attendance-data')
@login_required
def api_attendance_data():
    """API endpoint for real-time attendance data"""
    if current_user.role == 'faculty':
        attendance_records = db.session.query(Attendance).join(
            Timetable, Attendance.timetable_id == Timetable.id
        ).filter(
            Timetable.teacher_id == current_user.id
        ).order_by(Attendance.marked_at.desc()).limit(20).all()
    else:
        attendance_records = Attendance.query.filter_by(
            student_id=current_user.id
        ).order_by(Attendance.marked_at.desc()).limit(20).all()
    
    data = []
    for record in attendance_records:
        data.append({
            'id': record.id,
            'student': record.student.name,
            'course': record.timetable.course.name,
            'status': record.status,
            'date': record.date.strftime('%Y-%m-%d'),
            'marked_at': record.marked_at.strftime('%H:%M')
        })
    
    return jsonify({'success': True, 'data': data})

@app.route('/admin/bulk_delete_users', methods=['POST'])
@login_required
def admin_bulk_delete_users():
    """Bulk delete users"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    try:
        for user_id in user_ids:
            if int(user_id) != current_user.id:  # Don't delete current user
                user = User.query.get(user_id)
                if user:
                    db.session.delete(user)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Deleted {len(user_ids)} users'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@institution.com',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                name='System Administrator'
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
