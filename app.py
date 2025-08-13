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
    
    try:
        # Get statistics
        total_students = User.query.filter_by(role='student').count()
        total_faculty = User.query.filter_by(role='faculty').count()
        total_courses = Course.query.count()
        total_classrooms = Classroom.query.count()
        total_time_slots = TimeSlot.query.count()
        total_timetables = Timetable.query.count()
        total_attendance = Attendance.query.count()
        
        # Get recent attendance data
        recent_attendance = Attendance.query.order_by(Attendance.marked_at.desc()).limit(10).all()
        
        # Ensure all relationships are loaded
        for record in recent_attendance:
            if not hasattr(record, 'student') or not record.student:
                record.student = User.query.get(record.student_id)
            if not hasattr(record, 'marked_by_user') or not record.marked_by_user:
                record.marked_by_user = User.query.get(record.marked_by)
            if not hasattr(record, 'timetable') or not record.timetable:
                record.timetable = Timetable.query.get(record.timetable_id)
            if record.timetable:
                if not hasattr(record.timetable, 'course') or not record.timetable.course:
                    record.timetable.course = Course.query.get(record.timetable.course_id)
                    
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        total_students = 0
        total_faculty = 0
        total_courses = 0
        total_classrooms = 0
        total_time_slots = 0
        total_timetables = 0
        total_attendance = 0
        recent_attendance = []
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         total_faculty=total_faculty,
                         total_courses=total_courses,
                         total_classrooms=total_classrooms,
                         total_time_slots=total_time_slots,
                         total_timetables=total_timetables,
                         total_attendance=total_attendance,
                         recent_attendance=recent_attendance)

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get faculty's courses and timetables
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        timetables = Timetable.query.filter_by(teacher_id=current_user.id).all()
        
        # Get today's classes
        today = datetime.now().strftime('%A')
        today_classes = Timetable.query.join(TimeSlot).filter(
            Timetable.teacher_id == current_user.id,
            TimeSlot.day == today
        ).all()
        
        # Ensure all relationships are loaded for today's classes
        for tt in today_classes:
            if not hasattr(tt, 'time_slot') or not tt.time_slot:
                tt.time_slot = TimeSlot.query.get(tt.time_slot_id)
            if not hasattr(tt, 'course') or not tt.course:
                tt.course = Course.query.get(tt.course_id)
            if not hasattr(tt, 'classroom') or not tt.classroom:
                tt.classroom = Classroom.query.get(tt.classroom_id)
                
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        courses = []
        timetables = []
        today_classes = []
    
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
    
    try:
        # Get student's attendance records
        attendance_records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).limit(10).all()
        
        # Ensure all relationships are loaded
        for record in attendance_records:
            if not hasattr(record, 'timetable') or not record.timetable:
                record.timetable = Timetable.query.get(record.timetable_id)
            if record.timetable:
                if not hasattr(record.timetable, 'course') or not record.timetable.course:
                    record.timetable.course = Course.query.get(record.timetable.course_id)
                if not hasattr(record.timetable, 'teacher') or not record.timetable.teacher:
                    record.timetable.teacher = User.query.get(record.timetable.teacher_id)
                if not hasattr(record.timetable, 'classroom') or not record.timetable.classroom:
                    record.timetable.classroom = Classroom.query.get(record.timetable.classroom_id)
        
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
        
        # Ensure all relationships are loaded for today's classes
        for tt in today_classes:
            if not hasattr(tt, 'time_slot') or not tt.time_slot:
                tt.time_slot = TimeSlot.query.get(tt.time_slot_id)
            if not hasattr(tt, 'course') or not tt.course:
                tt.course = Course.query.get(tt.course_id)
            if not hasattr(tt, 'teacher') or not tt.teacher:
                tt.teacher = User.query.get(tt.teacher_id)
            if not hasattr(tt, 'classroom') or not tt.classroom:
                tt.classroom = Classroom.query.get(tt.classroom_id)
                
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        attendance_records = []
        total_classes = 0
        present_classes = 0
        late_classes = 0
        attendance_percentage = 0
        today_classes = []
    
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
    
    try:
        timetables = Timetable.query.all()
        courses = Course.query.all()
        classrooms = Classroom.query.all()
        teachers = User.query.filter_by(role='faculty').all()
        time_slots = TimeSlot.query.all()
        
        # Ensure all relationships are loaded
        for tt in timetables:
            if not hasattr(tt, 'time_slot') or not tt.time_slot:
                tt.time_slot = TimeSlot.query.get(tt.time_slot_id)
            if not hasattr(tt, 'course') or not tt.course:
                tt.course = Course.query.get(tt.course_id)
            if not hasattr(tt, 'classroom') or not tt.classroom:
                tt.classroom = Classroom.query.get(tt.classroom_id)
            if not hasattr(tt, 'teacher') or not tt.teacher:
                tt.teacher = User.query.get(tt.teacher_id)
                
    except Exception as e:
        flash(f'Error loading timetable data: {str(e)}', 'error')
        timetables = []
        courses = []
        classrooms = []
        teachers = []
        time_slots = []
    
    return render_template('admin/timetable.html', 
                         timetables=timetables,
                         courses=courses,
                         classrooms=classrooms,
                         teachers=teachers,
                         time_slots=time_slots)

