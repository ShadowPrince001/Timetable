#!/usr/bin/env python3
"""
Migration script to fix QR Code table schema
Adds missing qr_code_image column to qr_code table
"""

import os
import sys
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_qr_code_schema():
    """Add missing qr_code_image column to qr_code table"""
    
    with app.app_context():
        try:
            print(f"Database engine: {db.engine.name}")
            print(f"Database URL: {db.engine.url}")
            
            # Check if the column already exists using a simpler approach
            try:
                # Try to query the column directly
                result = db.session.execute(text("SELECT qr_code_image FROM qr_code LIMIT 1"))
                print("✓ qr_code_image column already exists in qr_code table")
                return True
            except Exception as e:
                if "column" in str(e).lower() and "does not exist" in str(e).lower():
                    print("Column qr_code_image does not exist, will add it...")
                else:
                    print(f"Unexpected error checking column: {e}")
                    return False
            
            # Add the missing column
            print("Adding qr_code_image column to qr_code table...")
            
            # For PostgreSQL
            if db.engine.name == 'postgresql':
                print("Using PostgreSQL ALTER TABLE command...")
                db.session.execute(text("""
                    ALTER TABLE qr_code 
                    ADD COLUMN qr_code_image TEXT
                """))
                print("Column added successfully!")
            else:
                print(f"Unsupported database engine: {db.engine.name}")
                return False
            
            db.session.commit()
            print("✓ Successfully committed changes to database")
            return True
            
        except OperationalError as e:
            print(f"OperationalError adding column: {e}")
            db.session.rollback()
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def verify_schema():
    """Verify the current schema of qr_code table"""
    
    with app.app_context():
        try:
            print("\nVerifying schema...")
            
            # For PostgreSQL, use a simpler approach
            if db.engine.name == 'postgresql':
                result = db.session.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'qr_code'
                    ORDER BY ordinal_position
                """))
                
                print("\nCurrent qr_code table schema:")
                print("-" * 50)
                for row in result:
                    print(f"{row.column_name:<20} {row.data_type:<15} {row.is_nullable}")
            else:
                print(f"Cannot verify schema for {db.engine.name}")
            
        except Exception as e:
            print(f"Error verifying schema: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("QR Code Schema Migration Script")
    print("=" * 40)
    
    if fix_qr_code_schema():
        print("\nMigration completed successfully!")
        verify_schema()
    else:
        print("\nMigration failed!")
        sys.exit(1)
