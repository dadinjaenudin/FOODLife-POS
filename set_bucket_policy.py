import os
import json
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

# Set bucket policy to public read
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"]
        }
    ]
}

try:
    print(f"\nSetting public read policy for bucket '{bucket}'...")
    client.set_bucket_policy(bucket, json.dumps(policy))
    print("✓ Bucket policy set successfully!")
    
    # Verify policy
    print("\nCurrent bucket policy:")
    current_policy = client.get_bucket_policy(bucket)
    print(current_policy)
    
except Exception as e:
    print(f"Error: {e}")
