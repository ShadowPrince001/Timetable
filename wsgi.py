from app import app
import os
import sys

# Optional: run sync script
with app.app_context():
    try:
        from sync_databases_flask import sync_database
        sync_database()
        print("✅ Database synchronization completed")
    except Exception as e:
        print(f"ℹ️ Sync script unavailable or failed ({e}); continuing")

if __name__ == "__main__":
    app.run()
