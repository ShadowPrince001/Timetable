# Timetable Creator and Automated Attendance System

A comprehensive web-based solution for academic institutions to manage class schedules and track student attendance automatically.

## 🎯 Project Overview

This system addresses the common challenges faced by academic institutions:
- **Complex scheduling constraints** (faculty availability, classroom capacity, student groups)
- **Manual attendance tracking** (time-consuming, error-prone)
- **Lack of real-time analytics** and reporting
- **Inefficient communication** between stakeholders

## ✨ Key Features

### 1. Smart Timetable Generation
- **AI-powered scheduling** with conflict resolution
- **Constraint management** (teacher availability, classroom capacity, student groups)
- **Automatic optimization** for subject frequency and time slots
- **Manual override** capabilities for schedule adjustments

### 2. Automated Attendance System
- **Real-time attendance tracking** aligned with class timetables
- **Multiple marking methods** (manual, QR code, biometric)
- **Automated triggers** based on scheduled sessions
- **Attendance validation** and correction tools

### 3. Role-Based Dashboards

#### 👨‍💼 Admin Dashboard
- System-wide statistics and analytics
- User management (students, faculty)
- Course and classroom management
- Timetable generation and oversight
- Comprehensive reporting tools

#### 👨‍🏫 Faculty Dashboard
- Today's class schedule
- Course management and attendance tracking
- Student performance monitoring
- Real-time notifications and alerts

#### 👨‍🎓 Student Dashboard
- Personal attendance overview with visual charts
- Today's schedule and upcoming classes
- Attendance history and statistics
- Low attendance warnings and alerts

### 4. Smart Notifications
- **Automated alerts** for low attendance
- **Missed class notifications** to students and parents
- **Schedule change announcements**
- **Real-time updates** via email and in-app notifications

### 5. Advanced Analytics
- **Attendance trends** and patterns
- **Performance analytics** by course, faculty, and student
- **Defaulter identification** and reporting
- **Export capabilities** (PDF, Excel, CSV)

## 🛠️ Technology Stack

### Backend
- **Flask** - Python web framework
- **SQLAlchemy** - Database ORM
- **Flask-Login** - User authentication
- **SQLite** - Database (can be upgraded to PostgreSQL/MySQL)

### Frontend
- **Bootstrap 5** - Responsive UI framework
- **jQuery** - JavaScript library
- **Font Awesome** - Icons
- **Chart.js** - Data visualization

### Additional Libraries
- **pandas** - Data manipulation
- **openpyxl** - Excel file handling
- **plotly** - Interactive charts
- **schedule** - Task scheduling

## 📋 System Requirements

- Python 3.8+
- Modern web browser
- 4GB RAM (minimum)
- 2GB storage space

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd timetable-attendance-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///timetable_attendance.db
```

### 5. Initialize Database
```bash
python init_db.py
```

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 👥 User Roles & Access

### Demo Accounts
- **Admin**: `admin` / `admin123`
- **Faculty**: `faculty` / `faculty123`
- **Student**: `student` / `student123`

### Role Permissions

| Feature | Admin | Faculty | Student |
|---------|-------|---------|---------|
| User Management | ✅ | ❌ | ❌ |
| Course Management | ✅ | ❌ | ❌ |
| Timetable Generation | ✅ | ❌ | ❌ |
| Attendance Marking | ✅ | ✅ | ❌ |
| Attendance Viewing | ✅ | ✅ | ✅ |
| Reports & Analytics | ✅ | ✅ | ❌ |
| System Settings | ✅ | ❌ | ❌ |

## 📊 Database Schema

### Core Tables
- **Users** - All system users (students, faculty, admin)
- **Courses** - Course information and details
- **Classrooms** - Classroom capacity and equipment
- **TimeSlots** - Available time slots for scheduling
- **Timetable** - Generated class schedules
- **StudentGroups** - Student groupings and batches
- **Attendance** - Daily attendance records
- **Notifications** - System notifications and alerts

## 🔧 Configuration

### Timetable Generation Settings
```python
# In app.py
TIMETABLE_CONSTRAINTS = {
    'max_hours_per_day': 8,
    'min_break_between_classes': 15,
    'preferred_time_slots': ['09:00-10:00', '10:15-11:15'],
    'avoid_conflicts': True
}
```

### Attendance Settings
```python
ATTENDANCE_SETTINGS = {
    'minimum_attendance': 75,
    'late_threshold_minutes': 15,
    'auto_mark_absent_after': 30,
    'notification_threshold': 80
}
```

## 📈 Usage Examples

### 1. Generating a Timetable
1. Login as Admin
2. Navigate to "Manage Timetable"
3. Select courses, teachers, and constraints
4. Click "Generate Timetable"
5. Review and adjust if needed

### 2. Taking Attendance
1. Faculty logs in
2. Views today's classes
3. Clicks "Take Attendance" for a class
4. Marks students as Present/Absent/Late
5. Saves attendance record

### 3. Viewing Reports
1. Access Reports section
2. Select report type (attendance, performance, etc.)
3. Choose date range and filters
4. Generate and export report

## 🔒 Security Features

- **Role-based access control**
- **Password hashing** with bcrypt
- **Session management**
- **CSRF protection**
- **Input validation** and sanitization
- **SQL injection prevention**

## 📱 Mobile Responsiveness

The system is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile phones
- All modern browsers

## 🔄 API Endpoints

### Authentication
- `POST /login` - User login
- `POST /logout` - User logout

### Timetable Management
- `GET /api/get-timetable` - Retrieve timetable
- `POST /api/generate-timetable` - Generate new timetable
- `PUT /api/update-timetable` - Update timetable

### Attendance Management
- `POST /api/mark-attendance` - Mark individual attendance
- `POST /api/bulk-mark-attendance` - Bulk attendance marking
- `GET /api/attendance-data` - Get attendance data

### Reports & Analytics
- `GET /api/export/{type}/{format}` - Export data
- `GET /api/analytics` - Get analytics data

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check if SQLite file exists
   - Verify file permissions
   - Run database initialization

2. **Login Issues**
   - Verify username/password
   - Check user role permissions
   - Clear browser cache

3. **Timetable Generation Fails**
   - Ensure all required data is entered
   - Check for conflicting constraints
   - Verify classroom availability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Email: support@timetable-system.com
- Documentation: [Wiki Link]
- Issues: [GitHub Issues]

## 🔮 Future Enhancements

- **Mobile App** development
- **Biometric integration** for attendance
- **AI-powered** attendance prediction
- **Parent portal** for attendance monitoring
- **Integration** with existing LMS systems
- **Advanced analytics** with machine learning
- **Multi-language** support
- **Cloud deployment** options

---

**Built with ❤️ for better education management**
