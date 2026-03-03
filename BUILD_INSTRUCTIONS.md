# Build Instructions for AS1100 Sensor Data Collector Executable

## Prerequisites

1. Python 3.14+ installed
2. All project dependencies installed:
   ```
   pip install -r requirements.txt
   ```
3. PyInstaller installed:
   ```
   pip install pyinstaller
   ```

## Building the Executable

### Method 1: Using the Build Script (Recommended)
Simply run:
```
build.bat
```

### Method 2: Manual PyInstaller Command
```
python -m PyInstaller build_exe.spec --clean
```

## Build Output

After a successful build, you will find:
- **Executable**: `dist\AS1100_Sensor_Collector.exe` (~47 MB)
- **Build files**: `build\` folder (can be deleted)
- **Spec file**: `build_exe.spec` (PyInstaller configuration)

## Distribution Package

To distribute the application, provide users with:
1. `AS1100_Sensor_Collector.exe` (from dist folder)
2. `README.txt` (user documentation)

**Note**: The executable is self-contained and includes all dependencies. No Python installation is required on the target machine.

## What Gets Bundled

The executable includes:
- Python 3.14 runtime
- PySide6 (Qt GUI framework)
- pyserial (sensor communication)
- All application modules (app/*)
- Required system DLLs

## Build Configuration

The build is configured via `build_exe.spec`:
- **Console**: Disabled (GUI-only application)
- **Icon**: None (you can add an .ico file if desired)
- **UPX Compression**: Enabled (reduces file size)
- **Single File**: Yes (one .exe, no external folders)

## Customizing the Build

### Adding an Icon
1. Create or obtain a `.ico` file
2. Place it in the project root (e.g., `icon.ico`)
3. Edit `build_exe.spec` and change the icon line:
   ```python
   icon='icon.ico',
   ```

### Changing the Executable Name
Edit `build_exe.spec` and modify the `name` parameter:
```python
name='YourCustomName',
```

### Including Additional Files
To bundle extra files (configs, resources), add to the `datas` list:
```python
datas=[
    ('config.ini', '.'),
    ('resources/*', 'resources'),
],
```

## Troubleshooting Build Issues

### "Module not found" Errors
Add missing modules to the `hiddenimports` list in `build_exe.spec`

### Large Executable Size
- Remove unused imports from the code
- Use `--onefile` mode for smaller distribution
- Exclude unnecessary modules in the spec file

### Runtime Errors
- Test the executable on a clean system without Python installed
- Check PyInstaller warnings in `build/build_exe/warn-build_exe.txt`

## Testing the Executable

Before distributing:
1. Run the executable on your development machine
2. Test on a clean Windows machine without Python
3. Verify all features work (connection, measurement, CSV export)
4. Check sensor communication on different COM ports

## Cleaning Build Artifacts

To clean up build files:
```
rmdir /s /q build
rmdir /s /q dist
```
Or just run `build.bat` which automatically cleans before building.

---
Build Process Time: ~1-2 minutes
Final Executable Size: ~47 MB
Compatible: Windows 10/11 64-bit
