from app import app
import os
import sys

# Set database URL for local development (same pattern as app.py)
if not os.getenv('DATABASE_URL'):
    # For local development, use SQLite
    os.environ['DATABASE_URL'] = 'sqlite:///timetable_attendance.db'

# Note: Database sync functionality has been removed
# The application will work with the local SQLite database

if __name__ == "__main__":
    app.run()