@app.route('/admin/time_slots')
@login_required
def admin_time_slots():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        time_slots = TimeSlot.query.order_by(
            db.case(
                (TimeSlot.day == 'Monday', 1),
                (TimeSlot.day == 'Tuesday', 2),
                (TimeSlot.day == 'Wednesday', 3),
                (TimeSlot.day == 'Thursday', 4),
                (TimeSlot.day == 'Friday', 5),
                (TimeSlot.day == 'Saturday', 6),
                else_=7
            ),
            TimeSlot.start_time
        ).all()
        
    except Exception as e:
        flash(f'Error loading time slots: {str(e)}', 'error')
        time_slots = []
    
    return render_template('admin/time_slots.html', time_slots=time_slots)

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
    
    try:
        # Get attendance records for this course through timetables
        attendance_records = db.session.query(Attendance).join(
            Timetable, Attendance.timetable_id == Timetable.id
        ).filter(
            Timetable.course_id == course_id,
            Timetable.teacher_id == current_user.id
        ).order_by(Attendance.date.desc()).all()
        
        # Ensure all relationships are loaded
        for record in attendance_records:
            if not hasattr(record, 'student') or not record.student:
                record.student = User.query.get(record.student_id)
            if not hasattr(record, 'marked_by_user') or not record.marked_by_user:
                record.marked_by_user = User.query.get(record.marked_by)
                
    except Exception as e:
        flash(f'Error loading attendance data: {str(e)}', 'error')
        attendance_records = []
    
    return render_template('faculty/course_attendance.html', course=course, attendance_records=attendance_records)

@app.route('/faculty/all_attendance')
@login_required
def faculty_all_attendance():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get all attendance records for courses taught by this faculty
        attendance_records = db.session.query(Attendance).join(
            Timetable, Attendance.timetable_id == Timetable.id
        ).filter(
            Timetable.teacher_id == current_user.id
        ).order_by(Attendance.date.desc()).all()
        
        # Ensure all relationships are loaded
        for record in attendance_records:
            if not hasattr(record, 'student') or not record.student:
                record.student = User.query.get(record.student_id)
            if not hasattr(record, 'marked_by_user') or not record.marked_by_user:
                record.marked_by_user = User.query.get(record.marked_by)
            if not hasattr(record, 'timetable') or not record.timetable:
                record.timetable = Timetable.query.get(record.timetable_id)
            if record.timetable:
                if not hasattr(record.timetable, 'course') or not record.timetable.course:
                    record.timetable.course = Course.query.get(record.timetable.course_id)
                if not hasattr(record.timetable, 'classroom') or not record.timetable.classroom:
                    record.timetable.classroom = Classroom.query.get(record.timetable.classroom_id)
                    
    except Exception as e:
        flash(f'Error loading attendance data: {str(e)}', 'error')
        attendance_records = []
    
    return render_template('faculty/all_attendance.html', attendance_records=attendance_records)

