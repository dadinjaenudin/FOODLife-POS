# HO API Integration Module

Module ini menangani semua komunikasi dengan HO (Head Office) Server API.

## 📁 Struktur

```
apps/core/ho_api/
├── __init__.py          # Module exports
├── client.py            # HOAPIClient - Main API client
├── exceptions.py        # Custom exceptions
└── README.md           # Dokumentasi ini
```

## 🚀 Quick Start

### Basic Usage

```python
from apps.core.ho_api import HOAPIClient

# Initialize client (uses settings.HO_API_URL by default)
client = HOAPIClient()

# Fetch companies
companies = client.get_companies()
# Returns: [{'id': 'uuid', 'code': 'AVRIL', 'name': 'AVRIL COMPANY', ...}, ...]

# Fetch stores for a company
stores = client.get_stores(company_id='company-uuid-here')
# Returns: [{'id': 'uuid', 'store_code': 'BSD01', 'store_name': 'Yogya BSD', ...}, ...]

# Fetch brands
brands = client.get_brands(company_id='company-uuid-here')

# Fetch categories
categories = client.get_categories(company_id='company-uuid-here')

# Fetch products
products = client.get_products(company_id='company-uuid-here')

# Fetch modifiers
modifiers = client.get_modifiers(company_id='company-uuid-here')
```

### Error Handling

```python
from apps.core.ho_api import (
    HOAPIClient, 
    HOAPIException,
    HOAPIConnectionError,
    HOAPIAuthenticationError,
    HOAPINotFoundError,
    HOAPITimeoutError
)

try:
    client = HOAPIClient()
    companies = client.get_companies()
except HOAPIConnectionError as e:
    # HO Server tidak dapat dijangkau
    print(f"Connection error: {e}")
except HOAPIAuthenticationError as e:
    # Kredensial tidak valid
    print(f"Authentication failed: {e}")
except HOAPITimeoutError as e:
    # Request timeout
    print(f"Request timeout: {e}")
except HOAPIException as e:
    # Error umum lainnya
    print(f"API error: {e}")
```

## 🔧 Configuration

Client menggunakan konfigurasi dari Django settings:

```python
# settings.py atau .env.edge
HO_API_URL = "http://host.docker.internal:8002"
HO_API_USERNAME = "admin"
HO_API_PASSWORD = "admin123"
```

### Custom Configuration

```python
# Override default configuration
client = HOAPIClient(
    base_url="http://custom-ho-server:8000",
    username="custom_user",
    password="custom_pass",
    timeout=15  # seconds
)
```

## 📡 API Endpoints

### 1. Get Companies

```python
companies = client.get_companies()
```

**Endpoint:** `POST /api/v1/sync/companies/`

**Returns:**
```python
[
    {
        'id': 'uuid',
        'code': 'AVRIL',
        'name': 'AVRIL COMPANY',
        'timezone': 'Asia/Jakarta',
        'is_active': True,
        'point_expiry_months': 12,
        'points_per_currency': 1.00
    },
    ...
]
```

### 2. Get Stores

```python
stores = client.get_stores(company_id='uuid', brand_id='uuid')
```

**Endpoint:** `POST /api/v1/sync/stores/`

**Parameters:**
- `company_id` (optional): Filter by company
- `brand_id` (optional): Filter by brand

**Returns:**
```python
[
    {
        'id': 'uuid',
        'store_code': 'BSD01',
        'store_name': 'Yogya BSD',
        'address': 'BSD City',
        'phone': '021-xxx',
        'brand_id': 'uuid',
        'timezone': 'Asia/Jakarta',
        'is_active': True
    },
    ...
]
```

### 3. Get Brands

```python
brands = client.get_brands(company_id='uuid')
```

**Endpoint:** `GET /api/v1/sync/brands/`

**Parameters:**
- `company_id` (optional): Filter by company

### 4. Get Categories

```python
categories = client.get_categories(company_id='uuid')
```

**Endpoint:** `POST /api/v1/sync/categories/`

**Parameters:**
- `company_id` (required): Company ID

### 5. Get Products

```python
products = client.get_products(company_id='uuid')
```

**Endpoint:** `POST /api/v1/sync/products/`

**Parameters:**
- `company_id` (required): Company ID

### 6. Get Modifiers

```python
modifiers = client.get_modifiers(company_id='uuid')
```

**Endpoint:** `POST /api/v1/sync/modifiers/`

**Parameters:**
- `company_id` (required): Company ID

### 7. Health Check

```python
is_healthy = client.health_check()
# Returns: True if HO Server is accessible, False otherwise
```

## 🔐 Authentication

Client secara otomatis menangani JWT authentication:

1. **Token Caching**: Access token di-cache dan di-reuse untuk multiple requests
2. **Auto Refresh**: Token otomatis di-refresh jika expired (401 response)
3. **Token Expiry**: Token di-cache selama 23 jam (refresh 1 jam sebelum expiry)

