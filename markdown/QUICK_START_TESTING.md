# 🚀 QUICK START - Testing Guide

## ✅ Setup Complete!
- [x] Test data generated (146 bills dengan recommendation patterns)
- [x] Recommendation Engine ready
- [x] Testing checklist created

---

## 🎯 Start Testing Now!

### Step 1: Start Server
```bash
python manage.py runserver
```

### Step 2: Open QR Order Page
```
http://localhost:8000/qr-order/1/1/
```
*Ganti `/1/1/` dengan outlet_id dan table_id yang sesuai jika perlu*

### Step 3: Login ke Management (Untuk test Photo Gallery)
```
http://localhost:8000/management/login/
```
Username: `admin` / Password: `admin123` (atau sesuai setup)

---

## 📋 Testing Priority

### ⭐ HIGH PRIORITY - Test Ini Dulu!

#### 1. Recommendation Engine (Fitur Baru!)
- [ ] **Buka QR Order page** → Lihat section "🔥 Paling Populer" di atas
- [ ] **Scroll ke bawah** → Lihat "📈 Lagi Trending" (horizontal scroll)
- [ ] **Tambah item ke cart** → Lihat "💡 Cocok dengan Pesanan Anda" muncul
- [ ] **Click produk** → Scroll modal ke bawah → Lihat:
  - "🛒 Sering Dibeli Bersamaan"
  - "💡 Anda Mungkin Juga Suka"

#### 2. Product Photos & Gallery
- [ ] **Login ke Management** → `/management/master-data/products/`
- [ ] **Click "📷 Photos"** button di produk manapun
- [ ] **Upload foto baru** → Check preview muncul
- [ ] **Toggle visibility** (hijau/abu-abu) → Works
- [ ] **Back to QR Order** → Click produk yang ada fotonya
- [ ] **Check carousel** → Previous/Next/Dots navigation works

---

## 🧪 Quick 5-Minute Test

```
1. Buka: http://localhost:8000/qr-order/1/1/
2. Check: Popular Items muncul di atas ✅
3. Check: Trending Items bisa di-scroll ✅
4. Tambah: Ayam Bakar ke cart (trending item)
5. Check: Cart Recommendations muncul ✅
6. Click: Nasi Goreng → Open modal
7. Scroll: Ke bawah → See "Frequently Bought Together" ✅
8. Click: Salah satu recommended item → Modal baru terbuka ✅
9. Close: Modal
10. Submit: Order → Success ✅
```

**Result:** Semua recommendation features working! 🎉

---

## 📊 Data Yang Sudah Digenerate

### Bills Created: 146
- **60 hari history** (Nov 18, 2025 - Jan 17, 2026)
- **Trending products:** Ayam Bakar, Ayam Goreng
- **Pattern:** Items sering dibeli bersamaan (co-occurrence)

### Products: 18
Semua produk dari demo data, sekarang dengan order history

---

## 🔍 What to Look For

### Popular Items (🔥)
- Produk dengan order count tertinggi
- 2-column grid
- Max 6 items
- Click langsung buka product detail

### Trending Items (📈)
- Produk dengan growth terbesar (7 hari terakhir vs 7 hari sebelumnya)
- Horizontal scroll
- Max 4 items
- Ayam Bakar & Ayam Goreng harus muncul (test data design)

### Cart Recommendations (💡)
- **Hanya muncul kalau ada item di cart!**
- Green highlighted background
- Produk yang sering dibeli dengan isi cart
- Dynamic - berubah kalau cart berubah

### Frequently Bought Together (🛒)
- Di dalam product detail modal
- Scroll ke bawah untuk lihat
- Produk yang sering dibeli bareng produk yang dibuka
- Blue border on hover

### You May Also Like (💡)
- Di dalam product detail modal (paling bawah)
- Produk populer dari kategori yang sama
- Tidak termasuk produk yang sedang dibuka
- Green border on hover

---

## 📱 Responsive Testing

### Mobile (< 768px)
```
F12 → Toggle Device Toolbar → iPhone 12 Pro
```
- [ ] 1-column grid
- [ ] Touch scroll works
- [ ] Modal full-screen
- [ ] Buttons easily tappable

### Tablet (768px - 1024px)
```
F12 → Toggle Device Toolbar → iPad
```
- [ ] 2-column grid
- [ ] Good spacing
- [ ] All features accessible

### Desktop (> 1024px)
```
Normal browser window
```
- [ ] Max-width container
- [ ] Centered layout
- [ ] All recommendations visible

---

## 🐛 Common Issues & Solutions

### Issue: "No recommendations showing"
**Fix:** 
```bash
# Re-generate test data
python manage.py generate_recommendation_data
```

### Issue: "Images not loading"
**Fix:**
```bash
# Make sure media files configured
# Check MEDIA_URL and MEDIA_ROOT in settings.py
```

### Issue: "Cart recommendations not appearing"
**Expected:** Only shows AFTER adding items to cart

### Issue: "Page loading slow"
**Normal:** First load might be slow (database queries)
**Solution:** Add caching in production

---

## ✅ Success Criteria

**Recommendation Engine is working if:**
- [ ] Popular Items section visible on menu page
- [ ] Trending Items show and scroll horizontally
- [ ] Cart Recommendations appear after adding items
- [ ] Frequently Bought Together shows in product modal
- [ ] You May Also Like shows in product modal
- [ ] All recommendations are clickable
- [ ] Product modals open on click
- [ ] No console errors (F12 → Console)

**Product Photos is working if:**
- [ ] Upload form works in management
- [ ] Photos display in grid
- [ ] Carousel works in QR Order
- [ ] Previous/Next buttons work
- [ ] Dot indicators work

---

## 📞 Quick Help

### Check Console for Errors
```
F12 → Console Tab
```
Should see no red errors

### Check Network Requests
```
F12 → Network Tab → Filter: XHR
```
HTMX requests should return 200 OK

### Check Database
```bash
python manage.py shell
>>> from apps.pos.models import Bill
>>> Bill.objects.count()  # Should be 146+
>>> from apps.core.models import Product
>>> Product.objects.count()  # Should be 18
```

---

## 🎉 Ready to Test!

1. **Start server:** `python manage.py runserver`
2. **Open browser:** http://localhost:8000/qr-order/1/1/
3. **Follow checklist:** `TESTING_CHECKLIST.md`
4. **Report issues:** Check boxes yang tidak work

**Happy Testing!** 🚀

---

**Next Steps After Testing:**
- [ ] Fix any bugs found
- [ ] Test on real mobile devices
- [ ] Performance optimization
- [ ] Deploy to staging
- [ ] User acceptance testing (UAT)
