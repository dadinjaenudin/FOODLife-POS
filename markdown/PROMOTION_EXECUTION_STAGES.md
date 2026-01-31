# Promotion Execution Stages

## 📋 Overview

Promotions dieksekusi dalam 3 tahap (stages) yang berbeda. Setiap promotion type memiliki execution stage default.

## 🎯 Execution Stages

### 1. Item Level (`item_level`)
**Kapan:** Dieksekusi saat item ditambahkan ke cart (auto-calculate)
**Target:** Individual items atau groups of items
**Timing:** Real-time saat add product

**Promotion Types:**
- ✅ `percent_discount` - 20% off beverages
- ✅ `buy_x_get_y` - Buy 2 Get 1 Free
- ✅ `combo` - 3 items for Rp 50,000
- ✅ `happy_hour` - Time-based discount

**Example:**
```json
{
    "promo_type": "percent_discount",
    "execution_stage": "item_level",
    "execution_priority": 500,
    "rules": {
        "discount_percent": 20
    },
    "scope": {
        "apply_to": "category",
        "categories": ["beverage-uuid"]
    }
}
```

**Behavior:**
- Calculated automatically when product added
- Shows discount immediately in cart
- Updates in real-time
- Displayed as "Item Discount (Auto)"

---

### 2. Cart Level / Subtotal Level (`cart_level`)
**Kapan:** Dieksekusi saat calculate promotions (manual button)
**Target:** Cart subtotal
**Timing:** When user clicks "Calculate Promotions"

**Promotion Types:**
- ✅ `amount_discount` - Rp 10,000 off cart
- ✅ `threshold_tier` - Spend Rp 100k get 10% off
- ✅ `free_item` - Free item with minimum purchase

**Example:**
```json
{
    "promo_type": "amount_discount",
    "execution_stage": "cart_level",
    "execution_priority": 600,
    "rules": {
        "discount_amount": 10000,
        "min_purchase_amount": 50000
    },
    "scope": {
        "apply_to": "all"
    }
}
```

**Behavior:**
- Calculated when clicking "Calculate Promotions"
- Applied to cart subtotal
- Requires minimum purchase (optional)
- Shows in results section

---

### 3. Payment Level (`payment_level`)
**Kapan:** Dieksekusi saat payment (setelah pilih metode bayar)
**Target:** Payment method specific
**Timing:** At payment stage

**Promotion Types:**
- ✅ `payment_discount` - 5% off with credit card
- ✅ `cashback` - Get 10% back as points (future)

**Example:**
```json
{
    "promo_type": "payment_discount",
    "execution_stage": "payment_level",
    "execution_priority": 700,
    "rules": {
        "discount_percent": 5,
        "payment_methods": ["card", "qris"]
    }
}
```

**Behavior:**
- Calculated at payment stage
- Depends on payment method selected
- Applied after cart-level promotions
- Final discount before payment

---

## 🔄 Execution Order

```
1. ITEM LEVEL (Auto)
   ↓
2. CART LEVEL (Manual)
   ↓
3. PAYMENT LEVEL (At Payment)
```

**Priority within same stage:**
- Lower number = Higher priority
- Default: 500 (item), 600 (cart), 700 (payment)

---

## 📊 Promotion Type → Stage Mapping

| Promotion Type | Default Stage | Auto-Calculate | Description |
|----------------|---------------|----------------|-------------|
| `percent_discount` | `item_level` | ✅ Yes | Discount on items |
| `amount_discount` | `cart_level` | ❌ No | Discount on cart |
| `buy_x_get_y` | `item_level` | ✅ Yes | Buy X Get Y |
| `combo` | `item_level` | ✅ Yes | Combo deals |
| `free_item` | `cart_level` | ❌ No | Free item with purchase |
| `happy_hour` | `item_level` | ✅ Yes | Time-based discount |
| `payment_discount` | `payment_level` | ❌ No | Payment method discount |
| `threshold_tier` | `cart_level` | ❌ No | Tiered discount |

---

## 💻 Implementation in Code

### Engine (apps/promotions/engine.py)

