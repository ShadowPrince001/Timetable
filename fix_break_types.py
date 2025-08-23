#!/usr/bin/env python3
"""
Migration script to fix inconsistent break types
Standardizes all break types to 'Break' and removes old break types
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_break_types():
    """Standardize all break types to 'Break'"""
    
    with app.app_context():
        try:
            print("Fixing inconsistent break types...")
            
            # Check current break type distribution
            result = db.session.execute(text("""
                SELECT break_type, COUNT(*) as count
                FROM time_slot 
                GROUP BY break_type
                ORDER BY break_type
            """))
            
            print("\nCurrent break type distribution:")
            print("-" * 40)
            for row in result:
                print(f"{row.break_type}: {row.count} slots")
            
            # Update all non-'none' break types to 'Break'
            print("\nUpdating break types...")
            
            if db.engine.name == 'postgresql':
                db.session.execute(text("""
                    UPDATE time_slot 
                    SET break_type = 'Break' 
                    WHERE break_type NOT IN ('none', 'Break')
                """))
            else:
                db.session.execute(text("""
                    UPDATE time_slot 
                    SET break_type = 'Break' 
                    WHERE break_type NOT IN ('none', 'Break')
                """))
            
            db.session.commit()
            print("✓ Successfully updated break types")
            
            # Verify the changes
            result = db.session.execute(text("""
                SELECT break_type, COUNT(*) as count
                FROM time_slot 
                GROUP BY break_type
                ORDER BY break_type
            """))
            
            print("\nUpdated break type distribution:")
            print("-" * 40)
            for row in result:
                print(f"{row.break_type}: {row.count} slots")
            
            return True
            
        except Exception as e:
            print(f"Error fixing break types: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def verify_break_consistency():
    """Verify that all breaks are now consistent"""
    
    with app.app_context():
        try:
            # Check if any inconsistent break types remain
            result = db.session.execute(text("""
                SELECT COUNT(*) as count
                FROM time_slot 
                WHERE break_type NOT IN ('none', 'Break')
            """))
            
            inconsistent_count = result.fetchone().count
            
            if inconsistent_count == 0:
                print("✓ All break types are now consistent!")
                return True
            else:
                print(f"❌ {inconsistent_count} inconsistent break types remain")
                return False
                
        except Exception as e:
            print(f"Error verifying consistency: {e}")
            return False

if __name__ == "__main__":
    print("Break Type Standardization Script")
    print("=" * 40)
    
    if fix_break_types():
        print("\nMigration completed successfully!")
        verify_break_consistency()
    else:
        print("\nMigration failed!")
        sys.exit(1)
