#!/usr/bin/env python3
"""
Test Calendar System
Tests the calendar-based timetable and attendance system.
"""

from app import app, db
from calendar_utils import (
    get_active_academic_year,
    get_today_classes,
    get_student_today_classes,
    get_faculty_today_classes,
    get_upcoming_classes,
    is_holiday,
    get_holiday_for_date
)
from datetime import date, datetime
from app import User, AcademicYear, AcademicSession, Holiday, ClassInstance, Timetable

def test_calendar_system():
    """Test the calendar-based system functionality"""
    print("🧪 Testing Calendar-Based System")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Test 1: Check active academic year
            print("\n1. Testing Active Academic Year:")
            active_year = get_active_academic_year()
            if active_year:
                print(f"   ✅ Active Year: {active_year.name}")
                print(f"   📅 Period: {active_year.start_date} to {active_year.end_date}")
            else:
                print("   ❌ No active academic year found")
            
            # Test 2: Check today's classes
            print("\n2. Testing Today's Classes:")
            today_classes = get_today_classes()
            print(f"   📚 Total classes today: {len(today_classes)}")
            for i, class_info in enumerate(today_classes, 1):
                print(f"   {i}. {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
            
            # Test 3: Check student classes
            print("\n3. Testing Student Classes:")
            students = User.query.filter_by(role='student').limit(3).all()
            for student in students:
                student_classes = get_student_today_classes(student.id)
                print(f"   👤 {student.name}: {len(student_classes)} classes today")
                for class_info in student_classes:
                    print(f"      - {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
            
            # Test 4: Check faculty classes
            print("\n4. Testing Faculty Classes:")
            faculty = User.query.filter_by(role='faculty').limit(3).all()
            for teacher in faculty:
                faculty_classes = get_faculty_today_classes(teacher.id)
                print(f"   👨‍🏫 {teacher.name}: {len(faculty_classes)} classes today")
                for class_info in faculty_classes:
                    print(f"      - {class_info['course_name']} ({class_info['start_time']}-{class_info['end_time']})")
            
            # Test 5: Check upcoming classes
            print("\n5. Testing Upcoming Classes:")
            upcoming = get_upcoming_classes(7)
            print(f"   📅 Upcoming classes (next 7 days): {len(upcoming)}")
            
            # Count holidays
            holidays = [c for c in upcoming if c.get('is_holiday')]
            print(f"   🏖️  Holidays in next 7 days: {len(holidays)}")
            
            # Test 6: Check holiday detection
            print("\n6. Testing Holiday Detection:")
            today = date.today()
            is_today_holiday = is_holiday(today)
            print(f"   📅 Today ({today}) is holiday: {is_today_holiday}")
            
            if is_today_holiday:
                holiday_info = get_holiday_for_date(today)
                if holiday_info:
                    print(f"   🎉 Holiday: {holiday_info.name}")
                    print(f"   📝 Description: {holiday_info.description}")
            
            # Test 7: Check class instances
            print("\n7. Testing Class Instances:")
            today_instances = ClassInstance.query.filter_by(class_date=today).all()
            print(f"   📚 Class instances today: {len(today_instances)}")
            
            for instance in today_instances[:3]:  # Show first 3
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    print(f"      - {timetable.course.name} at {timetable.time_slot.start_time}-{timetable.time_slot.end_time}")
            
            print("\n✅ Calendar system test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error testing calendar system: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_calendar_system()
