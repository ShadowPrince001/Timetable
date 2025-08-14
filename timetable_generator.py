#!/usr/bin/env python3
"""
Multi-Group Timetable Generator
Generates separate timetables for each student group while ensuring
global constraints prevent conflicts between groups.
"""

from dataclasses import dataclass
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
    availability: Set[Tuple[str, str]] = None  # Set of (day, time) tuples

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
    course_name: str
    teacher_id: int
    teacher_name: str
    classroom_id: int
    classroom_number: str
    day: str
    start_time: str
    end_time: str
    student_group_id: int
    time_slot_id: int = 0  # Default value for backward compatibility
    course_code: str = ''   # Default value for backward compatibility

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
        """
        Generate timetables for all student groups
        Returns: Dict[group_id, List[TimetableEntry]]
        """
        print(f"\n🚀 DEBUG: Starting timetable generation for {len(self.student_groups)} groups")
        print(f"   📚 Courses: {len(self.courses)}")
        print(f"   🏫 Classrooms: {len(self.classrooms)}")
        print(f"   👨‍🏫 Teachers: {len(self.teachers)}")
        print(f"   ⏰ Time slots: {len(self.time_slots)}")
        
        self.generated_timetables = {}
        self.global_classroom_usage = {}
        self.global_teacher_usage = {}
        self.conflicts = []
        
        # Generate timetable for each group
        for group in self.student_groups:
            print(f"\n👥 DEBUG: Generating timetable for group {group.name} ({group.department})")
            
            # Get courses for this group (filter by department)
            group_courses = [c for c in self.courses if c.department == group.department]
            print(f"   📚 Group courses: {len(group_courses)}")
            for course in group_courses:
                print(f"      - {course.code}: {course.name} (periods: {course.periods_per_week}, equipment: '{course.required_equipment}')")
            
            if not group_courses:
                print(f"   ❌ No courses found for group {group.name}")
                continue
            
            # Generate timetable for this group
            group_timetable = self._generate_group_timetable(group, group_courses)
            
            if group_timetable:
                print(f"   ✅ Successfully generated timetable with {len(group_timetable)} entries")
                self.generated_timetables[group.id] = group_timetable
                self._update_global_usage(group_timetable)
            else:
                print(f"   ❌ FAILED to generate timetable for group {group.name}")
                print(f"   💡 This group may not be feasible with current constraints")
        
        print(f"\n📊 DEBUG: Timetable generation completed")
        print(f"   ✅ Successful groups: {len(self.generated_timetables)}")
        print(f"   ❌ Failed groups: {len(self.student_groups) - len(self.generated_timetables)}")
        
        if self.conflicts:
            print(f"   ⚠️ Conflicts found: {len(self.conflicts)}")
            for conflict in self.conflicts:
                print(f"      - {conflict}")
        
        return self.generated_timetables
    
    def _generate_group_timetable(self, group: StudentGroup, courses: List[Course]) -> Optional[List[TimetableEntry]]:
        """Generate timetable for a specific student group"""
        print(f"      📅 DEBUG: Generating timetable for group {group.name}")
        
        group_timetable = []
        group_used_slots = set()
        
        # Sort courses by priority (more periods per week first)
        sorted_courses = sorted(courses, key=lambda x: x.periods_per_week, reverse=True)
        print(f"         📚 Scheduling {len(sorted_courses)} courses by priority")
        
        for course in sorted_courses:
            print(f"\n         🔍 DEBUG: Scheduling course {course.code} ({course.name})")
            print(f"            📊 Required periods: {course.periods_per_week}")
            print(f"            📏 Min capacity: {course.min_capacity}")
            print(f"            🔧 Equipment: '{course.required_equipment}'")
            
            periods_scheduled = 0
            attempts = 0
            max_attempts = len(self.time_slots) * 2  # Allow some retries
            
            while periods_scheduled < course.periods_per_week and attempts < max_attempts:
                attempts += 1
                print(f"            ⏰ Attempt {attempts}: Looking for slot {periods_scheduled + 1}/{course.periods_per_week}")
                
                # Find available resources
                slot, classroom, teacher = self._find_available_resources(course, group, group_used_slots)
                
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
                    
                    print(f"            ✅ Scheduled: {slot.day} {slot.start_time}-{slot.end_time} in {classroom.room_number} with {teacher.name}")
                else:
                    print(f"            ❌ No resources available for this attempt")
                    break
            
            if periods_scheduled < course.periods_per_week:
                print(f"            ❌ FAILED: Only scheduled {periods_scheduled}/{course.periods_per_week} periods")
                print(f"            💡 This course cannot be fully scheduled - constraint violation")
                return None  # Return None if any course fails
            else:
                print(f"            ✅ SUCCESS: Scheduled all {course.periods_per_week} periods")
        
        print(f"         🎉 DEBUG: Successfully generated timetable for group {group.name}")
        print(f"            📊 Total entries: {len(group_timetable)}")
        return group_timetable
    
    def _find_available_resources(self, course: Course, group: StudentGroup, 
                                 group_used_slots: Set[Tuple[str, str]]) -> Tuple[Optional[TimeSlot], Optional[Classroom], Optional[Teacher]]:
        """Find available time slot, classroom, and teacher for a course"""
        # Shuffle time slots for better distribution
        shuffled_slots = list(self.time_slots)
        random.shuffle(shuffled_slots)
        
        print(f"🔍 DEBUG: Looking for resources for course {course.code} ({course.name})")
        print(f"   📚 Course requirements: min_capacity={course.min_capacity}, equipment='{course.required_equipment}'")
        print(f"   👥 Student group: {group.name} ({group.department})")
        print(f"   ⏰ Available time slots: {len(self.time_slots)}")
        print(f"   🏫 Available classrooms: {len(self.classrooms)}")
        print(f"   👨‍🏫 Available teachers: {len(self.teachers)}")
        
        for slot in shuffled_slots:
            slot_key = (slot.day, slot.start_time)
            
            print(f"\n⏰ DEBUG: Checking time slot {slot.day} {slot.start_time}-{slot.end_time}")
            
            # Check if slot is used by this group
            if slot_key in group_used_slots:
                print(f"   ❌ Slot already used by this group")
                continue
                
            # Check global classroom conflict
            if slot_key in self.global_classroom_usage:
                print(f"   ❌ Global classroom conflict at this time")
                continue
                
            # Check global teacher conflict
            if slot_key in self.global_teacher_usage:
                print(f"   ❌ Global teacher conflict at this time")
                continue
                
            print(f"   ✅ Time slot available")
            
            # Find available classroom
            classroom = self._find_available_classroom(course, slot)
            if not classroom:
                print(f"   ❌ No suitable classroom found")
                continue
            else:
                print(f"   ✅ Found classroom: {classroom.room_number} (capacity: {classroom.capacity}, equipment: '{classroom.equipment}')")
                
            # Find available teacher
            teacher = self._find_available_teacher(course, slot)
            if not teacher:
                print(f"   ❌ No suitable teacher found")
                continue
            else:
                print(f"   ✅ Found teacher: {teacher.name} ({teacher.department})")
            
            print(f"   🎉 All resources found successfully!")
            return slot, classroom, teacher
        
        print(f"   ❌ FAILED: No available resources found for course {course.code}")
        return None, None, None
    
    def _find_available_classroom(self, course: Course, slot: TimeSlot) -> Optional[Classroom]:
        """Find available classroom for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        
        print(f"      🏫 DEBUG: Looking for classroom for course {course.code}")
        print(f"         📏 Required capacity: {course.min_capacity}")
        print(f"         🔧 Required equipment: '{course.required_equipment}'")
        
        # Filter classrooms by capacity and equipment requirements
        suitable_classrooms = []
        for c in self.classrooms:
            print(f"         🔍 Checking classroom {c.room_number}:")
            print(f"            📏 Capacity: {c.capacity} (required: {course.min_capacity})")
            print(f"            🔧 Equipment: '{c.equipment}'")
            
            if c.capacity >= course.min_capacity:
                print(f"            ✅ Capacity OK")
                # Check equipment requirements
                if not course.required_equipment:
                    print(f"            ✅ No equipment required")
                    suitable_classrooms.append(c)
                else:
                    # Parse required equipment and classroom equipment
                    required_equipment = [eq.strip().lower() for eq in course.required_equipment.split(',') if eq.strip()]
                    classroom_equipment = [eq.strip().lower() for eq in (c.equipment or '').split(',') if eq.strip()]
                    
                    print(f"            🔧 Required equipment: {required_equipment}")
                    print(f"            🔧 Classroom equipment: {classroom_equipment}")
                    
                    # Check if all required equipment is available
                    equipment_available = True
                    missing_equipment = []
                    for req_eq in required_equipment:
                        if req_eq:
                            # More flexible equipment matching
                            equipment_found = any(req_eq in eq or eq in req_eq for eq in classroom_equipment)
                            if not equipment_found:
                                equipment_available = False
                                missing_equipment.append(req_eq)
                                print(f"            ❌ Missing equipment: {req_eq}")
                            else:
                                print(f"            ✅ Equipment found: {req_eq}")
                    
                    if equipment_available:
                        print(f"            ✅ All equipment available")
                        suitable_classrooms.append(c)
                    else:
                        print(f"            ❌ Missing equipment: {missing_equipment}")
            else:
                print(f"            ❌ Capacity too low")
        
        print(f"         📊 Found {len(suitable_classrooms)} suitable classrooms")
        
        # Shuffle for better distribution
        random.shuffle(suitable_classrooms)
        
        for classroom in suitable_classrooms:
            # Check if classroom is available at this time globally
            if slot_key not in self.global_classroom_usage:
                print(f"         ✅ Classroom {classroom.room_number} available at this time")
                return classroom
            else:
                print(f"         ❌ Classroom {classroom.room_number} already booked at this time")
        
        print(f"         ❌ No available classrooms at this time slot")
        return None
    
    def _find_available_teacher(self, course: Course, slot: TimeSlot) -> Optional[Teacher]:
        """Find available teacher for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        
        print(f"      👨‍🏫 DEBUG: Looking for teacher for course {course.code}")
        print(f"         🏢 Course department: {course.department}")
        
        # Filter teachers by department
        suitable_teachers = []
        for t in self.teachers:
            print(f"         🔍 Checking teacher {t.name}:")
            print(f"            🏢 Department: {t.department} (required: {course.department})")
            
            if t.department == course.department:
                print(f"            ✅ Department matches")
                suitable_teachers.append(t)
            else:
                print(f"            ❌ Department mismatch")
        
        print(f"         📊 Found {len(suitable_teachers)} suitable teachers")
        
        # Shuffle for better distribution
        random.shuffle(suitable_teachers)
        
        for teacher in suitable_teachers:
            # Check if teacher is available at this time globally
            if slot_key not in self.global_teacher_usage:
                print(f"         ✅ Teacher {teacher.name} available at this time")
                return teacher
            else:
                print(f"         ❌ Teacher {teacher.name} already booked at this time")
        
        print(f"         ❌ No available teachers at this time slot")
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
        
        print(f"\n👨‍🏫 Faculty Workload:")
        for teacher, count in sorted(faculty_workload.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {teacher}: {count} classes")
