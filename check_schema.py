import sqlite3

def check_qr_code_schema():
    try:
        # Connect to the database
        conn = sqlite3.connect('instance/timetable_attendance.db')
        cursor = conn.cursor()
        
        # Check qr_code table structure
        cursor.execute("PRAGMA table_info(qr_code)")
        columns = cursor.fetchall()
        
        print("Current QR Code table schema:")
        print("-" * 50)
        for col in columns:
            print(f"Column {col[1]}: {col[2]} {'(NOT NULL)' if col[3] else '(NULL)'} {'(PRIMARY KEY)' if col[5] else ''}")
        
        # Check if qr_code_image column exists
        has_qr_code_image = any(col[1] == 'qr_code_image' for col in columns)
        print(f"\nqr_code_image column exists: {has_qr_code_image}")
        
        if not has_qr_code_image:
            print("Need to add qr_code_image column!")
        
        conn.close()
        return has_qr_code_image
        
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False

if __name__ == "__main__":
    check_qr_code_schema()
