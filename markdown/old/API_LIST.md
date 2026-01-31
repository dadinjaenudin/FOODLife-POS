PROMOTION

curl -X GET
"http://localhost:8002/api/sync/promotions/?company_id=xxx&brand_id=yyy" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Modifiers API

curl -X POST http://localhost:8002/api/sync/modifiers/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "your-company-uuid",
    "brand_id": "your-brand-uuid"
  }'
```

TABLES
curl -X POST http://localhost:8002/api/sync/tables/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id": "xxx", "brand_id": "yyy"}'




 Ringkasan API Calls:

Ketika tombol diklik, sistem melakukan 7-9 API calls ke HO Server:

 1. Authentication:
 • POST /api/token/ - Get JWT access token

 2. Fetch Master Data:
 • GET /api/sync/companies/ - Fetch company details
 • GET /api/v1/core/stores/ - Fetch store from HO
 • GET /api/sync/brands/ - Fetch brand details

3. Bulk Sync Master Data:

 • GET /api/sync/categories/ - Sync all categories
 • GET /api/sync/products/ - Sync all products
 • GET /api/sync/modifiers/ - Sync all modifiers/condiments
 • GET /api/sync/table-areas/ - (Optional) Table layouts
 • GET /api/sync/kitchen-stations/ - (Optional) Kitchen config


 
 GET /api/v1/core/companies/
✅ GET /api/v1/core/companies/sync/?last_sync={iso}
✅ GET /api/v1/core/brands/
✅ GET /api/v1/core/brands/sync/?brand_id={uuid}
✅ GET /api/v1/core/stores/
✅ GET /api/v1/core/stores/sync/?store_id={uuid}
✅ GET /api/v1/core/users/
✅ GET /api/v1/core/users/sync/?brand_id={uuid}
```

# Filter by company_id
GET /api/v1/core/stores/?company_id=<uuid>
# Filter by brand_id
GET /api/v1/core/stores/?brand_id=<uuid>
# Filter by store_id
GET /api/v1/core/stores/?store_id=<uuid>
# Sync endpoint
GET /api/v1/core/stores/sync/?company_id=<uuid>&last_sync=2024-01-27T10:00:00Z
```


1. API Sync Endpoints - Semua sudah support company_id + store_id:


  Endpoint                                 Required Params        Optional Params                          Status    
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  /api/v1/products/categories/sync/        company_id             store_id, brand_id, last_sync            ✅ Tested
  /api/v1/products/products/sync/          company_id             store_id, brand_id, category_id,         ✅ Tested
                                                                  last_sync
  /api/v1/products/modifiers/sync/         company_id             store_id, brand_id, last_sync            ✅ Tested
  /api/v1/products/kitchen-stations/syn…   company_id, store_id   -                                        ✅ Tested
  /api/v1/products/table-areas/sync/       company_id, store_id   brand_id                                 ✅ Tested
  /api/v1/products/tables/sync/            company_id, store_id   brand_id                                 ✅ Tested


URL: GET http://localhost:8002/api/sync/promotions/

                                              Required Query Parameters:
```
✅ store_id (required) - UUID of the store
✅ company_id (required) - UUID of the company
```
          Optional Query Parameters:

```
- brand_id (optional) - UUID of the brand
- updated_since (optional) - ISO datetime for incremental sync

                                        🏗️ Arsitektur Food Court yang Didukung:

```
Edge (Food Court)
├── 1 Company (Yogya Group)
├── 1 Store (Avril Store)
└── Multiple Brands (Tenant A, B, C...)
    ├── Products per Brand
    ├── Categories per Brand
    └── Modifiers per Brand
```

                                             📡 Contoh Request dari Edge:

```bash
# Get JWT Token
POST /api/token/
{
  "username": "edge_user",
  "password": "password"
}

# Sync all products from all brands in the store
GET /api/v1/products/products/sync/
?company_id=812e76b6-f235-4bb2-948a-cae58ee62b97
&store_id=ee90b1f6-2ec2-4b46-8b4a-79d208b3c04c

# Response:
{
  "count": 143,
  "last_sync": "2026-01-27T14:34:11",
  "company_id": "812e76b6-f235-4bb2-948a-cae58ee62b97",
  "store_id": "ee90b1f6-2ec2-4b46-8b4a-79d208b3c04c",
  "data": [...]
}
```