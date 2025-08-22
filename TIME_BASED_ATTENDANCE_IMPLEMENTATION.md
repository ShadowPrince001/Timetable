# Time-Based Attendance & QR Code Expiration Implementation

## Overview

This document describes the implementation of two major features:

1. **QR Code Expiration**: QR codes now expire after 24 hours and automatically refresh
2. **Time-Based Attendance**: Scanner marks "late entry" for students scanning 15+ minutes after class start time, and won't work outside class hours

## Features Implemented

### 1. QR Code Expiration (24-Hour System)

#### Changes Made:

**Backend (`app.py`):**
- Modified `generate_qr_code()` function to create QR codes valid for 24 hours instead of daily expiration
- QR codes now expire exactly 24 hours from generation time
- Automatic detection of expired QR codes and generation of new ones

**Frontend (`templates/student/my_qr_code.html`):**
- Updated UI text to reflect 24-hour validity
- Added automatic QR code refresh when expiration is detected
- Enhanced expiry timer with auto-refresh functionality
- Updated instructions to mention 24-hour validity

#### How It Works:
1. QR codes are generated with 24-hour expiration from creation time
2. Students see a countdown timer showing time until expiration
3. When QR code expires, it automatically refreshes after 5 seconds
4. Each QR code is unique and can only be used once per class session

### 2. Time-Based Attendance System

#### Changes Made:

**Backend (`app.py`):**
- Enhanced `scan_qr_code()` function with time-based logic
- Added validation for class start/end times
- Implemented 15-minute grace period for late entries
- Automatic status determination (present/late) based on scan time

**Frontend (`templates/faculty/attendance_scanner.html`):**
- Updated scanner interface to show time-based features
- Enhanced recent attendance display to show status (Present/Late)
- Modified scan feedback to handle late entries
- Updated status messages to reflect attendance status

#### How It Works:

**Class Time Validation:**
- Scanner checks if current time is within class hours
- Returns error if scanning before class starts or after class ends
- Only allows scanning during active class time

**Late Entry Detection:**
- 15-minute grace period after class start time
- Students scanning within 15 minutes = "Present"
- Students scanning after 15 minutes = "Late"
- Status is automatically determined and stored

**Visual Feedback:**
- Success feedback for on-time attendance
- Warning feedback for late entries
- Different sounds for present vs late entries
- Status badges in recent attendance list

## Technical Implementation

### Time Calculation Logic

```python
# Parse time slot start and end times
start_time = datetime.strptime(time_slot.start_time, '%H:%M').time()
end_time = datetime.strptime(time_slot.end_time, '%H:%M').time()

# Check if class is currently active
if current_time < start_time:
    return jsonify({'success': False, 'error': f'Class has not started yet. Class starts at {time_slot.start_time}'})

if current_time > end_time:
    return jsonify({'success': False, 'error': f'Class has ended. Class ended at {time_slot.end_time}'})

# Determine attendance status based on time
grace_period = timedelta(minutes=15)
class_start_datetime = datetime.combine(date.today(), start_time)
late_threshold = class_start_datetime + grace_period

if now > late_threshold:
    status = 'late'
    status_message = f'Late entry marked for {student.name} (arrived {((now - class_start_datetime).total_seconds() / 60):.0f} minutes after class start)'
else:
    status = 'present'
    status_message = f'Attendance marked for {student.name}'
```

### QR Code Auto-Refresh Logic

```javascript
// Auto-refresh QR code after 5 seconds
setTimeout(() => {
    console.log('QR code expired, auto-refreshing...');
    fetch('/generate_qr_code')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayQRCode(data);
                startExpiryTimer(data.expires_at);
                showSuccess('QR code automatically refreshed!');
            } else {
                showError('Error refreshing QR code: ' + data.error);
            }
        })
        .catch(error => {
            showError('Error refreshing QR code: ' + error);
        });
}, 5000);
```

## User Experience

### For Students:
- QR codes automatically refresh every 24 hours
- Clear countdown timer showing time until expiration
- Automatic refresh notification when QR code expires
- Updated instructions explaining time-based attendance

### For Faculty:
- Scanner shows time-based attendance features
- Visual indicators for late entries
- Different feedback for present vs late attendance
- Enhanced recent attendance list with status badges
- Clear error messages for invalid scan times

## Testing

A test script (`test_time_based_attendance.py`) was created to verify the time-based logic:

**Test Results:**
- ✅ Class start time validation
- ✅ Class end time validation  
- ✅ 15-minute grace period for on-time attendance
- ✅ Late entry detection after grace period
- ✅ Accurate minute calculation for late entries

## Benefits

1. **Improved Security**: QR codes expire more frequently (24 hours vs daily)
2. **Better Attendance Tracking**: Automatic late entry detection
3. **Enhanced User Experience**: Clear feedback and automatic refresh
4. **Reduced Manual Work**: No need for faculty to manually mark late entries
5. **Consistent Enforcement**: Standardized 15-minute grace period across all classes

## Configuration

The system can be easily configured by modifying these parameters:

- **Grace Period**: Currently set to 15 minutes (modifiable in `app.py`)
- **QR Code Expiration**: Currently set to 24 hours (modifiable in `app.py`)
- **Auto-refresh Delay**: Currently set to 5 seconds (modifiable in frontend)

## Future Enhancements

1. **Configurable Grace Period**: Allow faculty to set different grace periods per course
2. **Attendance Analytics**: Track late entry patterns and generate reports
3. **Notifications**: Alert students when their QR code is about to expire
4. **Mobile App Integration**: Push notifications for QR code expiration
