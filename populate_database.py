#!/usr/bin/env python3
"""
Database Population Script
Fills the database with sample data including:
- Indian names for students and teachers
- Engineering courses
- Student groups
- Time slots
- At least 30 periods, 3-4 student groups, 7-8 courses, ~200 students
"""

import sys
import os
from werkzeug.security import generate_password_hash
from app import (
    app,
    db,
    User,
    Course,
    StudentGroup,
    TimeSlot,
    Classroom,
    CourseTeacher,
    StudentGroupCourse,
    Timetable,
    Attendance,
    Notification,
)

# Indian names for students and teachers
INDIAN_NAMES = {
    'male': [
        'Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Reyansh', 'Aarush', 'Advait', 'Pranav', 'Shaurya',
        'Rohit', 'Rahul', 'Karan', 'Siddharth', 'Abhishek', 'Harsh', 'Manish', 'Nitin', 'Varun', 'Ankit'
    ],
    'female': [
        'Aanya', 'Pari', 'Diya', 'Myra', 'Sara', 'Ishita', 'Nisha', 'Kavya', 'Anika', 'Riya',
        'Pooja', 'Neha', 'Shruti', 'Priya', 'Aditi', 'Sakshi', 'Tanvi', 'Meera', 'Ananya', 'Simran'
    ],
    'surnames': [
        'Sharma', 'Verma', 'Patel', 'Kumar', 'Singh', 'Yadav', 'Gupta', 'Jain', 'Choudhary',
        'Malhotra', 'Reddy', 'Kapoor', 'Joshi', 'Chauhan', 'Mehta', 'Nair', 'Menon', 'Iyer',
        'Pillai', 'Nambiar', 'Krishnan', 'Venkatesh', 'Rao', 'Naidu', 'Gowda', 'Shetty',
        'Hegde', 'Bhat', 'Pandey', 'Tiwari', 'Mishra', 'Dubey', 'Trivedi', 'Shukla', 'Vishwakarma'
    ]
}

# Engineering courses with descriptions
ENGINEERING_COURSES = [
    {
        'code': 'CS101',
        'name': 'Introduction to Computer Science',
        'description': 'Fundamentals of computer science and programming',
        'credits': 3,
        'semester': '1',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 3
    },
    {
        'code': 'CS102',
        'name': 'Data Structures and Algorithms',
        'description': 'Core data structures and algorithmic concepts',
        'credits': 4,
        'semester': '2',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 4
    },
    {
        'code': 'CS201',
        'name': 'Object-Oriented Programming',
        'description': 'Advanced programming concepts and OOP principles',
        'credits': 4,
        'semester': '3',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector,computers',
        'min_capacity': 25,
        'periods_per_week': 4
    },
    {
        'code': 'CS202',
        'name': 'Database Management Systems',
        'description': 'Database design, SQL, and data modeling',
        'credits': 3,
        'semester': '4',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector,computers',
        'min_capacity': 25,
        'periods_per_week': 3
    },
    {
        'code': 'CS301',
        'name': 'Computer Networks',
        'description': 'Network protocols, architecture, and security',
        'credits': 4,
        'semester': '5',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 4
    },
    {
        'code': 'CS302',
        'name': 'Software Engineering',
        'description': 'Software development lifecycle and methodologies',
        'credits': 3,
        'semester': '6',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 3
    },
    {
        'code': 'CS401',
        'name': 'Artificial Intelligence',
        'description': 'AI fundamentals, machine learning, and neural networks',
        'credits': 4,
        'semester': '7',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector,computers',
        'min_capacity': 25,
        'periods_per_week': 4
    },
    {
        'code': 'CS402',
        'name': 'Computer Vision',
        'description': 'Image processing and computer vision algorithms',
        'credits': 3,
        'semester': '8',
        'department': 'Computer Science',
        'subject_area': 'Computer Science',
        'required_equipment': 'whiteboard,projector,computers',
        'min_capacity': 25,
        'periods_per_week': 3
    },
    {
        'code': 'EE101',
        'name': 'Electrical Engineering Fundamentals',
        'description': 'Basic electrical concepts and circuit analysis',
        'credits': 4,
        'semester': '1',
        'department': 'Electrical Engineering',
        'subject_area': 'Electrical Engineering',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 4
    },
    {
        'code': 'EE201',
        'name': 'Digital Electronics',
        'description': 'Digital logic design and electronic circuits',
        'credits': 4,
        'semester': '3',
        'department': 'Electrical Engineering',
        'subject_area': 'Electrical Engineering',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 4
    },
    {
        'code': 'ME101',
        'name': 'Mechanical Engineering Basics',
        'description': 'Mechanics, thermodynamics, and material science',
        'credits': 4,
        'semester': '1',
        'department': 'Mechanical Engineering',
        'subject_area': 'Mechanical Engineering',
        'required_equipment': 'whiteboard,projector',
        'min_capacity': 30,
        'periods_per_week': 4
    },
    {
        'code': 'ME201',
        'name': 'Machine Design',
        'description': 'Mechanical design principles and CAD',
        'credits': 4,
        'semester': '3',
        'department': 'Mechanical Engineering',
        'subject_area': 'Mechanical Engineering',
        'required_equipment': 'whiteboard,projector,computers',
        'min_capacity': 25,
        'periods_per_week': 4
    }
]

