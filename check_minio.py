import os
from minio import Minio

# Edge MinIO
endpoint = os.getenv('EDGE_MINIO_ENDPOINT', 'edgeminio:9000')
access_key = os.getenv('EDGE_MINIO_ACCESS_KEY', 'minioadmin')
secret_key = os.getenv('EDGE_MINIO_SECRET_KEY', 'minioadmin')

print(f"Connecting to Edge MinIO: {endpoint}")
client = Minio(
    endpoint,
    access_key=access_key,
    secret_key=secret_key,
    secure=False
)

bucket = 'product-images'
print(f"\nListing objects in bucket '{bucket}':")
try:
    objects = client.list_objects(bucket, recursive=True)
    count = 0
    for obj in objects:
        print(f"  - {obj.object_name} ({obj.size} bytes)")
        count += 1
    print(f"\nTotal objects: {count}")
except Exception as e:
    print(f"Error: {e}")
