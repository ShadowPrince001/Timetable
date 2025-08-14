from app import app, init_db
import os
import sys

# Initialize database when app starts (for production deployment)
with app.app_context():
    try:
        print("🔄 Starting automatic database synchronization...")
        init_db()
        print("✅ Database initialization completed")
        
        # Optional: run sync script
        try:
            from sync_databases_flask import sync_database
            sync_database()
            print("✅ Database synchronization completed")
        except Exception as e:
            print(f"ℹ️ Sync script unavailable or failed ({e}); continuing")

        # Optional: seed demo data if requested by env var
        if os.getenv('SEED_DEMO', '0') == '1':
            try:
                from seed_demo_data import seed_demo_data
                seed_demo_data()
                print("✅ Demo data seeding completed")
            except Exception as e:
                print(f"⚠️ Demo data seeding failed: {e}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Continue running the app even if DB init fails

if __name__ == "__main__":
    app.run()
