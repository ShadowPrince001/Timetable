#!/usr/bin/env python3
"""
Debug script to test timetable generation
"""

from app import app, db
from app import TimeSlot, Classroom, User, Course, StudentGroup
from timetable_generator import MultiGroupTimetableGenerator, TimeSlot as GenTimeSlot, Course as GenCourse, Classroom as GenClassroom, StudentGroup as GenStudentGroup, Teacher

def debug_timetable_generation():
    with app.app_context():
        print("🔍 Debugging Timetable Generation")
        print("=" * 50)
        
        # Get all data
        time_slots = TimeSlot.query.all()
        classrooms = Classroom.query.all()
        teachers = User.query.filter_by(role='faculty').all()
        courses = Course.query.all()
        student_groups = StudentGroup.query.all()
        
        print(f"📊 Available Resources:")
        print(f"   Time Slots: {len(time_slots)}")
        print(f"   Classrooms: {len(classrooms)}")
        print(f"   Teachers: {len(teachers)}")
        print(f"   Courses: {len(courses)}")
        print(f"   Student Groups: {len(student_groups)}")
        
        # Show sample data
        print(f"\n📅 Sample Time Slots:")
        for i, slot in enumerate(time_slots[:5]):
            print(f"   {i+1}. {slot.day} {slot.start_time}-{slot.end_time}")
        
        print(f"\n🏫 Sample Classrooms:")
        for i, room in enumerate(classrooms):
            print(f"   {i+1}. {room.room_number} (Capacity: {room.capacity}, Equipment: {room.equipment})")
        
        print(f"\n👨‍🏫 Teachers:")
        for i, teacher in enumerate(teachers):
            print(f"   {i+1}. {teacher.name} (Department: {teacher.department})")
        
        print(f"\n📚 Courses:")
        for i, course in enumerate(courses):
            print(f"   {i+1}. {course.code} - {course.name} (Dept: {course.department}, Periods: {course.periods_per_week})")
        
        print(f"\n👥 Student Groups:")
        for i, group in enumerate(student_groups):
            print(f"   {i+1}. {group.name} (Dept: {group.department})")
        
        # Test generator
        print(f"\n🚀 Testing Timetable Generator")
        print("=" * 50)
        
        generator = MultiGroupTimetableGenerator()
        
        # Add time slots
        gen_time_slots = []
        for slot in time_slots:
            gen_slot = GenTimeSlot(
                id=slot.id, day=slot.day, start_time=slot.start_time, 
                end_time=slot.end_time, break_type=slot.break_type
            )
            gen_time_slots.append(gen_slot)
        generator.add_time_slots(gen_time_slots)
        
        # Add classrooms
        gen_classrooms = []
        for classroom in classrooms:
            gen_classroom = GenClassroom(
                id=classroom.id, room_number=classroom.room_number,
                capacity=classroom.capacity, building=classroom.building,
                room_type=classroom.room_type, equipment=classroom.equipment or ''
            )
            gen_classrooms.append(gen_classroom)
        generator.add_classrooms(gen_classrooms)
        
        # Add teachers
        gen_teachers = []
        for teacher in teachers:
            gen_teacher = Teacher(
                id=teacher.id, name=teacher.name, department=teacher.department
            )
            gen_teachers.append(gen_teacher)
        generator.add_teachers(gen_teachers)
        
        # Add courses
        gen_courses = []
        for course in courses:
            gen_course = GenCourse(
                id=course.id, code=course.code, name=course.name,
                periods_per_week=course.periods_per_week,
                department=course.department, subject_area=course.subject_area,
                required_equipment=course.required_equipment or '',
                min_capacity=course.min_capacity, max_students=course.max_students
            )
            gen_courses.append(gen_course)
        generator.add_courses(gen_courses)
        
        # Add student groups
        gen_student_groups = []
        for group in student_groups:
            gen_group = GenStudentGroup(
                id=group.id, name=group.name, department=group.department,
                year=group.year, semester=group.semester
            )
            gen_student_groups.append(gen_group)
        generator.add_student_groups(gen_student_groups)
        
        print(f"✅ Added to generator:")
        print(f"   Time Slots: {len(generator.time_slots)}")
        print(f"   Classrooms: {len(generator.classrooms)}")
        print(f"   Teachers: {len(generator.teachers)}")
        print(f"   Courses: {len(generator.courses)}")
        print(f"   Student Groups: {len(generator.student_groups)}")
        
        # Test resource finding for first course and group
        if courses and student_groups:
            first_course = generator.courses[0]
            first_group = generator.student_groups[0]
            
            print(f"\n🔍 Testing resource finding for {first_course.code} in {first_group.name}")
            
            # Test classroom finding
            suitable_classrooms = [
                c for c in generator.classrooms
                if c.capacity >= first_course.min_capacity and
                (not first_course.required_equipment or first_course.required_equipment in c.equipment)
            ]
            print(f"   Suitable classrooms: {len(suitable_classrooms)}")
            
            # Test teacher finding
            suitable_teachers = [
                t for t in generator.teachers
                if t.department == first_course.department
            ]
            print(f"   Suitable teachers: {len(suitable_teachers)}")
            
            # Test time slot finding
            print(f"   Available time slots: {len(generator.time_slots)}")
            
            # Test resource finding
            slot, classroom, teacher = generator._find_available_resources(
                first_course, first_group, set()
            )
            
            print(f"   Found slot: {slot is not None}")
            print(f"   Found classroom: {classroom is not None}")
            print(f"   Found teacher: {teacher is not None}")
            
            if slot:
                print(f"   Slot: {slot.day} {slot.start_time}-{slot.end_time}")
            if classroom:
                print(f"   Classroom: {classroom.room_number}")
            if teacher:
                print(f"   Teacher: {teacher.name}")

if __name__ == "__main__":
    debug_timetable_generation()