```python
class PromotionEngine:
    def apply_promotions_to_cart(self, cart, auto_apply_only=True):
        """Apply promotions based on execution stage"""
        
        # Get applicable promotions
        promotions = self.get_applicable_promotions(cart)
        
        # Filter by auto-apply if needed
        if auto_apply_only:
            promotions = [p for p in promotions if p.is_auto_apply]
        
        # Sort by execution_stage and priority
        promotions = sorted(
            promotions,
            key=lambda p: (
                self._stage_order(p.execution_stage),
                p.execution_priority
            )
        )
        
        # Apply promotions in order
        for promotion in promotions:
            result = self.calculate_promotion(promotion, cart)
            # ... apply discount
    
    def _stage_order(self, stage):
        """Define stage execution order"""
        order = {
            'item_level': 1,
            'cart_level': 2,
            'payment_level': 3
        }
        return order.get(stage, 999)
```

### Simulator UI (templates/promotions/test_engine.html)

```javascript
// Auto-calculate item-level promotions
async function autoCalculateItemLevel() {
    const response = await fetch('/promotions/api/calculate/', {
        method: 'POST',
        body: JSON.stringify({
            items: cart,
            auto_apply_only: true  // Only item-level
        })
    });
    
    const data = await response.json();
    
    // Filter only item-level promotions
    const itemLevelPromos = data.applied_promotions.filter(
        p => p.execution_stage === 'item_level'
    );
    
    // Show in cart
    showItemLevelDiscount(itemLevelPromos);
}

// Manual calculate all promotions
async function calculateAllPromotions() {
    const response = await fetch('/promotions/api/calculate/', {
        method: 'POST',
        body: JSON.stringify({
            items: cart,
            auto_apply_only: false  // All stages
        })
    });
    
    const data = await response.json();
    
    // Show all promotions
    displayResults(data.applied_promotions);
}
```

---

## 🎯 Best Practices

### 1. Set Correct Execution Stage

```python
# Item-level: Affects individual items
Promotion(
    promo_type='percent_discount',
    execution_stage='item_level',  # ✅ Correct
    execution_priority=500
)

# Cart-level: Affects cart total
Promotion(
    promo_type='amount_discount',
    execution_stage='cart_level',  # ✅ Correct
    execution_priority=600
)

# Payment-level: Depends on payment method
Promotion(
    promo_type='payment_discount',
    execution_stage='payment_level',  # ✅ Correct
    execution_priority=700
)
```

### 2. Set Appropriate Priority

```python
# Higher priority (lower number) = Execute first
Promotion(
    name='VIP 30% Off',
    execution_priority=100  # Executes first
)

Promotion(
    name='Regular 20% Off',
    execution_priority=500  # Executes after VIP
)
```

### 3. Use Auto-Apply Wisely

```python
# Item-level: Usually auto-apply
Promotion(
    execution_stage='item_level',
    is_auto_apply=True  # ✅ Auto-calculate
)

# Cart-level: Usually manual
Promotion(
    execution_stage='cart_level',
    is_auto_apply=False  # ❌ Requires button click
)
```

---

## 🧪 Testing

### Test Item-Level (Auto)
1. Add product to cart
2. Check if discount appears automatically
3. Verify discount amount
4. Check promotion name displayed

### Test Cart-Level (Manual)
1. Add products to cart
2. Click "Calculate Promotions"
3. Verify cart-level promotions applied
4. Check minimum purchase requirements

### Test Payment-Level
1. Complete cart
2. Select payment method
3. Verify payment discount applied
4. Check final total

---

## 📝 Summary

**Item Level:**
- ✅ Auto-calculate when adding products
- ✅ Real-time discount display
- ✅ Affects individual items
- ✅ Examples: % off, Buy X Get Y, Combo

**Cart Level:**
- ❌ Manual calculate (button click)
- ✅ Affects cart subtotal
- ✅ May require minimum purchase
- ✅ Examples: Rp X off, Tiered discount

**Payment Level:**
- ❌ Calculate at payment stage
- ✅ Depends on payment method
- ✅ Final discount before payment
- ✅ Examples: Card discount, Cashback

---

**Last Updated:** 2026-01-30
**Version:** 1.0
