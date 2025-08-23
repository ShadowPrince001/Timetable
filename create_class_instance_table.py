#!/usr/bin/env python3
"""
Migration script to create the missing ClassInstance table
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, Date, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.exc import ProgrammingError

def create_class_instance_table():
    """Create the ClassInstance table if it doesn't exist"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check if table already exists
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'class_instance'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ ClassInstance table already exists")
                return True
            
            print("📋 Creating ClassInstance table...")
            
            # Create the table
            conn.execute(text("""
                CREATE TABLE class_instance (
                    id SERIAL PRIMARY KEY,
                    timetable_id INTEGER NOT NULL REFERENCES timetable(id) ON DELETE CASCADE,
                    class_date DATE NOT NULL,
                    is_cancelled BOOLEAN DEFAULT FALSE,
                    cancellation_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create unique constraint
            conn.execute(text("""
                ALTER TABLE class_instance 
                ADD CONSTRAINT unique_class_instance 
                UNIQUE (timetable_id, class_date);
            """))
            
            # Create index for better performance
            conn.execute(text("""
                CREATE INDEX idx_class_instance_date 
                ON class_instance(class_date);
            """))
            
            conn.commit()
            print("✅ ClassInstance table created successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error creating ClassInstance table: {e}")
        return False

if __name__ == "__main__":
    print("🔧 ClassInstance Table Migration Script")
    print("=" * 40)
    
    success = create_class_instance_table()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The ClassInstance table has been created and the system should now work properly.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
