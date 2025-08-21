#!/usr/bin/env python3
"""
Initialize database tables on Render's PostgreSQL
Run this ONCE on Render after deployment to create table structure
"""

import os
from app import app, db

def init_render_database():
    """Initialize database tables on Render"""
    print("🚀 Initializing Render PostgreSQL Database...")
    print("=" * 60)
    
    try:
        # Check if we're on Render (PostgreSQL)
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found. Are you on Render?")
            return False
        
        if 'postgresql' in database_url or 'postgres' in database_url:
            print("✅ Connected to Render's PostgreSQL database")
        else:
            print("❌ Not connected to PostgreSQL. Are you on Render?")
            return False
        
        # Create all tables
        print("\n📊 Creating database tables...")
        with app.app_context():
            db.create_all()
            print("✅ All tables created successfully!")
        
        # Verify tables were created
        print("\n🔍 Verifying table creation...")
        with app.app_context():
            # Get table names
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"📋 Tables created: {len(tables)}")
            for table in tables:
                print(f"  - {table}")
        
        print("\n🎉 Database initialization complete!")
        print("\n📋 Next Steps:")
        print("1. ✅ Tables are now created on Render")
        print("2. 📥 Download your migration script")
        print("3. 🚀 Run migration to populate data")
        print("4. 🧪 Test your app on Render")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("\n🔧 Troubleshooting:")
        print("- Make sure you're running this on Render")
        print("- Check that DATABASE_URL is set correctly")
        print("- Verify database connection")
        return False

if __name__ == "__main__":
    init_render_database()