# Student groups
STUDENT_GROUPS = [
    {'name': 'Computer Science A', 'year': 1, 'semester': 1, 'capacity': 60, 'department': 'Computer Science'},
    {'name': 'Computer Science B', 'year': 1, 'semester': 1, 'capacity': 60, 'department': 'Computer Science'},
    {'name': 'Computer Science A', 'year': 2, 'semester': 3, 'capacity': 55, 'department': 'Computer Science'},
    {'name': 'Computer Science B', 'year': 2, 'semester': 3, 'capacity': 55, 'department': 'Computer Science'},
    {'name': 'Computer Science A', 'year': 3, 'semester': 5, 'capacity': 50, 'department': 'Computer Science'},
    {'name': 'Computer Science B', 'year': 3, 'semester': 5, 'capacity': 50, 'department': 'Computer Science'},
    {'name': 'Computer Science A', 'year': 4, 'semester': 7, 'capacity': 45, 'department': 'Computer Science'},
    {'name': 'Computer Science B', 'year': 4, 'semester': 7, 'capacity': 45, 'department': 'Computer Science'},
    {'name': 'Electrical Engineering A', 'year': 1, 'semester': 1, 'capacity': 50, 'department': 'Electrical Engineering'},
    {'name': 'Electrical Engineering B', 'year': 1, 'semester': 1, 'capacity': 50, 'department': 'Electrical Engineering'},
    {'name': 'Electrical Engineering A', 'year': 2, 'semester': 3, 'capacity': 45, 'department': 'Electrical Engineering'},
    {'name': 'Electrical Engineering B', 'year': 2, 'semester': 3, 'capacity': 45, 'department': 'Electrical Engineering'},
    {'name': 'Mechanical Engineering A', 'year': 1, 'semester': 1, 'capacity': 50, 'department': 'Mechanical Engineering'},
    {'name': 'Mechanical Engineering B', 'year': 1, 'semester': 1, 'capacity': 50, 'department': 'Mechanical Engineering'},
    {'name': 'Mechanical Engineering A', 'year': 2, 'semester': 3, 'capacity': 45, 'department': 'Mechanical Engineering'},
    {'name': 'Mechanical Engineering B', 'year': 2, 'semester': 3, 'capacity': 45, 'department': 'Mechanical Engineering'}
]

