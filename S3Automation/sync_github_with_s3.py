#!/usr/bin/env python3
"""
Sync GitHub with S3 Database
Checks S3 for new/updated backups, processes them with the player analyzer,
and updates the GitHub repository with new data if needed.
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

# Add parent directory to path to import player_data_analyzer
sys.path.insert(0, str(Path(__file__).parent.parent / "DatabaseParser"))
from player_data_analyzer import PlayerDataAnalyzer

class GitHubS3Sync:
    def __init__(self, force_reprocess=False):
        # Load secrets from secrets.json first
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
        
        # Force reprocess is now opt-in (default: only process new files)
        self.force_reprocess = force_reprocess
        
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
        
        print(f"GitHubS3Sync initialized")
        print(f"  S3 Bucket: {self.s3_bucket_name}")
        print(f"  GitHub: {self.github_owner}/{self.github_repo}")
        print(f"  Force reprocess all files: {force_reprocess}")
    
    def load_secrets(self):
        """Load secrets from local secrets.json file"""
        secrets_file = os.path.join(os.path.dirname(__file__), 'secrets.json')
        if os.path.exists(secrets_file):
            with open(secrets_file, 'r') as f:
                return json.load(f)
        return None
    
    def list_s3_files(self):
        """List all tar.gz files in the S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket_name)
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.tar.gz'):
                        files.append({
                            'key': obj['Key'],
                            'last_modified': obj['LastModified'],
                            'size': obj['Size']
                        })
            return sorted(files, key=lambda x: x['last_modified'], reverse=True)
        except Exception as e:
            print(f"Error listing S3 files: {e}")
            return []
    
    def list_github_files(self):
        """Get list of CSV files in the GitHub repository"""
        if not self.github_token or not self.github_owner or not self.github_repo:
            print("GitHub credentials not configured.")
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
                files = response.json()
                existing_files = {f['name']: f for f in files if f['name'].endswith('.csv')}
                print(f"Found {len(existing_files)} CSV files in GitHub repository")
                return existing_files
            else:
                print(f"Error getting repository files: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error getting files from GitHub: {e}")
            return {}
    
    def tar_to_csv_filename(self, tar_filename):
        """Convert tar.gz filename to expected CSV filename"""
        # backup_2026-04-11_15-19-05_csv.tar.gz -> comprehensive_player_data_2026-04-11_151905.csv
        if 'backup_' in tar_filename:
            parts = tar_filename.replace('backup_', '').replace('_csv.tar.gz', '').split('_')
            if len(parts) >= 2:
                date_part = parts[0]  # 2026-04-11
                time_part = parts[1].replace('-', '')  # 15-19-05 -> 151905
                return f"comprehensive_player_data_{date_part}_{time_part}.csv"
        return None
    
    def csv_to_tar_filename(self, csv_filename):
        """Convert CSV filename back to tar.gz filename (approximate)"""
        # comprehensive_player_data_2026-04-11_151905.csv -> backup_2026-04-11_15-19-05_csv.tar.gz
        if csv_filename.startswith('comprehensive_player_data_'):
            parts = csv_filename.replace('comprehensive_player_data_', '').replace('.csv', '').split('_')
            if len(parts) >= 2:
                date_part = parts[0]  # 2026-04-11
                time_part = parts[1]  # 151905
                # Convert back to HH-MM-SS format
                if len(time_part) == 6:
                    time_formatted = f"{time_part[:2]}-{time_part[2:4]}-{time_part[4:]}"
                    return f"backup_{date_part}_{time_formatted}_csv.tar.gz"
        return None
    
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
            tar_filename = os.path.basename(tar_path)
            process_dir = os.path.join(self.temp_dir, f"processing_{tar_filename}")
            
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)
            
            os.makedirs(process_dir, exist_ok=True)
            
            tar_copy = os.path.join(process_dir, tar_filename)
            shutil.copy(tar_path, tar_copy)
            
            print(f"Processing {tar_filename} with PlayerDataAnalyzer...")
            analyzer = PlayerDataAnalyzer(process_dir)
            analyzer.generate_comprehensive_csv()
            
            output_files = list(Path(process_dir).glob("comprehensive_player_data_*.csv"))
            if output_files:
                print(f"Generated CSV: {output_files[0]}")
                return str(output_files[0])
            return None
        except Exception as e:
            print(f"Error processing tar file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def push_to_github(self, csv_file):
        """Push the CSV file to GitHub repository"""
        print(f"\n=== GitHub Push Debug Info ===")
        print(f"GitHub token configured: {bool(self.github_token)}")
        print(f"GitHub owner: {self.github_owner}")
        print(f"GitHub repo: {self.github_repo}")
        print(f"CSV file: {csv_file}")
        
        if not self.github_token or not self.github_owner or not self.github_repo:
            print("GitHub credentials not configured. Skipping push.")
            return False
        
        try:
            import requests
            import base64
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            
            csv_filename = os.path.basename(csv_file)
            csv_content_b64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            
            api_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{csv_filename}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"GitHub API URL: {api_url}")
            print("Checking if file exists in repository...")
            response = requests.get(api_url, headers=headers)
            print(f"GET response status: {response.status_code}")
            
            if response.status_code == 200:
                existing_data = response.json()
                github_sha = existing_data['sha']
                data = {
                    'message': f'Update {csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'sha': github_sha,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            else:
                data = {
                    'message': f'Add {csv_filename} - {datetime.now().isoformat()}',
                    'content': csv_content_b64,
                    'branch': 'main'
                }
                response = requests.put(api_url, json=data, headers=headers)
            
            if response.status_code in [200, 201]:
                print(f"✓ Successfully pushed {csv_filename} to GitHub")
                return True
            else:
                print(f"✗ Error pushing to GitHub: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"  Error details: {error_data}")
                except:
                    print(f"  Response text: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error pushing to GitHub: {e}")
            return False
    
    def sync(self):
        """Main sync logic"""
        try:
            print(f"\n{'='*80}")
            print(f"Starting GitHub-S3 Sync at {datetime.now().isoformat()}")
            print(f"{'='*80}\n")
            
            # Load secrets if available
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
            
            # List files in both locations
            s3_files = self.list_s3_files()
            github_files = self.list_github_files()
            
            print(f"\nS3 files: {len(s3_files)}")
            print(f"GitHub files: {len(github_files)}")
            
            # Build mapping of S3 tar files to expected CSV names
            s3_csv_mapping = {}
            for s3_file in s3_files:
                csv_name = self.tar_to_csv_filename(s3_file['key'])
                if csv_name:
                    s3_csv_mapping[csv_name] = s3_file
            
            # Determine which files to process
            if self.force_reprocess:
                # Process ALL S3 files (re-generate everything)
                files_to_process = list(s3_csv_mapping.keys())
                print(f"\nForce reprocess mode: will process ALL {len(files_to_process)} S3 files")
                print(f"This will replace existing GitHub files with newly generated CSV files")
            else:
                # Only process new files (in S3 but not in GitHub)
                files_to_process = [csv for csv in s3_csv_mapping.keys() if csv not in github_files]
                print(f"\nNormal mode: will process {len(files_to_process)} new files")
            
            if files_to_process:
                print(f"Files to process: {files_to_process}")
                
                for csv_name in files_to_process:
                    s3_file = s3_csv_mapping[csv_name]
                    print(f"\n{'='*60}")
                    print(f"Processing: {csv_name}")
                    print(f"{'='*60}")
                    
                    # Download from S3
                    tar_path = os.path.join(self.temp_dir, os.path.basename(s3_file['key']))
                    if self.download_file(s3_file['key'], tar_path):
                        # Process with player analyzer
                        csv_file = self.process_tar_file(tar_path)
                        if csv_file:
                            # Push to GitHub (will update if exists, create if new)
                            if self.push_to_github(csv_file):
                                print(f"✓ Successfully synced {csv_name}")
                            else:
                                print(f"✗ Failed to push {csv_name}")
                        else:
                            print(f"✗ Failed to process tar file")
                    else:
                        print(f"✗ Failed to download")
            else:
                print("No files to process")
            
            print(f"\n{'='*80}")
            print(f"Sync completed at {datetime.now().isoformat()}")
            print(f"{'='*80}\n")
            
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync GitHub repository with S3 database')
    parser.add_argument('--force', action='store_true', help='Force reprocess all files (default: only process new files)')
    
    args = parser.parse_args()
    
    # Only process new files by default, --force enables full reprocess
    force_reprocess = args.force
    
    sync = GitHubS3Sync(force_reprocess=force_reprocess)
    sync.sync()
