# HO API Client Implementation Summary

**Date:** 29 Januari 2026  
**Status:** ✅ Complete  
**Version:** 1.0

---

## 📋 Overview

Implementasi module khusus untuk integrasi dengan HO (Head Office) Server API. Module ini menyediakan interface yang clean dan terstruktur untuk komunikasi antara Edge Server dan HO Server.

## 🎯 Objectives

1. ✅ Membuat folder khusus `apps/core/ho_api/` untuk HO API integration
2. ✅ Implementasi `HOAPIClient` class dengan JWT authentication
3. ✅ Implementasi custom exceptions untuk error handling
4. ✅ Update views untuk menggunakan HOAPIClient
5. ✅ Dokumentasi lengkap

## 📁 File Structure

```
apps/core/ho_api/
├── __init__.py          # Module exports
├── client.py            # HOAPIClient - Main API client (450+ lines)
├── exceptions.py        # Custom exceptions (30 lines)
└── README.md           # Comprehensive documentation (400+ lines)
```

## 🔧 Implementation Details

### 1. HOAPIClient Class (`client.py`)

**Features:**
- ✅ JWT authentication dengan token caching
- ✅ Auto token refresh pada 401 response
- ✅ Request/response logging dengan unique request ID
- ✅ Error handling dengan custom exceptions
- ✅ Support multiple response formats (DRF pagination, legacy format)
- ✅ Configurable timeout (default 10s)

**Methods:**
```python
class HOAPIClient:
    # Authentication
    def _get_access_token(force_refresh=False) -> str
    def _make_request(method, endpoint, **kwargs) -> Dict
    
    # Sync API Endpoints
    def get_companies() -> List[Dict]
    def get_stores(company_id=None, brand_id=None) -> List[Dict]
    def get_brands(company_id=None) -> List[Dict]
    def get_categories(company_id) -> List[Dict]
    def get_products(company_id) -> List[Dict]
    def get_modifiers(company_id) -> List[Dict]
    
    # Health Check
    def health_check() -> bool
```

**Key Features:**

1. **Token Caching:**
   ```python
   # Token cached for 23 hours
   self._access_token = access_token
   self._token_expires_at = time.time() + (23 * 3600)
   ```

2. **Auto Retry on 401:**
   ```python
   if response.status_code == 401:
       # Token expired, refresh and retry
       access_token = self._get_access_token(force_refresh=True)
       # Retry request with new token
   ```

3. **Request Logging:**
   ```python
   req_id = uuid.uuid4().hex[:10]
   logger.info("[HO API][%s] POST %s", req_id, url)
   logger.info("[HO API][%s] Request successful elapsed_ms=%s", req_id, elapsed_ms)
   ```

### 2. Custom Exceptions (`exceptions.py`)

```python
HOAPIException (base)
├── HOAPIConnectionError      # Network/connection errors
├── HOAPIAuthenticationError  # Invalid credentials (401)
├── HOAPINotFoundError        # Resource not found (404)
├── HOAPIValidationError      # Validation errors (400)
└── HOAPITimeoutError         # Request timeout
```

### 3. Updated Views (`views_setup.py`)

**Before:**
```python
# Manual requests with token handling
token_response = requests.post(f"{ho_api_url}/api/v1/token/", ...)
access_token = token_response.json().get('access')
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.post(f"{ho_api_url}/api/v1/sync/companies/", headers=headers)
```

**After:**
```python
# Clean API client usage
from apps.core.ho_api import HOAPIClient, HOAPIException

try:
    client = HOAPIClient()
    companies = client.get_companies()
    return JsonResponse({'companies': companies, 'success': True})
except HOAPIException as e:
    return JsonResponse({'error': str(e), 'success': False})
```

**Updated Functions:**
- ✅ `fetch_companies_from_ho()` - Uses `client.get_companies()`
- ✅ `fetch_brands_from_ho()` - Uses `client.get_brands()`
- ✅ `fetch_stores_from_ho()` - Uses `client.get_stores()`

