"""
Genetic Algorithm Timetable Generator
An advanced timetable optimization system using evolutionary algorithms
"""

import random
import copy
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json

class GeneticTimetableGenerator:
    def __init__(self, 
                 population_size: int = 50,
                 generations: int = 100,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8,
                 elite_size: int = 5):
        """
        Initialize the genetic algorithm timetable generator
        
        Args:
            population_size: Number of solutions in each generation
            generations: Maximum number of generations to evolve
            mutation_rate: Probability of mutation (0.0 to 1.0)
            crossover_rate: Probability of crossover (0.0 to 1.0)
            elite_size: Number of best solutions to preserve each generation
        """
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        
        # Timetable constraints and data
        self.courses = []
        self.teachers = []
        self.classrooms = []
        self.time_slots = []
        self.student_groups = []
        
        # Fitness weights for multi-objective optimization
        self.fitness_weights = {
            'conflicts': 100.0,           # Hard constraint - must be 0
            'teacher_preferences': 10.0,  # Soft constraint
            'room_efficiency': 5.0,       # Soft constraint
            'student_load': 8.0,          # Soft constraint
            'time_distribution': 3.0      # Soft constraint
        }
        
        # Statistics tracking
        self.generation_stats = []
        self.best_fitness_history = []
        
    def set_data(self, courses: List, teachers: List, classrooms: List, 
                 time_slots: List, student_groups: List):
        """Set the data for timetable generation"""
        self.courses = courses
        self.teachers = teachers
        self.classrooms = classrooms
        self.time_slots = time_slots
        self.student_groups = student_groups
        
    def generate_timetable(self) -> Dict:
        """
        Generate timetable using genetic algorithm
        
        Returns:
            Dict containing the best timetable and statistics
        """
        print("🧬 Starting Genetic Algorithm Timetable Generation...")
        print(f"📊 Population: {self.population_size}, Generations: {self.generations}")
        
        # Initialize population
        population = self._initialize_population()
        
        # Evolution loop
        for generation in range(self.generations):
            # Evaluate fitness
            population_fitness = self._evaluate_population(population)
            
            # Track statistics
            best_fitness = max(population_fitness)
            avg_fitness = sum(population_fitness) / len(population_fitness)
            self.generation_stats.append({
                'generation': generation + 1,
                'best_fitness': best_fitness,
                'avg_fitness': avg_fitness,
                'best_solution': population[population_fitness.index(best_fitness)]
            })
            self.best_fitness_history.append(best_fitness)
            
            # Print progress
            if (generation + 1) % 10 == 0:
                print(f"🔄 Generation {generation + 1}: Best={best_fitness:.2f}, Avg={avg_fitness:.2f}")
            
            # Check for convergence
            if self._check_convergence(generation):
                print(f"🎯 Convergence reached at generation {generation + 1}")
                break
            
            # Create next generation
            population = self._create_next_generation(population, population_fitness)
        
        # Get best solution
        best_solution = self._get_best_solution(population)
        best_fitness = self._evaluate_fitness(best_solution)
        
        print(f"🏆 Best solution found with fitness: {best_fitness:.2f}")
        
        return {
            'timetable': self._solution_to_timetable(best_solution),
            'fitness': best_fitness,
            'generations_completed': len(self.generation_stats),
            'statistics': self.generation_stats,
            'constraint_violations': self._count_constraint_violations(best_solution)
        }
    
    def _initialize_population(self) -> List:
        """Initialize random population of timetable solutions"""
        population = []
        
        for _ in range(self.population_size):
            solution = self._create_random_solution()
            population.append(solution)
        
        return population
    
    def _create_random_solution(self) -> List:
        """Create a random timetable solution"""
        solution = []
        
        for course in self.courses:
            # Randomly assign time slot, classroom, and teacher
            time_slot = random.choice(self.time_slots)
            classroom = random.choice(self.classrooms)
            teacher = random.choice(self.teachers)
            
            solution.append({
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
        
        return solution
    
    def _evaluate_population(self, population: List) -> List[float]:
        """Evaluate fitness for entire population"""
        return [self._evaluate_fitness(solution) for solution in population]
    
    def _evaluate_fitness(self, solution: List) -> float:
        """Calculate fitness score for a single solution"""
        fitness = 0.0
        
        # Check for hard constraints (conflicts)
        conflicts = self._count_conflicts(solution)
        if conflicts > 0:
            fitness -= conflicts * self.fitness_weights['conflicts']
            return fitness  # Early return for invalid solutions
        
        # Soft constraints (preferences and efficiency)
        teacher_pref_score = self._evaluate_teacher_preferences(solution)
        room_efficiency_score = self._evaluate_room_efficiency(solution)
        student_load_score = self._evaluate_student_load_balance(solution)
        time_distribution_score = self._evaluate_time_distribution(solution)
        
        fitness += teacher_pref_score * self.fitness_weights['teacher_preferences']
        fitness += room_efficiency_score * self.fitness_weights['room_efficiency']
        fitness += student_load_score * self.fitness_weights['student_load']
        fitness += time_distribution_score * self.fitness_weights['time_distribution']
        
        return fitness
    
    def _count_conflicts(self, solution: List) -> int:
        """Count hard constraint violations"""
        conflicts = 0
        
        # Check for double-booking (same time slot, same classroom)
        time_classroom_assignments = {}
        for assignment in solution:
            key = (assignment['time_slot_id'], assignment['classroom_id'])
            if key in time_classroom_assignments:
                conflicts += 1
            else:
                time_classroom_assignments[key] = assignment
        
        # Check for teacher conflicts (same teacher, same time)
        teacher_time_assignments = {}
        for assignment in solution:
            key = (assignment['time_slot_id'], assignment['teacher_id'])
            if key in teacher_time_assignments:
                conflicts += 1
            else:
                teacher_time_assignments[key] = assignment
        
        # Check for student group conflicts (same group, same time)
        # This would require mapping courses to student groups
        
        return conflicts
    
    def _evaluate_teacher_preferences(self, solution: List) -> float:
        """Evaluate how well teacher preferences are satisfied"""
        score = 0.0
        
        for assignment in solution:
            teacher = assignment['teacher']
            time_slot = assignment['time_slot']
            
            # Prefer morning slots (9 AM - 12 PM)
            if '09:00' <= time_slot['start_time'] <= '12:00':
                score += 1.0
            
            # Prefer consecutive time slots for same teacher
            # This is a simplified version
            
        return score / len(solution)
    
    def _evaluate_room_efficiency(self, solution: List) -> float:
        """Evaluate room utilization efficiency"""
        score = 0.0
        
        for assignment in solution:
            course = next(c for c in self.courses if c['id'] == assignment['course_id'])
            classroom = assignment['classroom']
            
            # Prefer rooms that match course requirements
            if course.get('min_capacity', 1) <= classroom.get('capacity', 50):
                score += 1.0
            
            # Prefer appropriate room types
            if course.get('subject_area') == 'Computer Science' and 'lab' in classroom.get('room_type', '').lower():
                score += 0.5
        
        return score / len(solution)
    
    def _evaluate_student_load_balance(self, solution: List) -> float:
        """Evaluate student workload distribution"""
        score = 0.0
        
        # Count courses per day for each student group
        daily_loads = {}
        
        for assignment in solution:
            day = assignment['day']
            if day not in daily_loads:
                daily_loads[day] = 0
            daily_loads[day] += 1
        
        # Prefer balanced distribution
        if daily_loads:
            max_load = max(daily_loads.values())
            min_load = min(daily_loads.values())
            balance = 1.0 - (max_load - min_load) / max_load
            score += balance
        
        return score
    
    def _evaluate_time_distribution(self, solution: List) -> float:
        """Evaluate time slot distribution"""
        score = 0.0
        
        # Count assignments per time slot
        time_slot_counts = {}
        for assignment in solution:
            time_id = assignment['time_slot_id']
            time_slot_counts[time_id] = time_slot_counts.get(time_id, 0) + 1
        
        # Prefer even distribution
        if time_slot_counts:
            avg_count = len(solution) / len(time_slot_counts)
            variance = sum((count - avg_count) ** 2 for count in time_slot_counts.values())
            score += 1.0 / (1.0 + variance)
        
        return score
    
    def _create_next_generation(self, population: List, fitness_scores: List[float]) -> List:
        """Create the next generation using selection, crossover, and mutation"""
        new_population = []
        
        # Elitism: keep best solutions
        elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)[:self.elite_size]
        for idx in elite_indices:
            new_population.append(copy.deepcopy(population[idx]))
        
        # Generate rest of population
        while len(new_population) < self.population_size:
            # Selection
            parent1 = self._tournament_selection(population, fitness_scores)
            parent2 = self._tournament_selection(population, fitness_scores)
            
            # Crossover
            if random.random() < self.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = copy.deepcopy(parent1), copy.deepcopy(parent2)
            
            # Mutation
            if random.random() < self.mutation_rate:
                child1 = self._mutate(child1)
            if random.random() < self.mutation_rate:
                child2 = self._mutate(child2)
            
            new_population.extend([child1, child2])
        
        # Trim to exact population size
        return new_population[:self.population_size]
    
    def _tournament_selection(self, population: List, fitness_scores: List[float], tournament_size: int = 3) -> List:
        """Tournament selection for choosing parents"""
        tournament_indices = random.sample(range(len(population)), tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[tournament_fitness.index(max(tournament_fitness))]
        return population[winner_idx]
    
    def _crossover(self, parent1: List, parent2: List) -> Tuple[List, List]:
        """Perform crossover between two parent solutions"""
        # Single-point crossover
        crossover_point = random.randint(1, len(parent1) - 1)
        
        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]
        
        return child1, child2
    
    def _mutate(self, solution: List) -> List:
        """Perform mutation on a solution"""
        mutated = copy.deepcopy(solution)
        
        # Random mutation: change time slot, classroom, or teacher
        mutation_type = random.choice(['time', 'classroom', 'teacher'])
        
        if mutation_type == 'time':
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx]['time_slot'] = random.choice(self.time_slots)
            mutated[idx]['time_slot_id'] = mutated[idx]['time_slot']['id']
            mutated[idx]['day'] = mutated[idx]['time_slot'].get('day', 'Monday')
            mutated[idx]['start_time'] = mutated[idx]['time_slot'].get('start_time', '09:00')
            mutated[idx]['end_time'] = mutated[idx]['time_slot'].get('end_time', '10:00')
        
        elif mutation_type == 'classroom':
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx]['classroom'] = random.choice(self.classrooms)
            mutated[idx]['classroom_id'] = mutated[idx]['classroom']['id']
        
        elif mutation_type == 'teacher':
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx]['teacher'] = random.choice(self.teachers)
            mutated[idx]['teacher_id'] = mutated[idx]['teacher']['id']
        
        return mutated
    
    def _check_convergence(self, generation: int) -> bool:
        """Check if the algorithm has converged"""
        if generation < 20:  # Need minimum generations
            return False
        
        # Check if best fitness hasn't improved in last 20 generations
        recent_fitness = self.best_fitness_history[-20:]
        if len(recent_fitness) >= 20:
            improvement = max(recent_fitness) - min(recent_fitness)
            return improvement < 0.01  # Very small improvement threshold
        
        return False
    
    def _get_best_solution(self, population: List) -> List:
        """Get the best solution from the current population"""
        fitness_scores = self._evaluate_population(population)
        best_idx = fitness_scores.index(max(fitness_scores))
        return population[best_idx]
    
    def _solution_to_timetable(self, solution: List) -> Dict:
        """Convert solution to readable timetable format"""
        timetable = {
            'assignments': [],
            'summary': {
                'total_courses': len(solution),
                'total_conflicts': self._count_conflicts(solution),
                'generation_method': 'Genetic Algorithm'
            }
        }
        
        for assignment in solution:
            timetable['assignments'].append({
                'id': len(timetable['assignments']) + 1,
                'course_id': assignment['course_id'],
                'course_name': assignment['course_name'],
                'time_slot_id': assignment['time_slot_id'],
                'classroom_id': assignment['classroom_id'],
                'teacher_id': assignment['teacher_id'],
                'day': assignment['day'],
                'start_time': assignment['start_time'],
                'end_time': assignment['end_time'],
                'classroom_name': assignment['classroom'].get('room_number', 'Unknown'),
                'teacher_name': assignment['teacher'].get('name', 'Unknown')
            })
        
        return timetable
    
    def _count_constraint_violations(self, solution: List) -> Dict:
        """Count different types of constraint violations"""
        return {
            'total_conflicts': self._count_conflicts(solution),
            'teacher_conflicts': self._count_teacher_conflicts(solution),
            'room_conflicts': self._count_room_conflicts(solution),
            'time_conflicts': self._count_time_conflicts(solution)
        }
    
    def _count_teacher_conflicts(self, solution: List) -> int:
        """Count teacher scheduling conflicts"""
        teacher_time = {}
        conflicts = 0
        
        for assignment in solution:
            key = (assignment['time_slot_id'], assignment['teacher_id'])
            if key in teacher_time:
                conflicts += 1
            else:
                teacher_time[key] = assignment
        
        return conflicts
    
    def _count_room_conflicts(self, solution: List) -> int:
        """Count room scheduling conflicts"""
        room_time = {}
        conflicts = 0
        
        for assignment in solution:
            key = (assignment['time_slot_id'], assignment['classroom_id'])
            if key in room_time:
                conflicts += 1
            else:
                room_time[key] = assignment
        
        return conflicts
    
    def _count_time_conflicts(self, solution: List) -> int:
        """Count time slot conflicts"""
        time_assignments = {}
        conflicts = 0
        
        for assignment in solution:
            time_id = assignment['time_slot_id']
            if time_id in time_assignments:
                conflicts += 1
            else:
                time_assignments[time_id] = assignment
        
        return conflicts
    
    def get_statistics(self) -> Dict:
        """Get detailed statistics about the optimization process"""
        if not self.generation_stats:
            return {}
        
        best_fitness = max(stat['best_fitness'] for stat in self.generation_stats)
        avg_fitness = sum(stat['avg_fitness'] for stat in self.generation_stats) / len(self.generation_stats)
        
        return {
            'total_generations': len(self.generation_stats),
            'best_fitness': best_fitness,
            'average_fitness': avg_fitness,
            'fitness_improvement': best_fitness - self.generation_stats[0]['best_fitness'],
            'convergence_generation': self._find_convergence_generation(),
            'generation_details': self.generation_stats
        }
    
    def _find_convergence_generation(self) -> Optional[int]:
        """Find the generation where convergence occurred"""
        if len(self.best_fitness_history) < 20:
            return None
        
        for i in range(20, len(self.best_fitness_history)):
            recent = self.best_fitness_history[i-20:i]
            if max(recent) - min(recent) < 0.01:
                return i
        
        return None
    
    def save_solution(self, solution: List, filename: str = None):
        """Save the solution to a JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"genetic_timetable_{timestamp}.json"
        
        data = {
            'solution': solution,
            'statistics': self.get_statistics(),
            'parameters': {
                'population_size': self.population_size,
                'generations': self.generations,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
                'elite_size': self.elite_size
            },
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 Solution saved to {filename}")
    
    def load_solution(self, filename: str) -> Dict:
        """Load a solution from a JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print(f"📂 Solution loaded from {filename}")
        return data


