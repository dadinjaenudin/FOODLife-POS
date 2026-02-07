# Customer Display Configuration Guide

## 📋 Overview
Customer Display menggunakan HTML + CSS + JSON config untuk easy customization.

## 🎨 Customization

### 1. Edit Brand & Running Text
Edit file: `customer_display_config.json`

```json
{
  "brand": {
    "name": "YOGYA Food Life",           // Nama brand di header
    "logo_url": null,                    // URL logo (atau null untuk emoji)
    "tagline": "Nikmati Kelezatan Setiap Hari"  // Subtitle
  },
  "running_text": "🎉 Promo hari ini...",  // Text yang jalan di footer
  "running_text_speed": 80                  // Kecepatan (detik)
}
```

### 2. Customize Slideshow
Ada 2 cara:

**Option A: Placeholder (Text only)**
```json
"slideshow": [
  {
    "type": "placeholder",
    "title": "Promo Spesial!",
    "subtitle": "Beli 2 Gratis 1",
    "background_color": "#FF6B6B",
    "duration": 5000
  }
]
```

**Option B: Image (Coming soon)**
```json
"slideshow": [
  {
    "type": "image",
    "image_url": "assets/slideshow/promo1.jpg",
    "duration": 5000
  }
]
```

### 3. Theme Colors
```json
"theme": {
  "primary_color": "#667eea",          // Warna utama
  "secondary_color": "#764ba2",        // Warna gradien
  "text_color": "#ffffff",             // Warna text
  "billing_bg": "rgba(255,255,255,0.95)",  // Background billing
  "billing_text": "#333333"            // Text billing
}
```

## 📁 File Structure
```
pos_launcher_qt/
├─ customer_display.html            # UI (HTML/CSS/JS)
├─ customer_display_config.json     # Configuration (Edit this!)
├─ local_api.py                      # API server
└─ assets/ (optional)
   ├─ logo.png
   └─ slideshow/
      ├─ promo1.jpg
      └─ promo2.jpg
```

## 🔧 Advanced Customization

### Edit Layout (HTML)
File: `customer_display.html`

Layout structure:
- Lines 1-200: CSS styling
- Lines 200-300: HTML structure
- Lines 300-600: JavaScript logic

### Grid Proportions
Edit CSS Grid (line ~92):
```css
.main-content {
    grid-template-columns: 40% 60%;  /* Slideshow | Billing */
}
```

Change to:
```css
grid-template-columns: 30% 70%;  /* Lebih besar area billing */
grid-template-columns: 50% 50%;  /* Equal */
```

### Font Sizes
Edit CSS variables (lines ~35-150):
```css
.header-text h1 { font-size: 3rem; }      /* Header brand */
.slide h2 { font-size: 3rem; }            /* Slideshow title */
.item-name { font-size: 1.5rem; }         /* Item name */
.running-text { font-size: 1.8rem; }      /* Footer text */
```

## 🚀 Test Changes

### 1. Test Config Only
Edit `customer_display_config.json` then reload customer display window (Alt+F4 launcher → restart)

### 2. Test HTML Changes
Save `customer_display.html` → reload window

### 3. Test API Endpoint
```bash
curl http://127.0.0.1:5000/api/customer-display/config
```

## 📝 Tips

1. **Use Large Fonts**: Customer display dilihat dari jarak jauh
2. **High Contrast**: Pastikan text readable
3. **Smooth Animations**: Jangan terlalu cepat (min 5 detik/slide)
4. **Test on Real Monitor**: Size bisa berbeda di layar kecil vs besar
5. **Keep It Simple**: Jangan terlalu banyak animasi

## 🎯 Quick Edits (No Code)

Just edit `customer_display_config.json`:

**Change Brand Name:**
```json
"brand": { "name": "Your Brand Here" }
```

**Change Running Text:**
```json
"running_text": "Your message here 🎉"
```

**Add More Slides:**
```json
"slideshow": [
  { "title": "Slide 1", ... },
  { "title": "Slide 2", ... },
  { "title": "Slide 3", ... }  // Add more
]
```

**Change Colors:**
```json
"theme": {
  "primary_color": "#YOUR_COLOR",
  "secondary_color": "#YOUR_COLOR"
}
```

## 🔍 Troubleshooting

**Slideshow not showing:**
- Check `slideshow` array in config
- Min 1 slide required
- Duration must be > 0

**Running text not moving:**
- Check `running_text_speed` in config
- Default: 80 seconds

**Logo not showing:**
- Set `logo_url` to image path
- Or keep null for emoji placeholder

**Colors not applying:**
- Check `theme` object in config
- Use hex colors: #RRGGBB

## 📞 Need Help?

1. Check browser console (F12) for JavaScript errors
2. Check `customer_display_config.json` syntax (valid JSON?)
3. Restart launcher after config changes
4. Test API: `curl http://127.0.0.1:5000/api/customer-display/config`
