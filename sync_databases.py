#!/usr/bin/env python3
"""
Database Synchronization Script
Synchronizes database structure and data across different environments:
- Local workspace
- Codespace
- Render production

This script ensures all environments have identical database schemas and sample data.
"""

import os
import sys
import sqlite3
import psycopg2
from datetime import datetime
import json

def detect_environment():
    """Detect the current environment"""
    if 'RENDER' in os.environ:
        return 'render'
    elif 'CODESPACES' in os.environ:
        return 'codespace'
    else:
        return 'local'

def get_database_connection():
    """Get database connection based on environment"""
    env = detect_environment()
    
    if env == 'render':
        # Render PostgreSQL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in Render environment")
            return None
        
        try:
            conn = psycopg2.connect(database_url)
            print(f"✅ Connected to Render PostgreSQL database")
            return conn
        except Exception as e:
            print(f"❌ Failed to connect to Render database: {e}")
            return None
    
    else:
        # Local/Codespace SQLite
        db_path = os.path.join('instance', 'timetable_attendance.db')
        if not os.path.exists('instance'):
            os.makedirs('instance')
        
        try:
            conn = sqlite3.connect(db_path)
            print(f"✅ Connected to {'Codespace' if env == 'codespace' else 'Local'} SQLite database: {db_path}")
            return conn
        except Exception as e:
            print(f"❌ Failed to connect to SQLite database: {e}")
            return None

def get_database_type(conn):
    """Determine if connection is PostgreSQL or SQLite"""
    if hasattr(conn, 'server_version'):
        return 'postgresql'
    else:
        return 'sqlite'

def create_tables_postgresql(conn):
    """Create tables in PostgreSQL"""
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "user" (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(120) NOT NULL,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,
            qualifications TEXT,
            group_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Courses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3,
            department VARCHAR(100) NOT NULL,
            max_students INTEGER DEFAULT 50,
            semester VARCHAR(20) DEFAULT '1',
            description TEXT,
            subject_area VARCHAR(100) NOT NULL,
            required_equipment TEXT,
            min_capacity INTEGER DEFAULT 1,
            periods_per_week INTEGER DEFAULT 3,
            CONSTRAINT check_credits_range CHECK (credits >= 1 AND credits <= 6),
            CONSTRAINT check_max_students CHECK (max_students >= 1 AND max_students <= 200),
            CONSTRAINT check_min_capacity CHECK (min_capacity >= 1)
        )
    """)
    
    # Create CourseTeacher table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_teacher (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL REFERENCES course(id),
            teacher_id INTEGER NOT NULL REFERENCES "user"(id),
            is_primary BOOLEAN DEFAULT FALSE,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, teacher_id)
        )
    """)
    
    # Create Classrooms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classroom (
            id SERIAL PRIMARY KEY,
            room_number VARCHAR(20) UNIQUE NOT NULL,
            capacity INTEGER NOT NULL,
            building VARCHAR(50) NOT NULL,
            room_type VARCHAR(50) DEFAULT 'lecture',
            floor INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'active',
            facilities TEXT,
            equipment VARCHAR(200),
            CONSTRAINT check_capacity_range CHECK (capacity >= 1 AND capacity <= 500),
            CONSTRAINT check_floor_range CHECK (floor >= 0 AND floor <= 20)
        )
    """)
    
    # Create TimeSlots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slot (
            id SERIAL PRIMARY KEY,
            day VARCHAR(20) NOT NULL,
            start_time VARCHAR(10) NOT NULL,
            end_time VARCHAR(10) NOT NULL,
            break_type VARCHAR(20) DEFAULT 'none',
            notes TEXT
        )
    """)
    
    # Create StudentGroups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_group (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            department VARCHAR(100) NOT NULL,
            year INTEGER NOT NULL,
            semester INTEGER NOT NULL
        )
    """)
    
    # Create StudentGroupCourse table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_group_course (
            id SERIAL PRIMARY KEY,
            student_group_id INTEGER NOT NULL REFERENCES student_group(id),
            course_id INTEGER NOT NULL REFERENCES course(id)
        )
    """)
    
    # Create Timetables table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id SERIAL PRIMARY KEY,
            course_id INTEGER NOT NULL REFERENCES course(id),
            classroom_id INTEGER NOT NULL REFERENCES classroom(id),
            time_slot_id INTEGER NOT NULL REFERENCES time_slot(id),
            teacher_id INTEGER NOT NULL REFERENCES "user"(id),
            semester VARCHAR(20) NOT NULL,
            academic_year VARCHAR(10) NOT NULL,
            UNIQUE(classroom_id, time_slot_id, semester, academic_year),
            UNIQUE(teacher_id, time_slot_id, semester, academic_year)
        )
    """)
    
    # Create Attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL REFERENCES "user"(id),
            timetable_id INTEGER NOT NULL REFERENCES timetable(id),
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL,
            marked_by INTEGER NOT NULL REFERENCES "user"(id),
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id),
            title VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(20) NOT NULL,
            read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    print("✅ PostgreSQL tables created successfully")

def create_tables_sqlite(conn):
    """Create tables in SQLite"""
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "user" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(120) NOT NULL,
            role VARCHAR(20) NOT NULL,
            name VARCHAR(100) NOT NULL,
            department VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,
            qualifications TEXT,
            group_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Courses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3,
            department VARCHAR(100) NOT NULL,
            max_students INTEGER DEFAULT 50,
            semester VARCHAR(20) DEFAULT '1',
            description TEXT,
            subject_area VARCHAR(100) NOT NULL,
            required_equipment TEXT,
            min_capacity INTEGER DEFAULT 1,
            periods_per_week INTEGER DEFAULT 3
        )
    """)
    
    # Create CourseTeacher table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_teacher (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            is_primary BOOLEAN DEFAULT 0,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, teacher_id),
            FOREIGN KEY (course_id) REFERENCES course(id),
            FOREIGN KEY (teacher_id) REFERENCES "user"(id)
        )
    """)
    
    # Create Classrooms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classroom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number VARCHAR(20) UNIQUE NOT NULL,
            capacity INTEGER NOT NULL,
            building VARCHAR(50) NOT NULL,
            room_type VARCHAR(50) DEFAULT 'lecture',
            floor INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'active',
            facilities TEXT,
            equipment VARCHAR(200)
        )
    """)
    
    # Create TimeSlots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_slot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day VARCHAR(20) NOT NULL,
            start_time VARCHAR(10) NOT NULL,
            end_time VARCHAR(10) NOT NULL,
            break_type VARCHAR(20) DEFAULT 'none',
            notes TEXT
        )
    """)
    
    # Create StudentGroups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL,
            department VARCHAR(100) NOT NULL,
            year INTEGER NOT NULL,
            semester INTEGER NOT NULL
        )
    """)
    
    # Create StudentGroupCourse table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_group_course (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_group_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (student_group_id) REFERENCES student_group(id),
            FOREIGN KEY (course_id) REFERENCES course(id)
        )
    """)
    
    # Create Timetables table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            time_slot_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            semester VARCHAR(20) NOT NULL,
            academic_year VARCHAR(10) NOT NULL,
            UNIQUE(classroom_id, time_slot_id, semester, academic_year),
            UNIQUE(teacher_id, time_slot_id, semester, academic_year),
            FOREIGN KEY (course_id) REFERENCES course(id),
            FOREIGN KEY (classroom_id) REFERENCES classroom(id),
            FOREIGN KEY (time_slot_id) REFERENCES time_slot(id),
            FOREIGN KEY (teacher_id) REFERENCES "user"(id)
        )
    """)
    
    # Create Attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            timetable_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL,
            marked_by INTEGER NOT NULL,
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES "user"(id),
            FOREIGN KEY (timetable_id) REFERENCES timetable(id),
            FOREIGN KEY (marked_by) REFERENCES "user"(id)
        )
    """)
    
    # Create Notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            type VARCHAR(20) NOT NULL,
            read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES "user"(id)
        )
    """)
    
    conn.commit()
    print("✅ SQLite tables created successfully")

