#!/usr/bin/env python3
"""
Idempotent Demo Data Seeder

Seeds the database with a comprehensive demo dataset suitable for first deploys
on Render/GitHub Codespaces where shell access may be limited.

Safety:
- Idempotent: checks for existing records and skips duplicates
- Does NOT delete existing data
- Can be toggled via env var SEED_DEMO=1 and will safely no-op if already seeded
"""

from typing import Optional, Tuple
import os
from werkzeug.security import generate_password_hash

from app import app, db, User, Course, StudentGroup, TimeSlot, Classroom, CourseTeacher


def _get_or_create_user(username: str, defaults: dict) -> Tuple[User, bool]:
    user = User.query.filter_by(username=username).first()
    if user:
        return user, False
    user = User(username=username, **defaults)
    db.session.add(user)
    return user, True


def _get_or_create_course(code: str, defaults: dict) -> Tuple[Course, bool]:
    course = Course.query.filter_by(code=code).first()
    if course:
        return course, False
    course = Course(code=code, **defaults)
    db.session.add(course)
    return course, True


def _get_or_create_group(name: str, year: int, semester: int, defaults: dict) -> Tuple[StudentGroup, bool]:
    group = StudentGroup.query.filter_by(name=name, year=year, semester=semester).first()
    if group:
        return group, False
    group = StudentGroup(name=name, year=year, semester=semester, **defaults)
    db.session.add(group)
    return group, True


def _get_or_create_classroom(room_number: str, defaults: dict) -> Tuple[Classroom, bool]:
    room = Classroom.query.filter_by(room_number=room_number).first()
    if room:
        return room, False
    room = Classroom(room_number=room_number, **defaults)
    db.session.add(room)
    return room, True


def _get_or_create_timeslot(day: str, start_time: str, end_time: str) -> Tuple[TimeSlot, bool]:
    slot = TimeSlot.query.filter_by(day=day, start_time=start_time, end_time=end_time).first()
    if slot:
        return slot, False
    slot = TimeSlot(day=day, start_time=start_time, end_time=end_time)
    db.session.add(slot)
    return slot, True


INDIAN_MALE = [
    'Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Reyansh', 'Aarush', 'Advait', 'Pranav', 'Shaurya',
    'Rohit', 'Rahul', 'Karan', 'Siddharth', 'Abhishek', 'Harsh', 'Manish', 'Nitin', 'Varun', 'Ankit'
]
INDIAN_FEMALE = [
    'Aanya', 'Pari', 'Diya', 'Myra', 'Sara', 'Ishita', 'Nisha', 'Kavya', 'Anika', 'Riya',
    'Pooja', 'Neha', 'Shruti', 'Priya', 'Aditi', 'Sakshi', 'Tanvi', 'Meera', 'Ananya', 'Simran'
]
INDIAN_SURNAMES = [
    'Sharma', 'Verma', 'Patel', 'Kumar', 'Singh', 'Yadav', 'Gupta', 'Jain', 'Choudhary',
    'Malhotra', 'Reddy', 'Kapoor', 'Joshi', 'Chauhan', 'Mehta', 'Nair', 'Menon', 'Iyer',
    'Pillai', 'Nambiar', 'Krishnan', 'Venkatesh', 'Rao', 'Naidu', 'Gowda', 'Shetty',
    'Hegde', 'Bhat', 'Pandey', 'Tiwari', 'Mishra', 'Dubey', 'Trivedi', 'Shukla', 'Vishwakarma'
]


def _full_name(index: int) -> str:
    first = INDIAN_MALE[index % len(INDIAN_MALE)] if index % 2 == 0 else INDIAN_FEMALE[index % len(INDIAN_FEMALE)]
    last = INDIAN_SURNAMES[index % len(INDIAN_SURNAMES)]
    return f"{first} {last}"


