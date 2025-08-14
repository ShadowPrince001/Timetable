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
from timetable_generator import TimetableGenerator, TimeSlot as GenTimeSlot, Course as GenCourse, Classroom as GenClassroom, Teacher as GenTeacher, StudentGroup as GenStudentGroup

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
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    qualifications = db.Column(db.Text)  # For faculty - their teaching qualifications
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'))  # For students only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False, default=3)
    department = db.Column(db.String(100), nullable=False)
    max_students = db.Column(db.Integer, default=50)
    semester = db.Column(db.String(20), default='1')
    description = db.Column(db.Text)
    subject_area = db.Column(db.String(100), nullable=False)  # For teacher qualification checks
    required_equipment = db.Column(db.Text)  # Equipment required for the course
    min_capacity = db.Column(db.Integer, default=1)  # Minimum classroom capacity required
    periods_per_week = db.Column(db.Integer, default=3)  # Number of periods per week
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('credits >= 1 AND credits <= 6', name='check_credits_range'),
        db.CheckConstraint('max_students >= 1 AND max_students <= 200', name='check_max_students'),
        db.CheckConstraint('min_capacity >= 1', name='check_min_capacity'),
    )

# New model for course-teacher assignments (many-to-many)
class CourseTeacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)  # Primary teacher for the course
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='course_teachers')
    teacher = db.relationship('User', backref='course_assignments')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('course_id', 'teacher_id', name='unique_course_teacher'),
    )

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(50), nullable=False)
    room_type = db.Column(db.String(50), default='lecture')
    floor = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='active')
    facilities = db.Column(db.Text)
    equipment = db.Column(db.String(200))
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('capacity >= 1 AND capacity <= 500', name='check_capacity_range'),
        db.CheckConstraint('floor >= 0 AND floor <= 20', name='check_floor_range'),
    )

class TimeSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM format
    end_time = db.Column(db.String(10), nullable=False)  # HH:MM format
    break_type = db.Column(db.String(20), default='none')
    notes = db.Column(db.Text)

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
    
    # Constraints - Unique constraint to prevent double booking
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'time_slot_id', 'semester', 'academic_year', 
                           name='unique_classroom_time_slot'),
        db.UniqueConstraint('teacher_id', 'time_slot_id', 'semester', 'academic_year', 
                           name='unique_teacher_time_slot'),
    )

class StudentGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('User', backref='student_group', lazy=True)
    courses = db.relationship('StudentGroupCourse', backref='group', lazy=True)

class StudentGroupCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('student_group_id', 'course_id', name='unique_group_course'),
    )

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
        total_student_groups = StudentGroup.query.count()
        
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
        total_student_groups = 0
        recent_attendance = []
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         total_faculty=total_faculty,
                         total_courses=total_courses,
                         total_classrooms=total_classrooms,
                         total_time_slots=total_time_slots,
                         total_timetables=total_timetables,
                         total_attendance=total_attendance,
                         total_student_groups=total_student_groups,
                         recent_attendance=recent_attendance)

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get faculty's courses and timetables
        # Get courses where faculty is assigned as teacher
        course_assignments = CourseTeacher.query.filter_by(teacher_id=current_user.id).all()
        course_ids = [assignment.course_id for assignment in course_assignments]
        courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
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
    
    # Get filter parameters
    role_filter = request.args.get('role', '')
    department_filter = request.args.get('department', '')
    
    # Build query with filters
    query = User.query
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if department_filter:
        query = query.filter(User.department == department_filter)
    
    users = query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    department_filter = request.args.get('department', '')
    credits_filter = request.args.get('credits', '')
    
    # Build query with filters
    query = Course.query
    
    if department_filter:
        query = query.filter(Course.department == department_filter)
    
    if credits_filter:
        query = query.filter(Course.credits == int(credits_filter))
    
    courses = query.all()
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/courses.html', courses=courses, teachers=teachers)

@app.route('/admin/classrooms')
@login_required
def admin_classrooms():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    building_filter = request.args.get('building', '')
    capacity_filter = request.args.get('capacity', '')
    
    # Build query with filters
    query = Classroom.query
    
    if building_filter:
        query = query.filter(Classroom.building == building_filter)
    
    if capacity_filter:
        if capacity_filter == 'small':
            query = query.filter(Classroom.capacity <= 30)
        elif capacity_filter == 'medium':
            query = query.filter(Classroom.capacity > 30, Classroom.capacity <= 100)
        elif capacity_filter == 'large':
            query = query.filter(Classroom.capacity > 100)
    
    classrooms = query.all()
    return render_template('admin/classrooms.html', classrooms=classrooms)

