"""
Quick script to check if HO API sends printer_target field
"""
from apps.core.ho_api.client import HOAPIClient
import os

# Get credentials from environment
HO_API_URL = os.getenv('HO_API_URL', 'http://localhost:8000')
HO_API_USERNAME = os.getenv('HO_API_USERNAME', 'admin')
HO_API_PASSWORD = os.getenv('HO_API_PASSWORD', 'admin123')

# Hardcoded IDs from your setup
COMPANY_ID = "9a5775c5-b7aa-43f9-aae9-509eec584181"  # AVRIL-PT
STORE_ID = "21b2e3c0-275c-4169-b5df-c80b1edb87b4"    # AVRIL-001

print(f"HO API URL: {HO_API_URL}")
print(f"Username: {HO_API_USERNAME}")
print(f"Company ID: {COMPANY_ID}")
print(f"Store ID: {STORE_ID}")
print("-" * 80)

# Create HO API client
client = HOAPIClient(
    base_url=HO_API_URL,
    username=HO_API_USERNAME,
    password=HO_API_PASSWORD
)

# Get products from HO
print(f"\nFetching products from HO API...")
products = client.get_products(company_id=COMPANY_ID, store_id=STORE_ID)

print(f"\nTotal products received: {len(products)}")

if products:
    print(f"\n{'='*80}")
    print(f"FIRST PRODUCT DATA:")
    print(f"{'='*80}")
    
    first_product = products[0]
    print(f"\nProduct ID: {first_product.get('id')}")
    print(f"Product Name: {first_product.get('name')}")
    print(f"Brand ID: {first_product.get('brand_id')}")
    print(f"Category ID: {first_product.get('category_id')}")
    print(f"Printer Target: {first_product.get('printer_target', 'NOT FOUND IN API')}")
    
    print(f"\n{'='*80}")
    print(f"ALL FIELDS IN PRODUCT:")
    print(f"{'='*80}")
    for key in sorted(first_product.keys()):
        value = first_product[key]
        if len(str(value)) > 100:
            value = str(value)[:100] + "..."
        print(f"  {key}: {value}")
    
    # Check if any product has printer_target
    print(f"\n{'='*80}")
    print(f"CHECKING ALL PRODUCTS FOR printer_target:")
    print(f"{'='*80}")
    
    has_printer_target = []
    no_printer_target = []
    
    for p in products:
        if 'printer_target' in p and p['printer_target']:
            has_printer_target.append(p)
        else:
            no_printer_target.append(p)
    
    print(f"\nProducts WITH printer_target: {len(has_printer_target)}")
    if has_printer_target:
        for p in has_printer_target[:3]:  # Show first 3
            print(f"  - {p.get('name')}: {p.get('printer_target')}")
    
    print(f"\nProducts WITHOUT printer_target: {len(no_printer_target)}")
    if no_printer_target:
        for p in no_printer_target[:3]:  # Show first 3
            print(f"  - {p.get('name')}")
else:
    print("No products received from HO API")
