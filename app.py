from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import schedule
import time
import threading
import json
import os
from dotenv import load_dotenv
from timetable_generator import MultiGroupTimetableGenerator, TimeSlot as GenTimeSlot, Course as GenCourse, Classroom as GenClassroom, StudentGroup as GenStudentGroup, Teacher as GenTeacher
from collections import defaultdict
import sqlite3
import csv
from io import StringIO, BytesIO
from werkzeug.utils import secure_filename
import qrcode
import base64
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import QueuePool

# Load environment variables if .env file exists
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    # Set default environment variables
    if not os.getenv('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    if not os.getenv('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'your-secret-key-here'

# Ensure we have required environment variables set
if not os.getenv('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'
if not os.getenv('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'your-secret-key-here'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Custom Jinja2 filter for safe datetime formatting
@app.template_filter('safe_strftime')
def safe_strftime(value, format_string):
    """Safely format datetime objects, handling both datetime and string inputs"""
    if value is None:
        return 'N/A'
    if hasattr(value, 'strftime'):
        try:
            return value.strftime(format_string)
        except (ValueError, TypeError):
            return str(value)
    return str(value)

# Database configuration - PostgreSQL preferred, SQLite fallback for development
database_url = os.getenv('DATABASE_URL')
flask_env = os.getenv('FLASK_ENV', 'development')

if database_url:
    # PostgreSQL is available (production/render)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    # Use enhanced engine with connection pooling for PostgreSQL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    }
    print(f"✅ Using PostgreSQL database with enhanced connection pooling")
elif flask_env == 'production':
    # Production but no DATABASE_URL - this shouldn't happen
    raise ValueError("DATABASE_URL environment variable must be set in production")
else:
    # Development - use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(app.instance_path, "timetable_attendance.db")}'
    print(f"✅ Using SQLite database for development")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Start the background scheduler for automatic absent marking
# This will be called after the function is defined

# Register database event handlers after app context is available
with app.app_context():
    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance"""
        if 'sqlite' in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    @event.listens_for(db.engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Handle connection checkout"""
        try:
            # Test connection before use
            cursor = dbapi_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except Exception as e:
            print(f"Connection checkout failed: {e}")
            # Mark connection as invalid
            connection_proxy._pool.dispose()
            raise e

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, faculty, student
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    qualifications = db.Column(db.Text)  # For faculty - their teaching qualifications
    experience = db.Column(db.Integer)  # Years of experience for faculty
    bio = db.Column(db.Text)  # User bio/description
    access_level = db.Column(db.String(20), default='admin')  # For admin users
    group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'))  # For students only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

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
    
    @property
    def teacher(self):
        """Get the primary teacher assigned to this course"""
        primary_teacher = CourseTeacher.query.filter_by(
            course_id=self.id, 
            is_primary=True
        ).first()
        return primary_teacher.teacher if primary_teacher else None
    
    @property
    def teacher_id(self):
        """Get the primary teacher ID assigned to this course"""
        primary_teacher = CourseTeacher.query.filter_by(
            course_id=self.id, 
            is_primary=True
        ).first()
        return primary_teacher.teacher_id if primary_teacher else None

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
    student_group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_session.id'), nullable=False)
    # Keep old fields for backward compatibility during migration
    semester = db.Column(db.String(20), nullable=True)  # Now nullable for migration
    academic_year = db.Column(db.String(10), nullable=True)  # Now nullable for migration
    
    # Relationships
    course = db.relationship('Course', backref='timetable_entries')
    classroom = db.relationship('Classroom', backref='timetable_entries')
    time_slot = db.relationship('TimeSlot', backref='timetable_entries')
    teacher = db.relationship('User', backref='teaching_schedule')
    student_group = db.relationship('StudentGroup', backref='timetables')
    
    # Constraints - Multi-group timetable with global resource constraints
    __table_args__ = (
        # Group-specific: No double-booking within the same group
        db.UniqueConstraint('student_group_id', 'classroom_id', 'time_slot_id', 'academic_year_id', 'session_id', 
                           name='unique_group_classroom_time'),
        db.UniqueConstraint('student_group_id', 'teacher_id', 'time_slot_id', 'academic_year_id', 'session_id', 
                           name='unique_group_teacher_time'),
        # Global: No classroom conflicts across groups
        db.UniqueConstraint('classroom_id', 'time_slot_id', 'academic_year_id', 'session_id', 
                           name='unique_global_classroom_time'),
        # Global: No teacher conflicts across groups
        db.UniqueConstraint('teacher_id', 'time_slot_id', 'academic_year_id', 'session_id', 
                           name='unique_global_teacher_time'),
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
    """Attendance model for tracking student attendance"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_session.id'), nullable=False)
    class_instance_id = db.Column(db.Integer, db.ForeignKey('class_instance.id'), nullable=True)
    status = db.Column(db.String(20), default='present')  # present, absent, late
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # faculty who marked
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_used = db.Column(db.String(255))  # QR code hash used for attendance
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    course = db.relationship('Course', backref='attendance_records')
    time_slot = db.relationship('TimeSlot', backref='attendance_records')
    faculty = db.relationship('User', foreign_keys=[marked_by], backref='marked_attendance')
    timetable = db.relationship('Timetable', backref='attendance_records')
    class_instance = db.relationship('ClassInstance')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'date', 'time_slot_id', 'academic_year_id', 'session_id', name='unique_attendance'),
    )
    
    def __repr__(self):
        return f'<Attendance {self.student.name} - {self.course.name} - {self.date}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # attendance, timetable, general
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QRCode(db.Model):
    """QR Code model for student attendance"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    qr_code_hash = db.Column(db.String(255), unique=True, nullable=False)
    qr_code_image = db.Column(db.Text)  # Base64 encoded image
    is_active = db.Column(db.Boolean, default=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='qr_codes')
    
    def __repr__(self):
        return f'<QRCode {self.user.name} - {self.qr_code_hash[:10]}...>'

class AcademicYear(db.Model):
    """Academic Year model for managing academic sessions"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "2024-2025"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('AcademicSession', backref='academic_year', cascade='all, delete-orphan')
    holidays = db.relationship('Holiday', backref='academic_year', cascade='all, delete-orphan')
    timetables = db.relationship('Timetable', backref='academic_year_rel', cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='academic_year_rel', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AcademicYear {self.name}>'

class AcademicSession(db.Model):
    """Academic Session model for semesters/trimesters"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Fall Semester", "Spring Semester"
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    session_type = db.Column(db.String(50), nullable=False)  # semester, trimester, quarter
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    timetables = db.relationship('Timetable', backref='session_rel', cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='session_rel', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AcademicSession {self.name} - {self.academic_year.name}>'

class Holiday(db.Model):
    """Holiday model for managing academic holidays"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Christmas Break", "Easter"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)  # For annual holidays
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Holiday {self.name} - {self.start_date} to {self.end_date}>'

class ClassInstance(db.Model):
    """Class Instance model for specific date-based classes"""
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    class_date = db.Column(db.Date, nullable=False)  # Specific date for this class
    is_cancelled = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    timetable = db.relationship('Timetable', backref='class_instances')
    attendance_records = db.relationship('Attendance', foreign_keys='Attendance.class_instance_id', cascade='all, delete-orphan', overlaps="class_instance")
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('timetable_id', 'class_date', name='unique_class_instance'),
    )
    
    def __repr__(self):
        return f'<ClassInstance {self.timetable.course.name} - {self.class_date}>'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        # Try to reconnect and retry once
        try:
            db.engine.dispose()
            time.sleep(1)
            return User.query.get(int(user_id))
        except Exception as retry_error:
            print(f"Retry failed for user {user_id}: {retry_error}")
            return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')
    except Exception as e:
        flash(f'An error occurred during login: {str(e)}', 'error')
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
        # Get statistics with optimized queries
        total_students = User.query.filter_by(role='student').count()
        total_faculty = User.query.filter_by(role='faculty').count()
        total_courses = Course.query.count()
        total_classrooms = Classroom.query.count()
        total_time_slots = TimeSlot.query.count()
        total_timetables = Timetable.query.count()
        total_attendance = Attendance.query.count()
        total_student_groups = StudentGroup.query.count()
        
        # Get recent attendance data with proper joins
        recent_attendance = db.session.query(Attendance).options(
            db.joinedload(Attendance.student),
            db.joinedload(Attendance.faculty),
            db.joinedload(Attendance.course),
            db.joinedload(Attendance.time_slot)
        ).order_by(Attendance.marked_at.desc()).limit(10).all()
        
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
    
    # Get instructions from session for display
    export_instructions = session.pop('export_instructions', None)
    import_instructions = session.pop('import_instructions', None)
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         total_faculty=total_faculty,
                         total_courses=total_courses,
                         total_classrooms=total_classrooms,
                         total_time_slots=total_time_slots,
                         total_timetables=total_timetables,
                         total_attendance=total_attendance,
                         total_student_groups=total_student_groups,
                         recent_attendance=recent_attendance,
                         export_instructions=export_instructions,
                         import_instructions=import_instructions)

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get faculty's courses and timetables with optimized queries
        course_assignments = CourseTeacher.query.filter_by(teacher_id=current_user.id).all()
        course_ids = [assignment.course_id for assignment in course_assignments]
        courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
        
        # Get timetables with proper joins
        timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.time_slot)
        ).filter_by(teacher_id=current_user.id).all()
        
        # Get today's classes using direct database queries
        from datetime import datetime, timedelta
        today = datetime.now().date()
        today_weekday = today.strftime('%A')  # Monday, Tuesday, etc.
        
        # Get today's classes based on time slots
        today_classes = []
        for timetable in timetables:
            if timetable.time_slot and timetable.time_slot.day == today_weekday:
                today_classes.append({
                    'id': timetable.id,
                    'course_name': timetable.course.name if timetable.course else 'Unknown Course',
                    'course_code': timetable.course.code if timetable.course else 'N/A',
                    'start_time': timetable.time_slot.start_time if timetable.time_slot else 'N/A',
                    'end_time': timetable.time_slot.end_time if timetable.time_slot else 'N/A',
                    'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                    'time_slot_id': timetable.time_slot_id,
                    'course_id': timetable.course_id
                })
        
        # Get upcoming classes for the next 7 days
        upcoming_classes = []
        for i in range(7):
            future_date = today + timedelta(days=i)
            future_weekday = future_date.strftime('%A')
            
            for timetable in timetables:
                if timetable.time_slot and timetable.time_slot.day == future_weekday:
                    upcoming_classes.append({
                        'date': future_date,
                        'day_name': future_weekday,
                        'course_name': timetable.course.name if timetable.course else 'Unknown Course',
                        'course_code': timetable.course.code if timetable.course else 'N/A',
                        'start_time': timetable.time_slot.start_time if timetable.time_slot else 'N/A',
                        'end_time': timetable.time_slot.end_time if timetable.time_slot else 'N/A',
                        'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                        'time_slot_id': timetable.time_slot_id,
                        'course_id': timetable.course_id
                    })
        
        # Sort today's classes by start time
        today_classes.sort(key=lambda x: x['start_time'] if x['start_time'] != 'N/A' else '23:59')
        
        # Sort upcoming classes by date and time
        upcoming_classes.sort(key=lambda x: (x['date'], x['start_time'] if x['start_time'] != 'N/A' else '23:59'))
        
        # Remove duplicates from upcoming classes (same course on same day)
        seen = set()
        unique_upcoming = []
        for cls in upcoming_classes:
            key = (cls['date'], cls['course_id'])
            if key not in seen:
                seen.add(key)
                unique_upcoming.append(cls)
        upcoming_classes = unique_upcoming
        
        active_year = None
                
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        courses = []
        timetables = []
        today_classes = []
        upcoming_classes = []
        active_year = None
    
    return render_template('faculty/dashboard.html', 
                         courses=courses,
                         timetables=timetables,
                         today_classes=today_classes,
                         upcoming_classes=upcoming_classes,
                         active_year=active_year,
                         date=date)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get student's attendance records with proper joins
        attendance_records = db.session.query(Attendance).options(
            db.joinedload(Attendance.course),
            db.joinedload(Attendance.faculty),
            db.joinedload(Attendance.time_slot)
        ).filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).limit(10).all()
        
        # Get attendance statistics
        total_classes = Attendance.query.filter_by(student_id=current_user.id).count()
        present_classes = Attendance.query.filter_by(student_id=current_user.id, status='present').count()
        late_classes = Attendance.query.filter_by(student_id=current_user.id, status='late').count()
        attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
        
        # Get today's classes using direct database queries
        from datetime import datetime, timedelta
        today = datetime.now().date()
        today_weekday = today.strftime('%A')  # Monday, Tuesday, etc.
        
        # Get student's group
        student_group_id = current_user.group_id
        
        # Get today's classes based on student's group and time slots
        today_classes = []
        if student_group_id:
            student_timetables = db.session.query(Timetable).options(
                db.joinedload(Timetable.course),
                db.joinedload(Timetable.classroom),
                db.joinedload(Timetable.time_slot)
            ).filter_by(student_group_id=student_group_id).all()
            
            for timetable in student_timetables:
                if timetable.time_slot and timetable.time_slot.day == today_weekday:
                    today_classes.append({
                        'id': timetable.id,
                        'course_name': timetable.course.name if timetable.course else 'Unknown Course',
                        'course_code': timetable.course.code if timetable.course else 'N/A',
                        'start_time': timetable.time_slot.start_time if timetable.time_slot else 'N/A',
                        'end_time': timetable.time_slot.end_time if timetable.time_slot else 'N/A',
                        'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                        'time_slot_id': timetable.time_slot_id,
                        'course_id': timetable.course_id
                    })
        
        # Get upcoming classes for the next 7 days
        upcoming_classes = []
        if student_group_id:
            for i in range(7):
                future_date = today + timedelta(days=i)
                future_weekday = future_date.strftime('%A')
                
                for timetable in student_timetables:
                    if timetable.time_slot and timetable.time_slot.day == future_weekday:
                        upcoming_classes.append({
                            'date': future_date,
                            'day_name': future_weekday,
                            'course_name': timetable.course.name if timetable.course else 'Unknown Course',
                            'course_code': timetable.course.code if timetable.course else 'N/A',
                            'start_time': timetable.time_slot.start_time if timetable.time_slot else 'N/A',
                            'end_time': timetable.time_slot.end_time if timetable.time_slot else 'N/A',
                            'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                            'time_slot_id': timetable.time_slot_id,
                            'course_id': timetable.course_id
                        })
        
        # Sort today's classes by start time
        today_classes.sort(key=lambda x: x['start_time'] if x['start_time'] != 'N/A' else '23:59')
        
        # Sort upcoming classes by date and time
        upcoming_classes.sort(key=lambda x: (x['date'], x['start_time'] if x['start_time'] != 'N/A' else '23:59'))
        
        # Remove duplicates from upcoming classes (same course on same day)
        seen = set()
        unique_upcoming = []
        for cls in upcoming_classes:
            key = (cls['date'], cls['course_id'])
            if key not in seen:
                seen.add(key)
                unique_upcoming.append(cls)
        upcoming_classes = unique_upcoming
        
        active_year = None
                
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'error')
        attendance_records = []
        total_classes = 0
        present_classes = 0
        late_classes = 0
        attendance_percentage = 0
        today_classes = []
        upcoming_classes = []
        active_year = None
    
    return render_template('student/dashboard.html',
                         attendance_records=attendance_records,
                         total_classes=total_classes,
                         present_classes=present_classes,
                         late_classes=late_classes,
                         attendance_percentage=attendance_percentage,
                         today_classes=today_classes,
                         upcoming_classes=upcoming_classes,
                         active_year=active_year,
                         date=date)

# API Routes for AJAX calls
@app.route('/api/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        student_id = data.get('student_id')
        timetable_id = data.get('timetable_id')
        status = data.get('status')
        date_str = data.get('date')
        
        # Validate required fields
        if not all([student_id, timetable_id, status, date_str]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Validate status
        if status not in ['present', 'absent', 'late']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format'}), 400
        
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
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-timetable')
@login_required
def get_timetable():
    try:
        if current_user.role == 'student':
            # Get student's timetable through their group with proper joins
            timetables = db.session.query(Timetable).join(
                StudentGroupCourse, Timetable.course_id == StudentGroupCourse.course_id
            ).join(
                StudentGroup, StudentGroupCourse.student_group_id == StudentGroup.id
            ).options(
                db.joinedload(Timetable.time_slot),
                db.joinedload(Timetable.course),
                db.joinedload(Timetable.classroom)
            ).filter(
                StudentGroup.name == current_user.department
            ).all()
        else:
            timetables = db.session.query(Timetable).options(
                db.joinedload(Timetable.time_slot),
                db.joinedload(Timetable.course),
                db.joinedload(Timetable.classroom)
            ).filter_by(teacher_id=current_user.id).all()
        
        timetable_data = []
        for tt in timetables:
            if all([tt.time_slot, tt.course, tt.classroom]):
                timetable_data.append({
                    'id': tt.id,
                    'course': tt.course.name,
                    'classroom': tt.classroom.room_number,
                    'day': tt.time_slot.day,
                    'start_time': tt.time_slot.start_time,
                    'end_time': tt.time_slot.end_time
                })
        
        return jsonify(timetable_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Management Routes
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
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
        
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get filter parameters
        department_filter = request.args.get('department', '')
        credits_filter = request.args.get('credits', '')
        
        # Build query with filters
        query = Course.query
        
        if department_filter:
            query = query.filter(Course.department == department_filter)
        
        if credits_filter:
            try:
                credits_value = int(credits_filter)
                query = query.filter(Course.credits == credits_value)
            except ValueError:
                flash('Invalid credits filter value', 'error')
        
        courses = query.all()
        teachers = User.query.filter_by(role='faculty').all()
        return render_template('admin/courses.html', courses=courses, teachers=teachers)
        
    except Exception as e:
        flash(f'Error loading courses: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/classrooms')
@login_required
def admin_classrooms():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
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
        
    except Exception as e:
        flash(f'Error loading classrooms: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/timetable')
@login_required
def admin_timetable():
    """Admin timetable management page"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    

    
    # Get all timetables with proper joins and sort by time
    timetables = db.session.query(Timetable).options(
        db.joinedload(Timetable.time_slot),
        db.joinedload(Timetable.course),
        db.joinedload(Timetable.classroom),
        db.joinedload(Timetable.teacher),
        db.joinedload(Timetable.student_group)
    ).all()
    
    # Sort timetables by day and time
    timetables = sort_timetables_by_time(timetables)
    
    # Get generation results from session if available
    generation_results = session.get('timetable_generation_results')
    
    return render_template('admin/timetable.html',
                         timetables=timetables,
                         generation_results=generation_results,
                         student_groups=StudentGroup.query.all(),
                         courses=Course.query.all(),
                         teachers=User.query.filter_by(role='faculty').all(),
                         classrooms=Classroom.query.all(),
                         time_slots=TimeSlot.query.all())

@app.route('/admin/edit_timetable/<int:timetable_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_timetable(timetable_id):
    """Edit a specific timetable entry"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            course_id = request.form.get('course_id', type=int)
            teacher_id = request.form.get('teacher_id', type=int)
            classroom_id = request.form.get('classroom_id', type=int)
            time_slot_id = request.form.get('time_slot_id', type=int)
            student_group_id = request.form.get('student_group_id', type=int)
            
            # Create temporary entry for conflict checking
            temp_entry = Timetable(
                course_id=course_id,
                teacher_id=teacher_id,
                classroom_id=classroom_id,
                time_slot_id=time_slot_id,
                student_group_id=student_group_id,
                semester=timetable.semester,
                academic_year=timetable.academic_year
            )
            
            # Check for conflicts
            conflicts = get_timetable_conflicts(temp_entry, exclude_id=timetable_id)
            
            if conflicts:
                conflict_message = "Cannot update timetable due to conflicts:\n" + "\n".join(conflicts)
                flash(conflict_message, 'error')
                return render_template('admin/edit_timetable.html',
                                     timetable=timetable,
                                     courses=Course.query.all(),
                                     teachers=User.query.filter_by(role='faculty').all(),
                                     classrooms=Classroom.query.all(),
                                     time_slots=TimeSlot.query.all(),
                                     student_groups=StudentGroup.query.all())
            
            # Update timetable
            timetable.course_id = course_id
            timetable.teacher_id = teacher_id
            timetable.classroom_id = classroom_id
            timetable.time_slot_id = time_slot_id
            timetable.student_group_id = student_group_id
            
            db.session.commit()
            flash('Timetable updated successfully!', 'success')
            return redirect(url_for('admin_timetable'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating timetable: {str(e)}', 'error')
    
    return render_template('admin/edit_timetable.html',
                         timetable=timetable,
                         courses=Course.query.all(),
                         teachers=User.query.filter_by(role='faculty').all(),
                         classrooms=Classroom.query.all(),
                         time_slots=TimeSlot.query.all(),
                         student_groups=StudentGroup.query.all())

@app.route('/admin/delete_timetable/<int:timetable_id>', methods=['POST'])
@login_required
def admin_delete_timetable(timetable_id):
    """Delete a timetable entry"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_timetable'))
    
    try:
        timetable = Timetable.query.get_or_404(timetable_id)
        
        # Check for related ClassInstance records
        class_instances = ClassInstance.query.filter_by(timetable_id=timetable_id).all()
        if class_instances:
            # Delete related ClassInstance records first
            for class_instance in class_instances:
                db.session.delete(class_instance)
            print(f"Deleted {len(class_instances)} related class instances")
        
        # Check for related Attendance records
        attendance_records = Attendance.query.filter_by(timetable_id=timetable_id).all()
        if attendance_records:
            # Delete related Attendance records first
            for attendance in attendance_records:
                db.session.delete(attendance)
            print(f"Deleted {len(attendance_records)} related attendance records")
        
        # Now delete the timetable
        db.session.delete(timetable)
        db.session.commit()
        flash('Timetable entry and all related records deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timetable: {str(e)}', 'error')
        print(f"Timetable deletion error: {e}")
    
    return redirect(url_for('admin_timetable'))

@app.route('/admin/add_timetable', methods=['GET', 'POST'])
@login_required
def admin_add_timetable():
    """Add a new timetable entry manually"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_timetable'))
    
    if request.method == 'POST':
        try:
            # Get form data
            course_id = request.form.get('course_id', type=int)
            teacher_id = request.form.get('teacher_id', type=int)
            classroom_id = request.form.get('classroom_id', type=int)
            time_slot_id = request.form.get('time_slot_id', type=int)
            student_group_id = request.form.get('student_group_id', type=int)
            semester = request.form.get('semester', 'Fall 2024')
            academic_year = request.form.get('academic_year', '2024-25')
            
            # Create new entry
            new_timetable = Timetable(
                course_id=course_id,
                teacher_id=teacher_id,
                classroom_id=classroom_id,
                time_slot_id=time_slot_id,
                student_group_id=student_group_id,
                semester=semester,
                academic_year=academic_year
            )
            
            # Check for conflicts
            conflicts = get_timetable_conflicts(new_timetable)
            
            if conflicts:
                conflict_message = "Cannot add timetable due to conflicts:\n" + "\n".join(conflicts)
                flash(conflict_message, 'error')
                return render_template('admin/add_timetable.html',
                                     courses=Course.query.all(),
                                     teachers=User.query.filter_by(role='faculty').all(),
                                     classrooms=Classroom.query.all(),
                                     time_slots=TimeSlot.query.all(),
                                     student_groups=StudentGroup.query.all())
            
            db.session.add(new_timetable)
            db.session.commit()
            flash('Timetable entry added successfully!', 'success')
            return redirect(url_for('admin_timetable'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding timetable: {str(e)}', 'error')
    
    return render_template('admin/add_timetable.html',
                         courses=Course.query.all(),
                         teachers=User.query.filter_by(role='faculty').all(),
                         classrooms=Classroom.query.all(),
                         time_slots=TimeSlot.query.all(),
                         student_groups=StudentGroup.query.all())

@app.route('/admin/manage_breaks', methods=['GET', 'POST'])
@login_required
def admin_manage_breaks():
    """Manage break times in time slots"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_timetable'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            if action == 'add_break':
                day = request.form.get('day')
                start_time = request.form.get('start_time')
                end_time = request.form.get('end_time')
                break_type = request.form.get('break_type', 'Break')
                
                # Check for conflicts before adding the break
                conflicts = check_break_conflicts(day, start_time, end_time)
                if conflicts:
                    conflict_message = "Cannot add break due to conflicts:\n" + "\n".join(conflicts)
                    flash(conflict_message, 'error')
                    return redirect(url_for('admin_manage_breaks'))
                
                # Check if there's already a time slot at this time
                existing_slot = TimeSlot.query.filter_by(
                    day=day, 
                    start_time=start_time, 
                    end_time=end_time
                ).first()
                
                if existing_slot:
                    # If it's already a break, just update the type
                    if existing_slot.break_type == 'Break':
                        flash('Time slot is already a break', 'info')
                    else:
                        # Convert existing regular slot to break
                        existing_slot.break_type = 'Break'
                        flash('Converted existing time slot to break', 'info')
                else:
                    # Create new break time slot
                    break_slot = TimeSlot(
                        day=day,
                        start_time=start_time,
                        end_time=end_time,
                        break_type='Break'
                    )
                    db.session.add(break_slot)
                    flash('Added new break time slot', 'success')
                
                # Remove any existing timetable entries that conflict with this break
                conflicting_timetables = Timetable.query.join(TimeSlot).filter(
                    TimeSlot.day == day,
                    TimeSlot.start_time == start_time,
                    TimeSlot.end_time == end_time
                ).all()
                
                if conflicting_timetables:
                    for tt in conflicting_timetables:
                        db.session.delete(tt)
                    flash(f'Removed {len(conflicting_timetables)} conflicting class(es) from this time slot', 'warning')
                
            elif action == 'update_break':
                slot_id = request.form.get('slot_id', type=int)
                slot = TimeSlot.query.get_or_404(slot_id)
                old_break_type = slot.break_type
                new_break_type = request.form.get('break_type', 'Break')
                
                # If converting from regular slot to break, check for conflicts
                if old_break_type == 'none' and new_break_type == 'Break':
                    conflicts = check_break_conflicts(slot.day, slot.start_time, slot.end_time, exclude_slot_id=slot_id)
                    if conflicts:
                        conflict_message = "Cannot convert to break due to conflicts:\n" + "\n".join(conflicts)
                        flash(conflict_message, 'error')
                        return redirect(url_for('admin_manage_breaks'))
                    
                    # Remove conflicting classes
                    conflicting_timetables = Timetable.query.filter_by(time_slot_id=slot_id).all()
                    if conflicting_timetables:
                        for tt in conflicting_timetables:
                            db.session.delete(tt)
                        flash(f'Removed {len(conflicting_timetables)} conflicting class(es) when converting to break', 'warning')
                
                slot.break_type = new_break_type
                if old_break_type == 'none':
                    flash('Time slot converted to break successfully', 'success')
                else:
                    flash('Break type updated successfully', 'success')
                
            elif action == 'delete_break':
                slot_id = request.form.get('slot_id', type=int)
                slot = TimeSlot.query.get_or_404(slot_id)
                
                # Only allow deletion of break slots
                if slot.break_type == 'Break':
                    db.session.delete(slot)
                    flash('Deleted break time slot', 'success')
                else:
                    flash('Cannot delete regular time slots', 'error')
                    return redirect(url_for('admin_manage_breaks'))
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error managing breaks: {str(e)}', 'error')
    
    # Get all time slots sorted by day and time with timetable counts
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.start_time).all()
    
    # Add timetable count information for each time slot
    for slot in time_slots:
        slot.timetable_count = Timetable.query.filter_by(time_slot_id=slot.id).count()
    
    return render_template('admin/manage_breaks.html', time_slots=time_slots)

@app.route('/admin/group_timetable/<int:group_id>')
@login_required
def admin_group_timetable(group_id):
    """Show individual timetable for a specific student group"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get the specific student group
        student_group = StudentGroup.query.get_or_404(group_id)
        
        # Get all timetables for this group with proper joins
        timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.teacher),
            db.joinedload(Timetable.student_group)
        ).filter(
            Timetable.student_group_id == group_id
        ).order_by(
            Timetable.time_slot_id
        ).all()
        
        # Create a unique timetable map to prevent duplicates in the grid
        # Key: (day, start_time), Value: first timetable entry for that slot
        unique_timetables = {}
        for tt in timetables:
            if tt.time_slot and tt.course and tt.classroom and tt.teacher:
                key = (tt.time_slot.day, tt.time_slot.start_time)
                if key not in unique_timetables:
                    unique_timetables[key] = tt
        
        # Convert back to list for template rendering
        unique_timetables_list = list(unique_timetables.values())
        
        # Get unique time ranges for the grid rows
        unique_time_ranges = db.session.query(
            TimeSlot.start_time,
            TimeSlot.end_time
        ).distinct().order_by(TimeSlot.start_time).all()
        
        # Convert to a list of time range strings for the template
        time_slots = [f"{start} - {end}" for start, end in unique_time_ranges]
        
        # Get all days
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        return render_template('admin/group_timetable.html',
                             timetables=unique_timetables_list,
                             student_group=student_group,
                             time_slots=time_slots,
                             days=days)
                             
    except Exception as e:
        flash(f'Error loading group timetable: {str(e)}', 'error')
        return redirect(url_for('admin_timetable'))

@app.route('/admin/teacher_timetable/<int:teacher_id>')
@login_required
def admin_teacher_timetable(teacher_id):
    """Show individual timetable for a specific teacher"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get the specific teacher
        teacher = User.query.filter_by(id=teacher_id, role='faculty').first_or_404()
        
        # Get all timetables for this teacher with proper joins
        timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.student_group)
        ).filter(
            Timetable.teacher_id == teacher_id
        ).order_by(
            Timetable.time_slot_id
        ).all()
        
        # Create a unique timetable map to prevent duplicates in the grid
        # Key: (day, start_time), Value: first timetable entry for that slot
        unique_timetables = {}
        for tt in timetables:
            if tt.time_slot and tt.course and tt.classroom and tt.student_group:
                key = (tt.time_slot.day, tt.time_slot.start_time)
                if key not in unique_timetables:
                    unique_timetables[key] = tt
        
        # Convert back to list for template rendering
        unique_timetables_list = list(unique_timetables.values())
        
        # Get unique time ranges for the grid rows
        unique_time_ranges = db.session.query(
            TimeSlot.start_time,
            TimeSlot.end_time
        ).distinct().order_by(TimeSlot.start_time).all()
        
        # Convert to a list of time range strings for the template
        time_slots = [f"{start} - {end}" for start, end in unique_time_ranges]
        
        # Get all days
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        return render_template('admin/teacher_timetable.html',
                             timetables=unique_timetables_list,
                             teacher=teacher,
                             time_slots=time_slots,
                             days=days)
                             
    except Exception as e:
        flash(f'Error loading teacher timetable: {str(e)}', 'error')
        return redirect(url_for('admin_timetable'))

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
            try:
                start_time, end_time = time_slot_filter.split('-')
                query = query.join(TimeSlot).filter(
                    TimeSlot.start_time == start_time,
                    TimeSlot.end_time == end_time
                )
            except ValueError:
                flash('Invalid time slot format', 'error')
                return redirect(url_for('admin_timetable'))
        
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
        
        return render_template('admin/time_slots.html', time_slots=time_slots)
        
    except Exception as e:
        flash(f'Error loading time slots: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            name = request.form.get('name', '').strip()
            role = request.form.get('role', '').strip()
            department = request.form.get('department', '').strip()
            
            # Validate required fields
            if not all([username, email, password, name, role]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('admin_add_user'))
            
            # Check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return redirect(url_for('admin_add_user'))
            
            # Check if email already exists
            if User.query.filter_by(email=email).first():
                flash('Email already exists', 'error')
                return redirect(url_for('admin_add_user'))
            
            # Validate role
            if role not in ['admin', 'faculty', 'student']:
                flash('Invalid role selected', 'error')
                return redirect(url_for('admin_add_user'))
            
            # Create user
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
                try:
                    group_id = int(request.form['group_id'])
                    if StudentGroup.query.get(group_id):
                        user.group_id = group_id
                    else:
                        flash('Invalid student group selected', 'warning')
                except (ValueError, TypeError):
                    flash('Invalid student group ID', 'warning')
            
            db.session.add(user)
            db.session.commit()
            flash('User added successfully', 'success')
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding user: {e}")
            flash(f'Error adding user: {str(e)}', 'error')
            return redirect(url_for('admin_add_user'))
    
    # Get student groups for the form
    try:
        student_groups = StudentGroup.query.all()
    except Exception as e:
        print(f"Error loading student groups: {e}")
        student_groups = []
        flash('Error loading student groups', 'warning')
    
    return render_template('admin/add_user.html', student_groups=student_groups)

@app.route('/admin/add_course', methods=['GET', 'POST'])
@login_required
def admin_add_course():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            code = request.form.get('code', '').strip()
            name = request.form.get('name', '').strip()
            credits_str = request.form.get('credits', '3')
            department = request.form.get('department', '').strip()
            teacher_id_str = request.form.get('teacher_id', '')
            max_students_str = request.form.get('max_students', '50')
            semester = request.form.get('semester', '1').strip()
            description = request.form.get('description', '').strip()
            subject_area = request.form.get('subject_area', '').strip()
            required_equipment = request.form.get('required_equipment', '').strip()
            min_capacity_str = request.form.get('min_capacity', '1')
            periods_per_week_str = request.form.get('periods_per_week', '3')
            
            # Validate required fields
            if not all([code, name, department, subject_area]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('admin_add_course'))
            
            # Validate and convert numeric fields
            try:
                credits = int(credits_str)
                max_students = int(max_students_str)
                min_capacity = int(min_capacity_str)
                periods_per_week = int(periods_per_week_str)
                teacher_id = int(teacher_id_str) if teacher_id_str else None
            except ValueError:
                flash('Invalid numeric values provided', 'error')
                return redirect(url_for('admin_add_course'))
            
            # Validate ranges
            if credits < 1 or credits > 6:
                flash('Credits must be between 1 and 6', 'error')
                return redirect(url_for('admin_add_course'))
            
            if min_capacity < 1:
                flash('Minimum capacity must be at least 1', 'error')
                return redirect(url_for('admin_add_course'))
            
            if periods_per_week < 1 or periods_per_week > 10:
                flash('Periods per week must be between 1 and 10', 'error')
                return redirect(url_for('admin_add_course'))
            
            if max_students < 1:
                flash('Maximum students must be at least 1', 'error')
                return redirect(url_for('admin_add_course'))
            
            # Check if course code already exists
            if Course.query.filter_by(code=code).first():
                flash('Course code already exists', 'error')
                return redirect(url_for('admin_add_course'))
            
            # Validate teacher if specified
            if teacher_id:
                teacher = User.query.filter_by(id=teacher_id, role='faculty').first()
                if not teacher:
                    flash('Invalid teacher selected', 'error')
                    return redirect(url_for('admin_add_course'))
            
            # Create course
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
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding course: {str(e)}', 'error')
            print(f"Course addition error: {e}")
            return redirect(url_for('admin_add_course'))
    
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/add_course.html', teachers=teachers)

@app.route('/admin/add_classroom', methods=['GET', 'POST'])
@login_required
def admin_add_classroom():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            room_number = request.form.get('room_number', '').strip()
            capacity_str = request.form.get('capacity', '30')
            building = request.form.get('building', '').strip()
            room_type = request.form.get('room_type', 'lecture')
            floor_str = request.form.get('floor', '1')
            status = request.form.get('status', 'active')
            equipment = request.form.get('equipment', '').strip()
            facilities = request.form.get('facilities', '').strip()
            
            # Validate required fields
            if not all([room_number, building]):
                flash('Room number and building are required', 'error')
                return redirect(url_for('admin_add_classroom'))
            
            # Validate and convert numeric fields
            try:
                capacity = int(capacity_str)
                floor = int(floor_str)
            except ValueError:
                flash('Invalid numeric values provided', 'error')
                return redirect(url_for('admin_add_classroom'))
            
            # Validate ranges
            if capacity < 1 or capacity > 500:
                flash('Capacity must be between 1 and 500', 'error')
                return redirect(url_for('admin_add_classroom'))
            
            if floor < 0 or floor > 20:
                flash('Floor must be between 0 and 20', 'error')
                return redirect(url_for('admin_add_classroom'))
            
            # Check if room number already exists
            if Classroom.query.filter_by(room_number=room_number).first():
                flash('Room number already exists', 'error')
                return redirect(url_for('admin_add_classroom'))
            
            # Create classroom
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
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding classroom: {str(e)}', 'error')
            print(f"Classroom addition error: {e}")
            return redirect(url_for('admin_add_classroom'))
    
    return render_template('admin/add_classroom.html')

# Edit and Delete Routes for Admin
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        user = User.query.get_or_404(user_id)
        
        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip()
                role = request.form.get('role', '').strip()
                department = request.form.get('department', '').strip()
                phone = request.form.get('phone', '').strip()
                address = request.form.get('address', '').strip()
                
                # Validate required fields
                if not all([name, username, email, role]):
                    flash('All required fields must be filled', 'error')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                # Check if username already exists (excluding current user)
                existing_user = User.query.filter_by(username=username).first()
                if existing_user and existing_user.id != user.id:
                    flash('Username already exists', 'error')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                # Check if email already exists (excluding current user)
                existing_user = User.query.filter_by(email=email).first()
                if existing_user and existing_user.id != user.id:
                    flash('Email already exists', 'error')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                # Validate role
                if role not in ['admin', 'faculty', 'student']:
                    flash('Invalid role selected', 'error')
                    return redirect(url_for('admin_edit_user', user_id=user_id))
                
                # Update user fields
                user.name = name
                user.username = username
                user.email = email
                user.role = role
                user.department = department
                user.phone = phone
                user.address = address
                
                # Handle group assignment for students
                if user.role == 'student' and request.form.get('group_id'):
                    try:
                        group_id = int(request.form['group_id'])
                        if StudentGroup.query.get(group_id):
                            user.group_id = group_id
                        else:
                            flash('Invalid student group selected', 'warning')
                            user.group_id = None
                    except (ValueError, TypeError):
                        flash('Invalid student group ID', 'warning')
                        user.group_id = None
                elif user.role != 'student':
                    user.group_id = None
                
                # Only update password if provided
                if request.form.get('password'):
                    password = request.form.get('password', '').strip()
                    if password:
                        user.password_hash = generate_password_hash(password)
                
                db.session.commit()
                flash('User updated successfully', 'success')
                return redirect(url_for('admin_users'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating user: {e}")
                flash(f'Error updating user: {str(e)}', 'error')
                return redirect(url_for('admin_edit_user', user_id=user_id))
        
        # Get student groups for the form
        try:
            student_groups = StudentGroup.query.all()
        except Exception as e:
            print(f"Error loading student groups: {e}")
            student_groups = []
            flash('Error loading student groups', 'warning')
        
        return render_template('admin/edit_user.html', user=user, student_groups=student_groups)
        
    except Exception as e:
        print(f"Error in admin_edit_user: {e}")
        flash(f'Error loading user: {str(e)}', 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting the current user
        if user.id == current_user.id:
            flash('You cannot delete your own account', 'error')
            return redirect(url_for('admin_users'))
        
        # Check what records will be affected
        related_records = []
        
        # Check attendance records
        attendance_count = Attendance.query.filter_by(student_id=user.id).count()
        if attendance_count > 0:
            related_records.append(f"{attendance_count} attendance record(s)")
        
        # Check if user is marked by in attendance records
        marked_by_count = Attendance.query.filter_by(marked_by=user.id).count()
        if marked_by_count > 0:
            related_records.append(f"{marked_by_count} attendance marking record(s)")
        
        # Check QR codes
        qr_count = QRCode.query.filter_by(user_id=user.id).count()
        if qr_count > 0:
            related_records.append(f"{qr_count} QR code(s)")
        
        # Check course teacher assignments
        teacher_count = CourseTeacher.query.filter_by(teacher_id=user.id).count()
        if teacher_count > 0:
            related_records.append(f"{teacher_count} course teaching assignment(s)")
        
        # Check timetables
        timetable_count = Timetable.query.filter_by(teacher_id=user.id).count()
        if timetable_count > 0:
            related_records.append(f"{timetable_count} timetable entry(ies)")
        
        # If there are related records, handle them properly
        if related_records:
            print(f"Deleting user {user.id} with related records: {related_records}")
            
            # Handle attendance records where user is the student
            if attendance_count > 0:
                print(f"Removing {attendance_count} attendance records for user {user.id}")
                Attendance.query.filter_by(student_id=user.id).delete()
            
            # Handle attendance records where user is the faculty who marked attendance
            if marked_by_count > 0:
                print(f"Updating {marked_by_count} attendance records marked by user {user.id}")
                # Find another faculty user to reassign these records
                other_faculty = User.query.filter(
                    User.role == 'faculty',
                    User.id != user.id
                ).first()
                
                if other_faculty:
                    Attendance.query.filter_by(marked_by=user.id).update({
                        'marked_by': other_faculty.id
                    })
                    print(f"Reassigned attendance records to faculty {other_faculty.id}")
                else:
                    # If no other faculty, delete these records
                    Attendance.query.filter_by(marked_by=user.id).delete()
                    print("No other faculty found, deleted attendance records")
            
            # Handle QR codes
            if qr_count > 0:
                print(f"Removing {qr_count} QR codes for user {user.id}")
                QRCode.query.filter_by(user_id=user.id).delete()
            
            # Handle course teacher assignments
            if teacher_count > 0:
                print(f"Removing {teacher_count} course teaching assignments for user {user.id}")
                CourseTeacher.query.filter_by(teacher_id=user.id).delete()
            
            # Handle timetables
            if timetable_count > 0:
                print(f"Removing {timetable_count} timetable entries for user {user.id}")
                Timetable.query.filter_by(teacher_id=user.id).delete()
        
        # Now delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{user.name}" deleted successfully. Removed {len(related_records)} related record types.', 'success')
        return redirect(url_for('admin_users'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user {user_id}: {e}")
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/preview_user_deletion/<int:user_id>')
@login_required
def admin_preview_user_deletion(user_id):
    """Preview what will be deleted when removing a user"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent previewing deletion of current user
        if user.id == current_user.id:
            flash('You cannot delete your own account', 'error')
            return redirect(url_for('admin_users'))
        
        # Gather information about related records
        deletion_info = {
            'user': user,
            'attendance_records': Attendance.query.filter_by(student_id=user.id).all(),
            'marked_attendance_count': Attendance.query.filter_by(marked_by=user.id).count(),
            'qr_codes': QRCode.query.filter_by(user_id=user.id).all(),
            'course_assignments': CourseTeacher.query.filter_by(teacher_id=user.id).all(),
            'timetable_entries': Timetable.query.filter_by(teacher_id=user.id).all(),
            'total_related_records': 0
        }
        
        # Calculate total related records
        deletion_info['total_related_records'] = (
            len(deletion_info['attendance_records']) +
            deletion_info['marked_attendance_count'] +
            len(deletion_info['qr_codes']) +
            len(deletion_info['course_assignments']) +
            len(deletion_info['timetable_entries'])
        )
        
        return render_template('admin/preview_user_deletion.html', deletion_info=deletion_info)
        
    except Exception as e:
        print(f"Error previewing user deletion {user_id}: {e}")
        flash(f'Error previewing user deletion: {str(e)}', 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            code = request.form.get('code', '').strip()
            name = request.form.get('name', '').strip()
            credits_str = request.form.get('credits', '3')
            department = request.form.get('department', '').strip()
            max_students_str = request.form.get('max_students', '50')
            semester = request.form.get('semester', '1').strip()
            description = request.form.get('description', '').strip()
            subject_area = request.form.get('subject_area', '').strip()
            required_equipment = request.form.get('required_equipment', '').strip()
            min_capacity_str = request.form.get('min_capacity', '1')
            periods_per_week_str = request.form.get('periods_per_week', '3')
            teacher_id_str = request.form.get('teacher_id', '')
            
            # Validate required fields
            if not all([code, name, department, subject_area]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            # Validate and convert numeric fields
            try:
                credits = int(credits_str)
                max_students = int(max_students_str)
                min_capacity = int(min_capacity_str)
                periods_per_week = int(periods_per_week_str)
                teacher_id = int(teacher_id_str) if teacher_id_str else None
            except ValueError:
                flash('Invalid numeric values provided', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            # Validate ranges
            if credits < 1 or credits > 6:
                flash('Credits must be between 1 and 6', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            if min_capacity < 1:
                flash('Minimum capacity must be at least 1', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            if periods_per_week < 1 or periods_per_week > 10:
                flash('Periods per week must be between 1 and 10', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            if max_students < 1:
                flash('Maximum students must be at least 1', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            # Check if course code already exists (excluding current course)
            existing_course = Course.query.filter_by(code=code).first()
            if existing_course and existing_course.id != course.id:
                flash('Course code already exists', 'error')
                return redirect(url_for('admin_edit_course', course_id=course_id))
            
            # Validate teacher if specified
            if teacher_id:
                teacher = User.query.filter_by(id=teacher_id, role='faculty').first()
                if not teacher:
                    flash('Invalid teacher selected', 'error')
                    return redirect(url_for('admin_edit_course', course_id=course_id))
            
            # Update course
            course.code = code
            course.name = name
            course.credits = credits
            course.department = department
            course.max_students = max_students
            course.semester = semester
            course.description = description
            course.subject_area = subject_area
            course.required_equipment = required_equipment
            course.min_capacity = min_capacity
            course.periods_per_week = periods_per_week
            
            # Handle teacher assignment
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
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'error')
            print(f"Course update error: {e}")
            return redirect(url_for('admin_edit_course', course_id=course_id))
    
    teachers = User.query.filter_by(role='faculty').all()
    return render_template('admin/edit_course.html', course=course, teachers=teachers)

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
def admin_delete_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        course = Course.query.get_or_404(course_id)
        
        # Check if course is being used in timetables
        timetable_count = Timetable.query.filter_by(course_id=course_id).count()
        if timetable_count > 0:
            flash(f'Cannot delete course: It is scheduled in {timetable_count} timetable entries. Please remove timetable entries first.', 'error')
            return redirect(url_for('admin_courses'))
        
        # Check if course is assigned to student groups
        group_course_count = StudentGroupCourse.query.filter_by(course_id=course_id).count()
        if group_course_count > 0:
            flash(f'Cannot delete course: It is assigned to {group_course_count} student groups. Please remove group assignments first.', 'error')
            return redirect(url_for('admin_courses'))
        
        # Check if course has attendance records
        attendance_count = Attendance.query.filter_by(course_id=course_id).count()
        if attendance_count > 0:
            flash(f'Cannot delete course: It has {attendance_count} attendance records. Please remove attendance records first.', 'error')
            return redirect(url_for('admin_courses'))
        
        # Check if course has teacher assignments
        teacher_count = CourseTeacher.query.filter_by(course_id=course_id).count()
        if teacher_count > 0:
            flash(f'Cannot delete course: It has {teacher_count} teacher assignments. Please remove teacher assignments first.', 'error')
            return redirect(url_for('admin_courses'))
        
        # If all checks pass, delete the course
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully', 'success')
        
        # Log the deletion for audit purposes
        print(f"Course {course.code} - {course.name} deleted by admin {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'error')
        print(f"Course deletion error: {e}")
    
    return redirect(url_for('admin_courses'))

@app.route('/admin/course_dependencies/<int:course_id>')
@login_required
def admin_course_dependencies(course_id):
    """Get course dependencies for deletion check"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Check all dependencies
        timetable_count = Timetable.query.filter_by(course_id=course_id).count()
        group_count = StudentGroupCourse.query.filter_by(course_id=course_id).count()
        attendance_count = Attendance.query.filter_by(course_id=course_id).count()
        teacher_count = CourseTeacher.query.filter_by(course_id=course_id).count()
        
        return jsonify({
            'timetable_count': timetable_count,
            'group_count': group_count,
            'attendance_count': attendance_count,
            'teacher_count': teacher_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/cascade_delete_course/<int:course_id>', methods=['POST'])
@login_required
def admin_cascade_delete_course(course_id):
    """Force delete course and all related records"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_courses'))
    
    try:
        course = Course.query.get_or_404(course_id)
        
        # Get counts for logging
        timetable_count = Timetable.query.filter_by(course_id=course_id).count()
        group_count = StudentGroupCourse.query.filter_by(course_id=course_id).count()
        attendance_count = Attendance.query.filter_by(course_id=course_id).count()
        teacher_count = CourseTeacher.query.filter_by(course_id=course_id).count()
        
        # Delete all related records first
        if timetable_count > 0:
            Timetable.query.filter_by(course_id=course_id).delete()
            print(f"Deleted {timetable_count} timetable entries for course {course.code}")
        
        if group_count > 0:
            StudentGroupCourse.query.filter_by(course_id=course_id).delete()
            print(f"Deleted {group_count} group course assignments for course {course.code}")
        
        if attendance_count > 0:
            Attendance.query.filter_by(course_id=course_id).delete()
            print(f"Deleted {attendance_count} attendance records for course {course.code}")
        
        if teacher_count > 0:
            CourseTeacher.query.filter_by(course_id=course_id).delete()
            print(f"Deleted {teacher_count} teacher assignments for course {course.code}")
        
        # Now delete the course
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Course "{course.code} - {course.name}" and all related records ({timetable_count + group_count + attendance_count + teacher_count} total) deleted successfully', 'success')
        
        # Log the cascade deletion for audit purposes
        print(f"Course {course.code} - {course.name} cascade deleted by admin {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cascade deleting course: {str(e)}', 'error')
        print(f"Course cascade deletion error: {e}")
    
    return redirect(url_for('admin_courses'))

@app.route('/admin/edit_classroom/<int:classroom_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            room_number = request.form.get('room_number', '').strip()
            capacity_str = request.form.get('capacity', '30')
            building = request.form.get('building', '').strip()
            room_type = request.form.get('room_type', 'lecture')
            floor_str = request.form.get('floor', '1')
            status = request.form.get('status', 'active')
            facilities = request.form.get('facilities', '').strip()
            equipment = request.form.get('equipment', '').strip()
            
            # Validate required fields
            if not all([room_number, building]):
                flash('Room number and building are required', 'error')
                return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
            
            # Validate and convert numeric fields
            try:
                capacity = int(capacity_str)
                floor = int(floor_str)
            except ValueError:
                flash('Invalid numeric values provided', 'error')
                return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
            
            # Validate ranges
            if capacity < 1 or capacity > 500:
                flash('Capacity must be between 1 and 500', 'error')
                return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
            
            if floor < 0 or floor > 20:
                flash('Floor must be between 0 and 20', 'error')
                return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
            
            # Check if room number already exists (excluding current classroom)
            existing_classroom = Classroom.query.filter_by(room_number=room_number).first()
            if existing_classroom and existing_classroom.id != classroom.id:
                flash('Room number already exists', 'error')
                return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
            
            # Update classroom
            classroom.room_number = room_number
            classroom.capacity = capacity
            classroom.building = building
            classroom.room_type = room_type
            classroom.floor = floor
            classroom.status = status
            classroom.facilities = facilities
            classroom.equipment = equipment
            
            db.session.commit()
            flash('Classroom updated successfully', 'success')
            return redirect(url_for('admin_classrooms'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating classroom: {str(e)}', 'error')
            print(f"Classroom update error: {e}")
            return redirect(url_for('admin_edit_classroom', classroom_id=classroom_id))
    
    return render_template('admin/edit_classroom.html', classroom=classroom)

@app.route('/admin/delete_classroom/<int:classroom_id>', methods=['POST'])
@login_required
def admin_delete_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # Check if classroom is being used in timetables
        timetable_count = Timetable.query.filter_by(classroom_id=classroom_id).count()
        if timetable_count > 0:
            flash(f'Cannot delete classroom: It is scheduled in {timetable_count} timetable entries. Please remove timetable entries first.', 'error')
            return redirect(url_for('admin_classrooms'))
        
        # If all checks pass, delete the classroom
        db.session.delete(classroom)
        db.session.commit()
        flash('Classroom deleted successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting classroom: {str(e)}', 'error')
        print(f"Classroom deletion error: {e}")
    
    return redirect(url_for('admin_classrooms'))

# Student Group Management Routes
@app.route('/admin/student_groups')
@login_required
def admin_student_groups():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Load groups with relationships using proper SQLAlchemy joins
        groups = db.session.query(StudentGroup).options(
            db.joinedload(StudentGroup.students),
            db.joinedload(StudentGroup.courses)
        ).all()
        
        # Load courses for each group efficiently
        for group in groups:
            group_courses = StudentGroupCourse.query.filter_by(student_group_id=group.id).all()
            group.course_list = [Course.query.get(sgc.course_id) for sgc in group_courses if Course.query.get(sgc.course_id)]
                
    except Exception as e:
        flash(f'Error loading student groups: {str(e)}', 'error')
        groups = []
    
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
    
    try:
        group = StudentGroup.query.get_or_404(group_id)
        
        if request.method == 'POST':
            course_ids = request.form.getlist('courses')
            # Remove duplicates from course_ids to prevent constraint violations
            unique_course_ids = list(set([int(cid) for cid in course_ids if cid]))
            if len(unique_course_ids) != len(course_ids):
                duplicate_count = len(course_ids) - len(unique_course_ids)
                flash(f'Note: {duplicate_count} duplicate course selections were automatically removed', 'info')
            
            # Remove existing course assignments
            try:
                StudentGroupCourse.query.filter_by(student_group_id=group_id).delete()
            except Exception as e:
                flash(f'Error removing existing assignments: {str(e)}', 'error')
                return redirect(url_for('admin_student_groups'))
            
            # Add new course assignments with retry logic for sequence issues
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # Clear any existing objects in session
                    db.session.rollback()
                    
                    # Add new course assignments (now guaranteed to be unique)
                    for course_id in unique_course_ids:
                        group_course = StudentGroupCourse(
                            student_group_id=group_id,
                            course_id=course_id
                        )
                        db.session.add(group_course)
                    
                    db.session.commit()
                    flash(f'Group courses updated successfully! Added {len(unique_course_ids)} unique courses.', 'success')
                    return redirect(url_for('admin_student_groups'))
                    
                except IntegrityError as e:
                    # Check if it's a sequence issue
                    if 'duplicate key value violates unique constraint "student_group_course_pkey"' in str(e) and attempt == 0:
                        if reset_student_group_course_sequence():
                            continue
                        else:
                            break
                    
                    # Check if it's a unique constraint issue (shouldn't happen now with deduplication)
                    elif 'duplicate key value violates unique constraint "unique_group_course"' in str(e):
                        # This shouldn't happen now, but handle it gracefully
                        flash('Unexpected constraint violation. Please try again or contact support.', 'error')
                        break
                    else:
                        # Re-raise if it's not a sequence issue or we've already tried
                        raise
                except Exception as e:
                    # Re-raise any other exceptions
                    raise
            
            # If we get here, all retries failed
            flash('Failed to update group courses. Please run Database Health Check first.', 'error')
            return redirect(url_for('admin_student_groups'))
        
        # Get all courses and current group courses
        all_courses = Course.query.all()
        current_course_ids = [gc.course_id for gc in group.courses]
        
        return render_template('admin/manage_group_courses.html', 
                             group=group, 
                             all_courses=all_courses, 
                             current_course_ids=current_course_ids)
                             
    except Exception as e:
        print(f"Error in admin_manage_group_courses: {e}")
        flash(f'Error managing group courses: {str(e)}', 'error')
        return redirect(url_for('admin_student_groups'))

# Faculty Routes
@app.route('/faculty/take_attendance/<int:timetable_id>', endpoint='faculty_take_attendance')
@login_required
def faculty_take_attendance(timetable_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        timetable = Timetable.query.get_or_404(timetable_id)
        
        # Verify this timetable belongs to the current faculty
        if timetable.teacher_id != current_user.id:
            flash('You can only take attendance for your own classes', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        # Get students enrolled in this course through student groups
        students = db.session.query(User).join(
            StudentGroupCourse, User.group_id == StudentGroupCourse.student_group_id
        ).filter(
            StudentGroupCourse.course_id == timetable.course_id,
            User.role == 'student'
        ).all()
        
        # If no students found through groups, get all students (fallback)
        if not students:
            students = User.query.filter_by(role='student').limit(20).all()
        
        # Get today's attendance records for this class
        today = datetime.now().date()
        attendance_records = {record.student_id: record for record in 
                             Attendance.query.filter_by(course_id=timetable.course_id, time_slot_id=timetable.time_slot_id, date=today).all()}
        
        return render_template('faculty/take_attendance.html', 
                             timetable=timetable, 
                             students=students,
                             attendance_records=attendance_records,
                             today=today)
                             
    except Exception as e:
        flash(f'Error loading attendance page: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/save_attendance', methods=['POST'], endpoint='faculty_save_attendance')
@login_required
def save_attendance():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        timetable_id = request.form.get('timetable_id')
        date_str = request.form.get('date')
        
        # Validate required fields
        if not all([timetable_id, date_str]):
            flash('Missing required fields', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        # Get the timetable object
        timetable = Timetable.query.get(timetable_id)
        if not timetable:
            flash('Timetable not found', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        # Get all form data for attendance
        for key, value in request.form.items():
            if key.startswith('attendance_'):
                student_id = int(key.replace('attendance_', ''))
                status = value
                
                # Validate status
                if status not in ['present', 'absent', 'late']:
                    continue
                
                # Check if attendance already exists
                existing = Attendance.query.filter_by(
                    student_id=student_id,
                    course_id=timetable.course_id,
                    time_slot_id=timetable.time_slot_id,
                    date=date
                ).first()
                
                if existing:
                    existing.status = status
                    existing.marked_by = current_user.id
                    existing.marked_at = datetime.utcnow()
                else:
                    new_attendance = Attendance(
                        student_id=student_id,
                        course_id=timetable.course_id,
                        time_slot_id=timetable.time_slot_id,
                        date=date,
                        status=status,
                        marked_by=current_user.id
                    )
                    db.session.add(new_attendance)
        
        db.session.commit()
        flash('Attendance saved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving attendance: {str(e)}', 'error')
    
    return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/course_details/<int:course_id>')
@login_required
def course_details(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    try:
        course = Course.query.get_or_404(course_id)
        
        # Verify this course belongs to the current faculty
        course_teacher = CourseTeacher.query.filter_by(course_id=course_id, teacher_id=current_user.id).first()
        if not course_teacher:
            flash('You can only view details for your own courses', 'error')
            return redirect(url_for('faculty_dashboard'))
        
        # Get timetable entries for this course
        timetables = Timetable.query.filter_by(course_id=course_id, teacher_id=current_user.id).all()
        
        return render_template('faculty/course_details.html', course=course, timetables=timetables)
        
    except Exception as e:
        flash(f'Error loading course details: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/course_attendance/<int:course_id>')
@login_required
def course_attendance(course_id):
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Verify this course belongs to the current faculty
    course_teacher = CourseTeacher.query.filter_by(course_id=course_id, teacher_id=current_user.id).first()
    if not course_teacher:
        flash('You can only view attendance for your own courses', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    try:
        # Get attendance records for this course through timetables with proper joins
        attendance_records = db.session.query(Attendance).options(
            db.joinedload(Attendance.student),
            db.joinedload(Attendance.faculty)
        ).filter(
            Attendance.course_id == course_id,
            Attendance.marked_by == current_user.id
        ).order_by(Attendance.date.desc()).all()
                
    except Exception as e:
        flash(f'Error loading attendance data: {str(e)}', 'error')
        attendance_records = []
    
    return render_template('faculty/course_attendance.html', course=course, attendance_records=attendance_records)

@app.route('/faculty/all_attendance')
@login_required
def faculty_all_attendance():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    try:
        # Get all attendance records for courses taught by this faculty with proper joins
        attendance_records = db.session.query(Attendance).options(
            db.joinedload(Attendance.student),
            db.joinedload(Attendance.faculty),
            db.joinedload(Attendance.course),
            db.joinedload(Attendance.time_slot)
        ).filter(
            Attendance.marked_by == current_user.id
        ).order_by(Attendance.date.desc()).all()
                    
    except Exception as e:
        flash(f'Error loading attendance data: {str(e)}', 'error')
        attendance_records = []
    
    return render_template('faculty/all_attendance.html', attendance_records=attendance_records)

# Student Routes
@app.route('/student/timetable')
@login_required
def student_timetable():
    """Show student's comprehensive timetable with calendar and list views"""
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if not current_user.group_id:
        flash('You are not assigned to any student group', 'warning')
        return redirect(url_for('student_dashboard'))
    
    try:
        # Get all time slots to show breaks
        all_time_slots = TimeSlot.query.filter(
            TimeSlot.day.in_(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        ).order_by(TimeSlot.day, TimeSlot.start_time).all()
        
        # Get student's group timetable with proper joins
        timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.teacher),
            db.joinedload(Timetable.student_group)
        ).filter(
            Timetable.student_group_id == current_user.group_id
        ).all()
        
        # Group by day and time for better display
        timetable_by_day = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        # Initialize all days with empty lists and add time slot information
        for day in days:
            timetable_by_day[day] = []
            # Add time slot information for breaks
            for time_slot in all_time_slots:
                if time_slot.day == day:
                    timetable_by_day[day].append({
                        'start_time': time_slot.start_time,
                        'end_time': time_slot.end_time,
                        'break_type': time_slot.break_type,
                        'is_time_slot': True
                    })
        
        # Add timetable entries
        for entry in timetables:
            time_slot = entry.time_slot
            if not time_slot or time_slot.day not in days:
                continue
                
            day = time_slot.day
            
            # Get additional information
            course = entry.course
            classroom = entry.classroom
            teacher = entry.teacher
            
            # Find and update the existing time slot entry
            for slot in timetable_by_day[day]:
                if (slot['start_time'] == time_slot.start_time and 
                    slot['end_time'] == time_slot.end_time):
                    # Update with class information
                    slot.update({
                        'id': entry.id,
                        'course_code': course.code if course else 'Unknown',
                        'course_name': course.name if course else 'Unknown',
                        'classroom': classroom.room_number if classroom else 'Unknown',
                        'building': classroom.building if classroom else 'Unknown',
                        'teacher_name': teacher.name if teacher else 'Unknown',
                        'teacher_department': teacher.department if teacher else 'Unknown',
                        'semester': entry.semester,
                        'academic_year': entry.academic_year,
                        'is_time_slot': False  # Now it's a class
                    })
                    break
        
        # Sort each day by start time
        for day in timetable_by_day:
            timetable_by_day[day].sort(key=lambda x: x['start_time'])
        

        
        # Get unique time slots for calendar view
        time_slots = []
        for time_slot in all_time_slots:
            time_range = f"{time_slot.start_time}-{time_slot.end_time}"
            if time_range not in time_slots:
                time_slots.append(time_range)
        
        # Get student's group info
        student_group = StudentGroup.query.get(current_user.group_id)
                
    except Exception as e:
        flash(f'Error loading timetable data: {str(e)}', 'error')
        timetable_by_day = {}
        time_slots = []
        student_group = None
    
    return render_template('student/timetable.html', 
                         timetable_by_day=timetable_by_day,
                         time_slots=time_slots,
                         student_group=student_group)

@app.route('/student/attendance_history')
@login_required
def student_attendance_history():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get all attendance records for the student with proper joins
        attendance_records = db.session.query(Attendance).options(
            db.joinedload(Attendance.course),
            db.joinedload(Attendance.timetable).joinedload(Timetable.teacher),
            db.joinedload(Attendance.timetable).joinedload(Timetable.classroom)
        ).filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
        
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

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'change_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect', 'error')
                elif new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                elif len(new_password) < 6:
                    flash('New password must be at least 6 characters long', 'error')
                else:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password updated successfully', 'success')
            else:
                # Update profile information
                current_user.name = request.form.get('name')
                current_user.email = request.form.get('email')
                current_user.phone = request.form.get('phone')
                current_user.address = request.form.get('address')
                
                db.session.commit()
                flash('Profile updated successfully', 'success')
            
            return redirect(url_for('student_profile'))
        
        return render_template('student/profile.html', user=current_user)
        
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/student/attendance_alerts')
@login_required
def student_attendance_alerts():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get attendance records for the student with proper joins
        attendance_records = db.session.query(Attendance).options(
            db.joinedload(Attendance.course)
        ).filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
        
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





# Missing API and utility routes
@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    """API endpoint for real-time dashboard statistics"""
    try:
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications')
@login_required
def api_notifications():
    """API endpoint for notifications"""
    try:
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user.id
        ).first()
        
        if notification:
            notification.read = True
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user"""
    try:
        Notification.query.filter_by(
            user_id=current_user.id,
            read=False
        ).update({'read': True})
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user.id
        ).first()
        
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/clear-all', methods=['DELETE'])
@login_required
def clear_all_notifications():
    """Clear all notifications for the current user"""
    try:
        Notification.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>', methods=['GET'])
@login_required
def get_notification(notification_id):
    """Get a specific notification"""
    try:
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user.id
        ).first()
        
        if notification:
            return jsonify({
                'success': True, 
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.type,
                    'read': notification.read,
                    'created_at': notification.created_at.isoformat() if notification.created_at else None
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications', methods=['POST'])
@login_required
def create_notification():
    """Create a new notification (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        title = data.get('title')
        message = data.get('message')
        notification_type = data.get('type', 'info')
        users = data.get('users', ['all'])
        
        if not title or not message:
            return jsonify({'success': False, 'error': 'Title and message are required'}), 400
        
        # Create notifications for specified users
        created_count = 0
        
        if 'all' in users:
            # Send to all users
            all_users = User.query.all()
            for user in all_users:
                notification = Notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    type=notification_type,
                    read=False
                )
                db.session.add(notification)
                created_count += 1
        else:
            # Send to specific user types
            for user_type in users:
                if user_type == 'faculty':
                    faculty_users = User.query.filter_by(role='faculty').all()
                    for user in faculty_users:
                        notification = Notification(
                            user_id=user.id,
                            title=title,
                            message=message,
                            type=notification_type,
                            read=False
                        )
                        db.session.add(notification)
                        created_count += 1
                elif user_type == 'students':
                    student_users = User.query.filter_by(role='student').all()
                    for user in student_users:
                        notification = Notification(
                            user_id=user.id,
                            title=title,
                            message=message,
                            type=notification_type,
                            read=False
                        )
                        db.session.add(notification)
                        created_count += 1
                elif user_type == 'admins':
                    admin_users = User.query.filter_by(role='admin').all()
                    for user in admin_users:
                        notification = Notification(
                            user_id=user.id,
                            title=title,
                            message=message,
                            type=notification_type,
                            read=False
                        )
                        db.session.add(notification)
                        created_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Created {created_count} notifications'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/<int:notification_id>', methods=['PUT'])
@login_required
def update_notification(notification_id):
    """Update a notification (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        if 'title' in data:
            notification.title = data['title']
        if 'message' in data:
            notification.message = data['message']
        if 'type' in data:
            notification.type = data['type']
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/bulk_delete_users', methods=['POST'])
@login_required
def admin_bulk_delete_users():
    """Bulk delete users"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        user_ids = data.get('user_ids', [])
        if not user_ids:
            return jsonify({'success': False, 'message': 'No user IDs provided'}), 400
        
        # Validate user IDs
        try:
            user_ids = [int(uid) for uid in user_ids]
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid user ID format'}), 400
        
        deleted_count = 0
        for user_id in user_ids:
            if int(user_id) != current_user.id:  # Don't delete current user
                user = User.query.get(user_id)
                if user:
                    db.session.delete(user)
                    deleted_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Successfully deleted {deleted_count} users'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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
                        course_id=timetable.course_id,
                        time_slot_id=timetable.time_slot_id,
                        date=date
                    ).first()
                    
                    if not existing:
                        # Randomly assign attendance status
                        import random
                        status = random.choice(['present', 'absent', 'late'])
                        
                        new_attendance = Attendance(
                            student_id=student.id,
                            course_id=timetable.course_id,
                            time_slot_id=timetable.time_slot_id,
                            date=date,
                            status=status,
                            marked_by=current_user.id
                        )
                        db.session.add(new_attendance)
                        attendance_count += 1
        
        db.session.commit()
        flash(f'Added {attendance_count} sample attendance records', 'success')
        
    except Exception as e:
        db.session.rollback()
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
        day = request.form.get('day', '')
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        
        # Validate required fields
        if not all([day, start_time, end_time]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_timetable'))
        
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
        db.session.rollback()
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
        
        day = request.form.get('day', '')
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        
        # Validate required fields
        if not all([day, start_time, end_time]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_time_slots'))
        
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
        db.session.rollback()
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
        db.session.rollback()
        flash(f'Error deleting time slot: {str(e)}', 'error')
    
    return redirect(url_for('admin_time_slots'))



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
            group1 = StudentGroup.query.filter_by(name='CS-2024-1').first()
            group2 = StudentGroup.query.filter_by(name='MATH-2024-1').first()
            
            if all([course1, faculty1, classroom1, time_slot1, group1]):
                timetable1 = Timetable(
                    course_id=course1.id,
                    teacher_id=faculty1.id,
                    classroom_id=classroom1.id,
                    time_slot_id=time_slot1.id,
                    student_group_id=group1.id,
                    semester='Fall 2024',
                    academic_year='2024-2025'
                )
                db.session.add(timetable1)
            
            if all([course2, faculty2, classroom2, time_slot2, group2]):
                timetable2 = Timetable(
                    course_id=course2.id,
                    teacher_id=faculty2.id,
                    classroom_id=classroom2.id,
                    time_slot_id=time_slot2.id,
                    student_group_id=group2.id,
                    semester='Fall 2024',
                    academic_year='2024-2025'
                )
                db.session.add(timetable2)
            
            db.session.commit()

# Missing routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            # Validate required fields
            if not all([username, email, password]):
                flash('All fields are required', 'error')
                return render_template('register.html')
            
            # Validate email format
            if '@' not in email or '.' not in email:
                flash('Please enter a valid email address', 'error')
                return render_template('register.html')
            
            # Validate password length
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return render_template('register.html')
            
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
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/api/courses')
def api_courses():
    try:
        courses = Course.query.all()
        return jsonify([{
            'id': course.id,
            'code': course.code,
            'name': course.name,
            'credits': course.credits,
            'department': course.department
        } for course in courses])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/classrooms')
def api_classrooms():
    try:
        classrooms = Classroom.query.all()
        return jsonify([{
            'id': classroom.id,
            'room_number': classroom.room_number,
            'building': classroom.building,
            'capacity': classroom.capacity,
            'room_type': classroom.room_type
        } for classroom in classrooms])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/time_slots')
def api_time_slots():
    try:
        time_slots = TimeSlot.query.all()
        return jsonify([{
            'id': time_slot.id,
            'day': time_slot.day,
            'start_time': time_slot.start_time,
            'end_time': time_slot.end_time
        } for time_slot in time_slots])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Automatic Timetable Generation Routes
@app.route('/admin/clear_timetables', methods=['POST'])
@login_required
def admin_clear_timetables():
    """Clear all existing timetables but preserve break time slots"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        existing_count = Timetable.query.count()
        if existing_count > 0:
            # Preserve break time slots before clearing
            break_count = preserve_break_time_slots()
            
            # Only delete timetable entries, preserve all time slots including breaks
            Timetable.query.delete()
            db.session.commit()
            flash(f'🗑️ Successfully cleared {existing_count} existing timetables. {break_count} break time slots have been preserved.', 'success')
        else:
            flash('ℹ️ No existing timetables to clear', 'info')
        
        return redirect(url_for('admin_generate_timetables'))
        
    except Exception as e:
        db.session.rollback()
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
            generator = MultiGroupTimetableGenerator()
            
            # Get all time slots
            time_slots = TimeSlot.query.all()
            gen_time_slots = [GenTimeSlot(
                id=ts.id, day=ts.day, start_time=ts.start_time, 
                end_time=ts.end_time, break_type=ts.break_type
            ) for ts in time_slots]
            generator.add_time_slots(gen_time_slots)
            
            # Get all courses
            courses = Course.query.all()
            gen_courses = [GenCourse(
                id=c.id, code=c.code, name=c.name, 
                periods_per_week=c.periods_per_week, department=c.department,
                subject_area=c.subject_area, required_equipment=c.required_equipment or '',
                min_capacity=c.min_capacity, max_students=c.max_students
            ) for c in courses]
            generator.add_courses(gen_courses)
            
            # Get all classrooms
            classrooms = Classroom.query.all()
            gen_classrooms = [GenClassroom(
                id=c.id, room_number=c.room_number, capacity=c.capacity,
                building=c.building, room_type=c.room_type, equipment=c.equipment or ''
            ) for c in classrooms]
            generator.add_classrooms(gen_classrooms)
            
            # Get all teachers
            teachers = User.query.filter_by(role='faculty').all()
            gen_teachers = [GenTeacher(
                id=teacher.id, name=teacher.name, department=teacher.department
            ) for teacher in teachers]
            generator.add_teachers(gen_teachers)
            
            # Get all student groups with their courses
            student_groups = StudentGroup.query.all()
            gen_student_groups = [GenStudentGroup(
                id=group.id, name=group.name, department=group.department,
                year=group.year, semester=group.semester
            ) for group in student_groups]
            generator.add_student_groups(gen_student_groups)
            
            # Generate timetables for all groups
            generated_timetables = generator.generate_timetables()
            
            # Check if generation was successful
            if not generated_timetables:
                flash('❌ No timetables could be generated. The system may be over-constrained.', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
            # Validate global constraints
            if not generator.validate_constraints():
                flash('❌ Generated timetables violate global constraints. Please try again.', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
            # Save generated timetables to database
            # Check if user wants to clear existing timetables
            clear_existing = request.form.get('clear_existing') == 'on'
            
            # Preserve break time slots before any operations
            break_count = preserve_break_time_slots()
            if break_count > 0:
                flash(f'Preserved {break_count} break time slots', 'info')
            
            if clear_existing:
                existing_count = Timetable.query.count()
                if existing_count > 0:
                    Timetable.query.delete()
                    db.session.commit()
            
            # Now check for internal conflicts within the generated timetables
            conflicts_found = []
            global_classroom_usage = defaultdict(list)  # (day, time) -> [classroom_id]
            global_teacher_usage = defaultdict(list)    # (day, time) -> [teacher_id]
            
            for group_id, entries in generated_timetables.items():
                for entry in entries:
                    slot_key = (entry.day, entry.start_time)
                    
                    # Check for classroom conflicts within generated data
                    if entry.classroom_id in global_classroom_usage[slot_key]:
                        conflicts_found.append(f"Classroom {entry.classroom_number} double-booked at {entry.day} {entry.start_time}")
                        continue
                    
                    # Check for teacher conflicts within generated data
                    if entry.teacher_id in global_teacher_usage[slot_key]:
                        conflicts_found.append(f"Teacher {entry.teacher_name} double-booked at {entry.day} {entry.start_time}")
                        continue
                    
                    # Mark as used
                    global_classroom_usage[slot_key].append(entry.classroom_id)
                    global_teacher_usage[slot_key].append(entry.teacher_id)
            
            if conflicts_found:
                # Try to regenerate with stricter constraints
                flash(f'❌ Generated timetables have {len(conflicts_found)} internal conflicts. Please try again or adjust constraints.', 'error')
                return redirect(url_for('admin_generate_timetables'))
            
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
                        # Skip time slots that are breaks - don't schedule classes during breaks
                        if time_slot.break_type == 'Break':
                            continue
                        
                        timetable = Timetable(
                            course_id=entry.course_id,
                            teacher_id=entry.teacher_id,
                            classroom_id=entry.classroom_id,
                            time_slot_id=entry.time_slot_id,
                            student_group_id=entry.student_group_id,
                            semester='Fall 2024',
                            academic_year='2024-25'
                        )
                        db.session.add(timetable)
                        timetables_added += 1
                    else:
                        flash(f'Warning: Missing data for some timetable entries', 'warning')
            
            db.session.commit()
            
            # Get statistics about the generated timetables
            stats = generator.get_timetable_statistics()
            
            # Create a comprehensive summary message
            time_slot_summary = []
            for slot_key, count in sorted(stats['time_slot_usage'].items(), key=lambda x: (x[0][0], x[0][1])):
                day, time = slot_key
                time_slot_summary.append(f"{day} {time}: {count} classes")
            
            # Create detailed success message
            success_details = {
                'total_groups': len(generated_timetables),
                'total_classes': timetables_added,
                'time_slots_used': len(stats['time_slot_usage']),
                'max_classes_per_slot': max(stats['time_slot_usage'].values()) if stats['time_slot_usage'] else 0,
                'time_slot_breakdown': time_slot_summary
            }
            
            # Store detailed results in session for persistent display
            session['timetable_generation_results'] = success_details
            
            # Show immediate success message
            flash(f"✅ Timetables generated successfully! {timetables_added} entries scheduled for {len(generated_timetables)} groups. "
                  f"Maximum classes per time slot: {success_details['max_classes_per_slot']}. "
                  f"View detailed results below.", 'success')
            
            # Clean up generator to free memory
            generator.cleanup()
            
            return redirect(url_for('admin_timetable'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating timetables: {str(e)}', 'error')
            return redirect(url_for('admin_timetable'))
    
    return render_template('admin/generate_timetables.html',
                         student_groups=StudentGroup.query.all(),
                         courses=Course.query.all(),
                         teachers=User.query.filter_by(role='faculty').all(),
                         classrooms=Classroom.query.all(),
                         existing_timetables=Timetable.query.all(),
                         expected_periods=sum(c.periods_per_week for c in Course.query.all()))

@app.route('/faculty/timetable')
@login_required
def faculty_timetable():
    """Display faculty's timetable with attendance options"""
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get faculty's timetables with proper joins
        timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.time_slot)
        ).filter_by(teacher_id=current_user.id).order_by(Timetable.time_slot_id).all()
        
        # Group timetables by day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        timetables_by_day = {}
        for day in days:
            timetables_by_day[day] = []
        
        for timetable in timetables:
            day = timetable.time_slot.day
            if day in timetables_by_day:
                timetables_by_day[day].append(timetable)
        
        return render_template('faculty/timetable.html', 
                             timetables_by_day=timetables_by_day,
                             days=days)
                             
    except Exception as e:
        flash(f'Error loading timetable: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/admin/check_timetable_feasibility')
@login_required
def admin_check_timetable_feasibility():
    """Check if timetable generation is feasible with current constraints"""
    if current_user.role != 'admin':
        return jsonify({'feasible': False, 'reason': 'Access denied'}), 403
    
    try:
        # Starting feasibility check...
        
        # Get all required data
        courses = Course.query.all()
        classrooms = Classroom.query.all()
        teachers = User.query.filter_by(role='faculty').all()
        student_groups = StudentGroup.query.all()
        time_slots = TimeSlot.query.all()
        
        # Check basic resource availability
        if not courses:
            return jsonify({'feasible': False, 'reason': 'No courses available'})
        
        if not classrooms:
            return jsonify({'feasible': False, 'reason': 'No classrooms available'})
        
        if not teachers:
            return jsonify({'feasible': False, 'reason': 'No teachers available'})
        
        if not student_groups:
            return jsonify({'feasible': False, 'reason': 'No student groups available'})
        
        if not time_slots:
            return jsonify({'feasible': False, 'reason': 'No time slots available'})
        
        # Check course-group department matching
        for group in student_groups:
            group_courses = [c for c in courses if c.department == group.department]
            if not group_courses:
                return jsonify({'feasible': False, 'reason': f'No courses available for group {group.name}'})
        
        # Check classroom capacity constraints
        for course in courses:
            suitable_classrooms = [c for c in classrooms if c.capacity >= course.min_capacity]
            if not suitable_classrooms:
                return jsonify({'feasible': False, 'reason': f'No classrooms with sufficient capacity for course {course.code}'})
        
        # Check equipment constraints
        for course in courses:
            if course.required_equipment:
                required_equipment = [eq.strip().lower() for eq in course.required_equipment.split(',') if eq.strip()]
                
                suitable_classrooms = []
                for classroom in classrooms:
                    if classroom.capacity >= course.min_capacity:
                        classroom_equipment = [eq.strip().lower() for eq in (classroom.equipment or '').split(',') if eq.strip()]
                        
                        # Check if all required equipment is available
                        equipment_available = True
                        for req_eq in required_equipment:
                            if req_eq:
                                equipment_found = any(req_eq in eq or eq in req_eq for eq in classroom_equipment)
                                if not equipment_found:
                                    equipment_available = False
                                    break
                        
                        if equipment_available:
                            suitable_classrooms.append(classroom)
                
                if not suitable_classrooms:
                    return jsonify({'feasible': False, 'reason': f'No classrooms with required equipment for course {course.code}'})
        
        # Check teacher availability
        total_required_periods = sum(c.periods_per_week for c in courses)
        total_available_slots = len(time_slots) * len(student_groups)
        
        if total_required_periods > total_available_slots:
            return jsonify({'feasible': False, 'reason': f'Not enough time slots available. Required: {total_required_periods}, Available: {total_available_slots}'})
        
        # Try actual timetable generation
        generator = MultiGroupTimetableGenerator()
        
        # Convert database models to dataclass objects and add all resources
        gen_time_slots = [GenTimeSlot(
            id=ts.id, day=ts.day, start_time=ts.start_time, end_time=ts.end_time
        ) for ts in time_slots]
        generator.add_time_slots(gen_time_slots)
        
        gen_courses = [GenCourse(
            id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
            department=c.department, subject_area=c.subject_area,
            required_equipment=c.required_equipment or '',
            min_capacity=c.min_capacity, max_students=c.max_students
        ) for c in courses]
        generator.add_courses(gen_courses)
        
        gen_classrooms = [GenClassroom(
            id=c.id, room_number=c.room_number, capacity=c.capacity,
            room_type=c.room_type, equipment=c.equipment or '', building=c.building
        ) for c in classrooms]
        generator.add_classrooms(gen_classrooms)
        
        gen_teachers = [GenTeacher(
            id=t.id, name=t.name, department=t.department
        ) for t in teachers]
        generator.add_teachers(gen_teachers)
        
        gen_student_groups = [GenStudentGroup(
            id=g.id, name=g.name, department=g.department,
            year=g.year, semester=g.semester
        ) for g in student_groups]
        generator.add_student_groups(gen_student_groups)
        
        # Generate timetables
        generated_timetables = generator.generate_timetables()
        
        if generated_timetables:
            # Timetable generation successful!
            print(f"   📊 Generated timetables for {len(generated_timetables)} groups")
            
            # Clean up generator to free memory
            generator.cleanup()
            
            return jsonify({
                'feasible': True,
                'reason': f'Successfully generated timetables for {len(generated_timetables)} groups'
            })
        else:
            # Clean up generator to free memory
            generator.cleanup()
            
            return jsonify({
                'feasible': False,
                'reason': 'Timetable generation failed - check constraints and try again'
            })
            
    except Exception as e:
        return jsonify({'feasible': False, 'reason': f'Error during feasibility check: {str(e)}'})

@app.route('/admin/timetable_statistics')
@login_required
def admin_timetable_statistics():
    """Show timetable statistics and conflicts"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
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
                             
    except Exception as e:
        flash(f'Error loading timetable statistics: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

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
        ).options(
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.teacher),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.student_group)
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
            if all([timetable, course, user, classroom, time_slot, student_group]):
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





def sort_timetables_by_time(timetables):
    """Sort timetables by day and time for consistent display order"""
    # Define day order
    day_order = {
        'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7
    }
    
    def sort_key(entry):
        time_slot = entry.time_slot
        if not time_slot:
            return (999, '00:00')  # Put entries without time slots at the end
        return (day_order.get(time_slot.day, 999), time_slot.start_time)
    
    return sorted(timetables, key=sort_key)

def get_timetable_conflicts(timetable_entry, exclude_id=None):
    """Check if a timetable entry conflicts with existing entries"""
    conflicts = []
    
    # Check for classroom conflicts
    classroom_conflicts = Timetable.query.filter(
        Timetable.classroom_id == timetable_entry.classroom_id,
        Timetable.time_slot_id == timetable_entry.time_slot_id,
        Timetable.semester == timetable_entry.semester,
        Timetable.academic_year == timetable_entry.academic_year
    )
    if exclude_id:
        classroom_conflicts = classroom_conflicts.filter(Timetable.id != exclude_id)
    
    if classroom_conflicts.count() > 0:
        # Get classroom info for the conflict message
        classroom = Classroom.query.get(timetable_entry.classroom_id)
        classroom_name = classroom.room_number if classroom else f"ID:{timetable_entry.classroom_id}"
        conflicts.append(f"Classroom {classroom_name} is already booked at this time")
    
    # Check for teacher conflicts
    teacher_conflicts = Timetable.query.filter(
        Timetable.teacher_id == timetable_entry.teacher_id,
        Timetable.time_slot_id == timetable_entry.time_slot_id,
        Timetable.semester == timetable_entry.semester,
        Timetable.academic_year == timetable_entry.academic_year
    )
    if exclude_id:
        teacher_conflicts = teacher_conflicts.filter(Timetable.id != exclude_id)
    
    if teacher_conflicts.count() > 0:
        # Get teacher info for the conflict message
        teacher = User.query.get(timetable_entry.teacher_id)
        teacher_name = teacher.name if teacher else f"ID:{timetable_entry.teacher_id}"
        conflicts.append(f"Teacher {teacher_name} is already booked at this time")
    
    # Check for student group conflicts (same group can't have multiple classes at same time)
    group_conflicts = Timetable.query.filter(
        Timetable.student_group_id == timetable_entry.student_group_id,
        Timetable.time_slot_id == timetable_entry.time_slot_id,
        Timetable.semester == timetable_entry.semester,
        Timetable.academic_year == timetable_entry.academic_year
    )
    if exclude_id:
        group_conflicts = group_conflicts.filter(Timetable.id != exclude_id)
    
    if group_conflicts.count() > 0:
        # Get student group info for the conflict message
        group = StudentGroup.query.get(timetable_entry.student_group_id)
        group_name = group.name if group else f"ID:{timetable_entry.student_group_id}"
        conflicts.append(f"Student group {group_name} already has a class at this time")
    
    return conflicts

@app.route('/admin/clear_generation_results')
@login_required
def admin_clear_generation_results():
    """Clear timetable generation results from session"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('admin_timetable'))
    
    if 'timetable_generation_results' in session:
        del session['timetable_generation_results']
        flash('Generation results cleared successfully!', 'success')
    
    return redirect(url_for('admin_timetable'))

@app.route('/faculty/profile', methods=['GET', 'POST'])
@login_required
def faculty_profile():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'change_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect', 'error')
                elif new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                elif len(new_password) < 6:
                    flash('New password must be at least 6 characters long', 'error')
                else:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password updated successfully', 'success')
            else:
                # Update profile information
                current_user.name = request.form.get('name')
                current_user.email = request.form.get('email')
                current_user.department = request.form.get('department')
                current_user.phone = request.form.get('phone')
                current_user.qualifications = request.form.get('qualifications')
                current_user.experience = request.form.get('experience')
                current_user.bio = request.form.get('bio')
                
                db.session.commit()
                flash('Profile updated successfully', 'success')
            
            return redirect(url_for('faculty_profile'))
        
        return render_template('faculty/profile.html', user=current_user)
        
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'change_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect', 'error')
                elif new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                elif len(new_password) < 6:
                    flash('New password must be at least 6 characters long', 'error')
                else:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password updated successfully', 'success')
            else:
                # Update profile information
                current_user.name = request.form.get('name')
                current_user.email = request.form.get('email')
                current_user.department = request.form.get('department')
                current_user.phone = request.form.get('phone')
                current_user.bio = request.form.get('bio')
                current_user.access_level = request.form.get('access_level')
                
                db.session.commit()
                flash('Profile updated successfully', 'success')
            
            return redirect(url_for('admin_profile'))
        
        return render_template('admin/profile.html', user=current_user)
        
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/student/notifications')
@login_required
def student_notifications():
    if current_user.role != 'student':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
            Notification.created_at.desc()
        ).all()
        
        return render_template('student/notifications.html', notifications=notifications)
        
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'error')
        return redirect(url_for('student_dashboard'))

@app.route('/faculty/notifications')
@login_required
def faculty_notifications():
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
            Notification.created_at.desc()
        ).all()
        
        return render_template('faculty/notifications.html', notifications=notifications)
        
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
            Notification.created_at.desc()
        ).all()
        
        return render_template('admin/notifications.html', notifications=notifications)
        
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/export_database')
@login_required
def export_database():
    """Export database as SQL dump"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if 'postgresql' in database_url or 'postgres' in database_url:
            # For PostgreSQL, provide comprehensive instructions and options
            flash('PostgreSQL database detected. Web export not available due to security restrictions.', 'info')
            
            # Store export instructions in session for display
            session['export_instructions'] = {
                'type': 'postgresql',
                'database_url': database_url,
                'instructions': [
                    'PostgreSQL databases cannot be exported directly through the web interface for security reasons.',
                    'Use one of these methods to export your database:',
                    '',
                    'METHOD 1 - Command Line (Recommended):',
                    '1. Connect to your server via SSH',
                    '2. Run: pg_dump -h [HOST] -U [USERNAME] -d [DATABASE_NAME] > backup.sql',
                    '3. Download the backup.sql file to your computer',
                    '',
                    'METHOD 2 - Using pgAdmin:',
                    '1. Open pgAdmin application',
                    '2. Connect to your database',
                    '3. Right-click database → Backup → Custom format',
                    '4. Choose destination and save',
                    '',
                    'METHOD 3 - Contact Support:',
                    'If you need assistance, contact your database administrator or hosting provider.',
                    '',
                    'Note: For security, database credentials are not displayed here.'
                ]
            }
            return redirect(url_for('admin_dashboard'))
            
        else:
            # SQLite export
            db_path = database_url.replace('sqlite:///', '')
            if db_path.startswith('/'):
                db_path = db_path[1:]
            # Handle Windows paths
            if os.name == 'nt':  # Windows
                db_path = db_path.replace('/', '\\')
            
            # Create SQL dump
            import sqlite3
            conn = sqlite3.connect(db_path)
            dump = StringIO()
            
            for line in conn.iterdump():
                dump.write(f'{line}\n')
            
            conn.close()
            
            # Create response
            response = app.response_class(
                response=dump.getvalue(),
                status=200,
                mimetype='application/sql'
            )
            response.headers['Content-Disposition'] = f'attachment; filename=database_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
            
            flash('SQLite database exported successfully!', 'success')
            return response
        
    except Exception as e:
        flash(f'Error exporting database: {str(e)}', 'error')
        print(f"Database export error: {e}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/import_database', methods=['GET', 'POST'])
@login_required
def import_database():
    """Import database from SQL file"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        if 'database_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['database_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.sql'):
            try:
                # Read SQL file
                sql_content = file.read().decode('utf-8')
                database_url = app.config['SQLALCHEMY_DATABASE_URI']
                
                if 'postgresql' in database_url or 'postgres' in database_url:
                    # PostgreSQL import - provide comprehensive instructions
                    flash('PostgreSQL database detected. Web import not available due to security restrictions.', 'info')
                    
                    # Store import instructions in session for display
                    session['import_instructions'] = {
                        'type': 'postgresql',
                        'database_url': database_url,
                        'instructions': [
                            'PostgreSQL databases cannot be imported directly through the web interface for security reasons.',
                            'Use one of these methods to import your database:',
                            '',
                            'METHOD 1 - Command Line (Recommended):',
                            '1. Connect to your server via SSH',
                            '2. Run: psql -h [HOST] -U [USERNAME] -d [DATABASE_NAME] < backup.sql',
                            '3. Or use: pg_restore -h [HOST] -U [USERNAME] -d [DATABASE_NAME] backup.dump',
                            '',
                            'METHOD 2 - Using pgAdmin:',
                            '1. Open pgAdmin application',
                            '2. Connect to your database',
                            '3. Right-click database → Restore → Choose backup file',
                            '4. Select options and restore',
                            '',
                            'METHOD 3 - Contact Support:',
                            'If you need assistance, contact your database administrator or hosting provider.',
                            '',
                            'Note: For security, database credentials are not displayed here.'
                        ]
                    }
                    return redirect(url_for('admin_dashboard'))
                else:
                    # SQLite import
                    db_path = database_url.replace('sqlite:///', '')
                    if db_path.startswith('/'):
                        db_path = db_path[1:]
                    # Handle Windows paths
                    if os.name == 'nt':  # Windows
                        db_path = db_path.replace('/', '\\')
                    
                    # Execute SQL commands
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Split SQL commands and execute
                    sql_commands = sql_content.split(';')
                    for command in sql_commands:
                        command = command.strip()
                        if command:
                            try:
                                cursor.execute(command)
                            except sqlite3.Error as e:
                                print(f"SQL command failed: {command[:100]}... Error: {e}")
                                continue
                    
                    conn.commit()
                    conn.close()
                    
                    flash('Database imported successfully!', 'success')
                    return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'Error importing database: {str(e)}', 'error')
                print(f"Database import error: {e}")
                return redirect(request.url)
        else:
            flash('Invalid file format. Please upload a .sql file', 'error')
            return redirect(request.url)
    
    return render_template('admin/import_database.html')

