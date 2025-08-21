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
    semester = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    
    # Relationships
    course = db.relationship('Course', backref='timetable_entries')
    classroom = db.relationship('Classroom', backref='timetable_entries')
    time_slot = db.relationship('TimeSlot', backref='timetable_entries')
    teacher = db.relationship('User', backref='teaching_schedule')
    student_group = db.relationship('StudentGroup', backref='timetables')
    
    # Constraints - Multi-group timetable with global resource constraints
    __table_args__ = (
        # Group-specific: No double-booking within the same group
        db.UniqueConstraint('student_group_id', 'classroom_id', 'time_slot_id', 'semester', 'academic_year', 
                           name='unique_group_classroom_time'),
        db.UniqueConstraint('student_group_id', 'teacher_id', 'time_slot_id', 'semester', 'academic_year', 
                           name='unique_group_teacher_time'),
        # Global: No classroom conflicts across groups
        db.UniqueConstraint('classroom_id', 'time_slot_id', 'semester', 'academic_year', 
                           name='unique_global_classroom_time'),
        # Global: No teacher conflicts across groups
        db.UniqueConstraint('teacher_id', 'time_slot_id', 'semester', 'academic_year', 
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
    status = db.Column(db.String(20), default='present')  # present, absent, late
    marked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # faculty who marked
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_used = db.Column(db.String(255))  # QR code hash used for attendance
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='attendance_records')
    course = db.relationship('Course', backref='attendance_records')
    time_slot = db.relationship('TimeSlot', backref='attendance_records')
    faculty = db.relationship('User', foreign_keys=[marked_by], backref='marked_attendance')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'date', 'time_slot_id', name='unique_attendance'),
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
    """QR Code model for attendance tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    qr_code_hash = db.Column(db.String(255), unique=True, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='qr_codes')
    
    def __repr__(self):
        return f'<QRCode {self.qr_code_hash[:8]}...>'

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
        
        # Get today's classes with optimized query
        today = datetime.now().strftime('%A')
        today_classes = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom)
        ).join(TimeSlot).filter(
            Timetable.teacher_id == current_user.id,
            TimeSlot.day == today
        ).all()
                
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
        
        # Get today's classes with optimized query
        today = datetime.now().strftime('%A')
        today_classes = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.teacher),
            db.joinedload(Timetable.classroom)
        ).join(TimeSlot).filter(
            TimeSlot.day == today
        ).limit(5).all()
                
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
        db.session.delete(timetable)
        db.session.commit()
        flash('Timetable entry deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timetable: {str(e)}', 'error')
    
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
                
                # Create new break time slot
                break_slot = TimeSlot(
                    day=day,
                    start_time=start_time,
                    end_time=end_time,
                    break_type=break_type
                )
                db.session.add(break_slot)
                
            elif action == 'update_break':
                slot_id = request.form.get('slot_id', type=int)
                slot = TimeSlot.query.get_or_404(slot_id)
                slot.break_type = request.form.get('break_type', 'Break')
                
            elif action == 'delete_break':
                slot_id = request.form.get('slot_id', type=int)
                slot = TimeSlot.query.get_or_404(slot_id)
                
                # Only allow deletion of break slots
                if slot.break_type != 'none':
                    db.session.delete(slot)
                else:
                    flash('Cannot delete regular time slots', 'error')
                    return redirect(url_for('admin_manage_breaks'))
            
            db.session.commit()
            flash('Break time updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error managing breaks: {str(e)}', 'error')
    
    # Get all time slots sorted by day and time
    time_slots = TimeSlot.query.order_by(TimeSlot.day, TimeSlot.start_time).all()
    
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
# DISABLED - Use QR attendance scanner instead
# @app.route('/faculty/take_attendance/<int:timetable_id>', endpoint='faculty_take_attendance')
# @login_required
def faculty_take_attendance_disabled(timetable_id):
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
                        # If this time slot was previously a break, convert it back to a regular time slot
                        if time_slot.break_type != 'none':
                            time_slot.break_type = 'none'
                        
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
    """Show compiled timetable for faculty member across all groups"""
    if current_user.role != 'faculty':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        
        # Get all timetables for this faculty member with proper joins
        faculty_timetables = db.session.query(Timetable).options(
            db.joinedload(Timetable.time_slot),
            db.joinedload(Timetable.course),
            db.joinedload(Timetable.classroom),
            db.joinedload(Timetable.student_group)
        ).filter_by(teacher_id=current_user.id).all()
        
        # Get all time slots to show breaks
        all_time_slots = TimeSlot.query.filter(
            TimeSlot.day.in_(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        ).order_by(TimeSlot.day, TimeSlot.start_time).all()
        
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
        for entry in faculty_timetables:
            time_slot = entry.time_slot
            if not time_slot or time_slot.day not in days:
                continue
                
            day = time_slot.day
            
            # Get additional information
            course = entry.course
            classroom = entry.classroom
            student_group = entry.student_group
            
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
                        'student_group': student_group.name if student_group else 'Unknown',
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
        
        return render_template('faculty/timetable.html', 
                             timetable_by_day=timetable_by_day,
                             time_slots=time_slots,
                             faculty_name=current_user.name)
                             
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
        print(f"\n🔍 DEBUG: Starting feasibility check...")
        
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
            print(f"✅ DEBUG: Timetable generation successful!")
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
        # Get database file path - cross-platform compatible
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if db_path.startswith('/'):
            db_path = db_path[1:]
        # Handle Windows paths
        if os.name == 'nt':  # Windows
            db_path = db_path.replace('/', '\\')
        
        # Create SQL dump
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
        response.headers['Content-Disposition'] = 'attachment; filename=database_backup.sql'
        
        return response
        
    except Exception as e:
        flash(f'Error exporting database: {str(e)}', 'error')
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
                
                # Get database file path - cross-platform compatible
                db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                if db_path.startswith('/'):
                    db_path = db_path[1:]
                # Handle Windows paths
                if os.name == 'nt':  # Windows
                    db_path = db_path.replace('/', '\\')
                
                # Execute SQL commands
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Split SQL commands and execute
                sql_commands = sql_content.split(';')
                for command in sql_commands:
                    command = command.strip()
                    if command:
                        cursor.execute(command)
                
                conn.commit()
                conn.close()
                
                flash('Database imported successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'Error importing database: {str(e)}', 'error')
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
    """Generate QR code for current user - fixed per day"""
    try:
        # Check if user already has an active QR code for today
        today = date.today()
        existing_qr = QRCode.query.filter_by(
            user_id=current_user.id, 
            is_active=True
        ).first()
        
        if existing_qr:
            # Check if the existing QR code is for today
            if existing_qr.generated_at.date() == today:
                # Return existing QR code for today
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
                    'message': 'Using existing QR code for today'
                })
        
        # Generate new QR code for today
        qr_hash = str(uuid.uuid4())
        
        # Set expiration to end of today (23:59:59)
        expires_at = datetime.combine(today, datetime.max.time().replace(microsecond=0))
        
        # Deactivate any existing QR codes
        if existing_qr:
            existing_qr.is_active = False
        
        new_qr = QRCode(
            user_id=current_user.id,
            qr_code_hash=qr_hash,
            expires_at=expires_at
        )
        db.session.add(new_qr)
        db.session.commit()
        
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
            'generated_at': datetime.utcnow().isoformat(),
            'message': 'New QR code generated for today'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/scan_qr_code', methods=['POST'])
@login_required
def scan_qr_code():
    """Scan QR code and mark attendance"""
    if current_user.role != 'faculty':
        return jsonify({'success': False, 'error': 'Only faculty can mark attendance'})
    
    try:
        data = request.get_json()
        qr_hash = data.get('qr_hash')
        course_id = data.get('course_id')
        time_slot_id = data.get('time_slot_id')
        
        if not all([qr_hash, course_id, time_slot_id]):
            return jsonify({'success': False, 'error': 'Missing required data'})
        
        # Verify QR code
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
            return jsonify({'success': False, 'error': 'Course not found'})
        
        # Check if attendance already marked
        existing_attendance = Attendance.query.filter_by(
            student_id=student.id,
            course_id=course_id,
            date=date.today(),
            time_slot_id=time_slot_id
        ).first()
        
        if existing_attendance:
            return jsonify({'success': False, 'error': 'Attendance already marked for this session'})
        
        # Mark attendance
        attendance = Attendance(
            student_id=student.id,
            course_id=course_id,
            date=date.today(),
            time_slot_id=time_slot_id,
            marked_by=current_user.id,
            qr_code_used=qr_hash
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        # Deactivate QR code after use
        qr_code.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Attendance marked for {student.name}',
            'student_name': student.name,
            'course_name': f'{course.code} - {course.name}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/faculty/attendance_scanner')
@login_required
def attendance_scanner():
    """QR code scanner interface for faculty"""
    if current_user.role != 'faculty':
        flash('Access denied. Faculty privileges required.', 'error')
        return redirect(url_for('faculty_dashboard'))
    
    # Get current date for display
    today = date.today().strftime('%A, %B %d, %Y')
    
    return render_template('faculty/attendance_scanner.html', today=today)

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

if __name__ == '__main__':
    app.run(debug=True)
