#!/usr/bin/env python3
"""
Test Calendar System with Specific Date
Tests the calendar system with a specific date that has classes.
"""

from app import app, db
from calendar_utils import (
    get_today_classes,
    get_student_today_classes,
    get_faculty_today_classes,
    get_upcoming_classes
)
from datetime import date, timedelta
from app import ClassInstance, Timetable

def test_specific_date():
    """Test the calendar system with a specific date"""
    print("🧪 Testing Calendar System with Specific Date")
    print("=" * 55)
    
    with app.app_context():
        try:
            # Find a date that has classes (Monday, Tuesday, or Wednesday)
            today = date.today()
            print(f"📅 Today: {today} ({today.strftime('%A')})")
            
            # Find the next Monday
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, go to next Monday
            
            test_date = today + timedelta(days=days_until_monday)
            print(f"📅 Test date: {test_date} ({test_date.strftime('%A')})")
            
            # Generate class instances for this date
            from calendar_utils import generate_class_instances_for_timetable
            
            timetables = Timetable.query.all()
            total_generated = 0
            
            for timetable in timetables:
                generated = generate_class_instances_for_timetable(
                    timetable.id, 
                    test_date, 
                    test_date
                )
                if generated > 0:
                    print(f"   ✅ Generated {generated} instances for {timetable.course.name}")
                    total_generated += generated
            
            print(f"\n📊 Total instances generated for {test_date}: {total_generated}")
            
            # Test the calendar functions with this date
            print(f"\n🔍 Testing Calendar Functions for {test_date}:")
            
            # Temporarily override date.today() for testing
            import calendar_utils
            original_date_today = calendar_utils.date.today
            
            def mock_date_today():
                return test_date
            
            calendar_utils.date.today = mock_date_today
            
            try:
                # Test today's classes
                today_classes = get_today_classes()
                print(f"\n1. Today's Classes: {len(today_classes)}")
                for class_info in today_classes:
                    print(f"   - {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
                
                # Test student classes
                from app import User
                students = User.query.filter_by(role='student').limit(2).all()
                for student in students:
                    student_classes = get_student_today_classes(student.id)
                    print(f"\n2. {student.name}'s Classes: {len(student_classes)}")
                    for class_info in student_classes:
                        print(f"   - {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
                
                # Test faculty classes
                faculty = User.query.filter_by(role='faculty').limit(2).all()
                for teacher in faculty:
                    faculty_classes = get_faculty_today_classes(teacher.id)
                    print(f"\n3. {teacher.name}'s Classes: {len(faculty_classes)}")
                    for class_info in faculty_classes:
                        print(f"   - {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
                
                # Test upcoming classes
                upcoming = get_upcoming_classes(7)
                print(f"\n4. Upcoming Classes (next 7 days): {len(upcoming)}")
                
            finally:
                # Restore original date.today function
                calendar_utils.date.today = original_date_today
            
            print("\n✅ Calendar system test with specific date completed!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_specific_date()
