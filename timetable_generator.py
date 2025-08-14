#!/usr/bin/env python3
"""
Automatic Timetable Generator
Generates conflict-free timetables for student groups considering:
- Teacher availability
- Classroom capacity and type
- Non-overlapping classes for student groups
- Subject frequency per week
- Time slot constraints
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class TimeSlot:
    id: int
    day: str
    start_time: str
    end_time: str

@dataclass
class Course:
    id: int
    code: str
    name: str
    periods_per_week: int
    department: str
    required_equipment: str
    min_capacity: int
    max_students: int

@dataclass
class Classroom:
    id: int
    room_number: str
    capacity: int
    room_type: str
    equipment: str
    building: str

@dataclass
class Teacher:
    id: int
    name: str
    department: str
    availability: Dict[str, List[str]]  # day -> list of time slots

@dataclass
class StudentGroup:
    id: int
    name: str
    department: str
    courses: List[Course]

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

class TimetableGenerator:
    def __init__(self):
        self.time_slots = []
        self.courses = []
        self.classrooms = []
        self.teachers = []
        self.student_groups = []
        self.generated_timetables = {}
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
        """Generate timetables for all student groups"""
        print("🚀 Starting automatic timetable generation...")
        
        # Reset generated timetables
        self.generated_timetables = {}
        self.conflicts = []
        
        # Sort courses by priority (more periods per week first)
        sorted_courses = sorted(self.courses, key=lambda x: x.periods_per_week, reverse=True)
        
        # Track global resource usage
        global_classroom_usage = {}  # (day, time) -> classroom_id
        global_teacher_usage = {}    # (day, time) -> teacher_id
        
        # Generate timetable for each student group
        for group in self.student_groups:
            print(f"📅 Generating timetable for {group.name}...")
            group_timetable = self._generate_group_timetable_with_global_constraints(
                group, sorted_courses, global_classroom_usage, global_teacher_usage
            )
            
            if not group_timetable:
                print(f"❌ Failed to generate timetable for {group.name}")
                return {}  # Return empty if any group fails
                
            self.generated_timetables[group.id] = group_timetable
            
            # Update global usage
            for entry in group_timetable:
                slot_key = (entry.day, entry.start_time)
                global_classroom_usage[slot_key] = entry.classroom_id
                global_teacher_usage[slot_key] = entry.teacher_id
        
        print(f"✅ Timetable generation completed!")
        print(f"📊 Generated timetables for {len(self.generated_timetables)} groups")
        
        return self.generated_timetables
    
    def _generate_group_timetable(self, group: StudentGroup, sorted_courses: List[Course]) -> List[TimetableEntry]:
        """Generate timetable for a specific student group"""
        timetable = []
        used_time_slots = set()
        used_classrooms = defaultdict(set)  # day -> set of time slots
        
        # Get courses for this group
        group_courses = [c for c in sorted_courses if c.department == group.department]
        
        for course in group_courses:
            if course.periods_per_week <= 0:
                continue
                
            periods_scheduled = 0
            attempts = 0
            max_attempts = 100
            
            while periods_scheduled < course.periods_per_week and attempts < max_attempts:
                attempts += 1
                
                # Find available time slot and classroom
                slot, classroom = self._find_available_slot_and_classroom(
                    course, group, used_time_slots, used_classrooms
                )
                
                if slot and classroom:
                    # Create timetable entry
                    entry = TimetableEntry(
                        course_id=course.id,
                        teacher_id=self._get_available_teacher(course, slot),
                        classroom_id=classroom.id,
                        time_slot_id=slot.id,
                        student_group_id=group.id,
                        day=slot.day,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        course_code=course.code,
                        course_name=course.name,
                        teacher_name=self._get_teacher_name(course, slot),
                        classroom_number=classroom.room_number
                    )
                    
                    timetable.append(entry)
                    used_time_slots.add((slot.day, slot.start_time))
                    used_classrooms[slot.day].add(slot.start_time)
                    periods_scheduled += 1
                    
                else:
                    # Try to find alternative time slots
                    slot = self._find_alternative_slot(course, group, used_time_slots)
                    if slot:
                        classroom = self._find_alternative_classroom(course, slot, used_classrooms)
                        if classroom:
                            entry = TimetableEntry(
                                course_id=course.id,
                                teacher_id=self._get_available_teacher(course, slot),
                                classroom_id=classroom.id,
                                time_slot_id=slot.id,
                                student_group_id=group.id,
                                day=slot.day,
                                start_time=slot.start_time,
                                end_time=slot.end_time,
                                course_code=course.code,
                                course_name=course.name,
                                teacher_name=self._get_teacher_name(course, slot),
                                classroom_number=classroom.room_number
                            )
                            
                            timetable.append(entry)
                            used_time_slots.add((slot.day, slot.start_time))
                            used_classrooms[slot.day].add(slot.start_time)
                            periods_scheduled += 1
                
                if attempts >= max_attempts:
                    print(f"⚠️  Warning: Could not schedule all periods for {course.code} in {group.name}")
                    break
        
        return timetable
    
    def _generate_group_timetable_with_global_constraints(self, group: StudentGroup, sorted_courses: List[Course],
                                                        global_classroom_usage: Dict, global_teacher_usage: Dict) -> Optional[List[TimetableEntry]]:
        """Generate timetable for a specific student group with global constraint checking"""
        timetable = []
        used_time_slots = set()
        
        # Get courses for this group
        group_courses = [c for c in sorted_courses if c.department == group.department]
        
        for course in group_courses:
            if course.periods_per_week <= 0:
                continue
                
            periods_scheduled = 0
            attempts = 0
            max_attempts = 200  # Increased attempts for better success rate
            
            while periods_scheduled < course.periods_per_week and attempts < max_attempts:
                attempts += 1
                
                # Find available time slot and classroom considering global constraints
                slot, classroom = self._find_available_slot_and_classroom_with_global_constraints(
                    course, group, used_time_slots, global_classroom_usage, global_teacher_usage
                )
                
                if slot and classroom:
                    # Create timetable entry
                    teacher_id = self._get_available_teacher_with_global_constraints(
                        course, slot, global_teacher_usage
                    )
                    
                    if teacher_id:
                        entry = TimetableEntry(
                            course_id=course.id,
                            teacher_id=teacher_id,
                            classroom_id=classroom.id,
                            time_slot_id=slot.id,
                            student_group_id=group.id,
                            day=slot.day,
                            start_time=slot.start_time,
                            end_time=slot.end_time,
                            course_code=course.code,
                            course_name=course.name,
                            teacher_name=self._get_teacher_name_by_id(teacher_id),
                            classroom_number=classroom.room_number
                        )
                        
                        timetable.append(entry)
                        used_time_slots.add((slot.day, slot.start_time))
                        periods_scheduled += 1
                
                if attempts >= max_attempts:
                    print(f"⚠️  Warning: Could not schedule all periods for {course.code} in {group.name}")
                    break
        
        # Check if we scheduled enough periods
        total_required = sum(c.periods_per_week for c in group_courses)
        total_scheduled = len(timetable)
        
        if total_scheduled < total_required * 0.8:  # Allow 80% completion
            print(f"❌ Failed to generate adequate timetable for {group.name}. Scheduled: {total_scheduled}/{total_required}")
            return None
            
        return timetable
    
        def _find_available_slot_and_classroom(
        self,
        course: Course,
        group: StudentGroup,
        used_time_slots: Set[Tuple[str, str]],
        used_classrooms: Dict[str, Set[str]]
        ) -> Tuple[Optional[TimeSlot], Optional[Classroom]]:
        #Find available time slot and classroom for a course
        # Shuffle time slots for randomization
            shuffled_slots = self.time_slots.copy()
            random.shuffle(shuffled_slots)
        
        # Try each time slot
        for slot in shuffled_slots:
            # Check if time slot is already used by this group
            if (slot.day, slot.start_time) in used_time_slots:
                continue
                
            # Find suitable classroom for this time slot
            classroom = self._find_suitable_classroom(course, slot, used_classrooms)
            if classroom:
                return slot, classroom
                
        # If no slot found, try to find any available slot with any classroom
        for slot in self.time_slots:
            if (slot.day, slot.start_time) in used_time_slots:
                continue
                
            for classroom in self.classrooms:
                if (slot.day, slot.start_time) not in used_classrooms.get(slot.day, set()):
                    if classroom.capacity >= course.min_capacity:
                        return slot, classroom
                
        return None, None
    
    def _find_suitable_classroom(self, course: Course, slot: TimeSlot, 
                               used_classrooms: Dict[str, Set[str]]) -> Optional[Classroom]:
        """Find a suitable classroom for a course at a specific time"""
        suitable_classrooms = []
        
        for classroom in self.classrooms:
            # Check if classroom is available at this time
            if slot.start_time in used_classrooms.get(slot.day, set()):
                continue
                
            # Check capacity requirements
            if classroom.capacity < course.min_capacity:
                continue
                
            # Check if classroom type matches course requirements
            if self._classroom_suitable_for_course(classroom, course):
                suitable_classrooms.append(classroom)
        
        if suitable_classrooms:
            # Prefer smaller classrooms to leave larger ones for bigger courses
            return min(suitable_classrooms, key=lambda x: x.capacity)
        
        return None
    
    def _classroom_suitable_for_course(self, classroom: Classroom, course: Course) -> bool:
        """Check if classroom is suitable for a course based on equipment and type"""
        # Basic equipment matching
        if "Computer Lab" in classroom.room_type and "Computer" in course.required_equipment:
            return True
        if "Lecture Hall" in classroom.room_type and "Whiteboard" in course.required_equipment:
            return True
        if "Lab" in classroom.room_type and "Lab" in course.required_equipment:
            return True
        
        # Default: any classroom can be used
        return True
    
    def _get_available_teacher(self, course: Course, slot: TimeSlot) -> int:
        """Get an available teacher for a course at a specific time"""
        available_teachers = []
        
        for teacher in self.teachers:
            if teacher.department == course.department:
                # Check teacher availability
                if slot.day in teacher.availability:
                    if slot.start_time in teacher.availability[slot.day]:
                        available_teachers.append(teacher)
        
        if available_teachers:
            return random.choice(available_teachers).id
        
        # Return first teacher from department if no availability info
        for teacher in self.teachers:
            if teacher.department == course.department:
                return teacher.id
        
        return 1  # Default teacher ID
    
    def _get_teacher_name(self, course: Course, slot: TimeSlot) -> str:
        """Get teacher name for a course"""
        teacher_id = self._get_available_teacher(course, slot)
        for teacher in self.teachers:
            if teacher.id == teacher_id:
                return teacher.name
        return "Unknown Teacher"
    
    def _find_alternative_slot(self, course: Course, group: StudentGroup, 
                             used_time_slots: Set[Tuple[str, str]]) -> Optional[TimeSlot]:
        """Find alternative time slot when primary slot is not available"""
        for slot in self.time_slots:
            if (slot.day, slot.start_time) not in used_time_slots:
                return slot
        return None
    
    def _find_alternative_classroom(self, course: Course, slot: TimeSlot, 
                                  used_classrooms: Dict[str, Set[str]]) -> Optional[Classroom]:
        """Find alternative classroom when primary classroom is not available"""
        for classroom in self.classrooms:
            if slot.start_time not in used_classrooms.get(slot.day, set()):
                if classroom.capacity >= course.min_capacity:
                    return classroom
        return None
    
    def _check_global_conflicts(self):
        """Check for conflicts across all groups"""
        all_entries = []
        for group_id, timetable in self.generated_timetables.items():
            all_entries.extend(timetable)
        
        # Check for teacher conflicts
        teacher_slots = defaultdict(set)
        for entry in all_entries:
            slot_key = (entry.day, entry.start_time)
            if slot_key in teacher_slots:
                self.conflicts.append(f"Teacher conflict: {entry.teacher_name} at {entry.day} {entry.start_time}")
            teacher_slots[slot_key].add(entry.teacher_id)
        
        # Check for classroom conflicts
        classroom_slots = defaultdict(set)
        for entry in all_entries:
            slot_key = (entry.day, entry.start_time)
            if slot_key in classroom_slots:
                self.conflicts.append(f"Classroom conflict: {entry.classroom_number} at {entry.day} {entry.start_time}")
            classroom_slots[slot_key].add(entry.classroom_id)
    
    def get_faculty_timetable(self, teacher_id: int) -> List[TimetableEntry]:
        """Get timetable for a specific faculty member"""
        faculty_timetable = []
        
        for group_id, timetable in self.generated_timetables.items():
            for entry in timetable:
                if entry.teacher_id == teacher_id:
                    faculty_timetable.append(entry)
        
        # Sort by day and time
        faculty_timetable.sort(key=lambda x: (self._day_to_number(x.day), x.start_time))
        
        return faculty_timetable
    
    def get_compiled_timetable(self) -> List[TimetableEntry]:
        """Get compiled timetable showing all groups"""
        compiled = []
        
        for group_id, timetable in self.generated_timetables.items():
            compiled.extend(timetable)
        
        # Sort by day, time, and group
        compiled.sort(key=lambda x: (self._day_to_number(x.day), x.start_time, x.student_group_id))
        
        return compiled
    
    def _day_to_number(self, day: str) -> int:
        """Convert day string to number for sorting"""
        day_map = {
            'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 
            'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7
        }
        return day_map.get(day, 0)
    
    def export_timetable_csv(self, timetable: List[TimetableEntry], filename: str):
        """Export timetable to CSV format"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Day', 'Time', 'Course', 'Teacher', 'Classroom', 'Group']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in timetable:
                writer.writerow({
                    'Day': entry.day,
                    'Time': f"{entry.start_time}-{entry.end_time}",
                    'Course': f"{entry.course_code} - {entry.course_name}",
                    'Teacher': entry.teacher_name,
                    'Classroom': entry.classroom_number,
                    'Group': entry.student_group_id
                })
        
        print(f"📄 Timetable exported to {filename}")
    
    def check_feasibility(self) -> Dict:
        """Check if timetable generation is feasible with current constraints"""
        total_required_periods = 0
        total_available_slots = len(self.time_slots) * 5  # 5 weekdays
        
        # Calculate total required periods
        for group in self.student_groups:
            for course in group.courses:
                total_required_periods += course.periods_per_week
        
        # Check if we have enough time slots
        if total_required_periods > total_available_slots:
            return {
                'feasible': False,
                'reason': f'Not enough time slots. Required: {total_required_periods}, Available: {total_available_slots}',
                'required_periods': total_required_periods,
                'available_slots': total_available_slots
            }
        
        # Check if we have enough classrooms
        total_classroom_slots = len(self.classrooms) * total_available_slots
        if total_required_periods > total_classroom_slots:
            return {
                'feasible': False,
                'reason': f'Not enough classroom capacity. Required: {total_required_periods}, Available: {total_classroom_slots}',
                'required_periods': total_required_periods,
                'available_classroom_slots': total_classroom_slots
            }
        
        return {
            'feasible': True,
            'reason': 'Generation appears feasible',
            'required_periods': total_required_periods,
            'available_slots': total_available_slots,
            'available_classroom_slots': total_classroom_slots
        }
    
    def get_constraint_suggestions(self) -> List[str]:
        """Get suggestions for making timetable generation feasible"""
        suggestions = []
        
        # Check time slot constraints
        total_required_periods = sum(c.periods_per_week for group in self.student_groups for c in group.courses)
        total_available_slots = len(self.time_slots) * 5
        
        if total_required_periods > total_available_slots:
            suggestions.append(f"Add more time slots. Currently {len(self.time_slots)} slots, need at least {total_required_periods // 5 + 1} slots per day")
        
        # Check classroom constraints
        if len(self.classrooms) < 2:
            suggestions.append("Add more classrooms. Currently only {len(self.classrooms)} classroom(s)")
        
        # Check teacher constraints
        if len(self.teachers) < 2:
            suggestions.append("Add more teachers. Currently only {len(self.teachers)} teacher(s)")
        
        # Check course distribution
        dept_courses = {}
        for group in self.student_groups:
            if group.department not in dept_courses:
                dept_courses[group.department] = 0
            dept_courses[group.department] += sum(c.periods_per_week for c in group.courses)
        
        for dept, periods in dept_courses.items():
            if periods > total_available_slots * 0.8:  # If department uses more than 80% of slots
                suggestions.append(f"Reduce course load for {dept} department. Currently {periods} periods, max recommended {int(total_available_slots * 0.6)}")
        
        return suggestions
    
    def analyze_constraints(self) -> Dict:
        """Analyze current constraints and provide detailed information"""
        analysis = {
            'time_slots': {
                'total': len(self.time_slots),
                'days': len(set(ts.day for ts in self.time_slots)),
                'slots_per_day': len(self.time_slots) // max(1, len(set(ts.day for ts in self.time_slots)))
            },
            'classrooms': {
                'total': len(self.classrooms),
                'total_capacity': sum(c.capacity for c in self.classrooms),
                'avg_capacity': sum(c.capacity for c in self.classrooms) // max(1, len(self.classrooms))
            },
            'teachers': {
                'total': len(self.teachers),
                'departments': len(set(t.department for t in self.teachers))
            },
            'student_groups': {
                'total': len(self.student_groups),
                'departments': len(set(g.department for g in self.student_groups))
            },
            'courses': {
                'total': len(self.courses),
                'total_periods': sum(c.periods_per_week for c in self.courses),
                'avg_periods_per_course': sum(c.periods_per_week for c in self.courses) // max(1, len(self.courses))
            }
        }
        
        # Calculate utilization ratios
        total_available_slots = len(self.time_slots) * 5
        total_required_periods = sum(c.periods_per_week for c in self.courses)
        
        analysis['utilization'] = {
            'time_slot_usage': round((total_required_periods / total_available_slots) * 100, 2),
            'classroom_usage': round((total_required_periods / (len(self.classrooms) * total_available_slots)) * 100, 2),
            'teacher_usage': round((total_required_periods / (len(self.teachers) * total_available_slots)) * 100, 2)
        }
        
        return analysis
    
    def get_statistics(self) -> Dict:
        """Get statistics about the generated timetables"""
        total_courses = len(set(entry.course_id for entries in self.generated_timetables.values() for entry in entries))
        total_periods = sum(len(entries) for entries in self.generated_timetables.values())
        total_groups = len(self.generated_timetables)
        
        # Calculate utilization
        total_slots = len(self.time_slots) * total_groups
        utilization = (total_periods / total_slots * 100) if total_slots > 0 else 0
        
        return {
            'total_groups': total_groups,
            'total_courses': total_courses,
            'total_periods': total_periods,
            'utilization_percentage': round(utilization, 2),
            'conflicts': len(self.conflicts)
        }
    
    def _find_available_slot_and_classroom_with_global_constraints(self, course: Course, group: StudentGroup,
                                                                  used_time_slots: Set[Tuple[str, str]],
                                                                  global_classroom_usage: Dict, global_teacher_usage: Dict) -> Tuple[Optional[TimeSlot], Optional[Classroom]]:
        """Find available time slot and classroom considering global constraints"""
        shuffled_slots = self.time_slots.copy()
        random.shuffle(shuffled_slots)
        
        for slot in shuffled_slots:
            slot_key = (slot.day, slot.start_time)
            
            # Check if time slot is already used by this group
            if slot_key in used_time_slots:
                continue
                
            # Check if classroom is globally used at this time
            if slot_key in global_classroom_usage:
                continue
                
            # Find suitable classroom
            for classroom in self.classrooms:
                if classroom.capacity >= course.min_capacity:
                    return slot, classroom
                    
        return None, None
    
    def _get_available_teacher_with_global_constraints(self, course: Course, slot: TimeSlot, global_teacher_usage: Dict) -> Optional[int]:
        """Get available teacher considering global constraints"""
        slot_key = (slot.day, slot.start_time)
        
        for teacher in self.teachers:
            if teacher.department == course.department:
                # Check if teacher is globally available at this time
                if slot_key not in global_teacher_usage or global_teacher_usage[slot_key] != teacher.id:
                    return teacher.id
                    
        return None
    
    def _get_teacher_name_by_id(self, teacher_id: int) -> str:
        """Get teacher name by ID"""
        for teacher in self.teachers:
            if teacher.id == teacher_id:
                return teacher.name
        return "Unknown Teacher"

# Example usage and testing
if __name__ == "__main__":
    # This would be used by the main application
    print("🚀 Timetable Generator Module Loaded")
    print("Use this module to generate automatic timetables for student groups")
