"""
Timetable Algorithm Comparison
Compare Greedy vs Genetic Algorithm approaches
"""

import time
import json
from datetime import datetime
from genetic_timetable_generator import GeneticTimetableGenerator

class GreedyTimetableGenerator:
    """Simple greedy algorithm for comparison"""
    
    def __init__(self):
        self.courses = []
        self.teachers = []
        self.classrooms = []
        self.time_slots = []
        self.student_groups = []
    
    def set_data(self, courses, teachers, classrooms, time_slots, student_groups):
        """Set the data for timetable generation"""
        self.courses = courses
        self.teachers = teachers
        self.classrooms = classrooms
        self.time_slots = time_slots
        self.student_groups = student_groups
    
    def generate_timetable(self):
        """Generate timetable using greedy approach"""
        print("⚡ Starting Greedy Algorithm Timetable Generation...")
        
        start_time = time.time()
        assignments = []
        used_slots = set()
        used_rooms = set()
        used_teachers = set()
        
        for course in self.courses:
            # Find first available slot
            assigned = False
            for time_slot in self.time_slots:
                if assigned:
                    break
                    
                for classroom in self.classrooms:
                    if assigned:
                        break
                        
                    for teacher in self.teachers:
                        # Check if slot is available
                        slot_key = (time_slot['id'], classroom['id'])
                        teacher_key = (time_slot['id'], teacher['id'])
                        
                        if slot_key not in used_slots and teacher_key not in used_teachers:
                            assignments.append({
                                'course_id': course['id'],
                                'course_name': course['name'],
                                'time_slot_id': time_slot['id'],
                                'time_slot': time_slot,
                                'classroom_id': classroom['id'],
                                'classroom': classroom,
                                'teacher_id': teacher['id'],
                                'teacher': teacher,
                                'day': time_slot.get('day', 'Monday'),
                                'start_time': time_slot.get('start_time', '09:00'),
                                'end_time': time_slot.get('end_time', '10:00')
                            })
                            
                            used_slots.add(slot_key)
                            used_teachers.add(teacher_key)
                            assigned = True
                            break
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Count conflicts (should be 0 for greedy)
        conflicts = self._count_conflicts(assignments)
        
        return {
            'timetable': {
                'assignments': assignments,
                'summary': {
                    'total_courses': len(assignments),
                    'total_conflicts': conflicts,
                    'generation_method': 'Greedy Algorithm'
                }
            },
            'execution_time': execution_time,
            'conflicts': conflicts,
            'constraint_violations': self._count_constraint_violations(assignments)
        }
    
    def _count_conflicts(self, assignments):
        """Count conflicts in assignments"""
        conflicts = 0
        used_slots = set()
        used_teachers = set()
        
        for assignment in assignments:
            slot_key = (assignment['time_slot_id'], assignment['classroom_id'])
            teacher_key = (assignment['time_slot_id'], assignment['teacher_id'])
            
            if slot_key in used_slots:
                conflicts += 1
            if teacher_key in used_teachers:
                conflicts += 1
                
            used_slots.add(slot_key)
            used_teachers.add(teacher_key)
        
        return conflicts
    
    def _count_constraint_violations(self, assignments):
        """Count different types of constraint violations"""
        return {
            'total_conflicts': self._count_conflicts(assignments),
            'teacher_conflicts': 0,  # Greedy should have 0
            'room_conflicts': 0,     # Greedy should have 0
            'time_conflicts': 0      # Greedy should have 0
        }

