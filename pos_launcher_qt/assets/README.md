# Assets Folder

This folder contains static assets for the POS Launcher that need to work **offline**.

## Files

### `tailwind.js`
- **Size:** ~398 KB
- **Source:** https://cdn.tailwindcss.com
- **Version:** Play CDN (standalone, no build required)
- **Usage:** Used by `customer_display.html` for styling
- **Accessed via:** `http://127.0.0.1:5000/assets/tailwind.js`
- **Downloaded:** 2026-02-07

### How it Works

Customer display is served via Flask API on `http://127.0.0.1:5000/`:
1. Browser loads `http://127.0.0.1:5000/` → Flask serves `customer_display.html`
2. HTML references `<script src="assets/tailwind.js"></script>`
3. Browser requests `http://127.0.0.1:5000/assets/tailwind.js`
4. Flask route `/assets/<filename>` serves the local file
5. ✅ **Completely offline** - no external CDN needed

### Why Local?

The POS system operates in environments **without internet access**. All dependencies must be bundled locally to ensure:
- ✅ Offline functionality
- ✅ No dependency on external CDNs
- ✅ Consistent styling even without network
- ✅ Faster load times (no network latency)

## Updating Tailwind CSS

If you need to update Tailwind CSS to a newer version:

```powershell
# Navigate to pos_launcher_qt folder
cd D:\YOGYA-FOODLIFE\FoodLife-POS\pos_launcher_qt

# Download latest version
Invoke-WebRequest -Uri "https://cdn.tailwindcss.com" -OutFile "assets/tailwind.js"

# Verify file size
Get-Item "assets/tailwind.js" | Select-Object Name, Length
```

## Important Notes

⚠️ **DO NOT** change references back to CDN URLs like:
```html
<!-- ❌ DON'T DO THIS -->
<script src="https://cdn.tailwindcss.com"></script>
```

✅ **ALWAYS** use local reference:
```html
<!-- ✅ CORRECT -->
<script src="assets/tailwind.js"></script>
```

## File Integrity

- **Original Download Date:** February 7, 2026
- **Download Source:** Official Tailwind CSS Play CDN
- **File Type:** JavaScript (Tailwind CSS runtime)
- **No modifications:** File is used as-is from official source

---

**Last Updated:** 2026-02-07
