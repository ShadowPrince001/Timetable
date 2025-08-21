#!/usr/bin/env python3
"""
Database fix script for Timetable & Attendance System
Adds missing columns to existing database without losing data
"""

from app import app, db
from sqlalchemy import text

def fix_database():
    """Fix the existing database by adding missing columns"""
    
    with app.app_context():
        print("Checking and fixing database schema...")
        
        # Check if experience column exists
        try:
            result = db.session.execute(text("PRAGMA table_info(user)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"Existing columns in user table: {columns}")
            
            # Add missing columns if they don't exist
            if 'experience' not in columns:
                print("Adding experience column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN experience INTEGER"))
                
            if 'qualifications' not in columns:
                print("Adding qualifications column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN qualifications TEXT"))
                
            if 'bio' not in columns:
                print("Adding bio column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN bio TEXT"))
                
            if 'access_level' not in columns:
                print("Adding access_level column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN access_level VARCHAR(20) DEFAULT 'admin'"))
                
            if 'phone' not in columns:
                print("Adding phone column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN phone VARCHAR(20)"))
                
            if 'address' not in columns:
                print("Adding address column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN address TEXT"))
                
            if 'group_id' not in columns:
                print("Adding group_id column...")
                db.session.execute(text("ALTER TABLE user ADD COLUMN group_id INTEGER REFERENCES student_group(id)"))
                
            db.session.commit()
            print("Database schema updated successfully!")
            
            # Update existing users with default values
            print("Updating existing users with default values...")
            
            # Update admin user
            db.session.execute(text("""
                UPDATE user 
                SET experience = 15, 
                    qualifications = 'Ph.D. in Information Technology',
                    bio = 'Senior Administrator with expertise in educational management',
                    access_level = 'super_admin',
                    phone = '+91-9876543210',
                    address = 'Admin Block, Room 101, Institution Campus'
                WHERE username = 'admin'
            """))
            
            # Update faculty users
            db.session.execute(text("""
                UPDATE user 
                SET experience = 10, 
                    qualifications = 'Ph.D. in respective field',
                    bio = 'Faculty member with expertise in their domain',
                    access_level = 'faculty',
                    phone = '+91-9876543000',
                    address = 'Department Office, Main Block'
                WHERE role = 'faculty'
            """))
            
            # Update student users
            db.session.execute(text("""
                UPDATE user 
                SET experience = NULL, 
                    qualifications = NULL,
                    bio = 'Student pursuing engineering degree',
                    access_level = 'student',
                    phone = '+91-9876543000',
                    address = 'Student Hostel, Campus'
                WHERE role = 'student'
            """))
            
            db.session.commit()
            print("Existing users updated with default values!")
            
        except Exception as e:
            print(f"Error fixing database: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    fix_database()
