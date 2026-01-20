http://127.0.0.1:8000/setup/

# BULK IMPORT SYSTEM v3.0 - TWO-FILE APPROACH

## 🎯 Overview: Two-Step Import Process

**Step 1: Import Condiment Groups (Master Data)**
- URL: http://127.0.0.1:8000/management/master-data/import-condiment-groups/
- Define all modifier groups with their options ONCE
- Example: "Coffee Taste" with options (Bold, Fruity, Smooth)

**Step 2: Import Products**
- URL: http://127.0.0.1:8000/management/master-data/import-excel/
- Products REFERENCE existing groups by name
- Example: Product uses "Coffee Taste,Size,Ice Level"

## ✨ Benefits of Two-File System

✅ **Cleaner Excel Files**
- Products: 1 row per product (vs 10+ rows in old format!)
- Example: Hot Americano = 1 row (vs 7 rows for all condiments)

✅ **Define Once, Use Everywhere**
- Create "Coffee Taste" group → Use for ALL coffee products
- Update "Coffee Taste" → Automatically affects ALL coffees

✅ **No Duplication**
- Define "Size" (Regular, Large) once
- Reuse for Americano, Cappuccino, Latte, etc.

✅ **No Typos**
- Reference exact group names
- System validates groups exist

✅ **Easy Maintenance**
- Add new option to "Spicy Level" → All products updated
- Change fee for "Oat Milk" → All products with Milk Upgrade updated

---

# STEP 1: IMPORT CONDIMENT GROUPS
URL: http://127.0.0.1:8000/management/master-data/import-condiment-groups/

## 📥 Download Template
Click **"Download Template"** button to get condiment_groups_template.xlsx

## Excel File Format

### Required Columns:
- **Group Name** - Modifier group name (e.g., Coffee Taste, Spicy Level)
- **Option Name** - Individual option (e.g., Bold, Medium, Large)
- **Fee** - Additional charge (0 = free)

### Optional Columns:
- **Is Required** - Yes/No (must customer choose?)
- **Max Selections** - How many options can be selected (default: 1)

## Example Excel Structure:

| Group Name    | Option Name          | Fee   | Is Required | Max Selections |
|---------------|----------------------|-------|-------------|----------------|
| Coffee Taste  | Bold                | 0     | No          | 1              |
| Coffee Taste  | Fruity              | 0     | No          | 1              |
| Coffee Taste  | Smooth              | 0     | No          | 1              |
| Spicy Level   | No Chili            | 0     | No          | 1              |
| Spicy Level   | Medium              | 1000  | No          | 1              |
| Spicy Level   | Hot                 | 2000  | No          | 1              |
| Size          | Regular             | 0     | Yes         | 1              |
| Size          | Large               | 5000  | Yes         | 1              |
| Sugar Level   | No Sugar            | 0     | No          | 1              |
| Sugar Level   | Normal              | 0     | No          | 1              |
| Milk Upgrade  | Regular Milk        | 0     | No          | 1              |
| Milk Upgrade  | Oat Milk            | 8000  | No          | 1              |
| Extra Topping | Telur Mata Sapi     | 5000  | No          | 3              |
| Extra Topping | Ayam Suwir          | 12000 | No          | 3              |

**Note:**
- One row = One option within a group
- Same Group Name = Options belong to same group
- Max Selections = 1 for single choice, 3+ for multiple choice

---

# STEP 2: IMPORT PRODUCTS
URL: http://127.0.0.1:8000/management/master-data/import-excel/

## 📥 Download Template
Click **"Download Template"** button to get product_import_template_v3.xlsx

## Excel File Format

### Required Columns:
- **Category** - Main category (e.g., Beverage, Food)
- **Menu Category** - Sub-category/description (e.g., Hot Coffee, Ice Coffee)
- **Nama Product** - Product name
- **PLU Product** - Product SKU/code (unique identifier)
- **Price Product** - Base price in number format
- **Image Product** - Image file path (e.g., avril/images/menus/product.jpg)

