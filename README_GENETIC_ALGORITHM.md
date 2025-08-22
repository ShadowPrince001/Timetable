# 🧬 Genetic Algorithm Timetable Generator

A sophisticated timetable optimization system using evolutionary algorithms to create high-quality academic schedules.

## 🚀 **Quick Start**

### **1. Basic Usage**
```python
from genetic_timetable_generator import GeneticTimetableGenerator

# Create generator
generator = GeneticTimetableGenerator(
    population_size=50,      # Number of solutions per generation
    generations=100,         # Maximum generations to evolve
    mutation_rate=0.1,       # Probability of mutation
    crossover_rate=0.8,      # Probability of crossover
    elite_size=5             # Best solutions to preserve
)

# Set your data
generator.set_data(courses, teachers, classrooms, time_slots, student_groups)

# Generate timetable
result = generator.generate_timetable()

# Access results
timetable = result['timetable']
fitness = result['fitness']
conflicts = result['constraint_violations']['total_conflicts']
```

### **2. Run Comparison**
```bash
python timetable_algorithm_comparison.py
```

This will compare greedy vs genetic algorithms and show you the differences.

## 📊 **Algorithm Comparison**

| Feature | Greedy Algorithm | Genetic Algorithm |
|---------|------------------|-------------------|
| **Speed** | ⭐⭐⭐⭐⭐ (Seconds) | ⭐⭐⭐ (Minutes) |
| **Quality** | ⭐⭐ (Basic) | ⭐⭐⭐⭐⭐ (Excellent) |
| **Constraints** | ⭐⭐ (Simple) | ⭐⭐⭐⭐⭐ (Complex) |
| **Scalability** | ⭐⭐⭐ (Small-Medium) | ⭐⭐⭐⭐⭐ (Large) |
| **Reliability** | ⭐⭐⭐⭐ (Predictable) | ⭐⭐⭐ (Variable) |

## 🎯 **When to Use Each Algorithm**

### **Use Greedy Algorithm When:**
- ⚡ **Speed is critical** (real-time generation needed)
- 📚 **Simple constraints** (basic time/room conflicts only)
- 🔢 **Small-medium datasets** (< 100 courses)
- 🧪 **Development/testing** phase
- 💻 **Limited computational resources**

### **Use Genetic Algorithm When:**
- 🎯 **Solution quality matters** (academic/research institution)
- 🔒 **Complex constraints** (faculty preferences, student load balancing)
- 📊 **Medium-large datasets** (100-1000 courses)
- ⏰ **Can afford minutes of processing time**
- 🏆 **Need consistent, high-quality results**

## ⚙️ **Configuration Options**

### **Population Size**
```python
# Small dataset (fast, less optimal)
generator = GeneticTimetableGenerator(population_size=20, generations=30)

# Medium dataset (balanced)
generator = GeneticTimetableGenerator(population_size=50, generations=100)

# Large dataset (slow, very optimal)
generator = GeneticTimetableGenerator(population_size=100, generations=200)
```

### **Mutation & Crossover Rates**
```python
# Conservative (stable evolution)
generator = GeneticTimetableGenerator(
    mutation_rate=0.05,    # Low mutation
    crossover_rate=0.9     # High crossover
)

# Aggressive (fast exploration)
generator = GeneticTimetableGenerator(
    mutation_rate=0.2,     # High mutation
    crossover_rate=0.6     # Lower crossover
)

# Balanced (recommended)
generator = GeneticTimetableGenerator(
    mutation_rate=0.1,     # Medium mutation
    crossover_rate=0.8     # High crossover
)
```

## 🔧 **Advanced Features**

### **1. Custom Fitness Weights**
```python
# Modify fitness evaluation priorities
generator.fitness_weights = {
    'conflicts': 100.0,           # Hard constraint - must be 0
    'teacher_preferences': 15.0,  # Increase teacher preference weight
    'room_efficiency': 8.0,       # Increase room efficiency weight
    'student_load': 12.0,         # Increase student load balance weight
    'time_distribution': 5.0      # Time slot distribution
}
```

### **2. Save/Load Solutions**
```python
# Save best solution
generator.save_solution(result['timetable']['assignments'], 'my_timetable.json')

# Load previous solution
loaded_data = generator.load_solution('my_timetable.json')
```

### **3. Detailed Statistics**
```python
# Get optimization statistics
stats = generator.get_statistics()
print(f"Best Fitness: {stats['best_fitness']}")
print(f"Generations: {stats['total_generations']}")
print(f"Convergence: {stats['convergence_generation']}")
print(f"Improvement: {stats['fitness_improvement']}")
```

## 📈 **Performance Optimization Tips**

