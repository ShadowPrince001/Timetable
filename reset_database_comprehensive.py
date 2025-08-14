#!/usr/bin/env python3
"""
Comprehensive Database Reset Script for Timetable & Attendance System
This script will reset the database with new schema including all new fields,
constraints, and comprehensive sample data with Indian names and full week schedule.
"""
import os
from app import app, db, init_db, User, Course, Classroom, TimeSlot, Timetable, Attendance, CourseTeacher
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

def reset_database():
    print("🔄 Resetting database with comprehensive schema and data...")
    with app.app_context():
        print("🗑️  Dropping existing tables...")
        db.drop_all()
        print("🏗️  Creating new tables with constraints...")
        db.create_all()
        print("📊 Initializing with comprehensive sample data...")
        init_comprehensive_data()
        print("✅ Database reset completed successfully!")
        print("🎯 New schema includes:")
        print("   • User: phone, address, qualifications fields")
        print("   • Course: semester, description, subject_area fields with constraints")
        print("   • Classroom: room_type, floor, status, facilities fields with constraints")
        print("   • TimeSlot: break_type, notes fields")
        print("   • Timetable: Unique constraints for double booking prevention")
        print("   • Teacher qualification checks")
        print("\n🚀 You can now start the application with: python app.py")

def init_comprehensive_data():
    """Initialize database with comprehensive sample data"""
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@university.edu',
        password_hash=generate_password_hash('admin'),
        role='admin',
        name='Dr. Rajesh Kumar',
        department='Administration',
        phone='+91-9876543210',
        address='University Campus, Block A, Room 101',
        qualifications='PhD in Management, MBA'
    )
    db.session.add(admin)
    
    # Create faculty members with Indian names and qualifications
    faculty_members = [
        {
            'username': 'prof_sharma',
            'name': 'Dr. Priya Sharma',
            'email': 'priya.sharma@university.edu',
            'department': 'Computer Science',
            'phone': '+91-9876543211',
            'address': 'Faculty Quarters, Block B, Room 201',
            'qualifications': 'PhD in Computer Science, M.Tech in Software Engineering'
        },
        {
            'username': 'prof_patel',
            'name': 'Prof. Amit Patel',
            'email': 'amit.patel@university.edu',
            'department': 'Mathematics',
            'phone': '+91-9876543212',
            'address': 'Faculty Quarters, Block B, Room 202',
            'qualifications': 'PhD in Mathematics, M.Sc in Applied Mathematics'
        },
        {
            'username': 'prof_verma',
            'name': 'Dr. Sunita Verma',
            'email': 'sunita.verma@university.edu',
            'department': 'Physics',
            'phone': '+91-9876543213',
            'address': 'Faculty Quarters, Block B, Room 203',
            'qualifications': 'PhD in Physics, M.Sc in Physics'
        },
        {
            'username': 'prof_singh',
            'name': 'Prof. Rajinder Singh',
            'email': 'rajinder.singh@university.edu',
            'department': 'Chemistry',
            'phone': '+91-9876543214',
            'address': 'Faculty Quarters, Block B, Room 204',
            'qualifications': 'PhD in Chemistry, M.Sc in Organic Chemistry'
        },
        {
            'username': 'prof_gupta',
            'name': 'Dr. Meera Gupta',
            'email': 'meera.gupta@university.edu',
            'department': 'English',
            'phone': '+91-9876543215',
            'address': 'Faculty Quarters, Block B, Room 205',
            'qualifications': 'PhD in English Literature, MA in English'
        },
        {
            'username': 'prof_kumar',
            'name': 'Prof. Sanjay Kumar',
            'email': 'sanjay.kumar@university.edu',
            'department': 'Economics',
            'phone': '+91-9876543216',
            'address': 'Faculty Quarters, Block B, Room 206',
            'qualifications': 'PhD in Economics, MA in Economics'
        }
    ]
    
    faculty_users = []
    for faculty_data in faculty_members:
        faculty = User(
            username=faculty_data['username'],
            email=faculty_data['email'],
            password_hash=generate_password_hash('password'),
            role='faculty',
            name=faculty_data['name'],
            department=faculty_data['department'],
            phone=faculty_data['phone'],
            address=faculty_data['address'],
            qualifications=faculty_data['qualifications']
        )
        db.session.add(faculty)
        faculty_users.append(faculty)
    
    # Create students with Indian names
    student_names = [
        'Arjun Reddy', 'Priya Patel', 'Rahul Sharma', 'Anjali Singh', 'Vikram Malhotra',
        'Kavya Gupta', 'Aditya Verma', 'Zara Khan', 'Rohan Kapoor', 'Ishita Joshi',
        'Krishna Iyer', 'Maya Desai', 'Aryan Mehta', 'Diya Nair', 'Shaurya Rao',
        'Ananya Krishnan', 'Vedant Saxena', 'Riya Chopra', 'Dhruv Agarwal', 'Kiara Reddy',
        'Arnav Tiwari', 'Saanvi Mishra', 'Advait Sinha', 'Myra Bhat', 'Ishaan Das',
        'Aisha Khan', 'Vivaan Sharma', 'Zara Patel', 'Aarav Singh', 'Anaya Gupta'
    ]
    
    students = []
    for i, name in enumerate(student_names):
        student = User(
            username=f'student{i+1}',
            email=f'student{i+1}@university.edu',
            password_hash=generate_password_hash('password'),
            role='student',
            name=name,
            department='Computer Science' if i < 10 else 'Mathematics' if i < 20 else 'Physics',
            phone=f'+91-98765{43210+i:05d}',
            address=f'Student Hostel, Block C, Room {301+i}'
        )
        db.session.add(student)
        students.append(student)
    
    db.session.commit()
    
    # Create courses with subject areas and equipment requirements
    courses_data = [
        {
            'code': 'CS101',
            'name': 'Introduction to Computer Science',
            'credits': 4,
            'department': 'Computer Science',
            'subject_area': 'Computer Science',
            'max_students': 60,
            'min_capacity': 30,
            'semester': '1',
            'description': 'Fundamental concepts of computer science and programming',
            'required_equipment': 'Projector, Whiteboard'
        },
        {
            'code': 'CS201',
            'name': 'Data Structures and Algorithms',
            'credits': 4,
            'department': 'Computer Science',
            'subject_area': 'Computer Science',
            'max_students': 50,
            'min_capacity': 25,
            'semester': '2',
            'description': 'Advanced data structures and algorithm analysis',
            'required_equipment': 'Projector, Whiteboard, Computer'
        },
        {
            'code': 'CS301',
            'name': 'Database Management Systems',
            'credits': 3,
            'department': 'Computer Science',
            'subject_area': 'Computer Science',
            'max_students': 45,
            'min_capacity': 20,
            'semester': '3',
            'description': 'Database design, SQL, and database administration',
            'required_equipment': 'Projector, Whiteboard, Computer, Database Software'
        },
        {
            'code': 'MATH101',
            'name': 'Calculus I',
            'credits': 4,
            'department': 'Mathematics',
            'subject_area': 'Mathematics',
            'max_students': 70,
            'min_capacity': 40,
            'semester': '1',
            'description': 'Introduction to differential and integral calculus',
            'required_equipment': 'Whiteboard, Projector'
        },
        {
            'code': 'MATH201',
            'name': 'Linear Algebra',
            'credits': 3,
            'department': 'Mathematics',
            'subject_area': 'Mathematics',
            'max_students': 55,
            'min_capacity': 30,
            'semester': '2',
            'description': 'Vector spaces, matrices, and linear transformations',
            'required_equipment': 'Whiteboard, Projector'
        },
        {
            'code': 'PHY101',
            'name': 'Physics I',
            'credits': 4,
            'department': 'Physics',
            'subject_area': 'Physics',
            'max_students': 65,
            'min_capacity': 35,
            'semester': '1',
            'description': 'Classical mechanics and thermodynamics',
            'required_equipment': 'Projector, Whiteboard, Physics Lab Equipment'
        },
        {
            'code': 'CHEM101',
            'name': 'General Chemistry',
            'credits': 4,
            'department': 'Chemistry',
            'subject_area': 'Chemistry',
            'max_students': 60,
            'min_capacity': 25,
            'semester': '1',
            'description': 'Basic principles of chemistry and chemical reactions',
            'required_equipment': 'Chemistry Lab Equipment, Fume Hoods, Safety Equipment'
        },
        {
            'code': 'ENG101',
            'name': 'English Composition',
            'credits': 3,
            'department': 'English',
            'subject_area': 'English',
            'max_students': 40,
            'min_capacity': 20,
            'semester': '1',
            'description': 'Academic writing and communication skills',
            'required_equipment': 'Whiteboard'
        },
        {
            'code': 'ECO101',
            'name': 'Principles of Economics',
            'credits': 3,
            'department': 'Economics',
            'subject_area': 'Economics',
            'max_students': 75,
            'min_capacity': 40,
            'semester': '1',
            'description': 'Introduction to microeconomics and macroeconomics',
            'required_equipment': 'Projector, Whiteboard'
        }
    ]
    
    courses = []
    for course_data in courses_data:
        course = Course(**course_data)
        db.session.add(course)
        courses.append(course)
    
    # Create classrooms
    classrooms_data = [
        {
            'room_number': '101',
            'capacity': 60,
            'building': 'Science Building',
            'room_type': 'lecture',
            'floor': 1,
            'status': 'active',
            'facilities': 'Projector, Whiteboard, Air Conditioning, Sound System',
            'equipment': 'Projector, Whiteboard, Microphone'
        },
        {
            'room_number': '102',
            'capacity': 50,
            'building': 'Science Building',
            'room_type': 'lecture',
            'floor': 1,
            'status': 'active',
            'facilities': 'Projector, Whiteboard, Air Conditioning',
            'equipment': 'Projector, Whiteboard'
        },
        {
            'room_number': '201',
            'capacity': 70,
            'building': 'Science Building',
            'room_type': 'lecture',
            'floor': 2,
            'status': 'active',
            'facilities': 'Smart Board, Projector, Air Conditioning',
            'equipment': 'Smart Board, Projector'
        },
        {
            'room_number': '202',
            'capacity': 45,
            'building': 'Science Building',
            'room_type': 'seminar',
            'floor': 2,
            'status': 'active',
            'facilities': 'Whiteboard, Air Conditioning',
            'equipment': 'Whiteboard'
        },
        {
            'room_number': 'LAB101',
            'capacity': 30,
            'building': 'Science Building',
            'room_type': 'lab',
            'floor': 1,
            'status': 'active',
            'facilities': 'Computer Workstations, Projector, Air Conditioning',
            'equipment': '30 Computers, Projector, Network Switch'
        },
        {
            'room_number': 'LAB102',
            'capacity': 25,
            'building': 'Science Building',
            'room_type': 'lab',
            'floor': 1,
            'status': 'active',
            'facilities': 'Chemistry Lab Equipment, Fume Hoods, Air Conditioning',
            'equipment': 'Lab Equipment, Safety Equipment'
        }
    ]
    
    classrooms = []
    for classroom_data in classrooms_data:
        classroom = Classroom(**classroom_data)
        db.session.add(classroom)
        classrooms.append(classroom)
    
    db.session.commit()
    
    # Create comprehensive time slots for full week (9 AM to 5 PM with 1 hour break)
    time_slots_data = []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    time_periods = [
        ('09:00', '10:00'),
        ('10:00', '11:00'),
        ('11:15', '12:15'),  # Break from 11:00-11:15
        ('12:15', '13:15'),
        ('14:00', '15:00'),  # Lunch break from 13:15-14:00
        ('15:00', '16:00'),
        ('16:00', '17:00')
    ]
    
    for day in days:
        for start_time, end_time in time_periods:
            break_type = 'short' if start_time == '11:15' else 'none'
            time_slot = TimeSlot(
                day=day,
                start_time=start_time,
                end_time=end_time,
                break_type=break_type,
                notes=f'{day} {start_time}-{end_time} slot'
            )
            db.session.add(time_slot)
            time_slots_data.append(time_slot)
    
    db.session.commit()
    
    # Create CourseTeacher assignments (many-to-many relationship)
    teacher_assignments = {
        'prof_sharma': [('CS101', True), ('CS201', True), ('CS301', True)],  # Primary Computer Science teacher
        'prof_patel': [('MATH101', True), ('MATH201', True)],                # Primary Mathematics teacher
        'prof_verma': [('PHY101', True)],                                    # Primary Physics teacher
        'prof_singh': [('CHEM101', True)],                                   # Primary Chemistry teacher
        'prof_gupta': [('ENG101', True)],                                    # Primary English teacher
        'prof_kumar': [('ECO101', True)]                                     # Primary Economics teacher
    }
    
    # Add secondary teachers for some courses (multiple teachers per course)
    secondary_assignments = [
        ('prof_sharma', 'MATH101', False),  # CS teacher can also teach math
        ('prof_patel', 'CS101', False),     # Math teacher can also teach CS
        ('prof_verma', 'MATH101', False),   # Physics teacher can also teach math
        ('prof_singh', 'PHY101', False),    # Chemistry teacher can also teach physics
    ]
    
    # Create primary assignments
    for teacher_username, course_assignments in teacher_assignments.items():
        teacher = User.query.filter_by(username=teacher_username).first()
        for course_code, is_primary in course_assignments:
            course = Course.query.filter_by(code=course_code).first()
            if course and teacher:
                course_teacher = CourseTeacher(
                    course_id=course.id,
                    teacher_id=teacher.id,
                    is_primary=is_primary
                )
                db.session.add(course_teacher)
    
    # Create secondary assignments
    for teacher_username, course_code, is_primary in secondary_assignments:
        teacher = User.query.filter_by(username=teacher_username).first()
        course = Course.query.filter_by(code=course_code).first()
        if course and teacher:
            # Check if assignment already exists
            existing = CourseTeacher.query.filter_by(
                course_id=course.id,
                teacher_id=teacher.id
            ).first()
            if not existing:
                course_teacher = CourseTeacher(
                    course_id=course.id,
                    teacher_id=teacher.id,
                    is_primary=is_primary
                )
                db.session.add(course_teacher)
    
    db.session.commit()
    
    # Create comprehensive timetable entries for the full week
    timetable_entries = []
    
    # Monday Schedule
    monday_slots = TimeSlot.query.filter_by(day='Monday').order_by(TimeSlot.start_time).all()
    monday_courses = ['CS101', 'MATH101', 'PHY101', 'CHEM101', 'ENG101', 'ECO101', 'CS201']
    monday_teachers = ['prof_sharma', 'prof_patel', 'prof_verma', 'prof_singh', 'prof_gupta', 'prof_kumar', 'prof_sharma']
    
    for i, (slot, course_code, teacher_username) in enumerate(zip(monday_slots, monday_courses, monday_teachers)):
        course = Course.query.filter_by(code=course_code).first()
        teacher = User.query.filter_by(username=teacher_username).first()
        classroom = classrooms[i % len(classrooms)]
        
        if course and teacher and classroom:
            timetable = Timetable(
                course_id=course.id,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                time_slot_id=slot.id,
                semester='Fall 2024',
                academic_year='2024-25'
            )
            db.session.add(timetable)
            timetable_entries.append(timetable)
    
    # Tuesday Schedule
    tuesday_slots = TimeSlot.query.filter_by(day='Tuesday').order_by(TimeSlot.start_time).all()
    tuesday_courses = ['MATH101', 'CS101', 'CHEM101', 'PHY101', 'ENG101', 'ECO101', 'MATH201']
    tuesday_teachers = ['prof_patel', 'prof_sharma', 'prof_singh', 'prof_verma', 'prof_gupta', 'prof_kumar', 'prof_patel']
    
    for i, (slot, course_code, teacher_username) in enumerate(zip(tuesday_slots, tuesday_courses, tuesday_teachers)):
        course = Course.query.filter_by(code=course_code).first()
        teacher = User.query.filter_by(username=teacher_username).first()
        classroom = classrooms[(i + 1) % len(classrooms)]
        
        if course and teacher and classroom:
            timetable = Timetable(
                course_id=course.id,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                time_slot_id=slot.id,
                semester='Fall 2024',
                academic_year='2024-25'
            )
            db.session.add(timetable)
            timetable_entries.append(timetable)
    
    # Wednesday Schedule
    wednesday_slots = TimeSlot.query.filter_by(day='Wednesday').order_by(TimeSlot.start_time).all()
    wednesday_courses = ['PHY101', 'MATH101', 'CS101', 'ENG101', 'CHEM101', 'ECO101', 'CS301']
    wednesday_teachers = ['prof_verma', 'prof_patel', 'prof_sharma', 'prof_gupta', 'prof_singh', 'prof_kumar', 'prof_sharma']
    
    for i, (slot, course_code, teacher_username) in enumerate(zip(wednesday_slots, wednesday_courses, wednesday_teachers)):
        course = Course.query.filter_by(code=course_code).first()
        teacher = User.query.filter_by(username=teacher_username).first()
        classroom = classrooms[(i + 2) % len(classrooms)]
        
        if course and teacher and classroom:
            timetable = Timetable(
                course_id=course.id,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                time_slot_id=slot.id,
                semester='Fall 2024',
                academic_year='2024-25'
            )
            db.session.add(timetable)
            timetable_entries.append(timetable)
    
    # Thursday Schedule
    thursday_slots = TimeSlot.query.filter_by(day='Thursday').order_by(TimeSlot.start_time).all()
    thursday_courses = ['CHEM101', 'PHY101', 'MATH101', 'CS101', 'ENG101', 'ECO101', 'MATH201']
    thursday_teachers = ['prof_singh', 'prof_verma', 'prof_patel', 'prof_sharma', 'prof_gupta', 'prof_kumar', 'prof_patel']
    
    for i, (slot, course_code, teacher_username) in enumerate(zip(thursday_slots, thursday_courses, thursday_teachers)):
        course = Course.query.filter_by(code=course_code).first()
        teacher = User.query.filter_by(username=teacher_username).first()
        classroom = classrooms[(i + 3) % len(classrooms)]
        
        if course and teacher and classroom:
            timetable = Timetable(
                course_id=course.id,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                time_slot_id=slot.id,
                semester='Fall 2024',
                academic_year='2024-25'
            )
            db.session.add(timetable)
            timetable_entries.append(timetable)
    
    # Friday Schedule
    friday_slots = TimeSlot.query.filter_by(day='Friday').order_by(TimeSlot.start_time).all()
    friday_courses = ['ENG101', 'CHEM101', 'PHY101', 'MATH101', 'CS101', 'ECO101', 'CS201']
    friday_teachers = ['prof_gupta', 'prof_singh', 'prof_verma', 'prof_patel', 'prof_sharma', 'prof_kumar', 'prof_sharma']
    
    for i, (slot, course_code, teacher_username) in enumerate(zip(friday_slots, friday_courses, friday_teachers)):
        course = Course.query.filter_by(code=course_code).first()
        teacher = User.query.filter_by(username=teacher_username).first()
        classroom = classrooms[(i + 4) % len(classrooms)]
        
        if course and teacher and classroom:
            timetable = Timetable(
                course_id=course.id,
                teacher_id=teacher.id,
                classroom_id=classroom.id,
                time_slot_id=slot.id,
                semester='Fall 2024',
                academic_year='2024-25'
            )
            db.session.add(timetable)
            timetable_entries.append(timetable)
    
    db.session.commit()
    
    # Create sample attendance records for the past week
    print("📊 Creating sample attendance records...")
    
    # Get some timetable entries for attendance
    sample_timetables = Timetable.query.limit(10).all()
    sample_students = students[:20]  # First 20 students
    
    # Create attendance for the past 5 days
    for day_offset in range(5):
        attendance_date = date.today() - timedelta(days=day_offset + 1)
        
        for timetable in sample_timetables:
            for student in sample_students:
                # Random attendance (80% present, 15% absent, 5% late)
                status_choice = random.choices(['present', 'absent', 'late'], weights=[80, 15, 5])[0]
                
                attendance = Attendance(
                    student_id=student.id,
                    timetable_id=timetable.id,
                    date=attendance_date,
                    status=status_choice,
                    marked_by=timetable.teacher_id,
                    marked_at=datetime.now()
                )
                db.session.add(attendance)
    
    db.session.commit()
    
    print(f"✅ Created comprehensive data:")
    print(f"   • {len(faculty_users)} faculty members with Indian names")
    print(f"   • {len(students)} students with Indian names")
    print(f"   • {len(courses)} courses with subject areas")
    print(f"   • {len(classrooms)} classrooms with facilities")
    print(f"   • {len(time_slots_data)} time slots (full week 9 AM - 5 PM)")
    print(f"   • {len(timetable_entries)} timetable entries")
    print(f"   • Sample attendance records for past week")
    print(f"   • Teacher qualification constraints implemented")
    print(f"   • Double booking prevention constraints active")

if __name__ == "__main__":
    db_file = "timetable_attendance.db"
    if os.path.exists(db_file):
        print(f"⚠️  Warning: Database file '{db_file}' will be deleted!")
        response = input("Do you want to continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Database reset cancelled.")
            exit()
        os.remove(db_file)
        print(f"🗑️  Removed old database file: {db_file}")
    reset_database()