### Optional Columns:
- **Printer Kitchen** - Printer target for orders (default: kitchen)
  - **kitchen** - Food items go to kitchen printer (Nasi Goreng, Mie Goreng, Steak)
  - **bar** - Beverages go to bar printer (Coffee, Juice, Cocktails)
  - **dessert** - Desserts go to dessert station (Cake, Ice Cream)
  - **none** - No printing needed
- **Condiment Groups** - 🆕 Comma-separated group names (e.g., Coffee Taste,Size,Ice Level)

## Example Product Excel Structure (v3.0):

| Category | Menu Category | Nama Product      | PLU Product | Printer Kitchen | Condiment Groups                         | Price Product | Image Product                            |
|----------|---------------|-------------------|-------------|-----------------|------------------------------------------|---------------|------------------------------------------|
| Beverage | Hot Coffee    | Hot Americano     | 03835821    | bar             | Coffee Taste,Size,Ice Level             | 27000         | avril/images/menus/americano.jpg         |
| Beverage | Hot Coffee    | Hot Cappuccino    | 03835822    | bar             | Coffee Taste,Size,Sugar Level,Milk Upgrade | 33000       | avril/images/menus/cappuccino.jpg        |
| Beverage | Ice Coffee    | Ice Latte         | 03835823    | bar             | Coffee Taste,Size,Ice Level             | 38000         | avril/images/menus/latte.jpg             |
| Food     | Noodle        | Mie Goreng        | 15038301    | kitchen         | Spicy Level,Extra Topping               | 25000         | avril/images/menus/mie-goreng.jpg        |
| Food     | Rice          | Nasi Goreng       | 15038302    | kitchen         | Spicy Level,Extra Topping               | 22000         | avril/images/menus/nasi-goreng.jpg       |
| Beverage | Water         | Mineral Water     | 03835899    | none            |                                          | 5000          | avril/images/menus/mineral-water.jpg     |

**Key Features:**
- **1 Row = 1 Product** (vs 10+ rows in old format!)
- **Comma-separated groups**: "Coffee Taste,Size,Ice Level" links to 3 groups
- **Empty = No modifiers**: Mineral Water has no modifiers (blank cell)
- **Shared groups**: "Coffee Taste" REUSED by 3 coffee products
- **Mixed groups**: Food uses "Spicy Level,Extra Topping" / Coffee uses "Coffee Taste,Size"

---

## 📊 COMPARISON: Old vs New Format

### OLD FORMAT (Single File - Inline):
```
Product with 3 condiments = 7 ROWS in Excel
- Row 1: Product + Condiment 1, Option A
- Row 2: Same Product + Condiment 1, Option B  
- Row 3: Same Product + Condiment 1, Option C
- Row 4: Same Product + Condiment 2, Option A
- Row 5: Same Product + Condiment 2, Option B
- Row 6: Same Product + Condiment 3, Option A
- Row 7: Same Product + Condiment 3, Option B

3 Coffee Products × 7 rows each = 21 ROWS TOTAL!
```

### NEW FORMAT (Two Files - Reference):
```
FILE 1: Condiment Groups (Master Data)
- Define "Coffee Taste" once with 3 options
- Define "Size" once with 2 options  
- Define "Ice Level" once with 3 options
Total: 8 rows for ALL options

FILE 2: Products
- Hot Americano: Coffee Taste,Size,Ice Level (1 ROW)
- Hot Cappuccino: Coffee Taste,Size,Sugar Level (1 ROW)
- Ice Latte: Coffee Taste,Size,Ice Level (1 ROW)

3 Coffee Products = 3 ROWS ONLY!
Total: 8 + 3 = 11 rows (vs 21 rows in old format)
```

**Result**: 48% LESS ROWS + Easy maintenance!

---

# IMPORT WORKFLOW

## Step-by-Step Process:

### 1️⃣ **Import Condiment Groups FIRST**
```
Navigate to: http://127.0.0.1:8000/management/master-data/import-condiment-groups/
Download: condiment_groups_template.xlsx
Fill in: Your modifier groups and options
Upload: Click "Import" button
Result: ✅ 7 groups created with 18 options
```