COURSES = [
    # CS
    ('CS101', {
        'name': 'Introduction to Computer Science', 'credits': 3, 'department': 'Computer Science',
        'semester': '1', 'subject_area': 'Computer Science', 'description': 'Fundamentals of CS',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 3
    }),
    ('CS102', {
        'name': 'Data Structures and Algorithms', 'credits': 4, 'department': 'Computer Science',
        'semester': '2', 'subject_area': 'Computer Science', 'description': 'DSA core',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 4
    }),
    ('CS201', {
        'name': 'Object-Oriented Programming', 'credits': 4, 'department': 'Computer Science',
        'semester': '3', 'subject_area': 'Computer Science', 'description': 'OOP with projects',
        'required_equipment': 'whiteboard,projector,computers', 'min_capacity': 25, 'periods_per_week': 4
    }),
    ('CS202', {
        'name': 'Database Management Systems', 'credits': 3, 'department': 'Computer Science',
        'semester': '4', 'subject_area': 'Computer Science', 'description': 'DBMS & SQL',
        'required_equipment': 'whiteboard,projector,computers', 'min_capacity': 25, 'periods_per_week': 3
    }),
    ('CS301', {
        'name': 'Computer Networks', 'credits': 4, 'department': 'Computer Science',
        'semester': '5', 'subject_area': 'Computer Science', 'description': 'Networking',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 4
    }),
    ('CS302', {
        'name': 'Software Engineering', 'credits': 3, 'department': 'Computer Science',
        'semester': '6', 'subject_area': 'Computer Science', 'description': 'SDLC & methods',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 3
    }),
    ('CS401', {
        'name': 'Artificial Intelligence', 'credits': 4, 'department': 'Computer Science',
        'semester': '7', 'subject_area': 'Computer Science', 'description': 'AI & ML',
        'required_equipment': 'whiteboard,projector,computers', 'min_capacity': 25, 'periods_per_week': 4
    }),
    ('CS402', {
        'name': 'Computer Vision', 'credits': 3, 'department': 'Computer Science',
        'semester': '8', 'subject_area': 'Computer Science', 'description': 'Vision fundamentals',
        'required_equipment': 'whiteboard,projector,computers', 'min_capacity': 25, 'periods_per_week': 3
    }),
    # EE/ME
    ('EE101', {
        'name': 'Electrical Engineering Fundamentals', 'credits': 4, 'department': 'Electrical Engineering',
        'semester': '1', 'subject_area': 'Electrical Engineering', 'description': 'Basics & circuits',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 4
    }),
    ('EE201', {
        'name': 'Digital Electronics', 'credits': 4, 'department': 'Electrical Engineering',
        'semester': '3', 'subject_area': 'Electrical Engineering', 'description': 'Digital logic',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 4
    }),
    ('ME101', {
        'name': 'Mechanical Engineering Basics', 'credits': 4, 'department': 'Mechanical Engineering',
        'semester': '1', 'subject_area': 'Mechanical Engineering', 'description': 'Mechanics & thermo',
        'required_equipment': 'whiteboard,projector', 'min_capacity': 30, 'periods_per_week': 4
    }),
    ('ME201', {
        'name': 'Machine Design', 'credits': 4, 'department': 'Mechanical Engineering',
        'semester': '3', 'subject_area': 'Mechanical Engineering', 'description': 'Design & CAD',
        'required_equipment': 'whiteboard,projector,computers', 'min_capacity': 25, 'periods_per_week': 4
    }),
]


GROUPS = [
    ('Computer Science A', 'Computer Science', 1, 1),
    ('Computer Science B', 'Computer Science', 1, 1),
    ('Computer Science A', 'Computer Science', 2, 3),
    ('Computer Science B', 'Computer Science', 2, 3),
    ('Computer Science A', 'Computer Science', 3, 5),
    ('Computer Science B', 'Computer Science', 3, 5),
    ('Computer Science A', 'Computer Science', 4, 7),
    ('Computer Science B', 'Computer Science', 4, 7),
    ('Electrical Engineering A', 'Electrical Engineering', 1, 1),
    ('Electrical Engineering B', 'Electrical Engineering', 1, 1),
    ('Electrical Engineering A', 'Electrical Engineering', 2, 3),
    ('Electrical Engineering B', 'Electrical Engineering', 2, 3),
    ('Mechanical Engineering A', 'Mechanical Engineering', 1, 1),
    ('Mechanical Engineering B', 'Mechanical Engineering', 1, 1),
    ('Mechanical Engineering A', 'Mechanical Engineering', 2, 3),
    ('Mechanical Engineering B', 'Mechanical Engineering', 2, 3),
]