## 🔗 API Endpoints Mapping

| Method | Endpoint | HO Server Endpoint |
|--------|----------|-------------------|
| `get_companies()` | Edge: `/api/ho/companies/` | HO: `POST /api/v1/sync/companies/` |
| `get_stores()` | Edge: `/api/ho/stores/` | HO: `POST /api/v1/sync/stores/` |
| `get_brands()` | Edge: `/api/ho/brands/` | HO: `GET /api/v1/sync/brands/` |
| `get_categories()` | - | HO: `POST /api/v1/sync/categories/` |
| `get_products()` | - | HO: `POST /api/v1/sync/products/` |
| `get_modifiers()` | - | HO: `POST /api/v1/sync/modifiers/` |

## 📊 Configuration

### Environment Variables (.env.edge)

```bash
# HO Server Configuration
HO_API_URL=http://host.docker.internal:8002
HO_API_USERNAME=admin
HO_API_PASSWORD=admin123
```

### Django Settings (settings.py)

```python
# HO Server Sync Settings (for Edge Server)
HO_API_URL = os.environ.get('HO_API_URL', None)
HO_API_USERNAME = os.environ.get('HO_API_USERNAME', 'admin')
HO_API_PASSWORD = os.environ.get('HO_API_PASSWORD', 'admin123')
```

## 🚀 Usage Examples

### 1. Fetch Companies (Setup Wizard)

```python
from apps.core.ho_api import HOAPIClient, HOAPIException

@csrf_exempt
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
        logger.error("Error fetching companies: %s", str(e))
        # Return mock data as fallback
        return JsonResponse({
            'companies': [{'id': 'mock', 'name': 'Mock Company'}],
            'success': False
        })
```

### 2. Fetch Stores by Company

```python
client = HOAPIClient()
stores = client.get_stores(company_id='company-uuid-here')

for store in stores:
    print(f"{store['store_code']}: {store['store_name']}")
```

### 3. Health Check

```python
client = HOAPIClient()
if client.health_check():
    print("✅ HO Server is accessible")
else:
    print("❌ HO Server is not accessible")
```

## 🔍 Testing

### Manual Testing

1. **Start HO Server:**
   ```bash
   cd D:\YOGYA-Kiosk\FoodBeverages-CMS\FoodBeverages-CMS
   docker-compose up -d
   ```

2. **Start Edge Server:**
   ```bash
   cd D:\YOGYA-Kiosk\pos-django-htmx-main
   docker-compose up -d
   ```

3. **Test Endpoint:**
   ```bash
   # Open browser
   http://localhost:8001/setup/
   
   # Check dropdown - should load companies from HO Server
   # Check browser console for API calls
   # Check Edge Server logs: docker-compose logs edge_web -f
   ```

### Python Shell Testing

```python
# Enter Django shell
python manage.py shell

# Test HOAPIClient
from apps.core.ho_api import HOAPIClient

client = HOAPIClient()

# Test companies
companies = client.get_companies()
print(f"Found {len(companies)} companies")

# Test stores
stores = client.get_stores(company_id=companies[0]['id'])
print(f"Found {len(stores)} stores")

# Test health check
print(f"Health: {client.health_check()}")
```

## 📝 Logging Output

**Example Log Output:**
```
[HO API][a1b2c3d4e5] Requesting access token from http://host.docker.internal:8002/api/v1/token/
[HO API][a1b2c3d4e5] Access token obtained successfully
[HO API][f6g7h8i9j0] POST http://host.docker.internal:8002/api/v1/sync/companies/
[HO API][f6g7h8i9j0] Request successful status=200 elapsed_ms=245
[HO API] Fetched 2 companies
```

## ✅ Benefits

