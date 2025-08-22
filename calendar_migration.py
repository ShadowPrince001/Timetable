#!/usr/bin/env python3
"""
Calendar Migration Script
Transitions the timetable system from week-based to calendar-based with academic years, sessions, and holidays.
"""

import os
import sys
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import app and models
from app import app, db, AcademicYear, AcademicSession, Holiday, ClassInstance, Timetable, Attendance, TimeSlot

# Load environment variables if .env file exists
try:
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    # Set default environment variables
    import os
    if not os.getenv('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    if not os.getenv('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'your-secret-key-here'

def create_database_engine():
    """Create database engine based on environment"""
    database_url = os.getenv('DATABASE_URL')
    flask_env = os.getenv('FLASK_ENV', 'development')
    
    if database_url:
        # PostgreSQL (production)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return create_engine(database_url)
    elif flask_env == 'production':
        raise ValueError("DATABASE_URL environment variable must be set in production")
    else:
        # SQLite (development)
        return create_engine(f'sqlite:///{os.path.join(app.instance_path, "timetable_attendance.db")}')

def create_default_academic_year():
    """Create a default academic year for the current year"""
    current_year = datetime.now().year
    
    # Create academic year (e.g., 2024-2025)
    academic_year = AcademicYear(
        name=f"{current_year}-{current_year + 1}",
        start_date=date(current_year, 9, 1),  # September 1st
        end_date=date(current_year + 1, 8, 31),  # August 31st next year
        is_active=True
    )
    
    return academic_year

def create_default_sessions(academic_year):
    """Create default academic sessions for the academic year"""
    current_year = datetime.now().year
    
    sessions = [
        {
            'name': 'Fall Semester',
            'start_date': date(current_year, 9, 1),
            'end_date': date(current_year, 12, 20),
            'session_type': 'semester'
        },
        {
            'name': 'Spring Semester',
            'start_date': date(current_year + 1, 1, 15),
            'end_date': date(current_year + 1, 5, 15),
            'session_type': 'semester'
        },
        {
            'name': 'Summer Session',
            'start_date': date(current_year + 1, 6, 1),
            'end_date': date(current_year + 1, 8, 15),
            'session_type': 'semester'
        }
    ]
    
    created_sessions = []
    for session_data in sessions:
        session = AcademicSession(
            name=session_data['name'],
            academic_year_id=academic_year.id,
            start_date=session_data['start_date'],
            end_date=session_data['end_date'],
            session_type=session_data['session_type']
        )
        created_sessions.append(session)
    
    return created_sessions

def create_default_holidays(academic_year):
    """Create default holidays for the academic year"""
    current_year = datetime.now().year
    
    holidays = [
        {
            'name': 'Labor Day',
            'start_date': date(current_year, 9, 2),
            'end_date': date(current_year, 9, 2),
            'is_recurring': True,
            'description': 'Labor Day Holiday'
        },
        {
            'name': 'Thanksgiving Break',
            'start_date': date(current_year, 11, 25),
            'end_date': date(current_year, 11, 29),
            'is_recurring': True,
            'description': 'Thanksgiving Holiday Break'
        },
        {
            'name': 'Christmas Break',
            'start_date': date(current_year, 12, 23),
            'end_date': date(current_year, 12, 31),
            'is_recurring': True,
            'description': 'Christmas and New Year Break'
        },
        {
            'name': 'Martin Luther King Jr. Day',
            'start_date': date(current_year + 1, 1, 20),
            'end_date': date(current_year + 1, 1, 20),
            'is_recurring': True,
            'description': 'Martin Luther King Jr. Day'
        },
        {
            'name': 'Spring Break',
            'start_date': date(current_year + 1, 3, 10),
            'end_date': date(current_year + 1, 3, 14),
            'is_recurring': True,
            'description': 'Spring Break'
        },
        {
            'name': 'Easter Break',
            'start_date': date(current_year + 1, 4, 5),
            'end_date': date(current_year + 1, 4, 7),
            'is_recurring': True,
            'description': 'Easter Holiday'
        },
        {
            'name': 'Memorial Day',
            'start_date': date(current_year + 1, 5, 26),
            'end_date': date(current_year + 1, 5, 26),
            'is_recurring': True,
            'description': 'Memorial Day'
        },
        {
            'name': 'Independence Day',
            'start_date': date(current_year + 1, 7, 4),
            'end_date': date(current_year + 1, 7, 4),
            'is_recurring': True,
            'description': 'Independence Day'
        }
    ]
    
    created_holidays = []
    for holiday_data in holidays:
        holiday = Holiday(
            name=holiday_data['name'],
            academic_year_id=academic_year.id,
            start_date=holiday_data['start_date'],
            end_date=holiday_data['end_date'],
            is_recurring=holiday_data['is_recurring'],
            description=holiday_data['description']
        )
        created_holidays.append(holiday)
    
    return created_holidays

def migrate_existing_timetables(academic_year, fall_session):
    """Migrate existing timetables to the new calendar system"""
    print("🔄 Migrating existing timetables...")
    
    # Get all existing timetables
    existing_timetables = Timetable.query.all()
    
    migrated_count = 0
    for timetable in existing_timetables:
        try:
            # Update timetable with new academic year and session references
            timetable.academic_year_id = academic_year.id
            timetable.session_id = fall_session.id
            
            # Map old semester field to session if possible
            if timetable.semester and 'fall' in timetable.semester.lower():
                timetable.session_id = fall_session.id
            elif timetable.semester and 'spring' in timetable.semester.lower():
                # Find spring session
                spring_session = AcademicSession.query.filter_by(
                    academic_year_id=academic_year.id,
                    name='Spring Semester'
                ).first()
                if spring_session:
                    timetable.session_id = spring_session.id
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error migrating timetable {timetable.id}: {e}")
    
    print(f"✅ Migrated {migrated_count} timetables")
    return migrated_count

def migrate_existing_attendance(academic_year, fall_session):
    """Migrate existing attendance records to the new calendar system"""
    print("🔄 Migrating existing attendance records...")
    
    # Get all existing attendance records
    existing_attendance = Attendance.query.all()
    
    migrated_count = 0
    for attendance in existing_attendance:
        try:
            # Update attendance with new academic year and session references
            attendance.academic_year_id = academic_year.id
            attendance.session_id = fall_session.id
            
            # Determine session based on date
            if attendance.date:
                if attendance.date.month >= 9 or attendance.date.month <= 12:
                    # Fall semester
                    attendance.session_id = fall_session.id
                elif attendance.date.month >= 1 and attendance.date.month <= 5:
                    # Spring semester
                    spring_session = AcademicSession.query.filter_by(
                        academic_year_id=academic_year.id,
                        name='Spring Semester'
                    ).first()
                    if spring_session:
                        attendance.session_id = spring_session.id
                elif attendance.date.month >= 6 and attendance.date.month <= 8:
                    # Summer session
                    summer_session = AcademicSession.query.filter_by(
                        academic_year_id=academic_year.id,
                        name='Summer Session'
                    ).first()
                    if summer_session:
                        attendance.session_id = summer_session.id
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error migrating attendance {attendance.id}: {e}")
    
    print(f"✅ Migrated {migrated_count} attendance records")
    return migrated_count

def generate_class_instances(academic_year, session):
    """Generate class instances for all timetables in a session"""
    print(f"🔄 Generating class instances for {session.name}...")
    
    # Get all timetables for this session
    timetables = Timetable.query.filter_by(
        academic_year_id=academic_year.id,
        session_id=session.id
    ).all()
    
    total_instances = 0
    
    for timetable in timetables:
        try:
            # Get the time slot to determine the day of week
            time_slot = TimeSlot.query.get(timetable.time_slot_id)
            if not time_slot:
                continue
            
            # Map day names to weekday numbers (Monday=0, Sunday=6)
            day_mapping = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            
            weekday = day_mapping.get(time_slot.day)
            if weekday is None:
                continue
            
            # Generate class instances for each week in the session
            current_date = session.start_date
            while current_date <= session.end_date:
                # Check if this date falls on the correct weekday
                if current_date.weekday() == weekday:
                    # Check if this date is a holiday
                    holiday = Holiday.query.filter(
                        Holiday.academic_year_id == academic_year.id,
                        Holiday.start_date <= current_date,
                        Holiday.end_date >= current_date
                    ).first()
                    
                    if not holiday:
                        # Create class instance
                        class_instance = ClassInstance(
                            timetable_id=timetable.id,
                            class_date=current_date
                        )
                        db.session.add(class_instance)
                        total_instances += 1
                
                current_date += timedelta(days=1)
            
        except Exception as e:
            print(f"❌ Error generating class instances for timetable {timetable.id}: {e}")
    
    print(f"✅ Generated {total_instances} class instances for {session.name}")
    return total_instances

def run_migration():
    """Run the complete migration process"""
    print("🚀 Starting Calendar Migration Process")
    print("=" * 60)
    
    try:
        # Create application context
        ctx = app.app_context()
        ctx.push()
        
        try:
            # Create database tables
            print("📋 Creating new database tables...")
            db.create_all()
            print("✅ Database tables created")
            
            # Check if academic year already exists
            existing_year = AcademicYear.query.filter_by(is_active=True).first()
            if existing_year:
                print(f"⚠️  Active academic year already exists: {existing_year.name}")
                response = input("Do you want to continue with migration? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Migration cancelled")
                    return
            
            # Create default academic year
            print("📅 Creating default academic year...")
            academic_year = create_default_academic_year()
            db.session.add(academic_year)
            db.session.commit()
            print(f"✅ Created academic year: {academic_year.name}")
            
            # Create default sessions
            print("📚 Creating default academic sessions...")
            sessions = create_default_sessions(academic_year)
            for session in sessions:
                db.session.add(session)
            db.session.commit()
            print(f"✅ Created {len(sessions)} academic sessions")
            
            # Create default holidays
            print("🎉 Creating default holidays...")
            holidays = create_default_holidays(academic_year)
            for holiday in holidays:
                db.session.add(holiday)
            db.session.commit()
            print(f"✅ Created {len(holidays)} holidays")
            
            # Get fall session for migration
            fall_session = AcademicSession.query.filter_by(
                academic_year_id=academic_year.id,
                name='Fall Semester'
            ).first()
            
            # Migrate existing data
            print("🔄 Starting data migration...")
            migrated_timetables = migrate_existing_timetables(academic_year, fall_session)
            migrated_attendance = migrate_existing_attendance(academic_year, fall_session)
            
            # Commit migration changes
            db.session.commit()
            print("✅ Data migration completed")
            
            # Generate class instances for all sessions
            print("📅 Generating class instances...")
            total_instances = 0
            for session in sessions:
                instances = generate_class_instances(academic_year, session)
                total_instances += instances
            
            db.session.commit()
            print(f"✅ Generated {total_instances} total class instances")
            
            print("\n" + "=" * 60)
            print("🎉 Migration completed successfully!")
            print(f"📊 Migration Summary:")
            print(f"   • Academic Year: {academic_year.name}")
            print(f"   • Sessions: {len(sessions)}")
            print(f"   • Holidays: {len(holidays)}")
            print(f"   • Migrated Timetables: {migrated_timetables}")
            print(f"   • Migrated Attendance Records: {migrated_attendance}")
            print(f"   • Generated Class Instances: {total_instances}")
            print("\n🚀 The system is now ready for calendar-based operations!")
            
        finally:
            ctx.pop()
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

if __name__ == "__main__":
    run_migration()
