"""
HO API Client - Handles all communication with Head Office Server

This client provides a clean interface for interacting with the HO Server API,
including authentication, request handling, and error management.
"""

import requests
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from django.conf import settings

from .exceptions import (
    HOAPIConnectionError,
    HOAPIAuthenticationError,
    HOAPINotFoundError,
    HOAPIValidationError,
    HOAPITimeoutError,
)

logger = logging.getLogger(__name__)


class HOAPIClient:
    """
    Client for interacting with HO (Head Office) Server API
    
    Usage:
        client = HOAPIClient()
        companies = client.get_companies()
        stores = client.get_stores(company_id='uuid-here')
    """
    
    def __init__(self, base_url: Optional[str] = None, username: Optional[str] = None, 
                 password: Optional[str] = None, timeout: int = 10):
        """
        Initialize HO API Client
        
        Args:
            base_url: HO Server base URL (defaults to settings.HO_API_URL)
            username: HO API username (defaults to settings.HO_API_USERNAME)
            password: HO API password (defaults to settings.HO_API_PASSWORD)
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url or getattr(settings, 'HO_API_URL', None)
        self.username = username or getattr(settings, 'HO_API_USERNAME', 'admin')
        self.password = password or getattr(settings, 'HO_API_PASSWORD', 'admin123')
        self.timeout = timeout
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        
        if not self.base_url:
            raise HOAPIConnectionError("HO_API_URL not configured in settings")
    
    def _get_request_id(self) -> str:
        """Generate unique request ID for logging"""
        return uuid.uuid4().hex[:10]
    
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get JWT access token from HO Server
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            JWT access token
            
        Raises:
            HOAPIAuthenticationError: If authentication fails
            HOAPIConnectionError: If connection fails
        """
        # Check if we have a valid cached token
        if not force_refresh and self._access_token and self._token_expires_at:
            if time.time() < self._token_expires_at:
                return self._access_token
        
        req_id = self._get_request_id()
        token_url = f"{self.base_url}/api/v1/token/"
        
        logger.info("[HO API][%s] Requesting access token from %s", req_id, token_url)
        
        try:
            response = requests.post(
                token_url,
                json={'username': self.username, 'password': self.password},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access')
            
            if not access_token:
                logger.error("[HO API][%s] Token response missing 'access' field", req_id)
                raise HOAPIAuthenticationError("Token response missing 'access' field")
            
            # Cache token (assume 24 hour expiry, refresh 1 hour before)
            self._access_token = access_token
            self._token_expires_at = time.time() + (23 * 3600)  # 23 hours
            
            logger.info("[HO API][%s] Access token obtained successfully", req_id)
            return access_token
            
        except requests.exceptions.Timeout:
            logger.error("[HO API][%s] Token request timeout", req_id)
            raise HOAPITimeoutError(f"Token request timeout after {self.timeout}s")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("[HO API][%s] Authentication failed: Invalid credentials", req_id)
                raise HOAPIAuthenticationError("Invalid credentials")
            logger.error("[HO API][%s] HTTP error during authentication: %s", req_id, str(e))
            raise HOAPIConnectionError(f"HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error("[HO API][%s] Connection error during authentication: %s", req_id, str(e))
            raise HOAPIConnectionError(f"Connection error: {str(e)}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to HO API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/v1/sync/companies/')
            **kwargs: Additional arguments for requests (json, params, etc.)
            
        Returns:
            Response JSON data
            
        Raises:
            HOAPIException: Various API exceptions
        """
        req_id = self._get_request_id()
        url = f"{self.base_url}{endpoint}"
        started = time.time()
        
        # Get access token
        access_token = self._get_access_token()
        
        # Add authorization header
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        
        logger.info("[HO API][%s] %s %s", req_id, method, url)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            elapsed_ms = int((time.time() - started) * 1000)
            
            # Handle different status codes
            if response.status_code == 401:
                # Token might be expired, try refreshing once
                logger.warning("[HO API][%s] 401 Unauthorized, refreshing token", req_id)
                access_token = self._get_access_token(force_refresh=True)
                headers['Authorization'] = f'Bearer {access_token}'
                
                # Retry request with new token
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(
                "[HO API][%s] Request successful status=%s elapsed_ms=%s",
                req_id, response.status_code, elapsed_ms
            )
            
            return data
            
        except requests.exceptions.Timeout:
            elapsed_ms = int((time.time() - started) * 1000)
            logger.error("[HO API][%s] Request timeout after %sms", req_id, elapsed_ms)
            raise HOAPITimeoutError(f"Request timeout after {self.timeout}s")
        except requests.exceptions.HTTPError as e:
            elapsed_ms = int((time.time() - started) * 1000)
            status_code = e.response.status_code if e.response else None
            
            if status_code == 404:
                logger.error("[HO API][%s] Resource not found (404) after %sms", req_id, elapsed_ms)
                raise HOAPINotFoundError("Resource not found")
            elif status_code == 400:
                error_detail = e.response.json() if e.response else {}
                logger.error("[HO API][%s] Validation error (400) after %sms: %s", 
                           req_id, elapsed_ms, error_detail)
                raise HOAPIValidationError(f"Validation error: {error_detail}")
            else:
                logger.error("[HO API][%s] HTTP error %s after %sms: %s", 
                           req_id, status_code, elapsed_ms, str(e))
                raise HOAPIConnectionError(f"HTTP error {status_code}: {str(e)}")
        except requests.exceptions.RequestException as e:
            elapsed_ms = int((time.time() - started) * 1000)
            logger.error("[HO API][%s] Request error after %sms: %s", req_id, elapsed_ms, str(e))
            raise HOAPIConnectionError(f"Request error: {str(e)}")
    
    # ========== Sync API Endpoints ==========
    
    def get_companies(self) -> List[Dict[str, Any]]:
        """
        Fetch all companies from HO Server
        
        Endpoint: POST /api/v1/sync/companies/
        
        Returns:
            List of company dictionaries with fields:
            - id (uuid)
            - code (str)
            - name (str)
            - timezone (str)
            - is_active (bool)
            - point_expiry_months (int)
            - points_per_currency (decimal)
        """
        logger.info("[HO API] Fetching companies")
        
        data = self._make_request('POST', '/api/v1/sync/companies/')
        
        # Handle different response formats
        # Format 1: {"companies": [...], "total": N}
        # Format 2: {"results": [...], "count": N}
        companies = data.get('companies') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s companies", len(companies))
        return companies
    
    def get_stores(self, company_id: Optional[str] = None, 
                   brand_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch stores from HO Server
        
        Endpoint: POST /api/v1/sync/stores/
        
        Args:
            company_id: Filter by company ID (optional)
            brand_id: Filter by brand ID (optional)
            
        Returns:
            List of store dictionaries with fields:
            - id (uuid)
            - store_code (str)
            - store_name (str)
            - address (str)
            - phone (str)
            - brand_id (uuid)
            - timezone (str)
            - is_active (bool)
        """
        logger.info("[HO API] Fetching stores company_id=%s brand_id=%s", 
                   company_id, brand_id)
        
        payload = {}
        if company_id:
            payload['company_id'] = company_id
        if brand_id:
            payload['brand_id'] = brand_id
        
        data = self._make_request('POST', '/api/v1/sync/stores/', json=payload)
        
        # Handle different response formats
        stores = data.get('stores') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s stores", len(stores))
        return stores
    
    def get_store_brands(self, company_id: str, store_id: str) -> List[Dict[str, Any]]:
        """
        Fetch store-brand relationships from HO Server
        Supports multiple brands per store
        
        Endpoint: POST /api/v1/sync/store-brands/
        
        Args:
            company_id: Company ID
            store_id: Store ID
            
        Returns:
            List of store-brand relationship dictionaries with brand details
        """
        logger.info("[HO API] Fetching store-brands for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {
            'company_id': company_id,
            'store_id': store_id
        }
        
        data = self._make_request('POST', '/api/v1/sync/store-brands/', json=payload)
        
        store_brands = data.get('store_brands') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s store-brand relationships", len(store_brands))
        return store_brands
    
    def get_brands(self, company_id: Optional[str] = None, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch brands from HO Server
        
        Endpoint: POST /api/v1/sync/brands/
        
        Args:
            company_id: Filter by company ID (optional)
            store_id: Filter by store ID (optional)
            
        Returns:
            List of brand dictionaries
        """
        logger.info("[HO API] Fetching brands company_id=%s store_id=%s", company_id, store_id)
        
        payload = {}
        if company_id:
            payload['company_id'] = company_id
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request('POST', '/api/v1/sync/brands/', json=payload)
        
        brands = data.get('brands') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s brands", len(brands))
        return brands
    
    def get_categories(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch categories from HO Server
        
        Endpoint: POST /api/v1/sync/categories/
        
        Args:
            company_id: Company ID to fetch categories for
            store_id: Store ID to fetch categories for (optional)
            
        Returns:
            List of category dictionaries
        """
        logger.info("[HO API] Fetching categories for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request(
            'POST', 
            '/api/v1/sync/categories/',
            json=payload
        )
        
        categories = data.get('categories') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s categories", len(categories))
        return categories
    
    def get_products(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch products from HO Server
        
        Endpoint: POST /api/v1/sync/products/
        
        Args:
            company_id: Company ID to fetch products for
            store_id: Store ID to fetch products for (optional)
            
        Returns:
            List of product dictionaries
        """
        logger.info("[HO API] Fetching products for company_id=%s store_id=%s", 
                   company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request(
            'POST',
            '/api/v1/sync/products/',
            json=payload
        )
        
        products = data.get('products') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s products", len(products))
        return products
    
    def get_modifiers(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch modifiers from HO Server
        
        Endpoint: POST /api/v1/sync/modifiers/
        
        Args:
            company_id: Company ID to fetch modifiers for
            store_id: Store ID to fetch modifiers for (optional)
            
        Returns:
            List of modifier dictionaries
        """
        logger.info("[HO API] Fetching modifiers for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request(
            'POST',
            '/api/v1/sync/modifiers/',
            json=payload
        )
        
        modifiers = data.get('modifiers') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s modifiers", len(modifiers))
        return modifiers
    
    def get_modifier_options(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch modifier options from HO Server
        
        Endpoint: POST /api/v1/sync/modifier-options/
        
        Args:
            company_id: Company ID to fetch modifier options for
            store_id: Store ID to fetch modifier options for (optional)
            
        Returns:
            List of modifier option dictionaries
        """
        logger.info("[HO API] Fetching modifier options for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request(
            'POST',
            '/api/v1/sync/modifier-options/',
            json=payload
        )
        
        modifier_options = data.get('modifier_options') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s modifier options", len(modifier_options))
        return modifier_options
    
    def get_product_modifiers(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch product-modifier relationships from HO Server
        
        Endpoint: POST /api/v1/sync/product-modifiers/
        
        Args:
            company_id: Company ID to fetch product-modifiers for
            store_id: Store ID to fetch product-modifiers for (optional)
            
        Returns:
            List of product-modifier relationship dictionaries
        """
        logger.info("[HO API] Fetching product-modifiers for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request(
            'POST',
            '/api/v1/sync/product-modifiers/',
            json=payload
        )
        
        product_modifiers = data.get('product_modifiers') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s product-modifier relationships", len(product_modifiers))
        return product_modifiers
    
    def get_table_areas(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch table areas from HO Server"""
        logger.info("[HO API] Fetching table areas for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request('POST', '/api/v1/sync/table-areas/', json=payload)
        table_areas = data.get('table_areas') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s table areas", len(table_areas))
        return table_areas
    
    def get_tables(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch tables from HO Server"""
        logger.info("[HO API] Fetching tables for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request('POST', '/api/v1/sync/tables/', json=payload)
        tables = data.get('tables') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s tables", len(tables))
        return tables
    
    def get_table_groups(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch table groups from HO Server"""
        logger.info("[HO API] Fetching table groups for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request('POST', '/api/v1/sync/table-groups/', json=payload)
        table_groups = data.get('table_groups') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s table groups", len(table_groups))
        return table_groups
    
    def get_promotions(self, company_id: str, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch compiled promotions from HO Server"""
        logger.info("[HO API] Fetching promotions for company_id=%s store_id=%s", company_id, store_id)
        
        payload = {'company_id': company_id}
        if store_id:
            payload['store_id'] = store_id
        
        data = self._make_request('POST', '/api/v1/sync/promotions/', json=payload)
        promotions = data.get('promotions') or data.get('results', [])
        
        logger.info("[HO API] Fetched %s promotions", len(promotions))
        return promotions
    
    # ========== Health Check ==========
    
    def health_check(self) -> bool:
        """
        Check if HO Server is accessible
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            self._get_access_token()
            return True
        except Exception as e:
            logger.error("[HO API] Health check failed: %s", str(e))
            return False
