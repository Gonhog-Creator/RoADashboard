#!/usr/bin/env python3
"""
Test S3 Connection
Simple script to test S3 connection and list files in the bucket.
"""

import os
import json
import boto3
from datetime import datetime

def load_secrets():
    """Load secrets from local secrets.json file"""
    secrets_file = os.path.join(os.path.dirname(__file__), 'secrets.json')
    if os.path.exists(secrets_file):
        with open(secrets_file, 'r') as f:
            return json.load(f)
    return None

def test_s3_connection():
    # S3 Configuration
    s3_region = 'eu-west-par'
    s3_endpoint = 'https://s3.eu-west-par.io.cloud.ovh.net/'
    s3_bucket_name = 'rise-of-atlantis-csv-exports'
    
    # Try to load from secrets file first
    secrets = load_secrets()
    if secrets:
        access_key = secrets.get('S3_ACCESS_KEY_ID')
        secret_key = secrets.get('S3_SECRET_ACCESS_KEY')
    else:
        # Fallback to environment variables or prompt
        access_key = os.environ.get('S3_ACCESS_KEY_ID') or input("Enter S3 Access Key ID: ")
        secret_key = os.environ.get('S3_SECRET_ACCESS_KEY') or input("Enter S3 Secret Access Key: ")
    
    try:
        # Initialize S3 client
        print(f"Connecting to S3...")
        print(f"Region: {s3_region}")
        print(f"Endpoint: {s3_endpoint}")
        print(f"Bucket: {s3_bucket_name}")
        
        s3_client = boto3.client(
            's3',
            region_name=s3_region,
            endpoint_url=s3_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Test connection by listing objects
        print(f"\nListing files in bucket...")
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name)
        
        if 'Contents' in response:
            print(f"Found {len(response['Contents'])} files:")
            print(f"{'Last Modified':<25} {'Size':>15} {'Key'}")
            print("-" * 80)
            
            for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True):
                last_modified = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                size = f"{obj['Size']:,}"
                key = obj['Key']
                print(f"{last_modified:<25} {size:>15} {key}")
        else:
            print("Bucket is empty or no access")
        
        print(f"\n✓ S3 connection successful!")
        
    except Exception as e:
        print(f"\n✗ S3 connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print(f"S3 Connection Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    if test_s3_connection():
        print("\nYou can now run the full automation with:")
        print("  python s3_automation.py")
