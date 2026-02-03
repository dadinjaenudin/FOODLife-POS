"""
Test script untuk sync product photos dari HO ke Edge
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Store
from apps.core.services_photo_sync import ProductPhotoSyncService
import json


class Command(BaseCommand):
    help = 'Test sync product photos from HO to Edge'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== TEST SYNC PRODUCT PHOTOS ===\n'))
        
        try:
            # Get store config
            from apps.core.models import StoreBrand
            store_config = Store.get_current()
            if not store_config:
                self.stdout.write(self.style.ERROR('❌ Store configuration not found'))
                return
            
            # Get active StoreBrand to retrieve ho_store_id
            store_brand = StoreBrand.objects.filter(store=store_config, is_active=True).first()
            if not store_brand:
                self.stdout.write(self.style.ERROR('❌ No active brand found for this store'))
                return
            
            brand = store_brand.brand
            company = brand.company
            ho_store_id = str(store_brand.ho_store_id)
            
            self.stdout.write(self.style.SUCCESS(f'✓ Store: {store_config.store_name} (Edge ID: {store_config.id})'))
            self.stdout.write(self.style.SUCCESS(f'✓ Brand: {brand.name} ({brand.id})'))
            self.stdout.write(self.style.SUCCESS(f'✓ Company: {company.name} ({company.id})'))
            self.stdout.write(self.style.SUCCESS(f'✓ HO Store ID: {ho_store_id}'))
            
            # Initialize sync service
            self.stdout.write(self.style.WARNING('\n📡 Initializing sync service...'))
            sync_service = ProductPhotoSyncService()
            
            self.stdout.write(self.style.WARNING(f'   HO API URL: {sync_service.ho_client.base_url}'))
            self.stdout.write(self.style.WARNING(f'   Edge MinIO bucket: {sync_service.edge_minio.bucket_name}'))
            
            # Test HO API connection
            self.stdout.write(self.style.WARNING('\n🔑 Testing HO API authentication...'))
            try:
                token = sync_service.ho_client._get_access_token()
                self.stdout.write(self.style.SUCCESS(f'✓ Authentication successful'))
                self.stdout.write(self.style.SUCCESS(f'   Token: {token[:20]}...'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Authentication failed: {e}'))
                return
            
            # Test sync request
            self.stdout.write(self.style.WARNING('\n📥 Testing sync request...'))
            self.stdout.write(f'   Payload:')
            payload = {
                'company_id': str(company.id),
                'brand_id': str(brand.id),
                'store_id': ho_store_id,
                'limit': 10,
                'offset': 0
            }
            self.stdout.write(f'   {json.dumps(payload, indent=6)}')
            
            try:
                data = sync_service.ho_client._make_request(
                    'POST',
                    '/api/v1/sync/product-photos/',
                    json=payload
                )
                
                self.stdout.write(self.style.SUCCESS(f'\n✓ API request successful'))
                self.stdout.write(f'   Response:')
                self.stdout.write(f'   {json.dumps(data, indent=6, default=str)}')
                
                photos = data.get('photos', [])
                has_more = data.get('has_more', False)
                
                self.stdout.write(self.style.SUCCESS(f'\n✓ Found {len(photos)} photos'))
                self.stdout.write(f'   Has more: {has_more}')
                
                if photos:
                    self.stdout.write(f'\n   First photo sample:')
                    first_photo = photos[0]
                    for key, value in first_photo.items():
                        self.stdout.write(f'      {key}: {value}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ API request failed:'))
                self.stdout.write(self.style.ERROR(f'   Error: {str(e)}'))
                self.stdout.write(self.style.ERROR(f'   Type: {type(e).__name__}'))
                
                import traceback
                self.stdout.write(self.style.ERROR('\n   Full traceback:'))
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                return
            
            # Test actual sync (just 1 photo)
            if photos:
                self.stdout.write(self.style.WARNING('\n🔄 Testing actual sync (1 photo)...'))
                try:
                    sync_service._sync_single_photo(photos[0])
                    self.stdout.write(self.style.SUCCESS(f'✓ Photo synced successfully'))
                    self.stdout.write(self.style.SUCCESS(f'   Synced: {sync_service.synced_count}'))
                    self.stdout.write(self.style.SUCCESS(f'   Skipped: {sync_service.skipped_count}'))
                    self.stdout.write(self.style.SUCCESS(f'   Failed: {sync_service.failed_count}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Sync failed: {e}'))
                    import traceback
                    self.stdout.write(self.style.ERROR(traceback.format_exc()))
            
            self.stdout.write(self.style.SUCCESS('\n\n=== TEST COMPLETED ===\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Test failed: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