### 2️⃣ **Import Products SECOND**
```
Navigate to: http://127.0.0.1:8000/management/master-data/import-excel/
Download: product_import_template_v3.xlsx
Fill in: Your products with comma-separated group references
Upload: Click "Import" button
Result: ✅ 6 products created and linked to groups
```

### 3️⃣ **Verify Linkage**
```
Check: Product detail page in POS system
Result: Product shows all linked modifiers from groups
Example: Hot Americano displays:
  - Coffee Taste (Bold, Fruity, Smooth)
  - Size (Regular, Large +5000)
  - Ice Level (No Ice, Less Ice, Regular Ice)
```

---

# VALIDATION & ERROR HANDLING

## ✅ Success Messages:
- "✅ Successfully created 7 condiment groups with 18 options"
- "✅ Successfully imported 6 products and linked to 14 modifier groups"

## ⚠️ Common Errors:

### Error: "Condiment group 'Coffee Taste' not found. Import groups first!"
**Cause**: Trying to import products before importing groups
**Solution**: 
1. Import condiment_groups.xlsx FIRST
2. Then import products.xlsx

### Error: "Row 5: Condiment group 'Coffe Taste' not found"
**Cause**: Typo in group name (Coffe vs Coffee)
**Solution**: 
- Check exact spelling in condiment groups
- Group names are case-sensitive
- Use exact name from Step 1

### Error: "Missing required column: Group Name"
**Cause**: Wrong Excel template or modified headers
**Solution**: Download fresh template and don't modify headers

---

# BACKWARD COMPATIBILITY

## ✅ Old Format Still Works!

The system supports BOTH formats:

### Option A: New Format (Recommended)
- Two files: condiment_groups.xlsx + products.xlsx
- Clean and maintainable

### Option B: Old Format (Legacy Support)
- Single file with inline condiments
- Columns: Condiment Group, Condiment, PLU Condiment, Fee Condiment
- System auto-creates groups and options

**Recommendation**: Migrate to new format for easier maintenance!

---

# TEST FILES INCLUDED

## Download Test Files:

### 1. `test_condiment_groups.xlsx`
**Location**: Project root folder
**Contents**:
- 7 condiment groups:
  - Coffee Taste (3 options)
  - Spicy Level (3 options)  
  - Size (2 options)
  - Sugar Level (2 options)
  - Ice Level (3 options)
  - Milk Upgrade (2 options)
  - Extra Topping (3 options)
- **Total**: 18 options

**Purpose**: Import this FIRST to create master data

### 2. `test_products_v3.xlsx`
**Location**: Project root folder
**Contents**:
- 6 products demonstrating various group combinations:
  - Hot Americano → Coffee Taste,Size,Ice Level
  - Hot Cappuccino → Coffee Taste,Size,Sugar Level,Milk Upgrade
  - Ice Latte → Coffee Taste,Size,Ice Level
  - Nasi Goreng → Spicy Level,Extra Topping
  - Mie Goreng → Spicy Level,Extra Topping
  - Mineral Water → (no groups - blank)

**Purpose**: Import this SECOND to link products to groups

### Quick Test:
```bash
1. Go to: http://127.0.0.1:8000/management/master-data/import-condiment-groups/
2. Upload: test_condiment_groups.xlsx
3. Result: ✅ 7 groups, 18 options created

4. Go to: http://127.0.0.1:8000/management/master-data/import-excel/
5. Upload: test_products_v3.xlsx  
6. Result: ✅ 6 products linked to groups

7. Verify: Open POS → Hot Americano shows 3 modifier groups
```

---

# TIPS & BEST PRACTICES

## 📌 Organizing Condiment Groups

**Group Naming Convention:**
- Use descriptive names: "Coffee Taste" not "Taste1"
- Be specific: "Milk Upgrade" not "Milk"
- Use title case: "Spicy Level" not "spicy level"