# Time slots for a week
TIME_SLOTS = [
    # Monday
    {'day': 'Monday', 'start_time': '08:00', 'end_time': '09:00'},
    {'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00'},
    {'day': 'Monday', 'start_time': '10:00', 'end_time': '11:00'},
    {'day': 'Monday', 'start_time': '11:00', 'end_time': '12:00'},
    {'day': 'Monday', 'start_time': '12:00', 'end_time': '13:00'},
    {'day': 'Monday', 'start_time': '14:00', 'end_time': '15:00'},
    {'day': 'Monday', 'start_time': '15:00', 'end_time': '16:00'},
    {'day': 'Monday', 'start_time': '16:00', 'end_time': '17:00'},
    
    # Tuesday
    {'day': 'Tuesday', 'start_time': '08:00', 'end_time': '09:00'},
    {'day': 'Tuesday', 'start_time': '09:00', 'end_time': '10:00'},
    {'day': 'Tuesday', 'start_time': '10:00', 'end_time': '11:00'},
    {'day': 'Tuesday', 'start_time': '11:00', 'end_time': '12:00'},
    {'day': 'Tuesday', 'start_time': '12:00', 'end_time': '13:00'},
    {'day': 'Tuesday', 'start_time': '14:00', 'end_time': '15:00'},
    {'day': 'Tuesday', 'start_time': '15:00', 'end_time': '16:00'},
    {'day': 'Tuesday', 'start_time': '16:00', 'end_time': '17:00'},
    
    # Wednesday
    {'day': 'Wednesday', 'start_time': '08:00', 'end_time': '09:00'},
    {'day': 'Wednesday', 'start_time': '09:00', 'end_time': '10:00'},
    {'day': 'Wednesday', 'start_time': '10:00', 'end_time': '11:00'},
    {'day': 'Wednesday', 'start_time': '11:00', 'end_time': '12:00'},
    {'day': 'Wednesday', 'start_time': '12:00', 'end_time': '13:00'},
    {'day': 'Wednesday', 'start_time': '14:00', 'end_time': '15:00'},
    {'day': 'Wednesday', 'start_time': '15:00', 'end_time': '16:00'},
    {'day': 'Wednesday', 'start_time': '16:00', 'end_time': '17:00'},
    
    # Thursday
    {'day': 'Thursday', 'start_time': '08:00', 'end_time': '09:00'},
    {'day': 'Thursday', 'start_time': '09:00', 'end_time': '10:00'},
    {'day': 'Thursday', 'start_time': '10:00', 'end_time': '11:00'},
    {'day': 'Thursday', 'start_time': '11:00', 'end_time': '12:00'},
    {'day': 'Thursday', 'start_time': '12:00', 'end_time': '13:00'},
    {'day': 'Thursday', 'start_time': '14:00', 'end_time': '15:00'},
    {'day': 'Thursday', 'start_time': '15:00', 'end_time': '16:00'},
    {'day': 'Thursday', 'start_time': '16:00', 'end_time': '17:00'},
    
    # Friday
    {'day': 'Friday', 'start_time': '08:00', 'end_time': '09:00'},
    {'day': 'Friday', 'start_time': '09:00', 'end_time': '10:00'},
    {'day': 'Friday', 'start_time': '10:00', 'end_time': '11:00'},
    {'day': 'Friday', 'start_time': '11:00', 'end_time': '12:00'},
    {'day': 'Friday', 'start_time': '12:00', 'end_time': '13:00'},
    {'day': 'Friday', 'start_time': '14:00', 'end_time': '15:00'},
    {'day': 'Friday', 'start_time': '15:00', 'end_time': '16:00'},
    {'day': 'Friday', 'start_time': '16:00', 'end_time': '17:00'}
]

