# POS System - Development Roadmap & Feature Checklist

> Project: YOGYA Kiosk - POS F&B System  
> Technology: Django 6.0.1 + HTMX + Alpine.js + Tailwind CSS  
> Target: Edge Server (Offline-First LAN Operation)

---

## 🎯 Project Overview

**Architecture:** Edge Server per Store with Terminal Registration  
**Deployment:** Single-store offline LAN, sync to HO when online  
**Users:** Cashier, Supervisor, Manager, Kitchen Staff

---

## 📋 Development Phases

### Phase 1: Foundation & Setup ✅ (COMPLETED)
### Phase 0: Management Interface 🔄 (IN PROGRESS - PRIORITY)
### Phase 2: Core POS Operations 🔄 (IN PROGRESS)
### Phase 3: Kitchen Operations ⏳ (PENDING)
### Phase 4: Reporting & EOD ⏳ (PENDING)
### Phase 5: Advanced Features & Sync ⏳ (PENDING)

---

# PHASE 1: FOUNDATION & SETUP ✅

## 1.1 Multi-Tenant Architecture ✅

- [x] Company model with UUID
- [x] Outlet model with company FK
- [x] StoreConfig singleton per Edge Server
- [x] Multi-tenant data isolation
- [x] Demo data with company structure

## 1.2 Terminal Registration System ✅

- [x] POSTerminal model (UUID, terminal_code, device_type)
- [x] Terminal middleware injection (request.terminal)
- [x] localStorage + IndexedDB persistence
- [x] Heartbeat mechanism (2-minute interval)
- [x] IP address & MAC address tracking
- [x] Terminal online/offline status
- [x] Device types: POS, Tablet, Kiosk, Kitchen Display

## 1.3 Setup Wizard UI ✅
  
- [x] Welcome page dengan progress indicator
      http://127.0.0.1:8000/setup/terminal/
- [x] Company selection/creation
- [x] Store configuration form
- [x] Terminal registration page
        1. POS-001 (device fisik) 
        → Buka http://192.168.1.100:8000/setup/terminal/
        → Register dengan code "POS-001"
        → terminal_id disimpan di localStorage POS-001

        2. TAB-001 (tablet)
        → Buka http://192.168.1.100:8000/setup/terminal/
        → Register dengan code "TAB-001"
        → terminal_id disimpan di localStorage tablet

        3. POS-002 (device lain)
        → Buka http://192.168.1.100:8000/setup/terminal/
        → Register dengan code "POS-002"
        → terminal_id disimpan di localStorage POS-002
        
- [x] Status dashboard (store info + terminals)
- [x] Admin reset functionality
- [x] Beautiful gradient UI design

## 1.4 User Management ✅

- [x] Custom User model with company FK
- [x] Role-based access control
- [x] Login page with branding
- [x] User outlet assignment
- [x] Password management
- [x] Admin panel configuration

## 1.5 Product Master Data ✅

- [x] Category model with hierarchy
- [x] Product model with pricing
- [x] Product images
- [x] Printer target (kitchen/bar/dessert)
- [x] Stock tracking flag
- [x] Active/inactive status
- [x] Demo products (18 items)

## 1.6 Table Management ✅

- [x] Table model with capacity
- [x] Table status (available/occupied)
- [x] Table sections/zones
- [x] Demo tables data

---

# PHASE 0: MANAGEMENT INTERFACE 🔄 (PRIORITY)

> **Target Users:** Store Manager, Supervisor, IT Support  
> **Purpose:** Edge Server monitoring & control without Django admin access  
> **URL Base:** `/management/`

## 0.1 Management App Setup ✅

- [x] **Project Structure**
  - [x] Create `apps/management/` app
  - [x] Register app in settings.py
  - [x] Create base URL routing
  - [x] Access control decorator (@manager_required)
  - [x] Base template with sidebar navigation

## 0.2 Dashboard (Real-time Metrics) ✅

- [x] **Dashboard Layout**
  - [x] Responsive grid layout (4 columns)
  - [x] Auto-refresh every 30 seconds
  - [ ] Manual refresh button (future)
  - [x] Last updated timestamp

- [x] **Revenue Card**
  - [x] Today's total revenue (large, prominent)
  - [x] Bills count (open/closed/held)
  - [x] Average bill value
  - [ ] Comparison with yesterday (%) (future)
  - [x] Icon: 💰 chart icon

- [x] **Session Status Card** (Ready for integration)
  - [x] Current business date
  - [x] Session status (open/closed)
  - [ ] Hours since open (live counter) (ready with StoreSession)
  - [ ] Open new session button (if closed) (future)
  - [ ] EOD button (if ready) (future)
  - [x] Icon: 📅 calendar icon

- [x] **Terminals Card**
  - [x] Online terminals count (🟢 green)
  - [x] Offline terminals count (⚫ gray)
  - [x] Total registered terminals
  - [x] Quick link to terminals page
  - [x] Icon: 🖥️ monitor icon

- [x] **Cashiers Card** (Ready for integration)
  - [ ] Active shifts count (ready with CashierShift)
  - [x] Active cashiers count
  - [ ] Idle terminals (no shift) (ready)
  - [ ] Quick link to cashier reports (future)
  - [x] Icon: 👤 user icon

- [x] **Payment Methods Breakdown**
  - [x] Grid display (not chart yet)
  - [x] Cash, Card, QRIS, E-Wallet
  - [x] Amount per method
  - [ ] Percentage distribution (future)

- [ ] **Hourly Sales Chart** (future)
  - [ ] Bar chart (24 hours)
  - [ ] Current hour highlighted
  - [ ] Peak hour indicator
  - [ ] Tooltip with details

- [x] **Quick Actions Bar**
  - [x] Open POS button
  - [ ] View Reports button (placeholder)
  - [x] Manage Terminals button
  - [ ] Settings button (placeholder)

- [x] **Backend: Dashboard APIs**
  - [x] get_dashboard_stats() function (in view)
  - [x] Real-time data queries
  - [ ] Cache dashboard data (30 seconds) (future)
  - [x] HTMX partial updates endpoint

## 0.3 Terminal Management ⏳

