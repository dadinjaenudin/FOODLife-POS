# 📋 Setup & Sync API Flow Documentation

## Endpoint: `/setup/` - Setup & Sync All Data

Ketika user mengklik tombol **"🚀 Setup & Sync All Data"** di halaman `/setup/`, berikut adalah flow lengkapnya:

---

## 🔄 API Call Flow

### 1️⃣ **Form Submission**
- **Endpoint**: `POST /setup/store/`
- **Handler**: `apps.core.views_setup.setup_store_config_multi_brand()`
- **Data yang dikirim**:
  ```json
  {
    "company_id": "uuid-company",
    "ho_store_id": "uuid-store-dari-ho"
  }
  ```

---

## 📡 API Calls ke HO Server

### 2️⃣ **Authentication - Get JWT Token**
**Request:**
```http
POST {HO_API_URL}/api/token/
Content-Type: application/json

{
  "username": "admin",  // dari settings.HO_API_USERNAME
  "password": "admin123" // dari settings.HO_API_PASSWORD
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Fungsi**: Mendapatkan access token untuk autentikasi API berikutnya.

---

### 3️⃣ **Fetch Company Data**
**Request:**
```http
GET {HO_API_URL}/api/sync/companies/
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "companies": [
    {
      "id": "uuid-company",
      "code": "COMP001",
      "name": "PT Food Corp",
      "timezone": "Asia/Jakarta",
      "is_active": true,
      "point_expiry_months": 12,
      "points_per_currency": 1.00
    }
  ],
  "total": 1
}
```

**Fungsi**: Mendapatkan detail company dan membuat/update di Edge Server database melalui `sync_company_from_ho()`.

---

### 4️⃣ **Fetch Store Data from HO**
**Request:**
```http
GET {HO_API_URL}/api/v1/core/stores/
Authorization: Bearer {access_token}
Query Params: company_id={company_id}
```

**Response:**
```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid-store",
      "store_code": "FC001",
      "store_name": "Food Court Mall X",
      "brand_id": "uuid-brand",
      "address": "Jl. Mall X No.1",
      "phone": "021-12345678",
      "timezone": "Asia/Jakarta"
    }
  ]
}
```

**Fungsi**: Mendapatkan detail store dari HO Server, termasuk `brand_id` yang akan di-sync.

---

### 5️⃣ **Fetch & Sync Brand Data**
**Request:**
```http
GET {HO_API_URL}/api/sync/brands/
Authorization: Bearer {access_token}
Query Params: brand_id={brand_id}
```

**Response:**
```json
{
  "brands": [
    {
      "id": "uuid-brand",
      "company_id": "uuid-company",
      "code": "BRAND001",
      "name": "Burger House",
      "address": "Head Office Address",
      "phone": "021-87654321",
      "tax_id": "01.234.567.8-901.000",
      "tax_rate": 11.00,
      "service_charge": 5.00,
      "is_active": true
    }
  ]
}
```

**Fungsi**: Mendapatkan detail brand dan sync ke Edge Server melalui `sync_brand_from_ho()`.

---

### 6️⃣ **Create Edge Store & Link Brand**

**Local Database Operations:**

1. **Create Store** di Edge Server:
   ```python
   Store.objects.create(
       company=company,
       store_code="FC001",
       store_name="Food Court Mall X",
       address="...",
       phone="...",
       timezone="Asia/Jakarta",
       is_active=True
   )
   ```

2. **Link Brand to Store** via `StoreBrand`:
   ```python
   StoreBrand.objects.create(
       store=edge_store,
       brand=brand,
       ho_store_id="uuid-store-dari-ho",
       is_active=True
   )
   ```

---

### 7️⃣ **Sync Master Data (Bulk Sync)**

**Fungsi**: `sync_helpers.sync_master_data_from_ho(company_id, access_token)`

Melakukan sync semua master data dari HO:

#### A. **Sync Categories**
```http
GET {HO_API_URL}/api/sync/categories/
Authorization: Bearer {access_token}
Query Params: company_id={company_id}
```

**Response:**
```json
{
  "categories": [
    {
      "id": "uuid-cat",
      "brand_id": "uuid-brand",
      "name": "Burgers",
      "code": "BURGER",
      "description": "All burger items",
      "sort_order": 1,
      "is_active": true
    }
  ]
}
```

#### B. **Sync Products**
```http
GET {HO_API_URL}/api/sync/products/
Authorization: Bearer {access_token}
Query Params: company_id={company_id}
```

**Response:**
```json
{
  "products": [
    {
      "id": "uuid-product",
      "brand_id": "uuid-brand",
      "category_id": "uuid-cat",
      "sku": "BRG001",
      "name": "Cheese Burger",
      "description": "Classic cheese burger",
      "price": 45000.00,
      "cost": 20000.00,
      "image_url": "https://...",
      "is_active": true,
      "stock_quantity": 100
    }
  ]
}
```

#### C. **Sync Modifiers (Condiment Groups & Items)**
```http
GET {HO_API_URL}/api/sync/modifiers/
Authorization: Bearer {access_token}
Query Params: company_id={company_id}
```

**Response:**
```json
{
  "modifier_groups": [
    {
      "id": "uuid-group",
      "brand_id": "uuid-brand",
      "name": "Extra Toppings",
      "min_selection": 0,
      "max_selection": 5,
      "is_required": false
    }
  ],
  "modifier_items": [
    {
      "id": "uuid-item",
      "group_id": "uuid-group",
      "name": "Extra Cheese",
      "price": 5000.00,
      "is_active": true
    }
  ]
}
```

#### D. **Sync Table Areas (Optional)**
```http
GET {HO_API_URL}/api/sync/table-areas/
Authorization: Bearer {access_token}
Query Params: brand_id={brand_id}
```

#### E. **Sync Kitchen Stations (Optional)**
```http
GET {HO_API_URL}/api/sync/kitchen-stations/
Authorization: Bearer {access_token}
Query Params: brand_id={brand_id}
```

---

## ✅ Success Response

Setelah semua sync berhasil, user akan melihat:

```
✅ Edge Server Setup Complete!

