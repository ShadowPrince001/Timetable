#!/usr/bin/env python3
"""
Test script for time-based attendance logic
"""

from datetime import datetime, time, timedelta

def test_time_based_attendance():
    """Test the time-based attendance logic"""
    
    # Test cases
    test_cases = [
        {
            'name': 'Class starts at 9:00 AM',
            'start_time': '09:00',
            'end_time': '10:30',
            'scan_times': [
                ('08:45', 'Class has not started yet'),
                ('09:00', 'Present'),
                ('09:10', 'Present'),
                ('09:15', 'Present'),
                ('09:16', 'Late'),
                ('09:30', 'Late'),
                ('10:30', 'Late'),
                ('10:31', 'Class has ended'),
            ]
        },
        {
            'name': 'Class starts at 2:00 PM',
            'start_time': '14:00',
            'end_time': '15:30',
            'scan_times': [
                ('13:45', 'Class has not started yet'),
                ('14:00', 'Present'),
                ('14:10', 'Present'),
                ('14:15', 'Present'),
                ('14:16', 'Late'),
                ('14:30', 'Late'),
                ('15:30', 'Late'),
                ('15:31', 'Class has ended'),
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")
        start_time = datetime.strptime(test_case['start_time'], '%H:%M').time()
        end_time = datetime.strptime(test_case['end_time'], '%H:%M').time()
        
        print(f"Class time: {start_time} - {end_time}")
        print(f"Grace period: 15 minutes")
        print()
        
        for scan_time_str, expected_status in test_case['scan_times']:
            scan_time = datetime.strptime(scan_time_str, '%H:%M').time()
            status = determine_attendance_status(scan_time, start_time, end_time)
            print(f"Scan at {scan_time_str}: {status} (Expected: {expected_status})")

def determine_attendance_status(scan_time, start_time, end_time):
    """Determine attendance status based on scan time"""
    
    # Check if class has started
    if scan_time < start_time:
        return f"Class has not started yet. Class starts at {start_time.strftime('%H:%M')}"
    
    # Check if class has ended
    if scan_time > end_time:
        return f"Class has ended. Class ended at {end_time.strftime('%H:%M')}"
    
    # Calculate if late (15 minutes grace period)
    grace_period = timedelta(minutes=15)
    class_start_datetime = datetime.combine(datetime.today().date(), start_time)
    scan_datetime = datetime.combine(datetime.today().date(), scan_time)
    late_threshold = class_start_datetime + grace_period
    
    if scan_datetime > late_threshold:
        minutes_late = int((scan_datetime - class_start_datetime).total_seconds() / 60)
        return f"Late (arrived {minutes_late} minutes after class start)"
    else:
        return "Present"

if __name__ == "__main__":
    test_time_based_attendance()