- [ ] **Terminal List Page**
  - [ ] Table view with columns:
    - [ ] Status indicator (🟢 Online / ⚫ Offline)
    - [ ] Terminal Code (POS-001, TAB-001)
    - [ ] Device Type (POS, Tablet, Kitchen Display)
    - [ ] IP Address
    - [ ] Last Heartbeat (relative time)
    - [ ] Current Cashier (if active shift)
    - [ ] Actions (View, Deactivate, Delete)
  - [ ] Filter by status (All/Online/Offline)
  - [ ] Filter by device type
  - [ ] Search by terminal code
  - [ ] Sort by: status, code, last heartbeat
  - [ ] Auto-refresh list (30 seconds)

- [ ] **Terminal Status Badge**
  - [ ] 🟢 Online (green badge) - heartbeat < 5 min
  - [ ] ⚫ Offline (gray badge) - heartbeat > 5 min
  - [ ] ⚠️ Warning (yellow) - heartbeat 3-5 min
  - [ ] Relative time display ("2 minutes ago")

- [ ] **Terminal Details Modal**
  - [ ] Full terminal information:
    - [ ] UUID
    - [ ] Terminal code
    - [ ] Device type
    - [ ] Device info (browser, OS)
    - [ ] IP address (current + history)
    - [ ] MAC address
    - [ ] Created date
    - [ ] Last heartbeat
    - [ ] Is active status
  - [ ] Recent activity:
    - [ ] Last 10 bills processed
    - [ ] Last 5 shifts
    - [ ] Total bills count
    - [ ] Total sales amount
  - [ ] Close button

- [ ] **Register Terminal Manually** (Optional)
  - [ ] Register button (top right)
  - [ ] Modal form:
    - [ ] Terminal code input (auto-suggest next code)
    - [ ] Device type dropdown
    - [ ] Description/notes
    - [ ] Submit button
  - [ ] Generate terminal_id
  - [ ] Show QR code with terminal_id (for device scan)
  - [ ] Copy terminal_id button

- [ ] **Deactivate Terminal**
  - [ ] Deactivate button per terminal
  - [ ] Confirmation modal:
    - [ ] Terminal code display
    - [ ] Current status
    - [ ] Warning: "Active shift will be closed"
    - [ ] Reason dropdown (optional)
    - [ ] Confirm button
  - [ ] Set is_active = False
  - [ ] Force close active shift (if exists)
  - [ ] Audit log
  - [ ] Success notification

- [ ] **Delete Terminal** (Superuser Only)
  - [ ] Delete button (red, danger)
  - [ ] Double confirmation modal:
    - [ ] "Type terminal code to confirm"
    - [ ] Input validation
    - [ ] Cannot delete if has active shift
    - [ ] Cannot delete if has bills in current session
    - [ ] Reason required
  - [ ] Hard delete from database
  - [ ] Archive related data (optional)
  - [ ] Audit log

- [ ] **Reactivate Terminal**
  - [ ] Show deactivated terminals (toggle)
  - [ ] Reactivate button
  - [ ] Simple confirmation
  - [ ] Set is_active = True
  - [ ] Success notification

- [ ] **Terminal Activity Log**
  - [ ] Log table per terminal
  - [ ] Columns: Timestamp, Event, User, Details
  - [ ] Events: Registered, Heartbeat, Shift Start, Shift End, Deactivated, Reactivated, Deleted
  - [ ] Pagination
  - [ ] Export to CSV

- [ ] **Backend: Terminal Management**
  - [ ] terminal_list view
  - [ ] terminal_detail view
  - [ ] terminal_deactivate API
  - [ ] terminal_delete API (superuser)
  - [ ] terminal_reactivate API
  - [ ] terminal_activity_log view
  - [ ] Permissions: @manager_required

## 0.4 Access Control & Permissions ✅

- [x] **User Roles for Management Interface**
  - [x] Manager: Full access (dashboard + terminals + settings)
  - [x] Supervisor: Read-only + approve actions
  - [ ] IT Support: Terminals + sync (future)
  - [x] Cashier: No access (POS only)

- [x] **Permission Decorators**
  - [x] @manager_required
  - [x] @supervisor_required
  - [x] @management_access_required
  - [x] Redirect to POS if no access

- [ ] **Access Denied Page** (future)
  - [x] Error message display
  - [ ] Current user role display
  - [ ] Contact admin link
  - [x] Redirect to POS button

## 0.5 Navigation & Layout ✅

- [x] **Sidebar Navigation**
  - [x] 📊 Dashboard (home)
  - [x] 🖥️ Terminals
  - [x] 📈 Reports (future placeholder)
  - [x] 💾 Master Data (future placeholder - Phase 5)
  - [x] ⚙️ Settings (future placeholder)
  - [x] 🚪 Logout

- [x] **Top Bar**
  - [x] Store name + outlet
  - [x] Current business date (ready for session)
  - [x] Session status indicator
  - [x] User name + role
  - [ ] Quick links dropdown (future)

- [x] **Responsive Design**
  - [x] Desktop: Sidebar + content
  - [x] Tablet: Collapsible sidebar
  - [ ] Mobile: Bottom nav (future)

## 0.6 Settings Page (Basic) ⏳

- [ ] **Store Information**
  - [ ] Store name (read-only from StoreConfig)
  - [ ] Outlet info
  - [ ] Address, phone
  - [ ] Edit button (future)

- [ ] **System Info**
  - [ ] Edge Server version
  - [ ] Database size
  - [ ] Last backup time
  - [ ] Disk space usage

---

# PHASE 2: CORE POS OPERATIONS 🔄

## 2.1 Session & Shift Management ⏳

### Store Session (Business Date)
- [ ] **UI: Session Dashboard**
  - [ ] Current business date display
  - [ ] Session status (open/closed)
  - [ ] Hours since open indicator
  - [ ] Quick stats: bills, sales, shifts
  - [ ] Open new session button (if closed)
  - [ ] EOD button (if ready)
  - [ ] Overdue warning banner (if > 12 hours)
  - [ ] Critical lock screen (if > 24 hours)

- [ ] **UI: Open Session Modal**
  - [ ] Business date picker (default: today)
  - [ ] Opening notes textarea
  - [ ] Confirm button
  - [ ] Auto-redirect to shift open

- [ ] **Backend: Session Management**
  - [x] StoreSession model
  - [x] Only 1 active session validation
  - [ ] Session open API endpoint
  - [ ] Session status check middleware
  - [ ] Auto business_date assignment to bills

