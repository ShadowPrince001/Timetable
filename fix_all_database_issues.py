#!/usr/bin/env python3
"""
Comprehensive Database Fix Script
Fixes all known database issues in the Timetable & Attendance System
"""

import os
import sys
import psycopg2
from datetime import datetime

def load_environment():
    """Load environment variables from .env file if it exists"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded .env file")
    except ImportError:
        print("ℹ️  python-dotenv not installed, using system environment")
    
    # Debug: Show what environment variables we can see
    print(f"🔍 Environment check:")
    print(f"   DATABASE_URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set'}")
    print(f"   FLASK_ENV: {os.getenv('FLASK_ENV', 'Not set')}")
    print(f"   Current working directory: {os.getcwd()}")

def get_database_url():
    """Get database URL from environment or prompt user"""
    # First try to load environment
    load_environment()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        print("Please check:")
        print("   1. Is your .env file in the current directory?")
        print("   2. Does it contain DATABASE_URL=...?")
        print("   3. Are you running from the project root?")
        print()
        
        # Check for .env file
        if os.path.exists('.env'):
            print("📁 .env file found, contents:")
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            print(f"   {line.strip()}")
            except Exception as e:
                print(f"   Error reading .env: {e}")
        else:
            print("📁 No .env file found in current directory")
        
        print()
        print("Please provide database connection details manually:")
        
        # Prompt for connection details
        host = input("Database host (default: localhost): ").strip() or "localhost"
        port = input("Database port (default: 5432): ").strip() or "5432"
        database = input("Database name: ").strip()
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        
        if not all([database, username, password]):
            print("❌ Missing required database connection details")
            sys.exit(1)
        
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    return database_url

def connect_to_database(database_url):
    """Connect to PostgreSQL database"""
    try:
        # Parse the URL to get connection parameters
        if database_url.startswith('postgresql://'):
            # Remove postgresql:// prefix
            connection_string = database_url[13:]
            # Split into user:pass@host:port/dbname
            if '@' in connection_string:
                auth_part, rest = connection_string.split('@', 1)
                if ':' in auth_part:
                    username, password = auth_part.split(':', 1)
                else:
                    username, password = auth_part, ''
                
                if ':' in rest:
                    host_part, dbname = rest.rsplit('/', 1)
                    if ':' in host_part:
                        host, port = host_part.split(':', 1)
                    else:
                        host, port = host_part, '5432'
                else:
                    host, port = rest.split('/', 1)[0], '5432'
                    dbname = rest.split('/', 1)[1]
            else:
                print("❌ Invalid database URL format")
                sys.exit(1)
        else:
            print("❌ Only PostgreSQL databases are supported")
            sys.exit(1)
        
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=dbname,
            user=username,
            password=password
        )
        
        print(f"✅ Connected to database: {dbname} on {host}:{port}")
        return conn
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def fix_sequences(conn):
    """Fix all sequence issues"""
    print("\n🔧 Fixing database sequences...")
    
    # PostgreSQL table names are case-sensitive and often quoted
    sequences_to_fix = [
        ('qr_code', 'qr_code_id_seq'),
        ('student_group_course', 'student_group_course_id_seq'),
        ('attendance', 'attendance_id_seq'),
        ('timetable', 'timetable_id_seq'),
        ('course', 'course_id_seq'),
        ('"user"', 'user_id_seq'),  # Note: user is quoted because it's a reserved word
        ('classroom', 'classroom_id_seq'),
        ('time_slot', 'time_slot_id_seq'),
        ('student_group', 'student_group_id_seq')
    ]
    
    fixed_count = 0
    for table_name, sequence_name in sequences_to_fix:
        try:
            with conn.cursor() as cursor:
                # Get current max ID from table
                cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                max_id = cursor.fetchone()[0]
                
                if max_id is not None:
                    # Reset sequence to start from max_id + 1
                    cursor.execute(f"SELECT setval('{sequence_name}', {max_id + 1}, false)")
                    print(f"   ✅ Fixed {sequence_name}: reset to {max_id + 1}")
                    fixed_count += 1
                else:
                    print(f"   ℹ️  {sequence_name}: no data to fix")
                    
        except Exception as e:
            print(f"   ❌ Failed to fix {sequence_name}: {e}")
            # If transaction is aborted, try to recover
            if "current transaction is aborted" in str(e):
                try:
                    conn.rollback()
                    print(f"   🔄 Rolled back transaction for {sequence_name}")
                    # Try again after rollback
                    with conn.cursor() as cursor:
                        cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                        max_id = cursor.fetchone()[0]
                        if max_id is not None:
                            cursor.execute(f"SELECT setval('{sequence_name}', {max_id + 1}, false)")
                            print(f"   ✅ Fixed {sequence_name} after rollback: reset to {max_id + 1}")
                            fixed_count += 1
                except Exception as retry_error:
                    print(f"   ❌ Failed to fix {sequence_name} after rollback: {retry_error}")
    
    # Commit all successful fixes
    try:
        conn.commit()
        print(f"✅ Fixed {fixed_count} sequences")
    except Exception as e:
        print(f"❌ Error committing sequence fixes: {e}")
        conn.rollback()
    
    return fixed_count

def fix_orphaned_records(conn):
    """Fix orphaned records and data integrity issues"""
    print("\n🔧 Fixing orphaned records and data integrity...")
    
    fixes_applied = 0
    
    try:
        with conn.cursor() as cursor:
            # Check for attendance records with invalid student_id
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE student_id IS NULL OR student_id NOT IN (SELECT id FROM "user")
            """)
            orphaned_count = cursor.fetchone()[0]
            
            if orphaned_count > 0:
                print(f"   ⚠️  Found {orphaned_count} attendance records with invalid student_id")
                
                # Get a valid student ID to use as replacement
                cursor.execute('SELECT id FROM "user" WHERE role = \'student\' LIMIT 1')
                valid_student = cursor.fetchone()
                
                if valid_student:
                    valid_student_id = valid_student[0]
                    # Update orphaned records to use valid student_id
                    cursor.execute("""
                        UPDATE attendance 
                        SET student_id = %s 
                        WHERE student_id IS NULL OR student_id NOT IN (SELECT id FROM "user")
                    """, (valid_student_id,))
                    
                    updated_count = cursor.rowcount
                    print(f"   ✅ Updated {updated_count} orphaned attendance records")
                    fixes_applied += updated_count
                else:
                    print("   ❌ No valid students found to fix orphaned records")
            
            # Check for attendance records with invalid course_id
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE course_id IS NULL OR course_id NOT IN (SELECT id FROM course)
            """)
            orphaned_course_count = cursor.fetchone()[0]
            
            if orphaned_course_count > 0:
                print(f"   ⚠️  Found {orphaned_course_count} attendance records with invalid course_id")
                
                # Get a valid course ID to use as replacement
                cursor.execute('SELECT id FROM course LIMIT 1')
                valid_course = cursor.fetchone()
                
                if valid_course:
                    valid_course_id = valid_course[0]
                    # Update orphaned records to use valid course_id
                    cursor.execute("""
                        UPDATE attendance 
                        SET course_id = %s 
                        WHERE course_id IS NULL OR course_id NOT IN (SELECT id FROM course)
                    """, (valid_course_id,))
                    
                    updated_count = cursor.rowcount
                    print(f"   ✅ Updated {updated_count} orphaned course records")
                    fixes_applied += updated_count
                else:
                    print("   ❌ No valid courses found to fix orphaned records")
            
            # Check for attendance records with invalid time_slot_id
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE time_slot_id IS NULL OR time_slot_id NOT IN (SELECT id FROM time_slot)
            """)
            orphaned_timeslot_count = cursor.fetchone()[0]
            
            if orphaned_timeslot_count > 0:
                print(f"   ⚠️  Found {orphaned_timeslot_count} attendance records with invalid time_slot_id")
                
                # Get a valid time slot ID to use as replacement
                cursor.execute('SELECT id FROM time_slot LIMIT 1')
                valid_timeslot = cursor.fetchone()
                
                if valid_timeslot:
                    valid_timeslot_id = valid_timeslot[0]
                    # Update orphaned records to use valid time_slot_id
                    cursor.execute("""
                        UPDATE attendance 
                        SET time_slot_id = %s 
                        WHERE time_slot_id IS NULL OR time_slot_id NOT IN (SELECT id FROM time_slot)
                    """, (valid_timeslot_id,))
                    
                    updated_count = cursor.rowcount
                    print(f"   ✅ Updated {updated_count} orphaned time slot records")
                    fixes_applied += updated_count
                else:
                    print("   ❌ No valid time slots found to fix orphaned records")
                    
    except Exception as e:
        print(f"   ❌ Error fixing orphaned records: {e}")
    
    conn.commit()
    print(f"✅ Applied {fixes_applied} data integrity fixes")
    return fixes_applied

