#!/usr/bin/env python3
"""
Script to fix QR code sequence issues in the database
Run this script when you encounter "duplicate key value violates unique constraint" errors
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_qr_sequence():
    """Fix the QR code sequence issue"""
    with app.app_context():
        try:
            # Check if we're using PostgreSQL
            database_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if 'postgresql' in database_uri:
                print("🔍 Detected PostgreSQL database")
                
                # Get the current maximum ID from qr_code table
                result = db.session.execute(db.text("SELECT COALESCE(MAX(id), 0) FROM qr_code"))
                max_id = result.scalar()
                print(f"📊 Current maximum QR code ID: {max_id}")
                
                if max_id is not None:
                    # Reset the sequence to start from max_id + 1
                    db.session.execute(db.text(f"SELECT setval('qr_code_id_seq', {max_id + 1}, false)"))
                    db.session.commit()
                    print(f"✅ Successfully reset qr_code sequence to {max_id + 1}")
                    
                    # Verify the fix
                    result = db.session.execute(db.text("SELECT currval('qr_code_id_seq')"))
                    current_seq = result.scalar()
                    print(f"🔍 Sequence now starts from: {current_seq}")
                    
                    return True
                else:
                    print("⚠️  No QR codes found in database")
                    return False
            else:
                print("ℹ️  SQLite database detected - sequence reset not needed")
                return True
                
        except Exception as e:
            print(f"❌ Error fixing sequence: {e}")
            return False

def main():
    """Main function"""
    print("🔧 QR Code Sequence Fix Tool")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Check if we're in the right environment
    if not os.getenv('DATABASE_URL') and not os.path.exists('instance'):
        print("⚠️  Warning: No DATABASE_URL found and no instance directory")
        print("   This script should be run from the project root directory")
        response = input("   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted")
            return
    
    print("🚀 Starting sequence fix...")
    
    if fix_qr_sequence():
        print("\n✅ Sequence fix completed successfully!")
        print("💡 You can now generate QR codes without errors")
    else:
        print("\n❌ Sequence fix failed!")
        print("💡 Check the error messages above for details")
        sys.exit(1)

if __name__ == "__main__":
    main()
