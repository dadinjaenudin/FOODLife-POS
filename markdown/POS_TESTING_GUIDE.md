# POS System Testing Guide

## Quick Start - Testing POS

### Prerequisites
✅ Server running on http://127.0.0.1:8001/
✅ SQLite database with test data (146 bills generated)
✅ Management interface tested and working

## Step 1: Terminal Setup

POS system requires a registered terminal. Let's set one up:

### Option A: Setup New Terminal (Recommended for Testing)
1. Open browser: http://127.0.0.1:8001/setup/
2. Terminal akan auto-register dengan code: `TERMINAL-XXX`
3. Select staff user untuk login
4. Sistem akan redirect ke POS interface

### Option B: Use Existing Terminal (if already set up)
1. Open browser: http://127.0.0.1:8001/pos/
2. Jika sudah ada terminal, akan langsung masuk
3. Jika belum, akan redirect ke setup

## Step 2: POS Login

**Login Credentials (default users):**
- Username: `cashier1` / Password: `12345678`
- Username: `waiter1` / Password: `12345678`
- Username: `manager` / Password: `12345678` (full access)

**Or use PIN login:**
- Manager PIN: (set at first login)
- Cashier PIN: (set at first login)

## Step 3: POS Main Interface Testing

### URL: http://127.0.0.1:8001/pos/

### A. Product Selection & Cart
**Test Cases:**
1. ✅ Browse products by category
   - Click category tabs (Food, Drinks, etc.)
   - Verify products load correctly
   - Check product images display
   
2. ✅ Add items to cart
   - Click product card to add
   - Verify quantity increases
   - Check subtotal updates
   
3. ✅ Modify cart quantities
   - Click + button to increase
   - Click - button to decrease
   - Remove items (quantity to 0)
   
4. ✅ Search products
   - Use search box
   - Verify search results
   - Add from search results

### B. Table Selection
**Test Cases:**
1. ✅ Select table for dine-in
   - Click "Select Table" button
   - Choose table from modal
   - Verify table name shows in bill panel
   
2. ✅ Table status indicators
   - Green: Available
   - Red: Occupied
   - Yellow: Reserved
   
3. ✅ Change table mid-transaction
   - Select different table
   - Verify bill updates

### C. Bill Management
**Test Cases:**
1. ✅ View bill details
   - Check items list
   - Verify quantities
   - Check prices
   
2. ✅ Bill calculations
   - Subtotal = sum of items
   - Tax calculation (if enabled)
   - Service charge (if enabled)
   - Grand total correct
   
3. ✅ Hold bill
   - Click "Hold" button
   - Bill saved for later
   - New bill created
   
4. ✅ Retrieve held bills
   - Click "Held Bills" button
   - View list of held bills
   - Click to resume held bill

### D. Payment Processing
**Test Cases:**
1. ✅ Cash payment
   - Click "Pay" button
   - Select "Cash" method
   - Enter amount tendered
   - Verify change calculation
   - Complete payment
   
2. ✅ Card payment
   - Select "Card" method
   - Enter card details (if required)
   - Process payment
   
3. ✅ QRIS payment
   - Select "QRIS" method
   - Show QR code (if integrated)
   - Enter transaction ID
   - Complete payment
   
4. ✅ Split payment
   - Partially pay with one method
   - Pay remaining with another method
   
5. ✅ Payment validation
   - Insufficient amount warning
   - Cannot pay empty bill
   - Payment confirmation

### E. Discounts & Promotions
**Test Cases:**
1. ✅ Apply item discount
   - Select item in bill
   - Apply % or amount discount
   - Verify discount applied
   
2. ✅ Apply bill discount
   - Discount entire bill
   - Check total calculation
   
3. ✅ Auto-apply promotions
   - Add qualifying items
   - Promotion auto-applies
   - Verify discount amount
   
4. ✅ Manual promotion codes
   - Enter promo code
   - Validate and apply
   - Check discount

### F. Order Notes & Customization
**Test Cases:**
1. ✅ Add item notes
   - Click item in cart
   - Add special instructions
   - Notes display in bill
   
