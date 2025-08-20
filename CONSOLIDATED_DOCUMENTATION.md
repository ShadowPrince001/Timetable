# Timetable Creator and Automated Attendance System - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Installation](#installation)
5. [User Roles](#user-roles)
6. [Database Schema](#database-schema)
7. [Configuration](#configuration)
8. [Usage Examples](#usage-examples)
9. [Deployment](#deployment)
10. [Database Synchronization](#database-synchronization)
11. [Troubleshooting](#troubleshooting)
12. [API Endpoints](#api-endpoints)
13. [Security Considerations](#security-considerations)

## Project Overview

A comprehensive web-based system for creating and managing academic timetables with automated attendance tracking. The system supports multiple user roles (admin, faculty, students) and provides a robust timetable generation engine with constraint satisfaction.

### Key Components
- **Timetable Generation Engine**: Multi-group constraint-based scheduling
- **Attendance Management**: Automated tracking with real-time updates
- **User Management**: Role-based access control
- **Resource Management**: Classrooms, courses, teachers, and student groups
- **Web Interface**: Responsive design with Bootstrap 5

## Features

### Core Functionality
- **Multi-Group Timetable Generation**: Generate conflict-free timetables for multiple student groups simultaneously
- **Constraint Satisfaction**: Ensures no conflicts in classroom usage, teacher availability, and time slots
- **Resource Allocation**: Intelligent assignment of classrooms and teachers based on requirements
- **Attendance Tracking**: Real-time attendance marking with status tracking (present, absent, late)
- **Conflict Detection**: Automatic validation of generated timetables

### Advanced Features
- **Equipment Constraints**: Match classroom equipment with course requirements
- **Capacity Management**: Ensure classrooms meet minimum capacity requirements
- **Department Matching**: Automatically assign teachers from matching departments
- **Priority Scheduling**: Courses with more periods per week are scheduled first
- **Memory Management**: Efficient resource cleanup to prevent memory leaks

### User Interface
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Interactive Dashboards**: Role-specific views with relevant information
- **Real-time Updates**: Live attendance tracking and timetable display
- **Export Functionality**: CSV export for timetables and attendance data
- **Search and Filter**: Advanced filtering for courses, users, and timetables

## Technology Stack

### Backend
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (development) / PostgreSQL (production)
- **Authentication**: Flask-Login with password hashing
- **Timetable Engine**: Custom constraint satisfaction algorithm

### Frontend
- **CSS Framework**: Bootstrap 5
- **JavaScript**: jQuery for DOM manipulation
- **Charts**: Chart.js for data visualization
- **Icons**: Font Awesome for UI elements

### Deployment
- **Platform**: Render.com
- **Server**: Gunicorn WSGI server
- **Environment**: Python 3.9+
- **Database**: PostgreSQL (production)

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager
- Git (for cloning)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd timetable-attendance-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python init_db.py
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

### Environment Variables
Create a `.env` file in the project root:
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///timetable.db
```

## User Roles

### Admin
- **Dashboard**: Overview of system statistics
- **User Management**: Create, edit, and delete users
- **Course Management**: Manage courses and their requirements
- **Classroom Management**: Configure classrooms and equipment
- **Timetable Generation**: Generate and manage timetables
- **System Configuration**: Manage time slots and student groups

### Faculty
- **Dashboard**: Personal teaching schedule and statistics
- **Attendance Management**: Mark and view attendance
- **Timetable View**: Personal teaching timetable
- **Course Details**: View assigned courses and student groups

### Student
- **Dashboard**: Personal timetable and attendance summary
- **Attendance History**: View attendance records
- **Timetable View**: Personal class schedule
- **Profile Management**: Update personal information

## Database Schema

### Core Models

#### User
- `id`: Primary key
- `username`: Unique username
- `email`: Email address
- `password_hash`: Hashed password
- `role`: User role (admin, faculty, student)
- `name`: Full name
- `department`: Department affiliation
- `group_id`: Student group (for students)

#### Course
- `id`: Primary key
- `code`: Course code (e.g., CS101)
- `name`: Course name
- `credits`: Credit hours
- `department`: Department offering the course
- `periods_per_week`: Number of class periods per week
- `min_capacity`: Minimum classroom capacity required
- `required_equipment`: Comma-separated equipment list

#### Classroom
- `id`: Primary key
- `room_number`: Room identifier
- `building`: Building name
- `capacity`: Maximum student capacity
- `room_type`: Type of room (lecture, lab, etc.)
- `equipment`: Available equipment (comma-separated)

#### TimeSlot
- `id`: Primary key
- `day`: Day of week
- `start_time`: Class start time
- `end_time`: Class end time

#### Timetable
- `id`: Primary key
- `course_id`: Reference to Course
- `teacher_id`: Reference to User (faculty)
- `classroom_id`: Reference to Classroom
- `time_slot_id`: Reference to TimeSlot
- `student_group_id`: Reference to StudentGroup
- `semester`: Academic semester
- `academic_year`: Academic year

#### Attendance
- `id`: Primary key
- `student_id`: Reference to User (student)
- `timetable_id`: Reference to Timetable
- `date`: Attendance date
- `status`: Attendance status (present, absent, late)
- `marked_by`: Reference to User who marked attendance
- `marked_at`: Timestamp of attendance marking

#### StudentGroup
- `id`: Primary key
- `name`: Group name
- `department`: Department affiliation
- `year`: Academic year
- `semester`: Academic semester

## Configuration

### Database Configuration
The system automatically detects the environment and configures the database accordingly:
- **Development**: SQLite database file
- **Production**: PostgreSQL database (Render.com)

### Timetable Generation Settings
- **Conflict Resolution**: Automatic detection and prevention
- **Resource Allocation**: Intelligent classroom and teacher assignment
- **Constraint Validation**: Equipment, capacity, and availability checks

### Security Settings
- **Password Hashing**: bcrypt-based password security
- **Session Management**: Flask-Login session handling
- **Access Control**: Role-based route protection

## Usage Examples

### Generating Timetables

1. **Access Admin Dashboard**
   - Navigate to `/admin/generate_timetables`
   - Select student groups and courses
   - Choose generation options

2. **Configure Constraints**
   - Set classroom capacity requirements
   - Specify equipment needs
   - Define teacher availability

3. **Generate and Validate**
   - Click "Generate Timetables"
   - System validates constraints
   - Review generated schedules

### Managing Attendance

1. **Faculty Access**
   - Navigate to `/faculty/take_attendance`
   - Select course and date
   - Mark student attendance

2. **Real-time Updates**
   - Attendance changes are immediately reflected
   - Students can view their attendance history
   - Alerts for missed classes

### Exporting Data

1. **Timetable Export**
   - Admin dashboard → Export Timetables
   - CSV format with all schedule details
   - Filter by date range or group

2. **Attendance Export**
   - Faculty dashboard → Export Attendance
   - Date-specific attendance records
   - Student performance analytics

## Deployment

### Render.com Deployment

1. **Connect Repository**
   - Link GitHub repository to Render
   - Configure build settings

2. **Environment Variables**
   ```env
   PYTHON_VERSION=3.9.0
   FLASK_ENV=production
   SECRET_KEY=your-production-secret-key
   ```

3. **Build Configuration**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

### Database Migration
```bash
# Run database synchronization
python sync_databases.py

# Or use the deployment hook
python deploy_hook.py
```

## Database Synchronization

### Automatic Sync
The system includes automatic database synchronization between development and production environments.

### Manual Sync
```bash
# Detect environment
python sync_databases.py

# Force sync
python sync_databases.py --force

# Sync specific tables
python sync_databases.py --tables users,courses
```

### Sync Scripts
- `sync_databases.py`: Main synchronization script
- `sync_databases_flask.py`: Flask-based sync
- `deploy_hook.py`: Deployment automation
- `auto_sync.py`: Automated synchronization

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check environment variables
   - Verify database credentials
   - Ensure database server is running

2. **Timetable Generation Failures**
   - Verify resource availability
   - Check constraint configurations
   - Review course-group assignments

3. **Performance Issues**
   - Monitor database query performance
   - Check for N+1 query problems
   - Optimize database indexes

### Debug Tools
- `debug_timetable.py`: Timetable generation debugging
- `test_functionality.py`: System functionality testing
- `check_course.py`: Course constraint validation

### Logs and Monitoring
- Check application logs for errors
- Monitor database performance
- Review user activity patterns

## API Endpoints

### Authentication
- `POST /login`: User authentication
- `POST /register`: User registration
- `GET /logout`: User logout

### Timetable Management
- `GET /api/get-timetable`: Retrieve user timetable
- `POST /admin/generate_timetables`: Generate new timetables
- `GET /admin/timetable_statistics`: Timetable analytics

### Attendance Management
- `POST /api/mark_attendance`: Mark student attendance
- `GET /api/attendance_data`: Retrieve attendance data
- `GET /faculty/attendance`: Faculty attendance view

### User Management
- `GET /admin/users`: List all users
- `POST /admin/add_user`: Create new user
- `PUT /admin/edit_user`: Update user information

### Course Management
- `GET /api/courses`: List all courses
- `POST /admin/add_course`: Create new course
- `PUT /admin/edit_course`: Update course information

## Security Considerations

### Authentication & Authorization
- **Password Security**: bcrypt hashing with salt
- **Session Management**: Secure session handling
- **Role-based Access**: Route-level permission checks

### Data Protection
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Output escaping

### Access Control
- **Route Protection**: @login_required decorators
- **Role Verification**: Admin-only route restrictions
- **Resource Isolation**: Users can only access their data

### Best Practices
- **Environment Variables**: Sensitive data in .env files
- **Error Handling**: Generic error messages (no sensitive info)
- **Input Validation**: Server-side validation for all inputs
- **Database Security**: Connection string encryption

---

## System Requirements

### Minimum Requirements
- **RAM**: 512MB
- **Storage**: 100MB
- **Python**: 3.9+
- **Database**: SQLite (dev) / PostgreSQL (prod)

### Recommended Requirements
- **RAM**: 1GB+
- **Storage**: 500MB+
- **Python**: 3.11+
- **Database**: PostgreSQL with connection pooling

## Performance Optimization

### Database Optimization
- **Indexing**: Strategic database indexes
- **Query Optimization**: N+1 query prevention
- **Connection Pooling**: Efficient database connections

### Memory Management
- **Resource Cleanup**: Automatic memory cleanup
- **Efficient Algorithms**: Optimized timetable generation
- **Caching**: Frequently accessed data caching

### Scalability
- **Horizontal Scaling**: Multiple application instances
- **Load Balancing**: Request distribution
- **Database Sharding**: Data partitioning strategies

---

*This documentation covers all aspects of the Timetable Creator and Automated Attendance System. For additional support or questions, please refer to the troubleshooting section or contact the development team.*
