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
    semester: str

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
        self.group_courses = {}  # group_id -> List[Course]
        self.generated_timetables = {}  # group_id -> List[TimetableEntry]
        self.global_classroom_usage = defaultdict(list)  # (day, time) -> [classroom_id]
        self.global_teacher_usage = defaultdict(list)    # (day, time) -> [teacher_id]
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
        """Add student groups"""
        self.student_groups = student_groups
        
    def set_group_courses(self, group_courses: Dict[int, List[Course]]):
        """Set which courses are assigned to which groups"""
        self.group_courses = group_courses
        
    def generate_timetables(self) -> Dict[int, List[TimetableEntry]]:
        """
        Generate timetables for all student groups
        Returns: Dict[group_id, List[TimetableEntry]]
        """
        # Clear old data to prevent memory leaks
        self._clear_old_data()
        
        print(f"🚀 Starting timetable generation for {len(self.student_groups)} student groups...")
        print(f"📚 Available courses: {len(self.courses)}")
        print(f"🏫 Available classrooms: {len(self.classrooms)}")
        print(f"👨‍🏫 Available teachers: {len(self.teachers)}")
        print(f"⏰ Available time slots: {len(self.time_slots)}")
        
        # Generate timetable for each group
        for group in self.student_groups:
            print(f"\n📋 Generating timetable for group: {group.name} ({group.department})")
            
            # Get courses specifically assigned to this group
            group_courses = self.group_courses.get(group.id, [])
            
            if not group_courses:
                print(f"   ⚠️  No courses assigned to group: {group.name}")
                continue
            
            print(f"   📖 Found {len(group_courses)} courses assigned to this group")
            
            # Generate timetable for this group
            group_timetable = self._generate_group_timetable(group, group_courses)
            
            if group_timetable:
                self.generated_timetables[group.id] = group_timetable
                self._update_global_usage(group_timetable)
                print(f"   ✅ Successfully generated timetable with {len(group_timetable)} classes")
            else:
                print(f"   ❌ Failed to generate timetable for group {group.name}")
        
        # Print final statistics
        total_classes = sum(len(timetable) for timetable in self.generated_timetables.values())
        print(f"\n📊 Generation complete! Total classes scheduled: {total_classes}")
        
        # Show time slot usage
        for slot_key, classroom_ids in self.global_classroom_usage.items():
            if len(classroom_ids) > 1:
                print(f"   🎯 Time slot {slot_key}: {len(classroom_ids)} classes scheduled")
        
        return self.generated_timetables
    
    def _clear_old_data(self):
        """Clear old data to prevent memory leaks"""
        self.generated_timetables.clear()
        self.global_classroom_usage.clear()
        self.global_teacher_usage.clear()
        self.conflicts.clear()
        
    def cleanup(self):
        """Clean up resources and clear all data"""
        self._clear_old_data()
        self.time_slots.clear()
        self.courses.clear()
        self.classrooms.clear()
        self.teachers.clear()
        self.student_groups.clear()
    
    def _generate_group_timetable(self, group: StudentGroup, courses: List[Course]) -> Optional[List[TimetableEntry]]:
        """Generate timetable for a specific student group"""
        group_timetable = []
        group_used_slots = set()
        
        # Sort courses by priority (more periods per week first)
        sorted_courses = sorted(courses, key=lambda x: x.periods_per_week, reverse=True)
        
        for course in sorted_courses:
            periods_scheduled = 0
            attempts = 0
            max_attempts = len(self.time_slots) * 2  # Allow some retries
            
            while periods_scheduled < course.periods_per_week and attempts < max_attempts:
                attempts += 1
                
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
                else:
                    break
            
            if periods_scheduled < course.periods_per_week:
                return None  # Return None if any course fails
        
        return group_timetable
    
    def _find_available_resources(self, course: Course, group: StudentGroup, 
                                 group_used_slots: Set[Tuple[str, str]]) -> Tuple[Optional[TimeSlot], Optional[Classroom], Optional[Teacher]]:
        """Find available time slot, classroom, and teacher for a course"""
        # Shuffle time slots for better distribution
        shuffled_slots = list(self.time_slots)
        random.shuffle(shuffled_slots)
        
        for slot in shuffled_slots:
            slot_key = (slot.day, slot.start_time)
            
            # Check if slot is used by this group
            if slot_key in group_used_slots:
                continue
                
            # Find available classroom
            classroom = self._find_available_classroom(course, slot)
            if not classroom:
                continue
                
            # Find available teacher
            teacher = self._find_available_teacher(course, slot)
            if not teacher:
                continue
            
            # All resources found successfully!
            return slot, classroom, teacher
        
        print(f"   ❌ FAILED: No available resources found for course {course.code}")
        print(f"      Group used slots: {len(group_used_slots)}")
        print(f"      Available time slots: {len(self.time_slots)}")
        return None, None, None
    
    def _find_available_classroom(self, course: Course, slot: TimeSlot) -> Optional[Classroom]:
        """Find available classroom for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        
        # Filter classrooms by capacity and equipment requirements
        suitable_classrooms = []
        for c in self.classrooms:
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
                    missing_equipment = []
                    for req_eq in required_equipment:
                        if req_eq:
                            # More flexible equipment matching
                            equipment_found = any(req_eq in eq or eq in req_eq for eq in classroom_equipment)
                            if not equipment_found:
                                equipment_available = False
                                missing_equipment.append(req_eq)
                    
                    if equipment_available:
                        suitable_classrooms.append(c)
        
        # Shuffle for better distribution
        random.shuffle(suitable_classrooms)
        
        for classroom in suitable_classrooms:
            # Check if this specific classroom is available at this time
            if classroom.id not in self.global_classroom_usage[slot_key]:
                return classroom
        
        return None
    
    def _find_available_teacher(self, course: Course, slot: TimeSlot) -> Optional[Teacher]:
        """Find available teacher for a course and time slot"""
        slot_key = (slot.day, slot.start_time)
        
        # Filter teachers by department
        suitable_teachers = []
        for t in self.teachers:
            if t.department == course.department:
                suitable_teachers.append(t)
        
        # Shuffle for better distribution
        random.shuffle(suitable_teachers)
        
        for teacher in suitable_teachers:
            # Check if this specific teacher is available at this time
            if teacher.id not in self.global_teacher_usage[slot_key]:
                return teacher
        
        return None
    
    def _update_global_usage(self, group_timetable: List[TimetableEntry]):
        """Update global resource usage tracking"""
        for entry in group_timetable:
            slot_key = (entry.day, entry.start_time)
            self.global_classroom_usage[slot_key].append(entry.classroom_id)
            self.global_teacher_usage[slot_key].append(entry.teacher_id)
            
            # Show when multiple classes are scheduled in the same time slot
            if len(self.global_classroom_usage[slot_key]) > 1:
                print(f"      🎯 Multiple classes in {slot_key}: {len(self.global_classroom_usage[slot_key])} classes")
    
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
        classroom_conflicts = set()
        teacher_conflicts = set()
        
        # Check for classroom conflicts
        for slot_key, classroom_ids in self.global_classroom_usage.items():
            if len(classroom_ids) > len(set(classroom_ids)):  # Check for duplicate classroom usage
                classroom_conflicts.add(slot_key)
        
        # Check for teacher conflicts
        for slot_key, teacher_ids in self.global_teacher_usage.items():
            if len(teacher_ids) > len(set(teacher_ids)):  # Check for duplicate teacher usage
                teacher_conflicts.add(slot_key)
        
        if classroom_conflicts or teacher_conflicts:
            return False
        
        return True
    
    def get_timetable_statistics(self) -> Dict:
        """Get statistics about the generated timetables"""
        stats = {
            'total_groups': len(self.generated_timetables),
            'total_classes': sum(len(timetable) for timetable in self.generated_timetables.values()),
            'time_slot_usage': {},
            'classroom_usage': {},
            'teacher_usage': {}
        }
        
        # Count usage per time slot
        for slot_key, classroom_ids in self.global_classroom_usage.items():
            stats['time_slot_usage'][slot_key] = len(classroom_ids)
        
        # Count classroom usage
        for slot_key, classroom_ids in self.global_classroom_usage.items():
            for classroom_id in classroom_ids:
                if classroom_id not in stats['classroom_usage']:
                    stats['classroom_usage'][classroom_id] = 0
                stats['classroom_usage'][classroom_id] += 1
        
        # Count teacher usage
        for slot_key, teacher_ids in self.global_teacher_usage.items():
            for teacher_id in teacher_ids:
                if teacher_id not in stats['teacher_usage']:
                    stats['teacher_usage'][teacher_id] = 0
                stats['teacher_usage'][teacher_id] += 1
        
        return stats
    