@app.route('/admin/export_csv/<table_name>')
@login_required
def export_csv(table_name):
    """Export specific table as CSV"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Get table data
        if table_name == 'users':
            data = User.query.all()
            fields = ['id', 'username', 'email', 'role', 'name', 'department', 'phone', 'address', 'qualifications', 'experience', 'bio', 'access_level', 'group_id', 'created_at', 'last_login']
        elif table_name == 'courses':
            data = Course.query.all()
            fields = ['id', 'code', 'name', 'credits', 'department', 'max_students', 'semester', 'description', 'subject_area', 'required_equipment', 'min_capacity', 'periods_per_week']
        elif table_name == 'timetables':
            data = Timetable.query.all()
            fields = ['id', 'course_id', 'classroom_id', 'time_slot_id', 'teacher_id', 'student_group_id', 'semester', 'academic_year']
        else:
            flash('Invalid table name', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)
        
        for item in data:
            row = []
            for field in fields:
                value = getattr(item, field, '')
                if hasattr(value, 'strftime'):  # Handle datetime objects
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                row.append(str(value) if value is not None else '')
            writer.writerow(row)
        
        # Create response
        response = app.response_class(
            response=output.getvalue(),
            status=200,
            mimetype='text/csv'
        )
        response.headers['Content-Disposition'] = f'attachment; filename={table_name}_export.csv'
        
        return response
        
    except Exception as e:
        flash(f'Error exporting {table_name}: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/generate_qr_code')
@login_required
def generate_qr_code():
    """Generate QR code for current user - valid for 24 hours"""
    try:
        # Check if user already has an active QR code that hasn't expired
        now = datetime.utcnow()
        existing_qr = QRCode.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if existing_qr and existing_qr.expires_at > now:
            # Return existing QR code if it's still valid
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(existing_qr.qr_code_hash)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return jsonify({
                'success': True,
                'qr_code': img_str,
                'qr_hash': existing_qr.qr_code_hash,
                'expires_at': existing_qr.expires_at.isoformat(),
                'generated_at': existing_qr.generated_at.isoformat(),
                'message': 'Using existing QR code (valid for 24 hours)'
            })
        
        # Generate new QR code valid for 24 hours
        qr_hash = str(uuid.uuid4())
        
        # Set expiration to 24 hours from now
        expires_at = now + timedelta(hours=24)
        
        # Deactivate any existing QR codes
        if existing_qr:
            existing_qr.is_active = False
        
        # Try to create new QR code with retry logic for sequence issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                new_qr = QRCode(
                    user_id=current_user.id,
                    qr_code_hash=qr_hash,
                    expires_at=expires_at
                )
                db.session.add(new_qr)
                db.session.commit()
                break  # Success, exit retry loop
            except Exception as e:
                if "duplicate key value violates unique constraint" in str(e) and "qr_code_pkey" in str(e):
                    # Sequence issue - try to reset it
                    if attempt == 0:  # Only try to reset sequence on first attempt
                        try:
                            reset_qr_code_sequence()
                        except Exception as reset_error:
                            print(f"Failed to reset sequence: {reset_error}")
                    
                    if attempt < max_retries - 1:
                        db.session.rollback()
                        # Generate a new hash and try again
                        qr_hash = str(uuid.uuid4())
                        continue
                    else:
                        # Last attempt failed
                        raise e
                else:
                    # Different error, re-raise
                    raise e
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_hash)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': img_str,
            'qr_hash': qr_hash,
            'expires_at': expires_at.isoformat(),
            'generated_at': now.isoformat(),
            'message': 'New QR code generated (valid for 24 hours)'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def reset_qr_code_sequence():
    """Reset the PostgreSQL sequence for qr_code table to fix sequence issues"""
    try:
        # Check if we're using PostgreSQL
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            # Get the current maximum ID from qr_code table
            result = db.session.execute(db.text("SELECT COALESCE(MAX(id), 0) FROM qr_code"))
            max_id = result.scalar()
            
            if max_id is not None:
                # Reset the sequence to start from max_id + 1
                db.session.execute(db.text(f"SELECT setval('qr_code_id_seq', {max_id + 1}, false)"))
                db.session.commit()
                print(f"Reset qr_code sequence to {max_id + 1}")
                return True
        else:
            # For SQLite, this function is not needed
            print("SQLite database detected - sequence reset not needed")
            return True
    except Exception as e:
        print(f"Error resetting sequence: {e}")
        # Don't raise the error, just log it
        return False

def reset_student_group_course_sequence():
    """Reset the PostgreSQL sequence for student_group_course table to fix sequence issues"""
    try:
        # Check if we're using PostgreSQL
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            # Get the current maximum ID from student_group_course table
            result = db.session.execute(db.text("SELECT COALESCE(MAX(id), 0) FROM student_group_course"))
            max_id = result.scalar()
            
            if max_id is not None:
                # Reset the sequence to start from max_id + 1
                db.session.execute(db.text(f"SELECT setval('student_group_course_id_seq', {max_id + 1}, false)"))
                db.session.commit()
                print(f"Reset student_group_course sequence to {max_id + 1}")
                return True
        else:
            # For SQLite, this function is not needed
            print("SQLite database detected - sequence reset not needed")
            return True
    except Exception as e:
        print(f"Error resetting sequence: {e}")
        # Don't raise the error, just log it
        return False

@app.route('/admin/reset_qr_sequence')
@login_required
def admin_reset_qr_sequence():
    """Admin route to manually reset QR code sequence"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if reset_qr_code_sequence():
            flash('QR code sequence reset successfully', 'success')
        else:
            flash('Failed to reset QR code sequence', 'error')
    except Exception as e:
        flash(f'Error resetting sequence: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_student_group_course_sequence')
