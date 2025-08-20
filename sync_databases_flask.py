#!/usr/bin/env python3
"""
Database synchronization script for Flask application.
This script ensures the database schema matches the current models.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app import app, db
from sqlalchemy import text

def sync_database():
    """Synchronize database schema with current models."""
    with app.app_context():
        try:
            print("🔄 Starting database synchronization...")
            
            # Check if User table exists and add missing columns
            check_user_table()
            
            # Check if Notification table exists
            check_notification_table()
            
            print("✅ Database synchronization completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during database synchronization: {e}")
            db.session.rollback()
            raise

def check_user_table():
    """Check and update User table schema."""
    try:
        # Check if User table exists
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user'"))
        if not result.fetchone():
            print("📋 User table does not exist. Creating...")
            db.create_all()
            return
        
        print("🔍 Checking User table columns...")
        
        # Get existing columns
        result = db.session.execute(text("PRAGMA table_info(user)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        # Define required columns
        required_columns = {
            'experience': 'INTEGER',
            'bio': 'TEXT',
            'access_level': 'VARCHAR(20)',
            'last_login': 'DATETIME'
        }
        
        # Add missing columns
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                print(f"➕ Adding column: {column_name}")
                if column_type == 'DATETIME':
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {column_name} DATETIME"))
                else:
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {column_name} {column_type}"))
        
        # Set default values for existing rows
        if 'access_level' not in existing_columns:
            print("🔄 Setting default access_level for existing users...")
            db.session.execute(text("UPDATE user SET access_level = 'admin' WHERE role = 'admin'"))
            db.session.execute(text("UPDATE user SET access_level = 'faculty' WHERE role = 'faculty'"))
            db.session.execute(text("UPDATE user SET access_level = 'student' WHERE role = 'student'"))
        
        db.session.commit()
        print("✅ User table schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating User table: {e}")
        db.session.rollback()
        raise

def check_notification_table():
    """Check and create Notification table if it doesn't exist."""
    try:
        # Check if Notification table exists
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='notification'"))
        if not result.fetchone():
            print("📋 Notification table does not exist. Creating...")
            db.create_all()
        else:
            print("✅ Notification table exists.")
            
    except Exception as e:
        print(f"❌ Error checking Notification table: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    print("🚀 Database Synchronization Tool")
    print("=" * 40)
    
    try:
        sync_database()
        print("\n🎉 All done! Database is now synchronized with the current models.")
    except Exception as e:
        print(f"\n💥 Failed to synchronize database: {e}")
        sys.exit(1)