### Cashier Shift
- [ ] **UI: Shift Open Modal**
  - [ ] Terminal selection (auto-detect current)
  - [ ] Opening cash amount input
  - [ ] Shift notes textarea
  - [ ] Confirm button
  - [ ] Print shift start receipt

- [ ] **UI: Active Shift Indicator** (Top Bar)
  - [ ] Shift start time display
  - [ ] Current shift duration timer
  - [ ] Opening cash amount
  - [ ] Quick close shift button
  - [ ] Shift info tooltip

- [ ] **UI: Shift Close Modal**
  - [ ] Expected vs Actual comparison table
  - [ ] Payment method breakdown:
    - [ ] Cash (physical count input)
    - [ ] Card (settlement amount input)
    - [ ] QRIS (settlement amount input)
    - [ ] E-Wallet (settlement amount input)
    - [ ] Voucher (auto from system)
  - [ ] Auto-calculate differences
  - [ ] Color coding (green: match, red: variance)
  - [ ] Variance > threshold warning
  - [ ] Supervisor approval required (if variance high)
  - [ ] Shift notes textarea
  - [ ] Print shift report button
  - [ ] Confirm close button

- [ ] **Backend: Shift Management**
  - [x] CashierShift model
  - [x] ShiftPaymentSummary model
  - [x] ShiftService (open/close)
  - [ ] Shift open API endpoint
  - [ ] Shift close API endpoint
  - [ ] Cash reconciliation calculation
  - [ ] Variance threshold check
  - [ ] Supervisor approval workflow

## 2.2 POS Main Screen ✅ (Core Completed)

### Layout Structure ✅
- [x] Split screen: Products (left) + Bill (right)
- [x] Top navigation bar
- [x] Category tabs/pills
- [x] Product grid with images
- [x] Bill panel with items list
- [x] Responsive design

### Product Selection ✅
- [x] **Product Grid Display**
  - [x] Product image thumbnail
  - [x] Product name
  - [x] Price display
  - [x] Out of stock indicator
  - [x] Click to add to bill

- [x] **Category Filter**
  - [x] Category tabs navigation
  - [x] Active category highlight
  - [x] Scroll horizontal on mobile
  - [x] "All" category option

### Bill Panel - Enhanced 🔄
- [x] **Bill Header** ✅
  - [x] Bill number display
  - [x] Table badge (if dine-in)
  - [x] Guest count
  - [x] Created by & timestamp
  - [x] Terminal badge (📱 terminal_code) ✅

- [ ] **Bill Type Selector** ⏳
  - [ ] Dine In button (default)
  - [ ] Take Away button
  - [ ] Delivery button
  - [ ] Toggle active state
  - [ ] Icon + label
  - [ ] Change bill type after creation

- [ ] **Table Selector** ⏳
  - [x] Select table modal (basic) ✅
  - [ ] Table layout grid (visual)
  - [ ] Table status colors
  - [ ] Table capacity display
  - [ ] Quick search table number
  - [ ] Change table after selection

- [x] **Bill Items List** ✅
  - [x] Item name
  - [x] Quantity with +/- buttons
  - [x] Unit price
  - [x] Item total
  - [x] Item notes/modifiers display
  - [x] Void item button
  - [ ] Item status badge (pending/sent/preparing)
  - [ ] Item reorder (drag & drop)

- [ ] **Item Actions** ⏳
  - [x] Increase quantity (+) ✅
  - [x] Decrease quantity (-) ✅
  - [ ] Edit item modal
    - [ ] Update quantity
    - [ ] Add notes
    - [ ] Select modifiers
    - [ ] Update price (if supervisor)
  - [x] Void item with reason ✅
  - [ ] Move item to another bill
  - [ ] Split item quantity

- [ ] **Bill Totals Section** ⏳
  - [x] Subtotal display ✅
  - [ ] Discount input/select
    - [ ] Manual discount (percent or value)
    - [ ] Voucher code input
    - [ ] Promotion auto-apply
    - [ ] Discount reason required
  - [x] Tax calculation ✅
  - [x] Service charge ✅
  - [x] Grand total (bold, large) ✅
  - [ ] Rounding adjustment (if needed)

- [ ] **Bill Actions Bar** ⏳
  - [x] Hold Bill button ✅
  - [ ] Print KOT (Kitchen Order Ticket) button
  - [ ] Split Bill button
  - [ ] Merge Bills button
  - [ ] Cancel Bill button
  - [ ] Save & New button
  - [x] Payment button (prominent) ✅

## 2.3 New Bill Workflow ⏳

- [x] **Open New Bill** ✅
  - [x] Check active shift exists
  - [x] Auto-generate bill number
  - [x] Assign terminal & cashier
  - [x] Default guest count = 1
  - [x] Status = 'open'

- [ ] **Quick Start Options Modal**
  - [ ] Bill type selection (Dine In / Take Away / Delivery)
  - [ ] Guest count input (for dine-in)
  - [ ] Table selection (for dine-in)
  - [ ] Customer name (optional for takeaway)
  - [ ] Customer phone (optional)
  - [ ] Quick start button
  - [ ] Skip and start empty bill

- [ ] **Session Check**
  - [ ] Verify active session exists
  - [ ] Display warning if no session
  - [ ] Redirect to open session
  - [ ] Lock POS if session overdue

## 2.4 Hold & Recall Bills 🔄

- [x] **Hold Bill Modal** ✅
  - [x] Hold reason dropdown
  - [x] Custom reason textarea
  - [x] Confirm button
  - [x] Update bill status to 'hold'

- [x] **Held Bills List Modal** ✅
  - [x] List all held bills
  - [x] Bill number display
  - [x] Table info
  - [x] Hold reason
  - [x] Hold timestamp
  - [x] Resume button
  - [x] Cancel button

- [ ] **Enhanced Held Bills** ⏳
  - [ ] Filter by terminal
  - [ ] Filter by cashier
  - [ ] Filter by table
  - [ ] Sort by hold time
  - [ ] Quick search bill number
  - [ ] Bill preview tooltip
  - [ ] Auto-refresh list (polling)

## 2.5 Payment Process 🔄

- [x] **Payment Modal** ✅ (Basic)
  - [x] Grand total display
  - [x] Payment method tabs
  - [x] Amount input
  - [x] Calculate change (for cash)
  - [x] Confirm payment button

