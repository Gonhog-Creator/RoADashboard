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
import json
from datetime import datetime
from pathlib import Path

# Import player_data_analyzer from local directory
from player_data_analyzer import PlayerDataAnalyzer

class S3Automation:
    def __init__(self):
        # Load secrets from secrets.json for local development
        secrets = self.load_secrets()
        if secrets:
            if not os.environ.get('S3_ACCESS_KEY_ID'):
                os.environ['S3_ACCESS_KEY_ID'] = secrets.get('S3_ACCESS_KEY_ID', '')
            if not os.environ.get('S3_SECRET_ACCESS_KEY'):
                os.environ['S3_SECRET_ACCESS_KEY'] = secrets.get('S3_SECRET_ACCESS_KEY', '')
            if not os.environ.get('PAT_TOKEN'):
                os.environ['PAT_TOKEN'] = secrets.get('PAT_TOKEN', '')
            if not os.environ.get('GITHUB_OWNER'):
                os.environ['GITHUB_OWNER'] = secrets.get('GITHUB_OWNER', '')
            if not os.environ.get('GITHUB_REPO'):
                os.environ['GITHUB_REPO'] = secrets.get('GITHUB_REPO', '')
        
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
    
    def load_secrets(self):
        """Load secrets from secrets.json file for local development"""
        secrets_path = os.path.join(os.path.dirname(__file__), 'secrets.json')
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading secrets from {secrets_path}: {e}")
        return None
        
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
            # Create a unique temporary directory for processing this specific file
            tar_filename = os.path.basename(tar_path)
            process_dir = os.path.join(self.temp_dir, f"processing_{tar_filename}")
            
            # Clean up if directory exists from previous run
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)
            
            os.makedirs(process_dir, exist_ok=True)
            
            # Copy tar file to processing directory
            tar_copy = os.path.join(process_dir, tar_filename)
            shutil.copy(tar_path, tar_copy)
            
            # Process using PlayerDataAnalyzer (will only find this one file)
            analyzer = PlayerDataAnalyzer(process_dir)
            analyzer.generate_comprehensive_csv()
            
            # Find the generated compressed CSV file
            output_files = list(Path(process_dir).glob("comprehensive_player_data_*.csv.gz"))
            if output_files:
                return str(output_files[0])
            return None
        except Exception as e:
            print(f"Error processing tar file: {e}")
            return None
    
    def get_month_from_filename(self, filename):
        """Extract month and year from filename to determine bucket"""
        # Expected format: comprehensive_player_data_2026-04-22_160231.csv.gz
        # Extract date part: 2026-04-22
        if 'comprehensive_player_data_' in filename:
            # Remove .gz extension if present
            if filename.endswith('.gz'):
                filename = filename[:-3]
            date_part = filename.replace('comprehensive_player_data_', '').split('_')[0]
            try:
                date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                return date_obj.strftime('%m.%Y')
            except ValueError:
                # Fallback to current month if parsing fails
                return datetime.now().strftime('%m.%Y')
        return datetime.now().strftime('%m.%Y')
    
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
            
            # Read compressed CSV file as binary
            with open(csv_file, 'rb') as f:
                csv_content = f.read()
            
            print(f"Compressed CSV file size: {len(csv_content)} bytes")
            
            # Base64 encode the binary content
            csv_content_b64 = base64.b64encode(csv_content).decode('utf-8')
            print(f"Base64 encoded size: {len(csv_content_b64)} bytes")
            
            # Generate filename and monthly path
            csv_filename = os.path.basename(csv_file)
            month_bucket = self.get_month_from_filename(csv_filename)
            github_path = f"{month_bucket}/{csv_filename}"
            print(f"Target filename: {csv_filename}")
            print(f"Monthly bucket: {month_bucket}")
            print(f"GitHub path: {github_path}")
            
            # GitHub API URL
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{github_path}"
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
                    'message': f'Update {month_bucket}/{csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'sha': github_sha,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            else:
                # File doesn't exist, create it
                print(f"File does not exist (status {response.status_code}), creating new file")
                data = {
                    'message': f'Add {month_bucket}/{csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            
            print(f"PUT response status: {response.status_code}")
            print(f"PUT response body: {response.text[:500]}")
            
            if response.status_code in [200, 201]:
                print(f"✓ Successfully pushed {month_bucket}/{csv_filename} to GitHub")
                return True
            else:
                print(f"✗ Error pushing to GitHub: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error pushing to GitHub: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_existing_github_files(self):
        """Get list of existing CSV files in the GitHub repository with their full paths"""
        if not self.github_token or not self.github_owner or not self.github_repo:
            print("GitHub credentials not configured. Cannot check existing files.")
            return set()
        
        try:
            import requests
            
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                root_files = response.json()
                existing_files = set()
                
                # Check root directory for CSV files (backward compatibility)
                for f in root_files:
                    if (f['name'].endswith('.csv') or f['name'].endswith('.csv.gz')) and f['type'] == 'file':
                        existing_files.add(f['name'])
                    elif f['type'] == 'dir':
                        # Check if this looks like a monthly directory (contains digits)
                        # Recursively check subdirectories
                        sub_files = self.get_files_in_directory(f['name'])
                        existing_files.update(sub_files)
                
                print(f"Found {len(existing_files)} existing CSV files in repository")
                return existing_files
            else:
                print(f"Error getting repository files: {response.status_code} - {response.text}")
                return set()
        except Exception as e:
            print(f"Error getting existing files from GitHub: {e}")
            return set()
    
    def get_files_in_directory(self, dir_path):
        """Recursively get CSV files from a directory"""
        try:
            import requests
            
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{dir_path}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                csv_files = set()
                
                for f in files:
                    if (f['name'].endswith('.csv') or f['name'].endswith('.csv.gz')) and f['type'] == 'file':
                        # Store as full path: month/filename.csv
                        csv_files.add(f"{dir_path}/{f['name']}")
                    elif f['type'] == 'dir':
                        # Recursively check subdirectories
                        sub_files = self.get_files_in_directory(f"{dir_path}/{f['name']}")
                        csv_files.update(sub_files)
                
                return csv_files
            else:
                print(f"Error getting files in directory {dir_path}: {response.status_code}")
                return set()
        except Exception as e:
            print(f"Error getting files from directory {dir_path}: {e}")
            return set()
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def run(self, force=False):
        """Main automation loop"""
        try:
            print(f"Starting S3 automation at {datetime.now().isoformat()}")
            if force:
                print("Force mode enabled - will regenerate all files")
            
            # List files in S3
            files = self.list_s3_files()
            print(f"Found {len(files)} files in S3 bucket")
            
            # Filter for tar.gz files
            tar_files = [f for f in files if f['key'].endswith('.tar.gz')]
            print(f"Found {len(tar_files)} tar.gz files")
            
            # Filter out bad backups (anomalously small files)
            # Good backups are typically 380-470 MB, bad backups are 2-11 MB
            # Use 50 MB as a safe threshold
            MIN_SIZE_THRESHOLD = 50 * 1024 * 1024  # 50 MB
            tar_files = [f for f in tar_files if f['size'] >= MIN_SIZE_THRESHOLD]
            filtered_count = len(files) - len(tar_files)
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} small files (likely bad backups)")
            print(f"Found {len(tar_files)} valid tar.gz files after size filter")
            
            # Get existing files from GitHub
            existing_files = self.get_existing_github_files()
            print(f"Found {len(existing_files)} existing CSV files in repository")
            
            if force:
                print("Force mode - regenerating all files")
                existing_files = set()  # Clear existing files to force reprocessing
            
            # Process all tar.gz files
            if tar_files:
                # Sort by last modified (oldest first for chronological processing)
                tar_files.sort(key=lambda x: x['last_modified'])
                
                processed_count = 0
                skipped_count = 0
                
                for tar_file in tar_files:
                    # Convert tar.gz filename to expected CSV filename
                    tar_filename = os.path.basename(tar_file['key'])
                    # Extract timestamp from tar filename: backup_2026-04-11_15-19-05_csv.tar.gz
                    # to CSV filename: comprehensive_player_data_2026-04-11_151905.csv
                    if 'backup_' in tar_filename:
                        # Extract date and time parts
                        parts = tar_filename.replace('backup_', '').replace('_csv.tar.gz', '').split('_')
                        if len(parts) >= 2:
                            date_part = parts[0]  # 2026-04-11
                            time_part = parts[1].replace('-', '')  # 15-19-05 -> 151905
                            expected_csv = f"comprehensive_player_data_{date_part}_{time_part}.csv.gz"
                            
                            # Calculate expected monthly path
                            try:
                                date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                                month_bucket = date_obj.strftime('%m.%Y')
                                expected_path = f"{month_bucket}/{expected_csv}"
                            except ValueError:
                                # Fallback to current month if parsing fails
                                month_bucket = datetime.now().strftime('%m.%Y')
                                expected_path = f"{month_bucket}/{expected_csv}"
                            
                            # Check if this file already exists in repository (check both old and new formats)
                            if expected_csv in existing_files or expected_path in existing_files:
                                print(f"Skipping {tar_filename} - {expected_csv} already exists in repository")
                                skipped_count += 1
                                continue
                    
                    print(f"Processing file: {tar_file['key']}")
                    
                    # Download the file
                    tar_path = os.path.join(self.temp_dir, os.path.basename(tar_file['key']))
                    if self.download_file(tar_file['key'], tar_path):
                        # Process the file
                        csv_file = self.process_tar_file(tar_path)
                        if csv_file:
                            # Push to GitHub
                            if self.push_to_github(csv_file):
                                processed_count += 1
                                # Add to existing files to avoid duplicate processing in same run
                                csv_filename = os.path.basename(csv_file)
                                existing_files.add(csv_filename)
                            else:
                                print(f"Failed to push {csv_file} to GitHub")
                        else:
                            print("Failed to process tar file")
                    else:
                        print("Failed to download file")
                
                print(f"\nProcessing summary:")
                print(f"Processed: {processed_count} files")
                print(f"Skipped (already exist): {skipped_count} files")
            else:
                print("No tar.gz files found in S3 bucket")
            
        finally:
            self.cleanup()
        
        print(f"S3 automation completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='S3 Automation Script')
    parser.add_argument('--force', action='store_true', 
                       help='Force regeneration of all files, ignoring existing files')
    args = parser.parse_args()
    
    automation = S3Automation()
    automation.run(force=args.force)
