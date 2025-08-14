#!/usr/bin/env python3
"""
Flask-based Database Synchronization Script
Integrates with the existing Flask app to synchronize databases across environments.
"""

from app import app, db, User, Course, Classroom, TimeSlot, StudentGroup, StudentGroupCourse, Timetable, Attendance, Notification, CourseTeacher
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import sys

def detect_environment():
    """Detect the current environment"""
    if 'RENDER' in os.environ:
        return 'render'
    elif 'CODESPACES' in os.environ:
        return 'codespace'
    else:
        return 'local'

def sync_database():
    """Synchronize the database structure and data"""
    with app.app_context():
        print("🔄 Starting Flask-based database synchronization...")
        
        # Detect environment
        env = detect_environment()
        print(f"🌍 Environment detected: {env.upper()}")
        
        try:
            # Create all tables
            print("🏗️ Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if sample data already exists
            existing_users = User.query.count()
            if existing_users > 0:
                print(f"ℹ️ Found {existing_users} existing users, checking data consistency...")
                
                # Verify all required tables have data
                tables_data = {
                    'Users': User.query.count(),
                    'Courses': Course.query.count(),
                    'Classrooms': Classroom.query.count(),
                    'TimeSlots': TimeSlot.query.count(),
                    'StudentGroups': StudentGroup.query.count(),
                    'Timetables': Timetable.query.count(),
                    'Attendance': Attendance.query.count(),
                    'Notifications': Notification.query.count(),
                    'CourseTeachers': CourseTeacher.query.count()
                }
                
                print("📊 Current database state:")
                for table, count in tables_data.items():
                    print(f"   • {table}: {count} records")
                
                # If any table is empty, add sample data
                if any(count == 0 for count in tables_data.values()):
                    print("⚠️ Some tables are empty, adding sample data...")
                    add_sample_data()
                else:
                    print("✅ All tables have data, database is consistent")
                    return
            else:
                print("📝 No existing data found, adding sample data...")
                add_sample_data()
            
            # Verify final state
            verify_database_sync()
            
            print(f"\n🎉 Database synchronization completed successfully for {env.upper()} environment!")
            print(f"📅 Synchronized at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error during synchronization: {e}")
            db.session.rollback()
            raise

def add_sample_data():
    """Add sample data to the database"""
    print("📝 Adding sample data...")
    
    # Create admin user
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
        print("✅ Admin user created")
    
    # Create faculty users
    faculty_users = [
        {
            'username': 'faculty',
            'email': 'faculty@institution.com',
            'password': 'faculty123',
            'role': 'faculty',
            'name': 'Dr. John Smith',
            'department': 'Computer Science',
            'phone': '+91-9876543211',
            'address': 'Computer Science Department, Room 201',
            'qualifications': 'PhD in Computer Science, 10 years experience'
        },
        {
            'username': 'faculty2',
            'email': 'faculty2@institution.com',
            'password': 'faculty123',
            'role': 'faculty',
            'name': 'Prof. Jane Doe',
            'department': 'Mathematics',
            'phone': '+91-9876543212',
            'address': 'Mathematics Department, Room 105',
            'qualifications': 'PhD in Mathematics, 8 years experience'
        }
    ]
    
    for faculty_data in faculty_users:
        faculty = User.query.filter_by(username=faculty_data['username']).first()
        if not faculty:
            faculty = User(
                username=faculty_data['username'],
                email=faculty_data['email'],
                password_hash=generate_password_hash(faculty_data['password']),
                role=faculty_data['role'],
                name=faculty_data['name'],
                department=faculty_data['department'],
                phone=faculty_data['phone'],
                address=faculty_data['address'],
                qualifications=faculty_data['qualifications']
            )
            db.session.add(faculty)
            print(f"✅ Faculty user {faculty_data['username']} created")
    
    # Create student groups
    groups_data = [
        ('CS-2024-1', 'Computer Science', 2024, 1),
        ('CS-2024-2', 'Computer Science', 2024, 2),
        ('MATH-2024-1', 'Mathematics', 2024, 1)
    ]
    
    for group_data in groups_data:
        group = StudentGroup.query.filter_by(name=group_data[0]).first()
        if not group:
            group = StudentGroup(
                name=group_data[0],
                department=group_data[1],
                year=group_data[2],
                semester=group_data[3]
            )
            db.session.add(group)
            print(f"✅ Student group {group_data[0]} created")
    
    # Create sample students
    students_data = [
        {
            'username': 'student',
            'email': 'student@institution.com',
            'password': 'student123',
            'role': 'student',
            'name': 'Alice Johnson',
            'department': 'Computer Science',
            'phone': '+91-9876543213',
            'address': 'Student Hostel Block A, Room 101',
            'qualifications': '12th Standard, Computer Science Stream'
        },
        {
            'username': 'student2',
            'email': 'student2@institution.com',
            'password': 'student123',
            'role': 'student',
            'name': 'Bob Wilson',
            'department': 'Computer Science',
            'phone': '+91-9876543214',
            'address': 'Student Hostel Block A, Room 102',
            'qualifications': '12th Standard, Computer Science Stream'
        }
    ]
    
    for student_data in students_data:
        student = User.query.filter_by(username=student_data['username']).first()
        if not student:
            # Get the first CS group for students
            cs_group = StudentGroup.query.filter_by(department='Computer Science').first()
            student = User(
                username=student_data['username'],
                email=student_data['email'],
                password_hash=generate_password_hash(student_data['password']),
                role=student_data['role'],
                name=student_data['name'],
                department=student_data['department'],
                group_id=cs_group.id if cs_group else None,
                phone=student_data['phone'],
                address=student_data['address'],
                qualifications=student_data['qualifications']
            )
            db.session.add(student)
            print(f"✅ Student user {student_data['username']} created")
    
    # Create sample courses
    courses_data = [
        {
            'code': 'CS101',
            'name': 'Introduction to Computer Science',
            'credits': 3,
            'department': 'Computer Science',
            'max_students': 50,
            'semester': '1',
            'description': 'Fundamental concepts of computer science and programming',
            'subject_area': 'Computer Science',
            'required_equipment': 'Projector, Whiteboard',
            'min_capacity': 1,
            'periods_per_week': 3
        },
        {
            'code': 'MATH101',
            'name': 'Calculus I',
            'credits': 4,
            'department': 'Mathematics',
            'max_students': 40,
            'semester': '1',
            'description': 'Introduction to differential and integral calculus',
            'subject_area': 'Mathematics',
            'required_equipment': 'Whiteboard, Calculator',
            'min_capacity': 1,
            'periods_per_week': 4
        }
    ]
    
    for course_data in courses_data:
        course = Course.query.filter_by(code=course_data['code']).first()
        if not course:
            course = Course(**course_data)
            db.session.add(course)
            print(f"✅ Course {course_data['code']} created")
    
    # Create sample classrooms
    classrooms_data = [
        {
            'room_number': '101',
            'capacity': 50,
            'building': 'Science Building',
            'room_type': 'lecture',
            'floor': 1,
            'status': 'active',
            'facilities': 'Projector, Whiteboard, Air Conditioning',
            'equipment': 'Projector, Whiteboard'
        },
        {
            'room_number': '205',
            'capacity': 40,
            'building': 'Mathematics Building',
            'room_type': 'seminar',
            'floor': 2,
            'status': 'active',
            'facilities': 'Smart Board, Computer, Whiteboard',
            'equipment': 'Smart Board, Computer'
        }
    ]
    
    for classroom_data in classrooms_data:
        classroom = Classroom.query.filter_by(room_number=classroom_data['room_number']).first()
        if not classroom:
            classroom = Classroom(**classroom_data)
            db.session.add(classroom)
            print(f"✅ Classroom {classroom_data['room_number']} created")
    
    # Create sample time slots
    time_slots_data = [
        ('Monday', '09:00', '10:00', 'none'),
        ('Monday', '10:00', '11:00', 'short'),
        ('Tuesday', '09:00', '10:00', 'none'),
        ('Tuesday', '10:00', '11:00', 'short'),
        ('Wednesday', '09:00', '10:00', 'none'),
        ('Wednesday', '10:00', '11:00', 'short'),
        ('Thursday', '09:00', '10:00', 'none'),
        ('Thursday', '10:00', '11:00', 'short'),
        ('Friday', '09:00', '10:00', 'none'),
        ('Friday', '10:00', '11:00', 'short')
    ]
    
    for slot_data in time_slots_data:
        existing_slot = TimeSlot.query.filter_by(
            day=slot_data[0], 
            start_time=slot_data[1], 
            end_time=slot_data[2]
        ).first()
        
        if not existing_slot:
            slot = TimeSlot(
                day=slot_data[0],
                start_time=slot_data[1],
                end_time=slot_data[2],
                break_type=slot_data[3]
            )
            db.session.add(slot)
            print(f"✅ Time slot {slot_data[0]} {slot_data[1]}-{slot_data[2]} created")
    
    # Commit all changes
    db.session.commit()
    print("✅ All sample data committed to database")

def verify_database_sync():
    """Verify that the database is properly synchronized"""
    print("\n🔍 Verifying database synchronization...")
    
    # Check table counts
    tables_data = {
        'Users': User.query.count(),
        'Courses': Course.query.count(),
        'Classrooms': Classroom.query.count(),
        'TimeSlots': TimeSlot.query.count(),
        'StudentGroups': StudentGroup.query.count(),
        'Timetables': Timetable.query.count(),
        'Attendance': Attendance.query.count(),
        'Notifications': Notification.query.count(),
        'CourseTeachers': CourseTeacher.query.count()
    }
    
    print("📊 Final database state:")
    for table, count in tables_data.items():
        print(f"   • {table}: {count} records")
    
    # Check specific data
    users = User.query.limit(5).all()
    print(f"\n👥 Sample users: {len(users)} found")
    for user in users:
        print(f"   • {user.username} ({user.role})")
    
    print("\n✅ Database synchronization verification completed")

def main():
    """Main function to run the synchronization"""
    try:
        sync_database()
    except Exception as e:
        print(f"❌ Synchronization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