```python
# Authentication dilakukan otomatis
client = HOAPIClient()
companies = client.get_companies()  # Token obtained automatically

# Force token refresh
client._get_access_token(force_refresh=True)
```

## 📊 Logging

Client menggunakan Python logging untuk tracking:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('apps.core.ho_api.client')
```

**Log Format:**
```
[HO API][req_id] Message
```

**Example Logs:**
```
[HO API][a1b2c3d4e5] Requesting access token from http://ho-server:8002/api/v1/token/
[HO API][a1b2c3d4e5] Access token obtained successfully
[HO API][f6g7h8i9j0] POST http://ho-server:8002/api/v1/sync/companies/
[HO API][f6g7h8i9j0] Request successful status=200 elapsed_ms=245
[HO API] Fetched 2 companies
```

## 🎯 Use Cases

### 1. Setup Wizard (Fetch Companies & Stores)

```python
from apps.core.ho_api import HOAPIClient, HOAPIException

def fetch_companies_from_ho(request):
    try:
        client = HOAPIClient()
        companies = client.get_companies()
        
        return JsonResponse({
            'companies': companies,
            'total': len(companies),
            'success': True
        })
    except HOAPIException as e:
        # Return mock data on error
        return JsonResponse({
            'companies': [...],  # mock data
            'success': False,
            'error': str(e)
        })
```

### 2. Sync Master Data

```python
from apps.core.ho_api import HOAPIClient

def sync_master_data(company_id):
    client = HOAPIClient()
    
    # Fetch all master data
    categories = client.get_categories(company_id)
    products = client.get_products(company_id)
    modifiers = client.get_modifiers(company_id)
    
    # Save to local database
    for category in categories:
        Category.objects.update_or_create(
            id=category['id'],
            defaults={...}
        )
    
    return {
        'categories': len(categories),
        'products': len(products),
        'modifiers': len(modifiers)
    }
```

### 3. Health Check

```python
from apps.core.ho_api import HOAPIClient

def check_ho_connection():
    try:
        client = HOAPIClient()
        if client.health_check():
            return "HO Server is accessible"
        else:
            return "HO Server is not accessible"
    except Exception as e:
        return f"Error: {str(e)}"
```

## 🔄 Response Format Handling

Client secara otomatis menangani berbagai format response dari HO Server:

**Format 1 (Legacy):**
```json
{
    "companies": [...],
    "total": 10
}
```

**Format 2 (DRF Pagination):**
```json
{
    "results": [...],
    "count": 10,
    "next": null,
    "previous": null
}
```

Client menormalisasi kedua format menjadi list sederhana:
```python
companies = client.get_companies()
# Returns: [...]  (just the list)
```

## ⚠️ Error Handling

### Exception Hierarchy

```
HOAPIException (base)
├── HOAPIConnectionError      # Network/connection errors
├── HOAPIAuthenticationError  # Invalid credentials
├── HOAPINotFoundError        # 404 errors
├── HOAPIValidationError      # 400 validation errors
└── HOAPITimeoutError         # Request timeout
```

### Best Practices

```python
from apps.core.ho_api import HOAPIClient, HOAPIException

def safe_fetch_companies():
    try:
        client = HOAPIClient()
        return client.get_companies()
    except HOAPIException as e:
        # Log error
        logger.error(f"Failed to fetch companies: {e}")
        
        # Return fallback data
        return [
            {'id': 'mock-1', 'code': 'MOCK', 'name': 'Mock Company'}
        ]
```

## 🧪 Testing

### Mock HO Server

```python
# For testing without HO Server
from unittest.mock import patch

with patch('apps.core.ho_api.client.HOAPIClient.get_companies') as mock:
    mock.return_value = [
        {'id': 'test-1', 'code': 'TEST', 'name': 'Test Company'}
    ]
    
    client = HOAPIClient()
    companies = client.get_companies()
    assert len(companies) == 1
```

## 📝 Notes

1. **Thread Safety**: Client instance tidak thread-safe karena token caching. Gunakan instance baru per request.
2. **Timeout**: Default timeout 10 detik. Adjust sesuai kebutuhan network.
3. **Retry Logic**: Client tidak melakukan auto-retry. Implement di caller jika diperlukan.
4. **Rate Limiting**: Tidak ada built-in rate limiting. HO Server mungkin memiliki rate limits.

## 🔗 Related Documentation

- [DOCKER_ARCHITECTURE.md](../../../../DOCKER_ARCHITECTURE.md) - Docker setup
- [EDGE_SERVER_ARCHITECTURE.md](../../../../markdown/EDGE_SERVER_ARCHITECTURE.md) - Edge server architecture
- [SYNC_API_DOCUMENTATION.md](../../../../markdown/SYNC_API_DOCUMENTATION.md) - HO API endpoints

## 📞 Support

Untuk issues atau questions, hubungi development team.
