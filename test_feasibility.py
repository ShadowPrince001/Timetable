#!/usr/bin/env python3
"""
Test script to check timetable feasibility without Flask context
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def check_timetable_feasibility():
    """Check if timetable generation is feasible with current constraints"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine and session
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("🔍 DEBUG: Starting timetable feasibility check...")
        
        # Get all required data
        courses = session.execute(text("SELECT * FROM course")).fetchall()
        classrooms = session.execute(text("SELECT * FROM classroom")).fetchall()
        teachers = session.execute(text('SELECT * FROM "user" WHERE role = \'faculty\'')).fetchall()
        student_groups = session.execute(text("SELECT * FROM student_group")).fetchall()
        time_slots = session.execute(text("SELECT * FROM time_slot")).fetchall()
        
        # Check basic resource availability
        print(f"🔍 DEBUG: Checking basic resources...")
        print(f"   📚 Courses: {len(courses)}")
        print(f"   🏫 Classrooms: {len(classrooms)}")
        print(f"   👨‍🏫 Teachers: {len(teachers)}")
        print(f"   👥 Student Groups: {len(student_groups)}")
        print(f"   ⏰ Time Slots: {len(time_slots)}")
        
        if not courses:
            print(f"❌ DEBUG: No courses available")
            return False
        
        if not classrooms:
            print(f"❌ DEBUG: No classrooms available")
            return False
        
        if not teachers:
            print(f"❌ DEBUG: No teachers available")
            return False
        
        if not student_groups:
            print(f"❌ DEBUG: No student groups available")
            return False
        
        if not time_slots:
            print(f"❌ DEBUG: No time slots available")
            return False
        
        # Check course assignments for each group
        print(f"🔍 DEBUG: Checking course assignments for each group...")
        total_required_periods = 0
        
        for group in student_groups:
            # Get courses assigned to this group
            group_courses = session.execute(text(
                "SELECT c.* FROM course c JOIN student_group_course sgc ON c.id = sgc.course_id WHERE sgc.student_group_id = :group_id"
            ), {"group_id": group.id}).fetchall()
            
            print(f"   👥 Group {group.name} (ID: {group.id}): {len(group_courses)} courses assigned")
            
            if not group_courses:
                print(f"❌ DEBUG: Group {group.name} has no courses assigned")
                return False
            
            # Calculate periods needed for this group
            group_periods = sum(course.periods_per_week for course in group_courses)
            total_required_periods += group_periods
            
            for course in group_courses:
                print(f"     - {course.code}: {course.name} ({course.periods_per_week} periods/week)")
        
        # Check classroom capacity constraints
        print(f"🔍 DEBUG: Checking classroom capacity constraints...")
        assigned_course_ids = set()
        for group in student_groups:
            group_courses = session.execute(text(
                "SELECT c.id FROM course c JOIN student_group_course sgc ON c.id = sgc.course_id WHERE sgc.student_group_id = :group_id"
            ), {"group_id": group.id}).fetchall()
            for course in group_courses:
                assigned_course_ids.add(course.id)
        
        assigned_courses = [c for c in courses if c.id in assigned_course_ids]
        print(f"   📚 Total assigned courses: {len(assigned_courses)}")
        
        for course in assigned_courses:
            suitable_classrooms = [c for c in classrooms if c.capacity >= course.min_capacity]
            print(f"   🏫 Course {course.code} ({course.name}): min_capacity={course.min_capacity}, suitable_classrooms={len(suitable_classrooms)}")
            
            if not suitable_classrooms:
                print(f"❌ DEBUG: Course {course.code} needs min_capacity={course.min_capacity}, but no classrooms available")
                print(f"   Available classrooms:")
                for c in classrooms:
                    print(f"     - {c.room_number}: capacity={c.capacity}")
                return False
        
        # Check equipment constraints for assigned courses only
        print(f"🔍 DEBUG: Checking equipment constraints...")
        for course in assigned_courses:
            if course.required_equipment:
                required_equipment = [eq.strip().lower() for eq in course.required_equipment.split(',') if eq.strip()]
                print(f"   🔧 Course {course.code} requires equipment: {required_equipment}")
                
                suitable_classrooms = []
                for classroom in classrooms:
                    if classroom.capacity >= course.min_capacity:
                        classroom_equipment = [eq.strip().lower() for eq in (classroom.equipment or '').split(',') if eq.strip()]
                        print(f"     🏫 Classroom {classroom.room_number}: equipment={classroom_equipment}")
                        
                        # Check if all required equipment is available
                        equipment_available = True
                        missing_equipment = []
                        for req_eq in required_equipment:
                            if req_eq:
                                equipment_found = any(req_eq in eq or eq in req_eq for eq in classroom_equipment)
                                if not equipment_found:
                                    equipment_available = False
                                    missing_equipment.append(req_eq)
                        
                        if equipment_available:
                            suitable_classrooms.append(classroom)
                            print(f"       ✅ Equipment match found")
                        else:
                            print(f"       ❌ Missing equipment: {missing_equipment}")
                
                print(f"   🏫 Course {course.code}: {len(suitable_classrooms)} suitable classrooms with equipment")
                if not suitable_classrooms:
                    print(f"❌ DEBUG: Course {course.code} needs equipment {required_equipment}, but no suitable classrooms")
                    return False
            else:
                print(f"   🔧 Course {course.code}: No equipment requirements")
        
        # Check time slot availability
        print(f"🔍 DEBUG: Checking time slot availability...")
        total_available_slots = len(time_slots) * len(student_groups)
        
        print(f"   📊 Total required periods: {total_required_periods}")
        print(f"   📊 Total available slots: {total_available_slots}")
        print(f"   📊 Time slots per day: {len([ts for ts in time_slots if ts.day == 'Monday'])}")
        print(f"   📊 Break time slots: {len([ts for ts in time_slots if ts.break_type == 'Break'])}")
        print(f"   📊 Available time slots: {len([ts for ts in time_slots if ts.break_type != 'Break'])}")
        
        if total_required_periods > total_available_slots:
            print(f"❌ DEBUG: Not enough time slots available")
            print(f"   Required: {total_required_periods} periods")
            print(f"   Available: {total_available_slots} slots")
            print(f"   Deficit: {total_required_periods - total_available_slots} slots")
            return False
        
        print(f"✅ DEBUG: All feasibility checks passed!")
        print(f"   Timetable generation should be possible")
        print(f"   Required: {total_required_periods} periods")
        print(f"   Available: {total_available_slots} slots")
        print(f"   Surplus: {total_available_slots - total_required_periods} slots")
        
        return True
        
    except Exception as e:
        print(f"❌ DEBUG: Exception during feasibility check: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    print("🔧 Timetable Feasibility Check Script")
    print("=" * 40)
    
    success = check_timetable_feasibility()
    
    if success:
        print("\n✅ Feasibility check completed successfully!")
        print("The timetable should be feasible to generate.")
    else:
        print("\n❌ Feasibility check failed!")
        print("Check the debug output above to identify the issue.")
