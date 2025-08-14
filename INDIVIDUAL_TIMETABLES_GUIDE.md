# 🗓️ Individual Timetables System Guide

## Overview
The Timetable & Attendance System now provides **individual timetables** for each student group and each teacher, ensuring that every group and teacher has their own distinct schedule rather than a single shared timetable.

## 🎯 Key Features

### 1. **Individual Student Group Timetables**
- **Each student group gets its own timetable** with unique class schedules
- **Group-specific constraints** prevent double-booking within the same group
- **Visual weekly grid view** showing the complete schedule for each group
- **Quick access** from the main admin timetable page

### 2. **Individual Teacher Timetables**
- **Each teacher has their own teaching schedule** across all groups they teach
- **Teacher-specific views** showing all classes they're assigned to
- **Teaching statistics** including total classes, unique courses, and student groups
- **Quick access** from the users management page

### 3. **Smart Conflict Prevention**
- **No double-booking within groups**: A student group can't have two classes at the same time
- **No teacher conflicts**: A teacher can't teach two classes simultaneously
- **No classroom conflicts**: A classroom can't host two classes at the same time
- **Global resource management**: Ensures efficient use of classrooms and teachers

## 🏗️ Database Structure

### Timetable Model
```python
class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_group_id = db.Column(db.Integer, db.ForeignKey('student_group.id'), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
```

### Key Relationships
- **Each timetable entry belongs to ONE student group**
- **Each timetable entry has ONE teacher**
- **Each timetable entry uses ONE classroom and time slot**
- **Multiple groups can have different classes at the same time (in different classrooms)**

## 🚀 How to Access Individual Timetables

### For Administrators

#### 1. **From Main Timetable Page**
- Go to **Admin Dashboard → Manage Timetable**
- Scroll down to **"View Individual Timetables"** section
- Click on any **Student Group** button to view their timetable
- Click on any **Teacher** button to view their teaching schedule

#### 2. **From Student Groups Page**
- Go to **Admin Dashboard → Manage Student Groups**
- In the Actions column, click the **calendar icon** (📅) for any group
- This opens the individual group timetable view

#### 3. **From Users Page**
- Go to **Admin Dashboard → Manage Users**
- For faculty members, click the **calendar icon** (📅) in the Actions column
- This opens the individual teacher timetable view

### For Teachers
- Go to **Faculty Dashboard → My Timetable**
- View your personal teaching schedule across all groups

### For Students
- Go to **Student Dashboard → My Timetable**
- View your group's timetable (you see the same schedule as other students in your group)

## 📊 Individual Timetable Views

### Student Group Timetable View
- **Group Information Card**: Shows group name, department, year, and semester
- **Weekly Schedule Grid**: Visual representation of the week with all classes
- **Detailed Schedule List**: Tabular view with all timetable entries
- **Quick Actions**: Links to add entries, generate timetables, manage groups

### Teacher Timetable View
- **Teacher Information Card**: Shows teacher name, department, and qualifications
- **Weekly Teaching Schedule**: Visual grid showing all teaching assignments
- **Detailed Teaching Schedule**: List view with all classes they teach
- **Teaching Statistics**: Total classes, unique courses, student groups, classrooms
- **Quick Actions**: Links to add entries, generate timetables, manage courses

## 🔧 Creating Individual Timetables

### 1. **Manual Entry**
- Go to **Admin Dashboard → Manage Timetable**
- Click **"Add Timetable Entry"**
- Select the **student group** for this entry
- Choose **course**, **teacher**, **classroom**, and **time slot**
- The system automatically prevents conflicts

### 2. **Automatic Generation**
- Go to **Admin Dashboard → Generate Timetables**
- Click **"Generate Timetables"**
- The system creates individual timetables for all groups
- Each group gets its own schedule based on their assigned courses

### 3. **Bulk Operations**
- Use the **filter system** to view specific groups or teachers
- **Export timetables** for specific groups or teachers
- **Clear timetables** for specific groups if needed

## 🎨 Visual Features

### Weekly Grid View
- **Color-coded entries**: Different colors for different types of information
- **Responsive design**: Works on all device sizes
- **Clear time slots**: Easy to read time periods
- **Course information**: Shows course code, name, teacher, and classroom

### Statistics and Metrics
- **Total classes** for each group/teacher
- **Unique courses** being taught
- **Student groups** being served
- **Classrooms** being utilized

## 🔒 Conflict Prevention

### Group-Level Constraints
```python
# No double-booking within the same group
db.UniqueConstraint('student_group_id', 'classroom_id', 'time_slot_id', 'semester', 'academic_year')
db.UniqueConstraint('student_group_id', 'teacher_id', 'time_slot_id', 'semester', 'academic_year')
```

### Global Resource Constraints
```python
# No classroom conflicts across groups
db.UniqueConstraint('classroom_id', 'time_slot_id', 'semester', 'academic_year')
# No teacher conflicts across groups
db.UniqueConstraint('teacher_id', 'time_slot_id', 'semester', 'academic_year')
```

## 📱 Mobile Responsiveness

- **All individual timetable views** are mobile-friendly
- **Touch-friendly buttons** for mobile devices
- **Responsive grid layouts** that adapt to screen size
- **Optimized for tablets** and smartphones

## 🚀 Benefits of Individual Timetables

### For Students
- **Clear group schedule**: Know exactly when your group has classes
- **No confusion**: Each group has its own distinct timetable
- **Easy navigation**: Simple weekly view of your schedule

### For Teachers
- **Personal teaching schedule**: See all your classes in one place
- **Group management**: Know which groups you're teaching
- **Time management**: Plan your day efficiently

### For Administrators
- **Group oversight**: Monitor each group's schedule separately
- **Teacher workload**: Track individual teacher assignments
- **Resource optimization**: Ensure efficient use of classrooms and time slots
- **Conflict resolution**: Easy to identify and fix scheduling issues

## 🔍 Troubleshooting

### Common Issues

#### 1. **"No Timetable Available" Message**
- **Cause**: Group has no assigned courses or timetable entries
- **Solution**: Assign courses to the group or generate timetables

#### 2. **Missing Teacher Information**
- **Cause**: Teacher not properly assigned to timetable entries
- **Solution**: Check teacher assignments in timetable entries

#### 3. **Empty Timetable Views**
- **Cause**: No timetable entries exist for the group/teacher
- **Solution**: Create timetable entries or run automatic generation

### Best Practices

1. **Always assign courses to student groups** before generating timetables
2. **Use the automatic generation** feature for initial timetable creation
3. **Review individual timetables** after making changes
4. **Check for conflicts** when manually adding entries
5. **Export timetables** for backup and sharing purposes

## 📚 Related Documentation

- [Database Schema Guide](DATABASE_SYNC_README.md)
- [Admin Management Guide](DEPLOYMENT.md)
- [Course Management Guide](ENHANCED_FEATURES_SUMMARY.md)
- [Student Group Management](COMPREHENSIVE_FIXES_SUMMARY.md)

---

**🎉 The Individual Timetables System ensures that every student group and teacher has their own personalized schedule, making the system more organized, efficient, and user-friendly!** 