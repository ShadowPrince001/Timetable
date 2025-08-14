#!/usr/bin/env python3
"""
Database Migration Script
Adds student_group_id column to existing Timetable table
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app, db
from sqlalchemy import text

def migrate_database():
    """Migrate the database to add student_group_id column"""
    print("🔄 Starting database migration...")
    
    with app.app_context():
        try:
            # Check if student_group_id column already exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('timetable')]
            
            if 'student_group_id' in columns:
                print("✅ student_group_id column already exists")
                return True
            
            print("📝 Adding student_group_id column to timetable table...")
            
            # Add the column
            db.engine.execute(text("""
                ALTER TABLE timetable 
                ADD COLUMN student_group_id INTEGER 
                REFERENCES student_group(id)
            """))
            
            # Update existing records to have a default student group
            # First, get the first student group
            result = db.engine.execute(text("SELECT id FROM student_group LIMIT 1"))
            first_group = result.fetchone()
            
            if first_group:
                default_group_id = first_group[0]
                print(f"🔄 Setting default student_group_id to {default_group_id} for existing records...")
                
                db.engine.execute(text(f"""
                    UPDATE timetable 
                    SET student_group_id = {default_group_id} 
                    WHERE student_group_id IS NULL
                """))
                
                print(f"✅ Updated existing timetable records with default group {default_group_id}")
            else:
                print("⚠️ No student groups found - you'll need to create some first")
            
            print("✅ Database migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

def reset_database():
    """Reset the database completely (nuclear option)"""
    print("🗑️ Resetting database completely...")
    
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            print("✅ All tables dropped")
            
            # Recreate all tables
            db.create_all()
            print("✅ All tables recreated")
            
            # Initialize with sample data
            from app import init_db
            init_db()
            print("✅ Sample data initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Reset failed: {e}")
            return False

def main():
    """Main migration function"""
    print("🚀 Database Migration Tool")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Error: app.py not found. Please run from project root.")
        return 1
    
    print("Choose migration option:")
    print("1. Add student_group_id column (preserve existing data)")
    print("2. Reset database completely (lose all data)")
    print("3. Exit")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            if migrate_database():
                print("\n🎉 Migration completed successfully!")
                return 0
            else:
                print("\n❌ Migration failed!")
                return 1
                
        elif choice == '2':
            confirm = input("⚠️ This will DELETE ALL DATA. Are you sure? (yes/no): ").strip().lower()
            if confirm == 'yes':
                if reset_database():
                    print("\n🎉 Database reset completed successfully!")
                    return 0
                else:
                    print("\n❌ Database reset failed!")
                    return 1
            else:
                print("❌ Operation cancelled")
                return 0
                
        elif choice == '3':
            print("👋 Exiting...")
            return 0
            
        else:
            print("❌ Invalid choice")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
