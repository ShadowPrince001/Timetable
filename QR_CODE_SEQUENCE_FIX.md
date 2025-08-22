# QR Code Sequence Fix Documentation

## Problem Description

The system was encountering a PostgreSQL database error when generating QR codes:

```
Error loading QR code: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "qr_code_pkey" 
DETAIL: Key (id)=(2) already exists.
```

This error occurs when the PostgreSQL sequence for the `qr_code` table's `id` column gets out of sync with the actual data in the table.

## Root Cause

This typically happens when:
1. Data is imported from another source
2. The database was restored from a backup
3. Manual ID insertions were made
4. The sequence wasn't properly reset after table operations

## Solution Implemented

### 1. Enhanced QR Code Generation Function

The `generate_qr_code()` function in `app.py` has been enhanced with:

- **Retry Logic**: Up to 3 attempts to create a new QR code
- **Automatic Sequence Reset**: Automatically detects and fixes sequence issues
- **Graceful Error Handling**: Better error messages and fallback behavior

### 2. Sequence Reset Function

A new function `reset_qr_code_sequence()` that:
- Detects PostgreSQL databases automatically
- Finds the current maximum ID in the `qr_code` table
- Resets the sequence to start from `max_id + 1`
- Handles errors gracefully

### 3. Admin Route for Manual Reset

A new admin-only route `/admin/reset_qr_sequence` that allows administrators to manually reset the sequence when needed.

### 4. Admin Dashboard Integration

Added a "Reset QR Sequence" button in the admin dashboard under Database Management section.

### 5. Standalone Fix Script

Created `fix_qr_sequence.py` - a standalone script that can be run independently to fix sequence issues.

## How to Use

### Option 1: Automatic Fix (Recommended)

The system now automatically handles sequence issues when generating QR codes. Users don't need to do anything special - the system will:

1. Detect the sequence issue
2. Automatically reset the sequence
3. Retry the QR code generation
4. Continue normally

### Option 2: Manual Fix via Admin Dashboard

1. Log in as an administrator
2. Go to Admin Dashboard
3. Scroll to "Database Management" section
4. Click "Reset QR Sequence" button
5. Confirm the action

### Option 3: Standalone Script

Run the standalone script from the command line:

```bash
python fix_qr_sequence.py
```

This script will:
- Detect your database type
- Fix the sequence if needed
- Provide detailed feedback
- Exit with appropriate status codes

## Technical Details

### Database Compatibility

- **PostgreSQL**: Full support with automatic sequence reset
- **SQLite**: No action needed (no sequences)

### Error Handling

The system handles various error scenarios:
- Sequence out of sync
- Database connection issues
- Permission problems
- Invalid database states

### Retry Logic

The QR code generation now includes:
- Up to 3 retry attempts
- Automatic sequence reset on first failure
- New hash generation for each retry
- Proper transaction rollback between attempts

## Prevention

To prevent this issue in the future:

1. **Avoid Manual ID Insertions**: Let the database handle ID generation
2. **Proper Backup/Restore**: Use database tools that preserve sequences
3. **Data Import**: Use proper import tools that handle sequences correctly
4. **Regular Maintenance**: Monitor sequence health in production

## Monitoring

The system now logs sequence reset operations:
- Console output for debugging
- Success/failure status in admin interface
- Detailed error messages for troubleshooting

## Testing

To test the fix:

1. Generate a QR code as a student
2. If sequence issues occur, the system should automatically fix them
3. Check admin dashboard for the reset button
4. Verify QR codes generate successfully after the fix

## Support

If you continue to experience issues:

1. Check the console logs for detailed error messages
2. Use the admin dashboard reset button
3. Run the standalone fix script
4. Check database connectivity and permissions

## Files Modified

- `app.py` - Enhanced QR code generation and added sequence reset functions
- `templates/admin/dashboard.html` - Added reset button to admin dashboard
- `fix_qr_sequence.py` - New standalone fix script

## Conclusion

This comprehensive solution provides multiple ways to handle QR code sequence issues:
- **Automatic**: Happens transparently during normal operation
- **Manual**: Admin can trigger fixes when needed
- **Standalone**: Independent script for emergency situations

The system is now more robust and should handle sequence issues gracefully without user intervention.
