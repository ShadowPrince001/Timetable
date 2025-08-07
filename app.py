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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable_attendance.db'
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
    attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
    
    return render_template('student/dashboard.html',
                         attendance_records=attendance_records,
                         total_classes=total_classes,
                         present_classes=present_classes,
                         attendance_percentage=attendance_percentage)

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
