#!/usr/bin/env python3
"""
Deployment Hook Script
This script ensures database synchronization runs automatically during deployment.
It can be called by deployment scripts, CI/CD pipelines, or manually.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_deployment_sync():
    """Run database synchronization during deployment"""
    print("🚀 Deployment Hook: Database Synchronization")
    print("=" * 60)
    print(f"📅 Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 Environment: {os.getenv('RENDER', 'LOCAL')}")
    
    try:
        # Check if we're in the right directory
        if not os.path.exists('app.py'):
            print("❌ Error: app.py not found. Please run from project root.")
            return False
        
        # Run the Flask-based sync script
        print("\n🔄 Running database synchronization...")
        result = subprocess.run([
            sys.executable, 'sync_databases_flask.py'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ Database synchronization completed successfully")
            print("\n📊 Sync Output:")
            print(result.stdout)
            return True
        else:
            print("❌ Database synchronization failed")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Deployment hook failed: {e}")
        return False

def run_init_db_only():
    """Fallback: Run only init_db if sync script fails"""
    print("\n🔄 Fallback: Running init_db only...")
    try:
        from app import app, init_db
        
        with app.app_context():
            init_db()
            print("✅ init_db completed successfully")
            return True
    except Exception as e:
        print(f"❌ init_db failed: {e}")
        return False

def main():
    """Main deployment hook function"""
    print("🎯 Starting deployment process...")
    
    # Try the full sync first
    if run_deployment_sync():
        print("\n🎉 Deployment completed successfully!")
        return 0
    else:
        print("\n⚠️ Full sync failed, trying fallback...")
        
        # Fallback to init_db only
        if run_init_db_only():
            print("\n✅ Fallback deployment completed")
            return 0
        else:
            print("\n❌ All deployment methods failed")
            return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
