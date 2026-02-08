# POS Launcher Qt - Build Scripts Guide

> **Platform Support:** Windows (`.bat`) and Linux (`.sh`)

## 📋 Available Build Scripts

### 🪟 Windows Scripts
- `build_dev.bat` - Development build
- `build_prod.bat` - Production build + packaging (ZIP)
- `package_release.bat` - Package existing build into ZIP

### 🐧 Linux Scripts  
- `build_dev.sh` - Development build
- `build_prod.sh` - Production build + packaging (TGZ)
- `package_release.sh` - Package existing build into TGZ

---

## Windows Build Instructions

### 🔧 Development Build: `build_dev.bat`
**For testing and development purposes**

```bash
.\build_dev.bat
```

**What it does:**
- ✅ Checks Python installation
- ✅ Installs dependencies from requirements.txt
- ✅ Builds executable with PyInstaller
- ✅ Copies config.json to dist folder
- ⚠️ **DOES NOT** create ZIP package
- ⚠️ **NOT** for distribution to customers

**Output:**
```
dist\POSLauncher\
  ├── POSLauncher.exe
  ├── config.json
  ├── _internal\
  └── ...
```

**Use when:**
- Quick testing after code changes
- Development and debugging
- Local testing only

---

### 🚀 Production Build: `build_prod.bat`
**For creating deployment packages**

```bash
.\build_prod.bat
```

**What it does:**
- ✅ All steps from `build_dev.bat`
- ✅ Creates release folder with timestamp
- ✅ Copies executable and dependencies
- ✅ Creates template config.json for customers
- ✅ Creates README.txt with deployment instructions
- ✅ **Creates ZIP file** ready for distribution

**Output:**
```
releases\
  ├── POSLauncher-v2026-02-08\
  │   ├── POSLauncher.exe
  │   ├── config.json (template)
  │   ├── README.txt
  │   ├── _internal\
  │   └── ...
  └── POSLauncher-v2026-02-08.zip  ← SEND THIS TO CUSTOMERS
```

**Use when:**
- Creating release for deployment
- Preparing package for customers/stores
- Final build before distribution

---

### 🩹 Fix Build: `fix_and_build.bat`
**For fixing dependency issues**

```bash
.\fix_and_build.bat
```

**What it does:**
- ✅ Uninstalls PyQt6 and PyInstaller completely
- ✅ Reinstalls with correct compatible versions
- ✅ Builds executable
- ✅ Copies config.json

**Use when:**
- PyQt6 DLL errors occur
- After updating Python
- Dependency conflicts
- Build fails with Qt errors

---

### 📦 Package Only: `package_release.bat`
**For packaging existing build**

```bash
.\package_release.bat
```

**What it does:**
- ✅ Takes existing dist\POSLauncher\ folder
- ✅ Creates release folder and ZIP
- ⚠️ **Requires** existing build from build_dev.bat

**Use when:**
- Already have built executable
- Just need to create ZIP package
- Don't want to rebuild everything

---

## 🎯 Recommended Workflow

### Daily Development:
```bash
# Quick test cycle
.\build_dev.bat
cd dist\POSLauncher
.\POSLauncher.exe
```

### Before Deployment:
```bash
# Create production release
.\build_prod.bat

# Result: releases\POSLauncher-v2026-02-08.zip
# ✅ Send this ZIP to customer/store
```

### If Build Fails:
```bash
# Fix dependencies first
.\fix_and_build.bat

# Then try production build again
.\build_prod.bat
```

---

## 📊 Script Comparison

| Feature | build_dev.bat | build_prod.bat | fix_and_build.bat |
|---------|---------------|----------------|-------------------|
| Build executable | ✅ | ✅ | ✅ |
| Copy config.json | ✅ | ✅ | ✅ |
| Create ZIP | ❌ | ✅ | ❌ |
| Create README | ❌ | ✅ | ❌ |
| Fix dependencies | ❌ | ❌ | ✅ |
| Speed | Fast | Medium | Slow |
| **Use for** | Testing | Deployment | Fixing errors |

---

## 🔥 Quick Reference

```bash
# I want to test my changes
.\build_dev.bat

# I want to create a release for customers
.\build_prod.bat

# I have PyQt6 errors
.\fix_and_build.bat

# I just need to package existing build
.\package_release.bat
```

---

## 📝 Notes

1. **Always use `build_prod.bat` before sending to customers**
   - It creates proper ZIP package
   - Includes deployment instructions
   - Template config.json included

2. **Use `build_dev.bat` for daily work**
   - Much faster
   - Good for testing
   - Skip packaging step

---

## Linux Build Instructions

### 🔧 Development Build: `build_dev.sh`

```bash
chmod +x build_dev.sh
./build_dev.sh
```

**Creates:** `dist/POSLauncher/POSLauncher` (executable)

---

### 🚀 Production Build: `build_prod.sh`

```bash
chmod +x build_prod.sh
./build_prod.sh
```

**Creates:** `releases/POSLauncher-vYYYY-MM-DD.tar.gz`

---

### 📦 Package Only: `package_release.sh`

```bash
chmod +x package_release.sh
./package_release.sh
```

---

## 🔥 Quick Reference

### Windows
```bash
.\build_dev.bat          # Testing
.\build_prod.bat         # Release package (ZIP)
.\package_release.bat    # Package only
```

### Linux
```bash
./build_dev.sh          # Testing
./build_prod.sh         # Release package (TGZ)
./package_release.sh    # Package only
```

---

## 🐛 Linux Troubleshooting

**Permission denied:**
```bash
chmod +x *.sh
```

**Python3 not found:**
```bash
sudo apt install python3 python3-pip
```

**Qt platform plugin error:**
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0
```

---

**Last Updated:** February 8, 2026