### **1. Dataset Size Guidelines**
- **< 50 courses**: Use greedy algorithm
- **50-200 courses**: Use genetic algorithm with `population_size=30-50`
- **200-500 courses**: Use genetic algorithm with `population_size=50-100`
- **> 500 courses**: Use genetic algorithm with `population_size=100+`

### **2. Constraint Complexity**
- **Simple**: Basic time/room conflicts only
- **Medium**: Teacher preferences, room types
- **Complex**: Student load balancing, subject clustering, consecutive preferences

### **3. Time Budget**
- **< 1 minute**: Use greedy algorithm
- **1-5 minutes**: Use genetic algorithm with `generations=50-100`
- **5-15 minutes**: Use genetic algorithm with `generations=100-200`
- **> 15 minutes**: Use genetic algorithm with `generations=200+`

## 🧪 **Testing & Validation**

### **1. Run Sample Test**
```bash
python genetic_timetable_generator.py
```

### **2. Run Full Comparison**
```bash
python timetable_algorithm_comparison.py
```

### **3. Custom Data Testing**
```python
# Create your own test data
my_courses = [
    {'id': 1, 'name': 'Math 101', 'min_capacity': 30, 'subject_area': 'Mathematics'},
    # ... more courses
]

my_teachers = [
    {'id': 1, 'name': 'Dr. Smith', 'department': 'Mathematics'},
    # ... more teachers
]

# Test with your data
generator.set_data(my_courses, my_teachers, my_classrooms, my_time_slots, my_student_groups)
result = generator.generate_timetable()
```

## 📊 **Output Format**

### **Timetable Structure**
```json
{
  "timetable": {
    "assignments": [
      {
        "id": 1,
        "course_id": 1,
        "course_name": "Mathematics 101",
        "time_slot_id": 1,
        "classroom_id": 1,
        "teacher_id": 1,
        "day": "Monday",
        "start_time": "09:00",
        "end_time": "10:00",
        "classroom_name": "A101",
        "teacher_name": "Dr. Smith"
      }
    ],
    "summary": {
      "total_courses": 8,
      "total_conflicts": 0,
      "generation_method": "Genetic Algorithm"
    }
  },
  "fitness": 85.67,
  "generations_completed": 47,
  "constraint_violations": {
    "total_conflicts": 0,
    "teacher_conflicts": 0,
    "room_conflicts": 0,
    "time_conflicts": 0
  }
}
```

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Slow Performance**
```python
# Reduce population size and generations
generator = GeneticTimetableGenerator(
    population_size=20,    # Smaller population
    generations=30         # Fewer generations
)
```

#### **2. Poor Quality Results**
```python
# Increase population size and generations
generator = GeneticTimetableGenerator(
    population_size=100,   # Larger population
    generations=200        # More generations
)
```

#### **3. No Convergence**
```python
# Adjust mutation and crossover rates
generator = GeneticTimetableGenerator(
    mutation_rate=0.2,     # Higher mutation
    crossover_rate=0.6     # Lower crossover
)
```

#### **4. Memory Issues**
```python
# Reduce population size
generator = GeneticTimetableGenerator(population_size=20)
```

## 🎓 **Academic Applications**

### **1. University Timetabling**
- Course scheduling across multiple departments
- Faculty workload balancing
- Student group management
- Room utilization optimization

### **2. School Scheduling**
- Class period allocation
- Teacher assignment optimization
- Subject clustering
- Break time management

### **3. Corporate Training**
- Workshop scheduling
- Trainer availability
- Room capacity planning
- Participant grouping

## 🔬 **Research & Development**

### **1. Algorithm Improvements**
- Implement multi-objective optimization
- Add constraint satisfaction algorithms
- Integrate machine learning for preference learning
- Develop hybrid approaches

### **2. Performance Analysis**
- Benchmark against other algorithms
- Analyze scalability characteristics
- Study convergence patterns
- Measure solution quality metrics

### **3. Custom Extensions**
- Add new constraint types
- Implement different selection methods
- Create specialized mutation operators
- Develop domain-specific fitness functions

## 📚 **Further Reading**

- **Genetic Algorithms**: Holland, J. H. (1975). Adaptation in Natural and Artificial Systems
- **Timetabling**: Burke, E. K., & Petrovic, S. (2002). Recent research directions in automated timetabling
- **Constraint Satisfaction**: Rossi, F., van Beek, P., & Walsh, T. (2006). Handbook of Constraint Programming
- **Multi-objective Optimization**: Deb, K. (2001). Multi-Objective Optimization Using Evolutionary Algorithms

## 🤝 **Contributing**

Feel free to contribute improvements:
- Bug fixes
- Performance optimizations
- New constraint types
- Additional algorithms
- Documentation improvements

## 📄 **License**

This project is open source and available under the MIT License.

---

**Happy Timetabling! 🎯📅**