**Shared Groups Strategy:**
- **Universal groups**: Size, Sugar Level → Use for ALL beverages
- **Category groups**: Coffee Taste → Only for coffee products
- **Specialized groups**: Extra Topping → Only for food products

## 📌 Product Import Tips

**Comma-Separated Format:**
- No spaces after comma: `Coffee Taste,Size` ✅ 
- With spaces (ok): `Coffee Taste, Size` ✅
- Group order doesn't matter
- Blank cell = No modifiers (like Mineral Water)

**When to Use Multiple Groups:**
- Coffee: `Coffee Taste,Size,Sugar Level,Milk Upgrade` (4 groups)
- Food: `Spicy Level,Extra Topping` (2 groups)
- Simple products: Leave blank (no modifiers)

## 📌 Maintenance Workflow

**Adding New Option to Existing Group:**
1. Export current groups (manually from database or re-download template)
2. Add new row: `Coffee Taste | Caramel | 3000`
3. Enable "Update Existing Groups" checkbox
4. Upload → New option added to ALL products using Coffee Taste

**Creating New Group:**
1. Add rows to condiment_groups.xlsx
2. Upload condiment groups
3. Update product Excel: Add new group name to "Condiment Groups" column
4. Re-upload products

**Removing Group from Product:**
1. Edit product Excel
2. Remove group name from comma-separated list
3. Re-upload products

---

# TECHNICAL DETAILS

## Database Structure:

```python
# Modifier (Condiment Group)
- name = "Coffee Taste"
- is_required = False
- max_selections = 1
- products = M2M relationship

# ModifierOption (Individual Options)  
- modifier = ForeignKey to Modifier
- name = "Bold"
- price_adjustment = 0

# Product
- name = "Hot Americano"
- modifiers = M2M relationship to Modifier
```

## Import Process:

**Step 1 - Import Groups:**
```python
1. Read condiment_groups.xlsx
2. Group rows by "Group Name"
3. Create Modifier record for each unique group
4. Create ModifierOption for each option row
5. Set is_required, max_selections on Modifier
```

**Step 2 - Import Products:**
```python
1. Read products.xlsx
2. Parse "Condiment Groups" column (split by comma)
3. For each group name:
   - Look up existing Modifier by name
   - Link product via M2M relationship
   - Error if group not found
```

---

# TROUBLESHOOTING

## Issue: Products not showing modifiers in POS
**Check:**
1. Did you import groups FIRST?
2. Are group names spelled exactly the same?
3. Check admin panel: Does product have modifiers linked?

**Solution**: Re-import products with correct group names

## Issue: "Update Existing Groups" not working
**Check:**
1. Is group name EXACTLY the same? (case-sensitive)
2. Are you uploading to correct outlet?

**Solution**: Verify group name, try without checkbox first to create new

## Issue: Too many duplicate groups
**Cause**: Uploading same file multiple times without "Update Existing"
**Solution**: 
- Delete duplicate groups in admin panel
- Enable "Update Existing Groups" checkbox on re-upload

---

# MIGRATION GUIDE: Old Format → New Format

## Step 1: Export Current Data
1. Go to admin panel: `/admin/pos/product/`
2. Analyze existing modifiers used by products
3. List unique modifier groups (e.g., Coffee Taste, Size, Spicy Level)

## Step 2: Create Condiment Groups File
1. Download: condiment_groups_template.xlsx
2. Add all unique groups from Step 1
3. Add all options for each group
4. Set fees, is_required, max_selections

## Step 3: Update Product File
1. Download: product_import_template_v3.xlsx
2. List products (1 row per product)
3. In "Condiment Groups" column, add comma-separated group names
4. Remove old inline condiment columns

## Step 4: Test Import
1. Import condiment_groups.xlsx → Verify groups created
2. Import products.xlsx → Verify products linked
3. Test in POS system → Verify modifiers appear

## Step 5: Production Import
1. Backup database first!
2. Import condiment groups
3. Import products
4. Verify ALL products show correct modifiers