# Classrooms with equipment
CLASSROOMS = [
    {'room_number': 'A101', 'capacity': 60, 'equipment': 'whiteboard,projector,ac', 'building': 'Block A', 'floor': 1},
    {'room_number': 'A102', 'capacity': 60, 'equipment': 'whiteboard,projector,ac', 'building': 'Block A', 'floor': 1},
    {'room_number': 'A103', 'capacity': 50, 'equipment': 'whiteboard,projector', 'building': 'Block A', 'floor': 1},
    {'room_number': 'A104', 'capacity': 50, 'equipment': 'whiteboard,projector', 'building': 'Block A', 'floor': 1},
    {'room_number': 'B101', 'capacity': 60, 'equipment': 'whiteboard,projector,ac', 'building': 'Block B', 'floor': 1},
    {'room_number': 'B102', 'capacity': 60, 'equipment': 'whiteboard,projector,ac', 'building': 'Block B', 'floor': 1},
    {'room_number': 'B103', 'capacity': 50, 'equipment': 'whiteboard,projector', 'building': 'Block B', 'floor': 1},
    {'room_number': 'B104', 'capacity': 50, 'equipment': 'whiteboard,projector', 'building': 'Block B', 'floor': 1},
    {'room_number': 'C101', 'capacity': 40, 'equipment': 'whiteboard,ac', 'building': 'Block C', 'floor': 1},
    {'room_number': 'C102', 'capacity': 40, 'equipment': 'whiteboard,ac', 'building': 'Block C', 'floor': 1},
    {'room_number': 'Lab1', 'capacity': 30, 'equipment': 'computers,projector,ac', 'building': 'Computer Lab', 'floor': 1},
    {'room_number': 'Lab2', 'capacity': 30, 'equipment': 'computers,projector,ac', 'building': 'Computer Lab', 'floor': 1},
    {'room_number': 'Lab3', 'capacity': 25, 'equipment': 'computers,projector', 'building': 'Computer Lab', 'floor': 1},
    {'room_number': 'Lab4', 'capacity': 25, 'equipment': 'computers,projector', 'building': 'Computer Lab', 'floor': 1}
]

def generate_indian_name(gender='male'):
    """Generate a random Indian name"""
    import random
    first_name = random.choice(INDIAN_NAMES[gender])
    surname = random.choice(INDIAN_NAMES['surnames'])
    return f"{first_name} {surname}"

