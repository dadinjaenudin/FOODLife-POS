# HO Server - Promotion API Specification

## 📋 Overview

Dokumen ini menjelaskan field-field yang perlu ditambahkan di HO Server untuk mendukung promotion engine di Edge Server.

## 🎯 Required Fields

### 1. execution_stage (REQUIRED)

**Type:** String (Dropdown/Select)  
**Description:** Menentukan kapan promotion dieksekusi  
**Required:** Yes  
**Default:** `item_level`

**Options:**
```json
{
    "item_level": "Item Level - Auto-calculate saat add product",
    "cart_level": "Cart Level - Calculate saat klik button",
    "payment_level": "Payment Level - Calculate saat payment"
}
```

**Dropdown Values:**
| Value | Label | Description |
|-------|-------|-------------|
| `item_level` | Item Level | Dieksekusi saat item ditambahkan (auto-calculate) |
| `cart_level` | Cart/Subtotal Level | Dieksekusi saat calculate promotions (manual) |
| `payment_level` | Payment Level | Dieksekusi saat payment berdasarkan metode bayar |

**Usage:**
```python
# Django Model
execution_stage = models.CharField(
    max_length=20,
    choices=[
        ('item_level', 'Item Level'),
        ('cart_level', 'Cart Level'),
        ('payment_level', 'Payment Level'),
    ],
    default='item_level'
)
```

**UI Form:**
```html
<select name="execution_stage">
    <option value="item_level">Item Level (Auto-calculate)</option>
    <option value="cart_level">Cart Level (Manual)</option>
    <option value="payment_level">Payment Level (At Payment)</option>
</select>
```

---

### 2. is_auto_apply (REQUIRED)

**Type:** Boolean (Checkbox)  
**Description:** Apakah promotion otomatis diapply tanpa input user  
**Required:** Yes  
**Default:** `true` for item_level, `false` for others

**Values:**
- `true` - Promotion otomatis diapply
- `false` - Perlu manual apply (voucher code, button, etc)

**Usage:**
```python
# Django Model
is_auto_apply = models.BooleanField(
    default=True,
    help_text='Auto-apply promotion without user input'
)
```

**UI Form:**
```html
<input type="checkbox" name="is_auto_apply" checked>
<label>Auto-apply promotion</label>
```

**Logic:**
```python
# Recommended defaults based on execution_stage
if execution_stage == 'item_level':
    is_auto_apply = True  # Usually auto
elif execution_stage == 'cart_level':
    is_auto_apply = False  # Usually manual
elif execution_stage == 'payment_level':
    is_auto_apply = False  # Depends on payment method
```

---

### 3. execution_priority (OPTIONAL but RECOMMENDED)

**Type:** Integer  
**Description:** Priority order untuk execution (lower = higher priority)  
**Required:** No  
**Default:** Based on stage

**Default Values:**
- `item_level`: 500
- `cart_level`: 600
- `payment_level`: 700

**Range:** 1-999

**Usage:**
```python
# Django Model
execution_priority = models.IntegerField(
    default=500,
    help_text='Lower number = Higher priority (1-999)'
)
```

**UI Form:**
```html
<input type="number" name="execution_priority" value="500" min="1" max="999">
<small>Lower number = Higher priority</small>
```

---

## 📊 Promotion Type → Stage Mapping

### Recommended Defaults

| Promotion Type | Default execution_stage | Default is_auto_apply | Default Priority |
|----------------|------------------------|----------------------|------------------|
| `percent_discount` | `item_level` | `true` | 500 |
| `amount_discount` | `cart_level` | `false` | 600 |
| `buy_x_get_y` | `item_level` | `true` | 500 |
| `combo` | `item_level` | `true` | 500 |
| `free_item` | `cart_level` | `false` | 600 |
| `happy_hour` | `item_level` | `true` | 500 |
| `payment_discount` | `payment_level` | `false` | 700 |
| `threshold_tier` | `cart_level` | `false` | 600 |
| `cashback` | `payment_level` | `false` | 700 |
| `package` | `item_level` | `true` | 500 |
| `mix_match` | `item_level` | `true` | 500 |
| `upsell` | `item_level` | `false` | 500 |

---

## 🔄 API Response Format

### GET /api/promotions/compiled/

**Current Response:**
```json
{
    "id": "uuid",
    "code": "DISC20",
    "name": "20% Off Beverages",
    "promo_type": "percent_discount",
    "is_active": true,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "rules": {...},
    "scope": {...}
}
```

**NEW Response (Add these fields):**
```json
{
    "id": "uuid",
    "code": "DISC20",
    "name": "20% Off Beverages",
    "promo_type": "percent_discount",
    "is_active": true,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "rules": {...},
    "scope": {...},
    
    // NEW FIELDS ↓
    "execution_stage": "item_level",
    "is_auto_apply": true,
    "execution_priority": 500
}
```

---