---
  - Each group will be displayed separately in POS
  - Makes it easy for customers to choose from different categories
- **Condiment** - Option name within the group (e.g., Bold, Medium, Large)
- **PLU Condiment** - (Optional, for your reference only - NOT stored in database)
- **Fee Condiment** - Additional price for modifier (0 = free option)

## ✨ Condiment Groups Feature

### Why Use Condiment Groups?
Instead of mixing all modifiers together, you can organize them into logical groups:

**Without Groups (old way):**
```
Hot Americano Options:
  ○ Bold
  ○ Fruity  
  ○ Mild
  ○ Medium
  ○ Hot
  ○ Regular
  ○ Large
```

**With Groups (new way):**
```
☕ Coffee Taste (pick 1):
  ○ Bold (Free)
  ○ Fruity (Free)

🌶️ Spicy Level (pick 1):
  ○ Mild (Free)
  ○ Medium (+Rp 1.000)
  ○ Hot (+Rp 2.000)

📏 Size (pick 1):
  ○ Regular (Free)
  ○ Large (+Rp 5.000)
```

### 🔄 How Condiment Groups Work:

**Key Concept:** Condiment Groups are **SHARED** across products!

- ✅ "Coffee Taste" group → Reused for ALL coffee products
- ✅ "Spicy Level" group → Reused for ALL products that need spicy options
- ✅ "Size" group → Reused for ALL products that have size variations
- ⚡ **Benefit**: Update once, applies to all linked products

**Example:**
```
Product 1: Hot Americano → Uses "Coffee Taste", "Spicy Level", "Size"
Product 2: Hot Cappuccino → Uses "Coffee Taste", "Sugar Level" 
Product 3: Ice Latte → Uses "Coffee Taste", "Ice Level", "Size"
```

All three products **share** the same "Coffee Taste" modifier group!

**If you update "Coffee Taste" options:**
- Add new option "Smooth" → Automatically available for Americano, Cappuccino, AND Ice Latte
- Change fee for "Bold" → Changes for ALL products using "Coffee Taste"

### Example Excel Data:

| Category | Menu Category | Nama Product  | PLU Product | Printer Kitchen | Condiment Group | Condiment      | PLU Condiment | Fee Condiment | Price Product |
|----------|---------------|---------------|-------------|-----------------|-----------------|----------------|---------------|---------------|---------------|
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Coffee Taste    | Bold           |               | 0             | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Coffee Taste    | Fruity         |               | 0             | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Spicy Level     | Mild           |               | 0             | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Spicy Level     | Medium         |               | 1000          | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Spicy Level     | Hot            |               | 2000          | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Size            | Regular        |               | 0             | 27000         |
| Beverage | Hot Coffee    | Hot Americano | 03835821    | bar             | Size            | Large          |               | 5000          | 27000         |
| Beverage | Hot Coffee    | Hot Cappuccino| 03835822    | bar             | Sugar Level     | No Sugar       |               | 0             | 33000         |
| Beverage | Hot Coffee    | Hot Cappuccino| 03835822    | bar             | Sugar Level     | Less Sugar     |               | 0             | 33000         |
| Beverage | Hot Coffee    | Hot Cappuccino| 03835822    | bar             | Milk Upgrade    | Regular Milk   |               | 0             | 33000         |
| Beverage | Hot Coffee    | Hot Cappuccino| 03835822    | bar             | Milk Upgrade    | Oat Milk       | 101           | 8000          | 33000         |
| Food     | Nasi Goreng   | Nasi Special  | 12345       | kitchen         | Spicy Level     | No Chili       |               | 0             | 35000         |
| Food     | Nasi Goreng   | Nasi Special  | 12345       | kitchen         | Extra Topping   | Telur          | 201           | 5000          | 35000         |