def create_sample_data():
    """Create comprehensive sample data for testing"""
    courses = [
        {'id': 1, 'name': 'Mathematics 101', 'min_capacity': 30, 'subject_area': 'Mathematics', 'credits': 3},
        {'id': 2, 'name': 'Computer Science 101', 'min_capacity': 25, 'subject_area': 'Computer Science', 'credits': 4},
        {'id': 3, 'name': 'Physics 101', 'min_capacity': 35, 'subject_area': 'Physics', 'credits': 4},
        {'id': 4, 'name': 'English 101', 'min_capacity': 40, 'subject_area': 'English', 'credits': 3},
        {'id': 5, 'name': 'Chemistry 101', 'min_capacity': 30, 'subject_area': 'Chemistry', 'credits': 4},
        {'id': 6, 'name': 'History 101', 'min_capacity': 45, 'subject_area': 'History', 'credits': 3},
        {'id': 7, 'name': 'Biology 101', 'min_capacity': 35, 'subject_area': 'Biology', 'credits': 4},
        {'id': 8, 'name': 'Economics 101', 'min_capacity': 40, 'subject_area': 'Economics', 'credits': 3}
    ]
    
    teachers = [
        {'id': 1, 'name': 'Dr. Smith', 'department': 'Mathematics', 'preferences': ['morning', 'consecutive']},
        {'id': 2, 'name': 'Dr. Johnson', 'department': 'Computer Science', 'preferences': ['afternoon', 'lab_sessions']},
        {'id': 3, 'name': 'Dr. Brown', 'department': 'Physics', 'preferences': ['morning', 'large_rooms']},
        {'id': 4, 'name': 'Dr. Wilson', 'department': 'English', 'preferences': ['flexible', 'small_groups']},
        {'id': 5, 'name': 'Dr. Davis', 'department': 'Chemistry', 'preferences': ['lab_sessions', 'afternoon']},
        {'id': 6, 'name': 'Dr. Miller', 'department': 'History', 'preferences': ['lecture_halls', 'morning']},
        {'id': 7, 'name': 'Dr. Garcia', 'department': 'Biology', 'preferences': ['lab_sessions', 'flexible']},
        {'id': 8, 'name': 'Dr. Martinez', 'department': 'Economics', 'preferences': ['afternoon', 'interactive']}
    ]
    
    classrooms = [
        {'id': 1, 'room_number': 'A101', 'capacity': 40, 'room_type': 'lecture', 'building': 'A'},
        {'id': 2, 'room_number': 'A102', 'capacity': 30, 'room_type': 'lecture', 'building': 'A'},
        {'id': 3, 'room_number': 'Lab1', 'capacity': 25, 'room_type': 'lab', 'building': 'B'},
        {'id': 4, 'room_number': 'Lab2', 'capacity': 20, 'room_type': 'lab', 'building': 'B'},
        {'id': 5, 'room_number': 'A201', 'capacity': 50, 'room_type': 'lecture', 'building': 'A'},
        {'id': 6, 'room_number': 'A202', 'capacity': 35, 'room_type': 'lecture', 'building': 'A'},
        {'id': 7, 'room_number': 'Lab3', 'capacity': 30, 'room_type': 'lab', 'building': 'B'},
        {'id': 8, 'room_number': 'Auditorium', 'capacity': 100, 'room_type': 'auditorium', 'building': 'C'}
    ]
    
    time_slots = [
        {'id': 1, 'day': 'Monday', 'start_time': '08:00', 'end_time': '09:00'},
        {'id': 2, 'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00'},
        {'id': 3, 'day': 'Monday', 'start_time': '10:00', 'end_time': '11:00'},
        {'id': 4, 'day': 'Monday', 'start_time': '11:00', 'end_time': '12:00'},
        {'id': 5, 'day': 'Monday', 'start_time': '13:00', 'end_time': '14:00'},
        {'id': 6, 'day': 'Monday', 'start_time': '14:00', 'end_time': '15:00'},
        {'id': 7, 'day': 'Tuesday', 'start_time': '08:00', 'end_time': '09:00'},
        {'id': 8, 'day': 'Tuesday', 'start_time': '09:00', 'end_time': '10:00'},
        {'id': 9, 'day': 'Tuesday', 'start_time': '10:00', 'end_time': '11:00'},
        {'id': 10, 'day': 'Tuesday', 'start_time': '11:00', 'end_time': '12:00'},
        {'id': 11, 'day': 'Tuesday', 'start_time': '13:00', 'end_time': '14:00'},
        {'id': 12, 'day': 'Tuesday', 'start_time': '14:00', 'end_time': '15:00'},
        {'id': 13, 'day': 'Wednesday', 'start_time': '08:00', 'end_time': '09:00'},
        {'id': 14, 'day': 'Wednesday', 'start_time': '09:00', 'end_time': '10:00'},
        {'id': 15, 'day': 'Wednesday', 'start_time': '10:00', 'end_time': '11:00'},
        {'id': 16, 'day': 'Wednesday', 'start_time': '11:00', 'end_time': '12:00'}
    ]
    
    student_groups = [
        {'id': 1, 'name': 'Computer Science Year 1', 'size': 30, 'courses': [1, 2, 3, 4]},
        {'id': 2, 'name': 'Mathematics Year 1', 'size': 25, 'courses': [1, 3, 5, 6]},
        {'id': 3, 'name': 'Physics Year 1', 'size': 35, 'courses': [1, 3, 5, 7]},
        {'id': 4, 'name': 'Engineering Year 1', 'size': 40, 'courses': [1, 2, 3, 8]}
    ]
    
    return courses, teachers, classrooms, time_slots, student_groups

