@echo off
REM Build script for AS1100 Sensor Data Collector executable

echo ============================================
echo AS1100 Sensor Data Collector - Build Script
echo ============================================
echo.

echo [1/3] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [2/3] Building executable with PyInstaller...
python -m PyInstaller build_exe.spec --clean

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo Executable location: dist\AS1100_Sensor_Collector.exe
echo.
echo You can now run the application by double-clicking the .exe file
echo.
pause