- [ ] **Enhanced Payment Modal** ⏳
  - [ ] **Cash Payment:**
    - [ ] Quick amount buttons (50k, 100k, 200k, 500k)
    - [ ] Exact amount button
    - [ ] Custom amount input
    - [ ] Change amount (large display)
    - [ ] Print receipt checkbox
  
  - [ ] **Card Payment:**
    - [ ] Card type selection (Debit/Credit/Charge)
    - [ ] EDC terminal selection
    - [ ] Approval code input
    - [ ] Card number last 4 digits
    - [ ] Print receipt checkbox
  
  - [ ] **QRIS Payment:**
    - [ ] QR code display (generate)
    - [ ] Amount display
    - [ ] Payment status polling
    - [ ] Success confirmation
    - [ ] Transaction ID capture
  
  - [ ] **E-Wallet:**
    - [ ] Provider selection (GoPay/OVO/Dana/ShopeePay)
    - [ ] Amount display
    - [ ] Reference number input
    - [ ] Success confirmation
  
  - [ ] **Bank Transfer:**
    - [ ] Bank selection
    - [ ] Account number display
    - [ ] Reference number input
    - [ ] Upload proof (optional)
  
  - [ ] **Voucher:**
    - [ ] Voucher code input
    - [ ] Validate voucher
    - [ ] Discount calculation
    - [ ] Auto-deduct from total

- [ ] **Split Payment** ⏳
  - [ ] Multiple payment methods
  - [ ] Remaining amount tracker
  - [ ] Payment list display
  - [ ] Remove payment button
  - [ ] Complete when total paid

- [ ] **Payment Success** ⏳
  - [x] Success message ✅
  - [x] Receipt preview ✅
  - [ ] Print receipt button (auto-print)
  - [ ] Send receipt via email/WhatsApp
  - [ ] New bill button
  - [ ] Close and return button

- [ ] **Backend: Payment Processing**
  - [x] Payment model ✅
  - [x] Create payment record ✅
  - [ ] Payment validation
  - [ ] Split payment handling
  - [ ] Overpayment handling
  - [ ] Change calculation
  - [ ] Receipt generation
  - [ ] Print job queue

## 2.6 Kitchen Order Integration 🔄

- [x] **Send to Kitchen Button** ✅
  - [x] Check items status
  - [x] Filter items by printer_target
  - [x] Create kitchen orders by station

- [x] **Kitchen Order Model** ✅
  - [x] KitchenOrder model (bill, station)
  - [x] KitchenOrderItem model (snapshot)
  - [x] Unique constraint (bill, station)
  - [x] Prevent duplicate orders ✅

- [ ] **Kitchen Order Status Sync** ⏳
  - [ ] WebSocket connection to KDS
  - [ ] Real-time status updates
  - [ ] Update bill_item status
  - [ ] Visual indicator in POS
  - [ ] Notification when ready

- [ ] **Reprint KOT** ⏳
  - [ ] Reprint button
  - [ ] Select items to reprint
  - [ ] Mark as "REPRINT" on ticket
  - [ ] Audit log

## 2.7 Bill Management Features ⏳

- [ ] **Split Bill** 
  - [ ] Split bill modal
  - [ ] Item selection (checkboxes)
  - [ ] Split by item
  - [ ] Split by amount (percentage)
  - [ ] Split equally (guest count)
  - [ ] Create multiple bills
  - [ ] Link split bills (reference)
  - [ ] Update original bill

- [ ] **Merge Bills**
  - [ ] Select bills to merge
  - [ ] Preview merged bill
  - [ ] Confirm merge
  - [ ] Update table (if different)
  - [ ] Transfer items
  - [ ] Close original bills

- [ ] **Move Table**
  - [ ] Select new table
  - [ ] Check table availability
  - [ ] Update bill table
  - [ ] Audit log

- [ ] **Transfer Bill**
  - [ ] Transfer to another terminal
  - [ ] Transfer to another cashier
  - [ ] Supervisor approval (optional)
  - [ ] Notification to target

- [ ] **Cancel/Void Bill**
  - [ ] Cancel reason dropdown
  - [ ] Supervisor approval required
  - [ ] Void all items
  - [ ] Update bill status
  - [ ] Audit log
  - [ ] Cannot cancel paid bills

## 2.8 Quick Actions & Shortcuts ⏳

- [ ] **Keyboard Shortcuts**
  - [ ] F1: New Bill
  - [ ] F2: Hold Bill
  - [ ] F3: Recall Bills
  - [ ] F4: Payment
  - [ ] F5: Refresh
  - [ ] F8: Send to Kitchen
  - [ ] F9: Open shift
  - [ ] F10: Close shift
  - [ ] ESC: Close modal
  - [ ] Ctrl+F: Search product

- [ ] **Quick Access Bar**
  - [ ] Recent products (frequently used)
  - [ ] Favorites/starred products
  - [ ] Quick bill search (by bill number)
  - [ ] Open bills counter
  - [ ] Held bills counter
  - [ ] Active terminal indicator

- [ ] **Product Search**
  - [ ] Search input (top bar)
  - [ ] Search by name
  - [ ] Search by SKU
  - [ ] Search by barcode
  - [ ] Autocomplete dropdown
  - [ ] Quick add from search

- [ ] **Barcode Scanner Integration**
  - [ ] Listen to barcode scanner input
  - [ ] Product lookup by barcode
  - [ ] Auto-add to bill
  - [ ] Quantity scanning support

---

# PHASE 3: KITCHEN DISPLAY SYSTEM 🔄

## 3.1 KDS Layout & Design ⏳

- [x] **Station Selection** ✅
  - [x] Kitchen/Bar/Dessert dropdown
  - [x] URL routing per station
  - [x] Auto-load orders for station

- [ ] **KDS Main Screen** ⏳
  - [ ] **Layout Options:**
    - [ ] Grid view (cards)
    - [ ] List view (rows)
    - [ ] Kanban view (columns by status)
    - [ ] Toggle view button
  
  - [ ] **Order Card Design:**
    - [ ] Order number (large, prominent)
    - [ ] Table number badge
    - [ ] Order time (elapsed timer)
    - [ ] Priority indicator (color coded)
    - [ ] Items list
    - [ ] Special instructions (highlighted)
    - [ ] Status buttons (bottom)

