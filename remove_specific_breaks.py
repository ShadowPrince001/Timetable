#!/usr/bin/env python3
"""
Script to manually remove specific breaks on Wednesday and Friday from 11:15 to 12:15
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def remove_specific_breaks():
    """Remove breaks on Wednesday and Friday from 11:15 to 12:15"""
    
    with app.app_context():
        try:
            print("Removing specific breaks on Wednesday and Friday (11:15-12:15)...")
            
            # Check current state
            result = db.session.execute(text("""
                SELECT day, start_time, end_time, break_type 
                FROM time_slot 
                WHERE (day = 'Wednesday' OR day = 'Friday') 
                AND start_time = '11:15' 
                AND end_time = '12:15'
                ORDER BY day
            """))
            
            print("\nCurrent state of the specific time slots:")
            print("-" * 50)
            for row in result:
                print(f"{row.day} {row.start_time}-{row.end_time}: {row.break_type}")
            
            # Update the specific breaks to regular time slots
            print("\nConverting breaks to regular time slots...")
            
            if db.engine.name == 'postgresql':
                db.session.execute(text("""
                    UPDATE time_slot 
                    SET break_type = 'none' 
                    WHERE (day = 'Wednesday' OR day = 'Friday') 
                    AND start_time = '11:15' 
                    AND end_time = '12:15'
                    AND break_type = 'Break'
                """))
            else:
                db.session.execute(text("""
                    UPDATE time_slot 
                    SET break_type = 'none' 
                    WHERE (day = 'Wednesday' OR day = 'Friday') 
                    AND start_time = '11:15' 
                    AND end_time = '12:15'
                    AND break_type = 'Break'
                """))
            
            db.session.commit()
            print("✓ Successfully updated break types")
            
            # Verify the changes
            result = db.session.execute(text("""
                SELECT day, start_time, end_time, break_type 
                FROM time_slot 
                WHERE (day = 'Wednesday' OR day = 'Friday') 
                AND start_time = '11:15' 
                AND end_time = '12:15'
                ORDER BY day
            """))
            
            print("\nUpdated state of the specific time slots:")
            print("-" * 50)
            for row in result:
                print(f"{row.day} {row.start_time}-{row.end_time}: {row.break_type}")
            
            # Set flag for timetable regeneration
            from flask import session
            session['timetable_regeneration_required'] = True
            print("\n✓ Flag set: Timetable regeneration may be needed")
            
            return True
            
        except Exception as e:
            print(f"Error removing specific breaks: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("Remove Specific Breaks Script")
    print("=" * 40)
    
    if remove_specific_breaks():
        print("\nOperation completed successfully!")
        print("\nThe breaks on Wednesday and Friday (11:15-12:15) have been removed.")
        print("These time slots are now available for classes.")
    else:
        print("\nOperation failed!")
        sys.exit(1)
