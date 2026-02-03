"""
Product Photo Sync Service - Sync images from HO MinIO to Edge MinIO
"""
import requests
import hashlib
import logging
from io import BytesIO
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from apps.core.models import ProductPhoto, Product
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO client wrapper for Edge Server"""
    
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket_name = 'product-images'
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if not exists and set public read policy"""
        import json
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            
            # Set public read policy
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
            logger.info(f"Set public read policy for bucket: {self.bucket_name}")
            
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
    
    def upload_product_image(self, file_data, product_id, filename, content_type='image/jpeg', is_primary=False):
        """Upload product image to Edge MinIO"""
        try:
            # Generate object key
            suffix = 'primary' if is_primary else filename
            object_key = f"products/{product_id}/{suffix}"
            
            # Upload to MinIO
            self.client.put_object(
                self.bucket_name,
                object_key,
                data=file_data,
                length=len(file_data.getvalue()) if hasattr(file_data, 'getvalue') else len(file_data),
                content_type=content_type
            )
            
            logger.info(f"✓ Uploaded {object_key} to Edge MinIO")
            return object_key
            
        except S3Error as e:
            logger.error(f"Failed to upload {filename}: {e}")
            raise


class ProductPhotoSyncService:
    """Service to sync product photos from HO to Edge"""
    
    def __init__(self):
        from apps.core.ho_api import HOAPIClient
        
        # Use HOAPIClient for HO communication
        self.ho_client = HOAPIClient()
        
        # Edge MinIO configuration
        edge_minio_endpoint = getattr(settings, 'EDGE_MINIO_ENDPOINT', 'localhost:9002')
        edge_minio_access_key = getattr(settings, 'EDGE_MINIO_ACCESS_KEY', 'foodlife_admin')
        edge_minio_secret_key = getattr(settings, 'EDGE_MINIO_SECRET_KEY', 'foodlife_secret_2026')
        
        self.edge_minio = MinIOClient(
            endpoint=edge_minio_endpoint,
            access_key=edge_minio_access_key,
            secret_key=edge_minio_secret_key,
            secure=False
        )
        
        # Stats
        self.synced_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.total_size = 0
    
    def sync_photos(self, company_id, brand_id, store_id, limit=100):
        """
        Sync product photos from HO to Edge
        
        Args:
            company_id: UUID of company
            brand_id: UUID of brand
            store_id: UUID of store
            limit: Number of photos to sync per batch
        
        Returns:
            dict: Sync statistics
        """
        try:
            offset = 0
            has_more = True
            
            while has_more:
                # Step 1: Get photo list from HO using HOAPIClient
                logger.info(f"Fetching photos from HO (offset={offset}, limit={limit})")
                
                try:
                    # Use HOAPIClient to make authenticated request
                    data = self.ho_client._make_request(
                        'POST',
                        '/api/v1/sync/product-photos/',
                        json={
                            'company_id': str(company_id),
                            'brand_id': str(brand_id),
                            'store_id': str(store_id),
                            'limit': limit,
                            'offset': offset
                        }
                    )
                    
                    photos = data.get('photos', [])
                    has_more = data.get('has_more', False)
                    
                except Exception as e:
                    logger.error(f"Failed to fetch photos from HO: {e}")
                    break
                
                if not photos:
                    logger.info("No more photos to sync")
                    break
                
                # Process each photo
                for photo in photos:
                    self._sync_single_photo(photo)
                
                offset += limit
                
                if not has_more:
                    break
            
            return {
                'success': True,
                'synced_count': self.synced_count,
                'skipped_count': self.skipped_count,
                'failed_count': self.failed_count,
                'total_size': self.total_size
            }
            
        except Exception as e:
            logger.error(f"Error syncing photos: {e}")
            return {
                'success': False,
                'error': str(e),
                'synced_count': self.synced_count,
                'skipped_count': self.skipped_count,
                'failed_count': self.failed_count,
                'total_size': self.total_size
            }
    
    def _sync_single_photo(self, photo):
        """Sync a single photo from HO to Edge"""
        try:
            photo_id = photo['id']
            product_id = photo['product_id']
            image_url = photo['image_url']
            filename = photo['filename']
            expected_checksum = photo['checksum']
            
            logger.info(f"Syncing photo: {filename} (product: {product_id})")
            
            # Check if product exists in Edge
            if not Product.objects.filter(id=product_id).exists():
                logger.warning(f"Product {product_id} not found in Edge, skipping photo")
                self.skipped_count += 1
                return
            
            # Check if photo already synced (by checksum)
            existing_photo = ProductPhoto.objects.filter(
                id=photo_id,
                checksum=expected_checksum
            ).first()
            
            if existing_photo and existing_photo.last_sync_at:
                logger.info(f"Photo {filename} already synced, skipping")
                self.skipped_count += 1
                return
            
            # Step 2: Download from HO MinIO
            # Replace localhost:9000 with accessible HO MinIO endpoint from Edge container
            from django.conf import settings
            ho_minio_endpoint = getattr(settings, 'HO_MINIO_ENDPOINT', 'host.docker.internal:9000')
            ho_minio_secure = getattr(settings, 'HO_MINIO_SECURE', False)
            protocol = 'https' if ho_minio_secure else 'http'
            
            # Replace localhost:9000 or http://localhost:9000 with accessible endpoint
            accessible_url = image_url.replace('http://localhost:9000', f'{protocol}://{ho_minio_endpoint}')
            accessible_url = accessible_url.replace('https://localhost:9000', f'{protocol}://{ho_minio_endpoint}')
            
            logger.info(f"Downloading {filename} from {accessible_url}")
            image_response = requests.get(accessible_url, timeout=30)
            
            if image_response.status_code != 200:
                logger.error(f"Failed to download {filename}: HTTP {image_response.status_code}")
                self.failed_count += 1
                return
            
            image_data = image_response.content
            
            # Step 3: Verify checksum
            actual_checksum = hashlib.md5(image_data).hexdigest()
            if actual_checksum != expected_checksum:
                logger.error(f"Checksum mismatch for {filename}: expected={expected_checksum}, actual={actual_checksum}")
                self.failed_count += 1
                return
            
            # Step 4: Upload to Edge MinIO
            object_key = self.edge_minio.upload_product_image(
                file_data=BytesIO(image_data),
                product_id=product_id,
                filename=filename,
                content_type=photo.get('content_type', 'image/jpeg'),
                is_primary=photo.get('is_primary', False)
            )
            
            # Step 5: Save/update metadata in Edge PostgreSQL
            ProductPhoto.objects.update_or_create(
                id=photo_id,
                defaults={
                    'product_id': product_id,
                    'object_key': object_key,
                    'filename': filename,
                    'size': photo.get('size'),
                    'content_type': photo.get('content_type', 'image/jpeg'),
                    'checksum': expected_checksum,
                    'version': photo.get('version', 1),
                    'is_primary': photo.get('is_primary', False),
                    'sort_order': photo.get('sort_order', 0),
                    'last_sync_at': timezone.now()
                }
            )
            
            self.synced_count += 1
            self.total_size += photo.get('size', 0)
            logger.info(f"✓ Successfully synced {filename}")
            
        except Exception as e:
            logger.error(f"Failed to sync photo {photo.get('filename', 'unknown')}: {e}")
            self.failed_count += 1
