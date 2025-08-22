#!/usr/bin/env python3
"""
Debug script to test the attendance system and identify issues
Run this script to check database connectivity, models, and data
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Course, TimeSlot, QRCode, Attendance, CourseTeacher

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing database connection...")
    try:
        with app.app_context():
            # Test basic query
            user_count = User.query.count()
            print(f"✅ Database connection successful. Found {user_count} users.")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_models():
    """Test if all required models are accessible"""
    print("\n🔍 Testing database models...")
    try:
        with app.app_context():
            models = {
                'User': User,
                'Course': Course,
                'TimeSlot': TimeSlot,
                'QRCode': QRCode,
                'Attendance': Attendance,
                'CourseTeacher': CourseTeacher
            }
            
            for name, model in models.items():
                try:
                    count = model.query.count()
                    print(f"✅ {name}: {count} records")
                except Exception as e:
                    print(f"❌ {name}: Error - {e}")
            
            return True
    except Exception as e:
        print(f"❌ Model testing failed: {e}")
        return False

def test_faculty_data():
    """Test faculty and course data"""
    print("\n🔍 Testing faculty and course data...")
    try:
        with app.app_context():
            # Check faculty users
            faculty_users = User.query.filter_by(role='faculty').all()
            print(f"✅ Found {len(faculty_users)} faculty users")
            
            for faculty in faculty_users:
                print(f"   - {faculty.name} (ID: {faculty.id})")
                
                # Check course assignments
                assignments = CourseTeacher.query.filter_by(teacher_id=faculty.id).all()
                print(f"     Course assignments: {len(assignments)}")
                
                for assignment in assignments:
                    course = Course.query.get(assignment.course_id)
                    if course:
                        print(f"       - {course.code}: {course.name}")
                    else:
                        print(f"       - Course ID {assignment.course_id} not found!")
            
            # Check all courses
            all_courses = Course.query.all()
            print(f"\n✅ Total courses in system: {len(all_courses)}")
            for course in all_courses:
                print(f"   - {course.code}: {course.name}")
            
            return True
    except Exception as e:
        print(f"❌ Faculty data testing failed: {e}")
        return False

def test_time_slots():
    """Test time slot data"""
    print("\n🔍 Testing time slot data...")
    try:
        with app.app_context():
            time_slots = TimeSlot.query.all()
            print(f"✅ Found {len(time_slots)} time slots")
            
            for slot in time_slots:
                print(f"   - {slot.day} {slot.start_time}-{slot.end_time} (ID: {slot.id})")
            
            return True
    except Exception as e:
        print(f"❌ Time slot testing failed: {e}")
        return False

def test_qr_codes():
    """Test QR code functionality"""
    print("\n🔍 Testing QR code functionality...")
    try:
        with app.app_context():
            qr_codes = QRCode.query.all()
            print(f"✅ Found {len(qr_codes)} QR codes")
            
            for qr in qr_codes:
                user = User.query.get(qr.user_id)
                user_name = user.name if user else "Unknown User"
                print(f"   - {qr.qr_code_hash[:8]}... for {user_name} (ID: {qr.id})")
            
            return True
    except Exception as e:
        print(f"❌ QR code testing failed: {e}")
        return False

def test_attendance_system():
    """Test attendance system"""
    print("\n🔍 Testing attendance system...")
    try:
        with app.app_context():
            # Check existing attendance records
            attendance_records = Attendance.query.all()
            print(f"✅ Found {len(attendance_records)} attendance records")
            
            # Check attendance model structure
            if attendance_records:
                sample = attendance_records[0]
                print(f"   Sample attendance record:")
                print(f"     - Student ID: {sample.student_id}")
                print(f"     - Course ID: {sample.course_id}")
                print(f"     - Time Slot ID: {sample.time_slot_id}")
                print(f"     - Date: {sample.date}")
                print(f"     - Status: {sample.status}")
            
            return True
    except Exception as e:
        print(f"❌ Attendance system testing failed: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Attendance System Debug Tool")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Run tests
    tests = [
        test_database_connection,
        test_models,
        test_faculty_data,
        test_time_slots,
        test_qr_codes,
        test_attendance_system
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! The system appears to be working correctly.")
        print("💡 If you're still having issues, check the browser console for JavaScript errors.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above for details.")
        print("💡 Common issues:")
        print("   - Database not properly initialized")
        print("   - Missing sample data")
        print("   - Model relationship issues")
        print("   - Database connection problems")

if __name__ == "__main__":
    main()
