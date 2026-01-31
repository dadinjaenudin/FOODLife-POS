# Promotion Engine - POS Integration Guide

## 📋 Overview

Promotion Engine adalah sistem kalkulasi promosi yang digunakan untuk menghitung diskon otomatis pada transaksi POS. Engine ini menggunakan **Python logic** (bukan JavaScript) sehingga konsisten antara testing dan production.

## 🎯 Supported Promotion Types

| # | Type | Code | Description | Example |
|---|------|------|-------------|---------|
| 1 | Percent Discount | `percent_discount` | Diskon persentase | 20% off |
| 2 | Amount Discount | `amount_discount` | Diskon nominal | Rp 10,000 off |
| 3 | Buy X Get Y | `buy_x_get_y` | Beli X gratis Y | Buy 2 Get 1 Free |
| 4 | Combo Deal | `combo` | Paket combo | 3 items Rp 50,000 |
| 5 | Free Item | `free_item` | Item gratis | Free dessert |
| 6 | Happy Hour | `happy_hour` | Diskon waktu tertentu | 50% off 14:00-16:00 |
| 7 | Payment Discount | `payment_discount` | Diskon metode bayar | 5% off with card |
| 8 | Threshold/Tiered | `threshold_tier` | Belanja lebih hemat lebih | Spend 100k get 10% |

## 🔧 API Endpoints

### 1. Calculate Promotions

**Endpoint:** `POST /promotions/api/calculate/`

**Purpose:** Menghitung promosi yang applicable untuk cart dan return total discount.

**Request:**
```json
{
    "items": [
        {
            "product_id": "uuid-string",
            "product_name": "Hot Americano",
            "sku": "001",
            "price": 27000,
            "quantity": 2,
            "category_id": "uuid-string"
        },
        {
            "product_id": "uuid-string",
            "product_name": "Ice Latte",
            "sku": "002",
            "price": 35000,
            "quantity": 1,
            "category_id": "uuid-string"
        }
    ],
    "auto_apply_only": true
}
```

**Response:**
```json
{
    "success": true,
    "subtotal": 89000,
    "discount_amount": 17800,
    "total": 71200,
    "applied_promotions": [
        {
            "promotion_id": "uuid",
            "promotion_code": "DISC20",
            "promotion_name": "20% Off All Beverages",
            "promo_type": "percent_discount",
            "discount_amount": 17800,
            "message": "20% discount",
            "is_stackable": false,
            "execution_stage": "item_level"
        }
    ]
}
```

### 2. Get Applicable Promotions

**Endpoint:** `GET /promotions/api/applicable/`

**Purpose:** Mendapatkan list semua promosi yang sedang aktif.

**Response:**
```json
{
    "success": true,
    "promotions": [
        {
            "id": "uuid",
            "code": "DISC20",
            "name": "20% Off All Beverages",
            "description": "Get 20% discount on all beverages",
            "promo_type": "percent_discount",
            "is_auto_apply": true,
            "is_stackable": false,
            "execution_stage": "item_level",
            "execution_priority": 500,
            "rules": {
                "discount_percent": 20,
                "max_discount_amount": 50000
            },
            "scope": {
                "apply_to": "category",
                "categories": ["beverage-uuid"]
            }
        }
    ],
    "count": 5
}
```

## 💻 POS Integration Examples

### Example 1: Auto-Apply Promotions on Bill

```javascript
// When bill items change, recalculate promotions
async function recalculatePromotions(billItems) {
    try {
        // Format items for API
        const items = billItems.map(item => ({
            product_id: item.product.id,
            product_name: item.product.name,
            sku: item.product.sku,
            price: parseFloat(item.product.price),
            quantity: item.quantity,
            category_id: item.product.category_id
        }));
        
        // Call API
        const response = await fetch('/promotions/api/calculate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                items: items,
                auto_apply_only: true  // Only auto-apply promotions
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update bill totals
            updateBillTotals({
                subtotal: result.subtotal,
                discount: result.discount_amount,
                total: result.total
            });
            
            // Show applied promotions to user
            displayAppliedPromotions(result.applied_promotions);
            
            return result;
        }
    } catch (error) {
        console.error('Error calculating promotions:', error);
    }
}

// Call when items added/removed/changed
billItemsObserver.subscribe(() => {
    recalculatePromotions(currentBillItems);
});
```

### Example 2: Show Available Promotions

```javascript
// Load and display available promotions
async function loadAvailablePromotions() {
    try {
        const response = await fetch('/promotions/api/applicable/');
        const result = await response.json();
        
        if (result.success) {
            const promoList = document.getElementById('promo-list');
            promoList.innerHTML = '';
            
            result.promotions.forEach(promo => {
                const promoCard = `
                    <div class="promo-card">
                        <h4>${promo.name}</h4>
                        <p>${promo.description}</p>
                        <span class="badge">${promo.promo_type}</span>
                    </div>
                `;
                promoList.innerHTML += promoCard;
            });
        }
    } catch (error) {
        console.error('Error loading promotions:', error);
    }
}

// Load on page load
document.addEventListener('DOMContentLoaded', loadAvailablePromotions);
```

### Example 3: Manual Promotion Application

