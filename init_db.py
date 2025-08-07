#!/usr/bin/env python3
"""
Database initialization script for Timetable & Attendance System
Creates sample data for testing and demonstration
"""

from app import app, db, User, Course, Classroom, TimeSlot, StudentGroup, StudentGroupCourse
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_sample_data():
    """Initialize the database with sample data"""
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        print("Creating sample users...")
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@institution.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            name='System Administrator',
            department='IT'
        )
        db.session.add(admin)
        
        # Create faculty users
        faculty1 = User(
            username='faculty',
            email='faculty@institution.com',
            password_hash=generate_password_hash('faculty123'),
            role='faculty',
            name='Dr. John Smith',
            department='Computer Science'
        )
        db.session.add(faculty1)
        
        faculty2 = User(
            username='prof_johnson',
            email='johnson@institution.com',
            password_hash=generate_password_hash('faculty123'),
            role='faculty',
            name='Prof. Sarah Johnson',
            department='Computer Science'
        )
        db.session.add(faculty2)
        
        # Create student users
        student1 = User(
            username='student',
            email='student@institution.com',
            password_hash=generate_password_hash('student123'),
            role='student',
            name='Alice Johnson',
            department='Computer Science'
        )
        db.session.add(student1)
        
        student2 = User(
            username='john_doe',
            email='john.doe@institution.com',
            password_hash=generate_password_hash('student123'),
            role='student',
            name='John Doe',
            department='Computer Science'
        )
        db.session.add(student2)
        
        student3 = User(
            username='jane_smith',
            email='jane.smith@institution.com',
            password_hash=generate_password_hash('student123'),
            role='student',
            name='Jane Smith',
            department='Computer Science'
        )
        db.session.add(student3)
        
        print("Creating sample courses...")
        
        # Create courses
        course1 = Course(
            code='CS101',
            name='Introduction to Computer Science',
            credits=3,
            department='Computer Science',
            teacher_id=2,  # faculty1
            max_students=50
        )
        db.session.add(course1)
        
        course2 = Course(
            code='CS201',
            name='Data Structures and Algorithms',
            credits=4,
            department='Computer Science',
            teacher_id=2,  # faculty1
            max_students=40
        )
        db.session.add(course2)
        
        course3 = Course(
            code='CS301',
            name='Database Management Systems',
            credits=3,
            department='Computer Science',
            teacher_id=3,  # faculty2
            max_students=35
        )
        db.session.add(course3)
        
        course4 = Course(
            code='CS401',
            name='Software Engineering',
            credits=4,
            department='Computer Science',
            teacher_id=3,  # faculty2
            max_students=30
        )
        db.session.add(course4)
        
        print("Creating sample classrooms...")
        
        # Create classrooms
        classroom1 = Classroom(
            room_number='101',
            capacity=50,
            building='Main Building',
            equipment='Projector, Whiteboard, Computer'
        )
        db.session.add(classroom1)
        
        classroom2 = Classroom(
            room_number='102',
            capacity=40,
            building='Main Building',
            equipment='Projector, Whiteboard'
        )
        db.session.add(classroom2)
        
        classroom3 = Classroom(
            room_number='201',
            capacity=35,
            building='Main Building',
            equipment='Projector, Whiteboard, Computer Lab'
        )
        db.session.add(classroom3)
        
        classroom4 = Classroom(
            room_number='202',
            capacity=30,
            building='Main Building',
            equipment='Projector, Whiteboard'
        )
        db.session.add(classroom4)
        
        print("Creating time slots...")
        
        # Create time slots
        time_slots = [
            TimeSlot(day='Monday', start_time='09:00', end_time='10:00'),
            TimeSlot(day='Monday', start_time='10:15', end_time='11:15'),
            TimeSlot(day='Monday', start_time='11:30', end_time='12:30'),
            TimeSlot(day='Monday', start_time='14:00', end_time='15:00'),
            TimeSlot(day='Monday', start_time='15:15', end_time='16:15'),
            
            TimeSlot(day='Tuesday', start_time='09:00', end_time='10:00'),
            TimeSlot(day='Tuesday', start_time='10:15', end_time='11:15'),
            TimeSlot(day='Tuesday', start_time='11:30', end_time='12:30'),
            TimeSlot(day='Tuesday', start_time='14:00', end_time='15:00'),
            TimeSlot(day='Tuesday', start_time='15:15', end_time='16:15'),
            
            TimeSlot(day='Wednesday', start_time='09:00', end_time='10:00'),
            TimeSlot(day='Wednesday', start_time='10:15', end_time='11:15'),
            TimeSlot(day='Wednesday', start_time='11:30', end_time='12:30'),
            TimeSlot(day='Wednesday', start_time='14:00', end_time='15:00'),
            TimeSlot(day='Wednesday', start_time='15:15', end_time='16:15'),
            
            TimeSlot(day='Thursday', start_time='09:00', end_time='10:00'),
            TimeSlot(day='Thursday', start_time='10:15', end_time='11:15'),
            TimeSlot(day='Thursday', start_time='11:30', end_time='12:30'),
            TimeSlot(day='Thursday', start_time='14:00', end_time='15:00'),
            TimeSlot(day='Thursday', start_time='15:15', end_time='16:15'),
            
            TimeSlot(day='Friday', start_time='09:00', end_time='10:00'),
            TimeSlot(day='Friday', start_time='10:15', end_time='11:15'),
            TimeSlot(day='Friday', start_time='11:30', end_time='12:30'),
            TimeSlot(day='Friday', start_time='14:00', end_time='15:00'),
            TimeSlot(day='Friday', start_time='15:15', end_time='16:15'),
        ]
        
        for slot in time_slots:
            db.session.add(slot)
        
        print("Creating student groups...")
        
        # Create student groups
        group1 = StudentGroup(
            name='CS2021',
            department='Computer Science',
            year=2021,
            semester=1
        )
        db.session.add(group1)
        
        group2 = StudentGroup(
            name='CS2022',
            department='Computer Science',
            year=2022,
            semester=1
        )
        db.session.add(group2)
        
        # Commit all changes
        db.session.commit()
        
        print("Creating student-group-course relationships...")
        
        # Create student-group-course relationships
        relationships = [
            StudentGroupCourse(student_group_id=1, course_id=1),
            StudentGroupCourse(student_group_id=1, course_id=2),
            StudentGroupCourse(student_group_id=1, course_id=3),
            StudentGroupCourse(student_group_id=1, course_id=4),
            StudentGroupCourse(student_group_id=2, course_id=1),
            StudentGroupCourse(student_group_id=2, course_id=2),
        ]
        
        for rel in relationships:
            db.session.add(rel)
        
        db.session.commit()
        
        print("Sample data created successfully!")
        print("\nDemo Accounts:")
        print("Admin: admin / admin123")
        print("Faculty: faculty / faculty123")
        print("Student: student / student123")

if __name__ == '__main__':
    init_sample_data() 