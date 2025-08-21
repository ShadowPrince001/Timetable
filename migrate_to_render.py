#!/usr/bin/env python3
"""
Migration script to transfer data from local SQLite to Render's PostgreSQL
Run this ONCE after deploying to Render to populate the production database
"""

import os
import sqlite3
from datetime import datetime

def get_sqlite_data():
    """Extract data from local SQLite database"""
    sqlite_path = os.path.join('instance', 'timetable_attendance.db')
    
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at: {sqlite_path}")
        return None
    
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        data = {}
        for table in tables:
            table_name = table[0]
            if table_name == 'sqlite_sequence':
                continue
                
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Get all data
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            
            data[table_name] = {
                'columns': column_names,
                'rows': rows
            }
            
            print(f"📊 Extracted {len(rows)} rows from {table_name}")
        
        conn.close()
        return data
        
    except Exception as e:
        print(f"❌ Error extracting SQLite data: {e}")
        return None

def generate_render_migration_script(data):
    """Generate PostgreSQL INSERT statements for Render"""
    if not data:
        return None
    
    script_lines = [
        "-- Render PostgreSQL Migration Script",
        f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Run this ONCE after deploying to Render to populate production database",
        "-- This script will transfer all your local data to Render's PostgreSQL",
        "",
        "BEGIN;",
        ""
    ]
    
    for table_name, table_data in data.items():
        if not table_data['rows']:
            continue
            
        script_lines.append(f"-- Inserting data into {table_name}")
        
        # Don't truncate - just insert (tables are empty in Render)
        for row in table_data['rows']:
            # Handle different data types
            formatted_values = []
            for value in row:
                if value is None:
                    formatted_values.append('NULL')
                elif isinstance(value, str):
                    # Escape single quotes
                    escaped_value = value.replace("'", "''")
                    formatted_values.append(f"'{escaped_value}'")
                elif isinstance(value, datetime):
                    formatted_values.append(f"'{value.isoformat()}'")
                else:
                    formatted_values.append(str(value))
            
            values_str = ', '.join(formatted_values)
            script_lines.append(f"INSERT INTO {table_name} VALUES ({values_str});")
        
        script_lines.append("")
    
    script_lines.extend([
        "COMMIT;",
        "",
        "-- Migration completed successfully!",
        f"-- {sum(len(table_data['rows']) for table_data in data.values())} total records migrated"
    ])
    
    return '\n'.join(script_lines)

def save_migration_script(script_content):
    """Save migration script to file"""
    try:
        filename = f"render_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, 'w') as f:
            f.write(script_content)
        
        print(f"✅ Migration script saved as: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving migration script: {e}")
        return None

def main():
    """Main migration function"""
    print("🚀 SQLite to Render PostgreSQL Migration Tool")
    print("=" * 60)
    print("This will create a script to migrate your data to Render's database")
    print("Run this ONCE after deploying to Render")
    print("=" * 60)
    
    # Extract SQLite data
    print("\n📊 Extracting data from local SQLite...")
    data = get_sqlite_data()
    
    if not data:
        print("❌ No data to migrate")
        return
    
    # Generate migration script
    print("\n📝 Generating Render migration script...")
    script = generate_render_migration_script(data)
    
    if not script:
        print("❌ Failed to generate migration script")
        return
    
    # Save migration script
    filename = save_migration_script(script)
    
    if filename:
        print(f"\n🎉 Migration script ready for Render!")
        print(f"\n📋 Migration Steps (after deploying to Render):")
        print(f"1. Deploy your app to Render (tables will be created automatically)")
        print(f"2. Download the migration script: {filename}")
        print(f"3. Connect to Render's PostgreSQL database:")
        print(f"   - Use Render's database connection details")
        print(f"   - Or use Render's database dashboard")
        print(f"4. Run the migration script to populate data")
        print(f"5. Verify data: Check user count, courses, etc.")
        
        print(f"\n📊 Data Summary:")
        total_records = sum(len(table_data['rows']) for table_data in data.values())
        print(f"- Total records to migrate: {total_records}")
        for table_name, table_data in data.items():
            if table_data['rows']:
                print(f"- {table_name}: {len(table_data['rows'])} records")
        
        print(f"\n⚠️  Important notes:")
        print(f"- Run this migration ONLY ONCE after deploying to Render")
        print(f"- Backup your local SQLite database before migration")
        print(f"- Migration preserves all your current data")
        print(f"- After migration, Render will have your complete dataset")

if __name__ == "__main__":
    main()
