#!/usr/bin/env python3
"""
Migration script to add missing session_type column to academic_session table
"""

import os
from sqlalchemy import create_engine, text

def fix_academic_session_schema():
    """Add missing session_type column to academic_session table"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            print("🔍 Checking academic_session table schema...")
            
            # Check current columns
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'academic_session' ORDER BY ordinal_position"))
            current_columns = [row[0] for row in result]
            print(f"   📊 Current columns: {current_columns}")
            
            # Check if session_type column exists
            if 'session_type' in current_columns:
                print("✅ session_type column already exists")
                return True
            
            print("❌ session_type column missing - adding it now...")
            
            # Add the session_type column
            conn.execute(text("ALTER TABLE academic_session ADD COLUMN session_type VARCHAR(50) NOT NULL DEFAULT 'semester'"))
            
            # Update existing records to have 'semester' as default
            conn.execute(text("UPDATE academic_session SET session_type = 'semester' WHERE session_type IS NULL"))
            
            # Commit the changes
            conn.commit()
            
            print("✅ Successfully added session_type column")
            
            # Verify the column was added
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'academic_session' ORDER BY ordinal_position"))
            updated_columns = [row[0] for row in result]
            print(f"   📊 Updated columns: {updated_columns}")
            
            # Check existing data
            result = conn.execute(text("SELECT id, name, session_type FROM academic_session"))
            sessions = result.fetchall()
            print(f"   📚 Existing sessions:")
            for session in sessions:
                print(f"      - ID {session.id}: {session.name} (type: {session.session_type})")
            
            return True
        
    except Exception as e:
        print(f"❌ Error fixing academic_session schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Academic Session Schema Fix Script")
    print("=" * 40)
    
    success = fix_academic_session_schema()
    
    if success:
        print("\n✅ Schema fix completed successfully!")
        print("The timetable generation should now work.")
    else:
        print("\n❌ Schema fix failed!")