def insert_sample_data(conn, db_type):
    """Insert sample data into the database"""
    cursor = conn.cursor()
    
    # Check if data already exists
    if db_type == 'postgresql':
        cursor.execute("SELECT COUNT(*) FROM \"user\"")
    else:
        cursor.execute("SELECT COUNT(*) FROM \"user\"")
    
    count = cursor.fetchone()[0]
    if count > 0:
        print("ℹ️ Sample data already exists, skipping insertion")
        return
    
    print("📝 Inserting sample data...")
    
    # Insert sample users
    users_data = [
        ('admin', 'admin@institution.com', 'pbkdf2:sha256:600000$hash_here', 'admin', 'System Administrator', 'IT', '+91-9876543210', 'Main Campus, IT Department', 'M.Tech, PhD in Computer Science'),
        ('faculty', 'faculty@institution.com', 'pbkdf2:sha256:600000$hash_here', 'faculty', 'Dr. John Smith', 'Computer Science', '+91-9876543211', 'Computer Science Department, Room 201', 'PhD in Computer Science, 10 years experience'),
        ('student', 'student@institution.com', 'pbkdf2:sha256:600000$hash_here', 'student', 'Alice Johnson', 'Computer Science', '+91-9876543213', 'Student Hostel Block A, Room 101', '12th Standard, Computer Science Stream')
    ]
    
    for user in users_data:
        if db_type == 'postgresql':
            cursor.execute("""
                INSERT INTO "user" (username, email, password_hash, role, name, department, phone, address, qualifications)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, user)
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO "user" (username, email, password_hash, role, name, department, phone, address, qualifications)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, user)
    
    # Insert sample student groups
    groups_data = [
        ('CS-2024-1', 'Computer Science', 2024, 1),
        ('CS-2024-2', 'Computer Science', 2024, 2),
        ('MATH-2024-1', 'Mathematics', 2024, 1)
    ]
    
    for group in groups_data:
        if db_type == 'postgresql':
            cursor.execute("""
                INSERT INTO student_group (name, department, year, semester)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, group)
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO student_group (name, department, year, semester)
                VALUES (?, ?, ?, ?)
            """, group)
    
    # Insert sample courses
    courses_data = [
        ('CS101', 'Introduction to Computer Science', 3, 'Computer Science', 50, '1', 'Fundamental concepts of computer science and programming', 'Computer Science', 'Projector, Whiteboard', 1, 3),
        ('MATH101', 'Calculus I', 4, 'Mathematics', 40, '1', 'Introduction to differential and integral calculus', 'Mathematics', 'Whiteboard, Calculator', 1, 4)
    ]
    
    for course in courses_data:
        if db_type == 'postgresql':
            cursor.execute("""
                INSERT INTO course (code, name, credits, department, max_students, semester, description, subject_area, required_equipment, min_capacity, periods_per_week)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING
            """, course)
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO course (code, name, credits, department, max_students, semester, description, subject_area, required_equipment, min_capacity, periods_per_week)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, course)
    
    # Insert sample classrooms
    classrooms_data = [
        ('101', 50, 'Science Building', 'lecture', 1, 'active', 'Projector, Whiteboard, Air Conditioning', 'Projector, Whiteboard'),
        ('205', 40, 'Mathematics Building', 'seminar', 2, 'active', 'Smart Board, Computer, Whiteboard', 'Smart Board, Computer')
    ]
    
    for classroom in classrooms_data:
        if db_type == 'postgresql':
            cursor.execute("""
                INSERT INTO classroom (room_number, capacity, building, room_type, floor, status, facilities, equipment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (room_number) DO NOTHING
            """, classroom)
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO classroom (room_number, capacity, building, room_type, floor, status, facilities, equipment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, classroom)
    
    # Insert sample time slots
    time_slots_data = [
        ('Monday', '09:00', '10:00', 'none'),
        ('Monday', '10:00', '11:00', 'short'),
        ('Tuesday', '09:00', '10:00', 'none'),
        ('Tuesday', '10:00', '11:00', 'short'),
        ('Wednesday', '09:00', '10:00', 'none'),
        ('Wednesday', '10:00', '11:00', 'short'),
        ('Thursday', '09:00', '10:00', 'none'),
        ('Thursday', '10:00', '11:00', 'short'),
        ('Friday', '09:00', '10:00', 'none'),
        ('Friday', '10:00', '11:00', 'short')
    ]
    
    for slot in time_slots_data:
        if db_type == 'postgresql':
            cursor.execute("""
                INSERT INTO time_slot (day, start_time, end_time, break_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (day, start_time, end_time) DO NOTHING
            """, slot)
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO time_slot (day, start_time, end_time, break_type)
                VALUES (?, ?, ?, ?)
            """, slot)
    
    conn.commit()
    print("✅ Sample data inserted successfully")

def verify_database_sync(conn, db_type):
    """Verify that the database is properly synchronized"""
    cursor = conn.cursor()
    
    print("\n🔍 Verifying database synchronization...")
    
    # Check table counts
    tables = ['user', 'course', 'classroom', 'time_slot', 'student_group', 'timetable', 'attendance', 'notification']
    
    for table in tables:
        if db_type == 'postgresql':
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        else:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        
        count = cursor.fetchone()[0]
        print(f"📊 {table.capitalize()}: {count} records")
    
    # Check specific data
    if db_type == 'postgresql':
        cursor.execute('SELECT username, role FROM "user" LIMIT 5')
    else:
        cursor.execute('SELECT username, role FROM "user" LIMIT 5')
    
    users = cursor.fetchall()
    print(f"\n👥 Sample users: {len(users)} found")
    for user in users:
        print(f"   • {user[0]} ({user[1]})")
    
    print("\n✅ Database synchronization verification completed")

def main():
    """Main synchronization function"""
    print("🔄 Database Synchronization Script")
    print("=" * 50)
    
    # Detect environment
    env = detect_environment()
    print(f"🌍 Environment detected: {env.upper()}")
    
    # Get database connection
    conn = get_database_connection()
    if not conn:
        print("❌ Failed to establish database connection")
        sys.exit(1)
    
    try:
        # Determine database type
        db_type = get_database_type(conn)
        print(f"🗄️ Database type: {db_type.upper()}")
        
        # Create tables
        print("\n🏗️ Creating database tables...")
        if db_type == 'postgresql':
            create_tables_postgresql(conn)
        else:
            create_tables_sqlite(conn)
        
        # Insert sample data
        print("\n📝 Inserting sample data...")
        insert_sample_data(conn, db_type)
        
        # Verify synchronization
        verify_database_sync(conn, db_type)
        
        print(f"\n🎉 Database synchronization completed successfully for {env.upper()} environment!")
        print(f"📅 Synchronized at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error during synchronization: {e}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()