- [ ] **Order Status Workflow** ⏳
  - [x] New → Preparing → Ready → Served ✅
  - [ ] Color coding:
    - [ ] Red: New (< 2 min)
    - [ ] Orange: Preparing
    - [ ] Yellow: > 10 min (warning)
    - [ ] Green: Ready
    - [ ] Gray: Served
  - [ ] Status transition buttons
  - [ ] Swipe gesture support (tablets)

## 3.2 KDS Features ⏳

- [ ] **Order Management**
  - [ ] Accept order (new → preparing)
  - [ ] Mark ready (preparing → ready)
  - [ ] Bump order (ready → served)
  - [ ] Recall served order (if error)
  - [ ] Multi-select orders (batch actions)
  - [ ] Priority boost button
  - [ ] Delay notification

- [ ] **Order Details Modal**
  - [ ] Full order details
  - [ ] All items with modifiers
  - [ ] Special instructions (large text)
  - [ ] Customer name (if available)
  - [ ] Delivery/takeaway flag
  - [ ] Order source (POS/QR/Online)
  - [ ] Edit order (if not started)
  - [ ] Reprint ticket

- [ ] **KDS Filters & Sort**
  - [ ] Filter by status
  - [ ] Filter by order type (dine-in/takeaway)
  - [ ] Sort by time (oldest first)
  - [ ] Sort by priority
  - [ ] Sort by table number
  - [ ] Show/hide completed orders

- [ ] **KDS Settings Panel**
  - [ ] Auto-accept orders toggle
  - [ ] Auto-bump to served toggle
  - [ ] Alert sound toggle
  - [ ] Alert volume control
  - [ ] Display duration for served orders
  - [ ] Font size adjustment
  - [ ] Color scheme (theme)
  - [ ] Fullscreen mode

- [ ] **KDS Audio Alerts**
  - [ ] New order sound
  - [ ] Order overdue alert (> threshold)
  - [ ] Critical alert (> critical time)
  - [ ] Volume control
  - [ ] Test sound button

## 3.3 KDS Performance Metrics ⏳

- [ ] **Real-time Stats Widget**
  - [ ] Orders pending count
  - [ ] Orders preparing count
  - [ ] Average prep time (today)
  - [ ] Orders completed (today)
  - [ ] Longest pending order time
  - [ ] Station load indicator

- [ ] **Performance Dashboard**
  - [ ] Orders by hour (chart)
  - [ ] Average prep time trend
  - [ ] On-time percentage
  - [ ] Late orders count
  - [ ] Peak hour identification
  - [ ] Staff performance (if multi-user)

## 3.4 KDS Backend ⏳

- [x] **WebSocket Setup** ⏳
  - [ ] Django Channels configuration
  - [ ] Consumer for KDS station
  - [ ] Group subscription per station
  - [ ] Broadcast new orders
  - [ ] Broadcast status updates
  - [ ] Connection heartbeat

- [ ] **Order Flow**
  - [x] Create KitchenOrder on "Send to Kitchen" ✅
  - [ ] Push to WebSocket group
  - [ ] Update order status API
  - [ ] Status change notifications
  - [ ] Sync back to POS (bill_item status)

- [ ] **Order Priority Algorithm**
  - [ ] Auto-assign priority score
  - [ ] Factors: order time, items count, table status
  - [ ] VIP customer boost
  - [ ] Manual priority override

---

# PHASE 4: REPORTING & EOD ⏳

## 4.1 Cashier Reports ⏳

- [ ] **Shift Report UI**
  - [ ] Shift summary card
  - [ ] Period (shift_start → shift_end)
  - [ ] Bills opened count
  - [ ] Bills closed count
  - [ ] Total sales amount
  - [ ] Average bill value
  - [ ] Items added/voided count
  - [ ] Payment breakdown by method
  - [ ] Cash reconciliation section
  - [ ] Export PDF button
  - [ ] Print button

- [x] **Cashier Performance API** ✅
  - [x] get_cashier_summary()
  - [x] get_cashier_shift_report()
  - [x] get_all_cashiers_summary()
  - [x] get_terminal_cashier_report()

- [ ] **Report Views**
  - [x] views_reports.py created ✅
  - [ ] cashier_shift_report view
  - [ ] cashier_daily_report view
  - [ ] outlet_cashiers_report view
  - [ ] terminal_usage_report view
  - [ ] cashier_summary_api (JSON)

- [ ] **Report Templates**
  - [ ] templates/pos/reports/cashier_shift.html
  - [ ] templates/pos/reports/cashier_daily.html
  - [ ] templates/pos/reports/outlet_cashiers.html
  - [ ] templates/pos/reports/terminal_usage.html
  - [ ] templates/pos/reports/partials/cashier_summary.html

## 4.2 Daily Reports (Z-Report) ⏳

- [ ] **Z-Report UI**
  - [ ] Business date selector
  - [ ] Report generation button
  - [ ] Loading indicator
  - [ ] Report sections:
    - [ ] Session info (date, open/close time)
    - [ ] Sales summary (bills count, total amount)
    - [ ] Payment breakdown (by method)
    - [ ] Cashier summary (all cashiers)
    - [ ] Void/cancelled items
    - [ ] Discount summary
    - [ ] Tax & service charge total
    - [ ] Top products sold
    - [ ] Hourly sales chart
  - [ ] Export PDF/Excel
  - [ ] Print Z-Report

- [ ] **Z-Report Backend**
  - [x] generate_eod_report() in EODService ✅
  - [ ] Detailed breakdown by category
  - [ ] Product sales ranking
  - [ ] Hour-by-hour analysis
  - [ ] Comparison with previous day
  - [ ] Chart data generation

## 4.3 EOD (End of Day) Process ⏳

- [ ] **EOD Dashboard**
  - [ ] Current session card
  - [ ] Business date display
  - [ ] Hours since open
  - [ ] Overdue warning banner
  - [ ] Critical lock screen (> 24 hours)
  - [ ] EOD checklist progress
  - [ ] Ready for EOD indicator
  - [ ] Execute EOD button

