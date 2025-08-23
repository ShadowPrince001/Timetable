#!/usr/bin/env python3
"""
Debug script to simulate actual timetable generation and identify failures
"""

import os
import random
from datetime import datetime, time
from sqlalchemy import create_engine, text
from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Tuple

# Data classes matching the generator
@dataclass
class GenTimeSlot:
    id: int
    day: str
    start_time: time
    end_time: time

@dataclass
class GenCourse:
    id: int
    code: str
    name: str
    periods_per_week: int
    department: str
    subject_area: str
    required_equipment: str
    min_capacity: int
    max_students: int

@dataclass
class GenClassroom:
    id: int
    room_number: str
    capacity: int
    room_type: str
    equipment: str
    building: str

@dataclass
class GenTeacher:
    id: int
    name: str
    department: str

@dataclass
class GenStudentGroup:
    id: int
    name: str
    department: str
    year: int
    semester: str

@dataclass
class TimetableEntry:
    course_id: int
    course_name: str
    course_code: str
    teacher_id: int
    teacher_name: str
    classroom_id: int
    classroom_number: str
    day: str
    start_time: time
    end_time: time
    student_group_id: int
    time_slot_id: int

def debug_timetable_generation():
    """Debug the actual timetable generation process"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("🔍 DEBUG: Starting detailed timetable generation debug...")
            
            # Get all required data
            print("\n📊 Loading data from database...")
            
            # Get time slots
            result = conn.execute(text("SELECT * FROM time_slot ORDER BY day, start_time"))
            time_slots_data = result.fetchall()
            print(f"   ⏰ Time slots: {len(time_slots_data)}")
            
            # Get courses
            result = conn.execute(text("SELECT * FROM course ORDER BY code"))
            courses_data = result.fetchall()
            print(f"   📚 Courses: {len(courses_data)}")
            
            # Get classrooms
            result = conn.execute(text("SELECT * FROM classroom ORDER BY room_number"))
            classrooms_data = result.fetchall()
            print(f"   🏫 Classrooms: {len(classrooms_data)}")
            
            # Get teachers
            result = conn.execute(text('SELECT * FROM "user" WHERE role = \'faculty\' ORDER BY name'))
            teachers_data = result.fetchall()
            print(f"   👨‍🏫 Teachers: {len(teachers_data)}")
            
            # Get student groups
            result = conn.execute(text("SELECT * FROM student_group ORDER BY name"))
            student_groups_data = result.fetchall()
            print(f"   👥 Student groups: {len(student_groups_data)}")
            
            # Convert to dataclass objects
            print("\n🔄 Converting to dataclass objects...")
            
            gen_time_slots = [GenTimeSlot(
                id=ts.id, day=ts.day, start_time=ts.start_time, end_time=ts.end_time
            ) for ts in time_slots_data]
            
            gen_courses = [GenCourse(
                id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
                department=c.department, subject_area=c.subject_area,
                required_equipment=c.required_equipment or '',
                min_capacity=c.min_capacity, max_students=c.max_students
            ) for c in courses_data]
            
            gen_classrooms = [GenClassroom(
                id=c.id, room_number=c.room_number, capacity=c.capacity,
                room_type=c.room_type, equipment=c.equipment or '', building=c.building
            ) for c in classrooms_data]
            
            gen_teachers = [GenTeacher(
                id=t.id, name=t.name, department=t.department
            ) for t in teachers_data]
            
            gen_student_groups = [GenStudentGroup(
                id=g.id, name=g.name, department=g.department,
                year=g.year, semester=g.semester
            ) for g in student_groups_data]
            
            print(f"   ✅ Converted {len(gen_time_slots)} time slots, {len(gen_courses)} courses, {len(gen_classrooms)} classrooms, {len(gen_teachers)} teachers, {len(gen_student_groups)} groups")
            
            # Simulate timetable generation for each group
            print("\n🚀 Simulating timetable generation for each group...")
            
            global_classroom_usage = {}
            global_teacher_usage = {}
            
            # Initialize usage tracking
            for ts in gen_time_slots:
                slot_key = (ts.day, ts.start_time)
                global_classroom_usage[slot_key] = []
                global_teacher_usage[slot_key] = []
            
            total_successful_groups = 0
            total_classes_scheduled = 0
            
            for group in gen_student_groups:
                print(f"\n📋 Generating timetable for group: {group.name} ({group.department})")
                
                # Get courses assigned to this group
                result = conn.execute(text(
                    "SELECT c.* FROM course c JOIN student_group_course sgc ON c.id = sgc.course_id WHERE sgc.student_group_id = :group_id"
                ), {"group_id": group.id})
                group_courses_data = result.fetchall()
                
                if not group_courses_data:
                    print(f"   ❌ No courses assigned to group {group.name}")
                    continue
                
                print(f"   📖 Found {len(group_courses_data)} courses for this group")
                
                # Convert to GenCourse objects
                group_courses = [GenCourse(
                    id=c.id, code=c.code, name=c.name, periods_per_week=c.periods_per_week,
                    department=c.department, subject_area=c.subject_area,
                    required_equipment=c.required_equipment or '',
                    min_capacity=c.min_capacity, max_students=c.max_students
                ) for c in group_courses_data]
                
                # Generate timetable for this group
                group_timetable = generate_group_timetable_debug(
                    group, group_courses, gen_time_slots, gen_classrooms, 
                    gen_teachers, global_classroom_usage, global_teacher_usage
                )
                
                if group_timetable:
                    total_successful_groups += 1
                    total_classes_scheduled += len(group_timetable)
                    print(f"   ✅ Successfully generated timetable with {len(group_timetable)} classes")
                    
                    # Update global usage
                    for entry in group_timetable:
                        slot_key = (entry.day, entry.start_time)
                        global_classroom_usage[slot_key].append(entry.classroom_id)
                        global_teacher_usage[slot_key].append(entry.teacher_id)
                else:
                    print(f"   ❌ Failed to generate timetable for group {group.name}")
            
            # Print final statistics
            print(f"\n📊 Generation complete!")
            print(f"   Successful groups: {total_successful_groups}/{len(gen_student_groups)}")
            print(f"   Total classes scheduled: {total_classes_scheduled}")
            
            if total_successful_groups == 0:
                print("❌ No timetables could be generated - this explains the 'Not Feasible' result")
                return False
            elif total_successful_groups < len(gen_student_groups):
                print(f"⚠️  Only {total_successful_groups}/{len(gen_student_groups)} groups could be scheduled")
                return False
            else:
                print("✅ All groups could be scheduled - the issue might be elsewhere")
                return True
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_group_timetable_debug(group: GenStudentGroup, courses: List[GenCourse], 
                                 time_slots: List[GenTimeSlot], classrooms: List[GenClassroom],
                                 teachers: List[GenTeacher], global_classroom_usage: Dict, 
                                 global_teacher_usage: Dict) -> Optional[List[TimetableEntry]]:
    """Generate timetable for a specific student group with detailed debugging"""
    
    group_timetable = []
    group_used_slots = set()
    
    # Sort courses by priority (more periods per week first)
    sorted_courses = sorted(courses, key=lambda x: x.periods_per_week, reverse=True)
    
    for course in sorted_courses:
        print(f"     📚 Scheduling course: {course.code} ({course.periods_per_week} periods/week)")
        periods_scheduled = 0
        attempts = 0
        max_attempts = len(time_slots) * 2  # Allow some retries
        
        while periods_scheduled < course.periods_per_week and attempts < max_attempts:
            attempts += 1
            
            # Find available resources
            slot, classroom, teacher = find_available_resources_debug(
                course, group, group_used_slots, time_slots, classrooms, 
                teachers, global_classroom_usage, global_teacher_usage
            )
            
            if slot and classroom and teacher:
                # Create timetable entry
                entry = TimetableEntry(
                    course_id=course.id,
                    course_name=course.name,
                    course_code=course.code,
                    teacher_id=teacher.id,
                    teacher_name=teacher.name,
                    classroom_id=classroom.id,
                    classroom_number=classroom.room_number,
                    day=slot.day,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    student_group_id=group.id,
                    time_slot_id=slot.id
                )
                
                group_timetable.append(entry)
                group_used_slots.add((slot.day, slot.start_time))
                periods_scheduled += 1
                print(f"       ✅ Scheduled period {periods_scheduled}/{course.periods_per_week} at {slot.day} {slot.start_time}")
            else:
                if attempts == 1:  # Only show detailed failure on first attempt
                    print(f"       ❌ No available resources found for course {course.code}")
                    if not slot:
                        print(f"         - No available time slots")
                    if not classroom:
                        print(f"         - No available classrooms")
                    if not teacher:
                        print(f"         - No available teachers")
                break
        
        if periods_scheduled < course.periods_per_week:
            print(f"       ❌ Failed to schedule all periods for {course.code}: {periods_scheduled}/{course.periods_per_week}")
            return None  # Return None if any course fails
    
    return group_timetable

def find_available_resources_debug(course: GenCourse, group: GenStudentGroup, 
                                 group_used_slots: Set[Tuple[str, str]], 
                                 time_slots: List[GenTimeSlot], classrooms: List[GenClassroom],
                                 teachers: List[GenTeacher], global_classroom_usage: Dict, 
                                 global_teacher_usage: Dict) -> Tuple[Optional[GenTimeSlot], Optional[GenClassroom], Optional[GenTeacher]]:
    """Find available time slot, classroom, and teacher for a course with debugging"""
    
    # Shuffle time slots for better distribution
    shuffled_slots = list(time_slots)
    random.shuffle(shuffled_slots)
    
    for slot in shuffled_slots:
        slot_key = (slot.day, slot.start_time)
        
        # Check if slot is used by this group
        if slot_key in group_used_slots:
            continue
            
        # Find available classroom
        classroom = find_available_classroom_debug(course, slot, classrooms, global_classroom_usage)
        if not classroom:
            continue
            
        # Find available teacher
        teacher = find_available_teacher_debug(course, slot, teachers, global_teacher_usage)
        if not teacher:
            continue
        
        # All resources found successfully!
        return slot, classroom, teacher
    
    return None, None, None

def find_available_classroom_debug(course: GenCourse, slot: GenTimeSlot, 
                                 classrooms: List[GenClassroom], global_classroom_usage: Dict) -> Optional[GenClassroom]:
    """Find available classroom for a course and time slot with debugging"""
    
    slot_key = (slot.day, slot.start_time)
    
    # Filter classrooms by capacity and equipment requirements
    suitable_classrooms = []
    for c in classrooms:
        if c.capacity >= course.min_capacity:
            # Check equipment requirements
            if not course.required_equipment:
                suitable_classrooms.append(c)
            else:
                # Parse required equipment and classroom equipment
                required_equipment = [eq.strip().lower() for eq in course.required_equipment.split(',') if eq.strip()]
                classroom_equipment = [eq.strip().lower() for eq in (c.equipment or '').split(',') if eq.strip()]
                
                # Check if all required equipment is available
                equipment_available = True
                for req_eq in required_equipment:
                    if req_eq:
                        # More flexible equipment matching
                        equipment_found = any(req_eq in eq or eq in req_eq for eq in classroom_equipment)
                        if not equipment_found:
                            equipment_available = False
                            break
                
                if equipment_available:
                    suitable_classrooms.append(c)
    
    # Shuffle for better distribution
    random.shuffle(suitable_classrooms)
    
    for classroom in suitable_classrooms:
        # Check if this specific classroom is available at this time
        if classroom.id not in global_classroom_usage[slot_key]:
            return classroom
    
    return None

def find_available_teacher_debug(course: GenCourse, slot: GenTimeSlot, 
                               teachers: List[GenTeacher], global_teacher_usage: Dict) -> Optional[GenTeacher]:
    """Find available teacher for a course and time slot with debugging"""
    
    slot_key = (slot.day, slot.start_time)
    
    # Filter teachers by department
    suitable_teachers = []
    for t in teachers:
        if t.department == course.department:
            suitable_teachers.append(t)
    
    # Shuffle for better distribution
    random.shuffle(suitable_teachers)
    
    for teacher in suitable_teachers:
        # Check if this specific teacher is available at this time
        if teacher.id not in global_teacher_usage[slot_key]:
            return teacher
    
    return None

if __name__ == "__main__":
    print("🔧 Timetable Generation Debug Script")
    print("=" * 50)
    
    success = debug_timetable_generation()
    
    if success:
        print("\n✅ Debug completed successfully!")
        print("The issue might be elsewhere in the system.")
    else:
        print("\n❌ Debug identified the problem!")
        print("Check the output above to see what's failing.")