### Common Condiment Groups:
- **Coffee Taste**: Bold, Fruity, Smooth, Classic
- **Spicy Level**: No Chili, Mild, Medium, Hot, Extra Hot
- **Size**: Small, Regular, Large, Extra Large
- **Sugar Level**: No Sugar, Less Sugar, Normal, Extra Sweet
- **Ice Level**: No Ice, Less Ice, Normal, Extra Ice
- **Milk Upgrade**: Regular, Oat Milk, Almond Milk, Soy Milk
- **Temperature**: Hot, Warm, Cold, Iced
- **Add-ons**: Extra Shot, Whipped Cream, Caramel Drizzle, Chocolate Syrup

## Import Process
1. Click **"Download Template"** button to get the correct Excel format
2. Fill in your product data following the examples
3. Go to http://127.0.0.1:8000/management/master-data/
4. Click "Import Excel" button
5. Upload your Excel file
6. Select import options:
   - ✅ **Skip duplicates** - Skip products with existing PLU codes
   - **Update existing** - Update existing products with new data
   - ✅ **Create modifiers** - Create modifiers from Condiment columns
7. Click "Import Data"
8. **After import**: Copy your product image files to `media/products/` directory
   - System will map paths automatically
   - Example: `avril/images/menus/product.jpg` → `media/products/product.jpg`

## Notes
- One row = One product OR One product with one condiment option
- Same product (PLU + Name) can have multiple rows for different condiment groups
- Same Condiment Group for one product = same modifier with multiple options
- **Same Condiment Group NAME = SHARED modifier across ALL products** ⭐
  - Example: "Coffee Taste" used by Americano and Cappuccino → Both use SAME modifier
  - Benefit: Update "Coffee Taste" once → Changes apply to ALL products using it
- Leave Condiment Group empty if product has no modifiers
- Zero fee modifiers are allowed (free options like "No Sugar", "No Chili")
- **Backward Compatible**: Old Excel format (without Condiment Group) still works

## 🎯 Best Practices for Condiment Groups

### Use Consistent Names:
✅ **GOOD** - Same name for similar concepts:
- All coffee products use "Coffee Taste" (not "Coffee Flavor", "Taste Profile", etc.)
- All food products use "Spicy Level" (not "Pedas Level", "Sambal", etc.)
- All beverages use "Size" (not "Ukuran", "Portion", etc.)

❌ **BAD** - Inconsistent names:
- Americano uses "Coffee Taste"
- Cappuccino uses "Coffee Flavor" ← Different name = Different modifier!

### Smart Grouping Strategy:
```
Universal Groups (many products):
  - Size → For all beverages
  - Spicy Level → For all food items
  - Temperature → Hot/Cold options
  - Ice Level → For cold beverages

Category-Specific Groups:
  - Coffee Taste → Only coffee products
  - Tea Flavor → Only tea products
  - Sugar Level → Sweetened beverages

Product-Specific Groups:
  - Milk Upgrade → Only dairy-based drinks
  - Extra Topping → Only food/rice/noodles
```

## 🖨️ Printer Kitchen Feature

**Purpose**: Route orders to correct printer based on product type

**Available Options:**
- **kitchen** - Food items (Nasi Goreng, Mie Goreng, Steak, Main courses)
- **bar** - Beverages (Coffee, Juice, Smoothies, Cocktails)
- **dessert** - Desserts (Cake, Ice Cream, Pudding)
- **none** - Items that don't need kitchen printing (retail products, merchandise)

**Benefits:**
- ✅ Automatic order routing to correct station
- ✅ Bar staff only see beverage orders
- ✅ Kitchen staff only see food orders
- ✅ Dessert station only see dessert orders
- ✅ Reduces confusion and improves workflow
- ✅ Faster order fulfillment

**Example:**
```
Hot Americano (Printer Kitchen: bar)
└─ Order prints at Bar Station

Nasi Goreng Special (Printer Kitchen: kitchen)
└─ Order prints at Main Kitchen

Chocolate Ice Cream (Printer Kitchen: dessert)
└─ Order prints at Dessert Station
```