- [ ] **EOD Validation Screen**
  - [ ] Validation results display
  - [ ] Issues list (blocking)
  - [ ] Warnings list (non-blocking)
  - [ ] Resolution actions:
    - [ ] Close open shifts button
    - [ ] Close/void open bills button
    - [ ] Resolve pending kitchen orders
  - [ ] Refresh validation button
  - [ ] Cannot proceed if issues exist

- [ ] **EOD Checklist Modal**
  - [ ] Checklist items list
  - [ ] Checkbox per item
  - [ ] Completed by & timestamp
  - [ ] Notes ⏳

- [ ] **Database Backup**
  - [ ] Auto-backup schedule
  - [ ] Manual backup button
  - [ ] Backup to external drive
  - [ ] Backup to cloud (optional)
  - [ ] Restore from backup

## 5.8 Master Data Sync (HO/Cloud Integration) ⏳

> **Note:** This feature requires HO/Cloud server infrastructure first  
> **Priority:** Phase 5 (after Edge Server & POS are stable)

### **Production Architecture: Cloud-First Setup**

**Current (Development):** Edge Server creates Company/Outlet/Store locally  
**Production (Cloud-First):** HO/Cloud provides all master data to Edge Server

```
┌─────────────────────────────────────────────────────────┐
│              HO/CLOUD (Master Data)                     │
│                                                         │
│  Admin creates:                                         │
│  • Company (Tenant: YOGYA, ACME, etc)                  │
│  • Outlets (Brands: RESTO-01, CAFE-01)                 │
│  • Stores (Physical: YOGYA-JKT-01, YOGYA-BDG-01)       │
│  • Products, Categories, Users, Pricing                 │
│  • Generate API Key per Store                           │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 1. Authenticate (Store ID + API Key)
                     │ 2. Download Config (Company/Outlet/Store)
                     │ 3. Download Master Data (Products/Users)
                     │ 4. Push Transactions (Bills/Payments/EOD)
                     │
┌────────────────────▼────────────────────────────────────┐
│           EDGE SERVER (Store Replica)                   │
│                                                         │
│  Setup Wizard (Simplified):                             │
│  Step 1: Input Store ID + API Key                      │
│  Step 2: Download & Install Config                     │
│  Step 3: Register Terminal                             │
│  Step 4: Ready to Operate (Offline-First)              │
│                                                         │
│  Daily Operation:                                       │
│  • Run offline (SQLite local)                           │
│  • Sync transactions when online                        │
│  • Pull updates (products/prices)                       │
└─────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ Centralized master data management
- ✅ Consistent data across all stores
- ✅ Fast store setup (2 minutes vs 10 minutes)
- ✅ Real-time pricing/product updates
- ✅ Centralized reporting & analytics

- [ ] **Sync Architecture Design**
  - [ ] Define sync protocol (REST API / WebSocket)
  - [ ] Authentication & security (API Key + JWT)
  - [ ] Data conflict resolution strategy
  - [ ] Offline queue management

- [ ] **Sync Models**
  - [ ] SyncLog model (track sync history)
  - [ ] SyncQueue model (pending changes)
  - [ ] SyncConflict model (conflict resolution)

- [ ] **HO/Cloud API Endpoints (Server Side)**
  ```
  POST   /api/v1/edge/authenticate         (Store ID + API Key → JWT Token)
  GET    /api/v1/edge/stores/{store_id}/config    (Company/Outlet/Store data)
  GET    /api/v1/edge/stores/{store_id}/products  (All products & categories)
  GET    /api/v1/edge/stores/{store_id}/users     (Store staff & permissions)
  GET    /api/v1/edge/stores/{store_id}/tables    (Table layout & assignments)
  POST   /api/v1/edge/stores/{store_id}/transactions  (Push bills/payments)
  POST   /api/v1/edge/stores/{store_id}/eod       (Push EOD reports)
  GET    /api/v1/edge/stores/{store_id}/updates   (Check for updates)
  ```

- [ ] **Edge Server Client (Cloud Sync Service)**
  ```python
  # apps/core/services/cloud_sync.py
  
  class CloudSyncService:
      def authenticate(store_id, api_key):
          """Authenticate with HO/Cloud and get JWT token"""
      
      def download_config(store_id):
          """Download Company, Outlet, Store configuration"""
      
      def download_master_data(store_id):
          """Download Products, Categories, Users, Tables"""
      
      def setup_edge_server(store_id, api_key):
          """Complete automated setup wizard flow"""
          # 1. Authenticate & get token
          # 2. Download config (Company/Outlet/Store)
          # 3. Download master data (Products/Users/Tables)
          # 4. Save to local SQLite
          # 5. Mark as configured & ready
      
      def push_transactions(bills, payments):
          """Push completed transactions to HO/Cloud"""
      
      def pull_updates():
          """Check and download updates from HO/Cloud"""
  ```

- [ ] **Simplified Setup Wizard (Cloud-First)**
  - [ ] Step 1: Cloud Connection
    - [ ] Input HO/Cloud URL
    - [ ] Input Store ID
    - [ ] Input API Key
    - [ ] Test connection button
  - [ ] Step 2: Download Configuration
    - [ ] Show Company/Outlet/Store info
    - [ ] Display download progress (Products, Users, Tables)
    - [ ] Confirm & install button
  - [ ] Step 3: Register Terminal
    - [ ] Terminal code input
    - [ ] Device type selection
    - [ ] Register & activate

- [ ] **Sync to Head Office (Push)**
  - [ ] Push bills (completed transactions)
  - [ ] Push payments
  - [ ] Push shift reports
  - [ ] Push EOD reports
  - [ ] Push inventory adjustments
  - [ ] Auto-push when online
  - [ ] Manual push trigger

- [ ] **Sync from Head Office (Pull)**
  - [ ] Pull products (new items, price changes)
  - [ ] Pull categories
  - [ ] Pull promotions
  - [ ] Pull users (new staff)
  - [ ] Pull company/outlet config
  - [ ] Auto-pull schedule (every 1 hour)
  - [ ] Manual pull trigger

- [ ] **Sync Status UI** (in Management Interface)
  - [ ] Last sync timestamp
  - [ ] Sync in progress indicator
  - [ ] Pending items count (push queue)
  - [ ] Failed sync items (retry)
  - [ ] Sync history log
  - [ ] Manual sync button
  - [ ] View synced data

- [ ] **Conflict Resolution**
  - [ ] Detect conflicts (same record updated both sides)
  - [ ] Resolution strategies:
    - [ ] HO wins (default for master data)
    - [ ] Edge wins (for transactions)
    - [ ] Manual resolution (for critical data)
  - [ ] Conflict notification
  - [ ] Conflict resolution UI

- [ ] **Sync Error Handling**
  - [ ] Retry mechanism (3 attempts)
  - [ ] Exponential backoff
  - [ ] Error notification
  - [ ] Error log
  - [ ] Manual retry optionisplay
  - [ ] Validation issues list
  - [ ] Force close options:
    - [ ] Auto-close all shifts checkbox
    - [ ] Auto-void open bills checkbox
  - [ ] Supervisor password input
  - [ ] Force reason textarea (required)
  - [ ] Confirm force EOD button
  - [ ] Audit log preview

- [ ] **EOD Success Screen**
  - [ ] Success message
  - [ ] Closed session summary
  - [ ] New session created
  - [ ] Next business date
  - [ ] Print EOD report button
  - [ ] Open new shift button
  - [ ] Back to dashboard button

- [ ] **Backend: EOD Services**
  - [x] EODService class ✅
  - [x] check_eod_status()
  - [x] validate_eod_readiness()
  - [x] execute_eod()
  - [x] generate_eod_report()
  - [ ] EOD API endpoints
  - [ ] Force EOD with approval
  - [ ] EOD notification service

## 4.4 Sales Reports ⏳

- [ ] **Sales Summary**
  - [ ] Period selector (today/week/month/custom)
  - [ ] Total sales amount
  - [ ] Bills count
  - [ ] Average bill value
  - [ ] Payment method breakdown (pie chart)
  - [ ] Bill type breakdown (dine-in/takeaway/delivery)
  - [ ] Hourly sales chart (bar chart)
  - [ ] Daily trend (line chart)

- [ ] **Product Performance**
  - [ ] Top 10 products (best sellers)
  - [ ] Bottom 10 products (slow movers)
  - [ ] Product ranking by revenue
  - [ ] Product ranking by quantity
  - [ ] Category performance
  - [ ] Filter by date range
  - [ ] Export to Excel

- [ ] **Table Performance**
  - [ ] Table utilization rate
  - [ ] Average dining time per table
  - [ ] Revenue per table
  - [ ] Table turnover rate
  - [ ] Peak hour by table
  - [ ] Section performance comparison

## 4.5 Inventory Reports ⏳

- [ ] **Stock Level Report**
  - [ ] Current stock by product
  - [ ] Low stock alerts
  - [ ] Out of stock items
  - [ ] Stock value (cost)
  - [ ] Filter by category
  - [ ] Export to Excel

- [ ] **Stock Movement**
  - [ ] Usage by product (period)
  - [ ] Stock in/out tracking
  - [ ] Wastage tracking
  - [ ] COGS calculation
  - [ ] Variance analysis

---

# PHASE 5: ADVANCED FEATURES ⏳

## 5.1 Customer Management ⏳

- [ ] **Customer Database**
  - [ ] Customer model (name, phone, email)
  - [ ] Purchase history
  - [ ] Total spend
  - [ ] Visit count
  - [ ] Favorite products
  - [ ] Notes/preferences

- [ ] **Customer Lookup**
  - [ ] Quick search in POS
  - [ ] Search by phone
  - [ ] Search by name
  - [ ] Auto-complete
  - [ ] Add new customer inline
  - [ ] Link to bill

- [ ] **Loyalty Program** (Future)
  - [ ] Points accumulation
  - [ ] Points redemption
  - [ ] Membership tiers
  - [ ] Birthday discounts
  - [ ] Referral program

## 5.2 Promotions & Discounts ⏳

- [ ] **Promotion Setup**
  - [ ] Promotion model (already exists)
  - [ ] Rule configuration
  - [ ] Discount type (percent/value/free item)
  - [ ] Conditions (category/product/day/payment)
  - [ ] Time-based activation
  - [ ] Auto-apply flag

- [ ] **Promotion Application**
  - [ ] Auto-apply promotions
  - [ ] Manual promotion selection
  - [ ] Discount code input
  - [ ] Promotion preview
  - [ ] Multiple promotions conflict resolution
  - [ ] Promotion audit trail

- [ ] **Voucher System**
  - [ ] Voucher model (already exists)
  - [ ] Voucher code generation
  - [ ] Voucher validation
  - [ ] Usage limit tracking
  - [ ] Expiry date check
  - [ ] Voucher report

## 5.3 QR Order (Customer Self-Order) ⏳

- [x] **QR Order Model** ✅
  - [x] Basic structure exists

- [ ] **QR Code Generation**
  - [ ] Generate QR per table
  - [ ] QR includes: store, table, session token
  - [ ] Print QR stickers
  - [ ] QR code refresh (security)

- [ ] **Customer Menu UI**
  - [ ] Mobile-optimized menu
  - [ ] Product images & descriptions
  - [ ] Add to cart
  - [ ] Cart summary
  - [ ] Special instructions input
  - [ ] Submit order button

- [ ] **Order Confirmation**
  - [ ] Order submitted message
  - [ ] Order number display
  - [ ] Track order status
  - [ ] Call waiter button
  - [ ] Request bill button

- [ ] **Backend: QR Order**
  - [ ] QR validation
  - [ ] Create bill from QR order
  - [ ] Assign table
  - [ ] Notify KDS
  - [ ] Notify POS (new order alert)
  - [ ] Payment request handling

## 5.4 Delivery Integration ⏳

- [ ] **Delivery Partner Setup**
  - [ ] GrabFood integration
  - [ ] GoFood integration
  - [ ] ShopeeFood integration
  - [ ] API configuration
  - [ ] Order webhook handling

- [ ] **Delivery Order Processing**
  - [ ] Receive delivery order
  - [ ] Create bill automatically
  - [ ] Mark as delivery type
  - [ ] Send to kitchen
  - [ ] Update delivery partner status
  - [ ] Auto-complete when ready

## 5.5 Printing System ⏳

- [ ] **Printer Configuration**
  - [ ] Printer model (already exists)
  - [9] Printer setup UI
  - [ ] Test print function
  - [ ] Printer status monitoring
  - [ ] Fallback printer

- [ ] **Receipt Templates**
  - [ ] Customer receipt (thermal)
  - [ ] KOT (Kitchen Order Ticket)
  - [ ] Bill summary (A4)
  - [ ] Shift report
  - [ ] Z-Report
  - [ ] Customizable header/footer

- [ ] **Print Queue**
  - [ ] Print job queue
  - [ ] Retry failed prints
  - [ ] Print history
  - [ ] Reprint function

## 5.6 Multi-Language Support ⏳

- [ ] **Language Setup**
  - [ ] Django i18n configuration
  - [ ] Language selector
  - [ ] Supported languages (ID/EN)
  - [ ] Translation files

- [ ] **UI Translation**
  - [ ] POS interface
  - [ ] KDS interface
  - [ ] Reports
  - [ ] Receipts
  - [ ] Product names (optional)

## 5.7 Backup & Sync ⏳

- [ ] **Database Backup**
  - [ ] Auto-backup schedule
  - [ ] Manual backup button
  - [ ] Backup to external drive
  - [ ] Backup to cloud (optional)
  - [ ] Restore from backup

- [ ] **Sync to Head Office**
  - [ ] Sync queue (sync_log model)
  - [ ] Auto-sync when online
  - [ ] Manual sync trigger
  - [ ] Sync status indicator
  - [ ] Conflict resolution
  - [ ] Retry mechanism

## 5.8 Settings & Configuration ⏳

- [ ] **Store Settings UI**
  - [ ] Store info edit
  - [ ] Outlet selection
  - [ ] Tax rate configuration
  - [ ] Service charge configuration
  - [ ] Receipt customization
  - [ ] Printer assignment

- [ ] **User Management UI**
  - [ ] User list
  - [ ] Add/edit user
  - [ ] Role assignment
  - [ ] Password reset
  - [ ] User permissions
  - [ ] Active/inactive toggle

- [ ] **Terminal Management UI**
  - [ ] Terminal list (already exists)
  - [ ] Terminal registration
  - [ ] Terminal status
  - [ ] Deactivate terminal
  - [ ] Reassign terminal

- [ ] **Product Management UI**
  - [ ] Product list with search
  - [ ] Add/edit product
  - [ ] Bulk upload (Excel)
  - [ ] Image upload
  - [ ] Category management
  - [ ] Stock adjustment

- [ ] **Table Management UI**
  - [ ] Table layout designer
  - [ ] Add/edit/delete tables
  - [ ] Table capacity setting
  - [ ] Section/zone assignment
  - [ ] Visual table map

---

# 📊 PROGRESS SUMMARY

## Overall Completion: ~25%

### ✅ Completed (Phase 1): 100%
- Multi-tenant architecture
- Terminal registration system
- Setup wizard UI
- User management
- Product master data
- Table management

### 🔄 In Progress (Phase 0): 0% - **CURRENT PRIORITY**
- Management dashboard
- Terminal management page
- Access control
- Real-time metrics

### 🔄 In Progress (Phase 2): 40%
- Session & shift management (models ✅, UI ⏳)
- POS main screen (core ✅, enhanced ⏳)
- Payment process (basic ✅, enhanced ⏳)
- Kitchen order integration (models ✅, UI ⏳)
- Bill management features (partial)

### ⏳ Pending (Phase 3): 20%
- KDS layout & design (basic ✅)
- KDS features
- KDS performance metrics
- WebSocket implementation

### ⏳ Pending (Phase 4): 10%
- Cashier reports (backend ✅, UI ⏳)
- Daily reports (Z-Report)
- EOD process (models ✅, UI ⏳)
- Sales reports

### ⏳ Pending (Phase 5): 0%
- Advanced0 (CURRENT - NEW): Management Interface ⚡
> **Focus:** Edge Server monitoring & control for Store Manager
1. [ ] Create `/management/` app structure
2. [ ] Dashboard with real-time metrics (revenue, terminals, cashiers)
3. [ ] Terminal Management page (list, status, deactivate, delete)
4. [ ] Access control (@manager_required decorator)
5. [ ] Sidebar navigation layout

## Sprint 1
- Master data sync (HO/Cloud integration)

---

# 🎯 IMMEDIATE PRIORITIES

## Sprint 1 (Current): Session & Shift Management
1. [ ] Store session open/close UI
2. [ ] Cashier shift open/close UI
3. [ ] Cash reconciliation modal
4. [ ] Session dashboard

## Sprint 2: Enhanced Payment
1. [ ] Multi-payment method UI
2. [ ] Split payment
3. [ ] QRIS integration
4. [ ] Receipt templates

## Sprint 3: KDS Enhancement
1. [ ] WebSocket real-time updates
2. [ ] KDS order card redesign
3. [ ] Audio alerts
4. [ ] Performance metrics widget

## Sprint 4: EOD Process
1. [ ] EOD checklist UI
2. [ ] EOD validation screen
3. [ ] Force EOD workflow
4. [ ] Z-Report generation

## Sprint 5: Reports Dashboard
1. [ ] Cashier report UI
2. [ ] Sales report charts
3. [ ] Product performance
4. [ ] Export functionality

---

# 📝 NOTES & CONVENTIONS

## UI/UX Guidelines
- **Mobile-first**: All UI should work on tablets
- **Keyboard shortcuts**: Power users need speed
- **Color coding**: Consistent status colors across app
- **Loading states**: Always show loading indicators
- **Error handling**: User-friendly error messages
- **Confirmation modals**: For destructive actions

## Code Standards
- **HTMX for interactions**: Minimize JavaScript
- **Tailwind for styling**: Utility-first CSS
- **Alpine.js for reactivity**: Component-level state
- **Django views**: Server-side rendering preferred
- **API endpoints**: JSON for AJAX requests
- **Type hints**: Python 3.10+ type annotations

## Testing Strategy
- **Manual testing**: Each feature before commit
- **User acceptance**: Test with actual cashier
- **Performance testing**: Load test with 100+ bills
- **Offline testing**: Disconnect network, verify offline mode
- **Print testing**: Test with actual thermal printers

## Documentation
- **ERD**: Update when models change
- **API docs**: Document all endpoints
- **User guide**: Screenshots + instructions
- **Deployment guide**: Step-by-step setup

---

**Last Updated:** January 17, 2026  
**Next Review:** After Sprint 1 completion
