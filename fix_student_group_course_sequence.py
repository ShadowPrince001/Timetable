#!/usr/bin/env python3
"""
Fix Student Group Course Sequence Script

This script fixes the PostgreSQL sequence issue for the student_group_course table
where the sequence gets out of sync with the actual data, causing primary key
constraint violations.

Usage:
    python fix_student_group_course_sequence.py

Requirements:
    - PostgreSQL database
    - psycopg2 or psycopg2-binary installed
    - Database connection details in environment variables
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_student_group_course_sequence():
    """Fix the student_group_course sequence in PostgreSQL"""
    
    # Get database connection details
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        print("Please set DATABASE_URL in your .env file")
        return False
    
    if not database_url.startswith('postgresql://'):
        print("❌ This script only works with PostgreSQL databases")
        return False
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse the database URL
        parsed = urlparse(database_url)
        
        # Connect to the database
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password
        )
        
        cursor = conn.cursor()
        
        print("🔍 Checking student_group_course table...")
        
        # Get the current maximum ID
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM student_group_course")
        max_id = cursor.fetchone()[0]
        
        print(f"📊 Current maximum ID: {max_id}")
        
        if max_id == 0:
            print("ℹ️  Table is empty, setting sequence to start from 1")
            next_id = 1
        else:
            next_id = max_id + 1
            print(f"🔄 Setting sequence to start from {next_id}")
        
        # Reset the sequence
        cursor.execute(f"SELECT setval('student_group_course_id_seq', {next_id}, false)")
        
        # Verify the sequence value
        cursor.execute("SELECT currval('student_group_course_id_seq')")
        current_seq = cursor.fetchone()[0]
        
        print(f"✅ Sequence reset successfully to: {current_seq}")
        
        # Test inserting a dummy record (will be rolled back)
        print("🧪 Testing sequence with dummy insert...")
        cursor.execute("""
            INSERT INTO student_group_course (student_group_id, course_id) 
            VALUES (999999, 999999) 
            RETURNING id
        """)
        test_id = cursor.fetchone()[0]
        print(f"✅ Test insert successful, got ID: {test_id}")
        
        # Rollback the test insert
        conn.rollback()
        print("🔄 Test insert rolled back")
        
        # Commit the sequence change
        conn.commit()
        print("💾 Sequence change committed successfully")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Student Group Course sequence fixed successfully!")
        print(f"   Next insert will use ID: {next_id}")
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        print("Please install it with: pip install psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ Error fixing sequence: {str(e)}")
        return False

def main():
    """Main function"""
    print("🔧 Student Group Course Sequence Fix Tool")
    print("=" * 50)
    
    if fix_student_group_course_sequence():
        print("\n✅ All done! You can now try adding courses to student groups again.")
        sys.exit(0)
    else:
        print("\n❌ Failed to fix sequence. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
