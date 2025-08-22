#!/usr/bin/env python3
"""
Check Timetables and Generate Class Instances
Checks existing timetables and generates class instances for testing.
"""

from app import app, db
from calendar_utils import generate_class_instances_for_timetable
from datetime import date, timedelta
from app import Timetable, ClassInstance, AcademicSession

def check_and_generate_classes():
    """Check timetables and generate class instances for testing"""
    print("🔍 Checking Timetables and Generating Class Instances")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check existing timetables
            print("\n1. Checking Existing Timetables:")
            timetables = Timetable.query.all()
            print(f"   📚 Total timetables: {len(timetables)}")
            
            for i, timetable in enumerate(timetables, 1):
                print(f"   {i}. {timetable.course.name if timetable.course else 'Unknown Course'}")
                print(f"      - Time: {timetable.time_slot.day} {timetable.time_slot.start_time}-{timetable.time_slot.end_time}")
                print(f"      - Teacher: {timetable.teacher.name if timetable.teacher else 'Not assigned'}")
                print(f"      - Group: {timetable.student_group.name if timetable.student_group else 'Not assigned'}")
                print(f"      - Session: {timetable.session_rel.name if timetable.session_rel else 'Not assigned'}")
            
            # Check academic sessions
            print("\n2. Checking Academic Sessions:")
            sessions = AcademicSession.query.all()
            print(f"   📅 Total sessions: {len(sessions)}")
            
            for session in sessions:
                print(f"   - {session.name}: {session.start_date} to {session.end_date}")
            
            # Check existing class instances
            print("\n3. Checking Existing Class Instances:")
            instances = ClassInstance.query.all()
            print(f"   📚 Total class instances: {len(instances)}")
            
            # Generate class instances for the next 30 days for testing
            print("\n4. Generating Class Instances for Testing:")
            today = date.today()
            end_date = today + timedelta(days=30)
            
            total_generated = 0
            for timetable in timetables:
                if timetable.session_rel:
                    generated = generate_class_instances_for_timetable(
                        timetable.id, 
                        today, 
                        end_date
                    )
                    if generated > 0:
                        print(f"   ✅ Generated {generated} instances for {timetable.course.name}")
                        total_generated += generated
            
            print(f"\n   📊 Total instances generated: {total_generated}")
            
            # Check instances for today
            today_instances = ClassInstance.query.filter_by(class_date=today).all()
            print(f"\n5. Class Instances for Today ({today}):")
            print(f"   📚 Total: {len(today_instances)}")
            
            for instance in today_instances:
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    print(f"   - {timetable.course.name} at {timetable.time_slot.start_time}-{timetable.time_slot.end_time}")
            
            print("\n✅ Timetable check and generation completed!")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_and_generate_classes()
