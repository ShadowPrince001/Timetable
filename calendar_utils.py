#!/usr/bin/env python3
"""
Calendar Utility Functions
Provides utility functions for calendar-based operations in the timetable system.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
# Import models and db from current_app to avoid circular imports
from flask import current_app
from flask_sqlalchemy import SQLAlchemy

def get_active_academic_year() -> Optional['AcademicYear']:
    """Get the currently active academic year"""
    from app import AcademicYear
    return AcademicYear.query.filter_by(is_active=True).first()

def get_academic_session_for_date(target_date: date) -> Optional['AcademicSession']:
    """Get the academic session for a specific date"""
    from app import AcademicSession
    active_year = get_active_academic_year()
    if not active_year:
        return None
    
    return AcademicSession.query.filter(
        AcademicSession.academic_year_id == active_year.id,
        AcademicSession.start_date <= target_date,
        AcademicSession.end_date >= target_date
    ).first()

def is_holiday(target_date: date) -> bool:
    """Check if a specific date is a holiday"""
    from app import Holiday
    active_year = get_active_academic_year()
    if not active_year:
        return False
    
    holiday = Holiday.query.filter(
        Holiday.academic_year_id == active_year.id,
        Holiday.start_date <= target_date,
        Holiday.end_date >= target_date
    ).first()
    
    return holiday is not None

def get_holiday_for_date(target_date: date) -> Optional['Holiday']:
    """Get the holiday for a specific date if it exists"""
    from app import Holiday
    active_year = get_active_academic_year()
    if not active_year:
        return None
    
    return Holiday.query.filter(
        Holiday.academic_year_id == active_year.id,
        Holiday.start_date <= target_date,
        Holiday.end_date >= target_date
    ).first()

def is_weekend(target_date: date) -> bool:
    """Check if a date falls on a weekend"""
    return target_date.weekday() >= 5  # Saturday = 5, Sunday = 6

def is_valid_class_date(target_date: date) -> bool:
    """Check if a date is valid for classes (not weekend or holiday)"""
    return not is_weekend(target_date) and not is_holiday(target_date)

def get_class_instances_for_date(target_date: date) -> List['ClassInstance']:
    """Get all class instances for a specific date"""
    from app import ClassInstance
    return ClassInstance.query.filter_by(class_date=target_date).all()

def get_timetables_for_session(session_id: int) -> List['Timetable']:
    """Get all timetables for a specific academic session"""
    from app import Timetable
    return Timetable.query.filter_by(session_id=session_id).all()

def generate_class_instances_for_timetable(timetable_id: int, start_date: date, end_date: date) -> int:
    """Generate class instances for a specific timetable within a date range"""
    from app import Timetable, ClassInstance, db
    timetable = Timetable.query.get(timetable_id)
    if not timetable:
        return 0
    
    # Get the time slot to determine the day of week
    time_slot = timetable.time_slot
    if not time_slot:
        return 0
    
    # Map day names to weekday numbers (Monday=0, Sunday=6)
    day_mapping = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    weekday = day_mapping.get(time_slot.day)
    if weekday is None:
        return 0
    
    instances_created = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Check if this date falls on the correct weekday
        if current_date.weekday() == weekday:
            # Check if this date is valid for classes
            if is_valid_class_date(current_date):
                # Check if class instance already exists
                existing_instance = ClassInstance.query.filter_by(
                    timetable_id=timetable_id,
                    class_date=current_date
                ).first()
                
                if not existing_instance:
                    # Create class instance
                    class_instance = ClassInstance(
                        timetable_id=timetable_id,
                        class_date=current_date
                    )
                    db.session.add(class_instance)
                    instances_created += 1
        
        current_date += timedelta(days=1)
    
    if instances_created > 0:
        db.session.commit()
    
    return instances_created

def get_date_range_for_session(session_id: int) -> Tuple[date, date]:
    """Get the start and end dates for a specific session"""
    from app import AcademicSession
    session = AcademicSession.query.get(session_id)
    if not session:
        return None, None
    
    return session.start_date, session.end_date

def get_upcoming_classes(days_ahead: int = 7) -> List[Dict]:
    """Get upcoming classes for the next N days"""
    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    
    upcoming_classes = []
    current_date = today
    
    while current_date <= end_date:
        if is_valid_class_date(current_date):
            class_instances = get_class_instances_for_date(current_date)
            
            for instance in class_instances:
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    upcoming_classes.append({
                        'date': current_date,
                        'day_name': current_date.strftime('%A'),
                        'course_name': timetable.course.name,
                        'course_code': timetable.course.code,
                        'start_time': timetable.time_slot.start_time,
                        'end_time': timetable.time_slot.end_time,
                        'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                        'teacher': timetable.teacher.name if timetable.teacher else 'TBD',
                        'student_group': timetable.student_group.name if timetable.student_group else 'TBD',
                        'is_holiday': False
                    })
        else:
            # Add holiday information
            holiday = get_holiday_for_date(current_date)
            if holiday:
                upcoming_classes.append({
                    'date': current_date,
                    'day_name': current_date.strftime('%A'),
                    'course_name': holiday.name,
                    'course_code': 'HOLIDAY',
                    'start_time': '00:00',
                    'end_time': '23:59',
                    'classroom': 'N/A',
                    'teacher': 'N/A',
                    'student_group': 'N/A',
                    'is_holiday': True,
                    'holiday_description': holiday.description
                })
        
        current_date += timedelta(days=1)
    
    return upcoming_classes

def get_monthly_calendar(year: int, month: int) -> List[List[Dict]]:
    """Get a monthly calendar view with class information"""
    # Get the first day of the month
    first_day = date(year, month, 1)
    
    # Get the last day of the month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get the first day of the week (Monday) for the first week
    start_date = first_day - timedelta(days=first_day.weekday())
    
    calendar = []
    current_week = []
    current_date = start_date
    
    while current_date <= last_day or len(current_week) < 7:
        day_info = {
            'date': current_date,
            'day_name': current_date.strftime('%A'),
            'day_number': current_date.day,
            'is_current_month': current_date.month == month,
            'is_today': current_date == date.today(),
            'is_weekend': is_weekend(current_date),
            'is_holiday': is_holiday(current_date),
            'classes': []
        }
        
        # Add class information for this date
        if is_valid_class_date(current_date):
            class_instances = get_class_instances_for_date(current_date)
            for instance in class_instances:
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    day_info['classes'].append({
                        'course_name': timetable.course.name,
                        'course_code': timetable.course.code,
                        'start_time': timetable.time_slot.start_time,
                        'end_time': timetable.time_slot.end_time,
                        'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                        'teacher': timetable.teacher.name if timetable.teacher else 'TBD'
                    })
        
        # Add holiday information
        if day_info['is_holiday']:
            holiday = get_holiday_for_date(current_date)
            if holiday:
                day_info['holiday_name'] = holiday.name
                day_info['holiday_description'] = holiday.description
        
        current_week.append(day_info)
        
        if len(current_week) == 7:
            calendar.append(current_week)
            current_week = []
        
        current_date += timedelta(days=1)
    
    # Add the last week if it's not complete
    if current_week:
        calendar.append(current_week)
    
    return calendar

def get_weekly_schedule(start_date: date) -> List[Dict]:
    """Get a weekly schedule starting from a specific date"""
    week_schedule = []
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_info = {
            'date': current_date,
            'day_name': current_date.strftime('%A'),
            'is_weekend': is_weekend(current_date),
            'is_holiday': is_holiday(current_date),
            'classes': []
        }
        
        if is_valid_class_date(current_date):
            class_instances = get_class_instances_for_date(current_date)
            for instance in class_instances:
                timetable = instance.timetable
                if timetable and timetable.course and timetable.time_slot:
                    day_info['classes'].append({
                        'course_name': timetable.course.name,
                        'course_code': timetable.course.code,
                        'start_time': timetable.time_slot.start_time,
                        'end_time': timetable.time_slot.end_time,
                        'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                        'teacher': timetable.teacher.name if timetable.teacher else 'TBD',
                        'student_group': timetable.student_group.name if timetable.student_group else 'TBD'
                    })
        
        if day_info['is_holiday']:
            holiday = get_holiday_for_date(current_date)
            if holiday:
                day_info['holiday_name'] = holiday.name
                day_info['holiday_description'] = holiday.description
        
        week_schedule.append(day_info)
    
    return week_schedule

def get_today_classes() -> List[Dict]:
    """Get all classes scheduled for today"""
    today = date.today()
    
    if not is_valid_class_date(today):
        return []
    
    class_instances = get_class_instances_for_date(today)
    today_classes = []
    
    for instance in class_instances:
        timetable = instance.timetable
        if timetable and timetable.course and timetable.time_slot:
            today_classes.append({
                'id': instance.id,
                'course_name': timetable.course.name,
                'course_code': timetable.course.code,
                'start_time': timetable.time_slot.start_time,
                'end_time': timetable.time_slot.end_time,
                'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                'teacher': timetable.teacher.name if timetable.teacher else 'TBD',
                'student_group': timetable.student_group.name if timetable.student_group else 'TBD',
                'time_slot_id': timetable.time_slot_id,
                'course_id': timetable.course_id
            })
    
    # Sort by start time
    today_classes.sort(key=lambda x: x['start_time'])
    
    return today_classes

def get_student_today_classes(student_id: int) -> List[Dict]:
    """Get today's classes for a specific student"""
    today = date.today()
    
    if not is_valid_class_date(today):
        return []
    
    # Get student's group
    from app import User
    student = User.query.get(student_id)
    if not student or not student.student_group_id:
        return []
    
    class_instances = ClassInstance.query.join(Timetable).filter(
        ClassInstance.class_date == today,
        Timetable.student_group_id == student.student_group_id
    ).all()
    
    today_classes = []
    
    for instance in class_instances:
        timetable = instance.timetable
        if timetable and timetable.course and timetable.time_slot:
            today_classes.append({
                'id': instance.id,
                'course_name': timetable.course.name,
                'course_code': timetable.course.code,
                'start_time': timetable.time_slot.start_time,
                'end_time': timetable.time_slot.end_time,
                'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                'teacher': timetable.teacher.name if timetable.teacher else 'TBD',
                'time_slot_id': timetable.time_slot_id,
                'course_id': timetable.course_id
            })
    
    # Sort by start time
    today_classes.sort(key=lambda x: x['start_time'])
    
    return today_classes

def get_faculty_today_classes(faculty_id: int) -> List[Dict]:
    """Get today's classes for a specific faculty member"""
    today = date.today()
    
    if not is_valid_class_date(today):
        return []
    
    class_instances = ClassInstance.query.join(Timetable).filter(
        ClassInstance.class_date == today,
        Timetable.teacher_id == faculty_id
    ).all()
    
    today_classes = []
    
    for instance in class_instances:
        timetable = instance.timetable
        if timetable and timetable.course and timetable.time_slot:
            today_classes.append({
                'id': instance.id,
                'course_name': timetable.course.name,
                'course_code': timetable.course.code,
                'start_time': timetable.time_slot.start_time,
                'end_time': timetable.time_slot.end_time,
                'classroom': timetable.classroom.room_number if timetable.classroom else 'TBD',
                'student_group': timetable.student_group.name if timetable.student_group else 'TBD',
                'time_slot_id': timetable.time_slot_id,
                'course_id': timetable.course_id
            })
    
    # Sort by start time
    today_classes.sort(key=lambda x: x['start_time'])
    
    return today_classes