Company: PT Food Corp (COMP001)
Store: Food Court Mall X (FC001)

Synced Data:
- Categories: 15
- Products: 120
- Modifiers: 45
```

Dan redirect ke `/setup/` (setup status page).

---

## 🔧 Configuration Required

Di `pos_fnb/settings.py`, pastikan ada:

```python
# HO API Configuration
HO_API_URL = 'http://localhost:8002'  # atau URL HO Server
HO_API_USERNAME = 'admin'
HO_API_PASSWORD = 'admin123'
```

---

## 📂 Files Involved

1. **Template**: `templates/core/setup_store.html`
2. **View**: `apps/core/views_setup.py::setup_store_config_multi_brand()`
3. **Sync Helpers**: `apps/core/sync_helpers.py`
   - `sync_company_from_ho()`
   - `sync_brand_from_ho()`
   - `sync_master_data_from_ho()`
4. **Models**: `apps/core/models.py`
   - `Company`, `Brand`, `Store`, `StoreBrand`
   - `Category`, `Product`, `Modifier`

---

## 🎯 Summary

**Total API Calls ke HO Server:**
1. ✅ POST `/api/token/` - Authentication
2. ✅ GET `/api/sync/companies/` - Fetch company
3. ✅ GET `/api/v1/core/stores/` - Fetch store
4. ✅ GET `/api/sync/brands/` - Fetch brand (jika belum ada)
5. ✅ GET `/api/sync/categories/` - Sync categories
6. ✅ GET `/api/sync/products/` - Sync products
7. ✅ GET `/api/sync/modifiers/` - Sync modifiers
8. ✅ GET `/api/sync/table-areas/` (optional)
9. ✅ GET `/api/sync/kitchen-stations/` (optional)

**Data yang Di-sync ke Edge Server:**
- ✅ Company
- ✅ Brand(s)
- ✅ Store (local Edge store)
- ✅ StoreBrand (junction table)
- ✅ Categories (per brand)
- ✅ Products (per brand)
- ✅ Modifiers/Condiments (per brand)
- ✅ Table Areas (optional)
- ✅ Kitchen Stations (optional)
