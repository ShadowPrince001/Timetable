# 🔄 Database Synchronization Guide

This guide explains how to synchronize your database across different environments:
- **Local Workspace** (Windows/Mac/Linux)
- **GitHub Codespace** (Cloud development)
- **Render Production** (Live deployment)

## 🎯 Why Database Synchronization?

Different environments often have different database states:
- **Local**: May have test data or be empty
- **Codespace**: Fresh environment, no data
- **Render**: Production database, may be outdated

The sync scripts ensure all environments have:
- ✅ **Identical database schemas**
- ✅ **Same sample data**
- ✅ **Consistent user accounts**
- ✅ **Working timetables**

## 📁 Available Sync Scripts

### 1. **`sync_databases_flask.py`** (Recommended)
- **Flask-integrated** sync script
- **Automatic environment detection**
- **Uses existing app models**
- **Safe data insertion** (no duplicates)

### 2. **`sync_databases.py`**
- **Standalone** sync script
- **Direct database connections**
- **Manual environment setup**
- **Raw SQL operations**

### 3. **`sync_database.bat`** (Windows)
- **Double-click to run**
- **User-friendly interface**
- **Automatic execution**

### 4. **`sync_database.ps1`** (PowerShell)
- **PowerShell execution**
- **Colored output**
- **Better error handling**

## 🚀 Quick Start

### **Option 1: Python Script (Recommended)**
```bash
# Navigate to project directory
cd D:\Timetable

# Run the Flask-based sync script
python sync_databases_flask.py
```

### **Option 2: Windows Batch File**
```bash
# Double-click the file or run from command line
sync_database.bat
```

### **Option 3: PowerShell Script**
```powershell
# Run from PowerShell
.\sync_database.ps1
```

## 🔧 Manual Execution Steps

### **Step 1: Activate Virtual Environment**
```bash
# Windows
.\.venv\Scripts\Activate

# Mac/Linux
source .venv/bin/activate
```

### **Step 2: Run Sync Script**
```bash
python sync_databases_flask.py
```

### **Step 3: Verify Results**
The script will show:
- ✅ Environment detection
- ✅ Table creation
- ✅ Sample data insertion
- ✅ Final verification

## 🌍 Environment Detection

The scripts automatically detect your environment:

| Environment | Detection Method | Database Type |
|-------------|------------------|---------------|
| **Local** | No special env vars | SQLite |
| **Codespace** | `CODESPACES` env var | SQLite |
| **Render** | `RENDER` env var | PostgreSQL |

## 📊 What Gets Synchronized

### **Database Tables**
- ✅ **Users** (admin, faculty, students)
- ✅ **Courses** (CS101, MATH101, etc.)
- ✅ **Classrooms** (101, 205, etc.)
- ✅ **TimeSlots** (Monday-Friday schedules)
- ✅ **StudentGroups** (CS-2024-1, etc.)
- ✅ **Timetables** (class schedules)
- ✅ **Attendance** (student records)
- ✅ **Notifications** (system alerts)
- ✅ **CourseTeachers** (course assignments)

### **Sample Data**
- **Admin User**: `admin` / `admin123`
- **Faculty User**: `faculty` / `faculty123`
- **Student User**: `student` / `student123`
- **Sample Courses**: Computer Science, Mathematics
- **Sample Classrooms**: Science Building, Math Building
- **Time Slots**: Monday-Friday, 9 AM - 11 AM

## 🔒 Safety Features

### **Duplicate Prevention**
- **ON CONFLICT DO NOTHING** (PostgreSQL)
- **INSERT OR IGNORE** (SQLite)
- **Existing data preserved**

### **Transaction Safety**
- **Automatic rollback** on errors
- **Atomic operations**
- **Data consistency checks**

### **Environment Awareness**
- **Automatic database type detection**
- **Environment-specific optimizations**
- **Safe connection handling**

## 🐛 Troubleshooting

### **Common Issues**

#### **1. Import Errors**
```bash
# Error: No module named 'app'
# Solution: Ensure you're in the project directory
cd D:\Timetable
```

#### **2. Database Connection Errors**
```bash
# Error: Database locked
# Solution: Close any running Flask app
# Then run sync script
```

#### **3. Permission Errors**
```bash
# Error: Permission denied
# Solution: Run as administrator or check file permissions
```

#### **4. Virtual Environment Issues**
```bash
# Error: Module not found
# Solution: Activate virtual environment first
.\.venv\Scripts\Activate
```

### **Debug Mode**
```bash
# Run with verbose output
python -v sync_databases_flask.py
```

## 📋 Pre-Sync Checklist

Before running the sync script:

- ✅ **Project directory** is correct
- ✅ **Virtual environment** is activated
- ✅ **No Flask app** is running
- ✅ **Database files** are not locked
- ✅ **Sufficient permissions** to write files

## 🔄 Post-Sync Verification

After synchronization, verify:

1. **Database file exists** in `instance/` folder
2. **All tables created** successfully
3. **Sample data inserted** (users, courses, etc.)
4. **Flask app runs** without errors
5. **Login works** with sample accounts

## 🚀 Production Deployment (Render)

### **Automatic Sync**
The `wsgi.py` file automatically calls `init_db()` on startup, ensuring:
- ✅ **Database tables created** on first run
- ✅ **Sample data inserted** automatically
- ✅ **No manual intervention** required

### **Manual Sync (if needed)**
```bash
# Access Render shell
# Run sync script
python sync_databases_flask.py
```

## 📈 Performance Notes

### **Sync Time Estimates**
- **Local SQLite**: 2-5 seconds
- **Codespace SQLite**: 3-7 seconds
- **Render PostgreSQL**: 5-15 seconds

### **Data Size**
- **Sample Users**: ~8 records
- **Sample Courses**: ~4 records
- **Sample Classrooms**: ~6 records
- **Time Slots**: ~35 records
- **Total**: ~53 records

## 🔄 Regular Maintenance

### **When to Sync**
- ✅ **New environment setup**
- ✅ **After major schema changes**
- ✅ **Before important testing**
- ✅ **After database corruption**
- ✅ **Before production deployment**

### **Sync Frequency**
- **Development**: Every few days
- **Testing**: Before each test cycle
- **Production**: Only when needed

## 📞 Support

If you encounter issues:

1. **Check the error messages** carefully
2. **Verify environment setup**
3. **Ensure virtual environment is active**
4. **Check file permissions**
5. **Review the troubleshooting section**

## 🎉 Success Indicators

You'll know the sync worked when you see:

```
🎉 Database synchronization completed successfully for LOCAL environment!
📅 Synchronized at: 2025-08-14 17:32:21
📊 Final database state:
   • Users: 8 records
   • Courses: 4 records
   • Classrooms: 6 records
   • TimeSlots: 35 records
   • StudentGroups: 3 records
   • Timetables: 3 records
```

---

**Happy Synchronizing! 🚀✨**