@app.route('/admin/timetable')
@login_required
def admin_timetable():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get filter parameters
        day_filter = request.args.get('day', '')
        course_filter = request.args.get('course', '')
        teacher_filter = request.args.get('teacher', '')
        classroom_filter = request.args.get('classroom', '')
        semester_filter = request.args.get('semester', '')
        time_slot_filter = request.args.get('time_slot', '')
        
        # Build query with filters
        query = Timetable.query
        
        if day_filter:
            query = query.join(TimeSlot).filter(TimeSlot.day == day_filter)
        
        if course_filter:
            query = query.filter(Timetable.course_id == course_filter)
        
        if teacher_filter:
            query = query.filter(Timetable.teacher_id == teacher_filter)
        
        if classroom_filter:
            query = query.filter(Timetable.classroom_id == classroom_filter)
        
        if semester_filter:
            query = query.filter(Timetable.semester == semester_filter)
        
        if time_slot_filter:
            start_time, end_time = time_slot_filter.split('-')
            query = query.join(TimeSlot).filter(
                TimeSlot.start_time == start_time,
                TimeSlot.end_time == end_time
            )
        
        timetables = query.all()
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

@app.route('/admin/export_timetable')
@login_required
def admin_export_timetable():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Apply same filters as the main view
        day_filter = request.args.get('day', '')
        course_filter = request.args.get('course', '')
        teacher_filter = request.args.get('teacher', '')
        classroom_filter = request.args.get('classroom', '')
        semester_filter = request.args.get('semester', '')
        time_slot_filter = request.args.get('time_slot', '')
        
        query = Timetable.query
        
        if day_filter:
            query = query.join(TimeSlot).filter(TimeSlot.day == day_filter)
        if course_filter:
            query = query.filter(Timetable.course_id == course_filter)
        if teacher_filter:
            query = query.filter(Timetable.teacher_id == teacher_filter)
        if classroom_filter:
            query = query.filter(Timetable.classroom_id == classroom_filter)
        if semester_filter:
            query = query.filter(Timetable.semester == semester_filter)
        if time_slot_filter:
            start_time, end_time = time_slot_filter.split('-')
            query = query.join(TimeSlot).filter(
                TimeSlot.start_time == start_time,
                TimeSlot.end_time == end_time
            )
        
        timetables = query.all()
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Day', 'Time', 'Course Code', 'Course Name', 'Teacher', 'Teacher Initials', 'Classroom', 'Building', 'Semester', 'Academic Year'])
        
        # Write data
        for tt in timetables:
            time_slot = TimeSlot.query.get(tt.time_slot_id)
            course = Course.query.get(tt.course_id)
            teacher = User.query.get(tt.teacher_id)
            classroom = Classroom.query.get(tt.classroom_id)
            
            if all([time_slot, course, teacher, classroom]):
                teacher_initials = f"{teacher.name.split()[-1][0]}{teacher.name.split()[0][0]}"
                writer.writerow([
                    time_slot.day,
                    f"{time_slot.start_time}-{time_slot.end_time}",
                    course.code,
                    course.name,
                    teacher.name,
                    teacher_initials,
                    classroom.room_number,
                    classroom.building,
                    tt.semester,
                    tt.academic_year
                ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=timetable_export.csv'}
        )
        
    except Exception as e:
        flash(f'Error exporting timetable: {str(e)}', 'error')
        return redirect(url_for('admin_timetable'))

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
        
        # Assign to group if student
        if role == 'student' and request.form.get('group_id'):
            user.group_id = int(request.form['group_id'])
        db.session.add(user)
        db.session.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('admin_users'))
    
    # Get student groups for the form
    student_groups = StudentGroup.query.all()
    return render_template('admin/add_user.html', student_groups=student_groups)

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
        semester = request.form.get('semester', '1')
        description = request.form.get('description', '')
        subject_area = request.form['subject_area']
        required_equipment = request.form.get('required_equipment', '')
        min_capacity = int(request.form.get('min_capacity', 1))
        periods_per_week = int(request.form.get('periods_per_week', 3))
        
        if Course.query.filter_by(code=code).first():
            flash('Course code already exists', 'error')
            return redirect(url_for('admin_add_course'))
        
            course = Course(
                code=code,
                name=name,
                credits=credits,
                department=department,
                max_students=max_students,
                semester=semester,
                description=description,
                subject_area=subject_area,
                required_equipment=required_equipment,
                min_capacity=min_capacity,
                periods_per_week=periods_per_week
            )
        db.session.add(course)
        db.session.flush()  # Get the course ID
        
        # Add teacher assignment if specified
        if teacher_id:
            course_teacher = CourseTeacher(
                course_id=course.id,
                teacher_id=teacher_id,
                is_primary=True
            )
            db.session.add(course_teacher)
        
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
        room_type = request.form.get('room_type', 'lecture')
        floor = int(request.form.get('floor', 1))
        status = request.form.get('status', 'active')
        equipment = request.form.get('equipment', '')
        facilities = request.form.get('facilities', '')
        
        if Classroom.query.filter_by(room_number=room_number).first():
            flash('Room number already exists', 'error')
            return redirect(url_for('admin_add_classroom'))
        
        classroom = Classroom(
            room_number=room_number,
            capacity=capacity,
            building=building,
            room_type=room_type,
            floor=floor,
            status=status,
            equipment=equipment,
            facilities=facilities
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
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        user.department = request.form['department']
        user.phone = request.form.get('phone', '')
        user.address = request.form.get('address', '')
        
        # Handle group assignment for students
        if user.role == 'student' and request.form.get('group_id'):
            user.group_id = int(request.form['group_id'])
        elif user.role != 'student':
            user.group_id = None
        
        # Only update password if provided
        if request.form.get('password'):
            user.password_hash = generate_password_hash(request.form['password'])
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    # Get student groups for the form
    student_groups = StudentGroup.query.all()
    return render_template('admin/edit_user.html', user=user, student_groups=student_groups)

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
        course.code = request.form['code']
        course.name = request.form['name']
        course.credits = int(request.form['credits'])
        course.department = request.form['department']
        course.max_students = int(request.form['max_students'])
        course.semester = request.form.get('semester', '1')
        course.description = request.form.get('description', '')
        course.subject_area = request.form['subject_area']
        course.required_equipment = request.form.get('required_equipment', '')
        course.min_capacity = int(request.form.get('min_capacity', 1))
        course.periods_per_week = int(request.form.get('periods_per_week', 3))
        
        # Handle teacher assignment
        teacher_id = int(request.form['teacher_id']) if request.form['teacher_id'] else None
        
        # Remove existing teacher assignments
        CourseTeacher.query.filter_by(course_id=course.id).delete()
        
        # Add new teacher assignment if specified
        if teacher_id:
            course_teacher = CourseTeacher(
                course_id=course.id,
                teacher_id=teacher_id,
                is_primary=True
            )
            db.session.add(course_teacher)
        
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
        classroom.room_type = request.form.get('room_type', 'lecture')
        classroom.floor = int(request.form.get('floor', 1))
        classroom.status = request.form.get('status', 'active')
        classroom.facilities = request.form.get('facilities', '')
        classroom.equipment = request.form.get('equipment', '')
        
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

# Student Group Management Routes
@app.route('/admin/student_groups')
@login_required
def admin_student_groups():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Load groups with relationships
    groups = StudentGroup.query.all()
    
    # Ensure relationships are loaded for each group
    for group in groups:
        if not hasattr(group, 'students') or not group.students:
            group.students = User.query.filter_by(group_id=group.id, role='student').all()
        if not hasattr(group, 'courses') or not group.courses:
            group_courses = StudentGroupCourse.query.filter_by(student_group_id=group.id).all()
            group.courses = [Course.query.get(sgc.course_id) for sgc in group_courses if Course.query.get(sgc.course_id)]
    
    return render_template('admin/student_groups.html', groups=groups)

@app.route('/admin/add_student_group', methods=['GET', 'POST'])
@login_required
def admin_add_student_group():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        department = request.form['department']
        year = int(request.form['year'])
        semester = int(request.form['semester'])
        
        if StudentGroup.query.filter_by(name=name, department=department).first():
            flash('Student group already exists for this department', 'error')
            return redirect(url_for('admin_add_student_group'))
        
        group = StudentGroup(
            name=name,
            department=department,
            year=year,
            semester=semester
        )
        db.session.add(group)
        db.session.commit()
        flash('Student group added successfully', 'success')
        return redirect(url_for('admin_student_groups'))
    
    return render_template('admin/add_student_group.html')

@app.route('/admin/edit_student_group/<int:group_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_student_group(group_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    group = StudentGroup.query.get_or_404(group_id)
    
    if request.method == 'POST':
        group.name = request.form['name']
        group.department = request.form['department']
        group.year = int(request.form['year'])
        group.semester = int(request.form['semester'])
        
        db.session.commit()
        flash('Student group updated successfully', 'success')
        return redirect(url_for('admin_student_groups'))
    
    return render_template('admin/edit_student_group.html', group=group)

@app.route('/admin/delete_student_group/<int:group_id>', methods=['POST'])
@login_required
def admin_delete_student_group(group_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    group = StudentGroup.query.get_or_404(group_id)
    
    # Check if group has students
    if group.students:
        flash('Cannot delete group with assigned students', 'error')
        return redirect(url_for('admin_student_groups'))
    
    db.session.delete(group)
    db.session.commit()
    flash('Student group deleted successfully', 'success')
    return redirect(url_for('admin_student_groups'))

@app.route('/admin/manage_group_courses/<int:group_id>', methods=['GET', 'POST'])
@login_required
def admin_manage_group_courses(group_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    group = StudentGroup.query.get_or_404(group_id)
    
    if request.method == 'POST':
        course_ids = request.form.getlist('courses')
        
        # Remove existing course assignments
        StudentGroupCourse.query.filter_by(student_group_id=group_id).delete()
        
        # Add new course assignments
        for course_id in course_ids:
            if course_id:
                group_course = StudentGroupCourse(
                    student_group_id=group_id,
                    course_id=int(course_id)
                )
                db.session.add(group_course)
        
        db.session.commit()
        flash('Group courses updated successfully', 'success')
        return redirect(url_for('admin_student_groups'))
    
    # Get all courses and current group courses
    all_courses = Course.query.all()
    current_course_ids = [gc.course_id for gc in group.courses]
    
    return render_template('admin/manage_group_courses.html', 
                         group=group, 
                         all_courses=all_courses, 
                         current_course_ids=current_course_ids)

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
    course_teacher = CourseTeacher.query.filter_by(course_id=course_id, teacher_id=current_user.id).first()
    if not course_teacher:
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
    course_teacher = CourseTeacher.query.filter_by(course_id=course_id, teacher_id=current_user.id).first()
    if not course_teacher:
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

def is_teacher_qualified(teacher, subject_area):
    """Check if teacher is qualified to teach a specific subject area"""
    if not teacher.qualifications:
        return False
    
    # Simple qualification check based on subject area
    qualifications = teacher.qualifications.lower()
    subject_area_lower = subject_area.lower()
    
    # Define qualification mappings
    qualification_mappings = {
        'computer science': ['computer science', 'software engineering', 'information technology', 'cs', 'it'],
        'mathematics': ['mathematics', 'math', 'applied mathematics', 'statistics'],
        'physics': ['physics', 'physical sciences'],
        'chemistry': ['chemistry', 'chemical', 'organic chemistry', 'inorganic chemistry'],
        'english': ['english', 'literature', 'language'],
        'economics': ['economics', 'economic', 'business', 'finance']
    }
    
    if subject_area_lower in qualification_mappings:
        required_qualifications = qualification_mappings[subject_area_lower]
        return any(qual in qualifications for qual in required_qualifications)
    
    return True  # Default to allowing if no specific mapping

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
        
        # Check if teacher is qualified for this course
        course = Course.query.get(course_id)
        teacher = User.query.get(teacher_id)
        classroom = Classroom.query.get(classroom_id)
        
        if not course or not teacher or not classroom:
            flash('Invalid course, teacher, or classroom selected', 'error')
            return redirect(url_for('admin_timetable'))
        
        # Check if teacher is qualified for this subject
        if not is_teacher_qualified(teacher, course.subject_area):
            flash(f'Teacher {teacher.name} is not qualified to teach {course.subject_area}', 'error')
            return redirect(url_for('admin_timetable'))
        
        # Check classroom capacity constraint
        if classroom.capacity < course.min_capacity:
            flash(f'Classroom {classroom.room_number} capacity ({classroom.capacity}) is less than required minimum ({course.min_capacity})', 'error')
            return redirect(url_for('admin_timetable'))
        
        # Check equipment constraints
        if course.required_equipment:
            required_equipment = [eq.strip().lower() for eq in course.required_equipment.split(',')]
            classroom_equipment = [eq.strip().lower() for eq in (classroom.equipment or '').split(',')]
            
            missing_equipment = [eq for eq in required_equipment if eq and eq not in classroom_equipment]
            if missing_equipment:
                flash(f'Classroom {classroom.room_number} is missing required equipment: {", ".join(missing_equipment)}', 'error')
                return redirect(url_for('admin_timetable'))
        
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
                name='System Administrator',
                department='IT',
                phone='+91-9876543210',
                address='Main Campus, IT Department',
                qualifications='M.Tech, PhD in Computer Science'
            )
            db.session.add(admin)
            db.session.commit()
        
        # Add sample data if database is empty
        if not User.query.filter_by(role='faculty').first():
            # Create sample faculty
            faculty1 = User(
                username='faculty',
                email='faculty@institution.com',
                password_hash=generate_password_hash('faculty123'),
                role='faculty',
                name='Dr. John Smith',
                department='Computer Science',
                phone='+91-9876543211',
                address='Computer Science Department, Room 201',
                qualifications='PhD in Computer Science, 10 years experience'
            )
            faculty2 = User(
                username='faculty2',
                email='faculty2@institution.com',
                password_hash=generate_password_hash('faculty123'),
                role='faculty',
                name='Prof. Jane Doe',
                department='Mathematics',
                phone='+91-9876543212',
                address='Mathematics Department, Room 105',
                qualifications='PhD in Mathematics, 8 years experience'
            )
            db.session.add_all([faculty1, faculty2])
            db.session.commit()
        
        if not StudentGroup.query.first():
            # Create sample student groups
            group1 = StudentGroup(
                name='CS-2024-1',
                department='Computer Science',
                year=2024,
                semester=1
            )
            group2 = StudentGroup(
                name='CS-2024-2',
                department='Computer Science',
                year=2024,
                semester=2
            )
            group3 = StudentGroup(
                name='MATH-2024-1',
                department='Mathematics',
                year=2024,
                semester=1
            )
            db.session.add_all([group1, group2, group3])
            db.session.commit()
        
        if not User.query.filter_by(role='student').first():
            # Create sample students
            group1 = StudentGroup.query.filter_by(name='CS-2024-1').first()
            group2 = StudentGroup.query.filter_by(name='MATH-2024-1').first()
            
            student1 = User(
                username='student',
                email='student@institution.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                name='Alice Johnson',
                department='Computer Science',
                group_id=group1.id if group1 else None,
                phone='+91-9876543213',
                address='Student Hostel Block A, Room 101',
                qualifications='12th Standard, Computer Science Stream'
            )
            student2 = User(
                username='student2',
                email='student2@institution.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                name='Bob Wilson',
                department='Computer Science',
                group_id=group1.id if group1 else None,
                phone='+91-9876543214',
                address='Student Hostel Block A, Room 102',
                qualifications='12th Standard, Computer Science Stream'
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
                max_students=50,
                semester='1',
                description='Fundamental concepts of computer science and programming',
                subject_area='Computer Science',
                periods_per_week=3
            )
            course2 = Course(
                code='MATH101',
                name='Calculus I',
                credits=4,
                department='Mathematics',
                max_students=40,
                semester='1',
                description='Introduction to differential and integral calculus',
                subject_area='Mathematics',
                periods_per_week=4
            )
            db.session.add_all([course1, course2])
            db.session.flush()  # Get course IDs
            
            # Add teacher assignments
            if faculty1:
                course_teacher1 = CourseTeacher(
                    course_id=course1.id,
                    teacher_id=faculty1.id,
                    is_primary=True
                )
                db.session.add(course_teacher1)
            
            if faculty2:
                course_teacher2 = CourseTeacher(
                    course_id=course2.id,
                    teacher_id=faculty2.id,
                    is_primary=True
                )
                db.session.add(course_teacher2)
            
            db.session.commit()
        
        if not Classroom.query.first():
            # Create sample classrooms
            classroom1 = Classroom(
                room_number='101',
                capacity=50,
                building='Science Building',
                room_type='lecture',
                floor=1,
                status='active',
                facilities='Projector, Whiteboard, Air Conditioning',
                equipment='Projector, Whiteboard'
            )
            classroom2 = Classroom(
                room_number='205',
                capacity=40,
                building='Mathematics Building',
                room_type='seminar',
                floor=2,
                status='active',
                facilities='Smart Board, Computer, Whiteboard',
                equipment='Smart Board, Computer'
            )
            db.session.add_all([classroom1, classroom2])
            db.session.commit()
        
        if not TimeSlot.query.first():
            # Create sample time slots
            time_slots = [
                TimeSlot(day='Monday', start_time='09:00', end_time='10:00', break_type='none'),
                TimeSlot(day='Monday', start_time='10:00', end_time='11:00', break_type='short'),
                TimeSlot(day='Tuesday', start_time='09:00', end_time='10:00', break_type='none'),
                TimeSlot(day='Tuesday', start_time='10:00', end_time='11:00', break_type='short'),
                TimeSlot(day='Wednesday', start_time='09:00', end_time='10:00', break_type='none'),
                TimeSlot(day='Wednesday', start_time='10:00', end_time='11:00', break_type='short'),
                TimeSlot(day='Thursday', start_time='09:00', end_time='10:00', break_type='none'),
                TimeSlot(day='Thursday', start_time='10:00', end_time='11:00', break_type='short'),
                TimeSlot(day='Friday', start_time='09:00', end_time='10:00', break_type='none'),
                TimeSlot(day='Friday', start_time='10:00', end_time='11:00', break_type='short'),
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

# Missing routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user (default role is student)
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='student',
            name=username,
            department='General'
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/api/courses')
def api_courses():
    courses = Course.query.all()
    return jsonify([{
        'id': course.id,
        'code': course.code,
        'name': course.name,
        'credits': course.credits,
        'department': course.department
    } for course in courses])

@app.route('/api/classrooms')
def api_classrooms():
    classrooms = Classroom.query.all()
    return jsonify([{
        'id': classroom.id,
        'room_number': classroom.room_number,
        'building': classroom.building,
        'capacity': classroom.capacity,
        'room_type': classroom.room_type
    } for classroom in classrooms])

@app.route('/api/time_slots')
def api_time_slots():
    time_slots = TimeSlot.query.all()
    return jsonify([{
        'id': time_slot.id,
        'day': time_slot.day,
        'start_time': time_slot.start_time,
        'end_time': time_slot.end_time
    } for time_slot in time_slots])

# Automatic Timetable Generation Routes
@app.route('/admin/clear_timetables', methods=['POST'])
@login_required
def admin_clear_timetables():
    """Clear all existing timetables"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        existing_count = Timetable.query.count()
        if existing_count > 0:
            Timetable.query.delete()
            db.session.commit()
            flash(f'🗑️ Successfully cleared {existing_count} existing timetables', 'success')
        else:
            flash('ℹ️ No existing timetables to clear', 'info')
        
        return redirect(url_for('admin_generate_timetables'))
        
    except Exception as e:
        flash(f'Error clearing timetables: {str(e)}', 'error')
        return redirect(url_for('admin_generate_timetables'))

@app.route('/admin/generate_timetables', methods=['GET', 'POST'])
@login_required
def admin_generate_timetables():
    """Generate automatic timetables for all student groups"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Initialize timetable generator
            generator = TimetableGenerator()
            
            # Get all time slots
            time_slots = TimeSlot.query.all()
            gen_time_slots = [GenTimeSlot(
                id=ts.id, day=ts.day, start_time=ts.start_time, end_time=ts.end_time
            ) for ts in time_slots]
            generator.add_time_slots(gen_time_slots)
            
            # Get all courses
            courses = Course.query.all()
            gen_courses = [GenCourse(
                id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
                department=c.department, required_equipment=c.required_equipment or '',
                min_capacity=c.min_capacity, max_students=c.max_students
            ) for c in courses]
            generator.add_courses(gen_courses)
            
            # Get all classrooms
            classrooms = Classroom.query.all()
            gen_classrooms = [GenClassroom(
                id=c.id, room_number=c.room_number, capacity=c.capacity,
                room_type=c.room_type, equipment=c.equipment or '', building=c.building
            ) for c in classrooms]
            generator.add_classrooms(gen_classrooms)
            
            # Get all teachers with availability (simplified - all available)
            teachers = User.query.filter_by(role='faculty').all()
            gen_teachers = []
            for teacher in teachers:
                # Create default availability for all time slots
                availability = {}
                for ts in time_slots:
                    if ts.day not in availability:
                        availability[ts.day] = []
                    availability[ts.day].append(ts.start_time)
                
                gen_teachers.append(GenTeacher(
                    id=teacher.id, name=teacher.name, department=teacher.department,
                    availability=availability
                ))
            generator.add_teachers(gen_teachers)
            
            # Get all student groups with their courses
            student_groups = StudentGroup.query.all()
            gen_student_groups = []
            for group in student_groups:
                # Get courses for this group
                group_courses = []
                for course in courses:
                    if course.department == group.department:
                        group_courses.append(GenCourse(
                            id=course.id, code=course.code, name=course.name,
                            periods_per_week=course.periods_per_week,
                            department=course.department, required_equipment=course.required_equipment or '',
                            min_capacity=course.min_capacity, max_students=course.max_students
                        ))
                
                gen_student_groups.append(GenStudentGroup(
                    id=group.id, name=group.name, department=group.department,
                    courses=group_courses
                ))
            generator.add_student_groups(gen_student_groups)
            
            # Check feasibility before generation
            feasibility = generator.check_feasibility()
            if not feasibility['feasible']:
                flash(f'❌ Timetable generation not possible: {feasibility["reason"]}', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
            # Generate timetables
            print("🔄 Starting timetable generation...")
            generated_timetables = generator.generate_timetables()
            
            # Check if generation was successful
            if not generated_timetables:
                flash('❌ No timetables could be generated. The system may be over-constrained.', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
            print(f"✅ Generated {len(generated_timetables)} group timetables")
            
            # Save generated timetables to database
            # Check if user wants to clear existing timetables
            clear_existing = request.form.get('clear_existing') == 'on'
            
            if clear_existing:
                existing_count = Timetable.query.count()
                if existing_count > 0:
                    print(f"🗑️ Clearing {existing_count} existing timetables...")
                    Timetable.query.delete()
                    db.session.commit()
                    print("✅ Existing timetables cleared")
            else:
                print("ℹ️ Keeping existing timetables (clear_existing not checked)")
            
            # Now check for internal conflicts within the generated timetables
            conflicts_found = []
            global_classroom_usage = {}  # (day, time) -> classroom_id
            global_teacher_usage = {}    # (day, time) -> teacher_id
            
            for group_id, entries in generated_timetables.items():
                for entry in entries:
                    slot_key = (entry.day, entry.start_time)
                    
                    # Check for classroom conflicts within generated data
                    if slot_key in global_classroom_usage:
                        conflicts_found.append(f"Classroom {entry.classroom_number} double-booked at {entry.day} {entry.start_time}")
                        continue
                    
                    # Check for teacher conflicts within generated data
                    if slot_key in global_teacher_usage:
                        conflicts_found.append(f"Teacher {entry.teacher_name} double-booked at {entry.day} {entry.start_time}")
                        continue
                    
                    # Mark as used
                    global_classroom_usage[slot_key] = entry.classroom_id
                    global_teacher_usage[slot_key] = entry.teacher_id
            
            if conflicts_found:
                print(f"❌ Found {len(conflicts_found)} conflicts in generated timetables")
                for conflict in conflicts_found[:5]:
                    print(f"⚠️ {conflict}")
                
                # Try to regenerate with stricter constraints
                flash(f'❌ Generated timetables have {len(conflicts_found)} internal conflicts. Please try again or adjust constraints.', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
            print("✅ No conflicts detected in generated timetables")
            
            # Add new timetables
            timetables_added = 0
            for group_id, entries in generated_timetables.items():
                for entry in entries:
                    # Get the actual database objects
                    course = Course.query.get(entry.course_id)
                    teacher = User.query.get(entry.teacher_id)
                    classroom = Classroom.query.get(entry.classroom_id)
                    time_slot = TimeSlot.query.get(entry.time_slot_id)
                    
                    if all([course, teacher, classroom, time_slot]):
                        timetable = Timetable(
                            course_id=entry.course_id,
                            teacher_id=entry.teacher_id,
                            classroom_id=entry.classroom_id,
                            time_slot_id=entry.time_slot_id,
                            semester='Fall 2024',
                            academic_year='2024-25'
                        )
                        db.session.add(timetable)
                        timetables_added += 1
                    else:
                        print(f"⚠️ Missing data for entry: course={entry.course_id}, teacher={entry.teacher_id}, classroom={entry.classroom_id}, time_slot={entry.time_slot_id}")
            
            db.session.commit()
            print(f"✅ Saved {timetables_added} timetable entries to database")
            
            # Get statistics
            stats = generator.get_statistics()
            
            flash(f'Timetables generated successfully! {stats["total_periods"]} periods scheduled for {stats["total_groups"]} groups.', 'success')
            
            if generator.conflicts:
                flash(f'⚠️ {len(generator.conflicts)} conflicts detected. Please review manually.', 'warning')
            
            return redirect(url_for('admin_timetable'))
            
        except Exception as e:
            flash(f'Error generating timetables: {str(e)}', 'error')
            return redirect(url_for('admin_timetable'))
    
    return render_template('admin/generate_timetables.html',
                         student_groups=StudentGroup.query.all(),
                         courses=Course.query.all(),
                         teachers=User.query.filter_by(role='faculty').all(),
                         classrooms=Classroom.query.all(),
                         existing_timetables=Timetable.query.all(),
                         expected_periods=sum(c.periods_per_week for c in Course.query.all()))

@app.route('/admin/check_timetable_feasibility')
@login_required
def admin_check_timetable_feasibility():
    """Check if timetable generation is feasible"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Initialize timetable generator
        generator = TimetableGenerator()
        
        # Get all time slots
        time_slots = TimeSlot.query.all()
        gen_time_slots = [GenTimeSlot(
            id=ts.id, day=ts.day, start_time=ts.start_time, end_time=ts.end_time
        ) for ts in time_slots]
        generator.add_time_slots(gen_time_slots)
        
        # Get all courses
        courses = Course.query.all()
        gen_courses = [GenCourse(
            id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
            department=c.department, required_equipment=c.required_equipment or '',
            min_capacity=c.min_capacity, max_students=c.max_students
        ) for c in courses]
        generator.add_courses(gen_courses)
        
        # Get all classrooms
        classrooms = Classroom.query.all()
        generator.add_classrooms([GenClassroom(
            id=c.id, room_number=c.room_number, capacity=c.capacity,
            room_type=c.room_type, equipment=c.equipment or '', building=c.building
        ) for c in classrooms])
        
        # Get all student groups
        student_groups = StudentGroup.query.all()
        gen_student_groups = []
        for group in student_groups:
            group_courses = []
            for course in courses:
                if course.department == group.department:
                    group_courses.append(GenCourse(
                        id=course.id, code=course.code, name=course.name,
                        periods_per_week=course.periods_per_week,
                        department=course.department, required_equipment=course.required_equipment or '',
                        min_capacity=course.min_capacity, max_students=course.max_students
                    ))
            
            gen_student_groups.append(GenStudentGroup(
                id=group.id, name=group.name, department=group.department,
                courses=group_courses
            ))
        generator.add_student_groups(gen_student_groups)
        
        # Check feasibility
        feasibility = generator.check_feasibility()
        
        # Add suggestions if not feasible
        if not feasibility['feasible']:
            suggestions = generator.get_constraint_suggestions()
            feasibility['suggestions'] = suggestions
        
        return jsonify(feasibility)
        
    except Exception as e:
        return jsonify({
            'feasible': False,
            'reason': f'Error checking feasibility: {str(e)}'
        })

@app.route('/admin/timetable_statistics')
@login_required
def admin_timetable_statistics():
    """Show timetable statistics and conflicts"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get basic statistics
    total_timetables = Timetable.query.count()
    total_courses = Course.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_faculty = User.query.filter_by(role='faculty').count()
    
    # Get timetable distribution by day
    day_distribution = db.session.query(
        TimeSlot.day, db.func.count(Timetable.id)
    ).join(Timetable, TimeSlot.id == Timetable.time_slot_id).group_by(TimeSlot.day).all()
    
    # Get classroom utilization
    classroom_utilization = db.session.query(
        Classroom.room_number, db.func.count(Timetable.id)
    ).join(Timetable, Classroom.id == Timetable.classroom_id).group_by(Classroom.room_number).all()
    
    return render_template('admin/timetable_statistics.html',
                         total_timetables=total_timetables,
                         total_courses=total_courses,
                         total_students=total_students,
                         total_faculty=total_faculty,
                         day_distribution=day_distribution,
                         classroom_utilization=classroom_utilization)

@app.route('/admin/export_timetables')
@login_required
def admin_export_timetables():
    """Export all timetables to CSV"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        import csv
        from io import StringIO
        
        # Get all timetables with related data
        timetables = db.session.query(
            Timetable, Course, User, Classroom, TimeSlot, StudentGroup
        ).join(
            Course, Timetable.course_id == Course.id
        ).join(
            User, Timetable.teacher_id == User.id
        ).join(
            Classroom, Timetable.classroom_id == Classroom.id
        ).join(
            TimeSlot, Timetable.time_slot_id == TimeSlot.id
        ).join(
            StudentGroup, User.group_id == StudentGroup.id
        ).filter(
            User.role == 'student'
        ).all()
        
        # Create CSV data
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Day', 'Time', 'Course Code', 'Course Name', 'Teacher', 'Classroom', 'Student Group'])
        
        for timetable, course, user, classroom, time_slot, student_group in timetables:
            writer.writerow([
                time_slot.day,
                f"{time_slot.start_time}-{time_slot.end_time}",
                course.code,
                course.name,
                user.name,
                classroom.room_number,
                student_group.name if student_group else 'No Group'
            ])
        
        output.seek(0)
        
        from flask import send_file
        return send_file(
            StringIO(output.getvalue()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'timetables_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        flash(f'Error exporting timetables: {str(e)}', 'error')
        return redirect(url_for('admin_timetable'))

@app.route('/faculty/my_timetable')
@login_required
def faculty_my_timetable():
    """Show faculty member's personal timetable"""
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get faculty's timetable
    faculty_timetables = db.session.query(
        Timetable, Course, Classroom, TimeSlot
    ).join(
        Course, Timetable.course_id == Course.id
    ).join(
        Classroom, Timetable.classroom_id == Classroom.id
    ).join(
        TimeSlot, Timetable.time_slot_id == TimeSlot.id
    ).filter(
        Timetable.teacher_id == current_user.id
    ).order_by(
        TimeSlot.day, TimeSlot.start_time
    ).all()
    
    # Group by day
    timetable_by_day = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for day in days:
        timetable_by_day[day] = []
    
    for timetable, course, classroom, time_slot in faculty_timetables:
        if time_slot.day in timetable_by_day:
            timetable_by_day[time_slot.day].append({
                'time': f"{time_slot.start_time}-{time_slot.end_time}",
                'course': f"{course.code} - {course.name}",
                'classroom': classroom.room_number,
                'building': classroom.building
            })
    
    return render_template('faculty/my_timetable.html', timetable_by_day=timetable_by_day)

@app.route('/student/my_timetable')
@login_required
def student_my_timetable():
    """Show student's personal timetable"""
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.group_id:
        flash('You are not assigned to any student group', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Get student's group timetable
    group_timetables = db.session.query(
        Timetable, Course, User, Classroom, TimeSlot
    ).join(
        Course, Timetable.course_id == Course.id
    ).join(
        User, Timetable.teacher_id == User.id
    ).join(
        Classroom, Timetable.classroom_id == Classroom.id
    ).join(
        TimeSlot, Timetable.time_slot_id == TimeSlot.id
    ).filter(
        Course.department == current_user.department
    ).order_by(
        TimeSlot.day, TimeSlot.start_time
    ).all()
    
    # Group by day
    timetable_by_day = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    for day in days:
        timetable_by_day[day] = []
    
    for timetable, course, teacher, classroom, time_slot in group_timetables:
        if time_slot.day in timetable_by_day:
            timetable_by_day[time_slot.day].append({
                'time': f"{time_slot.start_time}-{time_slot.end_time}",
                'course': f"{course.code} - {course.name}",
                'teacher': teacher.name,
                'classroom': classroom.room_number,
                'building': classroom.building
            })
    
    return render_template('student/my_timetable.html', timetable_by_day=timetable_by_day)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
