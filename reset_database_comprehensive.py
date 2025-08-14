
#!/usr/bin/env python3
"""
Comprehensive Database Reset Script
This script will completely reset the database and recreate all tables with the new schema
including student groups and periods_per_week for courses.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app import app, db, User, Course, CourseTeacher, Classroom, TimeSlot, Timetable, StudentGroup, StudentGroupCourse, Attendance, Notification
from werkzeug.security import generate_password_hash
from datetime import datetime

def reset_database():
    """Completely reset and recreate the database"""
    print("🔄 Starting comprehensive database reset...")
    
    with app.app_context():
        try:
            # Drop all tables
            print("🗑️  Dropping all existing tables...")
            db.drop_all()
            
            # Create all tables
            print("🏗️  Creating new tables...")
            db.create_all()
            
            print("✅ Database tables created successfully!")
            
            # Initialize with sample data
            print("📊 Initializing with sample data...")
            init_sample_data()
            
            print("🎉 Database reset completed successfully!")
            print("\n📋 Sample data created:")
            print("   - Admin user: admin/admin123")
            print("   - Faculty user: faculty1/faculty123")
            print("   - Student users: student1/student123, student2/student123")
            print("   - Student groups: CS-2024-1, CS-2024-2, MATH-2024-1")
            print("   - Courses: CS101, MATH101")
            print("   - Classrooms: Various types and capacities")
            
        except Exception as e:
            print(f"❌ Error during database reset: {str(e)}")
            return False
    
    return True

def init_sample_data():
    """Initialize database with comprehensive sample data"""
    
    # Create student groups first
    print("👥 Creating student groups...")
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
    
    # Create users
    print("👤 Creating users...")
    admin = User(
        username='admin',
        email='admin@institution.com',
        password_hash=generate_password_hash('admin123'),
        role='admin',
        name='System Administrator',
        department='Administration'
    )
    
    faculty1 = User(
        username='faculty1',
        email='faculty1@institution.com',
        password_hash=generate_password_hash('faculty123'),
        role='faculty',
        name='Dr. John Smith',
        department='Computer Science',
        phone='+1-555-0101',
        address='Faculty Building, Room 101',
        qualifications='PhD in Computer Science, 10 years teaching experience'
    )
    
    faculty2 = User(
        username='faculty2',
        email='faculty2@institution.com',
        password_hash=generate_password_hash('faculty123'),
        role='faculty',
        name='Dr. Sarah Johnson',
        department='Mathematics',
        phone='+1-555-0102',
        address='Faculty Building, Room 102',
        qualifications='PhD in Mathematics, 8 years teaching experience'
    )
    
    student1 = User(
        username='student1',
        email='student1@institution.com',
        password_hash=generate_password_hash('student123'),
        role='student',
        name='Alice Johnson',
        department='Computer Science',
        phone='+1-555-0201',
        address='Student Housing, Block A, Room 101',
        group_id=group1.id
    )
    
    student2 = User(
        username='student2',
        email='student2@institution.com',
        password_hash=generate_password_hash('student123'),
        role='student',
        name='Bob Wilson',
        department='Computer Science',
        phone='+1-555-0202',
        address='Student Housing, Block A, Room 102',
        group_id=group1.id
    )
    
    student3 = User(
        username='student3',
        email='student3@institution.com',
        password_hash=generate_password_hash('student123'),
        role='student',
        name='Charlie Brown',
        department='Mathematics',
        phone='+1-555-0203',
        address='Student Housing, Block B, Room 101',
        group_id=group3.id
    )
    
    db.session.add_all([admin, faculty1, faculty2, student1, student2, student3])
    db.session.commit()
    
    # Create courses
    print("📚 Creating courses...")
    course1 = Course(
        code='CS101',
        name='Introduction to Computer Science',
        credits=3,
        department='Computer Science',
        max_students=50,
        semester='1',
        description='Fundamental concepts of computer science and programming',
        subject_area='Computer Science',
        required_equipment='Computer lab with programming software',
        min_capacity=30,
        periods_per_week=3
    )
    
    course2 = Course(
        code='CS102',
        name='Programming Fundamentals',
        credits=4,
        department='Computer Science',
        max_students=40,
        semester='1',
        description='Introduction to programming concepts and problem solving',
        subject_area='Computer Science',
        required_equipment='Computer lab with Python/Java',
        min_capacity=25,
        periods_per_week=4
    )
    
    course3 = Course(
        code='MATH101',
        name='Calculus I',
        credits=4,
        department='Mathematics',
        max_students=40,
        semester='1',
        description='Introduction to differential and integral calculus',
        subject_area='Mathematics',
        required_equipment='Scientific calculators, whiteboard',
        min_capacity=20,
        periods_per_week=4
    )
    
    course4 = Course(
        code='MATH102',
        name='Linear Algebra',
        credits=3,
        department='Mathematics',
        max_students=35,
        semester='2',
        description='Study of vectors, matrices, and linear transformations',
        subject_area='Mathematics',
        required_equipment='Scientific calculators, whiteboard',
        min_capacity=20,
        periods_per_week=3
    )
    
    db.session.add_all([course1, course2, course3, course4])
    db.session.commit()
    
    # Create course-teacher assignments
    print("👨‍🏫 Assigning teachers to courses...")
    ct1 = CourseTeacher(
        course_id=course1.id,
        teacher_id=faculty1.id,
        is_primary=True
    )
    ct2 = CourseTeacher(
        course_id=course2.id,
        teacher_id=faculty1.id,
        is_primary=True
    )
    ct3 = CourseTeacher(
        course_id=course3.id,
        teacher_id=faculty2.id,
        is_primary=True
    )
    ct4 = CourseTeacher(
        course_id=course4.id,
        teacher_id=faculty2.id,
        is_primary=True
    )
    
    db.session.add_all([ct1, ct2, ct3, ct4])
    db.session.commit()
    
    # Create student group course assignments
    print("📖 Assigning courses to student groups...")
    sgc1 = StudentGroupCourse(
        student_group_id=group1.id,
        course_id=course1.id
    )
    sgc2 = StudentGroupCourse(
        student_group_id=group1.id,
        course_id=course2.id
    )
    sgc3 = StudentGroupCourse(
        student_group_id=group3.id,
        course_id=course3.id
    )
    
    db.session.add_all([sgc1, sgc2, sgc3])
    db.session.commit()
    
    # Create classrooms
    print("🏢 Creating classrooms...")
    classroom1 = Classroom(
        room_number='CS Lab 101',
        building='Computer Science Building',
        capacity=50,
        room_type='Computer Lab',
        floor=1,
        status='Available',
        facilities='Computers, Projector, Whiteboard',
        equipment='30 Computers, Projector, Whiteboard'
    )
    
    classroom2 = Classroom(
        room_number='Math 201',
        building='Mathematics Building',
        capacity=40,
        room_type='Lecture Hall',
        floor=2,
        status='Available',
        facilities='Projector, Whiteboard, Audio System',
        equipment='Projector, Whiteboard, Audio System'
    )
    
    classroom3 = Classroom(
        room_number='General 301',
        building='Main Building',
        capacity=60,
        room_type='Lecture Hall',
        floor=3,
        status='Available',
        facilities='Projector, Whiteboard, Audio System',
        equipment='Projector, Whiteboard, Audio System'
    )
    
    classroom4 = Classroom(
        room_number='Small Lab 102',
        building='Computer Science Building',
        capacity=25,
        room_type='Computer Lab',
        floor=1,
        status='Available',
        facilities='Computers, Whiteboard',
        equipment='25 Computers, Whiteboard'
    )
    
    db.session.add_all([classroom1, classroom2, classroom3, classroom4])
    db.session.commit()
    
    # Create time slots
    print("⏰ Creating time slots...")
    time_slots = []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    start_times = ['09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00']
    end_times = ['10:00', '11:00', '12:00', '13:00', '15:00', '16:00', '17:00']
    
    for day in days:
        for i, start_time in enumerate(start_times):
            time_slot = TimeSlot(
                day=day,
                start_time=start_time,
                end_time=end_times[i]
            )
            time_slots.append(time_slot)
    
    db.session.add_all(time_slots)
    db.session.commit()
    
    # Create sample timetables
    print("📅 Creating sample timetables...")
    group1 = StudentGroup.query.filter_by(name='CS-2024-1').first()
    group2 = StudentGroup.query.filter_by(name='MATH-2024-1').first()
    
    if group1:
        timetable1 = Timetable(
            course_id=course1.id,
            teacher_id=faculty1.id,
            classroom_id=classroom1.id,
            time_slot_id=time_slots[0].id,  # Monday 9:00-10:00
            student_group_id=group1.id,
            semester='Fall 2024',
            academic_year='2024-25'
        )
        
        timetable2 = Timetable(
            course_id=course2.id,
            teacher_id=faculty1.id,
            classroom_id=classroom4.id,
            time_slot_id=time_slots[8].id,  # Tuesday 10:00-11:00
            student_group_id=group1.id,
            semester='Fall 2024',
            academic_year='2024-25'
        )
    
    if group2:
        timetable3 = Timetable(
            course_id=course3.id,
            teacher_id=faculty2.id,
            classroom_id=classroom2.id,
            time_slot_id=time_slots[16].id,  # Wednesday 11:00-12:00
            student_group_id=group2.id,
            semester='Fall 2024',
            academic_year='2024-25'
        )
    
    # Add timetables conditionally
    timetables_to_add = []
    if group1:
        timetables_to_add.extend([timetable1, timetable2])
    if group2:
        timetables_to_add.append(timetable3)
    
    if timetables_to_add:
        db.session.add_all(timetables_to_add)
        db.session.commit()
    
    print("✅ Sample data initialization completed!")

if __name__ == '__main__':
    print("🚀 Timetable & Attendance System - Database Reset Tool")
    print("=" * 60)
    
    # Confirm before proceeding
    response = input("\n⚠️  This will DELETE ALL existing data and recreate the database. Continue? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        success = reset_database()
        if success:
            print("\n🎯 Next steps:")
            print("   1. Run the application: python app.py")
            print("   2. Login with admin/admin123")
            print("   3. Navigate to Student Groups to manage groups")
            print("   4. Assign courses to groups")
            print("   5. Create timetables for the groups")
        else:
            print("\n❌ Database reset failed. Check the error messages above.")
            sys.exit(1)
    else:
        print("\n❌ Database reset cancelled.")
        sys.exit(0)