def evaluate_timetable_quality(assignments, courses, teachers, classrooms, time_slots):
    """Evaluate the quality of a timetable solution"""
    quality_score = 0.0
    total_assignments = len(assignments)
    
    if total_assignments == 0:
        return 0.0
    
    # Room efficiency (capacity matching)
    room_efficiency = 0.0
    for assignment in assignments:
        course = next(c for c in courses if c['id'] == assignment['course_id'])
        
        # Handle both object and ID formats
        if 'classroom' in assignment and isinstance(assignment['classroom'], dict):
            # Genetic algorithm format (object)
            classroom = assignment['classroom']
        else:
            # Greedy algorithm format (ID)
            classroom_id = assignment.get('classroom_id')
            classroom = next(c for c in classrooms if c['id'] == classroom_id)
        
        if course['min_capacity'] <= classroom['capacity']:
            room_efficiency += 1.0
        
        # Bonus for appropriate room types
        if course['subject_area'] == 'Computer Science' and 'lab' in classroom['room_type']:
            room_efficiency += 0.5
        elif course['subject_area'] == 'Chemistry' and 'lab' in classroom['room_type']:
            room_efficiency += 0.5
    
    room_efficiency /= total_assignments
    quality_score += room_efficiency * 25.0
    
    # Time distribution (prefer balanced days)
    daily_loads = {}
    for assignment in assignments:
        day = assignment['day']
        daily_loads[day] = daily_loads.get(day, 0) + 1
    
    if daily_loads:
        max_load = max(daily_loads.values())
        min_load = min(daily_loads.values())
        balance = 1.0 - (max_load - min_load) / max_load if max_load > 0 else 1.0
        quality_score += balance * 20.0
    
    # Teacher preferences
    teacher_pref_score = 0.0
    for assignment in assignments:
        # Handle both object and ID formats
        if 'teacher' in assignment and isinstance(assignment['teacher'], dict):
            # Genetic algorithm format (object)
            teacher = assignment['teacher']
        else:
            # Greedy algorithm format (ID)
            teacher_id = assignment.get('teacher_id')
            teacher = next(t for t in teachers if t['id'] == teacher_id)
        
        if 'time_slot' in assignment and isinstance(assignment['time_slot'], dict):
            # Genetic algorithm format (object)
            time_slot = assignment['time_slot']
        else:
            # Greedy algorithm format (ID)
            time_slot_id = assignment.get('time_slot_id')
            time_slot = next(ts for ts in time_slots if ts['id'] == time_slot_id)
        
        # Morning preference
        if '08:00' <= time_slot['start_time'] <= '12:00':
            teacher_pref_score += 1.0
        
        # Consecutive slots preference
        # This is simplified - would need more complex logic
    
    teacher_pref_score /= total_assignments
    quality_score += teacher_pref_score * 15.0
    
    # Subject area clustering (similar subjects on same days)
    subject_days = {}
    for assignment in assignments:
        course = next(c for c in courses if c['id'] == assignment['course_id'])
        day = assignment['day']
        subject = course['subject_area']
        
        if subject not in subject_days:
            subject_days[subject] = set()
        subject_days[subject].add(day)
    
    clustering_score = 0.0
    for subject, days in subject_days.items():
        if len(days) <= 2:  # Prefer subjects spread across fewer days
            clustering_score += 1.0
    
    clustering_score /= len(subject_days) if subject_days else 1
    quality_score += clustering_score * 10.0
    
    return quality_score

