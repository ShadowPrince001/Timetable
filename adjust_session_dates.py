#!/usr/bin/env python3
"""
Adjust Session Dates for Testing
Adjusts academic session dates to include today for testing purposes.
"""

from app import app, db
from datetime import date, timedelta
from app import AcademicSession

def adjust_session_dates():
    """Adjust session dates to include today for testing"""
    print("🔧 Adjusting Session Dates for Testing")
    print("=" * 50)
    
    with app.app_context():
        try:
            today = date.today()
            print(f"📅 Today's date: {today}")
            
            # Get all sessions
            sessions = AcademicSession.query.all()
            print(f"\n📚 Found {len(sessions)} academic sessions")
            
            for session in sessions:
                print(f"\n📅 Session: {session.name}")
                print(f"   Current: {session.start_date} to {session.end_date}")
                
                # Check if today is within the session
                if session.start_date <= today <= session.end_date:
                    print(f"   ✅ Today is within this session")
                else:
                    print(f"   ❌ Today is outside this session")
                    
                    # Extend the session to include today
                    if today < session.start_date:
                        # Today is before session start, extend start date
                        new_start = today
                        new_end = session.end_date
                    else:
                        # Today is after session end, extend end date
                        new_start = session.start_date
                        new_end = today + timedelta(days=30)  # Extend by 30 days
                    
                    print(f"   🔧 Adjusting to: {new_start} to {new_end}")
                    
                    session.start_date = new_start
                    session.end_date = new_end
            
            # Commit changes
            db.session.commit()
            print(f"\n✅ Session dates adjusted successfully!")
            
            # Verify the changes
            print(f"\n🔍 Verifying changes:")
            for session in sessions:
                print(f"   📅 {session.name}: {session.start_date} to {session.end_date}")
                if session.start_date <= today <= session.end_date:
                    print(f"      ✅ Today is now within this session")
                else:
                    print(f"      ❌ Today is still outside this session")
            
        except Exception as e:
            print(f"❌ Error adjusting session dates: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    adjust_session_dates()
