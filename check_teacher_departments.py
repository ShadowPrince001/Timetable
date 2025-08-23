#!/usr/bin/env python3
"""
Check teacher departments vs course departments to identify mismatches
"""

import os
from sqlalchemy import create_engine, text

def check_teacher_course_departments():
    """Check teacher and course department mismatches"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Get all teachers
            print("🔍 Checking teacher departments...")
            result = conn.execute(text('SELECT id, name, department FROM "user" WHERE role = \'faculty\' ORDER BY department, name'))
            teachers = result.fetchall()
            
            teacher_departments = set()
            for teacher in teachers:
                teacher_departments.add(teacher.department)
                print(f"   👨‍🏫 {teacher.name}: {teacher.department}")
            
            print(f"\n📊 Unique teacher departments: {teacher_departments}")
            
            # Get all courses
            print("\n🔍 Checking course departments...")
            result = conn.execute(text("SELECT id, code, name, department FROM course ORDER BY department, code"))
            courses = result.fetchall()
            
            course_departments = set()
            for course in courses:
                course_departments.add(course.department)
                print(f"   📚 {course.code}: {course.name} ({course.department})")
            
            print(f"\n📊 Unique course departments: {course_departments}")
            
            # Check for mismatches
            print("\n🔍 Checking for department mismatches...")
            missing_departments = course_departments - teacher_departments
            if missing_departments:
                print(f"❌ Courses exist for departments with no teachers: {missing_departments}")
                
                for dept in missing_departments:
                    dept_courses = [c for c in courses if c.department == dept]
                    print(f"   📚 Department {dept} has {len(dept_courses)} courses but no teachers:")
                    for course in dept_courses:
                        print(f"     - {course.code}: {course.name}")
            else:
                print("✅ All course departments have corresponding teachers")
            
            # Check specific examples
            print("\n🔍 Checking specific examples...")
            
            # Check Math courses
            math_courses = [c for c in courses if c.department == 'Mathematics']
            if math_courses:
                print(f"   📚 Math courses ({len(math_courses)}):")
                for course in math_courses:
                    print(f"     - {course.code}: {course.name}")
                
                math_teachers = [t for t in teachers if t.department == 'Mathematics']
                if math_teachers:
                    print(f"   👨‍🏫 Math teachers ({len(math_teachers)}):")
                    for teacher in math_teachers:
                        print(f"     - {teacher.name}")
                else:
                    print("   ❌ No Math teachers found!")
            
            # Check Physics courses
            physics_courses = [c for c in courses if c.department == 'Physics']
            if physics_courses:
                print(f"   📚 Physics courses ({len(physics_courses)}):")
                for course in physics_courses:
                    print(f"     - {course.code}: {course.name}")
                
                physics_teachers = [t for t in teachers if t.department == 'Physics']
                if physics_teachers:
                    print(f"   👨‍🏫 Physics teachers ({len(physics_teachers)}):")
                    for teacher in physics_teachers:
                        print(f"     - {teacher.name}")
                else:
                    print("   ❌ No Physics teachers found!")
            
            # Check Chemistry courses
            chemistry_courses = [c for c in courses if c.department == 'Chemistry']
            if chemistry_courses:
                print(f"   📚 Chemistry courses ({len(chemistry_courses)}):")
                for course in chemistry_courses:
                    print(f"     - {course.code}: {course.name}")
                
                chemistry_teachers = [t for t in teachers if t.department == 'Chemistry']
                if chemistry_teachers:
                    print(f"   👨‍🏫 Chemistry teachers ({len(chemistry_teachers)}):")
                    for teacher in chemistry_teachers:
                        print(f"     - {teacher.name}")
                else:
                    print("   ❌ No Chemistry teachers found!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking departments: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Teacher-Course Department Mismatch Check")
    print("=" * 50)
    
    success = check_teacher_course_departments()
    
    if success:
        print("\n✅ Department check completed successfully!")
    else:
        print("\n❌ Department check failed!")