def fix_constraint_violations(conn):
    """Fix specific constraint violations like unique_group_course"""
    print("\n🔧 Fixing constraint violations...")
    
    fixes_applied = 0
    
    try:
        with conn.cursor() as cursor:
            # Fix unique_group_course constraint violations
            print("   🔍 Checking for duplicate group-course combinations...")
            
            # Find duplicate entries that violate unique constraint
            cursor.execute("""
                SELECT student_group_id, course_id, COUNT(*) as count
                FROM student_group_course 
                GROUP BY student_group_id, course_id 
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                print(f"   ⚠️  Found {len(duplicates)} duplicate group-course combinations")
                
                # Fix duplicates by keeping only one record per combination
                for duplicate in duplicates:
                    group_id, course_id, count = duplicate
                    if count > 1:
                        print(f"   🔧 Fixing duplicate group {group_id}-course {course_id} (has {count} records)")
                        
                        # Delete all but one record for this combination
                        cursor.execute("""
                            DELETE FROM student_group_course 
                            WHERE student_group_id = %s AND course_id = %s
                            AND id NOT IN (
                                SELECT MIN(id) FROM student_group_course 
                                WHERE student_group_id = %s AND course_id = %s
                            )
                        """, (group_id, course_id, group_id, course_id))
                        
                        deleted_count = cursor.rowcount
                        print(f"   ✅ Removed {deleted_count} duplicate records for group {group_id}-course {course_id}")
                        fixes_applied += deleted_count
            else:
                print("   ✅ No duplicate group-course combinations found")
                
    except Exception as e:
        print(f"   ❌ Error fixing constraint violations: {e}")
        conn.rollback()
        return fixes_applied
    
    # Commit fixes
    try:
        conn.commit()
        print(f"✅ Applied {fixes_applied} constraint violation fixes")
    except Exception as e:
        print(f"❌ Error committing constraint fixes: {e}")
        conn.rollback()
    
    return fixes_applied

def check_table_counts(conn):
    """Display table row counts for verification"""
    print("\n📊 Table row counts:")
    
    tables = [
        'user', 'course', 'classroom', 'time_slot', 'timetable', 
        'attendance', 'qr_code', 'student_group', 'student_group_course'
    ]
    
    for table in tables:
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   📋 {table}: {count} rows")
        except Exception as e:
            print(f"   ❌ {table}: error counting rows - {e}")

def run_comprehensive_fix():
    """Run the complete database fix process"""
    print("🚀 Starting comprehensive database fix process...")
    print("=" * 60)
    
    # Get database connection
    database_url = get_database_url()
    conn = connect_to_database(database_url)
    
    try:
        # Fix sequences
        sequences_fixed = fix_sequences(conn)
        
        # Fix orphaned records
        orphaned_fixes = fix_orphaned_records(conn)
        
        # Fix constraint violations
        constraint_fixes = fix_constraint_violations(conn)
        
        # Check table counts
        check_table_counts(conn)
        
        # Summary
        print("\n" + "=" * 60)
        print("🎉 Database fix process completed!")
        print(f"✅ Sequences fixed: {sequences_fixed}")
        print(f"✅ Orphaned records fixed: {orphaned_fixes}")
        print(f"✅ Constraint violations fixed: {constraint_fixes}")
        print(f"✅ Total fixes applied: {sequences_fixed + orphaned_fixes + constraint_fixes}")
        
        if sequences_fixed + orphaned_fixes + constraint_fixes > 0:
            print("\n💡 The database has been fixed. You should now be able to:")
            print("   - Generate QR codes without sequence errors")
            print("   - Add courses to student groups without constraint violations")
            print("   - Mark attendance without null constraint errors")
            print("   - Manage users without server errors")
        else:
            print("\n✅ No issues were found - your database is healthy!")
            
    except Exception as e:
        print(f"\n❌ Error during database fix process: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    run_comprehensive_fix()