def populate_database():
    """Populate the database with sample data"""
    print("Starting database population...")
    
    with app.app_context():
        # Clear existing data (delete dependent tables first)
        print("Clearing existing data...")
        db.session.query(Attendance).delete()
        db.session.query(Notification).delete()
        db.session.query(Timetable).delete()
        db.session.query(StudentGroupCourse).delete()
        db.session.query(CourseTeacher).delete()
        db.session.query(TimeSlot).delete()
        db.session.query(Classroom).delete()
        db.session.query(Course).delete()
        db.session.query(StudentGroup).delete()
        db.session.query(User).delete()
        
        # Create admin user
        print("Creating admin user...")
        admin = User(
            username='admin',
            email='admin@college.edu',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            name='Administrator'
        )
        db.session.add(admin)
        
        # Create faculty users (teachers)
        print("Creating faculty users...")
        faculty_users = []
        for i in range(20):  # 20 teachers
            gender = 'male' if i % 2 == 0 else 'female'
            faculty = User(
                username=f'faculty{i+1}',
                email=f'faculty{i+1}@college.edu',
                password_hash=generate_password_hash('faculty123'),
                role='faculty',
                name=generate_indian_name(gender)
            )
            faculty_users.append(faculty)
            db.session.add(faculty)
        
        # Create student users
        print("Creating student users...")
        student_users = []
        for i in range(200):  # 200 students
            gender = 'male' if i % 2 == 0 else 'female'
            student = User(
                username=f'student{i+1}',
                email=f'student{i+1}@college.edu',
                password_hash=generate_password_hash('student123'),
                role='student',
                name=generate_indian_name(gender)
            )
            student_users.append(student)
            db.session.add(student)
        
        # Create courses
        print("Creating courses...")
        courses = []
        for course_data in ENGINEERING_COURSES:
            course = Course(
                code=course_data['code'],
                name=course_data['name'],
                description=course_data['description'],
                credits=course_data['credits'],
                semester=course_data['semester'],
                department=course_data['department'],
                subject_area=course_data['subject_area'],
                required_equipment=course_data['required_equipment'],
                min_capacity=course_data['min_capacity'],
                periods_per_week=course_data['periods_per_week']
            )
            courses.append(course)
            db.session.add(course)
        
        # Create student groups
        print("Creating student groups...")
        student_groups = []
        for group_data in STUDENT_GROUPS:
            group = StudentGroup(
                name=group_data['name'],
                department=group_data['department'],
                year=group_data['year'],
                semester=group_data['semester']
            )
            student_groups.append(group)
            db.session.add(group)
        
        # Create classrooms
        print("Creating classrooms...")
        classrooms = []
        for room_data in CLASSROOMS:
            classroom = Classroom(
                room_number=room_data['room_number'],
                capacity=room_data['capacity'],
                equipment=room_data['equipment'],
                building=room_data['building'],
                floor=room_data['floor']
            )
            classrooms.append(classroom)
            db.session.add(classroom)
        
        # Create time slots
        print("Creating time slots...")
        time_slots = []
        for slot_data in TIME_SLOTS:
            time_slot = TimeSlot(
                day=slot_data['day'],
                start_time=slot_data['start_time'],
                end_time=slot_data['end_time']
            )
            time_slots.append(time_slot)
            db.session.add(time_slot)
        
        # Commit to get IDs
        db.session.commit()
        print("Basic data committed, creating relationships...")
        
        # Assign teachers to courses
        print("Assigning teachers to courses...")
        import random
        for course in courses:
            # Assign 1-2 teachers per course
            num_teachers = random.randint(1, 2)
            course_teachers = random.sample(faculty_users, num_teachers)
            
            for i, teacher in enumerate(course_teachers):
                course_teacher = CourseTeacher(
                    course_id=course.id,
                    teacher_id=teacher.id,
                    is_primary=(i == 0)  # First teacher is primary
                )
                db.session.add(course_teacher)
        
        # Assign students to groups (use correct FK field: group_id)
        print("Assigning students to groups...")
        students_per_group = len(student_users) // len(student_groups)
        for i, group in enumerate(student_groups):
            start_idx = i * students_per_group
            end_idx = start_idx + students_per_group if i < len(student_groups) - 1 else len(student_users)
            group_students = student_users[start_idx:end_idx]
            
            for student in group_students:
                student.group_id = group.id
        
        # Final commit
        db.session.commit()
        print("Database population completed successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("DATABASE POPULATION SUMMARY")
        print("="*50)
        print(f"Admin users: {db.session.query(User).filter_by(role='admin').count()}")
        print(f"Faculty users: {db.session.query(User).filter_by(role='faculty').count()}")
        print(f"Student users: {db.session.query(User).filter_by(role='student').count()}")
        print(f"Total users: {db.session.query(User).count()}")
        print(f"Courses: {db.session.query(Course).count()}")
        print(f"Student groups: {db.session.query(StudentGroup).count()}")
        print(f"Classrooms: {db.session.query(Classroom).count()}")
        print(f"Time slots: {db.session.query(TimeSlot).count()}")
        print(f"Course-teacher assignments: {db.session.query(CourseTeacher).count()}")
        print("="*50)
        
        # Show sample data
        print("\nSample data:")
        print("Sample course:", courses[0].name if courses else "None")
        print("Sample faculty:", faculty_users[0].name if faculty_users else "None")
        print("Sample student:", student_users[0].name if student_users else "None")
        print("Sample group:", student_groups[0].name if student_groups else "None")
        print("Sample classroom:", classrooms[0].room_number if classrooms else "None")
        print("Sample time slot:", f"{time_slots[0].day} {time_slots[0].start_time}-{time_slots[0].end_time}" if time_slots else "None")

if __name__ == '__main__':
    try:
        populate_database()
        print("\nDatabase population completed successfully!")
        print("You can now log in with:")
        print("Admin: username='admin', password='admin123'")
        print("Faculty: username='faculty1', password='faculty123'")
        print("Student: username='student1', password='student123'")
    except Exception as e:
        print(f"Error populating database: {e}")
        import traceback
        traceback.print_exc()