2. ✅ Bill-level notes
   - Add customer name
   - Add phone number
   - Add special requests

## Step 4: Kitchen Display System (KDS) Testing

### URL: http://127.0.0.1:8001/kitchen/kds/

**Test Cases:**
1. ✅ Order appears in KDS
   - Complete payment in POS
   - Check KDS screen
   - Order shows immediately
   
2. ✅ Order status updates
   - Click "Start" on order
   - Status changes to "Preparing"
   - Click "Complete"
   - Status changes to "Ready"
   
3. ✅ Order filtering
   - Filter by status
   - Search by bill number
   - View order details
   
4. ✅ Real-time updates
   - New orders appear automatically
   - Status changes sync
   - Completed orders move

## Step 5: QR Order Testing (Customer Side)

### URL: http://127.0.0.1:8001/qr-order/{outlet_id}/{table_id}/

**Example:** http://127.0.0.1:8001/qr-order/1/1/

### A. Menu Browsing
**Test Cases:**
1. ✅ View menu categories
   - Browse category tabs
   - View product cards
   - Check product photos
   
2. ✅ Product details
   - Click product for details
   - View full description
   - See price and photos
   - Check recommendations
   
3. ✅ Recommendation engine
   - "Popular Items" section
   - "Trending Now" section
   - "Frequently Bought Together"
   - "You May Also Like"

### B. Cart & Order
**Test Cases:**
1. ✅ Add to cart
   - Select items
   - Adjust quantities
   - Add special requests
   
2. ✅ Cart management
   - View cart summary
   - Modify quantities
   - Remove items
   - See total
   
3. ✅ Submit order
   - Enter customer name
   - Add phone number
   - Add order notes
   - Submit order
   
4. ✅ Order confirmation
   - Order submitted message
   - Order number displayed
   - Estimated time shown

### C. Order Status Tracking
**Test Cases:**
1. ✅ View order status
   - After submitting order
   - Status updates live
   - Progress indicators
   
2. ✅ Status stages
   - Pending (just submitted)
   - Confirmed (kitchen received)
   - Preparing (cooking)
   - Ready (ready for pickup)
   - Completed

## Step 6: Reports Testing

### URL: http://127.0.0.1:8001/management/reports/

**Test Cases:**
1. ✅ Sales report
   - View today's sales
   - Filter by date range
   - Check totals
   
2. ✅ Products report
   - Top selling products
   - Category breakdown
   - Revenue by product
   
3. ✅ Cashier report
   - Performance by cashier
   - Transaction count
   - Average bill value
   
4. ✅ Payment methods report
   - Cash vs Card vs QRIS
   - Method totals
   - Percentage breakdown

## Test Scenarios

### Scenario 1: Dine-In Order (Complete Flow)
1. Login to POS as cashier
2. Select Table 5
3. Add items: 2x Nasi Goreng, 2x Es Teh
4. Add special request: "No spicy"
5. View total
6. Process payment (Cash Rp 100,000)
7. Print receipt
8. Check KDS - order appears
9. Kitchen marks as preparing
10. Kitchen marks as ready
11. Customer receives order

### Scenario 2: Take-Away Order
1. Login to POS
2. Don't select table (takeaway)
3. Add items
4. Add customer phone number
5. Process payment
6. Print receipt
7. Provide order number

### Scenario 3: QR Order Flow
1. Customer scans QR code at table
2. Opens menu on phone
3. Browses categories
4. Adds items to cart
5. Enters name & phone
6. Submits order
7. Views order status
8. Kitchen receives order
9. Kitchen prepares
10. Customer notified when ready

### Scenario 4: Hold & Resume Bill
1. Start new bill
2. Add some items
3. Customer says "wait, I need to check"
4. Click Hold Bill
5. Start serving another customer
6. Complete that order
7. Click Held Bills
8. Resume first customer's bill
9. Add more items
10. Complete payment

### Scenario 5: Split Payment
1. Create bill Rp 150,000
2. Customer pays Rp 100,000 cash
3. Enter cash payment
4. Remaining Rp 50,000
5. Customer pays balance with card
6. Enter card payment
7. Bill fully paid