```javascript
// Allow cashier to manually apply promotion
async function applyManualPromotion(promotionCode, billItems) {
    try {
        const items = billItems.map(item => ({
            product_id: item.product.id,
            product_name: item.product.name,
            sku: item.product.sku,
            price: parseFloat(item.product.price),
            quantity: item.quantity,
            category_id: item.product.category_id
        }));
        
        const response = await fetch('/promotions/api/calculate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                items: items,
                auto_apply_only: false,  // Include manual promotions
                promotion_code: promotionCode  // Specific promotion
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Check if promotion was applied
            const applied = result.applied_promotions.find(
                p => p.promotion_code === promotionCode
            );
            
            if (applied) {
                showSuccess(`Promotion ${promotionCode} applied! Discount: Rp ${applied.discount_amount}`);
                updateBillTotals(result);
            } else {
                showError('Promotion not applicable to current items');
            }
        }
    } catch (error) {
        console.error('Error applying promotion:', error);
        showError('Failed to apply promotion');
    }
}
```

## 🔄 Integration Flow

### 1. Bill Creation Flow

```
1. User adds item to bill
   ↓
2. Call recalculatePromotions()
   ↓
3. API calculates applicable promotions
   ↓
4. Update bill with discount
   ↓
5. Display applied promotions
```

### 2. Payment Flow

```
1. User clicks "Pay"
   ↓
2. Final promotion calculation
   ↓
3. Apply payment-level promotions (if any)
   ↓
4. Show final total
   ↓
5. Process payment
   ↓
6. Record promotion usage
```

## 📊 Promotion Execution Stages

Promotions are executed in stages:

1. **item_level** - Applied to individual items (e.g., 20% off beverages)
2. **cart_level** - Applied to cart subtotal (e.g., Rp 10,000 off)
3. **payment_level** - Applied based on payment method (e.g., 5% off with card)

**Execution Order:**
```
item_level → cart_level → payment_level
```

## 🎯 Promotion Scope

Promotions can target:

### 1. All Products
```json
{
    "apply_to": "all",
    "exclude_products": [],
    "exclude_categories": []
}
```

### 2. Specific Categories
```json
{
    "apply_to": "category",
    "categories": ["beverage-uuid", "food-uuid"]
}
```

### 3. Specific Products
```json
{
    "apply_to": "product",
    "products": ["product-uuid-1", "product-uuid-2"]
}
```

## ⚙️ Promotion Rules Examples

### 1. Percent Discount
```json
{
    "discount_percent": 20,
    "max_discount_amount": 50000,
    "min_purchase_amount": 0
}
```

### 2. Amount Discount
```json
{
    "discount_amount": 10000,
    "min_purchase_amount": 50000
}
```

### 3. Buy X Get Y
```json
{
    "buy_quantity": 2,
    "get_quantity": 1,
    "get_discount_percent": 100
}
```

### 4. Combo Deal
```json
{
    "required_quantity": 3,
    "combo_price": 50000
}
```

### 5. Threshold/Tiered
```json
{
    "tiers": [
        {
            "threshold": 100000,
            "discount_type": "percent",
            "discount_percent": 10
        },
        {
            "threshold": 200000,
            "discount_type": "percent",
            "discount_percent": 15
        }
    ]
}
```

## 🧪 Testing

### Using Simulator

1. Go to: `http://localhost:8001/promotions/simulator/`
2. Add products to cart
3. Click "Calculate Promotions"
4. Verify results match expectations

### Manual Testing Checklist

- [ ] Auto-apply promotions work
- [ ] Manual promotion application works
- [ ] Promotion stacking works correctly
- [ ] Exclusions are respected
- [ ] Time-based promotions activate/deactivate
- [ ] Usage limits are enforced
- [ ] Discount caps are applied
- [ ] Multiple items calculate correctly

## 🚨 Error Handling

```javascript
async function safeCalculatePromotions(billItems) {
    try {
        const result = await recalculatePromotions(billItems);
        return result;
    } catch (error) {
        console.error('Promotion calculation failed:', error);
        
        // Fallback: Continue without promotions
        return {
            success: false,
            subtotal: calculateSubtotal(billItems),
            discount_amount: 0,
            total: calculateSubtotal(billItems),
            applied_promotions: []
        };
    }
}
```

## 📝 Best Practices

### 1. Call API on Every Cart Change
```javascript
// Good
billItems.addEventListener('change', () => {
    recalculatePromotions(billItems);
});

// Bad - only calculate once
const promotions = await calculateOnce();
```

### 2. Show Promotion Details to User
```javascript
// Show which promotions are applied
result.applied_promotions.forEach(promo => {
    showNotification(`${promo.promotion_name}: -Rp ${promo.discount_amount}`);
});
```

### 3. Handle Stackable Promotions
```javascript
// Engine handles stacking automatically
// Just display all applied promotions
displayPromotions(result.applied_promotions);
```

### 4. Validate Before Payment
```javascript
async function finalizePayment() {
    // Recalculate one more time before payment
    const finalResult = await recalculatePromotions(billItems);
    
    // Proceed with payment
    processPayment(finalResult.total);
}
```

## 🔗 Related Documentation

- [Promotion Engine Architecture](./PROMOTION_ENGINE_ARCHITECTURE.md)
- [Promotion Types Reference](./PROMOTION_TYPES_REFERENCE.md)
- [API Documentation](./API_DOCUMENTATION.md)

## 💡 Tips

1. **Always recalculate** when cart changes
2. **Show promotion details** to customers
3. **Handle errors gracefully** - continue without promotions if API fails
4. **Test thoroughly** using simulator before production
5. **Monitor usage** - check promotion_sync_log table

## 📞 Support

For issues or questions:
- Check simulator: `/promotions/simulator/`
- View promotion details: `/management/master-data/promotions/`
- Check logs: `promotion_sync_log` table

---

**Last Updated:** 2026-01-30
**Version:** 1.0
