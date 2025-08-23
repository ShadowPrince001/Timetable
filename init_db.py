#!/usr/bin/env python3
"""
Database initialization script for Timetable & Attendance System
Creates sample data for testing and demonstration with Indian names and engineering subjects
"""

from app import app, db, User, Course, Classroom, TimeSlot, StudentGroup, StudentGroupCourse, Timetable
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
            name='Dr. Rajesh Kumar',
            department='IT',
            phone='+91-9876543210',
            address='Admin Block, Room 101, Institution Campus',
            qualifications='Ph.D. in Information Technology',
            experience=15,
            bio='Senior Administrator with expertise in educational management',
            access_level='super_admin'
        )
        db.session.add(admin)
        
        # Create faculty users with Indian names
        faculty_users = [
            {
                'username': 'faculty',
                'email': 'faculty@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Dr. Priya Sharma',
                'department': 'Computer Science',
                'phone': '+91-9876543211',
                'address': 'CS Department, Room 201, Main Block',
                'qualifications': 'Ph.D. in Computer Science, M.Tech in Software Engineering',
                'experience': 8,
                'bio': 'Expert in Data Structures, Algorithms, and Software Engineering'
            },
            {
                'username': 'prof_verma',
                'email': 'verma@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Prof. Amit Verma',
                'department': 'Computer Science',
                'phone': '+91-9876543212',
                'address': 'CS Department, Room 202, Main Block',
                'qualifications': 'Ph.D. in Computer Science, M.Tech in Computer Networks',
                'experience': 12,
                'bio': 'Specialist in Computer Networks and Distributed Systems'
            },
            {
                'username': 'dr_patel',
                'email': 'patel@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Dr. Sneha Patel',
                'department': 'Electrical Engineering',
                'phone': '+91-9876543213',
                'address': 'EE Department, Room 301, Engineering Block',
                'qualifications': 'Ph.D. in Electrical Engineering, M.Tech in Power Systems',
                'experience': 10,
                'bio': 'Expert in Power Systems and Control Engineering'
            },
            {
                'username': 'prof_singh',
                'email': 'singh@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Prof. Harpreet Singh',
                'department': 'Mechanical Engineering',
                'phone': '+91-9876543214',
                'address': 'ME Department, Room 401, Engineering Block',
                'qualifications': 'Ph.D. in Mechanical Engineering, M.Tech in Machine Design',
                'experience': 14,
                'bio': 'Specialist in Machine Design and Manufacturing Processes'
            },
            {
                'username': 'dr_gupta',
                'email': 'gupta@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Dr. Anjali Gupta',
                'department': 'Civil Engineering',
                'phone': '+91-9876543215',
                'address': 'CE Department, Room 501, Engineering Block',
                'qualifications': 'Ph.D. in Civil Engineering, M.Tech in Structural Engineering',
                'experience': 11,
                'bio': 'Expert in Structural Analysis and Design'
            },
            {
                'username': 'prof_reddy',
                'email': 'reddy@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Prof. Karthik Reddy',
                'department': 'Information Technology',
                'phone': '+91-9876543216',
                'address': 'IT Department, Room 601, Main Block',
                'qualifications': 'Ph.D. in Information Technology, M.Tech in Web Technologies',
                'experience': 9,
                'bio': 'Specialist in Web Development and Mobile Applications'
            },
            {
                'username': 'dr_malhotra',
                'email': 'malhotra@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Dr. Ritu Malhotra',
                'department': 'Electronics & Communication',
                'phone': '+91-9876543217',
                'address': 'EC Department, Room 701, Engineering Block',
                'qualifications': 'Ph.D. in Electronics, M.Tech in Communication Systems',
                'experience': 13,
                'bio': 'Expert in Digital Communication and VLSI Design'
            },
            {
                'username': 'prof_khanna',
                'email': 'khanna@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Prof. Vikram Khanna',
                'department': 'Mathematics',
                'phone': '+91-9876543218',
                'address': 'Math Department, Room 801, Main Block',
                'qualifications': 'Ph.D. in Mathematics, M.Sc. in Applied Mathematics',
                'experience': 16,
                'bio': 'Specialist in Engineering Mathematics and Numerical Methods'
            },
            {
                'username': 'dr_iyer',
                'email': 'iyer@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Dr. Meera Iyer',
                'department': 'Physics',
                'phone': '+91-9876543219',
                'address': 'Physics Department, Room 901, Main Block',
                'qualifications': 'Ph.D. in Physics, M.Sc. in Applied Physics',
                'experience': 7,
                'bio': 'Expert in Engineering Physics and Applied Sciences'
            },
            {
                'username': 'prof_chopra',
                'email': 'chopra@institution.com',
                'password': 'faculty123',
                'role': 'faculty',
                'name': 'Prof. Arjun Chopra',
                'department': 'Chemistry',
                'phone': '+91-9876543220',
                'address': 'Chemistry Department, Room 1001, Main Block',
                'qualifications': 'Ph.D. in Chemistry, M.Sc. in Applied Chemistry',
                'experience': 6,
                'bio': 'Specialist in Engineering Chemistry and Materials Science'
            }
        ]
        
        for faculty_data in faculty_users:
            faculty = User(
                username=faculty_data['username'],
                email=faculty_data['email'],
                password_hash=generate_password_hash(faculty_data['password']),
                role=faculty_data['role'],
                name=faculty_data['name'],
                department=faculty_data['department'],
                phone=faculty_data['phone'],
                address=faculty_data['address'],
                qualifications=faculty_data['qualifications'],
                experience=faculty_data['experience'],
                bio=faculty_data['bio']
            )
            db.session.add(faculty)
        
        # Create student users with Indian names
        student_names = [
            'Arjun Singh', 'Priya Patel', 'Rahul Sharma', 'Anjali Verma', 'Vikram Kumar',
            'Meera Reddy', 'Karthik Gupta', 'Ritu Malhotra', 'Amit Khanna', 'Sneha Iyer',
            'Harpreet Chopra', 'Anjali Singh', 'Rajesh Patel', 'Priya Sharma', 'Amit Verma',
            'Sneha Kumar', 'Vikram Reddy', 'Meera Gupta', 'Karthik Malhotra', 'Ritu Khanna',
            'Harpreet Iyer', 'Anjali Chopra', 'Rajesh Singh', 'Priya Patel', 'Amit Sharma',
            'Sneha Verma', 'Vikram Kumar', 'Meera Reddy', 'Karthik Gupta', 'Ritu Malhotra'
        ]
        
        # Create the specific demo student account first
        demo_student = User(
            username='student',
            email='student@institution.com',
            password_hash=generate_password_hash('student123'),
            role='student',
            name='Arjun Sharma',
            department='Computer Science',
            phone='+91-9876543221',
            address='Student Hostel Block A, Room 101',
            bio='Third year Computer Science student interested in software development',
            group_id=1  # Assign to CS-3A group
        )
        db.session.add(demo_student)
        
        for i, name in enumerate(student_names):
            # Determine group_id based on department
            if i < 10:  # Computer Science students
                group_id = 1  # CS-3A
            elif i < 20:  # Electrical Engineering students
                group_id = 3  # EE-2A
            else:  # Mechanical Engineering students
                group_id = 4  # ME-2A
                
            student = User(
                username=f'student_{i+1}',
                email=f'student{i+1}@institution.com',
                password_hash=generate_password_hash('student123'),
                role='student',
                name=name,
                department='Computer Science' if i < 10 else 'Electrical Engineering' if i < 20 else 'Mechanical Engineering',
                phone=f'+91-9876543{221+i+1}',
                address=f'Student Hostel Block {"A" if i < 10 else "B" if i < 20 else "C"}, Room {101+i+1}',
                bio=f'Student in {name.split()[1]} department',
                group_id=group_id
            )
            db.session.add(student)
        
        print("Creating sample courses...")
        
        # Create engineering courses
        courses_data = [
            # Computer Science Courses
            {'code': 'CS101', 'name': 'Introduction to Computer Science', 'credits': 3, 'department': 'Computer Science', 'max_students': 60, 'subject_area': 'Programming', 'periods_per_week': 3},
            {'code': 'CS201', 'name': 'Data Structures and Algorithms', 'credits': 4, 'department': 'Computer Science', 'max_students': 50, 'subject_area': 'Programming', 'periods_per_week': 4},
            {'code': 'CS301', 'name': 'Database Management Systems', 'credits': 3, 'department': 'Computer Science', 'max_students': 45, 'subject_area': 'Database', 'periods_per_week': 3},
            {'code': 'CS401', 'name': 'Computer Networks', 'credits': 3, 'department': 'Computer Science', 'max_students': 40, 'subject_area': 'Networking', 'periods_per_week': 3},
            {'code': 'CS501', 'name': 'Software Engineering', 'credits': 4, 'department': 'Computer Science', 'max_students': 35, 'subject_area': 'Software Development', 'periods_per_week': 4},
            {'code': 'CS601', 'name': 'Artificial Intelligence', 'credits': 3, 'department': 'Computer Science', 'max_students': 30, 'subject_area': 'AI/ML', 'periods_per_week': 3},
            
            # Electrical Engineering Courses
            {'code': 'EE101', 'name': 'Basic Electrical Engineering', 'credits': 3, 'department': 'Electrical Engineering', 'max_students': 55, 'subject_area': 'Electrical Fundamentals', 'periods_per_week': 3},
            {'code': 'EE201', 'name': 'Digital Electronics', 'credits': 4, 'department': 'Electrical Engineering', 'max_students': 45, 'subject_area': 'Electronics', 'periods_per_week': 4},
            {'code': 'EE301', 'name': 'Power Systems', 'credits': 3, 'department': 'Electrical Engineering', 'max_students': 40, 'subject_area': 'Power Engineering', 'periods_per_week': 3},
            {'code': 'EE401', 'name': 'Control Systems', 'credits': 3, 'department': 'Electrical Engineering', 'max_students': 35, 'subject_area': 'Control Engineering', 'periods_per_week': 3},
            
            # Mechanical Engineering Courses
            {'code': 'ME101', 'name': 'Engineering Mechanics', 'credits': 3, 'department': 'Mechanical Engineering', 'max_students': 60, 'subject_area': 'Mechanics', 'periods_per_week': 3},
            {'code': 'ME201', 'name': 'Thermodynamics', 'credits': 4, 'department': 'Mechanical Engineering', 'max_students': 50, 'subject_area': 'Thermal Engineering', 'periods_per_week': 4},
            {'code': 'ME301', 'name': 'Machine Design', 'credits': 3, 'department': 'Mechanical Engineering', 'max_students': 45, 'subject_area': 'Design Engineering', 'periods_per_week': 3},
            {'code': 'ME401', 'name': 'Fluid Mechanics', 'credits': 3, 'department': 'Mechanical Engineering', 'max_students': 40, 'subject_area': 'Fluid Engineering', 'periods_per_week': 3},
            
            # Civil Engineering Courses
            {'code': 'CE101', 'name': 'Engineering Drawing', 'credits': 2, 'department': 'Civil Engineering', 'max_students': 50, 'subject_area': 'Technical Drawing', 'periods_per_week': 2},
            {'code': 'CE201', 'name': 'Structural Analysis', 'credits': 4, 'department': 'Civil Engineering', 'max_students': 45, 'subject_area': 'Structural Engineering', 'periods_per_week': 4},
            {'code': 'CE301', 'name': 'Concrete Technology', 'credits': 3, 'department': 'Civil Engineering', 'max_students': 40, 'subject_area': 'Construction Materials', 'periods_per_week': 3},
            {'code': 'CE401', 'name': 'Transportation Engineering', 'credits': 3, 'department': 'Civil Engineering', 'max_students': 35, 'subject_area': 'Transportation', 'periods_per_week': 3},
            
            # Information Technology Courses
            {'code': 'IT101', 'name': 'Programming Fundamentals', 'credits': 3, 'department': 'Information Technology', 'max_students': 55, 'subject_area': 'Programming', 'periods_per_week': 3},
            {'code': 'IT201', 'name': 'Web Development', 'credits': 4, 'department': 'Information Technology', 'max_students': 45, 'subject_area': 'Web Technologies', 'periods_per_week': 4},
            {'code': 'IT301', 'name': 'Mobile App Development', 'credits': 3, 'department': 'Information Technology', 'max_students': 40, 'subject_area': 'Mobile Development', 'periods_per_week': 3},
            
            # Electronics & Communication Courses
            {'code': 'EC101', 'name': 'Electronic Devices', 'credits': 3, 'department': 'Electronics & Communication', 'max_students': 50, 'subject_area': 'Electronics', 'periods_per_week': 3},
            {'code': 'EC201', 'name': 'Digital Communication', 'credits': 4, 'department': 'Electronics & Communication', 'max_students': 45, 'subject_area': 'Communication Systems', 'periods_per_week': 4},
            {'code': 'EC301', 'name': 'VLSI Design', 'credits': 3, 'department': 'Electronics & Communication', 'max_students': 35, 'subject_area': 'VLSI', 'periods_per_week': 3},
            
            # Mathematics Courses
            {'code': 'MA101', 'name': 'Engineering Mathematics I', 'credits': 3, 'department': 'Mathematics', 'max_students': 80, 'subject_area': 'Mathematics', 'periods_per_week': 3},
            {'code': 'MA201', 'name': 'Engineering Mathematics II', 'credits': 3, 'department': 'Mathematics', 'max_students': 75, 'subject_area': 'Mathematics', 'periods_per_week': 3},
            {'code': 'MA301', 'name': 'Linear Algebra', 'credits': 3, 'department': 'Mathematics', 'max_students': 60, 'subject_area': 'Mathematics', 'periods_per_week': 3},
            
            # Physics Courses
            {'code': 'PH101', 'name': 'Engineering Physics', 'credits': 3, 'department': 'Physics', 'max_students': 70, 'subject_area': 'Physics', 'periods_per_week': 3},
            {'code': 'PH201', 'name': 'Applied Physics', 'credits': 3, 'department': 'Physics', 'max_students': 65, 'subject_area': 'Physics', 'periods_per_week': 3},
            
            # Chemistry Courses
            {'code': 'CH101', 'name': 'Engineering Chemistry', 'credits': 3, 'department': 'Chemistry', 'max_students': 70, 'subject_area': 'Chemistry', 'periods_per_week': 3},
            {'code': 'CH201', 'name': 'Applied Chemistry', 'credits': 3, 'department': 'Chemistry', 'max_students': 65, 'subject_area': 'Chemistry', 'periods_per_week': 3}
        ]
        
        for course_data in courses_data:
            course = Course(**course_data)
            db.session.add(course)
        
        print("Creating sample classrooms...")
        
        # Create classrooms
        classrooms_data = [
            {'room_number': '101', 'capacity': 60, 'building': 'Main Block', 'equipment': 'Projector, Whiteboard, AC'},
            {'room_number': '102', 'capacity': 60, 'building': 'Main Block', 'equipment': 'Projector, Whiteboard, AC'},
            {'room_number': '201', 'capacity': 50, 'building': 'Main Block', 'equipment': 'Projector, Whiteboard'},
            {'room_number': '202', 'capacity': 50, 'building': 'Main Block', 'equipment': 'Projector, Whiteboard'},
            {'room_number': '301', 'capacity': 40, 'building': 'Main Block', 'equipment': 'Whiteboard, AC'},
            {'room_number': '302', 'capacity': 40, 'building': 'Main Block', 'equipment': 'Whiteboard, AC'},
            {'room_number': 'Lab-101', 'capacity': 30, 'building': 'Computer Center', 'equipment': 'Computers, Projector, AC'},
            {'room_number': 'Lab-102', 'capacity': 30, 'building': 'Computer Center', 'equipment': 'Computers, Projector, AC'},
            {'room_number': 'Lab-201', 'capacity': 25, 'building': 'Laboratory Block', 'equipment': 'Lab Equipment, Whiteboard'},
            {'room_number': 'Lab-202', 'capacity': 25, 'building': 'Laboratory Block', 'equipment': 'Lab Equipment, Whiteboard'},
            {'room_number': 'A101', 'capacity': 80, 'building': 'Auditorium', 'equipment': 'Projector, Sound System, AC'},
            {'room_number': 'A102', 'capacity': 60, 'building': 'Auditorium', 'equipment': 'Projector, Whiteboard, AC'},
            {'room_number': 'T101', 'capacity': 35, 'building': 'Engineering Block', 'equipment': 'Whiteboard, AC'},
            {'room_number': 'T102', 'capacity': 35, 'building': 'Engineering Block', 'equipment': 'Whiteboard, AC'},
            {'room_number': 'T201', 'capacity': 35, 'building': 'Engineering Block', 'equipment': 'Whiteboard, AC'},
            {'room_number': 'T202', 'capacity': 35, 'building': 'Engineering Block', 'equipment': 'Whiteboard, AC'}
        ]
        
        for classroom_data in classrooms_data:
            classroom = Classroom(**classroom_data)
            db.session.add(classroom)
        
        print("Creating time slots for 5-day week with 6 periods each...")
        
        # Create time slots for 5 days (Monday to Friday) with 6 periods each
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_slots_data = [
            # Monday
            {'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00', 'break_type': 'none'},
            {'day': 'Monday', 'start_time': '10:00', 'end_time': '11:00', 'break_type': 'none'},
            {'day': 'Monday', 'start_time': '11:15', 'end_time': '12:15', 'break_type': 'Break'},
            {'day': 'Monday', 'start_time': '12:15', 'end_time': '13:15', 'break_type': 'none'},
            {'day': 'Monday', 'start_time': '14:00', 'end_time': '15:00', 'break_type': 'none'},
            {'day': 'Monday', 'start_time': '15:00', 'end_time': '16:00', 'break_type': 'none'},
            
            # Tuesday
            {'day': 'Tuesday', 'start_time': '09:00', 'end_time': '10:00', 'break_type': 'none'},
            {'day': 'Tuesday', 'start_time': '10:00', 'end_time': '11:00', 'break_type': 'none'},
            {'day': 'Tuesday', 'start_time': '11:15', 'end_time': '12:15', 'break_type': 'Break'},
            {'day': 'Tuesday', 'start_time': '12:15', 'end_time': '13:15', 'break_type': 'none'},
            {'day': 'Tuesday', 'start_time': '14:00', 'end_time': '15:00', 'break_type': 'none'},
            {'day': 'Tuesday', 'start_time': '15:00', 'end_time': '16:00', 'break_type': 'none'},
            
            # Wednesday
            {'day': 'Wednesday', 'start_time': '09:00', 'end_time': '10:00', 'break_type': 'none'},
            {'day': 'Wednesday', 'start_time': '10:00', 'end_time': '11:00', 'break_type': 'none'},
            {'day': 'Wednesday', 'start_time': '11:15', 'end_time': '12:15', 'break_type': 'Break'},
            {'day': 'Wednesday', 'start_time': '12:15', 'end_time': '13:15', 'break_type': 'none'},
            {'day': 'Wednesday', 'start_time': '14:00', 'end_time': '15:00', 'break_type': 'none'},
            {'day': 'Wednesday', 'start_time': '15:00', 'end_time': '16:00', 'break_type': 'none'},
            
            # Thursday
            {'day': 'Thursday', 'start_time': '09:00', 'end_time': '10:00', 'break_type': 'none'},
            {'day': 'Thursday', 'start_time': '10:00', 'end_time': '11:00', 'break_type': 'none'},
            {'day': 'Thursday', 'start_time': '11:15', 'end_time': '12:15', 'break_type': 'Break'},
            {'day': 'Thursday', 'start_time': '12:15', 'end_time': '13:15', 'break_type': 'none'},
            {'day': 'Thursday', 'start_time': '14:00', 'end_time': '15:00', 'break_type': 'none'},
            {'day': 'Thursday', 'start_time': '15:00', 'end_time': '16:00', 'break_type': 'none'},
            
            # Friday
            {'day': 'Friday', 'start_time': '09:00', 'end_time': '10:00', 'break_type': 'none'},
            {'day': 'Friday', 'start_time': '10:00', 'end_time': '11:00', 'break_type': 'none'},
            {'day': 'Friday', 'start_time': '11:15', 'end_time': '12:15', 'break_type': 'Break'},
            {'day': 'Friday', 'start_time': '12:15', 'end_time': '13:15', 'break_type': 'none'},
            {'day': 'Friday', 'start_time': '14:00', 'end_time': '15:00', 'break_type': 'none'},
            {'day': 'Friday', 'start_time': '15:00', 'end_time': '16:00', 'break_type': 'none'}
        ]
        
        for time_slot_data in time_slots_data:
            time_slot = TimeSlot(**time_slot_data)
            db.session.add(time_slot)
        
        print("Creating student groups...")
        
        # Create student groups
        student_groups_data = [
            {'name': 'CS-3A', 'department': 'Computer Science', 'year': 3, 'semester': 5},
            {'name': 'CS-3B', 'department': 'Computer Science', 'year': 3, 'semester': 5},
            {'name': 'EE-2A', 'department': 'Electrical Engineering', 'year': 2, 'semester': 3},
            {'name': 'ME-2A', 'department': 'Mechanical Engineering', 'year': 2, 'semester': 3},
            {'name': 'CE-2A', 'department': 'Civil Engineering', 'year': 2, 'semester': 3},
            {'name': 'IT-2A', 'department': 'Information Technology', 'year': 2, 'semester': 3},
            {'name': 'EC-2A', 'department': 'Electronics & Communication', 'year': 2, 'semester': 3}
        ]
        
        for group_data in student_groups_data:
            group = StudentGroup(**group_data)
            db.session.add(group)
        
        db.session.commit()
        
        print("Creating sample timetable...")
        
        # Create a sample timetable for the week
        # This will create a realistic timetable with proper distribution
        timetable_data = [
            # Monday
            {'course_id': 1, 'classroom_id': 1, 'time_slot_id': 1, 'teacher_id': 2, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 7, 'classroom_id': 2, 'time_slot_id': 2, 'teacher_id': 4, 'student_group_id': 3, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 11, 'classroom_id': 3, 'time_slot_id': 3, 'teacher_id': 5, 'student_group_id': 4, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 15, 'classroom_id': 4, 'time_slot_id': 4, 'teacher_id': 6, 'student_group_id': 5, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 19, 'classroom_id': 5, 'time_slot_id': 5, 'teacher_id': 7, 'student_group_id': 6, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 22, 'classroom_id': 6, 'time_slot_id': 6, 'teacher_id': 8, 'student_group_id': 7, 'semester': '3', 'academic_year': '2024-25'},
            
            # Tuesday
            {'course_id': 2, 'classroom_id': 1, 'time_slot_id': 7, 'teacher_id': 2, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 8, 'classroom_id': 2, 'time_slot_id': 8, 'teacher_id': 4, 'student_group_id': 3, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 12, 'classroom_id': 3, 'time_slot_id': 9, 'teacher_id': 5, 'student_group_id': 4, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 16, 'classroom_id': 4, 'time_slot_id': 10, 'teacher_id': 6, 'student_group_id': 5, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 20, 'classroom_id': 5, 'time_slot_id': 11, 'teacher_id': 7, 'student_group_id': 6, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 23, 'classroom_id': 6, 'time_slot_id': 12, 'teacher_id': 8, 'student_group_id': 7, 'semester': '3', 'academic_year': '2024-25'},
            
            # Wednesday
            {'course_id': 3, 'classroom_id': 1, 'time_slot_id': 13, 'teacher_id': 3, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 9, 'classroom_id': 2, 'time_slot_id': 14, 'teacher_id': 4, 'student_group_id': 3, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 13, 'classroom_id': 3, 'time_slot_id': 15, 'teacher_id': 5, 'student_group_id': 4, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 17, 'classroom_id': 4, 'time_slot_id': 16, 'teacher_id': 6, 'student_group_id': 5, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 21, 'classroom_id': 5, 'time_slot_id': 17, 'teacher_id': 7, 'student_group_id': 6, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 24, 'classroom_id': 6, 'time_slot_id': 18, 'teacher_id': 8, 'student_group_id': 7, 'semester': '3', 'academic_year': '2024-25'},
            
            # Thursday
            {'course_id': 4, 'classroom_id': 1, 'time_slot_id': 19, 'teacher_id': 2, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 10, 'classroom_id': 2, 'time_slot_id': 20, 'teacher_id': 4, 'student_group_id': 3, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 14, 'classroom_id': 3, 'time_slot_id': 21, 'teacher_id': 5, 'student_group_id': 4, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 18, 'classroom_id': 4, 'time_slot_id': 22, 'teacher_id': 6, 'student_group_id': 5, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 25, 'classroom_id': 5, 'time_slot_id': 23, 'teacher_id': 9, 'student_group_id': 1, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 26, 'classroom_id': 6, 'time_slot_id': 24, 'teacher_id': 10, 'student_group_id': 3, 'semester': '3', 'academic_year': '2024-25'},
            
            # Friday
            {'course_id': 5, 'classroom_id': 1, 'time_slot_id': 25, 'teacher_id': 3, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 6, 'classroom_id': 2, 'time_slot_id': 26, 'teacher_id': 2, 'student_group_id': 1, 'semester': '5', 'academic_year': '2024-25'},
            {'course_id': 27, 'classroom_id': 3, 'time_slot_id': 27, 'teacher_id': 9, 'student_group_id': 4, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 28, 'classroom_id': 4, 'time_slot_id': 28, 'teacher_id': 10, 'student_group_id': 5, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 29, 'classroom_id': 5, 'time_slot_id': 29, 'teacher_id': 11, 'student_group_id': 6, 'semester': '3', 'academic_year': '2024-25'},
            {'course_id': 30, 'classroom_id': 6, 'time_slot_id': 30, 'teacher_id': 11, 'student_group_id': 7, 'semester': '3', 'academic_year': '2024-25'}
        ]
        
        for timetable_data_item in timetable_data:
            timetable = Timetable(**timetable_data_item)
            db.session.add(timetable)
        
        # Create student group course associations
        print("Creating student group course associations...")
        
        # Associate courses with student groups
        group_course_data = [
            # CS-3A group courses
            {'student_group_id': 1, 'course_id': 1},  # CS101
            {'student_group_id': 1, 'course_id': 2},  # CS201
            {'student_group_id': 1, 'course_id': 3},  # CS301
            {'student_group_id': 1, 'course_id': 4},  # CS401
            {'student_group_id': 1, 'course_id': 5},  # CS501
            {'student_group_id': 1, 'course_id': 6},  # CS601
            
            # EE-2A group courses
            {'student_group_id': 3, 'course_id': 7},  # EE101
            {'student_group_id': 3, 'course_id': 8},  # EE201
            {'student_group_id': 3, 'course_id': 9},  # EE301
            {'student_group_id': 3, 'course_id': 10}, # EE401
            
            # ME-2A group courses
            {'student_group_id': 4, 'course_id': 11}, # ME101
            {'student_group_id': 4, 'course_id': 12}, # ME201
            {'student_group_id': 4, 'course_id': 13}, # ME301
            {'student_group_id': 4, 'course_id': 14}, # ME401
            
            # CE-2A group courses
            {'student_group_id': 5, 'course_id': 15}, # CE101
            {'student_group_id': 5, 'course_id': 16}, # CE201
            {'student_group_id': 5, 'course_id': 17}, # CE301
            {'student_group_id': 5, 'course_id': 18}, # CE401
            
            # IT-2A group courses
            {'student_group_id': 6, 'course_id': 19}, # IT101
            {'student_group_id': 6, 'course_id': 20}, # IT201
            {'student_group_id': 6, 'course_id': 21}, # IT301
            
            # EC-2A group courses
            {'student_group_id': 7, 'course_id': 22}, # EC101
            {'student_group_id': 7, 'course_id': 23}, # EC201
            {'student_group_id': 7, 'course_id': 24}, # EC301
            
            # Common courses for all groups
            {'student_group_id': 1, 'course_id': 25}, # MA101
            {'student_group_id': 3, 'course_id': 25}, # MA101
            {'student_group_id': 4, 'course_id': 25}, # MA101
            {'student_group_id': 5, 'course_id': 25}, # MA101
            {'student_group_id': 6, 'course_id': 25}, # MA101
            {'student_group_id': 7, 'course_id': 25}, # MA101
            
            {'student_group_id': 1, 'course_id': 26}, # PH101
            {'student_group_id': 3, 'course_id': 26}, # PH101
            {'student_group_id': 4, 'course_id': 26}, # PH101
            {'student_group_id': 5, 'course_id': 26}, # PH101
            {'student_group_id': 6, 'course_id': 26}, # PH101
            {'student_group_id': 7, 'course_id': 26}, # PH101
            
            {'student_group_id': 1, 'course_id': 27}, # CH101
            {'student_group_id': 3, 'course_id': 27}, # CH101
            {'student_group_id': 4, 'course_id': 27}, # CH101
            {'student_group_id': 5, 'course_id': 27}, # CH101
            {'student_group_id': 6, 'course_id': 27}, # CH101
            {'student_group_id': 7, 'course_id': 27}, # CH101
        ]
        
        for group_course_item in group_course_data:
            group_course = StudentGroupCourse(**group_course_item)
            db.session.add(group_course)
        
        db.session.commit()
        
        print("Database initialization completed successfully!")
        print(f"Created {len(faculty_users)} faculty members")
        print(f"Created {len(student_names)} students")
        print(f"Created {len(courses_data)} courses")
        print(f"Created {len(classrooms_data)} classrooms")
        print(f"Created {len(time_slots_data)} time slots")
        print(f"Created {len(student_groups_data)} student groups")
        print(f"Created {len(timetable_data)} timetable entries")
        print(f"Created {len(group_course_data)} student group course associations")

if __name__ == '__main__':
    init_sample_data() 