# Example usage and testing
if __name__ == "__main__":
    # Sample data for testing
    sample_courses = [
        {'id': 1, 'name': 'Mathematics 101', 'min_capacity': 30, 'subject_area': 'Mathematics'},
        {'id': 2, 'name': 'Computer Science 101', 'min_capacity': 25, 'subject_area': 'Computer Science'},
        {'id': 3, 'name': 'Physics 101', 'min_capacity': 35, 'subject_area': 'Physics'}
    ]
    
    sample_teachers = [
        {'id': 1, 'name': 'Dr. Smith', 'department': 'Mathematics'},
        {'id': 2, 'name': 'Dr. Johnson', 'department': 'Computer Science'},
        {'id': 3, 'name': 'Dr. Brown', 'department': 'Physics'}
    ]
    
    sample_classrooms = [
        {'id': 1, 'room_number': 'A101', 'capacity': 40, 'room_type': 'lecture'},
        {'id': 2, 'room_number': 'A102', 'capacity': 30, 'room_type': 'lecture'},
        {'id': 3, 'room_number': 'Lab1', 'capacity': 25, 'room_type': 'lab'}
    ]
    
    sample_time_slots = [
        {'id': 1, 'day': 'Monday', 'start_time': '09:00', 'end_time': '10:00'},
        {'id': 2, 'day': 'Monday', 'start_time': '10:00', 'end_time': '11:00'},
        {'id': 3, 'day': 'Tuesday', 'start_time': '09:00', 'end_time': '10:00'},
        {'id': 4, 'day': 'Tuesday', 'start_time': '10:00', 'end_time': '11:00'}
    ]
    
    sample_student_groups = [
        {'id': 1, 'name': 'Group A', 'size': 30},
        {'id': 2, 'name': 'Group B', 'size': 25}
    ]
    
    # Create generator instance
    generator = GeneticTimetableGenerator(
        population_size=30,
        generations=50,
        mutation_rate=0.15,
        crossover_rate=0.8,
        elite_size=3
    )
    
    # Set data
    generator.set_data(sample_courses, sample_teachers, sample_classrooms, sample_time_slots, sample_student_groups)
    
    # Generate timetable
    result = generator.generate_timetable()
    
    # Print results
    print("\n" + "="*50)
    print("🏆 FINAL RESULTS")
    print("="*50)
    print(f"Best Fitness: {result['fitness']:.2f}")
    print(f"Generations: {result['generations_completed']}")
    print(f"Conflicts: {result['constraint_violations']['total_conflicts']}")
    
    # Save solution
    generator.save_solution(result['timetable']['assignments'])
    
    # Show statistics
    stats = generator.get_statistics()
    print(f"\n📊 Optimization Statistics:")
    print(f"Fitness Improvement: {stats['fitness_improvement']:.2f}")
    if stats['convergence_generation']:
        print(f"Convergence at Generation: {stats['convergence_generation']}")
