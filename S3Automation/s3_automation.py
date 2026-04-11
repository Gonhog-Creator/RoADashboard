#!/usr/bin/env python3
"""
S3 Automation Script
Downloads hourly backups from S3, processes them, and pushes to GitHub repository.
"""

import os
import sys
import boto3
import tarfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import player_data_analyzer
sys.path.insert(0, str(Path(__file__).parent.parent / "DatabaseParser"))
from player_data_analyzer import PlayerDataAnalyzer

class S3Automation:
    def __init__(self):
        # S3 Configuration
        self.s3_region = os.environ.get('S3_REGION', 'eu-west-par')
        self.s3_endpoint = os.environ.get('S3_ENDPOINT', 'https://s3.eu-west-par.io.cloud.ovh.net/')
        self.s3_bucket_name = os.environ.get('S3_BUCKET_NAME', 'rise-of-atlantis-csv-exports')
        
        # GitHub Configuration
        self.github_token = os.environ.get('PAT_TOKEN')
        self.github_repo = os.environ.get('GITHUB_REPO', 'roarealmdata')
        self.github_owner = os.environ.get('GITHUB_OWNER')
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.s3_region,
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=os.environ.get('S3_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY')
        )
        
        # Temporary directory for processing
        self.temp_dir = tempfile.mkdtemp()
        
    def list_s3_files(self):
        """List all files in the S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket_name)
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'last_modified': obj['LastModified'],
                        'size': obj['Size']
                    })
            return files
        except Exception as e:
            print(f"Error listing S3 files: {e}")
            return []
    
    def download_file(self, s3_key, local_path):
        """Download a file from S3"""
        try:
            print(f"Downloading {s3_key}...")
            self.s3_client.download_file(self.s3_bucket_name, s3_key, local_path)
            print(f"Downloaded to {local_path}")
            return True
        except Exception as e:
            print(f"Error downloading {s3_key}: {e}")
            return False
    
    def process_tar_file(self, tar_path):
        """Process a tar file using PlayerDataAnalyzer"""
        try:
            # Create a temporary directory for processing
            process_dir = os.path.join(self.temp_dir, "processing")
            os.makedirs(process_dir, exist_ok=True)
            
            # Copy tar file to processing directory
            tar_filename = os.path.basename(tar_path)
            tar_copy = os.path.join(process_dir, tar_filename)
            shutil.copy(tar_path, tar_copy)
            
            # Process using PlayerDataAnalyzer
            analyzer = PlayerDataAnalyzer(process_dir)
            analyzer.generate_comprehensive_csv()
            
            # Find the generated CSV file
            output_files = list(Path(process_dir).glob("comprehensive_player_data_*.csv"))
            if output_files:
                return str(output_files[0])
            return None
        except Exception as e:
            print(f"Error processing tar file: {e}")
            return None
    
    def push_to_github(self, csv_file):
        """Push the CSV file to GitHub repository"""
        print(f"\n=== GitHub Push Debug Info ===")
        print(f"GitHub token configured: {bool(self.github_token)}")
        print(f"GitHub owner: {self.github_owner}")
        print(f"GitHub repo: {self.github_repo}")
        print(f"CSV file: {csv_file}")
        
        if not self.github_token or not self.github_owner or not self.github_repo:
            print("ERROR: GitHub credentials not configured. Skipping GitHub push.")
            return False
        
        if not os.path.exists(csv_file):
            print(f"ERROR: CSV file does not exist: {csv_file}")
            return False
        
        try:
            import requests
            import base64
            
            # Read CSV file
            with open(csv_file, 'r') as f:
                csv_content = f.read()
            
            print(f"CSV file size: {len(csv_content)} bytes")
            
            # Base64 encode the content
            csv_content_b64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            print(f"Base64 encoded size: {len(csv_content_b64)} bytes")
            
            # Generate filename
            csv_filename = os.path.basename(csv_file)
            print(f"Target filename: {csv_filename}")
            
            # GitHub API URL
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{csv_filename}"
            print(f"GitHub API URL: {api_url}")
            
            # Check if file already exists
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            print("Checking if file exists in repository...")
            response = requests.get(api_url, headers=headers)
            print(f"GET response status: {response.status_code}")
            
            if response.status_code == 200:
                # File exists, update it
                existing_data = response.json()
                github_sha = existing_data['sha']
                print(f"File exists with SHA: {github_sha}")
                data = {
                    'message': f'Update {csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'sha': github_sha,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            else:
                # File doesn't exist, create it
                print(f"File does not exist (status {response.status_code}), creating new file")
                data = {
                    'message': f'Add {csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            
            print(f"PUT response status: {response.status_code}")
            print(f"PUT response body: {response.text[:500]}")
            
            if response.status_code in [200, 201]:
                print(f"✓ Successfully pushed {csv_filename} to GitHub")
                return True
            else:
                print(f"✗ Error pushing to GitHub: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error pushing to GitHub: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def run(self):
        """Main automation loop"""
        try:
            print(f"Starting S3 automation at {datetime.now().isoformat()}")
            
            # List files in S3
            files = self.list_s3_files()
            print(f"Found {len(files)} files in S3 bucket")
            
            # Filter for tar.gz files
            tar_files = [f for f in files if f['key'].endswith('.tar.gz')]
            print(f"Found {len(tar_files)} tar.gz files")
            
            # Process the most recent file (for now)
            if tar_files:
                # Sort by last modified, get the most recent
                tar_files.sort(key=lambda x: x['last_modified'], reverse=True)
                latest_file = tar_files[0]
                
                print(f"Processing most recent file: {latest_file['key']}")
                
                # Download the file
                tar_path = os.path.join(self.temp_dir, os.path.basename(latest_file['key']))
                if self.download_file(latest_file['key'], tar_path):
                    # Process the file
                    csv_file = self.process_tar_file(tar_path)
                    if csv_file:
                        # Push to GitHub
                        self.push_to_github(csv_file)
                    else:
                        print("Failed to process tar file")
                else:
                    print("Failed to download file")
            else:
                print("No tar.gz files found in S3 bucket")
            
        finally:
            self.cleanup()
        
        print(f"S3 automation completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    automation = S3Automation()
    automation.run()