### Before Implementation:
- ❌ Duplicate code untuk authentication di setiap view
- ❌ Manual token management
- ❌ Inconsistent error handling
- ❌ Sulit untuk testing dan maintenance
- ❌ No request logging

### After Implementation:
- ✅ Single source of truth untuk HO API integration
- ✅ Automatic token caching dan refresh
- ✅ Consistent error handling dengan custom exceptions
- ✅ Easy to test dan mock
- ✅ Comprehensive logging dengan request ID
- ✅ Clean dan maintainable code

## 🔄 Migration Path

### Old Code:
```python
# 50+ lines of boilerplate code
ho_api_url = getattr(settings, 'HO_API_URL', None)
username = getattr(settings, 'HO_API_USERNAME', 'admin')
password = getattr(settings, 'HO_API_PASSWORD', 'admin123')

token_response = requests.post(f"{ho_api_url}/api/v1/token/", ...)
access_token = token_response.json().get('access')
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.post(f"{ho_api_url}/api/v1/sync/companies/", headers=headers)
# ... error handling ...
```

### New Code:
```python
# 5 lines of clean code
from apps.core.ho_api import HOAPIClient, HOAPIException

try:
    client = HOAPIClient()
    companies = client.get_companies()
except HOAPIException as e:
    # handle error
```

**Code Reduction:** ~90% less boilerplate code

## 📚 Documentation

### Created Files:
1. ✅ `apps/core/ho_api/README.md` - Comprehensive module documentation (400+ lines)
2. ✅ `HO_API_CLIENT_IMPLEMENTATION.md` - This implementation summary

### Documentation Includes:
- Quick start guide
- API reference
- Configuration guide
- Error handling examples
- Use cases
- Testing guide
- Best practices

## 🎯 Next Steps

### Recommended Enhancements:

1. **Retry Logic:**
   ```python
   # Add automatic retry for transient errors
   @retry(max_attempts=3, backoff=2)
   def _make_request(self, method, endpoint, **kwargs):
       ...
   ```

2. **Rate Limiting:**
   ```python
   # Add rate limiting to prevent overwhelming HO Server
   from ratelimit import limits
   
   @limits(calls=10, period=60)  # 10 calls per minute
   def get_companies(self):
       ...
   ```

3. **Async Support:**
   ```python
   # Add async methods for better performance
   async def get_companies_async(self):
       ...
   ```

4. **Caching:**
   ```python
   # Add Redis caching for frequently accessed data
   @cache_result(ttl=300)  # Cache for 5 minutes
   def get_companies(self):
       ...
   ```

5. **Metrics:**
   ```python
   # Add metrics collection
   from prometheus_client import Counter, Histogram
   
   api_requests = Counter('ho_api_requests_total', 'Total HO API requests')
   api_latency = Histogram('ho_api_latency_seconds', 'HO API latency')
   ```

## 🔗 Related Files

### Modified Files:
- `apps/core/views_setup.py` - Updated to use HOAPIClient

### New Files:
- `apps/core/ho_api/__init__.py`
- `apps/core/ho_api/client.py`
- `apps/core/ho_api/exceptions.py`
- `apps/core/ho_api/README.md`
- `HO_API_CLIENT_IMPLEMENTATION.md`

### Related Documentation:
- `DOCKER_ARCHITECTURE.md` - Docker setup
- `markdown/EDGE_SERVER_ARCHITECTURE.md` - Edge server architecture
- `markdown/SYNC_API_DOCUMENTATION.md` - HO API endpoints

## 📞 Support

Untuk testing atau issues:
1. Check logs: `docker-compose logs edge_web -f`
2. Check HO Server: `http://localhost:8002/admin/`
3. Check Edge Server: `http://localhost:8001/setup/`

---

**Implementation Complete! ✅**

Module HO API Client sudah siap digunakan untuk integrasi dengan HO Server. Semua endpoint sudah terimplementasi dengan clean interface, proper error handling, dan comprehensive logging.
