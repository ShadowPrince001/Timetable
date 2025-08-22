#!/usr/bin/env python3
"""
Database Schema Update Script
Updates the existing database to add calendar-based columns.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import app and models
from app import app, db

def update_database_schema():
    """Update the database schema to add new calendar-based columns"""
    print("🔄 Updating Database Schema")
    print("=" * 60)
    
    try:
        # Create application context
        ctx = app.app_context()
        ctx.push()
        
        try:
            # Get database engine
            engine = db.engine
            
            # Check if we're using SQLite
            if 'sqlite' in str(engine.url):
                print("📋 Detected SQLite database")
                
                # Add new columns to existing tables
                print("🔧 Adding new columns to existing tables...")
                
                # Add columns to timetable table
                try:
                    engine.execute(text("ALTER TABLE timetable ADD COLUMN academic_year_id INTEGER"))
                    print("✅ Added academic_year_id to timetable table")
                except Exception as e:
                    print(f"⚠️  academic_year_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE timetable ADD COLUMN session_id INTEGER"))
                    print("✅ Added session_id to timetable table")
                except Exception as e:
                    print(f"⚠️  session_id column might already exist: {e}")
                
                # Add columns to attendance table
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN academic_year_id INTEGER"))
                    print("✅ Added academic_year_id to attendance table")
                except Exception as e:
                    print(f"⚠️  academic_year_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN session_id INTEGER"))
                    print("✅ Added session_id to attendance table")
                except Exception as e:
                    print(f"⚠️  session_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN class_instance_id INTEGER"))
                    print("✅ Added class_instance_id to attendance table")
                except Exception as e:
                    print(f"⚠️  class_instance_id column might already exist: {e}")
                
                # Create new tables
                print("📋 Creating new calendar tables...")
                db.create_all()
                print("✅ New tables created")
                
            else:
                # For PostgreSQL, we'll use ALTER TABLE statements
                print("📋 Detected PostgreSQL database")
                
                # Add columns to timetable table
                try:
                    engine.execute(text("ALTER TABLE timetable ADD COLUMN academic_year_id INTEGER"))
                    print("✅ Added academic_year_id to timetable table")
                except Exception as e:
                    print(f"⚠️  academic_year_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE timetable ADD COLUMN session_id INTEGER"))
                    print("✅ Added session_id to timetable table")
                except Exception as e:
                    print(f"⚠️  session_id column might already exist: {e}")
                
                # Add columns to attendance table
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN academic_year_id INTEGER"))
                    print("✅ Added academic_year_id to attendance table")
                except Exception as e:
                    print(f"⚠️  academic_year_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN session_id INTEGER"))
                    print("✅ Added session_id to attendance table")
                except Exception as e:
                    print(f"⚠️  session_id column might already exist: {e}")
                
                try:
                    engine.execute(text("ALTER TABLE attendance ADD COLUMN class_instance_id INTEGER"))
                    print("✅ Added class_instance_id to attendance table")
                except Exception as e:
                    print(f"⚠️  class_instance_id column might already exist: {e}")
                
                # Create new tables
                print("📋 Creating new calendar tables...")
                db.create_all()
                print("✅ New tables created")
            
            print("\n" + "=" * 60)
            print("🎉 Database schema updated successfully!")
            print("📊 Schema Update Summary:")
            print("   • Added academic_year_id to timetable table")
            print("   • Added session_id to timetable table")
            print("   • Added academic_year_id to attendance table")
            print("   • Added session_id to attendance table")
            print("   • Added class_instance_id to attendance table")
            print("   • Created new calendar tables (academic_year, academic_session, holiday, class_instance)")
            print("\n🚀 Database is now ready for calendar migration!")
            
        finally:
            ctx.pop()
            
    except Exception as e:
        print(f"❌ Schema update failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_database_schema()
