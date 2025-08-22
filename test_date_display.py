#!/usr/bin/env python3
"""
Test script to verify date display functionality in the current system.
This script tests the calendar utilities and template data structures.
"""

import sys
import os
from datetime import date, datetime, timedelta

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
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
    # Models are defined in app.py
    from app import User, AcademicYear, AcademicSession, Holiday, ClassInstance, Timetable
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_date_display():
    """Test date display functionality"""
    print("🔍 Testing Date Display Functionality")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Test 1: Active Academic Year
            print("\n1. Testing Active Academic Year:")
            active_year = get_active_academic_year()
            if active_year:
                print(f"   ✅ Active Year: {active_year.name}")
                print(f"   📅 Start Date: {active_year.start_date.strftime('%B %d, %Y')}")
                print(f"   📅 End Date: {active_year.end_date.strftime('%B %d, %Y')}")
            else:
                print("   ❌ No active academic year found")
            
            # Test 2: Today's Date
            print(f"\n2. Testing Today's Date:")
            today = date.today()
            print(f"   📅 Today: {today.strftime('%A, %B %d, %Y')}")
            print(f"   📅 Short format: {today.strftime('%b %d')}")
            print(f"   📅 ISO format: {today.strftime('%Y-%m-%d')}")
            
            # Test 3: Today's Classes
            print(f"\n3. Testing Today's Classes:")
            today_classes = get_today_classes()
            print(f"   📊 Total classes today: {len(today_classes)}")
            for i, class_info in enumerate(today_classes, 1):
                print(f"   {i}. {class_info['course_name']} ({class_info['course_code']})")
                print(f"      Time: {class_info['start_time']} - {class_info['end_time']}")
                print(f"      Classroom: {class_info['classroom']}")
            
            # Test 4: Upcoming Classes
            print(f"\n4. Testing Upcoming Classes:")
            upcoming_classes = get_upcoming_classes(7)
            print(f"   📊 Total upcoming classes (next 7 days): {len(upcoming_classes)}")
            for i, class_info in enumerate(upcoming_classes[:5], 1):  # Show first 5
                print(f"   {i}. {class_info['date'].strftime('%b %d')} ({class_info['day_name']})")
                print(f"      {class_info['course_name']} ({class_info['course_code']})")
                print(f"      Time: {class_info['start_time']} - {class_info['end_time']}")
                if class_info['is_holiday']:
                    print(f"      🏖️ Holiday: {class_info.get('holiday_description', 'Holiday')}")
            
            # Test 5: Holiday Check
            print(f"\n5. Testing Holiday Check:")
            for i in range(7):
                test_date = today + timedelta(days=i)
                if is_holiday(test_date):
                    holiday = get_holiday_for_date(test_date)
                    print(f"   🏖️ {test_date.strftime('%b %d')} ({test_date.strftime('%A')}): {holiday.name}")
                else:
                    print(f"   📅 {test_date.strftime('%b %d')} ({test_date.strftime('%A')}): Regular day")
            
            # Test 6: Student/Faculty Specific Classes
            print(f"\n6. Testing User-Specific Classes:")
            
            # Find a student
            student = User.query.filter_by(role='student').first()
            if student:
                print(f"   👨‍🎓 Testing for student: {student.name}")
                student_classes = get_student_today_classes(student.id)
                print(f"   📊 Student classes today: {len(student_classes)}")
                for class_info in student_classes:
                    print(f"      - {class_info['course_name']} ({class_info['course_code']})")
                    print(f"        Time: {class_info['start_time']} - {class_info['end_time']}")
                    print(f"        Teacher: {class_info['teacher']}")
            
            # Find a faculty member
            faculty = User.query.filter_by(role='faculty').first()
            if faculty:
                print(f"   👨‍🏫 Testing for faculty: {faculty.name}")
                faculty_classes = get_faculty_today_classes(faculty.id)
                print(f"   📊 Faculty classes today: {len(faculty_classes)}")
                for class_info in faculty_classes:
                    print(f"      - {class_info['course_name']} ({class_info['course_code']})")
                    print(f"        Time: {class_info['start_time']} - {class_info['end_time']}")
                    print(f"        Group: {class_info['student_group']}")
            
            # Test 7: Template Data Structure Validation
            print(f"\n7. Testing Template Data Structures:")
            
            # Test today_classes structure
            if today_classes:
                sample_class = today_classes[0]
                print(f"   📋 Today's class structure:")
                print(f"      Keys: {list(sample_class.keys())}")
                print(f"      Course: {sample_class.get('course_name', 'N/A')}")
                print(f"      Time: {sample_class.get('start_time', 'N/A')} - {sample_class.get('end_time', 'N/A')}")
            
            # Test upcoming_classes structure
            if upcoming_classes:
                sample_upcoming = upcoming_classes[0]
                print(f"   📋 Upcoming class structure:")
                print(f"      Keys: {list(sample_upcoming.keys())}")
                print(f"      Date: {sample_upcoming.get('date', 'N/A')}")
                print(f"      Day: {sample_upcoming.get('day_name', 'N/A')}")
                print(f"      Course: {sample_upcoming.get('course_name', 'N/A')}")
            
            print(f"\n✅ Date display testing completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_date_display()
