# Master Data Views - Table Areas, Promotions & Vouchers

## Overview
Telah ditambahkan 3 halaman view baru untuk melihat data yang akan di-sync dari Head Office:
- **Table Areas**: Zona/area meja dalam restoran
- **Promotions**: Promosi dan diskon aktif
- **Vouchers**: Voucher kode diskon pelanggan

## Files Created/Modified

### 1. Views (apps/management/views.py)
Ditambahkan 3 view functions baru:

#### `table_areas_list()`
- Menampilkan semua table areas untuk outlet
- Fitur: Search, count tables per area
- URL: `/management/master-data/table-areas/`

#### `promotions_list()`
- Menampilkan semua promotions untuk outlet
- Fitur: Filter by status (active/inactive), filter by type, search
- Stats: Active count, valid count, inactive count
- URL: `/management/master-data/promotions/`

#### `vouchers_list()`
- Menampilkan semua vouchers
- Fitur: Filter by status (active/used/inactive), search by code/customer
- Stats: Active count, used count, expired count
- URL: `/management/master-data/vouchers/`

### 2. URLs (apps/management/urls.py)
Ditambahkan 3 URL patterns:
```python
path('master-data/table-areas/', views.table_areas_list, name='table_areas'),
path('master-data/promotions/', views.promotions_list, name='promotions'),
path('master-data/vouchers/', views.vouchers_list, name='vouchers'),
```

### 3. Templates
Dibuat 3 template baru:

#### templates/management/table_areas.html
- List semua table areas dengan sort order
- Menampilkan jumlah tables per area
- Search functionality
- Info note: Data will be synced from HO

#### templates/management/promotions.html
- List promotions dengan filtering
- Tipe promosi: Percent Discount, Amount Discount, Buy X Get Y, Combo, Free Item
- Menampilkan: Name, code, type, discount value, valid period, usage count, status
- Filter by: Status (active/inactive), Type, Search (name/code)
- Stats cards: Total, Active, Currently Valid, Inactive

#### templates/management/vouchers.html
- List vouchers dengan filtering
- Menampilkan: Code, promotion, customer, expiry date, status, used_at
- Filter by: Status (active/used/inactive), Search (code/customer)
- Stats cards: Total, Active (unused), Used, Expired

### 4. Master Data Dashboard Updated
Updated `master_data()` view untuk menambahkan URL links:
- Table Areas → clickable "View" button
- Promotions → clickable "View" button
- Vouchers → clickable "View" button

## Features per View

### Table Areas View
- **Search**: Search by area name
- **Display**: Area name, sort order, table count, outlet
- **Stats**: Total areas, total tables in all areas
- **Note**: Read-only, synced from HO

### Promotions View
**Filters:**
- Status: All / Active / Inactive
- Type: All types / Percent Discount / Amount Discount / Buy X Get Y / Combo / Free Item
- Search: Name or code

**Display Columns:**
- Name / Code
- Type (badge)
- Discount value (%, Rp, or combo price)
- Valid period (start - end date)
- Usage count (current / max)
- Status (Active/Inactive + Auto-apply badge)

**Stats:**
- Total promotions
- Active promotions
- Currently valid (within date range & active)
- Inactive promotions

### Vouchers View
**Filters:**
- Status: All / Active (unused) / Used / Inactive
- Search: Code, customer name, or phone

**Display Columns:**
- Voucher code (monospace font)
- Promotion name & type
- Customer name & phone (if assigned)
- Expiry date
- Status (Active/Used/Inactive/Expired)
- Used at (timestamp)

**Stats:**
- Total vouchers
- Active (available for use)
- Used vouchers
- Expired vouchers

## Access URLs

From Master Data dashboard (http://127.0.0.1:8001/management/master-data/):

1. **Table Areas**: 
   - http://127.0.0.1:8001/management/master-data/table-areas/
   - Shows all restaurant zones/areas

2. **Promotions**: 
   - http://127.0.0.1:8001/management/master-data/promotions/
   - Shows all discount promotions and deals

3. **Vouchers**: 
   - http://127.0.0.1:8001/management/master-data/vouchers/
   - Shows all voucher codes

## Design Patterns

All three views follow consistent design:
- **Header**: Title, description, back button
- **Filters**: Search and status/type filters
- **Stats Cards**: Key metrics at a glance
- **Data Table**: Clean, responsive table layout
- **Empty State**: Friendly message with icon when no data
- **Info Note**: Blue banner explaining HO sync

## Database Queries

All views properly handle relationships:
- Table Areas: `outlet` foreign key
- Promotions: `outlet` foreign key
- Vouchers: Through `promotion__outlet` relationship

Count queries are optimized to avoid N+1 problems.

## Status Badges

Consistent color scheme:
- **Green**: Active, Available, Used (completed)
- **Blue**: Currently Valid, Special states
- **Yellow**: Reserved, Pending
- **Red**: Inactive, Expired
- **Purple**: Type badges

## Notes

1. **Read-Only Views**: These are view-only pages. Data management happens at HO level.
2. **Sync Ready**: All views show data that will be synced from Head Office
3. **Responsive**: All tables are responsive and work on mobile
4. **Consistent UI**: Follows same design patterns as Categories, Products, Users, Tables pages
5. **Empty States**: Graceful handling when no data exists yet

## Testing Checklist

✅ Server running on port 8001
✅ Views added to apps/management/views.py
✅ URLs configured in apps/management/urls.py
✅ Templates created in templates/management/
✅ Master data dashboard links updated
✅ Imports added (Promotion, Voucher models)

**To Test:**
1. Access http://127.0.0.1:8001/management/master-data/
2. Click "View →" button on Table Areas card
3. Click "View →" button on Promotions card
4. Click "View →" button on Vouchers card
5. Test filters and search on each page
6. Verify empty states show properly (if no data)
7. Check responsive design on different screen sizes

## Next Steps

Future enhancements:
- Add detail modals for viewing full promotion details
- Add voucher validation preview
- Add export functionality
- Add sync status indicators
- Add last sync timestamp display
