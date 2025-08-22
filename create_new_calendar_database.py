#!/usr/bin/env python3
"""
Create New Calendar Database
Creates a new database with calendar-based schema from scratch.
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import app and models
from app import app, db, AcademicYear, AcademicSession, Holiday, ClassInstance, Timetable, Attendance, TimeSlot, User, Course, Classroom, StudentGroup

def create_new_calendar_database():
    """Create a new database with calendar-based schema"""
    print("🚀 Creating New Calendar Database")
    print("=" * 60)
    
    try:
        # Create application context
        ctx = app.app_context()
        ctx.push()
        
        try:
            # Drop all tables and recreate them
            print("📋 Dropping existing tables...")
            db.drop_all()
            print("✅ Dropped existing tables")
            
            # Create all tables with new schema
            print("📋 Creating new tables with calendar schema...")
            db.create_all()
            print("✅ Created new tables")
            
            # Create default academic year
            print("📅 Creating default academic year...")
            current_year = datetime.now().year
            academic_year = AcademicYear(
                name=f"{current_year}-{current_year + 1}",
                start_date=date(current_year, 9, 1),
                end_date=date(current_year + 1, 8, 31),
                is_active=True
            )
            db.session.add(academic_year)
            db.session.commit()
            print(f"✅ Created academic year: {academic_year.name}")
            
            # Create default sessions
            print("📚 Creating default academic sessions...")
            sessions_data = [
                {
                    'name': 'Fall Semester',
                    'start_date': date(current_year, 9, 1),
                    'end_date': date(current_year, 12, 20),
                    'session_type': 'semester'
                },
                {
                    'name': 'Spring Semester',
                    'start_date': date(current_year + 1, 1, 15),
                    'end_date': date(current_year + 1, 5, 15),
                    'session_type': 'semester'
                },
                {
                    'name': 'Summer Session',
                    'start_date': date(current_year + 1, 6, 1),
                    'end_date': date(current_year + 1, 8, 15),
                    'session_type': 'semester'
                }
            ]
            
            sessions = []
            for session_data in sessions_data:
                session = AcademicSession(
                    name=session_data['name'],
                    academic_year_id=academic_year.id,
                    start_date=session_data['start_date'],
                    end_date=session_data['end_date'],
                    session_type=session_data['session_type']
                )
                db.session.add(session)
                sessions.append(session)
            
            db.session.commit()
            print(f"✅ Created {len(sessions)} academic sessions")
            
            # Create default holidays
            print("🎉 Creating default holidays...")
            holidays_data = [
                {
                    'name': 'Labor Day',
                    'start_date': date(current_year, 9, 2),
                    'end_date': date(current_year, 9, 2),
                    'is_recurring': True,
                    'description': 'Labor Day Holiday'
                },
                {
                    'name': 'Thanksgiving Break',
                    'start_date': date(current_year, 11, 25),
                    'end_date': date(current_year, 11, 29),
                    'is_recurring': True,
                    'description': 'Thanksgiving Holiday Break'
                },
                {
                    'name': 'Christmas Break',
                    'start_date': date(current_year, 12, 23),
                    'end_date': date(current_year, 12, 31),
                    'is_recurring': True,
                    'description': 'Christmas and New Year Break'
                },
                {
                    'name': 'Martin Luther King Jr. Day',
                    'start_date': date(current_year + 1, 1, 20),
                    'end_date': date(current_year + 1, 1, 20),
                    'is_recurring': True,
                    'description': 'Martin Luther King Jr. Day'
                },
                {
                    'name': 'Spring Break',
                    'start_date': date(current_year + 1, 3, 10),
                    'end_date': date(current_year + 1, 3, 14),
                    'is_recurring': True,
                    'description': 'Spring Break'
                },
                {
                    'name': 'Easter Break',
                    'start_date': date(current_year + 1, 4, 5),
                    'end_date': date(current_year + 1, 4, 7),
                    'is_recurring': True,
                    'description': 'Easter Holiday'
                },
                {
                    'name': 'Memorial Day',
                    'start_date': date(current_year + 1, 5, 26),
                    'end_date': date(current_year + 1, 5, 26),
                    'is_recurring': True,
                    'description': 'Memorial Day'
                },
                {
                    'name': 'Independence Day',
                    'start_date': date(current_year + 1, 7, 4),
                    'end_date': date(current_year + 1, 7, 4),
                    'is_recurring': True,
                    'description': 'Independence Day'
                }
            ]
            
            for holiday_data in holidays_data:
                holiday = Holiday(
                    name=holiday_data['name'],
                    academic_year_id=academic_year.id,
                    start_date=holiday_data['start_date'],
                    end_date=holiday_data['end_date'],
                    is_recurring=holiday_data['is_recurring'],
                    description=holiday_data['description']
                )
                db.session.add(holiday)
            
            db.session.commit()
            print(f"✅ Created {len(holidays_data)} holidays")
            
            # Create sample data for testing
            print("📝 Creating sample data...")
            
            # Create sample time slots
            time_slots_data = [
                {'day': 'Monday', 'start_time': '09:00', 'end_time': '10:30'},
                {'day': 'Monday', 'start_time': '11:00', 'end_time': '12:30'},
                {'day': 'Tuesday', 'start_time': '09:00', 'end_time': '10:30'},
                {'day': 'Tuesday', 'start_time': '11:00', 'end_time': '12:30'},
                {'day': 'Wednesday', 'start_time': '09:00', 'end_time': '10:30'},
                {'day': 'Wednesday', 'start_time': '11:00', 'end_time': '12:30'},
                {'day': 'Thursday', 'start_time': '09:00', 'end_time': '10:30'},
                {'day': 'Thursday', 'start_time': '11:00', 'end_time': '12:30'},
                {'day': 'Friday', 'start_time': '09:00', 'end_time': '10:30'},
                {'day': 'Friday', 'start_time': '11:00', 'end_time': '12:30'},
            ]
            
            time_slots = []
            for slot_data in time_slots_data:
                time_slot = TimeSlot(
                    day=slot_data['day'],
                    start_time=slot_data['start_time'],
                    end_time=slot_data['end_time']
                )
                db.session.add(time_slot)
                time_slots.append(time_slot)
            
            db.session.commit()
            print(f"✅ Created {len(time_slots)} time slots")
            
            # Create sample courses
            courses_data = [
                {'code': 'CS101', 'name': 'Introduction to Computer Science', 'credits': 3, 'department': 'Computer Science', 'subject_area': 'Computer Science'},
                {'code': 'MATH101', 'name': 'Calculus I', 'credits': 4, 'department': 'Mathematics', 'subject_area': 'Mathematics'},
                {'code': 'ENG101', 'name': 'English Composition', 'credits': 3, 'department': 'English', 'subject_area': 'English'},
                {'code': 'PHYS101', 'name': 'Physics I', 'credits': 4, 'department': 'Physics', 'subject_area': 'Physics'},
            ]
            
            courses = []
            for course_data in courses_data:
                course = Course(
                    code=course_data['code'],
                    name=course_data['name'],
                    credits=course_data['credits'],
                    department=course_data['department'],
                    subject_area=course_data['subject_area'],
                    max_students=30
                )
                db.session.add(course)
                courses.append(course)
            
            db.session.commit()
            print(f"✅ Created {len(courses)} courses")
            
            # Create sample classrooms
            classrooms_data = [
                {'room_number': '101', 'building': 'Main Building', 'capacity': 30},
                {'room_number': '102', 'building': 'Main Building', 'capacity': 30},
                {'room_number': '201', 'building': 'Main Building', 'capacity': 30},
                {'room_number': '202', 'building': 'Main Building', 'capacity': 30},
            ]
            
            classrooms = []
            for classroom_data in classrooms_data:
                classroom = Classroom(
                    room_number=classroom_data['room_number'],
                    building=classroom_data['building'],
                    capacity=classroom_data['capacity']
                )
                db.session.add(classroom)
                classrooms.append(classroom)
            
            db.session.commit()
            print(f"✅ Created {len(classrooms)} classrooms")
            
            # Create sample student groups
            groups_data = [
                {'name': 'Computer Science Year 1', 'department': 'Computer Science', 'year': 1, 'semester': 1},
                {'name': 'Mathematics Year 1', 'department': 'Mathematics', 'year': 1, 'semester': 1},
            ]
            
            groups = []
            for group_data in groups_data:
                group = StudentGroup(
                    name=group_data['name'],
                    department=group_data['department'],
                    year=group_data['year'],
                    semester=group_data['semester']
                )
                db.session.add(group)
                groups.append(group)
            
            db.session.commit()
            print(f"✅ Created {len(groups)} student groups")
            
            # Create sample users
            users_data = [
                {'username': 'admin', 'email': 'admin@university.edu', 'name': 'System Administrator', 'role': 'admin'},
                {'username': 'faculty1', 'email': 'faculty1@university.edu', 'name': 'Dr. John Smith', 'role': 'faculty', 'department': 'Computer Science'},
                {'username': 'faculty2', 'email': 'faculty2@university.edu', 'name': 'Dr. Jane Doe', 'role': 'faculty', 'department': 'Mathematics'},
                {'username': 'student1', 'email': 'student1@university.edu', 'name': 'Alice Johnson', 'role': 'student', 'student_group_id': 1},
                {'username': 'student2', 'email': 'student2@university.edu', 'name': 'Bob Wilson', 'role': 'student', 'student_group_id': 1},
            ]
            
            from werkzeug.security import generate_password_hash
            
            users = []
            for user_data in users_data:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    name=user_data['name'],
                    role=user_data['role'],
                    password_hash=generate_password_hash('password123')
                )
                if 'department' in user_data:
                    user.department = user_data['department']
                if 'student_group_id' in user_data:
                    user.student_group_id = user_data['student_group_id']
                
                db.session.add(user)
                users.append(user)
            
            db.session.commit()
            print(f"✅ Created {len(users)} users")
            
            # Create sample timetables
            print("📅 Creating sample timetables...")
            fall_session = sessions[0]  # Fall semester
            
            timetables_data = [
                {'course_id': 1, 'teacher_id': 2, 'classroom_id': 1, 'time_slot_id': 1, 'student_group_id': 1},
                {'course_id': 2, 'teacher_id': 3, 'classroom_id': 2, 'time_slot_id': 3, 'student_group_id': 1},
                {'course_id': 3, 'teacher_id': 2, 'classroom_id': 3, 'time_slot_id': 5, 'student_group_id': 1},
            ]
            
            timetables = []
            for timetable_data in timetables_data:
                timetable = Timetable(
                    course_id=timetable_data['course_id'],
                    teacher_id=timetable_data['teacher_id'],
                    classroom_id=timetable_data['classroom_id'],
                    time_slot_id=timetable_data['time_slot_id'],
                    student_group_id=timetable_data['student_group_id'],
                    academic_year_id=academic_year.id,
                    session_id=fall_session.id
                )
                db.session.add(timetable)
                timetables.append(timetable)
            
            db.session.commit()
            print(f"✅ Created {len(timetables)} timetables")
            
            # Generate class instances for the fall semester
            print("📅 Generating class instances...")
            total_instances = 0
            
            for timetable in timetables:
                # Get the time slot to determine the day of week
                time_slot = TimeSlot.query.get(timetable.time_slot_id)
                if not time_slot:
                    continue
                
                # Map day names to weekday numbers (Monday=0, Sunday=6)
                day_mapping = {
                    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                    'Friday': 4, 'Saturday': 5, 'Sunday': 6
                }
                
                weekday = day_mapping.get(time_slot.day)
                if weekday is None:
                    continue
                
                # Generate class instances for each week in the session
                current_date = fall_session.start_date
                while current_date <= fall_session.end_date:
                    # Check if this date falls on the correct weekday
                    if current_date.weekday() == weekday:
                        # Check if this date is a holiday
                        holiday = Holiday.query.filter(
                            Holiday.academic_year_id == academic_year.id,
                            Holiday.start_date <= current_date,
                            Holiday.end_date >= current_date
                        ).first()
                        
                        if not holiday:
                            # Create class instance
                            class_instance = ClassInstance(
                                timetable_id=timetable.id,
                                class_date=current_date
                            )
                            db.session.add(class_instance)
                            total_instances += 1
                    
                    current_date += timedelta(days=1)
            
            db.session.commit()
            print(f"✅ Generated {total_instances} class instances")
            
            print("\n" + "=" * 60)
            print("🎉 New Calendar Database Created Successfully!")
            print("📊 Database Summary:")
            print(f"   • Academic Year: {academic_year.name}")
            print(f"   • Sessions: {len(sessions)}")
            print(f"   • Holidays: {len(holidays_data)}")
            print(f"   • Time Slots: {len(time_slots)}")
            print(f"   • Courses: {len(courses)}")
            print(f"   • Classrooms: {len(classrooms)}")
            print(f"   • Student Groups: {len(groups)}")
            print(f"   • Users: {len(users)}")
            print(f"   • Timetables: {len(timetables)}")
            print(f"   • Class Instances: {total_instances}")
            print("\n🚀 The calendar-based system is now ready!")
            print("\n📝 Default Login Credentials:")
            print("   • Admin: admin / password123")
            print("   • Faculty: faculty1 / password123")
            print("   • Student: student1 / password123")
            
        finally:
            ctx.pop()
            
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_new_calendar_database()