## 🎨 UI/UX Recommendations

### Form Layout

```
┌─────────────────────────────────────────┐
│ Promotion Details                       │
├─────────────────────────────────────────┤
│ Name: [20% Off Beverages            ]  │
│ Code: [DISC20                       ]  │
│ Type: [Percent Discount        ▼]      │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Execution Settings                  │ │
│ ├─────────────────────────────────────┤ │
│ │ Stage: [Item Level          ▼]     │ │
│ │        ℹ️ When to apply promotion   │ │
│ │                                     │ │
│ │ ☑ Auto-apply                        │ │
│ │   Apply automatically without       │ │
│ │   user input                        │ │
│ │                                     │ │
│ │ Priority: [500]                     │ │
│ │          Lower = Higher priority    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Rules: {...}                            │
│ Scope: {...}                            │
└─────────────────────────────────────────┘
```

### Help Text

**execution_stage:**
```
ℹ️ Item Level: Applied when items are added to cart (real-time)
ℹ️ Cart Level: Applied when calculating cart total (manual)
ℹ️ Payment Level: Applied based on payment method selected
```

**is_auto_apply:**
```
ℹ️ Auto-apply: Promotion applies automatically without user action
   Manual: Requires voucher code or manual selection
```

**execution_priority:**
```
ℹ️ Priority determines execution order within same stage
   Lower number = Higher priority (executes first)
   Range: 1-999
```

---

## 🔧 Database Migration

### PostgreSQL

```sql
-- Add new columns
ALTER TABLE promotions_promotion 
ADD COLUMN execution_stage VARCHAR(20) DEFAULT 'item_level',
ADD COLUMN is_auto_apply BOOLEAN DEFAULT true,
ADD COLUMN execution_priority INTEGER DEFAULT 500;

-- Add check constraint
ALTER TABLE promotions_promotion
ADD CONSTRAINT check_execution_stage 
CHECK (execution_stage IN ('item_level', 'cart_level', 'payment_level'));

-- Add index for performance
CREATE INDEX idx_promotion_execution 
ON promotions_promotion(execution_stage, execution_priority);

-- Update existing promotions based on type
UPDATE promotions_promotion 
SET execution_stage = 'item_level',
    is_auto_apply = true,
    execution_priority = 500
WHERE promo_type IN ('percent_discount', 'buy_x_get_y', 'combo', 'happy_hour');

UPDATE promotions_promotion 
SET execution_stage = 'cart_level',
    is_auto_apply = false,
    execution_priority = 600
WHERE promo_type IN ('amount_discount', 'threshold_tier', 'free_item');

UPDATE promotions_promotion 
SET execution_stage = 'payment_level',
    is_auto_apply = false,
    execution_priority = 700
WHERE promo_type IN ('payment_discount', 'cashback');
```

### Django Migration

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('promotions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='execution_stage',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('item_level', 'Item Level'),
                    ('cart_level', 'Cart Level'),
                    ('payment_level', 'Payment Level'),
                ],
                default='item_level'
            ),
        ),
        migrations.AddField(
            model_name='promotion',
            name='is_auto_apply',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='execution_priority',
            field=models.IntegerField(default=500),
        ),
    ]
```

---

## ✅ Validation Rules

### execution_stage
- Must be one of: `item_level`, `cart_level`, `payment_level`
- Cannot be null/empty

### is_auto_apply
- Must be boolean (true/false)
- Recommended: `true` for item_level, `false` for others

### execution_priority
- Must be integer
- Range: 1-999
- Lower number = Higher priority

---

## 🧪 Testing Checklist

- [ ] Create promotion with `execution_stage = 'item_level'`
- [ ] Create promotion with `execution_stage = 'cart_level'`
- [ ] Create promotion with `execution_stage = 'payment_level'`
- [ ] Test `is_auto_apply = true` behavior
- [ ] Test `is_auto_apply = false` behavior
- [ ] Test priority ordering (100 vs 500 vs 900)
- [ ] Verify API response includes new fields
- [ ] Test Edge Server sync with new fields
- [ ] Verify auto-calculate works for item_level
- [ ] Verify manual calculate works for cart_level

---

## 📝 Summary

**3 New Fields Required:**

1. **execution_stage** (String, Dropdown)
   - Options: `item_level`, `cart_level`, `payment_level`
   - Default: `item_level`

2. **is_auto_apply** (Boolean, Checkbox)
   - Default: `true` for item_level, `false` for others

3. **execution_priority** (Integer, Number Input)
   - Range: 1-999
   - Default: 500 (item), 600 (cart), 700 (payment)

**Impact:**
- ✅ Enables auto-calculate for item-level promotions
- ✅ Separates item vs cart level promotions
- ✅ Controls execution order
- ✅ Better user experience in POS

---

**Last Updated:** 2026-01-30  
**Version:** 1.0  
**For:** HO Server Development Team
