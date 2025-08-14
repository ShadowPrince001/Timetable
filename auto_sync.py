#!/usr/bin/env python3
"""
Automatic Database Synchronization Script
This script can be scheduled to run frequently to keep databases in sync.
Use with cron, systemd timers, or deployment hooks.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def should_run_sync():
    """Determine if sync should run based on last sync time"""
    log_file = Path('last_sync.txt')
    
    if not log_file.exists():
        logger.info("No previous sync record found, running sync")
        return True
    
    try:
        with open(log_file, 'r') as f:
            last_sync_str = f.read().strip()
            last_sync = datetime.fromisoformat(last_sync_str)
            
        # Run sync if it's been more than 6 hours
        time_since_last = datetime.now() - last_sync
        if time_since_last > timedelta(hours=6):
            logger.info(f"Last sync was {time_since_last} ago, running sync")
            return True
        else:
            logger.info(f"Last sync was {time_since_last} ago, skipping")
            return False
            
    except Exception as e:
        logger.error(f"Error reading last sync time: {e}, running sync")
        return True

def record_sync_time():
    """Record the current sync time"""
    try:
        with open('last_sync.txt', 'w') as f:
            f.write(datetime.now().isoformat())
        logger.info("Sync time recorded")
    except Exception as e:
        logger.error(f"Error recording sync time: {e}")

def run_sync():
    """Run the database synchronization"""
    try:
        logger.info("🔄 Starting automatic database synchronization...")
        
        # Import and run sync
        from sync_databases_flask import sync_database
        
        start_time = time.time()
        sync_database()
        end_time = time.time()
        
        duration = end_time - start_time
        logger.info(f"✅ Database synchronization completed in {duration:.2f} seconds")
        
        # Record successful sync
        record_sync_time()
        return True
        
    except ImportError:
        logger.error("❌ sync_databases_flask.py not found")
        return False
    except Exception as e:
        logger.error(f"❌ Database synchronization failed: {e}")
        return False

def main():
    """Main function for automatic sync"""
    logger.info("🚀 Automatic Database Sync Started")
    logger.info(f"🌍 Environment: {os.getenv('RENDER', 'LOCAL')}")
    logger.info(f"📅 Current Time: {datetime.now().isoformat()}")
    
    # Check if we should run sync
    if not should_run_sync():
        logger.info("⏭️ Skipping sync based on time threshold")
        return 0
    
    # Run the sync
    if run_sync():
        logger.info("🎉 Automatic sync completed successfully")
        return 0
    else:
        logger.error("❌ Automatic sync failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⏹️ Sync interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
