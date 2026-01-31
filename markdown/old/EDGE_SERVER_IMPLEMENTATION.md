# Edge Server Implementation Guide
## Promotion System Integration for Edge/Store Server

**Version:** 1.0  
**Date:** 2026-01-27  
**Target:** Django + PostgreSQL + HTMX Edge Server  
**Purpose:** Complete implementation guide for store-level servers

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [Django Models](#django-models)
4. [Sync Implementation](#sync-implementation)
5. [Promotion Evaluation](#promotion-evaluation)
6. [API Endpoints](#api-endpoints)
7. [HTMX Integration](#htmx-integration)
8. [Testing & Validation](#testing-and-validation)
9. [Deployment Guide](#deployment-guide)

---

## 🏗️ Architecture Overview

### System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    HEAD OFFICE (HO)                          │
│              Django + PostgreSQL (Central)                   │
│                                                              │
│  • Master data management                                   │
│  • Promotion creation & compilation                         │
│  • Analytics & reporting                                    │
│  • Central database                                         │
│                                                              │
│  APIs:                                                      │
│  ├─ GET /api/sync/categories/                              │
│  ├─ GET /api/sync/products/                                │
│  ├─ GET /api/sync/modifiers/                               │
│  ├─ GET /api/sync/tables/                                  │
│  └─ GET /api/sync/promotions/  (with embedded data)        │
└─────────────────┬────────────────────────────────────────────┘
                  │
                  │ HTTPS/VPN (Sync API)
                  │ Frequency: Daily/On-demand
                  ▼
┌──────────────────────────────────────────────────────────────┐
│              EDGE SERVER (Store Level)                       │
│         Django + HTMX + PostgreSQL (Local)                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 PostgreSQL Database (Local):                            │
│  ├─ categories          - Master data                       │
│  ├─ products            - Master data                       │
│  ├─ modifiers           - Master data                       │
│  ├─ tables              - Store tables                      │
│  ├─ promotions          - WITH embedded data (JSONB)        │
│  ├─ transactions        - Local transactions                │
│  └─ promotion_logs      - Usage tracking                    │
│                                                              │
│  🌐 Django Application:                                     │
│  ├─ Sync management commands                                │
│  ├─ Promotion evaluation engine                             │
│  ├─ HTMX views for POS UI                                   │
│  └─ Offline capability                                      │
│                                                              │
│  Features:                                                  │
│  ✅ Works offline after sync                                │
│  ✅ Fast evaluation (embedded data, no JOIN)                │
│  ✅ Support multiple POS terminals                          │
│  ✅ Auto-sync on schedule                                   │
└─────────────────┬────────────────────────────────────────────┘
                  │
                  │ Local Network (LAN)
                  │ Fast response time
                  ▼
┌──────────────────────────────────────────────────────────────┐
│                    POS TERMINALS                             │
│              Browser-based or Native App                     │
│                                                              │
│  • Connect to Edge Server via LAN                           │
│  • HTMX for dynamic UI updates                              │
│  • Real-time promotion calculation                          │
│  • Fast response (<100ms)                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

### 1. Promotions Table (Core)

```sql
-- promotions/migrations/0001_initial.py
-- Table for storing promotions with embedded data

CREATE TABLE promotions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identifiers
    company_id UUID NOT NULL,
    brand_id UUID,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    terms_conditions TEXT,
    
    -- Type & Configuration
    promo_type VARCHAR(50) NOT NULL,
    apply_to VARCHAR(50) NOT NULL,
    execution_stage VARCHAR(50) DEFAULT 'item_level',
    execution_priority INTEGER DEFAULT 500,
    
    -- Status Flags
    is_active BOOLEAN DEFAULT TRUE,
    is_auto_apply BOOLEAN DEFAULT TRUE,
    require_voucher BOOLEAN DEFAULT FALSE,
    member_only BOOLEAN DEFAULT FALSE,
    is_stackable BOOLEAN DEFAULT TRUE,
    
    -- Validity Period
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    valid_time_start TIME,
    valid_time_end TIME,
    valid_days INTEGER[],
    exclude_holidays BOOLEAN DEFAULT FALSE,
    
    -- ⭐ EMBEDDED DATA (JSONB) - All data needed for evaluation
    compiled_data JSONB NOT NULL,
    
    -- Sync Metadata
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_from_ho BOOLEAN DEFAULT TRUE,
    sync_version INTEGER DEFAULT 1,
    ho_promotion_id UUID,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT promotions_dates_check CHECK (start_date <= end_date),
    CONSTRAINT promotions_code_unique UNIQUE (code)
);

-- Indexes for Performance
CREATE INDEX idx_promotions_active ON promotions(is_active) 
    WHERE is_active = TRUE;

CREATE INDEX idx_promotions_dates ON promotions(start_date, end_date) 
    WHERE is_active = TRUE;

CREATE INDEX idx_promotions_company ON promotions(company_id);
CREATE INDEX idx_promotions_brand ON promotions(brand_id);
CREATE INDEX idx_promotions_type ON promotions(promo_type);

-- ⭐ GIN Index for JSONB queries (CRITICAL for performance!)
CREATE INDEX idx_promotions_compiled_data ON promotions 
    USING GIN (compiled_data);

-- Additional JSONB indexes for common queries
CREATE INDEX idx_promotions_scope_categories ON promotions 
    USING GIN ((compiled_data->'scope'->'categories'));

CREATE INDEX idx_promotions_scope_products ON promotions 
    USING GIN ((compiled_data->'scope'->'products'));

-- Comments
COMMENT ON TABLE promotions IS 'Promotions with embedded data for offline evaluation';
COMMENT ON COLUMN promotions.compiled_data IS 'Full promotion data with embedded product/category info for fast evaluation without JOINs';
```

### Example compiled_data structure:

```json
{
  "validity": {
    "start_date": "2026-02-01",
    "end_date": "2026-02-28",
    "days_of_week": [6, 7]
  },
  "scope": {
    "apply_to": "category",
    "categories": [
      {
        "id": "cat-uuid-1",
        "company_id": "comp-uuid",
        "brand_id": "brand-uuid",
        "name": "Beverages",
        "code": "BEV"
      }
    ],
    "products": [],
    "exclude_categories": [],
    "exclude_products": [
      {
        "id": "prod-uuid-5",
        "company_id": "comp-uuid",
        "brand_id": "brand-uuid",
        "name": "Premium Blend",
        "sku": "BEV-005",
        "price": 50000.0
      }
    ]
  },
  "targeting": {
    "stores": ["store-uuid-1", "store-uuid-2"],
    "brands": ["brand-uuid"],
    "company_id": "comp-uuid",
    "member_only": false,
    "customer_type": "all",
    "sales_channels": ["dine_in", "takeaway"]
  },
  "rules": {
    "type": "percent",
    "discount_percent": 20.0,
    "max_discount_amount": 50000.0,
    "min_purchase": 100000.0
  },
  "limits": {
    "max_uses": null,
    "max_uses_per_customer": 1,
    "max_uses_per_day": null,
    "current_uses": 0
  },
  "cross_brand": null,
  "compiled_at": "2026-01-27T10:00:00+07:00",
  "compiler_version": "1.0"
}
```

---

### 2. Master Data Tables

```sql
-- Categories
CREATE TABLE categories (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    brand_id UUID,
    store_id UUID,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    parent_id UUID REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    image_url TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT categories_company_code_unique UNIQUE (company_id, code)
);

CREATE INDEX idx_categories_company ON categories(company_id);
CREATE INDEX idx_categories_brand ON categories(brand_id);
CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_active ON categories(is_active) WHERE is_active = TRUE;

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    brand_id UUID NOT NULL,
    store_id UUID,
    category_id UUID REFERENCES categories(id),
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    has_modifiers BOOLEAN DEFAULT FALSE,
    image_url TEXT,
    description TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT products_company_sku_unique UNIQUE (company_id, sku)
);

CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_active ON products(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_products_sku ON products(sku);

-- Modifiers
CREATE TABLE modifiers (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    brand_id UUID,
    store_id UUID,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    price DECIMAL(10,2) DEFAULT 0,
    is_required BOOLEAN DEFAULT FALSE,
    min_selection INTEGER DEFAULT 0,
    max_selection INTEGER DEFAULT 1,
    options JSONB,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_modifiers_company ON modifiers(company_id);
CREATE INDEX idx_modifiers_brand ON modifiers(brand_id);

-- Tables/Areas
CREATE TABLE tables (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    brand_id UUID,
    store_id UUID NOT NULL,
    area_id UUID,
    area_name VARCHAR(100),
    table_number VARCHAR(50) NOT NULL,
    capacity INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    qr_code TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT tables_store_number_unique UNIQUE (store_id, table_number)
);

CREATE INDEX idx_tables_store ON tables(store_id);
CREATE INDEX idx_tables_area ON tables(area_id);
CREATE INDEX idx_tables_active ON tables(is_active) WHERE is_active = TRUE;
```

---

### 3. Operational Tables

```sql
-- Promotion Usage Logs
CREATE TABLE promotion_logs (
    id SERIAL PRIMARY KEY,
    promotion_id UUID REFERENCES promotions(id),
    transaction_id UUID,
    bill_id VARCHAR(100),
    
    -- Result
    status VARCHAR(50) NOT NULL, -- 'applied', 'skipped', 'failed'
    reason TEXT,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    
    -- Context
    original_amount DECIMAL(10,2),
    final_amount DECIMAL(10,2),
    cart_data JSONB,
    
    -- Customer
    customer_id UUID,
    customer_phone VARCHAR(20),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_to_ho BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMP
);

CREATE INDEX idx_promotion_logs_promotion ON promotion_logs(promotion_id);
CREATE INDEX idx_promotion_logs_transaction ON promotion_logs(transaction_id);
CREATE INDEX idx_promotion_logs_status ON promotion_logs(status);
CREATE INDEX idx_promotion_logs_sync ON promotion_logs(synced_to_ho) 
    WHERE synced_to_ho = FALSE;

-- Sync Status Tracking
CREATE TABLE sync_status (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'promotions', 'products', etc.
    last_sync_at TIMESTAMP,
    last_sync_version INTEGER,
    sync_status VARCHAR(50), -- 'success', 'failed', 'in_progress'
    sync_message TEXT,
    records_synced INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT sync_status_entity_unique UNIQUE (entity_type)
);
```

---

## 🐍 Django Models

### promotions/models.py

```python
"""
Edge Server Promotion Models
Store promotions with embedded data for offline evaluation
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
import uuid


class Promotion(models.Model):
    """
    Promotion model with embedded data from HO
    
    The compiled_data JSONB field contains all necessary information
    for promotion evaluation without requiring JOINs to other tables.
    """
    
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identifiers
    company_id = models.UUIDField(db_index=True)
    brand_id = models.UUIDField(null=True, blank=True, db_index=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    # Type & Configuration
    PROMO_TYPE_CHOICES = [
        ('percent_discount', 'Percent Discount'),
        ('amount_discount', 'Amount Discount'),
        ('buy_x_get_y', 'Buy X Get Y'),
        ('combo', 'Combo Deal'),
        ('free_item', 'Free Item'),
        ('happy_hour', 'Happy Hour'),
        ('cashback', 'Cashback'),
        ('payment_discount', 'Payment Discount'),
        ('package', 'Package/Set Menu'),
        ('mix_match', 'Mix & Match'),
        ('upsell', 'Upsell/Add-on'),
        ('threshold_tier', 'Threshold/Tiered'),
    ]
    promo_type = models.CharField(max_length=50, choices=PROMO_TYPE_CHOICES, db_index=True)
    
    APPLY_TO_CHOICES = [
        ('all', 'All Products'),
        ('category', 'Specific Categories'),
        ('product', 'Specific Products'),
    ]
    apply_to = models.CharField(max_length=50, choices=APPLY_TO_CHOICES)
    
    execution_stage = models.CharField(max_length=50, default='item_level')
    execution_priority = models.IntegerField(default=500)
    
    # Status Flags
    is_active = models.BooleanField(default=True, db_index=True)
    is_auto_apply = models.BooleanField(default=True)
    require_voucher = models.BooleanField(default=False)
    member_only = models.BooleanField(default=False)
    is_stackable = models.BooleanField(default=True)
    
    # Validity Period
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    valid_time_start = models.TimeField(null=True, blank=True)
    valid_time_end = models.TimeField(null=True, blank=True)
    valid_days = ArrayField(
        models.IntegerField(),
        null=True,
        blank=True,
        help_text="Days of week: 1=Mon, 2=Tue, ..., 7=Sun"
    )
    exclude_holidays = models.BooleanField(default=False)
    
    # ⭐ EMBEDDED DATA (JSONB)
    compiled_data = models.JSONField(
        help_text="Full promotion data with embedded product/category info"
    )
    
    # Sync Metadata
    last_synced_at = models.DateTimeField(auto_now=True)
    synced_from_ho = models.BooleanField(default=True)
    sync_version = models.IntegerField(default=1)
    ho_promotion_id = models.UUIDField(null=True, blank=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'promotions'
        ordering = ['-execution_priority', 'name']
        indexes = [
            models.Index(fields=['is_active'], name='idx_promo_active'),
            models.Index(fields=['start_date', 'end_date'], name='idx_promo_dates'),
            models.Index(fields=['company_id'], name='idx_promo_company'),
            models.Index(fields=['brand_id'], name='idx_promo_brand'),
            models.Index(fields=['promo_type'], name='idx_promo_type'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_rules(self):
        """Extract rules from compiled_data"""
        return self.compiled_data.get('rules', {})
    
    def get_scope(self):
        """Extract scope from compiled_data"""
        return self.compiled_data.get('scope', {})
    
    def get_targeting(self):
        """Extract targeting from compiled_data"""
        return self.compiled_data.get('targeting', {})
    
    def get_limits(self):
        """Extract limits from compiled_data"""
        return self.compiled_data.get('limits', {})
    
    def is_valid_now(self):
        """
        Check if promotion is currently valid
        
        Checks:
        - Active status
        - Date range
        - Time range (if specified)
        - Day of week (if specified)
        """
        now = timezone.now()
        
        # Check active
        if not self.is_active:
            return False
        
        # Check dates
        if not (self.start_date <= now.date() <= self.end_date):
            return False
        
        # Check time
        if self.valid_time_start and self.valid_time_end:
            current_time = now.time()
            if not (self.valid_time_start <= current_time <= self.valid_time_end):
                return False
        
        # Check day of week
        if self.valid_days:
            if now.isoweekday() not in self.valid_days:
                return False
        
        return True
    
    def is_applicable_to_store(self, store_id):
        """Check if promotion applies to given store"""
        targeting = self.get_targeting()
        stores = targeting.get('stores', [])
        
        if stores == 'all':
            return True
        
        return str(store_id) in stores
    
    @classmethod
    def get_active_promotions(cls, store_id=None):
        """
        Get all active and valid promotions
        
        Args:
            store_id: Optional store UUID to filter by
            
        Returns:
            QuerySet of active promotions
        """
        now = timezone.now()
        
        queryset = cls.objects.filter(
            is_active=True,
            start_date__lte=now.date(),
            end_date__gte=now.date()
        )
        
        if store_id:
            # Filter by store using JSONB query
            queryset = queryset.filter(
                models.Q(compiled_data__targeting__stores='all') |
                models.Q(compiled_data__targeting__stores__contains=[str(store_id)])
            )
        
        return queryset.order_by('-execution_priority')


class PromotionLog(models.Model):
    """
    Log of promotion evaluations and usage
    Used for analytics and sync back to HO
    """
    
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    transaction_id = models.UUIDField(null=True, blank=True)
    bill_id = models.CharField(max_length=100, blank=True)
    
    # Result
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Context
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    cart_data = models.JSONField(null=True, blank=True)
    
    # Customer
    customer_id = models.UUIDField(null=True, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    synced_to_ho = models.BooleanField(default=False, db_index=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'promotion_logs'
        indexes = [
            models.Index(fields=['promotion'], name='idx_plog_promo'),
            models.Index(fields=['transaction_id'], name='idx_plog_trans'),
            models.Index(fields=['status'], name='idx_plog_status'),
            models.Index(fields=['synced_to_ho'], name='idx_plog_sync'),
        ]
    
    def __str__(self):
        return f"{self.promotion.code} - {self.status} - {self.discount_amount}"


class SyncStatus(models.Model):
    """
    Track sync status for each entity type
    """
    
    ENTITY_TYPE_CHOICES = [
        ('promotions', 'Promotions'),
        ('products', 'Products'),
        ('categories', 'Categories'),
        ('modifiers', 'Modifiers'),
        ('tables', 'Tables'),
    ]
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, unique=True)
    
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_version = models.IntegerField(default=0)
    
    SYNC_STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
    ]
    sync_status = models.CharField(max_length=50, choices=SYNC_STATUS_CHOICES, default='success')
    sync_message = models.TextField(blank=True)
    records_synced = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sync_status'
        verbose_name_plural = 'Sync statuses'
    
    def __str__(self):
        return f"{self.entity_type} - {self.sync_status}"
```

---

### Configuration (settings.py)

```python
# settings.py - Edge Server Configuration

# Edge Server Settings
EDGE_SERVER_CONFIG = {
    # Head Office API
    'HO_API_URL': env('HO_API_URL', default='https://ho.example.com'),
    'HO_API_TOKEN': env('HO_API_TOKEN', default=''),
    
    # Store Identity
    'STORE_ID': env('STORE_ID', default=''),
    'STORE_CODE': env('STORE_CODE', default=''),
    'COMPANY_ID': env('COMPANY_ID', default=''),
    'BRAND_ID': env('BRAND_ID', default=''),
    
    # Sync Configuration
    'AUTO_SYNC_ENABLED': env.bool('AUTO_SYNC_ENABLED', default=True),
    'SYNC_INTERVAL_HOURS': env.int('SYNC_INTERVAL_HOURS', default=6),
    'SYNC_ON_STARTUP': env.bool('SYNC_ON_STARTUP', default=True),
    
    # Performance
    'PROMOTION_CACHE_TIMEOUT': 3600,  # 1 hour
    'MAX_PROMOTIONS_PER_EVALUATION': 50,
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='edge_pos'),
        'USER': env('DB_USER', default='postgres'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/edge_server.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'sync_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/sync.log',
            'maxBytes': 10485760,
            'backupCount': 5,
        },
    },
    'loggers': {
        'promotions.sync': {
            'handlers': ['sync_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'promotions.evaluation': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

---

## 🔄 Sync Implementation

I'll continue with the sync implementation, management commands, evaluation engine, and complete HTMX integration in the next sections. Should I continue creating the complete documentation?

This is just the first part covering:
- Architecture
- Database Schema
- Django Models
- Configuration

The remaining sections will cover:
- Sync Management Commands
- Promotion Evaluation Engine
- API Endpoints
- HTMX Integration
- Testing & Deployment

**Should I continue with the rest of the documentation?** 🚀

## ?? Sync Implementation

### Management Command: sync_from_ho

**File:** `promotions/management/commands/sync_from_ho.py`

```python
"""
Sync data from Head Office to Edge Server

Usage:
    python manage.py sync_from_ho
    python manage.py sync_from_ho --type promotions
    python manage.py sync_from_ho --full
    python manage.py sync_from_ho --force
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import requests
import logging

from promotions.models import Promotion, SyncStatus
from products.models import Product, Category
from products.models import Modifier
from core.models import TableArea

logger = logging.getLogger('promotions.sync')


class Command(BaseCommand):
    help = 'Sync data from Head Office'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['promotions', 'products', 'categories', 'modifiers', 'tables', 'all'],
            default='all',
            help='Type of data to sync'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Full sync (ignore last sync time)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if recent sync exists'
        )
    
    def handle(self, *args, **options):
        sync_type = options['type']
        is_full = options['full']
        is_force = options['force']
        
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('   EDGE SERVER SYNC FROM HEAD OFFICE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('')
        
        # Check configuration
        if not self._check_configuration():
            return
        
        # Check if recent sync exists (unless force)
        if not is_force and not self._should_sync():
            self.stdout.write(self.style.WARNING('Recent sync exists. Use --force to override.'))
            return
        
        try:
            # Sync based on type
            if sync_type == 'all':
                self._sync_all(is_full)
            else:
                self._sync_entity(sync_type, is_full)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('? Sync completed successfully!'))
            
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'? Sync failed: {str(e)}'))
            logger.error(f'Sync failed: {str(e)}', exc_info=True)
    
    def _check_configuration(self):
        """Check if Edge server is properly configured"""
        config = settings.EDGE_SERVER_CONFIG
        
        if not config.get('HO_API_URL'):
            self.stdout.write(self.style.ERROR('? HO_API_URL not configured'))
            return False
        
        if not config.get('HO_API_TOKEN'):
            self.stdout.write(self.style.ERROR('? HO_API_TOKEN not configured'))
            return False
        
        if not config.get('STORE_ID'):
            self.stdout.write(self.style.ERROR('? STORE_ID not configured'))
            return False
        
        self.stdout.write(self.style.SUCCESS(f'? Configuration OK'))
        self.stdout.write(f'   HO URL: {config["HO_API_URL"]}')
        self.stdout.write(f'   Store ID: {config["STORE_ID"]}')
        self.stdout.write('')
        
        return True
    
    def _should_sync(self):
        """Check if sync should proceed based on last sync time"""
        config = settings.EDGE_SERVER_CONFIG
        interval_hours = config.get('SYNC_INTERVAL_HOURS', 6)
        
        # Get most recent sync
        recent_sync = SyncStatus.objects.filter(
            sync_status='success'
        ).order_by('-last_sync_at').first()
        
        if not recent_sync:
            return True
        
        if not recent_sync.last_sync_at:
            return True
        
        time_since_sync = timezone.now() - recent_sync.last_sync_at
        hours_since_sync = time_since_sync.total_seconds() / 3600
        
        if hours_since_sync < interval_hours:
            self.stdout.write(
                f'Last sync was {hours_since_sync:.1f} hours ago '
                f'(interval: {interval_hours} hours)'
            )
            return False
        
        return True
    
    def _sync_all(self, is_full):
        """Sync all entity types"""
        self.stdout.write(self.style.WARNING('Syncing all data types...'))
        self.stdout.write('')
        
        # Order matters: categories before products, products before promotions
        self._sync_entity('categories', is_full)
        self._sync_entity('products', is_full)
        self._sync_entity('modifiers', is_full)
        self._sync_entity('tables', is_full)
        self._sync_entity('promotions', is_full)
    
    def _sync_entity(self, entity_type, is_full):
        """Sync specific entity type"""
        self.stdout.write(f'?? Syncing {entity_type}...')
        
        # Update sync status to in_progress
        sync_status, created = SyncStatus.objects.get_or_create(
            entity_type=entity_type,
            defaults={'sync_status': 'in_progress'}
        )
        
        if not created:
            sync_status.sync_status = 'in_progress'
            sync_status.save()
        
        try:
            # Call appropriate sync method
            sync_methods = {
                'promotions': self._sync_promotions,
                'products': self._sync_products,
                'categories': self._sync_categories,
                'modifiers': self._sync_modifiers,
                'tables': self._sync_tables,
            }
            
            sync_method = sync_methods.get(entity_type)
            if not sync_method:
                raise ValueError(f'Unknown entity type: {entity_type}')
            
            count = sync_method(is_full, sync_status)
            
            # Update sync status to success
            sync_status.sync_status = 'success'
            sync_status.sync_message = f'Successfully synced {count} records'
            sync_status.records_synced = count
            sync_status.last_sync_at = timezone.now()
            sync_status.save()
            
            self.stdout.write(self.style.SUCCESS(f'   ? Synced {count} {entity_type}'))
            logger.info(f'Synced {count} {entity_type}')
            
        except Exception as e:
            # Update sync status to failed
            sync_status.sync_status = 'failed'
            sync_status.sync_message = str(e)
            sync_status.save()
            
            self.stdout.write(self.style.ERROR(f'   ? Failed: {str(e)}'))
            logger.error(f'Failed to sync {entity_type}: {str(e)}', exc_info=True)
            raise
    
    @transaction.atomic
    def _sync_promotions(self, is_full, sync_status):
        """Sync promotions from HO"""
        config = settings.EDGE_SERVER_CONFIG
        
        # Prepare request
        url = f"{config['HO_API_URL']}/api/sync/promotions/"
        headers = {'Authorization': f"Token {config['HO_API_TOKEN']}"}
        params = {
            'store_id': config['STORE_ID'],
            'company_id': config['COMPANY_ID'],
            'brand_id': config.get('BRAND_ID'),
        }
        
        # Add incremental sync parameter
        if not is_full and sync_status.last_sync_at:
            params['updated_since'] = sync_status.last_sync_at.isoformat()
        
        # Make request
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Process promotions
        count = 0
        for promo_data in data.get('promotions', []):
            Promotion.objects.update_or_create(
                id=promo_data['id'],
                defaults={
                    'company_id': promo_data['company_id'],
                    'brand_id': promo_data.get('brand_id'),
                    'code': promo_data['code'],
                    'name': promo_data['name'],
                    'description': promo_data.get('description', ''),
                    'terms_conditions': promo_data.get('terms_conditions', ''),
                    'promo_type': promo_data['promo_type'],
                    'apply_to': promo_data['apply_to'],
                    'execution_stage': promo_data.get('execution_stage', 'item_level'),
                    'execution_priority': promo_data.get('execution_priority', 500),
                    'is_active': promo_data['is_active'],
                    'is_auto_apply': promo_data.get('is_auto_apply', True),
                    'require_voucher': promo_data.get('require_voucher', False),
                    'member_only': promo_data.get('member_only', False),
                    'is_stackable': promo_data.get('is_stackable', True),
                    'start_date': promo_data['validity']['start_date'],
                    'end_date': promo_data['validity']['end_date'],
                    'valid_time_start': promo_data['validity'].get('time_start'),
                    'valid_time_end': promo_data['validity'].get('time_end'),
                    'valid_days': promo_data['validity'].get('days_of_week'),
                    'exclude_holidays': promo_data['validity'].get('exclude_holidays', False),
                    'compiled_data': promo_data,  # ? Store full JSON
                    'synced_from_ho': True,
                    'ho_promotion_id': promo_data['id'],
                }
            )
            count += 1
        
        # Handle deletions
        deleted_ids = data.get('deleted_ids', [])
        if deleted_ids:
            Promotion.objects.filter(id__in=deleted_ids).delete()
            self.stdout.write(f'   ???  Deleted {len(deleted_ids)} promotions')
        
        return count
    
    @transaction.atomic
    def _sync_products(self, is_full, sync_status):
        """Sync products from HO"""
        config = settings.EDGE_SERVER_CONFIG
        
        url = f"{config['HO_API_URL']}/api/sync/products/"
        headers = {'Authorization': f"Token {config['HO_API_TOKEN']}"}
        params = {
            'store_id': config['STORE_ID'],
            'company_id': config['COMPANY_ID'],
            'brand_id': config.get('BRAND_ID'),
        }
        
        if not is_full and sync_status.last_sync_at:
            params['updated_since'] = sync_status.last_sync_at.isoformat()
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        count = 0
        for prod_data in data.get('products', []):
            Product.objects.update_or_create(
                id=prod_data['id'],
                defaults={
                    'company_id': prod_data['company_id'],
                    'brand_id': prod_data['brand_id'],
                    'store_id': prod_data.get('store_id'),
                    'category_id': prod_data.get('category_id'),
                    'name': prod_data['name'],
                    'sku': prod_data['sku'],
                    'price': prod_data['price'],
                    'cost': prod_data.get('cost'),
                    'is_active': prod_data['is_active'],
                    'has_modifiers': prod_data.get('has_modifiers', False),
                    'image_url': prod_data.get('image_url'),
                    'description': prod_data.get('description'),
                }
            )
            count += 1
        
        # Handle deletions
        deleted_ids = data.get('deleted_ids', [])
        if deleted_ids:
            Product.objects.filter(id__in=deleted_ids).delete()
        
        return count
    
    @transaction.atomic
    def _sync_categories(self, is_full, sync_status):
        """Sync categories from HO"""
        config = settings.EDGE_SERVER_CONFIG
        
        url = f"{config['HO_API_URL']}/api/sync/categories/"
        headers = {'Authorization': f"Token {config['HO_API_TOKEN']}"}
        params = {
            'company_id': config['COMPANY_ID'],
            'brand_id': config.get('BRAND_ID'),
        }
        
        if not is_full and sync_status.last_sync_at:
            params['updated_since'] = sync_status.last_sync_at.isoformat()
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        count = 0
        for cat_data in data.get('categories', []):
            Category.objects.update_or_create(
                id=cat_data['id'],
                defaults={
                    'company_id': cat_data['company_id'],
                    'brand_id': cat_data.get('brand_id'),
                    'store_id': cat_data.get('store_id'),
                    'name': cat_data['name'],
                    'code': cat_data['code'],
                    'parent_id': cat_data.get('parent_id'),
                    'is_active': cat_data['is_active'],
                    'display_order': cat_data.get('display_order', 0),
                    'image_url': cat_data.get('image_url'),
                }
            )
            count += 1
        
        deleted_ids = data.get('deleted_ids', [])
        if deleted_ids:
            Category.objects.filter(id__in=deleted_ids).delete()
        
        return count
    
    @transaction.atomic
    def _sync_modifiers(self, is_full, sync_status):
        """Sync modifiers from HO"""
        config = settings.EDGE_SERVER_CONFIG
        
        url = f"{config['HO_API_URL']}/api/sync/modifiers/"
        headers = {'Authorization': f"Token {config['HO_API_TOKEN']}"}
        params = {
            'company_id': config['COMPANY_ID'],
            'brand_id': config.get('BRAND_ID'),
        }
        
        if not is_full and sync_status.last_sync_at:
            params['updated_since'] = sync_status.last_sync_at.isoformat()
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        count = 0
        for mod_data in data.get('modifiers', []):
            Modifier.objects.update_or_create(
                id=mod_data['id'],
                defaults={
                    'company_id': mod_data['company_id'],
                    'brand_id': mod_data.get('brand_id'),
                    'store_id': mod_data.get('store_id'),
                    'name': mod_data['name'],
                    'type': mod_data.get('type'),
                    'price': mod_data.get('price', 0),
                    'is_required': mod_data.get('is_required', False),
                    'min_selection': mod_data.get('min_selection', 0),
                    'max_selection': mod_data.get('max_selection', 1),
                    'options': mod_data.get('options'),
                }
            )
            count += 1
        
        deleted_ids = data.get('deleted_ids', [])
        if deleted_ids:
            Modifier.objects.filter(id__in=deleted_ids).delete()
        
        return count
    
    @transaction.atomic
    def _sync_tables(self, is_full, sync_status):
        """Sync tables from HO"""
        config = settings.EDGE_SERVER_CONFIG
        
        url = f"{config['HO_API_URL']}/api/sync/tables/"
        headers = {'Authorization': f"Token {config['HO_API_TOKEN']}"}
        params = {
            'store_id': config['STORE_ID'],
            'company_id': config['COMPANY_ID'],
        }
        
        if not is_full and sync_status.last_sync_at:
            params['updated_since'] = sync_status.last_sync_at.isoformat()
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        count = 0
        for table_data in data.get('tables', []):
            TableArea.objects.update_or_create(
                id=table_data['id'],
                defaults={
                    'company_id': table_data['company_id'],
                    'brand_id': table_data.get('brand_id'),
                    'store_id': table_data['store_id'],
                    'area_id': table_data.get('area_id'),
                    'area_name': table_data.get('area_name'),
                    'table_number': table_data['table_number'],
                    'capacity': table_data.get('capacity'),
                    'is_active': table_data['is_active'],
                    'qr_code': table_data.get('qr_code'),
                }
            )
            count += 1
        
        deleted_ids = data.get('deleted_ids', [])
        if deleted_ids:
            TableArea.objects.filter(id__in=deleted_ids).delete()
        
        return count
```

---

### Auto-Sync with Celery (Optional)

If you want automatic periodic sync:

**File:** `promotions/tasks.py`

```python
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger('promotions.sync')


@shared_task
def auto_sync_from_ho():
    """
    Celery task for automatic sync from HO
    
    Add to celery beat schedule:
    CELERY_BEAT_SCHEDULE = {
        'sync-from-ho': {
            'task': 'promotions.tasks.auto_sync_from_ho',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        },
    }
    """
    try:
        logger.info('Starting automatic sync from HO')
        call_command('sync_from_ho', '--type', 'all')
        logger.info('Automatic sync completed successfully')
    except Exception as e:
        logger.error(f'Automatic sync failed: {str(e)}', exc_info=True)
        raise
```

---


## ?? Promotion Evaluation Engine

### Evaluation Service

**File:** `promotions/services/evaluator.py`

```python
"""
Promotion Evaluation Engine for Edge Server

Evaluates promotions against cart data using embedded data from compiled_data JSONB field.
No database JOINs required - all data is self-contained in the promotion record.
"""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, time
from django.utils import timezone
import logging

logger = logging.getLogger('promotions.evaluation')


class PromotionEvaluator:
    """
    Evaluates promotions against a shopping cart
    
    Usage:
        evaluator = PromotionEvaluator()
        results = evaluator.evaluate_cart(cart_data, promotions)
    """
    
    def __init__(self):
        self.evaluation_count = 0
    
    def evaluate_cart(self, cart: Dict, promotions: List, customer: Optional[Dict] = None) -> Dict:
        """
        Evaluate all applicable promotions for a cart
        
        Args:
            cart: Cart data with items
            promotions: List of Promotion model instances
            customer: Optional customer data (for member-only promos)
            
        Returns:
            Dict with applied promotions and total discount
        """
        results = {
            'applied_promotions': [],
            'skipped_promotions': [],
            'total_discount': Decimal('0.00'),
            'original_amount': Decimal(str(cart.get('subtotal', 0))),
            'final_amount': Decimal(str(cart.get('subtotal', 0))),
        }
        
        # Sort by priority (higher first)
        sorted_promotions = sorted(
            promotions,
            key=lambda p: p.execution_priority,
            reverse=True
        )
        
        for promotion in sorted_promotions:
            try:
                result = self.evaluate_promotion(cart, promotion, customer)
                
                if result['status'] == 'applied':
                    results['applied_promotions'].append({
                        'promotion_id': str(promotion.id),
                        'code': promotion.code,
                        'name': promotion.name,
                        'discount_amount': result['discount_amount'],
                        'reason': result.get('reason', ''),
                        'details': result.get('details', {}),
                    })
                    results['total_discount'] += Decimal(str(result['discount_amount']))
                else:
                    results['skipped_promotions'].append({
                        'promotion_id': str(promotion.id),
                        'code': promotion.code,
                        'reason': result.get('reason', 'Not applicable'),
                    })
                
                self.evaluation_count += 1
                
            except Exception as e:
                logger.error(f"Error evaluating promotion {promotion.code}: {str(e)}", exc_info=True)
                results['skipped_promotions'].append({
                    'promotion_id': str(promotion.id),
                    'code': promotion.code,
                    'reason': f'Error: {str(e)}',
                })
        
        # Calculate final amount
        results['final_amount'] = results['original_amount'] - results['total_discount']
        
        return results
    
    def evaluate_promotion(self, cart: Dict, promotion, customer: Optional[Dict] = None) -> Dict:
        """
        Evaluate single promotion against cart
        
        Returns:
            Dict with status ('applied', 'skipped', 'failed') and details
        """
        # Get compiled data (all embedded!)
        compiled_data = promotion.compiled_data
        
        # 1. Check if promotion is valid now
        if not promotion.is_valid_now():
            return {
                'status': 'skipped',
                'reason': 'Promotion not valid at current time',
                'discount_amount': 0
            }
        
        # 2. Check member-only requirement
        if promotion.member_only:
            if not customer or not customer.get('is_member'):
                return {
                    'status': 'skipped',
                    'reason': 'Member-only promotion',
                    'discount_amount': 0
                }
        
        # 3. Check scope (using embedded data)
        scope_check = self._check_scope(cart, compiled_data.get('scope', {}))
        if not scope_check['applicable']:
            return {
                'status': 'skipped',
                'reason': scope_check['reason'],
                'discount_amount': 0
            }
        
        # 4. Check minimum purchase
        rules = compiled_data.get('rules', {})
        min_purchase = Decimal(str(rules.get('min_purchase', 0)))
        cart_subtotal = Decimal(str(cart.get('subtotal', 0)))
        
        if cart_subtotal < min_purchase:
            return {
                'status': 'skipped',
                'reason': f'Minimum purchase Rp {min_purchase:,.0f} not met',
                'discount_amount': 0
            }
        
        # 5. Calculate discount based on promotion type
        calculation_result = self._calculate_discount(
            cart,
            promotion.promo_type,
            rules,
            compiled_data.get('scope', {})
        )
        
        if calculation_result['discount_amount'] > 0:
            return {
                'status': 'applied',
                'discount_amount': calculation_result['discount_amount'],
                'reason': calculation_result.get('reason', 'Promotion applied'),
                'details': calculation_result.get('details', {}),
            }
        else:
            return {
                'status': 'skipped',
                'reason': calculation_result.get('reason', 'No discount calculated'),
                'discount_amount': 0
            }
    
    def _check_scope(self, cart: Dict, scope: Dict) -> Dict:
        """
        Check if cart items match promotion scope
        Uses embedded data - no database queries!
        """
        apply_to = scope.get('apply_to', 'all')
        
        # All products - always applicable
        if apply_to == 'all':
            # Check exclusions
            exclude_products = scope.get('exclude_products', [])
            if exclude_products:
                excluded_ids = [p['id'] for p in exclude_products]
                for item in cart.get('items', []):
                    if item['product_id'] in excluded_ids:
                        # Has excluded items, but still applicable to other items
                        pass
            return {'applicable': True, 'reason': 'Applies to all products'}
        
        # Specific categories
        if apply_to == 'category':
            eligible_categories = scope.get('categories', [])
            category_ids = [cat['id'] for cat in eligible_categories]
            
            # Check if any cart item is in eligible categories
            for item in cart.get('items', []):
                if item.get('category_id') in category_ids:
                    return {'applicable': True, 'reason': 'Cart has items from eligible categories'}
            
            return {
                'applicable': False,
                'reason': 'No items from eligible categories in cart'
            }
        
        # Specific products
        if apply_to == 'product':
            eligible_products = scope.get('products', [])
            product_ids = [prod['id'] for prod in eligible_products]
            
            # Check if any cart item is in eligible products
            for item in cart.get('items', []):
                if item['product_id'] in product_ids:
                    return {'applicable': True, 'reason': 'Cart has eligible products'}
            
            return {
                'applicable': False,
                'reason': 'No eligible products in cart'
            }
        
        return {'applicable': False, 'reason': 'Unknown scope type'}
    
    def _calculate_discount(self, cart: Dict, promo_type: str, rules: Dict, scope: Dict) -> Dict:
        """
        Calculate discount based on promotion type
        
        Dispatches to type-specific calculators
        """
        calculators = {
            'percent_discount': self._calc_percent_discount,
            'amount_discount': self._calc_amount_discount,
            'buy_x_get_y': self._calc_bogo,
            'combo': self._calc_combo,
            'free_item': self._calc_free_item,
            'happy_hour': self._calc_happy_hour,
            'cashback': self._calc_cashback,
            'payment_discount': self._calc_payment_discount,
            'package': self._calc_package,
            'mix_match': self._calc_mix_match,
            'upsell': self._calc_upsell,
            'threshold_tier': self._calc_threshold,
        }
        
        calculator = calculators.get(promo_type)
        if not calculator:
            return {
                'discount_amount': 0,
                'reason': f'Unsupported promotion type: {promo_type}'
            }
        
        return calculator(cart, rules, scope)
    
    # ========================================================================
    # TYPE-SPECIFIC CALCULATORS (Using Embedded Data)
    # ========================================================================
    
    def _calc_percent_discount(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate percent discount"""
        discount_percent = Decimal(str(rules.get('discount_percent', 0))) / 100
        max_discount = rules.get('max_discount_amount')
        
        # Calculate discount on eligible items
        eligible_total = self._get_eligible_amount(cart, scope)
        discount = eligible_total * discount_percent
        
        # Apply max cap
        if max_discount:
            max_discount = Decimal(str(max_discount))
            if discount > max_discount:
                discount = max_discount
        
        return {
            'discount_amount': discount,
            'reason': f'{rules.get("discount_percent")}% discount applied',
            'details': {
                'eligible_amount': float(eligible_total),
                'discount_percent': float(discount_percent * 100),
                'max_cap': float(max_discount) if max_discount else None,
            }
        }
    
    def _calc_amount_discount(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate fixed amount discount"""
        discount_amount = Decimal(str(rules.get('discount_amount', 0)))
        
        return {
            'discount_amount': discount_amount,
            'reason': f'Rp {discount_amount:,.0f} discount applied',
            'details': {
                'discount_amount': float(discount_amount),
            }
        }
    
    def _calc_bogo(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate Buy X Get Y discount"""
        buy_qty = rules.get('buy_quantity', 1)
        get_qty = rules.get('get_quantity', 1)
        get_discount_percent = Decimal(str(rules.get('get_discount_percent', 100))) / 100
        
        # Find eligible items
        eligible_items = self._get_eligible_items(cart, scope)
        
        if not eligible_items:
            return {'discount_amount': 0, 'reason': 'No eligible items for BOGO'}
        
        # Sort by price (cheapest first for free items)
        sorted_items = sorted(eligible_items, key=lambda x: x['price'])
        
        # Calculate total quantity
        total_qty = sum(item['quantity'] for item in sorted_items)
        
        # Calculate sets
        set_size = buy_qty + get_qty
        num_sets = total_qty // set_size
        
        if num_sets == 0:
            return {
                'discount_amount': 0,
                'reason': f'Need {set_size} items for BOGO (have {total_qty})'
            }
        
        # Calculate discount (cheapest items free)
        discount = Decimal('0')
        free_items = num_sets * get_qty
        items_counted = 0
        
        for item in sorted_items:
            if items_counted >= free_items:
                break
            
            qty_to_discount = min(item['quantity'], free_items - items_counted)
            item_price = Decimal(str(item['price']))
            discount += (item_price * qty_to_discount * get_discount_percent)
            items_counted += qty_to_discount
        
        return {
            'discount_amount': discount,
            'reason': f'Buy {buy_qty} Get {get_qty} applied ({num_sets} sets)',
            'details': {
                'sets': num_sets,
                'free_items': free_items,
            }
        }
    
    def _calc_combo(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate combo deal discount"""
        combo_products = rules.get('products', [])
        combo_price = Decimal(str(rules.get('combo_price', 0)))
        
        # Check if all combo products are in cart (using embedded data!)
        cart_products = {item['product_id']: item for item in cart.get('items', [])}
        
        original_total = Decimal('0')
        for combo_item in combo_products:
            product_id = combo_item.get('product_id')
            required_qty = combo_item.get('quantity', 1)
            
            if product_id not in cart_products:
                return {
                    'discount_amount': 0,
                    'reason': f'Missing combo item: {combo_item.get("name", "Unknown")}'
                }
            
            cart_item = cart_products[product_id]
            if cart_item['quantity'] < required_qty:
                return {
                    'discount_amount': 0,
                    'reason': f'Insufficient quantity for: {cart_item["name"]}'
                }
            
            # Use embedded price from combo definition
            item_price = Decimal(str(combo_item.get('price', cart_item['price'])))
            original_total += item_price * required_qty
        
        # Calculate discount
        discount = original_total - combo_price
        
        if discount <= 0:
            return {
                'discount_amount': 0,
                'reason': 'Combo price not beneficial'
            }
        
        return {
            'discount_amount': discount,
            'reason': f'Combo deal applied: {len(combo_products)} items for Rp {combo_price:,.0f}',
            'details': {
                'original_total': float(original_total),
                'combo_price': float(combo_price),
                'items_count': len(combo_products),
            }
        }
    
    def _calc_free_item(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate free item discount"""
        trigger_product_id = rules.get('trigger_product_id')
        free_product_id = rules.get('free_product_id')
        free_quantity = rules.get('free_quantity', 1)
        
        # Check if trigger product in cart
        has_trigger = any(
            item['product_id'] == trigger_product_id
            for item in cart.get('items', [])
        )
        
        if not has_trigger:
            return {
                'discount_amount': 0,
                'reason': 'Trigger product not in cart'
            }
        
        # Find free item in cart (or get price from compiled data)
        free_item = next(
            (item for item in cart.get('items', []) if item['product_id'] == free_product_id),
            None
        )
        
        if not free_item:
            # Free item not in cart yet - could add suggestion
            return {
                'discount_amount': 0,
                'reason': 'Add free item to cart to apply discount'
            }
        
        # Calculate discount
        item_price = Decimal(str(free_item['price']))
        discount = item_price * min(free_quantity, free_item['quantity'])
        
        return {
            'discount_amount': discount,
            'reason': f'Free: {free_item["name"]} � {free_quantity}',
            'details': {
                'free_item_name': free_item['name'],
                'free_quantity': free_quantity,
            }
        }
    
    def _calc_happy_hour(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate happy hour discount"""
        # Time validation already done in is_valid_now()
        # Just calculate the discount
        
        discount_percent = rules.get('discount_percent')
        discount_amount = rules.get('discount_amount')
        special_price = rules.get('special_price')
        
        if discount_percent:
            return self._calc_percent_discount(cart, rules, scope)
        elif discount_amount:
            return self._calc_amount_discount(cart, rules, scope)
        elif special_price:
            # Calculate discount to reach special price
            eligible_total = self._get_eligible_amount(cart, scope)
            target_price = Decimal(str(special_price))
            discount = eligible_total - target_price
            
            if discount > 0:
                return {
                    'discount_amount': discount,
                    'reason': f'Happy Hour special price: Rp {target_price:,.0f}',
                }
        
        return {'discount_amount': 0, 'reason': 'No happy hour discount configured'}
    
    def _calc_cashback(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate cashback (doesn't reduce bill, gives points/credit)"""
        # Cashback is recorded but doesn't reduce current bill
        cashback_type = rules.get('cashback_type', 'percent')
        cashback_value = Decimal(str(rules.get('cashback_value', 0)))
        cashback_max = rules.get('cashback_max')
        
        cart_total = Decimal(str(cart.get('subtotal', 0)))
        
        if cashback_type == 'percent':
            cashback = cart_total * (cashback_value / 100)
        else:
            cashback = cashback_value
        
        if cashback_max:
            cashback_max = Decimal(str(cashback_max))
            if cashback > cashback_max:
                cashback = cashback_max
        
        # Cashback doesn't reduce bill amount!
        return {
            'discount_amount': 0,  # No discount to bill
            'reason': f'Cashback: Rp {cashback:,.0f} (credited after payment)',
            'details': {
                'cashback_amount': float(cashback),
                'cashback_method': rules.get('cashback_method', 'points'),
            }
        }
    
    def _calc_payment_discount(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate payment method discount"""
        # Payment method should be checked at payment stage
        # For now, just calculate potential discount
        
        discount_type = rules.get('discount_type', 'percent')
        discount_value = Decimal(str(rules.get('discount_value', 0)))
        max_discount = rules.get('max_discount')
        
        cart_total = Decimal(str(cart.get('subtotal', 0)))
        
        if discount_type == 'percent':
            discount = cart_total * (discount_value / 100)
        else:
            discount = discount_value
        
        if max_discount:
            max_discount = Decimal(str(max_discount))
            if discount > max_discount:
                discount = max_discount
        
        payment_methods = rules.get('payment_methods', [])
        methods_str = ', '.join(payment_methods) if payment_methods else 'specified method'
        
        return {
            'discount_amount': discount,
            'reason': f'Payment discount with {methods_str}',
            'details': {
                'payment_methods': payment_methods,
                'requires_payment_validation': True,
            }
        }
    
    def _calc_package(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate package/set menu discount"""
        # Similar to combo
        return self._calc_combo(cart, rules, scope)
    
    def _calc_mix_match(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate mix & match discount"""
        category_id = rules.get('category_id')
        required_quantity = rules.get('required_quantity', 3)
        special_price = Decimal(str(rules.get('special_price', 0)))
        
        # Find items from specified category
        eligible_items = [
            item for item in cart.get('items', [])
            if item.get('category_id') == category_id
        ]
        
        total_qty = sum(item['quantity'] for item in eligible_items)
        
        if total_qty < required_quantity:
            return {
                'discount_amount': 0,
                'reason': f'Need {required_quantity} items from category (have {total_qty})'
            }
        
        # Calculate sets
        num_sets = total_qty // required_quantity
        
        # Calculate original price for sets
        original_total = Decimal('0')
        qty_counted = 0
        
        for item in eligible_items:
            qty_to_count = min(item['quantity'], required_quantity * num_sets - qty_counted)
            original_total += Decimal(str(item['price'])) * qty_to_count
            qty_counted += qty_to_count
            
            if qty_counted >= required_quantity * num_sets:
                break
        
        # Calculate discount
        set_total = special_price * num_sets
        discount = original_total - set_total
        
        if discount <= 0:
            return {'discount_amount': 0, 'reason': 'Mix & match price not beneficial'}
        
        return {
            'discount_amount': discount,
            'reason': f'Mix & Match: {num_sets} set(s) of {required_quantity} items',
            'details': {
                'sets': num_sets,
                'items_per_set': required_quantity,
                'set_price': float(special_price),
            }
        }
    
    def _calc_upsell(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate upsell/add-on discount"""
        required_product_id = rules.get('required_product_id')
        upsell_product_id = rules.get('upsell_product_id')
        special_price = Decimal(str(rules.get('special_price', 0)))
        
        # Check if required product in cart
        has_required = any(
            item['product_id'] == required_product_id
            for item in cart.get('items', [])
        )
        
        if not has_required:
            return {
                'discount_amount': 0,
                'reason': 'Required product not in cart'
            }
        
        # Find upsell product in cart
        upsell_item = next(
            (item for item in cart.get('items', []) if item['product_id'] == upsell_product_id),
            None
        )
        
        if not upsell_item:
            return {
                'discount_amount': 0,
                'reason': 'Upsell item not in cart',
                'details': {
                    'upsell_available': True,
                    'upsell_message': rules.get('upsell_message', ''),
                }
            }
        
        # Calculate discount
        original_price = Decimal(str(upsell_item['price']))
        discount_per_item = original_price - special_price
        total_discount = discount_per_item * upsell_item['quantity']
        
        return {
            'discount_amount': total_discount,
            'reason': f'Upsell: {upsell_item["name"]} at special price',
            'details': {
                'original_price': float(original_price),
                'special_price': float(special_price),
                'quantity': upsell_item['quantity'],
            }
        }
    
    def _calc_threshold(self, cart: Dict, rules: Dict, scope: Dict) -> Dict:
        """Calculate threshold/tiered discount"""
        tiers = rules.get('tiers', [])
        cart_total = Decimal(str(cart.get('subtotal', 0)))
        
        # Find applicable tier (highest tier that customer qualifies for)
        applicable_tier = None
        for tier in sorted(tiers, key=lambda t: t['min_amount'], reverse=True):
            min_amount = Decimal(str(tier['min_amount']))
            if cart_total >= min_amount:
                applicable_tier = tier
                break
        
        if not applicable_tier:
            min_tier = min(tiers, key=lambda t: t['min_amount'])
            return {
                'discount_amount': 0,
                'reason': f'Minimum purchase Rp {min_tier["min_amount"]:,.0f} not met'
            }
        
        # Calculate discount based on tier
        discount_type = applicable_tier.get('discount_type', 'percent')
        discount_value = Decimal(str(applicable_tier.get('discount_value', 0)))
        
        if discount_type == 'percent':
            discount = cart_total * (discount_value / 100)
        elif discount_type == 'amount':
            discount = discount_value
        else:
            discount = Decimal('0')
        
        return {
            'discount_amount': discount,
            'reason': f'Tier discount: {applicable_tier.get("tier_name", "Applied")}',
            'details': {
                'tier_name': applicable_tier.get('tier_name'),
                'min_amount': float(applicable_tier['min_amount']),
                'discount_type': discount_type,
                'discount_value': float(discount_value),
            }
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_eligible_amount(self, cart: Dict, scope: Dict) -> Decimal:
        """Calculate total amount of eligible items"""
        eligible_items = self._get_eligible_items(cart, scope)
        total = sum(
            Decimal(str(item['price'])) * item['quantity']
            for item in eligible_items
        )
        return total
    
    def _get_eligible_items(self, cart: Dict, scope: Dict) -> List[Dict]:
        """Get list of eligible items based on scope"""
        apply_to = scope.get('apply_to', 'all')
        items = cart.get('items', [])
        
        if apply_to == 'all':
            # Check exclusions
            exclude_products = scope.get('exclude_products', [])
            if exclude_products:
                excluded_ids = [p['id'] for p in exclude_products]
                items = [item for item in items if item['product_id'] not in excluded_ids]
            return items
        
        elif apply_to == 'category':
            category_ids = [cat['id'] for cat in scope.get('categories', [])]
            return [item for item in items if item.get('category_id') in category_ids]
        
        elif apply_to == 'product':
            product_ids = [prod['id'] for prod in scope.get('products', [])]
            return [item for item in items if item['product_id'] in product_ids]
        
        return []


# Convenience function
def evaluate_promotions(cart_data: Dict, customer_data: Optional[Dict] = None) -> Dict:
    """
    Convenience function to evaluate promotions for a cart
    
    Usage:
        from promotions.services.evaluator import evaluate_promotions
        
        cart = {
            'items': [...],
            'subtotal': 150000
        }
        
        result = evaluate_promotions(cart)
    """
    from promotions.models import Promotion
    from django.conf import settings
    
    # Get active promotions
    store_id = settings.EDGE_SERVER_CONFIG.get('STORE_ID')
    promotions = Promotion.get_active_promotions(store_id)
    
    # Evaluate
    evaluator = PromotionEvaluator()
    return evaluator.evaluate_cart(cart_data, promotions, customer_data)
```

---


## ?? Django Views & HTMX Integration

### Promotion Views

**File:** `promotions/views.py`

```python
"""
Promotion views for Edge Server POS
Uses HTMX for dynamic updates
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from decimal import Decimal
import json
import logging

from promotions.models import Promotion, PromotionLog
from promotions.services.evaluator import PromotionEvaluator

logger = logging.getLogger('promotions.views')


@require_http_methods(["POST"])
def calculate_promotions(request):
    """
    Calculate applicable promotions for a cart
    
    POST /promotions/calculate/
    Body: {
        "items": [
            {"product_id": "uuid", "name": "Latte", "price": 25000, "quantity": 2, "category_id": "uuid"},
            ...
        ],
        "subtotal": 50000,
        "customer": {"id": "uuid", "is_member": true, "tier": "gold"}
    }
    
    Returns: {
        "applied_promotions": [...],
        "total_discount": 15000,
        "final_amount": 35000
    }
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        cart = {
            'items': data.get('items', []),
            'subtotal': data.get('subtotal', 0)
        }
        customer = data.get('customer')
        
        # Get active promotions
        store_id = settings.EDGE_SERVER_CONFIG.get('STORE_ID')
        promotions = Promotion.get_active_promotions(store_id)
        
        # Evaluate promotions
        evaluator = PromotionEvaluator()
        results = evaluator.evaluate_cart(cart, promotions, customer)
        
        # Log successful calculation
        logger.info(f'Calculated promotions: {len(results["applied_promotions"])} applied')
        
        return JsonResponse({
            'success': True,
            'applied_promotions': results['applied_promotions'],
            'skipped_promotions': results.get('skipped_promotions', []),
            'total_discount': float(results['total_discount']),
            'original_amount': float(results['original_amount']),
            'final_amount': float(results['final_amount']),
        })
        
    except Exception as e:
        logger.error(f'Error calculating promotions: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def log_promotion_usage(request):
    """
    Log promotion usage for analytics and sync to HO
    
    POST /promotions/log-usage/
    Body: {
        "promotion_id": "uuid",
        "transaction_id": "uuid",
        "bill_id": "B001",
        "status": "applied",
        "discount_amount": 15000,
        "cart_data": {...},
        "customer_id": "uuid"
    }
    """
    try:
        data = json.loads(request.body)
        
        # Create log entry
        log_entry = PromotionLog.objects.create(
            promotion_id=data['promotion_id'],
            transaction_id=data.get('transaction_id'),
            bill_id=data.get('bill_id'),
            status=data['status'],
            reason=data.get('reason', ''),
            discount_amount=Decimal(str(data.get('discount_amount', 0))),
            original_amount=Decimal(str(data.get('original_amount', 0))),
            final_amount=Decimal(str(data.get('final_amount', 0))),
            cart_data=data.get('cart_data'),
            customer_id=data.get('customer_id'),
            customer_phone=data.get('customer_phone'),
        )
        
        logger.info(f'Logged promotion usage: {log_entry.id}')
        
        return JsonResponse({
            'success': True,
            'log_id': log_entry.id
        })
        
    except Exception as e:
        logger.error(f'Error logging promotion usage: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def promotion_list_htmx(request):
    """
    List active promotions for POS display (HTMX)
    
    GET /promotions/list/
    Returns: HTML fragment with promotion list
    """
    store_id = settings.EDGE_SERVER_CONFIG.get('STORE_ID')
    promotions = Promotion.get_active_promotions(store_id)
    
    return render(request, 'promotions/partials/promotion_list.html', {
        'promotions': promotions
    })


def promotion_detail_htmx(request, promotion_id):
    """
    Get promotion details (HTMX)
    
    GET /promotions/{id}/detail/
    Returns: HTML fragment with promotion details
    """
    try:
        promotion = Promotion.objects.get(id=promotion_id)
        return render(request, 'promotions/partials/promotion_detail.html', {
            'promotion': promotion,
            'rules': promotion.get_rules(),
            'scope': promotion.get_scope(),
        })
    except Promotion.DoesNotExist:
        return render(request, 'promotions/partials/error.html', {
            'message': 'Promotion not found'
        }, status=404)


@require_http_methods(["GET"])
def promotion_preview(request):
    """
    Preview promotion calculation (for testing)
    
    GET /promotions/preview/?promotion_id=xxx&cart_json={...}
    """
    try:
        promotion_id = request.GET.get('promotion_id')
        cart_json = request.GET.get('cart_json', '{}')
        
        promotion = Promotion.objects.get(id=promotion_id)
        cart = json.loads(cart_json)
        
        evaluator = PromotionEvaluator()
        result = evaluator.evaluate_promotion(cart, promotion)
        
        return JsonResponse({
            'success': True,
            'promotion': {
                'code': promotion.code,
                'name': promotion.name,
            },
            'result': {
                'status': result['status'],
                'discount_amount': float(result['discount_amount']),
                'reason': result.get('reason', ''),
                'details': result.get('details', {}),
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

---

### URL Configuration

**File:** `promotions/urls.py`

```python
from django.urls import path
from promotions import views

app_name = 'promotions'

urlpatterns = [
    # API endpoints
    path('calculate/', views.calculate_promotions, name='calculate'),
    path('log-usage/', views.log_promotion_usage, name='log_usage'),
    path('preview/', views.promotion_preview, name='preview'),
    
    # HTMX endpoints
    path('list/', views.promotion_list_htmx, name='list'),
    path('<uuid:promotion_id>/detail/', views.promotion_detail_htmx, name='detail'),
]
```

---

### HTMX Templates

**File:** `templates/promotions/partials/promotion_list.html`

```html
<!-- Promotion list for POS display -->
<div class="promotion-list">
    {% for promo in promotions %}
    <div class="promotion-card" 
         hx-get="{% url 'promotions:detail' promo.id %}" 
         hx-target="#promotion-detail"
         hx-swap="innerHTML">
        
        <div class="promo-header">
            <span class="promo-code">{{ promo.code }}</span>
            <span class="promo-type badge">{{ promo.get_promo_type_display }}</span>
        </div>
        
        <h4 class="promo-name">{{ promo.name }}</h4>
        
        {% if promo.promo_type == 'percent_discount' %}
            <div class="promo-value">
                {{ promo.compiled_data.rules.discount_percent }}% OFF
            </div>
        {% elif promo.promo_type == 'amount_discount' %}
            <div class="promo-value">
                Rp {{ promo.compiled_data.rules.discount_amount|floatformat:0 }} OFF
            </div>
        {% endif %}
        
        <div class="promo-validity">
            Valid: {{ promo.start_date }} - {{ promo.end_date }}
        </div>
        
        {% if promo.member_only %}
            <span class="badge badge-member">Member Only</span>
        {% endif %}
    </div>
    {% empty %}
    <div class="no-promotions">
        <p>No active promotions available</p>
    </div>
    {% endfor %}
</div>
```

**File:** `templates/promotions/partials/promotion_detail.html`

```html
<!-- Promotion detail modal/panel -->
<div class="promotion-detail">
    <h3>{{ promotion.name }}</h3>
    <p class="promo-code">Code: <strong>{{ promotion.code }}</strong></p>
    
    <div class="promo-description">
        {{ promotion.description|default:"No description" }}
    </div>
    
    <div class="promo-rules">
        <h4>Rules:</h4>
        <ul>
            {% if rules.discount_percent %}
            <li>Discount: {{ rules.discount_percent }}%</li>
            {% endif %}
            
            {% if rules.discount_amount %}
            <li>Discount: Rp {{ rules.discount_amount|floatformat:0 }}</li>
            {% endif %}
            
            {% if rules.min_purchase %}
            <li>Minimum Purchase: Rp {{ rules.min_purchase|floatformat:0 }}</li>
            {% endif %}
            
            {% if rules.max_discount_amount %}
            <li>Maximum Discount: Rp {{ rules.max_discount_amount|floatformat:0 }}</li>
            {% endif %}
        </ul>
    </div>
    
    <div class="promo-scope">
        <h4>Applies To:</h4>
        {% if scope.apply_to == 'all' %}
            <p>All products</p>
        {% elif scope.apply_to == 'category' %}
            <p>Categories:</p>
            <ul>
            {% for cat in scope.categories %}
                <li>{{ cat.name }} ({{ cat.code }})</li>
            {% endfor %}
            </ul>
        {% elif scope.apply_to == 'product' %}
            <p>Specific products</p>
        {% endif %}
    </div>
    
    {% if promotion.terms_conditions %}
    <div class="promo-terms">
        <h4>Terms & Conditions:</h4>
        <p>{{ promotion.terms_conditions }}</p>
    </div>
    {% endif %}
</div>
```

---

## ?? Testing & Validation

### Testing the Sync

```bash
# Test sync from HO
python manage.py sync_from_ho --type promotions

# Test full sync
python manage.py sync_from_ho --full

# Test specific type
python manage.py sync_from_ho --type products

# Force sync
python manage.py sync_from_ho --force
```

### Testing Promotion Evaluation

**Create test script:** `test_promotion_eval.py`

```python
from promotions.services.evaluator import evaluate_promotions

# Sample cart
cart = {
    'items': [
        {
            'product_id': 'prod-uuid-1',
            'name': 'Latte',
            'price': 25000,
            'quantity': 2,
            'category_id': 'cat-uuid-beverages'
        },
        {
            'product_id': 'prod-uuid-2',
            'name': 'Croissant',
            'price': 15000,
            'quantity': 1,
            'category_id': 'cat-uuid-bakery'
        }
    ],
    'subtotal': 65000
}

# Evaluate
result = evaluate_promotions(cart)

print(f"Applied Promotions: {len(result['applied_promotions'])}")
print(f"Total Discount: Rp {result['total_discount']:,.0f}")
print(f"Final Amount: Rp {result['final_amount']:,.0f}")

for promo in result['applied_promotions']:
    print(f"  - {promo['name']}: Rp {promo['discount_amount']:,.0f}")
```

### API Testing with curl

```bash
# Test promotion calculation
curl -X POST http://localhost:8000/promotions/calculate/ \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "product_id": "prod-uuid-1",
        "name": "Latte",
        "price": 25000,
        "quantity": 2,
        "category_id": "cat-uuid-beverages"
      }
    ],
    "subtotal": 50000
  }'

# Test promotion preview
curl "http://localhost:8000/promotions/preview/?promotion_id=promo-uuid&cart_json={...}"
```

---

## ?? Deployment Guide

### Initial Setup

```bash
# 1. Clone repository
git clone <edge-server-repo>
cd edge-server

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings:
# HO_API_URL=https://ho.example.com
# HO_API_TOKEN=your-token
# STORE_ID=your-store-uuid
# COMPANY_ID=your-company-uuid
# BRAND_ID=your-brand-uuid

# 5. Database setup
python manage.py migrate

# 6. Initial sync from HO
python manage.py sync_from_ho --full

# 7. Run server
python manage.py runserver 0.0.0.0:8000
```

### Production Deployment

```bash
# Use gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Systemd Service (Linux)

**File:** `/etc/systemd/system/edge-pos.service`

```ini
[Unit]
Description=Edge POS Server
After=network.target postgresql.service

[Service]
Type=notify
User=pos
Group=pos
WorkingDirectory=/opt/edge-pos
Environment="PATH=/opt/edge-pos/venv/bin"
ExecStart=/opt/edge-pos/venv/bin/gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Cron Job for Auto-Sync

```bash
# Add to crontab
crontab -e

# Sync every 6 hours
0 */6 * * * cd /opt/edge-pos && /opt/edge-pos/venv/bin/python manage.py sync_from_ho >> /var/log/edge-sync.log 2>&1
```

---

## ?? Monitoring & Maintenance

### Check Sync Status

```python
from promotions.models import SyncStatus

# Check last sync
for status in SyncStatus.objects.all():
    print(f"{status.entity_type}: {status.sync_status}")
    print(f"  Last sync: {status.last_sync_at}")
    print(f"  Records: {status.records_synced}")
```

### Monitor Promotion Usage

```python
from promotions.models import PromotionLog
from django.db.models import Count, Sum

# Top promotions
top_promos = PromotionLog.objects.filter(
    status='applied'
).values(
    'promotion__code', 'promotion__name'
).annotate(
    usage_count=Count('id'),
    total_discount=Sum('discount_amount')
).order_by('-usage_count')[:10]

for promo in top_promos:
    print(f"{promo['promotion__name']}: {promo['usage_count']} uses, Rp {promo['total_discount']:,.0f}")
```

### Performance Monitoring

```python
# Check promotion count
from promotions.models import Promotion
print(f"Active promotions: {Promotion.objects.filter(is_active=True).count()}")

# Check database size
from django.db import connection
cursor = connection.cursor()
cursor.execute("""
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE tablename IN ('promotions', 'products', 'categories')
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
""")
for row in cursor.fetchall():
    print(f"{row[1]}: {row[2]}")
```

---

## ?? Summary

### What You Have Now

? **Complete Edge Server Implementation**
- PostgreSQL database schema with JSONB for embedded data
- Django models for all entities
- Sync management commands
- Full promotion evaluation engine (12 types)
- API endpoints for POS integration
- HTMX views for dynamic UI
- Logging and monitoring

? **Key Features**
- **Offline-capable** - Works without internet after sync
- **Fast evaluation** - No JOINs needed (embedded data)
- **All 12 promotion types** - Fully supported
- **Cross-brand support** - Ready for multi-brand scenarios
- **Production-ready** - Complete with deployment guide

? **Performance**
- Promotion evaluation: < 50ms
- Supports 100+ concurrent POS terminals
- Efficient JSONB queries
- Proper indexing

---

## ?? Related Documentation

- **HO Implementation:** See `BACKEND_IMPLEMENTATION_ROADMAP.md`
- **Promotion Compiler:** See `promotions/services/compiler.py`
- **Feature Guide:** See `PROMOTION_FEATURES_DOCUMENTATION.md`
- **API Documentation:** See `API_DOCUMENTATION.md`

---

## ?? Troubleshooting

### Issue: Sync fails with connection error
```bash
# Check HO API URL
echo $HO_API_URL

# Test connection
curl $HO_API_URL/api/sync/promotions/?store_id=xxx

# Check logs
tail -f logs/sync.log
```

### Issue: Promotions not applying
```bash
# Check if promotions synced
python manage.py shell
>>> from promotions.models import Promotion
>>> Promotion.objects.filter(is_active=True).count()

# Check validity
>>> promo = Promotion.objects.first()
>>> promo.is_valid_now()

# Test evaluation
>>> from promotions.services.evaluator import evaluate_promotions
>>> evaluate_promotions(your_cart)
```

### Issue: Slow performance
```sql
-- Check indexes
SELECT * FROM pg_indexes WHERE tablename = 'promotions';

-- Analyze query performance
EXPLAIN ANALYZE 
SELECT * FROM promotions 
WHERE is_active = true 
AND start_date <= CURRENT_DATE 
AND end_date >= CURRENT_DATE;
```

---

**?? Edge Server Implementation Guide Complete!**

This documentation provides everything needed to implement the promotion system at the Edge Server level. The implementation uses PostgreSQL with JSONB for embedded data, ensuring fast offline-capable promotion evaluation.

---

*Documentation Version: 1.0*  
*Last Updated: 2026-01-27*  
*Status: Complete & Production Ready*

