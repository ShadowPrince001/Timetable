#!/usr/bin/env python3
"""
Check database schema to understand table structures
"""

import os
from sqlalchemy import create_engine, text

def check_schema():
    """Check the database schema"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check user table columns
            print("🔍 Checking user table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user' ORDER BY ordinal_position"))
            user_columns = [row[0] for row in result]
            print(f"   User table columns: {user_columns}")
            
            # Check course table columns
            print("\n🔍 Checking course table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'course' ORDER BY ordinal_position"))
            course_columns = [row[0] for row in result]
            print(f"   Course table columns: {course_columns}")
            
            # Check time_slot table columns
            print("\n🔍 Checking time_slot table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'time_slot' ORDER BY ordinal_position"))
            time_slot_columns = [row[0] for row in result]
            print(f"   Time_slot table columns: {time_slot_columns}")
            
            # Check student_group table columns
            print("\n🔍 Checking student_group table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'student_group' ORDER BY ordinal_position"))
            student_group_columns = [row[0] for row in result]
            print(f"   Student_group table columns: {student_group_columns}")
            
            # Check student_group_course table columns
            print("\n🔍 Checking student_group_course table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'student_group_course' ORDER BY ordinal_position"))
            sgc_columns = [row[0] for row in result]
            print(f"   Student_group_course table columns: {sgc_columns}")
            
            # Check classroom table columns
            print("\n🔍 Checking classroom table columns...")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'classroom' ORDER BY ordinal_position"))
            classroom_columns = [row[0] for row in result]
            print(f"   Classroom table columns: {classroom_columns}")
            
            # Check if role column exists in user table
            if 'role' in user_columns:
                print("\n✅ Role column exists in user table")
                # Check what roles exist
                result = conn.execute(text("SELECT DISTINCT role FROM \"user\""))
                roles = [row[0] for row in result]
                print(f"   Available roles: {roles}")
            else:
                print("\n❌ Role column does not exist in user table")
                print("   Available columns: {user_columns}")
                
                # Check if there's a different column for user type
                possible_role_columns = ['user_type', 'type', 'category', 'group']
                for col in possible_role_columns:
                    if col in user_columns:
                        print(f"   Found potential role column: {col}")
                        result = conn.execute(text(f'SELECT DISTINCT "{col}" FROM "user"'))
                        values = [row[0] for row in result]
                        print(f"   Values in {col}: {values}")
                        break
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Database Schema Check Script")
    print("=" * 40)
    
    success = check_schema()
    
    if success:
        print("\n✅ Schema check completed successfully!")
    else:
        print("\n❌ Schema check failed!")
