#!/usr/bin/env python3
"""
Test script to verify Course model properties work correctly
"""

from app import app, db, Course, CourseTeacher, User

def test_course_properties():
    with app.app_context():
        # Test 1: Check if we can create a course
        print("Testing Course model properties...")
        
        # Get all courses
        courses = Course.query.all()
        print(f"Found {len(courses)} courses")
        
        for course in courses:
            print(f"\nCourse: {course.code} - {course.name}")
            print(f"  Teacher property: {course.teacher}")
            print(f"  Teacher ID property: {course.teacher_id}")
            
            # Check if there are any CourseTeacher assignments
            assignments = CourseTeacher.query.filter_by(course_id=course.id).all()
            print(f"  CourseTeacher assignments: {len(assignments)}")
            for assignment in assignments:
                print(f"    - Teacher ID: {assignment.teacher_id}, Primary: {assignment.is_primary}")

if __name__ == "__main__":
    test_course_properties() 