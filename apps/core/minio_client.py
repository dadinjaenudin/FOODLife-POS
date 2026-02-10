"""
MinIO Client Helper
Helper functions for interacting with MinIO object storage
"""
from minio import Minio
from minio.error import S3Error
from django.conf import settings
import os
from io import BytesIO


def get_minio_client():
    """
    Get configured MinIO client
    
    Settings required in settings.py:
    MINIO_ENDPOINT = 'minio:9000'  # or 'localhost:9000' for local dev
    MINIO_ACCESS_KEY = 'minioadmin'
    MINIO_SECRET_KEY = 'minioadmin'
    MINIO_USE_SSL = False
    MINIO_PUBLIC_URL = 'http://minio:9000'  # Public URL for browser access
    """
    endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
    access_key = getattr(settings, 'MINIO_ACCESS_KEY', 'minioadmin')
    secret_key = getattr(settings, 'MINIO_SECRET_KEY', 'minioadmin')
    use_ssl = getattr(settings, 'MINIO_USE_SSL', False)
    
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=use_ssl
    )


def ensure_bucket_exists(bucket_name):
    """
    Ensure bucket exists, create if not
    """
    client = get_minio_client()
    
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"[MinIO] Bucket '{bucket_name}' created")
            
            # Set public read policy for customer-display bucket
            if bucket_name == 'customer-display':
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
                import json
                client.set_bucket_policy(bucket_name, json.dumps(policy))
                print(f"[MinIO] Bucket '{bucket_name}' set to public read")
    except S3Error as e:
        print(f"[MinIO] Error ensuring bucket: {e}")
        raise


def upload_to_minio(bucket_name, object_name, file_data, content_type='image/jpeg'):
    """
    Upload file to MinIO
    
    Args:
        bucket_name: MinIO bucket name
        object_name: Object path/key in bucket
        file_data: File data as bytes or BytesIO
        content_type: MIME type of file
    
    Returns:
        str: Public URL to access the file
    """
    client = get_minio_client()
    
    # Ensure bucket exists
    ensure_bucket_exists(bucket_name)
    
    # Convert bytes to BytesIO if needed
    if isinstance(file_data, bytes):
        file_data = BytesIO(file_data)
        file_size = len(file_data.getvalue())
        file_data.seek(0)
    else:
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Seek back to start
    
    try:
        # Upload to MinIO
        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=content_type
        )
        
        # Build public URL
        public_url = get_minio_url(bucket_name, object_name)
        
        print(f"[MinIO] Uploaded: {object_name} to {bucket_name}")
        return public_url
        
    except S3Error as e:
        print(f"[MinIO] Upload error: {e}")
        raise Exception(f"Failed to upload to MinIO: {str(e)}")


def delete_from_minio(object_path):
    """
    Delete file from MinIO
    
    Args:
        object_path: Full path like "bucket_name/object_name" or just "object_name"
                     If just object_name, assumes 'customer-display' bucket
    """
    client = get_minio_client()
    
    # Parse path
    if '/' in object_path:
        parts = object_path.split('/', 1)
        bucket_name = parts[0]
        object_name = parts[1] if len(parts) > 1 else parts[0]
    else:
        bucket_name = 'customer-display'
        object_name = object_path
    
    try:
        client.remove_object(bucket_name, object_name)
        print(f"[MinIO] Deleted: {object_name} from {bucket_name}")
        return True
        
    except S3Error as e:
        print(f"[MinIO] Delete error: {e}")
        raise Exception(f"Failed to delete from MinIO: {str(e)}")


def get_minio_url(bucket_name, object_name):
    """
    Get public URL for MinIO object
    
    Args:
        bucket_name: MinIO bucket name
        object_name: Object path/key in bucket
    
    Returns:
        str: Public URL
    """
    # Get public URL from settings or build from endpoint
    public_url = getattr(settings, 'MINIO_PUBLIC_URL', None)
    
    if not public_url:
        # Build from endpoint
        endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
        use_ssl = getattr(settings, 'MINIO_USE_SSL', False)
        protocol = 'https' if use_ssl else 'http'
        public_url = f"{protocol}://{endpoint}"
    
    return f"{public_url}/{bucket_name}/{object_name}"


def get_minio_endpoint_for_request(request):
    """
    Derive MinIO public endpoint dynamically from the Django request host.
    Since MinIO runs on the same machine as Django (exposed on port 9002),
    we take the hostname from the request and append the MinIO port.

    This ensures images load correctly from both localhost and remote computers.
    """
    from urllib.parse import urlparse

    minio_public_url = getattr(settings, 'MINIO_PUBLIC_URL', 'http://localhost:9002')
    parsed = urlparse(minio_public_url)
    minio_port = parsed.port or 9002

    host = request.get_host()
    hostname = host.split(':')[0]
    scheme = 'https' if request.is_secure() else 'http'

    return f"{scheme}://{hostname}:{minio_port}"


def list_objects(bucket_name, prefix=''):
    """
    List objects in bucket with optional prefix
    
    Args:
        bucket_name: MinIO bucket name
        prefix: Optional prefix to filter objects
    
    Returns:
        list: List of object names
    """
    client = get_minio_client()
    
    try:
        objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]
    except S3Error as e:
        print(f"[MinIO] List error: {e}")
        return []
