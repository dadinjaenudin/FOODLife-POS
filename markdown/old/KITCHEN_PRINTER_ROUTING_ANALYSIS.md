# 🖨️ KITCHEN PRINTER ROUTING: ANALISIS KRITIS

**Created:** 24 Januari 2026  
**Status:** 🔴 CRITICAL DISCUSSION NEEDED  
**Impact:** High - Operational efficiency & kitchen workflow

---

## 🎯 **CURRENT IMPLEMENTATION ANALYSIS**

### **Existing Kitchen Model:**
```python
# apps/kitchen/models.py
class PrinterConfig(models.Model):
    name = models.CharField(max_length=100)
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE)
    station = models.CharField(max_length=20)  # 'kitchen', 'bar', 'grill'
    
    connection_type = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True)
    # ...

class KitchenOrder(models.Model):
    bill = models.ForeignKey('pos.Bill', on_delete=models.CASCADE)
    station = models.CharField(max_length=20)  # Kitchen station
    status = models.CharField(max_length=20)
    # ...
```

### **Current Routing Logic:**
```python
# apps/kitchen/services.py
def print_kitchen_order(bill, station, items):
    """Print order to kitchen printer"""
    config = PrinterConfig.objects.filter(
        brand=bill.brand,
        station=station,  # ← STATIC: 1 printer per station per brand
        is_active=True
    ).first()
```

**PROBLEM:** Printer tied to **Brand + Station**, not to **Terminal**!

---

## 🔴 **SKENARIO REAL & CHALLENGES**

### **Scenario 1: Single Brand, Multiple POS Terminals**

```
Brand: AYAMGEPREK (BSD Store)
├── Terminal: KASIR-01 (Lantai 1)
├── Terminal: KASIR-02 (Lantai 1)
└── Terminal: KIOSK-01 (Lantai 2)

Kitchen Printer: TP808-KITCHEN (Lantai 1)
```

**Question:** Kalau KIOSK-01 di lantai 2 kirim order, tetap print ke lantai 1?

**Options:**
1. ✅ **Centralized Routing:** Semua terminal → 1 kitchen printer (current)
2. ⚠️ **Zone-based Routing:** Terminal lantai 2 → printer lantai 2

---

### **Scenario 2: Multiple Brands, Shared Kitchen**

```
BSD Food Court:
├── Brand: AYAMGEPREK
│   ├── Terminal: KASIR-GEPREK-01
│   └── Terminal: KIOSK-GEPREK-01
│
├── Brand: NASGORENG
│   ├── Terminal: KASIR-NASGR-01
│   └── Terminal: KIOSK-NASGR-01
│
└── Shared Kitchen Printer: TP808-SHARED
```

**Question:** 2 brand pakai 1 kitchen printer yang sama?

**Challenge:**
- Current logic: `PrinterConfig.brand = AYAMGEPREK`
- Kalau shared, brand mana yang "owner" printer?

---

### **Scenario 3: Dedicated Kitchen per Brand**

```
BSD Food Court:
├── Brand: AYAMGEPREK
│   ├── Terminal: KASIR-GEPREK-01
│   ├── Terminal: KIOSK-GEPREK-01
│   └── Kitchen Printer: TP808-KITCHEN-GEPREK (dedicated)
│
└── Brand: NASGORENG
    ├── Terminal: KASIR-NASGR-01
    ├── Terminal: KIOSK-NASGR-01
    └── Kitchen Printer: TP808-KITCHEN-NASGR (dedicated)
```

**Question:** Each brand punya kitchen sendiri?

**Current logic:** ✅ **WORKS** - Each brand has own PrinterConfig

---

### **Scenario 4: Multiple Stations per Brand**

```
Brand: AYAMGEPREK
Kitchen Stations:
├── MAIN (Ayam + Nasi)    → Printer: MAIN-KITCHEN
├── GRILL (Grill station)  → Printer: GRILL-STATION
├── DESSERT (Dessert)      → Printer: DESSERT-BAR
└── BAR (Drinks)           → Printer: BAR-COUNTER

Product Routing:
├── "Ayam Geprek" → station='MAIN'
├── "Sate Ayam" → station='GRILL'
├── "Es Teh" → station='BAR'
└── "Pisang Goreng" → station='DESSERT'
```

**Question:** Gimana route product ke station yang tepat?

**Current:** Station determined **per product** (not in current code!)

---

## 🎯 **ROUTING STRATEGY COMPARISON**

### **Strategy 1: Brand-Level (CURRENT)** ⚠️

```python
# Printer tied to Brand + Station
PrinterConfig:
  - brand = AYAMGEPREK
  - station = "kitchen"
  - printer = TP808

# All terminals in brand → same printer
```

**✅ PROS:**
- Simple configuration
- Works for single-location brands
- Easy to manage

**❌ CONS:**
- No multi-location support (different floors)
- All terminals print to same printer
- No terminal-specific routing

---

### **Strategy 2: Terminal-Level Assignment** 🟡

```python
# Printer assigned per terminal
Terminal:
  - terminal_code = "KASIR-01"
  - kitchen_printer_id = FK(PrinterConfig)

# Each terminal has designated printer
```

