#!/usr/bin/env python3
"""
Multi-Group Timetable Generator
Generates separate timetables for each student group while ensuring
global constraints prevent conflicts between groups.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import random

@dataclass
class TimeSlot:
    id: int
    day: str
    start_time: str
    end_time: str
    break_type: str = 'none'

@dataclass
class Course:
    id: int
    code: str
    name: str
    department: str
    periods_per_week: int
    subject_area: str
    required_equipment: str = ''
    min_capacity: int = 1
    max_students: int = 50

@dataclass
class Classroom:
    id: int
    room_number: str
    capacity: int
    building: str
    room_type: str = 'lecture'
    equipment: str = ''

@dataclass
class Teacher:
    id: int
    name: str
    department: str
    availability: Optional[Set[Tuple[str, str]]] = None  # None means always available

@dataclass
class StudentGroup:
    id: int
    name: str
    department: str
    year: int
    semester: int

@dataclass
class TimetableEntry:
    course_id: int
    teacher_id: int
    classroom_id: int
    time_slot_id: int
    student_group_id: int
    day: str
    start_time: str
    end_time: str
    course_code: str
    course_name: str
    teacher_name: str
    classroom_number: str

class MultiGroupTimetableGenerator:
    def __init__(self):
        self.time_slots = []
        self.courses = []
        self.classrooms = []
        self.teachers = []
        self.student_groups = []
        self.generated_timetables = {}  # group_id -> List[TimetableEntry]
        self.global_classroom_usage = {}  # (day, time) -> classroom_id
        self.global_teacher_usage = {}    # (day, time) -> teacher_id
        self.conflicts = []
        
    def add_time_slots(self, time_slots: List[TimeSlot]):
        """Add available time slots"""
        print(f"Adding {len(time_slots)} time slots: {[f'{ts.day} {ts.start_time}-{ts.end_time}' for ts in time_slots]}")
        self.time_slots = time_slots
        
    def add_courses(self, courses: List[Course]):
        """Add courses to be scheduled"""
        self.courses = courses
        
    def add_classrooms(self, classrooms: List[Classroom]):
        """Add available classrooms"""
        self.classrooms = classrooms
        
    def add_teachers(self, teachers: List[Teacher]):
        """Add teachers with their availability"""
        self.teachers = teachers
        
    def add_student_groups(self, student_groups: List[StudentGroup]):
        """Add student groups with their courses"""
        self.student_groups = student_groups
        
    def generate_timetables(self) -> Dict[int, List[TimetableEntry]]:
        """Generate separate timetables for all student groups with global constraints"""
        print("🚀 Starting multi-group timetable generation...")
        
        # Reset state
        self.generated_timetables = {}
        self.global_classroom_usage = {}
        self.global_teacher_usage = {}
        self.conflicts = []
        
        # Sort courses by priority (more periods per week first)
        sorted_courses = sorted(self.courses, key=lambda x: x.periods_per_week, reverse=True)
        
        # Generate timetable for each student group
        for group in self.student_groups:
            print(f"📅 Generating timetable for {group.name}...")
            group_timetable = self._generate_group_timetable(group, sorted_courses)
            
            if not group_timetable:
                print(f"❌ Failed to generate timetable for {group.name}")
                return {}  # Return empty if any group fails
                
            self.generated_timetables[group.id] = group_timetable
            
            # Update global usage tracking
            self._update_global_usage(group_timetable)
        
        print(f"✅ Multi-group timetable generation completed!")
        print(f"📊 Generated timetables for {len(self.generated_timetables)} groups")
        
        return self.generated_timetables
    
    def _generate_group_timetable(self, group: StudentGroup, sorted_courses: List[Course]) -> List[TimetableEntry]:
        """Generate timetable for a specific student group"""
        timetable = []
        group_used_time_slots = set()  # Local to this group
        
        # Get courses for this group (filter by department)
        group_courses = [c for c in sorted_courses if c.department == group.department]
        
        if not group_courses:
            print(f"⚠️ No courses found for group {group.name}")
            return []
        
        print(f"📚 Scheduling {len(group_courses)} courses for {group.name}")
        
        for course in group_courses:
            if course.periods_per_week <= 0:
                continue
                
            periods_scheduled = 0
            attempts = 0
            max_attempts = 100
            
            while periods_scheduled < course.periods_per_week and attempts < max_attempts:
                attempts += 1
                
                # Find available time slot and classroom considering global constraints
                slot, classroom, teacher = self._find_available_resources(
                    course, group, group_used_time_slots
                )
                
                if slot and classroom and teacher:
                    # Create timetable entry
                    entry = TimetableEntry(
                        course_id=course.id,
                        teacher_id=teacher.id,
                        classroom_id=classroom.id,
                        time_slot_id=slot.id,
                        student_group_id=group.id,
                        day=slot.day,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        course_code=course.code,
                        course_name=course.name,
                        teacher_name=teacher.name,
                        classroom_number=classroom.room_number
                    )
                    
                    timetable.append(entry)
                    group_used_time_slots.add((slot.day, slot.start_time))
                    periods_scheduled += 1
                    
                else:
                    # Try alternative approaches
                    if attempts % 20 == 0:
                        print(f"🔄 Attempt {attempts} for {course.code} in {group.name}")
                
                if attempts >= max_attempts:
                    print(f"⚠️ Warning: Could not schedule all periods for {course.code} in {group.name}")
                    break
        
        print(f"✅ {group.name}: {len(timetable)} entries scheduled")
        return timetable
    
    def _find_available_resources(self, course: Course, group: StudentGroup, 
                                 group_used_slots: Set[Tuple[str, str]]) -> Tuple[Optional[TimeSlot], Optional[Classroom], Optional[Teacher]]:
        """Find available time slot, classroom, and teacher for a course"""
        # Shuffle time slots for better distribution
        shuffled_slots = list(self.time_slots)
        random.shuffle(shuffled_slots)
        
        for slot in shuffled_slots:
            slot_key = (slot.day, slot.start_time)
            print(f"Trying slot {slot.day} {slot.start_time}-{slot.end_time} for course {course.code} and group {group.name}")

            # Check if slot is used by this group
            if slot_key in group_used_slots:
                print(f"  Skipped: Slot already used by group {group.name}")
                continue
                
            # Check global classroom conflict
            if slot_key in self.global_classroom_usage:
                print(f"  Skipped: Classroom conflict at {slot_key}")
                continue
                
            # Check global teacher conflict
            if slot_key in self.global_teacher_usage:
                print(f"  Skipped: Teacher conflict at {slot_key}")
                continue
                
            # Find available classroom
            classroom = self._find_available_classroom(course, slot)
            if not classroom:
                print(f"  Skipped: No suitable classroom available")
                continue
                
            # Find available teacher
            teacher = self._find_available_teacher(course, slot)
            if not teacher:
                print(f"  Skipped: No suitable teacher available")
                continue
                
            print(f"  Selected slot {slot.day} {slot.start_time}-{slot.end_time} for course {course.code} and group {group.name}")
            return slot, classroom, teacher

        print(f"⚠️ No available slot found for course {course.code} and group {group.name}")
        return None, None, None
    
    def _find_available_classroom(self, course: Course, slot: TimeSlot) -> Optional[Classroom]:
        """Find available classroom for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        print(f"    All classrooms: {[f'{c.room_number} (cap={c.capacity}, eq={c.equipment})' for c in self.classrooms]}")
        print(f"    Course {course.code} min_capacity={course.min_capacity}, required_equipment='{course.required_equipment}'")
        suitable_classrooms = []
        for c in self.classrooms:
            cap_ok = c.capacity >= course.min_capacity
            eq_ok = (
                not course.required_equipment or
                any(
                    eq.strip().lower() == course.required_equipment.strip().lower()
                    for eq in c.equipment.split(',')
                )
            )
            print(f"      Checking {c.room_number}: capacity={c.capacity} (ok? {cap_ok}), equipment='{c.equipment}' (ok? {eq_ok})")
            if cap_ok and eq_ok:
                suitable_classrooms.append(c)
        print(f"    {len(suitable_classrooms)} suitable classrooms for course {course.code} at {slot.day} {slot.start_time}-{slot.end_time}: {[c.room_number for c in suitable_classrooms]}")
        random.shuffle(suitable_classrooms)
        for classroom in suitable_classrooms:
            if self.global_classroom_usage.get(slot_key) == classroom.id:
                print(f"      Classroom {classroom.room_number} is NOT available for slot {slot_key} (already booked)")
                continue
            print(f"      Classroom {classroom.room_number} is available for slot {slot_key}")
            return classroom
        print(f"    No classroom available for course {course.code} at {slot.day} {slot.start_time}-{slot.end_time}")
        return None
    
    def _find_available_teacher(self, course: Course, slot: TimeSlot) -> Optional[Teacher]:
        """Find available teacher for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        print(f"    All teachers: {[f'{t.name} (dept={t.department})' for t in self.teachers]}")
        print(f"    Course {course.code} department={course.department}")
        suitable_teachers = []
        for t in self.teachers:
            dept_ok = t.department == course.department
            # If teacher has availability, check if slot is in it; if None, assume always available
            avail_ok = (t.availability is None or slot_key in t.availability)
            print(f"      Checking {t.name}: department={t.department} (ok? {dept_ok}), available at {slot_key}? {avail_ok}")
            if dept_ok and avail_ok:
                suitable_teachers.append(t)
        print(f"    {len(suitable_teachers)} suitable teachers for course {course.code} at {slot.day} {slot.start_time}-{slot.end_time}: {[t.name for t in suitable_teachers]}")
        random.shuffle(suitable_teachers)
        for teacher in suitable_teachers:
            # Check if teacher is already used at this slot globally
            if self.global_teacher_usage.get(slot_key) == teacher.id:
                print(f"      Teacher {teacher.name} is NOT available for slot {slot_key} (already booked)")
                continue
            print(f"      Teacher {teacher.name} is available for slot {slot_key}")
            return teacher
        print(f"    No teacher available for course {course.code} at {slot.day} {slot.start_time}-{slot.end_time}")
        return None
    
    def _update_global_usage(self, group_timetable: List[TimetableEntry]):
        """Update global resource usage tracking"""
        for entry in group_timetable:
            slot_key = (entry.day, entry.start_time)
            self.global_classroom_usage[slot_key] = entry.classroom_id
            self.global_teacher_usage[slot_key] = entry.teacher_id
    
    def get_faculty_timetable(self, teacher_id: int) -> List[TimetableEntry]:
        """Get compiled timetable for a specific faculty member across all groups"""
        faculty_timetable = []
        
        for group_id, group_timetable in self.generated_timetables.items():
            for entry in group_timetable:
                if entry.teacher_id == teacher_id:
                    faculty_timetable.append(entry)
        
        # Sort by day and time
        faculty_timetable.sort(key=lambda x: (x.day, x.start_time))
        return faculty_timetable
    
    def get_group_timetable(self, group_id: int) -> List[TimetableEntry]:
        """Get timetable for a specific student group"""
        return self.generated_timetables.get(group_id, [])
    
    def get_all_timetables(self) -> Dict[int, List[TimetableEntry]]:
        """Get all generated timetables"""
        return self.generated_timetables
    
    def validate_constraints(self) -> bool:
        """Validate that all global constraints are satisfied"""
        print("🔍 Validating global constraints...")
        
        classroom_conflicts = set()
        teacher_conflicts = set()
        
        # Check for classroom conflicts
        classroom_usage = defaultdict(list)
        for group_id, group_timetable in self.generated_timetables.items():
            for entry in group_timetable:
                slot_key = (entry.day, entry.start_time)
                classroom_usage[slot_key].append((entry.classroom_id, group_id))
                
                if len(classroom_usage[slot_key]) > 1:
                    classroom_conflicts.add(slot_key)
        
        # Check for teacher conflicts
        teacher_usage = defaultdict(list)
        for group_id, group_timetable in self.generated_timetables.items():
            for entry in group_timetable:
                slot_key = (entry.day, entry.start_time)
                teacher_usage[slot_key].append((entry.teacher_id, group_id))
                
                if len(teacher_usage[slot_key]) > 1:
                    teacher_conflicts.add(slot_key)
        
        if classroom_conflicts or teacher_conflicts:
            print("❌ Constraint violations found:")
            if classroom_conflicts:
                print(f"   • Classroom conflicts: {len(classroom_conflicts)}")
            if teacher_conflicts:
                print(f"   • Teacher conflicts: {len(teacher_conflicts)}")
            return False
        
        print("✅ All global constraints satisfied")
        return True
    
    def print_summary(self):
        """Print summary of generated timetables"""
        print("\n📊 Multi-Group Timetable Summary")
        print("=" * 50)
        
        total_entries = 0
        for group_id, group_timetable in self.generated_timetables.items():
            group_name = next((g.name for g in self.student_groups if g.id == group_id), f"Group {group_id}")
            print(f"📅 {group_name}: {len(group_timetable)} entries")
            total_entries += len(group_timetable)
        
        print(f"\n📈 Total Entries: {total_entries}")
        print(f"🏫 Groups: {len(self.generated_timetables)}")
        print(f"⏰ Time Slots Used: {len(self.global_classroom_usage)}")
        
        # Faculty summary
        faculty_workload = defaultdict(int)
        for group_timetable in self.generated_timetables.values():
            for entry in group_timetable:
                faculty_workload[entry.teacher_name] += 1

        print("-" * 50)
        print("\nFaculty Workload:")
        for teacher, count in sorted(faculty_workload.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {teacher}: {count} classes")
