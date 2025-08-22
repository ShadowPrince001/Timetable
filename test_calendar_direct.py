#!/usr/bin/env python3
"""
Direct Test of Calendar Functions
Directly tests calendar functions with specific dates.
"""

from app import app, db
from datetime import date, timedelta
from app import ClassInstance, Timetable, User

def test_calendar_direct():
    """Directly test calendar functions"""
    print("🧪 Direct Test of Calendar Functions")
    print("=" * 45)
    
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
            
            # Directly test class instances for the test date
            print(f"\n🔍 Direct Test for {test_date}:")
            
            # Get class instances for the test date
            test_instances = ClassInstance.query.filter_by(class_date=test_date).all()
            print(f"\n1. Class Instances for {test_date}: {len(test_instances)}")
            
            for instance in test_instances:
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    print(f"   - {timetable.course.name} at {timetable.time_slot.start_time}-{timetable.time_slot.end_time}")
                    print(f"     Teacher: {timetable.teacher.name if timetable.teacher else 'Not assigned'}")
                    print(f"     Group: {timetable.student_group.name if timetable.student_group else 'Not assigned'}")
            
            # Test student-specific classes
            print(f"\n2. Student Classes for {test_date}:")
            students = User.query.filter_by(role='student').limit(2).all()
            
            for student in students:
                print(f"\n   👤 {student.name}:")
                if student.group_id:
                    # Get classes for this student's group on the test date
                    student_instances = ClassInstance.query.join(Timetable).filter(
                        ClassInstance.class_date == test_date,
                        Timetable.student_group_id == student.group_id
                    ).all()
                    
                    print(f"      Classes: {len(student_instances)}")
                    for instance in student_instances:
                        timetable = instance.timetable
                        if timetable and timetable.course and timetable.time_slot:
                            print(f"      - {timetable.course.name} ({timetable.time_slot.start_time}-{timetable.time_slot.end_time})")
                else:
                    print(f"      No group assigned")
            
            # Test faculty-specific classes
            print(f"\n3. Faculty Classes for {test_date}:")
            faculty = User.query.filter_by(role='faculty').limit(2).all()
            
            for teacher in faculty:
                print(f"\n   👨‍🏫 {teacher.name}:")
                # Get classes taught by this faculty on the test date
                faculty_instances = ClassInstance.query.join(Timetable).filter(
                    ClassInstance.class_date == test_date,
                    Timetable.teacher_id == teacher.id
                ).all()
                
                print(f"      Classes: {len(faculty_instances)}")
                for instance in faculty_instances:
                    timetable = instance.timetable
                    if timetable and timetable.course and timetable.time_slot:
                        print(f"      - {timetable.course.name} ({timetable.time_slot.start_time}-{timetable.time_slot.end_time})")
                        print(f"        Group: {timetable.student_group.name if timetable.student_group else 'Not assigned'}")
            
            print("\n✅ Direct calendar test completed!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_calendar_direct()
