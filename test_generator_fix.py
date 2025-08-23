#!/usr/bin/env python3
"""
Test script to verify the fixed timetable generator works
"""

import os
import sys
from datetime import datetime, time
from sqlalchemy import create_engine, text
from timetable_generator import MultiGroupTimetableGenerator, TimeSlot, Course, Classroom, Teacher, StudentGroup

def test_generator():
    """Test the fixed timetable generator"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("🔍 Testing fixed timetable generator...")
            
            # Get sample data
            result = conn.execute(text("SELECT * FROM time_slot LIMIT 5"))
            time_slots_data = result.fetchall()
            
            result = conn.execute(text("SELECT * FROM course LIMIT 3"))
            courses_data = result.fetchall()
            
            result = conn.execute(text("SELECT * FROM classroom LIMIT 3"))
            classrooms_data = result.fetchall()
            
            result = conn.execute(text('SELECT * FROM "user" WHERE role = \'faculty\' LIMIT 3'))
            teachers_data = result.fetchall()
            
            result = conn.execute(text("SELECT * FROM student_group LIMIT 2"))
            groups_data = result.fetchall()
            
            print(f"   📊 Loaded: {len(time_slots_data)} time slots, {len(courses_data)} courses, {len(classrooms_data)} classrooms, {len(teachers_data)} teachers, {len(groups_data)} groups")
            
            # Convert to dataclass objects
            time_slots = [TimeSlot(
                id=ts.id, day=ts.day, start_time=ts.start_time, end_time=ts.end_time
            ) for ts in time_slots_data]
            
            courses = [Course(
                id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
                department=c.department, subject_area=c.subject_area,
                required_equipment=c.required_equipment or '',
                min_capacity=c.min_capacity, max_students=c.max_students
            ) for c in courses_data]
            
            classrooms = [Classroom(
                id=c.id, room_number=c.room_number, capacity=c.capacity,
                room_type=c.room_type, equipment=c.equipment or '', building=c.building
            ) for c in classrooms_data]
            
            teachers = [Teacher(
                id=t.id, name=t.name, department=t.department
            ) for t in teachers_data]
            
            student_groups = [StudentGroup(
                id=g.id, name=g.name, department=g.department,
                year=g.year, semester=g.semester
            ) for g in groups_data]
            
            # Test the generator
            generator = MultiGroupTimetableGenerator()
            generator.add_time_slots(time_slots)
            generator.add_courses(courses)
            generator.add_classrooms(classrooms)
            generator.add_teachers(teachers)
            generator.add_student_groups(student_groups)
            
            # Set group-course assignments (assign first 2 courses to first group, last course to second group)
            group_courses_mapping = {
                student_groups[0].id: courses[:2],
                student_groups[1].id: courses[2:]
            }
            generator.set_group_courses(group_courses_mapping)
            
            print(f"   🔧 Testing generator with:")
            print(f"      - Group {student_groups[0].name}: {len(group_courses_mapping[student_groups[0].id])} courses")
            print(f"      - Group {student_groups[1].name}: {len(group_courses_mapping[student_groups[1].id])} courses")
            
            # Try to generate timetables
            print(f"   🚀 Attempting timetable generation...")
            generated_timetables = generator.generate_timetables()
            
            if generated_timetables:
                print(f"   ✅ SUCCESS! Generated timetables for {len(generated_timetables)} groups")
                for group_id, entries in generated_timetables.items():
                    print(f"      👥 Group {group_id}: {len(entries)} classes scheduled")
                return True
            else:
                print(f"   ❌ FAILED! No timetables generated")
                return False
        
    except Exception as e:
        print(f"❌ Error testing generator: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Timetable Generator Fix Test")
    print("=" * 40)
    
    success = test_generator()
    
    if success:
        print("\n✅ Generator test passed!")
        print("The feasibility check should now work.")
    else:
        print("\n❌ Generator test failed!")
        print("There are still issues to fix.")
