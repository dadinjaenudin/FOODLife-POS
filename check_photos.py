from apps.core.models import ProductPhoto, Product

print(f"Total ProductPhoto: {ProductPhoto.objects.count()}")
print(f"Primary photos: {ProductPhoto.objects.filter(is_primary=True).count()}")
print(f"\nFirst 5 photos:")
for p in ProductPhoto.objects.select_related("product")[:5]:
    print(f"  - Product: {p.product.name}")
    print(f"    Object Key: {p.object_key}")
    print(f"    Is Primary: {p.is_primary}")
    print(f"    Checksum: {p.checksum[:8] if p.checksum else 'N/A'}")
    print()

print(f"\nFirst 5 products with their photos:")
products = Product.objects.prefetch_related('photos').filter(is_active=True)[:5]
for prod in products:
    photos = prod.photos.filter(is_primary=True)
    print(f"  - {prod.name}: {photos.count()} primary photo(s)")
    for photo in photos:
        print(f"    -> {photo.object_key}")