# Student Routes
@app.route('/student/timetable')
@login_required
def student_timetable():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get student's full timetable (simplified - showing all timetables for demo)
        timetables = Timetable.query.join(TimeSlot).join(Course).join(Classroom).join(User, Timetable.teacher_id == User.id).order_by(
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
        
        # Ensure all relationships are loaded
        for tt in timetables:
            if not hasattr(tt, 'time_slot') or not tt.time_slot:
                tt.time_slot = TimeSlot.query.get(tt.time_slot_id)
            if not hasattr(tt, 'course') or not tt.course:
                tt.course = Course.query.get(tt.course_id)
            if not hasattr(tt, 'classroom') or not tt.classroom:
                tt.classroom = Classroom.query.get(tt.classroom_id)
            if not hasattr(tt, 'teacher') or not tt.teacher:
                tt.teacher = User.query.get(tt.teacher_id)
                
    except Exception as e:
        flash(f'Error loading timetable data: {str(e)}', 'error')
        timetables = []
    
    return render_template('student/timetable.html', timetables=timetables)

@app.route('/student/attendance_history')
@login_required
def student_attendance_history():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get all attendance records for the student
        attendance_records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
        
        # Ensure all relationships are loaded
        for record in attendance_records:
            if not hasattr(record, 'timetable') or not record.timetable:
                record.timetable = Timetable.query.get(record.timetable_id)
            if record.timetable:
                if not hasattr(record.timetable, 'course') or not record.timetable.course:
                    record.timetable.course = Course.query.get(record.timetable.course_id)
                if not hasattr(record.timetable, 'teacher') or not record.timetable.teacher:
                    record.timetable.teacher = User.query.get(record.timetable.teacher_id)
                if not hasattr(record.timetable, 'classroom') or not record.timetable.classroom:
                    record.timetable.classroom = Classroom.query.get(record.timetable.classroom_id)
        
        # Get attendance statistics by course
        course_stats = {}
        for record in attendance_records:
            if record.timetable and record.timetable.course:
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
            
    except Exception as e:
        flash(f'Error loading attendance data: {str(e)}', 'error')
        attendance_records = []
        course_stats = {}
    
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

@app.route('/student/attendance_alerts')
@login_required
def student_attendance_alerts():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get attendance records for the student
        attendance_records = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
        
        # Ensure all relationships are loaded
        for record in attendance_records:
            if not hasattr(record, 'timetable') or not record.timetable:
                record.timetable = Timetable.query.get(record.timetable_id)
            if record.timetable:
                if not hasattr(record.timetable, 'course') or not record.timetable.course:
                    record.timetable.course = Course.query.get(record.timetable.course_id)
        
        # Calculate attendance statistics by course
        course_stats = {}
        for record in attendance_records:
            if record.timetable and record.timetable.course:
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
        
        # Calculate percentages and identify alerts
        alerts = []
        for course_id in course_stats:
            stats = course_stats[course_id]
            stats['percentage'] = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            # Generate alerts based on attendance
            if stats['percentage'] < 75:
                alerts.append({
                    'type': 'warning',
                    'title': f'Low Attendance in {stats["course"].code}',
                    'message': f'Your attendance in {stats["course"].name} is {stats["percentage"]:.1f}%, which is below the required 75%.',
                    'course': stats['course']
                })
            elif stats['percentage'] < 60:
                alerts.append({
                    'type': 'danger',
                    'title': f'Critical Attendance in {stats["course"].code}',
                    'message': f'Your attendance in {stats["course"].name} is {stats["percentage"]:.1f}%, which is critically low.',
                    'course': stats['course']
                })
        
        # Check for consecutive absences
        recent_records = attendance_records[:10]  # Last 10 records
        consecutive_absences = 0
        for record in recent_records:
            if record.status == 'absent':
                consecutive_absences += 1
            else:
                break
        
        if consecutive_absences >= 3:
            alerts.append({
                'type': 'danger',
                'title': 'Consecutive Absences',
                'message': f'You have missed {consecutive_absences} consecutive classes. Please contact your faculty.',
                'course': None
            })
            
    except Exception as e:
        flash(f'Error loading attendance alerts: {str(e)}', 'error')
        alerts = []
        course_stats = {}
    
    return render_template('student/attendance_alerts.html', alerts=alerts, course_stats=course_stats)

# Timetable Management Routes
@app.route('/admin/add_timetable_entry', methods=['POST'])
@login_required
def admin_add_timetable_entry():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
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
        
    except Exception as e:
        flash(f'Error adding timetable entry: {str(e)}', 'error')
    
    return redirect(url_for('admin_timetable'))

@app.route('/admin/delete_timetable/<int:timetable_id>', methods=['POST'])
@login_required
def admin_delete_timetable(timetable_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        timetable = Timetable.query.get_or_404(timetable_id)
        db.session.delete(timetable)
        db.session.commit()
        flash('Timetable entry deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting timetable entry: {str(e)}', 'error')
    
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

@app.route('/admin/add_sample_attendance')
@login_required
def admin_add_sample_attendance():
    """Add sample attendance records for testing"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get sample data
        students = User.query.filter_by(role='student').limit(2).all()
        timetables = Timetable.query.limit(2).all()
        
        if not students or not timetables:
            flash('Need students and timetables to create sample attendance', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Create sample attendance records
        sample_dates = [
            datetime.now().date() - timedelta(days=i) for i in range(7)
        ]
        
        attendance_count = 0
        for timetable in timetables:
            for student in students:
                for date in sample_dates:
                    # Check if attendance already exists
                    existing = Attendance.query.filter_by(
                        student_id=student.id,
                        timetable_id=timetable.id,
                        date=date
                    ).first()
                    
                    if not existing:
                        # Randomly assign attendance status
                        import random
                        status = random.choice(['present', 'absent', 'late'])
                        
                        new_attendance = Attendance(
                            student_id=student.id,
                            timetable_id=timetable.id,
                            date=date,
                            status=status,
                            marked_by=current_user.id
                        )
                        db.session.add(new_attendance)
                        attendance_count += 1
        
        db.session.commit()
        flash(f'Added {attendance_count} sample attendance records', 'success')
        
    except Exception as e:
        flash(f'Error creating sample attendance: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_time_slot', methods=['POST'])
@login_required
def admin_add_time_slot():
    """Add new time slot"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        day = request.form['day']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Check if time slot already exists
        existing = TimeSlot.query.filter_by(
            day=day,
            start_time=start_time,
            end_time=end_time
        ).first()
        
        if existing:
            flash('Time slot already exists', 'error')
            return redirect(url_for('admin_timetable'))
        
        new_time_slot = TimeSlot(
            day=day,
            start_time=start_time,
            end_time=end_time
        )
        
        db.session.add(new_time_slot)
        db.session.commit()
        flash('Time slot added successfully', 'success')
        
    except Exception as e:
        flash(f'Error adding time slot: {str(e)}', 'error')
    
    return redirect(url_for('admin_timetable'))

@app.route('/admin/edit_time_slot/<int:time_slot_id>', methods=['POST'])
@login_required
def admin_edit_time_slot(time_slot_id):
    """Edit time slot"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        time_slot = TimeSlot.query.get_or_404(time_slot_id)
        
        day = request.form['day']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        
        # Check if time slot already exists (excluding current one)
        existing = TimeSlot.query.filter(
            TimeSlot.day == day,
            TimeSlot.start_time == start_time,
            TimeSlot.end_time == end_time,
            TimeSlot.id != time_slot_id
        ).first()
        
        if existing:
            flash('Time slot already exists', 'error')
            return redirect(url_for('admin_time_slots'))
        
        time_slot.day = day
        time_slot.start_time = start_time
        time_slot.end_time = end_time
        
        db.session.commit()
        flash('Time slot updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating time slot: {str(e)}', 'error')
    
    return redirect(url_for('admin_time_slots'))

@app.route('/admin/delete_time_slot/<int:time_slot_id>', methods=['POST'])
@login_required
def admin_delete_time_slot(time_slot_id):
    """Delete time slot"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        time_slot = TimeSlot.query.get_or_404(time_slot_id)
        
        # Check if time slot is used in timetables
        used_in_timetables = Timetable.query.filter_by(time_slot_id=time_slot_id).first()
        if used_in_timetables:
            flash('Cannot delete time slot as it is used in timetables', 'error')
            return redirect(url_for('admin_time_slots'))
        
        db.session.delete(time_slot)
        db.session.commit()
        flash('Time slot deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting time slot: {str(e)}', 'error')
    
    return redirect(url_for('admin_time_slots'))

@app.route('/admin/edit_timetable/<int:timetable_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_timetable(timetable_id):
    """Edit timetable entry"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    if request.method == 'POST':
        try:
            timetable.course_id = int(request.form['course_id'])
            timetable.teacher_id = int(request.form['teacher_id'])
            timetable.classroom_id = int(request.form['classroom_id'])
            timetable.time_slot_id = int(request.form['time_slot_id'])
            timetable.semester = request.form['semester']
            timetable.academic_year = request.form['academic_year']
            
            db.session.commit()
            flash('Timetable updated successfully', 'success')
            return redirect(url_for('admin_timetable'))
            
        except Exception as e:
            flash(f'Error updating timetable: {str(e)}', 'error')
    
    # Get data for form
    courses = Course.query.all()
    teachers = User.query.filter_by(role='faculty').all()
    classrooms = Classroom.query.all()
    time_slots = TimeSlot.query.all()
    
    return render_template('admin/edit_timetable.html', 
                         timetable=timetable,
                         courses=courses,
                         teachers=teachers,
                         classrooms=classrooms,
                         time_slots=time_slots)

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
        
        # Add sample data if database is empty
        if not User.query.filter_by(role='faculty').first():
            # Create sample faculty
            faculty1 = User(
                username='faculty1',
                email='faculty1@institution.com',
                password_hash=generate_password_hash('faculty123'),
                role='faculty',
                name='Dr. John Smith',
                department='Computer Science'
            )
            faculty2 = User(
                username='faculty2',
                email='faculty2@institution.com',
                password_hash=generate_password_hash('faculty123'),
                role='faculty',
                name='Prof. Jane Doe',
                department='Mathematics'
            )
            db.session.add_all([faculty1, faculty2])
            db.session.commit()
        
        if not User.query.filter_by(role='student').first():
            # Create sample students
            student1 = User(
                username='student1',
                email='student1@institution.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                name='Alice Johnson',
                department='Computer Science'
            )
            student2 = User(
                username='student2',
                email='student2@institution.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                name='Bob Wilson',
                department='Computer Science'
            )
            db.session.add_all([student1, student2])
            db.session.commit()
        
        if not Course.query.first():
            # Create sample courses
            faculty1 = User.query.filter_by(username='faculty1').first()
            faculty2 = User.query.filter_by(username='faculty2').first()
            
            course1 = Course(
                code='CS101',
                name='Introduction to Computer Science',
                credits=3,
                department='Computer Science',
                teacher_id=faculty1.id if faculty1 else None,
                max_students=50
            )
            course2 = Course(
                code='MATH101',
                name='Calculus I',
                credits=4,
                department='Mathematics',
                teacher_id=faculty2.id if faculty2 else None,
                max_students=40
            )
            db.session.add_all([course1, course2])
            db.session.commit()
        
        if not Classroom.query.first():
            # Create sample classrooms
            classroom1 = Classroom(
                room_number='101',
                capacity=50,
                building='Science Building',
                equipment='Projector, Whiteboard'
            )
            classroom2 = Classroom(
                room_number='205',
                capacity=40,
                building='Mathematics Building',
                equipment='Smart Board, Computer'
            )
            db.session.add_all([classroom1, classroom2])
            db.session.commit()
        
        if not TimeSlot.query.first():
            # Create sample time slots
            time_slots = [
                TimeSlot(day='Monday', start_time='09:00', end_time='10:00'),
                TimeSlot(day='Monday', start_time='10:00', end_time='11:00'),
                TimeSlot(day='Tuesday', start_time='09:00', end_time='10:00'),
                TimeSlot(day='Tuesday', start_time='10:00', end_time='11:00'),
                TimeSlot(day='Wednesday', start_time='09:00', end_time='10:00'),
                TimeSlot(day='Wednesday', start_time='10:00', end_time='11:00'),
                TimeSlot(day='Thursday', start_time='09:00', end_time='10:00'),
                TimeSlot(day='Thursday', start_time='10:00', end_time='11:00'),
                TimeSlot(day='Friday', start_time='09:00', end_time='10:00'),
                TimeSlot(day='Friday', start_time='10:00', end_time='11:00'),
            ]
            db.session.add_all(time_slots)
            db.session.commit()
        
        if not Timetable.query.first():
            # Create sample timetable entries
            course1 = Course.query.filter_by(code='CS101').first()
            course2 = Course.query.filter_by(code='MATH101').first()
            faculty1 = User.query.filter_by(username='faculty1').first()
            faculty2 = User.query.filter_by(username='faculty2').first()
            classroom1 = Classroom.query.filter_by(room_number='101').first()
            classroom2 = Classroom.query.filter_by(room_number='205').first()
            time_slot1 = TimeSlot.query.filter_by(day='Monday', start_time='09:00').first()
            time_slot2 = TimeSlot.query.filter_by(day='Tuesday', start_time='09:00').first()
            
            if all([course1, faculty1, classroom1, time_slot1]):
                timetable1 = Timetable(
                    course_id=course1.id,
                    teacher_id=faculty1.id,
                    classroom_id=classroom1.id,
                    time_slot_id=time_slot1.id,
                    semester='Fall 2024',
                    academic_year='2024-2025'
                )
                db.session.add(timetable1)
            
            if all([course2, faculty2, classroom2, time_slot2]):
                timetable2 = Timetable(
                    course_id=course2.id,
                    teacher_id=faculty2.id,
                    classroom_id=classroom2.id,
                    time_slot_id=time_slot2.id,
                    semester='Fall 2024',
                    academic_year='2024-2025'
                )
                db.session.add(timetable2)
            
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