@login_required
def admin_reset_student_group_course_sequence():
    """Admin route to manually reset student group course sequence"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if reset_student_group_course_sequence():
            flash('Student group course sequence reset successfully', 'success')
        else:
            flash('Failed to reset student group course sequence', 'error')
    except Exception as e:
        flash(f'Error resetting sequence: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/database_health_check')
@login_required
def admin_database_health_check():
    """Admin route to run comprehensive database health check"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        print("🔍 Admin requested database health check...")
        health_result = check_database_health()
        
        if health_result['healthy']:
            flash('Database health check completed - no issues found', 'success')
        else:
            if health_result['fixes_applied']:
                flash(f'Database health check completed - {len(health_result["fixes_applied"])} fixes applied, {len(health_result["issues"])} issues remain', 'warning')
            else:
                flash(f'Database health check completed - {len(health_result["issues"])} issues found', 'error')
        
        # Log the results for debugging
        print(f"Health check results: {health_result}")
        
    except Exception as e:
        print(f"Error running health check: {e}")
        flash(f'Error running database health check: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/api/mark-attendance', methods=['POST'])
@login_required
def api_mark_attendance():
    """API endpoint for marking attendance (used by main.js)"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Only faculty can mark attendance'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        time_slot_id = data.get('time_slot_id')
        timetable_id = data.get('timetable_id')  # For backward compatibility
        status = data.get('status')
        date_str = data.get('date')
        
        # API mark attendance called
        
        # Handle both new format (course_id + time_slot_id) and old format (timetable_id)
        if timetable_id and not (course_id and time_slot_id):
            # Old format - we need to get course_id and time_slot_id from timetable
            # For now, we'll use a default time slot (you may need to adjust this)
            if not course_id:
                course_id = 1  # Default course ID
            if not time_slot_id:
                time_slot_id = 1  # Default time slot ID
            print(f"Using default values - course_id: {course_id}, time_slot_id: {time_slot_id}")
        
        if not all([student_id, course_id, time_slot_id, status, date_str]):
            missing = []
            if not student_id: missing.append('student_id')
            if not course_id: missing.append('course_id')
            if not time_slot_id: missing.append('time_slot_id')
            if not status: missing.append('status')
            if not date_str: missing.append('date')
            return jsonify({'success': False, 'error': f'Missing required data: {", ".join(missing)}'})
        
        # Convert to proper types
        try:
            student_id = int(student_id)
            course_id = int(course_id)
            time_slot_id = int(time_slot_id)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid data format'})
        
        # Check if attendance already marked
        existing_attendance = Attendance.query.filter_by(
            student_id=student_id,
            course_id=course_id,
            time_slot_id=time_slot_id,
            date=date_obj
        ).first()
        
        if existing_attendance:
            # Update existing attendance
            existing_attendance.status = status
            existing_attendance.marked_by = current_user.id
            existing_attendance.marked_at = datetime.utcnow()
        else:
            # Create new attendance
            attendance = Attendance(
                student_id=student_id,
                course_id=course_id,
                time_slot_id=time_slot_id,
                date=date_obj,
                status=status,
                marked_by=current_user.id,
                marked_at=datetime.utcnow()
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        # Successfully marked attendance
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked successfully'
        })
        
    except Exception as e:
        print(f"Error in api_mark_attendance: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/scan_qr_code', methods=['POST'])
@login_required
def scan_qr_code():
    """Scan QR code and mark attendance"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Only faculty can mark attendance'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'})
        
        qr_hash = data.get('qr_hash')
        course_id = data.get('course_id')
        time_slot_id = data.get('time_slot_id')
        
        # Received QR code data
        
        if not all([qr_hash, course_id, time_slot_id]):
            missing = []
            if not qr_hash: missing.append('qr_hash')
            if not course_id: missing.append('course_id')
            if not time_slot_id: missing.append('time_slot_id')
            return jsonify({'success': False, 'error': f'Missing required data: {", ".join(missing)}'})
        
        # Convert IDs to integers
        try:
            course_id = int(course_id)
            time_slot_id = int(time_slot_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid course_id or time_slot_id format'})
        
        # Check if this is a test QR code
        if qr_hash.startswith('test-qr-'):
            # For test QR codes, we'll create a mock attendance record
            # Get course information for response
            course = Course.query.get(course_id)
            if not course:
                return jsonify({'success': False, 'error': f'Course with ID {course_id} not found'})
            
            # Get time slot information
            time_slot = TimeSlot.query.get(time_slot_id)
            if not time_slot:
                return jsonify({'success': False, 'error': f'Time slot with ID {time_slot_id} not found'})
            
            # Find the class instance for today
            today = date.today()
            class_instance = ClassInstance.query.filter_by(
                timetable_id=db.session.query(Timetable.id).filter_by(
                    course_id=course_id,
                    time_slot_id=time_slot_id
                ).scalar(),
                class_date=today
            ).first()
            
            if not class_instance:
                return jsonify({'success': False, 'error': f'No class scheduled for {course.name} on {today.strftime("%A, %B %d, %Y")}'})
            
            # Check if test attendance already marked for this session
            existing_test_attendance = Attendance.query.filter_by(
                course_id=course_id,
                class_instance_id=class_instance.id,
                date=today,
                qr_code_used=qr_hash
            ).first()
            
            if existing_test_attendance:
                return jsonify({'success': False, 'error': 'Test attendance already marked for this session'})
            
            # For test QR codes, we need a valid student_id
            # Let's find the first student in the system or create a dummy one
            test_student = User.query.filter_by(role='student').first()
            if not test_student:
                # If no students exist, we can't create test attendance
                return jsonify({'success': False, 'error': 'No students found in system. Cannot create test attendance.'})
            
            # Create test attendance record with valid student_id
            test_attendance = Attendance(
                student_id=test_student.id,  # Use actual student ID for test
                course_id=course_id,
                time_slot_id=time_slot_id,
                class_instance_id=class_instance.id,
                date=today,
                marked_by=current_user.id,
                qr_code_used=qr_hash,
                status='present'  # Default status for test
            )
            
            db.session.add(test_attendance)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Test attendance marked successfully for {course.name}',
                'student_name': f'Test Student ({test_student.name})',
                'course_name': f'{course.code} - {course.name}'
            })
        
        # Handle real QR codes
        # Verify QR code exists and is active
        qr_code = QRCode.query.filter_by(
            qr_code_hash=qr_hash,
            is_active=True
        ).first()
        
        if not qr_code:
            return jsonify({'success': False, 'error': 'Invalid or expired QR code'})
        
        if qr_code.expires_at < datetime.utcnow():
            return jsonify({'success': False, 'error': 'QR code has expired'})
        
        # Get student from QR code
        student = qr_code.user
        if student.role != 'student':
            return jsonify({'success': False, 'error': 'QR code is not for a student'})
        
        # Get course information for response
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'success': False, 'error': f'Course with ID {course_id} not found'})
        
        # Get time slot information
        time_slot = TimeSlot.query.get(time_slot_id)
        if not time_slot:
            return jsonify({'success': False, 'error': f'Time slot with ID {time_slot_id} not found'})
        
        # Find the class instance for today
        today = date.today()
        class_instance = ClassInstance.query.filter_by(
            timetable_id=db.session.query(Timetable.id).filter_by(
                course_id=course_id,
                time_slot_id=time_slot_id
            ).scalar(),
            class_date=today
        ).first()
        
        if not class_instance:
            return jsonify({'success': False, 'error': f'No class scheduled for {course.name} on {today.strftime("%A, %B %d, %Y")}'})
        
        # Processing attendance for student
        
        # Check if attendance already marked for this class instance
        existing_attendance = Attendance.query.filter_by(
            student_id=student.id,
            course_id=course_id,
            class_instance_id=class_instance.id,
            date=today
        ).first()
        
        if existing_attendance:
            return jsonify({'success': False, 'error': 'Attendance already marked for this session'})
        
        # Time-based attendance logic
        now = datetime.utcnow()
        current_time = now.time()
        
        # Parse time slot start and end times
        try:
            start_time = datetime.strptime(time_slot.start_time, '%H:%M').time()
            end_time = datetime.strptime(time_slot.end_time, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid time slot format'})
        
        # Check if class is currently active
        if current_time < start_time:
            return jsonify({'success': False, 'error': f'Class has not started yet. Class starts at {time_slot.start_time}'})
        
        if current_time > end_time:
            return jsonify({'success': False, 'error': f'Class has ended. Class ended at {time_slot.end_time}'})
        
        # Determine attendance status based on time
        # Calculate minutes late (15 minutes grace period)
        grace_period = timedelta(minutes=15)
        class_start_datetime = datetime.combine(today, start_time)
        late_threshold = class_start_datetime + grace_period
        
        if now > late_threshold:
            status = 'late'
            status_message = f'Late entry marked for {student.name} (arrived {((now - class_start_datetime).total_seconds() / 60):.0f} minutes after class start)'
        else:
            status = 'present'
            status_message = f'Attendance marked for {student.name}'
        
        # Mark attendance with determined status
        attendance = Attendance(
            student_id=student.id,
            course_id=course_id,
            time_slot_id=time_slot_id,
            class_instance_id=class_instance.id,
            date=today,
            marked_by=current_user.id,
            qr_code_used=qr_hash,
            status=status
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        # Deactivate QR code after use
        qr_code.is_active = False
        db.session.commit()
        
        # Successfully marked attendance
        
        return jsonify({
            'success': True,
            'message': status_message,
            'student_name': student.name,
            'course_name': f'{course.code} - {course.name}',
            'status': status,
            'marked_at': now.isoformat()
        })
        
    except Exception as e:
        print(f"Error in scan_qr_code: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/faculty/attendance_scanner')
@login_required
def attendance_scanner():
    """QR code scanner interface for faculty"""
    if current_user.role != 'faculty':
        flash('Access denied. Faculty privileges required.', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    try:
        # Get current date for display
        today = date.today().strftime('%A, %B %d, %Y')
        
        # Get faculty's courses for selection
        course_assignments = CourseTeacher.query.filter_by(teacher_id=current_user.id).all()
        course_ids = [assignment.course_id for assignment in course_assignments]
        courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
        
        # If no courses assigned, show all courses as fallback
        if not courses:
            courses = Course.query.all()
            print(f"Warning: No courses assigned to faculty {current_user.id}, showing all courses as fallback")
        
        # Get time slots
        time_slots = TimeSlot.query.all()
        
        # Faculty course assignments and dropdown data loaded
        
        return render_template('faculty/attendance_scanner.html', 
                             today=today, 
                             courses=courses, 
                             time_slots=time_slots)
                             
    except Exception as e:
        print(f"Error in attendance_scanner route: {str(e)}")
        flash(f'Error loading attendance scanner: {str(e)}', 'error')
        return redirect(url_for('faculty_dashboard'))

@app.route('/faculty/mark_absent_manually', methods=['POST'])
@login_required
def mark_absent_manually():
    """Manual endpoint to trigger absent marking for faculty"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Only faculty can mark attendance'})
    
    try:
        # Run the absent marking process
        mark_absent_students()
        
        return jsonify({
            'success': True,
            'message': 'Automatic absent marking completed successfully'
        })
        
    except Exception as e:
        print(f"Error in manual absent marking: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error marking absent students: {str(e)}'
        })

@app.route('/student/my_qr_code')
@login_required
def my_qr_code():
    """Display student's QR code"""
    if current_user.role != 'student':
        flash('Access denied. Student privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    return render_template('student/my_qr_code.html')

# API endpoints for attendance scanner
@app.route('/api/course/<int:course_id>')
@login_required
def api_course(course_id):
    """Get course information for API"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'error': 'Course not found'})
    
    return jsonify({
        'success': True,
        'course': {
            'id': course.id,
            'code': course.code,
            'name': course.name,
            'department': course.department
        }
    })

@app.route('/api/timeslot/<int:timeslot_id>')
@login_required
def api_timeslot(timeslot_id):
    """Get time slot information for API"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    timeslot = TimeSlot.query.get(timeslot_id)
    if not timeslot:
        return jsonify({'success': False, 'error': 'Time slot not found'})
    
    return jsonify({
        'success': True,
        'timeslot': {
            'id': timeslot.id,
            'day': timeslot.day,
            'start_time': timeslot.start_time,  # Already in HH:MM format
            'end_time': timeslot.end_time       # Already in HH:MM format
        }
    })

# Temporary route for Render database initialization
@app.route('/init-db')
def init_database():
    """Temporary route to initialize database tables on Render"""
    try:
        # Check if we're on Render (PostgreSQL)
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return jsonify({
                'success': False,
                'error': 'DATABASE_URL not found. Are you on Render?'
            })
        
        if 'postgresql' in database_url or 'postgres' in database_url:
            # Create all tables
            with app.app_context():
                db.create_all()
                
                # Verify tables were created
                inspector = db.inspect(db.engine)
                tables = inspector.get_table_names()
                
                return jsonify({
                    'success': True,
                    'message': 'Database tables created successfully!',
                    'tables_created': len(tables),
                    'table_names': tables,
                    'next_steps': [
                        'Tables are now created on Render',
                        'Download your migration script',
                        'Run migration to populate data',
                        'Test your app on Render'
                    ]
                })
        else:
            return jsonify({
                'success': False,
                'error': 'Not connected to PostgreSQL. Are you on Render?'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/init-db-page')
def init_database_page():
    """Page to initialize database tables on Render"""
    return render_template('init_db.html')

@app.route('/admin/attendance_statistics')
@login_required
def admin_attendance_statistics():
    """Show comprehensive attendance statistics"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Overall statistics
        total_attendance = Attendance.query.count()
        total_present = Attendance.query.filter_by(status='present').count()
        total_absent = Attendance.query.filter_by(status='absent').count()
        total_late = Attendance.query.filter_by(status='late').count()
        
        # Calculate percentages
        attendance_percentage = (total_present / total_attendance * 100) if total_attendance > 0 else 0
        absent_percentage = (total_absent / total_attendance * 100) if total_attendance > 0 else 0
        late_percentage = (total_late / total_attendance * 100) if total_attendance > 0 else 0
        
        # Student statistics
        students = User.query.filter_by(role='student').all()
        student_stats = []
        for student in students:
            student_attendance = Attendance.query.filter_by(student_id=student.id).all()
            total_classes = len(student_attendance)
            present_classes = len([a for a in student_attendance if a.status == 'present'])
            attendance_pct = (present_classes / total_classes * 100) if total_classes > 0 else 0
            
            student_stats.append({
                'student': student,
                'total_classes': total_classes,
                'present_classes': present_classes,
                'attendance_percentage': attendance_pct,
                'status': 'Good' if attendance_pct >= 75 else 'Warning' if attendance_pct >= 60 else 'Critical'
            })
        
        # Sort students by attendance percentage
        student_stats.sort(key=lambda x: x['attendance_percentage'], reverse=True)
        
        # Faculty statistics
        faculty_stats = []
        faculty_users = User.query.filter_by(role='faculty').all()
        for faculty in faculty_users:
            marked_attendance = Attendance.query.filter_by(marked_by=faculty.id).all()
            total_marked = len(marked_attendance)
            present_marked = len([a for a in marked_attendance if a.status == 'present'])
            
            faculty_stats.append({
                'faculty': faculty,
                'total_marked': total_marked,
                'present_marked': present_marked,
                'attendance_percentage': (present_marked / total_marked * 100) if total_marked > 0 else 0
            })
        
        # Course statistics
        courses = Course.query.all()
        course_stats = []
        for course in courses:
            course_attendance = Attendance.query.filter_by(course_id=course.id).all()
            total_course_classes = len(course_attendance)
            present_course_classes = len([a for a in course_attendance if a.status == 'present'])
            
            course_stats.append({
                'course': course,
                'total_classes': total_course_classes,
                'present_classes': present_course_classes,
                'attendance_percentage': (present_course_classes / total_course_classes * 100) if total_course_classes > 0 else 0
            })
        
        # Group statistics
        groups = StudentGroup.query.all()
        group_stats = []
        for group in groups:
            group_students = User.query.filter_by(group_id=group.id).all()
            group_total_attendance = 0
            group_total_present = 0
            
            for student in group_students:
                student_attendance = Attendance.query.filter_by(student_id=student.id).all()
                group_total_attendance += len(student_attendance)
                group_total_present += len([a for a in student_attendance if a.status == 'present'])
            
            group_stats.append({
                'group': group,
                'total_students': len(group_students),
                'total_attendance': group_total_attendance,
                'total_present': group_total_present,
                'attendance_percentage': (group_total_present / group_total_attendance * 100) if group_total_attendance > 0 else 0
            })
        
        # Recent attendance trends (last 30 days)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        recent_attendance = Attendance.query.filter(Attendance.date >= thirty_days_ago).all()
        
        # Daily attendance for the last 30 days
        daily_stats = {}
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            day_attendance = [a for a in recent_attendance if a.date == date]
            total_day = len(day_attendance)
            present_day = len([a for a in day_attendance if a.status == 'present'])
            
            daily_stats[date] = {
                'total': total_day,
                'present': present_day,
                'percentage': (present_day / total_day * 100) if total_day > 0 else 0
            }
        
        # Department statistics
        departments = db.session.query(User.department).filter(User.department.isnot(None)).distinct().all()
        dept_stats = []
        for dept in departments:
            dept_name = dept[0]
            dept_students = User.query.filter_by(role='student', department=dept_name).all()
            dept_total_attendance = 0
            dept_total_present = 0
            
            for student in dept_students:
                student_attendance = Attendance.query.filter_by(student_id=student.id).all()
                dept_total_attendance += len(student_attendance)
                dept_total_present += len([a for a in student_attendance if a.status == 'present'])
            
            dept_stats.append({
                'department': dept_name,
                'total_students': len(dept_students),
                'total_attendance': dept_total_attendance,
                'total_present': dept_total_present,
                'attendance_percentage': (dept_total_present / dept_total_attendance * 100) if dept_total_attendance > 0 else 0
            })
        
        return render_template('admin/attendance_statistics.html',
                             total_attendance=total_attendance,
                             total_present=total_present,
                             total_absent=total_absent,
                             total_late=total_late,
                             attendance_percentage=attendance_percentage,
                             absent_percentage=absent_percentage,
                             late_percentage=late_percentage,
                             student_stats=student_stats,
                             faculty_stats=faculty_stats,
                             course_stats=course_stats,
                             group_stats=group_stats,
                             daily_stats=daily_stats,
                             dept_stats=dept_stats)
                             
    except Exception as e:
        flash(f'Error loading attendance statistics: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

def check_database_health():
    """Comprehensive database health check to identify and fix common issues"""
    try:
        issues = []
        fixes_applied = []
        
        print("🔍 Starting database health check...")
        
        # Check if we're using PostgreSQL
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            print("📊 PostgreSQL database detected, checking sequences...")
            
            # Check and fix QR code sequence
            try:
                result = db.session.execute(db.text("SELECT COALESCE(MAX(id), 0) FROM qr_code"))
                max_qr_id = result.scalar()
                if max_qr_id is not None:
                    db.session.execute(db.text(f"SELECT setval('qr_code_id_seq', {max_qr_id + 1}, false)"))
                    fixes_applied.append(f"QR code sequence reset to {max_qr_id + 1}")
            except Exception as e:
                issues.append(f"QR code sequence check failed: {e}")
            
            # Check and fix student group course sequence
            try:
                result = db.session.execute(db.text("SELECT COALESCE(MAX(id), 0) FROM student_group_course"))
                max_sgc_id = result.scalar()
                if max_sgc_id is not None:
                    db.session.execute(db.text(f"SELECT setval('student_group_course_id_seq', {max_sgc_id + 1}, false)"))
                    fixes_applied.append(f"Student group course sequence reset to {max_sgc_id + 1}")
            except Exception as e:
                issues.append(f"Student group course sequence check failed: {e}")
            
            # Check for orphaned records
            try:
                # Check for attendance records with invalid student_id
                orphaned_attendance = db.session.execute(db.text(
                    "SELECT COUNT(*) FROM attendance WHERE student_id IS NULL OR student_id NOT IN (SELECT id FROM \"user\")"
                )).scalar()
                if orphaned_attendance > 0:
                    issues.append(f"Found {orphaned_attendance} attendance records with invalid student_id")
                
                # Check for attendance records with invalid course_id
                orphaned_course_attendance = db.session.execute(db.text(
                    "SELECT COUNT(*) FROM attendance WHERE course_id IS NULL OR course_id NOT IN (SELECT id FROM course)"
                )).scalar()
                if orphaned_course_attendance > 0:
                    issues.append(f"Found {orphaned_course_attendance} attendance records with invalid course_id")
                
                # Check for attendance records with invalid time_slot_id
                orphaned_timeslot_attendance = db.session.execute(db.text(
                    "SELECT COUNT(*) FROM attendance WHERE time_slot_id IS NULL OR time_slot_id NOT IN (SELECT id FROM time_slot)"
                )).scalar()
                if orphaned_timeslot_attendance > 0:
                    issues.append(f"Found {orphaned_timeslot_attendance} attendance records with invalid time_slot_id")
                
            except Exception as e:
                issues.append(f"Orphaned record check failed: {e}")
            
            # Check for unique constraint violations in student_group_course
            try:
                # Find duplicate entries that violate unique constraint
                duplicates = db.session.execute(db.text("""
                    SELECT student_group_id, course_id, COUNT(*) as count
                    FROM student_group_course 
                    GROUP BY student_group_id, course_id 
                    HAVING COUNT(*) > 1
                """)).fetchall()
                
                if duplicates:
                    issues.append(f"Found {len(duplicates)} duplicate group-course combinations")
                    
                    # Fix duplicates by keeping only one record per combination
                    for duplicate in duplicates:
                        group_id, course_id, count = duplicate
                        if count > 1:
                            # Delete all but one record for this combination
                            db.session.execute(db.text("""
                                DELETE FROM student_group_course 
                                WHERE student_group_id = %s AND course_id = %s
                                AND id NOT IN (
                                    SELECT MIN(id) FROM student_group_course 
                                    WHERE student_group_id = %s AND course_id = %s
                                )
                            """), (group_id, course_id, group_id, course_id))
                            
                            deleted_count = db.session.execute(db.text("""
                                SELECT COUNT(*) FROM student_group_course 
                                WHERE student_group_id = %s AND course_id = %s
                            """), (group_id, course_id)).scalar()
                            
                            fixes_applied.append(f"Fixed duplicate group {group_id}-course {course_id}: kept 1 record")
                
            except Exception as e:
                issues.append(f"Duplicate constraint check failed: {e}")
            
            # Commit all fixes
            if fixes_applied:
                db.session.commit()
                print("✅ Database fixes applied successfully")
            else:
                print("✅ No database fixes needed")
                
        else:
            print("📊 SQLite database detected - sequence checks not needed")
        
        # Check table row counts
        try:
            tables = ['user', 'course', 'classroom', 'time_slot', 'timetable', 'attendance', 'qr_code', 'student_group', 'student_group_course']
            for table in tables:
                try:
                    count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"📋 {table}: {count} rows")
                except Exception as e:
                    issues.append(f"Failed to count rows in {table}: {e}")
        except Exception as e:
            issues.append(f"Table count check failed: {e}")
        
        # Report results
        if issues:
            print("⚠️  Database health check found issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Database health check completed - no issues found")
            
        if fixes_applied:
            print("🔧 Fixes applied:")
            for fix in fixes_applied:
                print(f"   - {fix}")
        
        return {
            'issues': issues,
            'fixes_applied': fixes_applied,
            'healthy': len(issues) == 0
        }
        
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return {
            'issues': [f"Health check failed: {e}"],
            'fixes_applied': [],
            'healthy': False
        }

# Add connection event handlers
# Connection event handlers will be registered after app context is available

# Database connection recovery function
def get_db_engine():
    """Get database engine with connection recovery"""
    if 'DATABASE_URL' in os.environ:
        database_url = os.environ['DATABASE_URL']
        # Add connection pooling and recovery options
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Test connections before use
            pool_recycle=3600,   # Recycle connections every hour
            connect_args={
                "connect_timeout": 10,
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5
            }
        )
        return engine
    return None

# Enhanced database session with retry logic
def get_db_session_with_retry(max_retries=3, delay=1):
    """Get database session with automatic retry on connection failures"""
    for attempt in range(max_retries):
        try:
            session = db.session
            # Test the connection
            session.execute("SELECT 1")
            return session
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                # Try to refresh the session
                try:
                    db.session.rollback()
                except:
                    pass
            else:
                print("Max retries reached, raising exception")
                raise e
    return None

@app.route('/api/db-health')
def api_db_health():
    """Check database connection health"""
    try:
        # Test basic connection
        result = db.session.execute(text("SELECT 1 as test"))
        basic_connection = result.fetchone()[0] == 1
        
        # Test a simple query
        user_count = User.query.count()
        
        # Get connection info
        engine_info = {
            'pool_size': db.engine.pool.size(),
            'checked_in': db.engine.pool.checkedin(),
            'checked_out': db.engine.pool.checkedout(),
            'overflow': db.engine.pool.overflow(),
            'invalid': db.engine.pool.invalid()
        }
        
        return jsonify({
            'status': 'healthy',
            'basic_connection': basic_connection,
            'user_count': user_count,
            'connection_pool': engine_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/db-reconnect')
def api_db_reconnect():
    """Force database reconnection"""
    try:
        # Dispose of current connection pool
        db.engine.dispose()
        
        # Test new connection
        result = db.session.execute(text("SELECT 1 as test"))
        test_result = result.fetchone()[0] == 1
        
        return jsonify({
            'status': 'reconnected',
            'test_result': test_result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'reconnection_failed',
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def init_database_connection():
    """Initialize database connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Test the connection
            with app.app_context():
                result = db.session.execute(text("SELECT 1"))
                test_result = result.fetchone()[0]
                if test_result == 1:
                    print("✅ Database connection established successfully")
                    return True
        except Exception as e:
            print(f"❌ Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
            else:
                print("💥 Max retries reached. Database connection failed.")
                return False
    return False

def mark_absent_students():
    """Automatically mark students as absent for classes that have ended"""
    try:
        now = datetime.utcnow()
        today = date.today()
        
        print(f"Running automatic absent marking at {now}")
        
        # Get all class instances for today that have ended
        ended_classes = []
        
        # Get all class instances for today
        today_class_instances = ClassInstance.query.filter_by(class_date=today).all()
        
        for class_instance in today_class_instances:
            try:
                # Get the timetable and time slot for this class instance
                timetable = class_instance.timetable
                if not timetable or not timetable.time_slot:
                    continue
                
                # Parse end time
                end_time = datetime.strptime(timetable.time_slot.end_time, '%H:%M').time()
                class_end_datetime = datetime.combine(today, end_time)
                
                # Check if class has ended (more than 5 minutes after end time to allow for processing)
                if now > class_end_datetime + timedelta(minutes=5):
                    ended_classes.append(class_instance)
            except ValueError:
                print(f"Warning: Invalid time format for time slot {timetable.time_slot.id if timetable and timetable.time_slot else 'unknown'}")
                continue
        
        if not ended_classes:
            print("No classes have ended yet today")
            return
        
        print(f"Found {len(ended_classes)} classes that have ended")
        
        # For each ended class, find students who should be marked absent
        absent_count = 0
        
        for class_instance in ended_classes:
            timetable = class_instance.timetable
            if not timetable:
                continue
            
            # Get all students in the group for this timetable
            student_group = timetable.student_group
            if not student_group:
                continue
            
            # Get all students in this group
            students = User.query.filter_by(
                role='student',
                student_group_id=student_group.id
            ).all()
            
            for student in students:
                # Check if attendance is already marked for this student, course, and class instance today
                existing_attendance = Attendance.query.filter_by(
                    student_id=student.id,
                    course_id=timetable.course_id,
                    class_instance_id=class_instance.id,
                    date=today
                ).first()
                
                # If no attendance record exists, mark as absent
                if not existing_attendance:
                    # Find a faculty member to mark the attendance (use the course teacher or first available faculty)
                    faculty = timetable.teacher if timetable.teacher else User.query.filter_by(role='faculty').first()
                    
                    if faculty:
                        absent_attendance = Attendance(
                            student_id=student.id,
                            course_id=timetable.course_id,
                            time_slot_id=timetable.time_slot_id,
                            class_instance_id=class_instance.id,
                            date=today,
                            status='absent',
                            marked_by=faculty.id,
                            marked_at=now,
                            qr_code_used='auto_marked_absent'
                        )
                        
                        db.session.add(absent_attendance)
                        absent_count += 1
                        
                        print(f"Marked {student.name} as absent for {timetable.course.name} at {timetable.time_slot.start_time}-{timetable.time_slot.end_time}")
        
        if absent_count > 0:
            db.session.commit()
            print(f"Successfully marked {absent_count} students as absent")
        else:
            print("No students needed to be marked as absent")
            
    except Exception as e:
        print(f"Error in mark_absent_students: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

def start_scheduler():
    """Start the background scheduler for automatic tasks"""
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    # Schedule automatic absent marking to run every 5 minutes
    schedule.every(5).minutes.do(mark_absent_students)
    
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ Background scheduler started for automatic absent marking")

def check_break_conflicts(day, start_time, end_time, exclude_slot_id=None):
    """Check if a break time conflicts with existing classes or other breaks"""
    conflicts = []
    
    # Check for overlapping time slots
    overlapping_slots = TimeSlot.query.filter(
        TimeSlot.day == day,
        db.or_(
            db.and_(TimeSlot.start_time < end_time, TimeSlot.end_time > start_time),
            db.and_(TimeSlot.start_time == start_time, TimeSlot.end_time == end_time)
        )
    )
    
    if exclude_slot_id:
        overlapping_slots = overlapping_slots.filter(TimeSlot.id != exclude_slot_id)
    
    for slot in overlapping_slots:
        if slot.break_type == 'Break':
            conflicts.append(f"Conflicts with existing break at {slot.start_time}-{slot.end_time}")
        else:
            # Check if there are classes scheduled in this time slot
            existing_classes = Timetable.query.filter_by(time_slot_id=slot.id).count()
            if existing_classes > 0:
                conflicts.append(f"Conflicts with {existing_classes} scheduled class(es) at {slot.start_time}-{slot.end_time}")
    
    return conflicts

def preserve_break_time_slots():
    """Ensure all break time slots are preserved and not accidentally modified"""
    try:
        # Get all time slots that are breaks
        break_slots = TimeSlot.query.filter(TimeSlot.break_type == 'Break').all()
        
        # Ensure these slots remain as breaks
        for slot in break_slots:
            if slot.break_type != 'Break':
                # This shouldn't happen, but let's fix it
                slot.break_type = 'Break'
                print(f"Fixed break slot {slot.id} on {slot.day} {slot.start_time}-{slot.end_time}")
        
        db.session.commit()
        return len(break_slots)
    except Exception as e:
        print(f"Error preserving break time slots: {e}")
        return 0

if __name__ == '__main__':
    # Initialize database connection before starting the app
    if init_database_connection():
        # Start the background scheduler for automatic absent marking
        start_scheduler()
        app.run(debug=True)
    else:
        print("❌ Cannot start application without database connection")
else:
    # Start the background scheduler for automatic absent marking when imported
    # This ensures it runs in both development and production
    try:
        start_scheduler()
    except Exception as e:
        print(f"Warning: Could not start scheduler: {e}")
