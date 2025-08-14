#!/usr/bin/env python3
"""
Simple route testing script to verify all URLs work correctly
"""

import requests
from urllib.parse import urljoin
import sys

# Base URL - change this to your actual server URL
BASE_URL = 'http://localhost:5000'

# Test routes (without authentication for now)
PUBLIC_ROUTES = [
    '/',
    '/login',
]

# Routes that require authentication (will return redirect to login)
PROTECTED_ROUTES = [
    '/dashboard',
    '/logout',
    '/admin/dashboard',
    '/admin/users',
    '/admin/courses', 
    '/admin/classrooms',
    '/admin/timetable',
    '/admin/add_user',
    '/admin/add_course',
    '/admin/add_classroom',
    '/faculty/dashboard',
    '/student/dashboard',
    '/student/timetable',
    '/student/attendance_history',
    '/student/profile',
]

def test_route(route, should_be_accessible=True):
    """Test a single route"""
    try:
        url = urljoin(BASE_URL, route)
        response = requests.get(url, timeout=5)
        
        if should_be_accessible:
            if response.status_code == 200:
                print(f"✅ {route} - OK (200)")
                return True
            else:
                print(f"❌ {route} - Failed ({response.status_code})")
                return False
        else:
            # Protected routes should redirect to login (302) or return 401/403
            if response.status_code in [302, 401, 403]:
                print(f"✅ {route} - Protected as expected ({response.status_code})")
                return True
            else:
                print(f"⚠️  {route} - Unexpected status ({response.status_code})")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ {route} - Connection error: {e}")
        return False

def main():
    """Run all route tests"""
    print("🧪 Testing Timetable & Attendance System Routes")
    print("=" * 50)
    
    total_tests = 0
    passed_tests = 0
    
    print("\n📖 Testing public routes:")
    for route in PUBLIC_ROUTES:
        total_tests += 1
        if test_route(route, should_be_accessible=True):
            passed_tests += 1
    
    print("\n🔒 Testing protected routes (should redirect):")
    for route in PROTECTED_ROUTES:
        total_tests += 1
        if test_route(route, should_be_accessible=False):
            passed_tests += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All routes are working correctly!")
        return 0
    else:
        print("⚠️  Some routes have issues. Check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())