## Common Issues & Solutions

### Issue 1: Cannot access POS
**Solution:** 
- Check terminal setup: http://127.0.0.1:8001/setup/
- Verify user permissions (role must be cashier/manager)
- Check browser console for errors

### Issue 2: Products not showing
**Solution:**
- Check categories exist in database
- Verify products are active (`is_active=True`)
- Check outlet assignment

### Issue 3: Payment not processing
**Solution:**
- Verify bill total > 0
- Check payment amount >= bill total
- Ensure terminal is active
- Check browser console

### Issue 4: KDS not updating
**Solution:**
- Check WebSocket connection
- Refresh KDS page
- Verify order status in database
- Check Daphne server logs

### Issue 5: QR Order not working
**Solution:**
- Verify table exists and is active
- Check outlet ID in URL
- Ensure products are available
- Check product photos uploaded

## Performance Testing

### Load Testing Points
1. ✅ Add 50 items to cart - UI responsive?
2. ✅ 10 held bills - can retrieve quickly?
3. ✅ 100 products in category - loads fast?
4. ✅ Multiple payment methods - processes smoothly?
5. ✅ Long order notes - saves correctly?

### Browser Testing
- ✅ Chrome (primary)
- ✅ Firefox
- ✅ Edge
- ✅ Safari (if available)
- ✅ Mobile browsers (responsive design)

### Screen Sizes
- ✅ Desktop (1920x1080)
- ✅ Laptop (1366x768)
- ✅ Tablet (768x1024)
- ✅ Mobile (375x667)

## Testing Checklist

### POS Core Functions
- [ ] Terminal setup & registration
- [ ] User login (username/password)
- [ ] PIN login
- [ ] Product browsing by category
- [ ] Product search
- [ ] Add items to cart
- [ ] Modify cart quantities
- [ ] Remove cart items
- [ ] Select table (dine-in)
- [ ] No table (takeaway)
- [ ] Hold bill
- [ ] Resume held bill
- [ ] Apply discounts
- [ ] Process cash payment
- [ ] Process card payment
- [ ] Process QRIS payment
- [ ] Split payment
- [ ] Print receipt
- [ ] Void transaction

### Kitchen Display
- [ ] Orders appear automatically
- [ ] Order details correct
- [ ] Status updates work
- [ ] Filter by status
- [ ] Search orders
- [ ] Mark preparing
- [ ] Mark ready/complete
- [ ] Real-time sync

### QR Order System
- [ ] Menu loads correctly
- [ ] Categories work
- [ ] Product details modal
- [ ] Product photos display
- [ ] Recommendations show
- [ ] Add to cart
- [ ] Cart management
- [ ] Submit order
- [ ] Order confirmation
- [ ] Status tracking
- [ ] Live updates

### Reports & Analytics
- [ ] Sales report generates
- [ ] Date filters work
- [ ] Products report accurate
- [ ] Cashier performance
- [ ] Payment methods breakdown
- [ ] Export to Excel

## Next Steps After Testing

1. **Document bugs found**
   - Create issue list
   - Priority levels
   - Steps to reproduce

2. **Performance optimization**
   - Slow query identification
   - Frontend optimization
   - Caching strategy

3. **User feedback**
   - Cashier usability
   - Kitchen staff feedback
   - Customer experience

4. **Production preparation**
   - Switch to PostgreSQL
   - Configure production settings
   - Setup SSL/HTTPS
   - Configure payment gateways

## Quick Test URLs

- **POS**: http://127.0.0.1:8001/pos/
- **Terminal Setup**: http://127.0.0.1:8001/setup/
- **KDS**: http://127.0.0.1:8001/kitchen/kds/
- **QR Order**: http://127.0.0.1:8001/qr-order/1/1/
- **Management**: http://127.0.0.1:8001/management/
- **Reports**: http://127.0.0.1:8001/management/reports/

## Test Data Available

- **276 Bills** (historical transactions)
- **5 Payments** (payment records)
- **Products** with categories
- **Tables** with areas
- **Users** (multiple roles)
- **Recommendation data** (co-occurrence patterns)

Ready to start testing! 🚀
