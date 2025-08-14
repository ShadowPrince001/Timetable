from app import app, init_db
import os
import sys

# Initialize database when app starts (for production deployment)
with app.app_context():
    try:
        print("🔄 Starting automatic database synchronization...")
        init_db()
        print("✅ Database initialization completed")
        
        # Import and run sync script for additional data consistency
        try:
            from sync_databases_flask import sync_database
            sync_database()
            print("✅ Database synchronization completed")
        except ImportError:
            print("ℹ️ Sync script not available, using init_db only")
        except Exception as e:
            print(f"⚠️ Sync script failed: {e}, continuing with init_db only")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Continue running the app even if DB init fails

if __name__ == "__main__":
    app.run()
