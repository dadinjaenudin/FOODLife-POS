# Build Guide - POS Launcher Qt

## Quick Build (Development)

```bash
# Windows
.\build_dev.bat

# Linux
./build_dev.sh
```

## Common Issues

### Error: "The process cannot access the file because it is being used by another process"

**Cause:** Windows File Explorer or other applications are accessing the `dist\` folder.

**Solutions:**

1. **Close all File Explorer windows** showing the `dist\` folder

2. **Run helper script:**
   ```bash
   .\close_explorer.bat
   ```
   This will close all Explorer windows and restart Explorer.

3. **Manual fix:**
   - Close any open File Explorer windows
   - Close POSLauncher.exe if running
   - Wait 5 seconds
   - Run build_dev.bat again

### Build Process

The build script automatically:
1. ✅ Kills running POSLauncher.exe processes
2. ✅ Kills Python processes running pos_launcher_qt.py
3. ✅ Waits 3 seconds for file handles to release
4. ✅ Renames `dist\` to `dist_old\` (instead of deleting)
5. ✅ Runs PyInstaller to create new `dist\`
6. ✅ Cleans up `dist_old\` after successful build

### Manual Cleanup

If you still have issues:

```bash
# Kill all POSLauncher processes
taskkill /F /IM POSLauncher.exe

# Close all Python processes
taskkill /F /IM python.exe

# Remove old folders manually
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q dist_old

# Run build again
.\build_dev.bat
```

## Output

Successful build creates:
- `dist\POSLauncher\` - Folder with executable
- `dist\POSLauncher\POSLauncher.exe` - Main executable
- All dependencies included

## Testing

```bash
cd dist\POSLauncher
.\POSLauncher.exe
```

## Production Build

For release distribution:

```bash
.\build_prod.bat
```

This will:
1. Run `build_dev.bat` to create executable
2. Run `package_release.bat` to create ZIP
3. Output: `releases\POSLauncher_{version}_{date}.zip`