CLASSROOMS = [
    ('A101', 60, 'whiteboard,projector,ac', 'Block A', 1),
    ('A102', 60, 'whiteboard,projector,ac', 'Block A', 1),
    ('A103', 50, 'whiteboard,projector', 'Block A', 1),
    ('A104', 50, 'whiteboard,projector', 'Block A', 1),
    ('B101', 60, 'whiteboard,projector,ac', 'Block B', 1),
    ('B102', 60, 'whiteboard,projector,ac', 'Block B', 1),
    ('B103', 50, 'whiteboard,projector', 'Block B', 1),
    ('B104', 50, 'whiteboard,projector', 'Block B', 1),
    ('C101', 40, 'whiteboard,ac', 'Block C', 1),
    ('C102', 40, 'whiteboard,ac', 'Block C', 1),
    ('Lab1', 30, 'computers,projector,ac', 'Computer Lab', 1),
    ('Lab2', 30, 'computers,projector,ac', 'Computer Lab', 1),
    ('Lab3', 25, 'computers,projector', 'Computer Lab', 1),
    ('Lab4', 25, 'computers,projector', 'Computer Lab', 1),
]


def seed_demo_data() -> None:
    """Seed a comprehensive demo dataset if not already present."""
    with app.app_context():
        created_any = False

        # Ensure tables exist
        db.create_all()

        # Admin
        _, created = _get_or_create_user(
            'admin',
            {
                'email': 'admin@college.edu',
                'password_hash': generate_password_hash('admin123'),
                'role': 'admin',
                'name': 'Administrator',
            },
        )
        created_any = created_any or created

        # Faculty (target 20)
        faculty_targets = 20
        existing_faculty = User.query.filter_by(role='faculty').count()
        for i in range(existing_faculty, faculty_targets):
            username = f'faculty{i+1}'
            _, created = _get_or_create_user(
                username,
                {
                    'email': f'{username}@college.edu',
                    'password_hash': generate_password_hash('faculty123'),
                    'role': 'faculty',
                    'name': _full_name(i),
                },
            )
            created_any = created_any or created

        # Students (target 200)
        student_targets = 200
        existing_students = User.query.filter_by(role='student').count()
        for i in range(existing_students, student_targets):
            username = f'student{i+1}'
            _, created = _get_or_create_user(
                username,
                {
                    'email': f'{username}@college.edu',
                    'password_hash': generate_password_hash('student123'),
                    'role': 'student',
                    'name': _full_name(i),
                },
            )
            created_any = created_any or created

        # Courses
        for code, defaults in COURSES:
            _, created = _get_or_create_course(code, defaults)
            created_any = created_any or created

        # Groups
        for name, dept, year, sem in GROUPS:
            _, created = _get_or_create_group(name, year, sem, {'department': dept})
            created_any = created_any or created

        # Classrooms
        for room_number, capacity, equipment, building, floor in CLASSROOMS:
            _, created = _get_or_create_classroom(
                room_number,
                {
                    'capacity': capacity,
                    'equipment': equipment,
                    'building': building,
                    'floor': floor,
                },
            )
            created_any = created_any or created

        # Time slots (Mon-Fri, 8 slots/day)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        slots = ['08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '14:00-15:00', '15:00-16:00', '16:00-17:00']
        for day in days:
            for s in slots:
                start, end = s.split('-')
                _, created = _get_or_create_timeslot(day, start, end)
                created_any = created_any or created

        db.session.commit()

        # Assign teachers to courses (mark first as primary)
        import random
        faculty = User.query.filter_by(role='faculty').all()
        all_courses = Course.query.all()
        for course in all_courses:
            # Skip if already has a primary
            has_primary = CourseTeacher.query.filter_by(course_id=course.id, is_primary=True).first() is not None
            if has_primary:
                continue
            if len(faculty) == 0:
                break
            picks = random.sample(faculty, k=min(2, len(faculty)))
            for idx, teacher in enumerate(picks):
                exists = CourseTeacher.query.filter_by(course_id=course.id, teacher_id=teacher.id).first()
                if exists:
                    continue
                db.session.add(
                    CourseTeacher(course_id=course.id, teacher_id=teacher.id, is_primary=(idx == 0))
                )
                created_any = True

        db.session.commit()

        # Assign students evenly to groups if not already assigned
        groups = StudentGroup.query.all()
        students = User.query.filter_by(role='student').all()
        unassigned = [s for s in students if not getattr(s, 'group_id', None)]
        if groups and unassigned:
            per_group = max(1, len(unassigned) // len(groups))
            idx = 0
            for group in groups:
                for _ in range(per_group):
                    if idx >= len(unassigned):
                        break
                    unassigned[idx].group_id = group.id
                    idx += 1
            db.session.commit()

        # Log
        print("✅ Demo data seed completed (idempotent)")


if __name__ == '__main__':
    # Manual run (optional)
    seed_demo_data()

