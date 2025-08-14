@echo off
echo ========================================
echo    Database Synchronization Script
echo ========================================
echo.
echo This script will synchronize your database
echo across all environments (Local, Codespace, Render)
echo.
echo Press any key to continue...
pause >nul

echo.
echo 🔄 Starting database synchronization...
echo.

python sync_databases_flask.py

echo.
echo ========================================
echo    Synchronization Complete!
echo ========================================
echo.
echo Press any key to exit...
pause >nul