**✅ PROS:**
- Terminal can print to specific printer
- Support multi-location (floor 1 vs floor 2)
- Flexible per-terminal config

**❌ CONS:**
- More configuration (setup per terminal)
- What if printer offline? No fallback
- Doesn't support multi-station routing (grill vs bar)

---

### **Strategy 3: Product-Station Routing** ⭐ **RECOMMENDED**

```python
# Product determines station
Product:
  - name = "Ayam Geprek"
  - kitchen_station = "MAIN"

# Station determines printer per brand
PrinterConfig:
  - brand = AYAMGEPREK
  - station = "MAIN"
  - printer = TP808-KITCHEN-MAIN

# Routing logic:
Order Item → Product.kitchen_station → PrinterConfig(brand, station) → Printer
```

**✅ PROS:**
- Flexible per-product routing
- Support multiple stations (grill, bar, dessert)
- Independent of terminal (any POS can order)
- Kitchen workflow optimization

**❌ CONS:**
- Need to configure station per product
- More complex setup

---

### **Strategy 4: Hybrid Terminal + Station** 🟢 **BEST FOR MULTI-LOCATION**

```python
# Terminal has zone assignment
Terminal:
  - terminal_code = "KASIR-01"
  - zone = "FLOOR-1"  # or NULL for central

# Printer config with zone support
PrinterConfig:
  - brand = AYAMGEPREK
  - station = "MAIN"
  - zone = "FLOOR-1"  # or NULL for shared
  - priority = 1

# Routing logic:
1. Product → kitchen_station
2. Terminal → zone (if has zone)
3. Find printer: brand + station + zone (matching or NULL)
4. Fallback to brand + station (no zone)
```

**✅ PROS:**
- Support multi-location per brand
- Support multi-station (grill, bar)
- Flexible fallback mechanism
- Terminal can override to specific zone

**❌ CONS:**
- Most complex configuration
- Need UI to manage zones

---

## 🏗️ **PROPOSED DATA MODEL**

### **Option A: Minimal Change (Product-Station)** 🟡

```python
# apps/pos/models.py
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey('Category', ...)
    kitchen_station = models.CharField(
        max_length=20,
        default='kitchen',
        choices=[
            ('kitchen', 'Main Kitchen'),
            ('grill', 'Grill Station'),
            ('bar', 'Bar/Drinks'),
            ('dessert', 'Dessert Station'),
        ],
        help_text="Which kitchen station handles this product"
    )
    # ...
```

**Routing Logic:**
```python
def print_kitchen_order(bill, items):
    """Group items by station, print to each station"""
    from collections import defaultdict
    
    # Group items by station
    stations = defaultdict(list)
    for item in items:
        station = item.product.kitchen_station
        stations[station].append(item)
    
    # Print to each station
    for station, station_items in stations.items():
        printer_config = PrinterConfig.objects.filter(
            brand=bill.brand,
            station=station,
            is_active=True
        ).first()
        
        if printer_config:
            send_to_printer(printer_config, bill, station_items)
```

---

### **Option B: Terminal Zone Support (Multi-Location)** 🟢

```python
# apps/core/models.py
class Terminal(models.Model):
    terminal_code = models.CharField(max_length=50, unique=True)
    brand = models.ForeignKey('Brand', ...)
    zone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Location zone (e.g., FLOOR-1, OUTDOOR, DRIVE-THRU)"
    )
    # ...

# apps/kitchen/models.py
class PrinterConfig(models.Model):
    brand = models.ForeignKey('core.Brand', ...)
    station = models.CharField(max_length=20)  # kitchen, bar, grill
    zone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Zone served by this printer (NULL = all zones)"
    )
    priority = models.IntegerField(
        default=1,
        help_text="Priority when multiple printers match (1=highest)"
    )
    # ...
```

**Routing Logic:**
```python
def get_kitchen_printer(brand, station, terminal=None):
    """Get best matching printer for station"""
    filters = {
        'brand': brand,
        'station': station,
        'is_active': True
    }
    
    # Try zone-specific first (if terminal has zone)
    if terminal and terminal.zone:
        printer = PrinterConfig.objects.filter(
            **filters,
            zone=terminal.zone
        ).order_by('priority').first()
        
        if printer:
            return printer
    
    # Fallback: shared printer (zone=NULL)
    return PrinterConfig.objects.filter(
        **filters,
        zone__isnull=True
    ).order_by('priority').first()
```

---

## 🎮 **RECOMMENDED IMPLEMENTATION**

### **Phase 1: Product-Station Routing (SHORT-TERM)**

**Changes:**
1. ✅ Add `kitchen_station` field to Product model
2. ✅ Update routing to group by station
3. ✅ Keep PrinterConfig as brand + station (current)

**Use Cases:**
- ✅ Single location with multiple stations (bar, grill, kitchen)
- ✅ Each brand has dedicated kitchen
- ❌ Multi-location per brand (different floors)

---

### **Phase 2: Zone Support (LONG-TERM)**

