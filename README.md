# POS F&B - Django + HTMX

Aplikasi Point of Sale untuk Food & Beverage dengan Django dan HTMX.

## Features

- **Core POS**: Open/Hold/Resume/Close Bill, Void Item, Reprint
- **Table Service**: Open/Move/Join/Split Table, Merge Bill
- **Quick Service**: Quick Order, Direct Payment, Queue Number
- **Order Management**: Modifier & Notes, Split Order/Bill, Multi Payment
- **Kitchen Display System (KDS)**: Real-time order display, Status tracking
- **QR Order**: Guest ordering via QR code
- **Promotions**: Discount, Buy X Get Y, Voucher

## Requirements

- Python 3.10+
- PostgreSQL (or SQLite for development)
- Redis (optional, for WebSocket and caching)

## Quick Start

### 1. Clone and setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment

For quick development with SQLite:

```bash
export USE_SQLITE=True
export USE_LOCMEM_CACHE=True
export USE_INMEMORY_CHANNEL=True
export DEBUG=True
```

Or create `.env` file for production setup.

### 3. Initialize database

```bash
python manage.py migrate
python manage.py setup_demo
```

### 4. Run server

```bash
python manage.py runserver
```

Visit http://localhost:8000

### Login Credentials

- **Admin**: admin / admin123
- **Kasir**: kasir / kasir123 (PIN: 1234)

## Production Setup

### With PostgreSQL and Redis

```bash
export DB_NAME=pos_fnb
export DB_USER=postgres
export DB_PASSWORD=yourpassword
export DB_HOST=localhost
export REDIS_URL=redis://localhost:6379/0
export DEBUG=False
export SECRET_KEY=your-secret-key
```

### Run with Daphne (for WebSocket support)

```bash
daphne -b 0.0.0.0 -p 8000 pos_fnb.asgi:application
```

### Run Celery (for background tasks)

```bash
celery -A pos_fnb worker -l info
```

## Project Structure

```
pos_fnb/
├── apps/
│   ├── core/          # User, Outlet, Product, Category
│   ├── pos/           # Bill, Payment, Order management
│   ├── tables/        # Table management
│   ├── kitchen/       # KDS, Printer
│   ├── qr_order/      # Guest QR ordering
│   └── promotions/    # Promo & Voucher
├── templates/
├── static/
└── pos_fnb/           # Django settings
```

## API Endpoints

### POS
- `GET /` - Main POS interface
- `POST /bill/open/` - Open new bill
- `POST /bill/<id>/add-item/` - Add item to bill
- `POST /bill/<id>/pay/` - Process payment

### Kitchen
- `GET /kitchen/kds/` - Kitchen Display System
- `GET /kitchen/kds/<station>/` - KDS by station

### QR Order
- `GET /order/<outlet_id>/<table_id>/` - Guest menu

## License

MIT