def run_comparison():
    """Run comparison between greedy and genetic algorithms"""
    print("🔬 TIMETABLE ALGORITHM COMPARISON")
    print("=" * 60)
    
    # Create sample data
    courses, teachers, classrooms, time_slots, student_groups = create_sample_data()
    
    print(f"📚 Courses: {len(courses)}")
    print(f"👨‍🏫 Teachers: {len(teachers)}")
    print(f"🏫 Classrooms: {len(classrooms)}")
    print(f"⏰ Time Slots: {len(time_slots)}")
    print(f"👥 Student Groups: {len(student_groups)}")
    print()
    
    # Test Greedy Algorithm
    print("⚡ TESTING GREEDY ALGORITHM")
    print("-" * 40)
    
    greedy_generator = GreedyTimetableGenerator()
    greedy_generator.set_data(courses, teachers, classrooms, time_slots, student_groups)
    
    greedy_start = time.time()
    greedy_result = greedy_generator.generate_timetable()
    greedy_end = time.time()
    
    greedy_time = greedy_end - greedy_start
    greedy_quality = evaluate_timetable_quality(
        greedy_result['timetable']['assignments'], 
        courses, teachers, classrooms, time_slots
    )
    
    print(f"⏱️  Execution Time: {greedy_time:.4f} seconds")
    print(f"🎯 Quality Score: {greedy_quality:.2f}/100")
    print(f"❌ Conflicts: {greedy_result['conflicts']}")
    print()
    
    # Test Genetic Algorithm
    print("🧬 TESTING GENETIC ALGORITHM")
    print("-" * 40)
    
    genetic_generator = GeneticTimetableGenerator(
        population_size=30,
        generations=50,
        mutation_rate=0.15,
        crossover_rate=0.8,
        elite_size=3
    )
    
    genetic_generator.set_data(courses, teachers, classrooms, time_slots, student_groups)
    
    genetic_start = time.time()
    genetic_result = genetic_generator.generate_timetable()
    genetic_end = time.time()
    
    genetic_time = genetic_end - genetic_start
    genetic_quality = evaluate_timetable_quality(
        genetic_result['timetable']['assignments'], 
        courses, teachers, classrooms, time_slots
    )
    
    print(f"⏱️  Execution Time: {genetic_time:.4f} seconds")
    print(f"🎯 Quality Score: {genetic_quality:.2f}/100")
    print(f"❌ Conflicts: {genetic_result['constraint_violations']['total_conflicts']}")
    print()
    
    # Comparison Results
    print("📊 COMPARISON RESULTS")
    print("=" * 60)
    
    time_ratio = genetic_time / greedy_time if greedy_time > 0 else float('inf')
    quality_improvement = genetic_quality - greedy_quality
    quality_ratio = genetic_quality / greedy_quality if greedy_quality > 0 else float('inf')
    
    print(f"⏱️  Time Ratio (Genetic/Greedy): {time_ratio:.2f}x")
    print(f"🎯 Quality Improvement: {quality_improvement:+.2f} points")
    print(f"📈 Quality Ratio (Genetic/Greedy): {quality_ratio:.2f}x")
    print()
    
    # Detailed Analysis
    print("🔍 DETAILED ANALYSIS")
    print("-" * 40)
    
    if time_ratio < 10:
        print("✅ Genetic algorithm is reasonably fast")
    elif time_ratio < 50:
        print("⚠️  Genetic algorithm is moderately slower")
    else:
        print("❌ Genetic algorithm is significantly slower")
    
    if quality_improvement > 20:
        print("🎉 Genetic algorithm provides substantial quality improvement")
    elif quality_improvement > 10:
        print("👍 Genetic algorithm provides good quality improvement")
    elif quality_improvement > 0:
        print("📈 Genetic algorithm provides modest quality improvement")
    else:
        print("⚠️  Genetic algorithm didn't improve quality in this case")
    
    if quality_ratio > 1.5:
        print("🏆 Genetic algorithm is clearly superior for quality")
    elif quality_ratio > 1.2:
        print("📊 Genetic algorithm shows good quality advantage")
    elif quality_ratio > 1.0:
        print("📈 Genetic algorithm has slight quality advantage")
    else:
        print("⚡ Greedy algorithm performed better in this case")
    
    print()
    
    # Recommendations
    print("💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if quality_improvement > 15 and time_ratio < 20:
        print("🎯 Use Genetic Algorithm: High quality improvement with reasonable time cost")
    elif quality_improvement > 10 and time_ratio < 10:
        print("👍 Consider Genetic Algorithm: Good quality improvement and acceptable time cost")
    elif time_ratio > 50:
        print("⚡ Stick with Greedy Algorithm: Genetic algorithm too slow for current needs")
    elif quality_improvement < 5:
        print("⚡ Stick with Greedy Algorithm: Minimal quality improvement doesn't justify time cost")
    else:
        print("🤔 Consider both: Use greedy for quick results, genetic for final optimization")
    
    # Save results
    comparison_data = {
        'timestamp': datetime.now().isoformat(),
        'data_summary': {
            'courses': len(courses),
            'teachers': len(teachers),
            'classrooms': len(classrooms),
            'time_slots': len(time_slots),
            'student_groups': len(student_groups)
        },
        'greedy_results': {
            'execution_time': greedy_time,
            'quality_score': greedy_quality,
            'conflicts': greedy_result['conflicts']
        },
        'genetic_results': {
            'execution_time': genetic_time,
            'quality_score': genetic_quality,
            'conflicts': genetic_result['constraint_violations']['total_conflicts'],
            'generations': genetic_result['generations_completed']
        },
        'comparison': {
            'time_ratio': time_ratio,
            'quality_improvement': quality_improvement,
            'quality_ratio': quality_ratio
        }
    }
    
    filename = f"algorithm_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(comparison_data, f, indent=2, default=str)
    
    print(f"\n💾 Comparison results saved to: {filename}")
    
    return comparison_data

if __name__ == "__main__":
    # Run the comparison
    results = run_comparison()
    
    print("\n" + "=" * 60)
    print("🏁 COMPARISON COMPLETE")
    print("=" * 60)
    print("Check the generated JSON file for detailed results!")
