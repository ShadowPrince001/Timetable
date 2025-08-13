#!/usr/bin/env python3
"""
Database Reset Script for Timetable & Attendance System
This script will reset the database with the new schema including all new fields
"""

import os
from app import app, db, init_db

def reset_database():
    """Reset the database with new schema"""
    print("🔄 Resetting database with new schema...")
    
    with app.app_context():
        # Drop all tables
        print("🗑️  Dropping existing tables...")
        db.drop_all()
        
        # Create all tables with new schema
        print("🏗️  Creating new tables...")
        db.create_all()
        
        # Initialize with sample data
        print("📊 Initializing with sample data...")
        init_db()
        
        print("✅ Database reset completed successfully!")
        print("🎯 New schema includes:")
        print("   • User: phone, address fields")
        print("   • Course: semester, description fields")
        print("   • Classroom: room_type, floor, status, facilities fields")
        print("   • TimeSlot: break_type, notes fields")
        print("\n🚀 You can now start the application with: python app.py")

if __name__ == "__main__":
    # Check if database file exists
    db_file = "timetable_attendance.db"
    if os.path.exists(db_file):
        print(f"⚠️  Warning: Database file '{db_file}' will be deleted!")
        response = input("Do you want to continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Database reset cancelled.")
            exit()
        
        # Remove the database file
        os.remove(db_file)
        print(f"🗑️  Removed old database file: {db_file}")
    
    reset_database()