**Changes:**
1. ✅ Add `zone` field to Terminal model
2. ✅ Add `zone` + `priority` to PrinterConfig
3. ✅ Update routing with fallback logic

**Use Cases:**
- ✅ Multi-floor stores (Floor 1 vs Floor 2)
- ✅ Multiple outlets (Indoor vs Outdoor)
- ✅ Drive-thru scenarios
- ✅ Large venues (different sections)

---

## ❓ **CRITICAL QUESTIONS FOR YOU**

### **1. Brand Kitchen Setup:**
**Q:** Apakah setiap brand punya kitchen sendiri, atau shared kitchen?

**A1: Dedicated per brand** (e.g., Ayam Geprek kitchen terpisah dari Nasi Goreng)
- ✅ Current model works
- Each brand → own PrinterConfig

**A2: Shared kitchen** (e.g., 1 kitchen handle 3 brands)
- ⚠️ Need to redesign: PrinterConfig tidak bisa tied ke brand
- Solution: Store-level printer, brand hanya routing

---

### **2. Multi-Station Requirement:**
**Q:** Apakah perlu routing berdasarkan product category? (Drinks → Bar, Food → Kitchen)

**A1: Yes** - Need multi-station routing
- ✅ Implement Product.kitchen_station
- Group items by station before printing

**A2: No** - Semua print ke 1 printer
- ✅ Current model already works
- No changes needed

---

### **3. Multi-Location per Brand:**
**Q:** Apakah 1 brand bisa punya multiple locations dengan printer berbeda?

**A1: Yes** - (e.g., Floor 1 vs Floor 2, Indoor vs Outdoor)
- ✅ Implement Terminal.zone + PrinterConfig.zone
- Support zone-based routing

**A2: No** - 1 brand = 1 location
- ✅ Current model works
- No zone needed

---

### **4. Terminal-Specific Override:**
**Q:** Apakah ada kebutuhan terminal tertentu print ke printer tertentu?

**A1: Yes** - (e.g., Drive-thru terminal → special printer)
- ✅ Add Terminal.kitchen_printer_override (FK)
- Check override first before station routing

**A2: No** - Semua terminal treat equally
- ✅ Current model works

---

### **5. Printer Failure Handling:**
**Q:** Kalau kitchen printer offline, apa yang terjadi?

**A1: Queue print job** - Save to print queue, retry later
- ✅ Implement PrintQueue model
- Print agent polls and retries

**A2: Print to backup printer** - Automatic fallback
- ✅ Add PrinterConfig.backup_printer (FK)
- ✅ Add PrinterConfig.priority for fallback order

**A3: Manual reprint** - Staff manually reprint
- ✅ Current: Staff clicks "Reprint Kitchen"
- No automatic retry

---

## 🎯 **DECISION MATRIX**

| Scenario | Current Model | Product-Station | Zone Support | Terminal Override |
|----------|---------------|-----------------|--------------|-------------------|
| Single location, 1 kitchen | ✅ | ✅ | ✅ | ✅ |
| Single location, multi-station (bar/grill) | ❌ | ✅ | ✅ | ✅ |
| Multi-floor (Floor 1 vs 2) | ❌ | ❌ | ✅ | ⚠️ |
| Shared kitchen (multi-brand) | ❌ | ⚠️ | ⚠️ | ❌ |
| Drive-thru special routing | ❌ | ❌ | ⚠️ | ✅ |
| Automatic failover | ❌ | ❌ | ⚠️ | ❌ |

---

## 🚀 **RECOMMENDED APPROACH**

### **Start Simple, Evolve:**

**MVP (Phase 1):**
```python
# Add to Product model
kitchen_station = models.CharField(
    max_length=20,
    default='kitchen'
)

# Routing: Product → Station → Printer (brand + station)
```

**Future (Phase 2):**
```python
# Add to Terminal model (if multi-location needed)
zone = models.CharField(max_length=50, null=True, blank=True)

# Add to PrinterConfig
zone = models.CharField(max_length=50, null=True, blank=True)
priority = models.IntegerField(default=1)

# Routing: Product → Station + Terminal.zone → Printer (brand + station + zone)
```

---

## 📝 **ACTION ITEMS (PENDING YOUR DECISION)**

### **Before Implementation:**
- [ ] **DECIDE:** Single kitchen or multi-station per brand?
- [ ] **DECIDE:** Need zone support (multi-location)?
- [ ] **DECIDE:** Shared kitchen across brands?
- [ ] **DECIDE:** Printer failover strategy?
- [ ] **DECIDE:** Product-level routing or terminal-level?

### **After Decision:**
- [ ] Update Product model (if product-station routing)
- [ ] Update Terminal model (if zone support)
- [ ] Update PrinterConfig model (zone + priority)
- [ ] Update kitchen routing logic
- [ ] Update print queue system
- [ ] Create admin UI for printer management
- [ ] Test with actual printers

---

**Status:** 🔴 **WAITING FOR BUSINESS DECISION**  
**Priority:** HIGH - Affects kitchen operations  
**Impact:** All POS terminals + kitchen workflow

**Next:** Please answer the 5 critical questions above so we can finalize the design!