## Test Files
- **Old format**: `test_products.xlsx` - Still compatible (backward compatible)
- **With Condiment Groups**: `test_products_with_groups.xlsx` - Demonstrates modifier grouping
- **Shared groups demo**: `test_shared_groups.xlsx` - Shows how groups are reused ⭐
- **With Printer Kitchen**: `test_products_with_printers.xlsx` - Demonstrates printer routing (bar/kitchen/dessert) 🆕

# LOGIN SYSTEM
URL Login: http://127.0.0.1:8000/login/
**URL yang SAMA untuk semua user** (Admin, Manager, POS Staff)

Sistem akan otomatis redirect berdasarkan role user:

## Login Admin/Manager
http://127.0.0.1:8000/login/
username : manager
pass     : manager123
→ Auto redirect ke: http://127.0.0.1:8000/management/dashboard/

## Login POS Staff (Cashier/Waiter/Kitchen)
http://127.0.0.1:8000/login/
username : [username cashier/waiter]
pass     : [password]
→ Auto redirect ke: http://127.0.0.1:8000/pos/

## Login dengan PIN (Alternative)
http://127.0.0.1:8000/pin-login/
→ Quick login untuk staff dengan PIN 


---

# FAQ - FREQUENTLY ASKED QUESTIONS

## Q: Do I have to use two-file system?
**A**: No, backward compatible. Old inline format still works, but new format recommended for easier maintenance.

## Q: Can I mix old and new format?
**A**: Not recommended. Choose one approach:
- New: Import groups once, reference in products
- Old: Everything inline in single product file

## Q: What if I make typo in group name in products file?
**A**: Import will fail with error message: "Group 'Coffe Taste' not found. Import groups first!"
Fix typo and re-upload.

## Q: Can one product use multiple groups?
**A**: Yes! Use comma-separated: `Coffee Taste,Size,Ice Level,Sugar Level` 
Product can have as many modifier groups as needed.

## Q: How to update existing group options?
**A**: 
1. Edit condiment_groups.xlsx (add/modify options)
2. Enable "Update Existing Groups" checkbox
3. Upload → Options updated for ALL products using that group

## Q: Can different products share same group?
**A**: YES! That's the main benefit!
Example: "Size" group shared by ALL beverage products.
Update "Size" once → All beverages updated.

## Q: What is Max Selections used for?
**A**: Controls how many options customer can choose:
- Max Selections = 1: Radio buttons (choose one)
- Max Selections = 3: Checkboxes (choose up to 3)
- Max Selections = 999: Choose unlimited

Example:
- Size (Max=1): Choose only Regular OR Large
- Extra Topping (Max=3): Choose up to 3 toppings

## Q: What is Is Required used for?
**A**: Forces customer to make selection:
- Is Required = Yes: Customer MUST choose (Size is required)
- Is Required = No: Customer can skip (Sugar Level optional)

## Q: Can I have free and paid options in same group?
**A**: YES! Example:
```
Group: Milk Upgrade
- Regular Milk: Fee = 0 (free)
- Oat Milk: Fee = 8000 (paid +8000)
- Almond Milk: Fee = 10000 (paid +10000)
```

## Q: What happens if I import products without importing groups first?
**A**: Import fails with error: "Condiment group '[name]' not found. Import groups first!"
You MUST import groups before products.

## Q: Can I export current groups to Excel?
**A**: Not automated yet. Workaround:
1. Go to admin panel: `/admin/pos/modifier/`
2. View existing groups
3. Manually create Excel matching template format

## Q: How to delete all groups and start fresh?
**A**: Admin panel → Modifiers → Select all → Delete
Or use Django shell:
```python
from apps.pos.models import Modifier
Modifier.objects.all().delete()
```

## Q: What's the file size limit for Excel?
**A**: No hard limit, but recommend:
- Condiment groups: < 1000 options
- Products: < 5000 rows
- Larger files may take longer to process

---

# ADVANCED USAGE

## Multi-Outlet Setup

**Scenario**: Different outlets, different modifier options

### Option 1: Separate Files per Outlet
```
outlet_A_condiment_groups.xlsx → Upload for Outlet A
outlet_B_condiment_groups.xlsx → Upload for Outlet B
```

