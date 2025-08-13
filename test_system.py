#!/usr/bin/env python3
"""
Simple test script to verify the Timetable & Attendance System functionality
"""

import requests
import json

# Base URL - change this to match your setup
BASE_URL = "http://localhost:5000"

def test_system():
    """Test basic system functionality"""
    print("Testing Timetable & Attendance System...")
    print("=" * 50)
    
    # Test 1: Check if the system is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✓ System is running and accessible")
        else:
            print(f"✗ System returned status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to the system. Make sure it's running on localhost:5000")
        return False
    except Exception as e:
        print(f"✗ Error testing system: {e}")
        return False
    
    # Test 2: Check login page
    try:
        response = requests.get(f"{BASE_URL}/login")
        if response.status_code == 200:
            print("✓ Login page is accessible")
        else:
            print(f"✗ Login page returned status code: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing login page: {e}")
    
    # Test 3: Check admin dashboard (should redirect to login)
    try:
        response = requests.get(f"{BASE_URL}/admin/dashboard", allow_redirects=False)
        if response.status_code == 302:  # Redirect to login
            print("✓ Admin dashboard properly redirects unauthenticated users")
        else:
            print(f"✗ Admin dashboard returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing admin dashboard: {e}")
    
    print("\n" + "=" * 50)
    print("Basic system tests completed!")
    print("\nTo test full functionality:")
    print("1. Start the system: python app.py")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Login with admin credentials:")
    print("   - Username: admin")
    print("   - Password: admin123")
    print("4. Test faculty login:")
    print("   - Username: faculty1")
    print("   - Password: faculty123")
    print("5. Test student login:")
    print("   - Username: student1")
    print("   - Password: student123")
    
    return True

if __name__ == "__main__":
    test_system()