### Option 2: Shared Groups
```
common_groups.xlsx → Upload for ALL outlets
- Size (Regular, Large) → Same for all
- Sugar Level → Same for all
```

## Complex Modifier Examples

### Example 1: Coffee Shop
**Groups:**
- Coffee Taste (Max=1, Required=No): Bold, Fruity, Smooth
- Size (Max=1, Required=Yes): Regular (+0), Large (+5000)
- Sugar Level (Max=1, Required=No): No Sugar, Normal, Extra Sweet
- Milk Upgrade (Max=1, Required=No): Regular (+0), Oat (+8000), Almond (+10000)
- Ice Level (Max=1, Required=No): No Ice, Less Ice, Regular Ice

**Products:**
- Hot Americano: `Coffee Taste,Size,Sugar Level`
- Ice Latte: `Coffee Taste,Size,Ice Level,Milk Upgrade`
- Cold Brew: `Size,Ice Level,Milk Upgrade`

### Example 2: Restaurant
**Groups:**
- Spicy Level (Max=1, Required=No): No Chili, Medium (+1000), Hot (+2000)
- Rice Portion (Max=1, Required=Yes): Small (-2000), Regular, Large (+3000)
- Extra Topping (Max=5, Required=No): 
  - Telur Mata Sapi (+5000)
  - Ayam Suwir (+12000)
  - Kerupuk (+2000)
  - Sambal Matah (+3000)
  - Acar (+2000)
- Cooking Method (Max=1, Required=No): Goreng, Bakar (+2000), Rebus

**Products:**
- Nasi Goreng: `Spicy Level,Rice Portion,Extra Topping`
- Ayam Geprek: `Spicy Level,Rice Portion,Extra Topping,Cooking Method`
- Sate Ayam: `Spicy Level,Extra Topping`

### Example 3: Bakery
**Groups:**
- Cake Size (Max=1, Required=Yes): Slice, Half Cake (+50000), Full Cake (+95000)
- Toppings (Max=3, Required=No): Strawberry (+5000), Blueberry (+7000), Chocolate Chips (+4000)
- Candles (Max=1, Required=No): No Candles, Number Candles (+10000), Message Candles (+15000)

**Products:**
- Chocolate Cake: `Cake Size,Toppings,Candles`
- Red Velvet: `Cake Size,Toppings,Candles`
- Cheesecake: `Cake Size,Toppings`

---

# KEYBOARD SHORTCUTS & TIPS

## Excel Tips:
- **Ctrl + D**: Fill down (copy cell to cells below)
- **Alt + Enter**: New line within cell
- **Ctrl + Home**: Go to A1 (start)
- **F2**: Edit cell

## Bulk Editing:
1. Sort by Group Name
2. Select all rows for one group
3. Ctrl + D to fill down Is Required, Max Selections

## Template Customization:
- Add more example rows for your use case
- Color-code groups (green=beverage, yellow=food)
- Add notes column for internal reference (won't be imported)

---

# NEXT STEPS

After successful import:

1. **Test in POS System**
   - Add products to cart
   - Verify modifiers appear
   - Check prices calculated correctly

2. **Train Staff**
   - Show how modifiers work
   - Explain required vs optional
   - Practice taking orders with modifiers

3. **Print Kitchen Orders**
   - Verify modifiers print on kitchen tickets
   - Check printer routing works (kitchen/bar/dessert)

4. **Monitor & Adjust**
   - Watch for customer feedback
   - Adjust fees if needed
   - Add/remove options based on demand

5. **Regular Maintenance**
   - Update seasonal options
   - Add limited-time modifiers
   - Remove discontinued options

---

# SUPPORT

## Need Help?

**Common Issues**: Check Troubleshooting section above

**Bug Reports**: GitHub Issues (if applicable)

**Feature Requests**: Submit via project repository

**Documentation**: This file + inline comments in code

---

**Last Updated**: 2025  
**Version**: 3.0 (Two-File System)  
**Compatibility**: Django 6.0+, Python 3.10+
