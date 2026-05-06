"""Data loading module for CSV files from GitHub"""
import streamlit as st
import pandas as pd
import json
import os
import gzip
from datetime import datetime
import requests
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import calculate_daily_rate
try:
    from auth import get_github_credentials
except ImportError:
    try:
        from DailyReportTools.auth import get_github_credentials
    except ImportError:
        # Fallback - define minimal function needed
        import streamlit as st
        import json
        import os
        def get_github_credentials():
            try:
                # Try st.secrets first
                if hasattr(st, 'secrets'):
                    github_token = st.secrets.get("github_token", "")
                    csv_repo_url = st.secrets.get("csv_repo_url", "")
                    if github_token and csv_repo_url:
                        return github_token, csv_repo_url
                
                # Fallback to local_config.json
                config_path = os.path.join(os.path.dirname(__file__), "local_config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    return config.get("GITHUB_TOKEN", ""), config.get("CSV_REPO_URL", "")
                
                return "", ""
            except:
                return "", ""

def parse_comprehensive_csv_from_string(content, filename):
    """Parse comprehensive CSV from string content (for GitHub loading)"""
    try:
        # Try to extract date from filename
        if "comprehensive_player_data" in filename:
            # Look for date pattern in filename - format: comprehensive_player_data_YYYY-MM-DD_HHMMSS.csv
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{6})', filename)
            if date_match:
                date_part = date_match.group(1)
                time_part = date_match.group(2)
                # Convert HHMMSS to HH:MM:SS format
                if len(time_part) == 6:
                    formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
                    date_str = date_part + "_" + formatted_time
                    date = datetime.strptime(date_str, "%Y-%m-%d_%H:%M:%S")
                else:
                    # Fallback to current time
                    date = datetime.now()
            else:
                # Fallback to current time
                date = datetime.now()
        else:
            return None
        
        # Read the comprehensive CSV from string
        df = pd.read_csv(StringIO(content))
        
        # Calculate realm summary data
        total_players = len(df)
        
        # Calculate total power (sum of power column if it exists)
        total_power = 0
        if 'power' in df.columns:
            total_power = df['power'].fillna(0).sum()
        
        # Calculate average power per player
        avg_power_per_player = total_power / total_players if total_players > 0 else 0
        
        # Aggregate items data from individual player rows
        items = {}
        # Try items_json format first (new comprehensive format)
        if 'items_json' in df.columns:
            for _, row in df.iterrows():
                try:
                    items_json_str = row['items_json']
                    if pd.notna(items_json_str) and items_json_str:
                        # Handle double-escaped JSON from CSV: "{\"key\": value}"
                        # pandas read_csv should handle the outer quotes, but we need to handle inner escaping
                        items_dict = json.loads(items_json_str)
                        for item_name, count in items_dict.items():
                            items[item_name] = items.get(item_name, 0) + count
                except:
                    continue
        else:
            # Fallback to old format (individual item columns)
            item_columns = [col for col in df.columns if col.startswith('item_')]
            for col in item_columns:
                item_name = col.replace('item_', '')
                total_amount = df[col].fillna(0).sum()
                if total_amount > 0:
                    items[item_name] = total_amount

        # Aggregate resources (comprehensive format uses resource_ prefix)
        resources = {}
        resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'resource_ruby']
        resource_names = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        
        for col, name in zip(resource_columns, resource_names):
            if col in df.columns:
                total_amount = df[col].fillna(0).sum()
                resources[name] = total_amount
        
        # Extract additional data for new tabs
        buildings_data = {}  # Buildings data extraction moved to buildings.py
        
        # Parse troops data from JSON format
        troops_data = {}
        if 'troops_json' in df.columns:
            for _, row in df.iterrows():
                try:
                    troops_json_str = row['troops_json']
                    if pd.notna(troops_json_str) and troops_json_str:
                        troops_dict = json.loads(troops_json_str)
                        for troop_name, count in troops_dict.items():
                            # Skip resource columns (they start with 'resource_')
                            if not troop_name.startswith('resource_'):
                                troops_data[troop_name] = troops_data.get(troop_name, 0) + count
                except:
                    continue
        else:
            # Fallback to old format (individual troop columns)
            troop_columns = [col for col in df.columns if col.startswith('troop_')]
            for col in troop_columns:
                troop_name = col
                total_amount = df[col].fillna(0).sum()
                if total_amount > 0:
                    troops_data[troop_name] = total_amount
        
        # Parse skins data
        skins_data = {}
        if 'equipped_skins' in df.columns:
            df['equipped_skins'].value_counts().to_dict()
        
        # Parse quests and research data
        quests_data = {
            'completed_quests': df['completed_quests_count'].fillna(0).sum(),
            'completed_research': df['completed_research_count'].fillna(0).sum(),
            'in_progress_quests': df['in_progress_quests_count'].fillna(0).sum()
        }
        
        # Calculate ceasefire protection data - always initialize as empty dict
        ceasefire_data = {}
        
        # Only calculate ceasefire data for comprehensive CSV files with required columns
        if 'active_effects' in df.columns and 'resource_gold' in df.columns:
            # Check for ceasefire effects (prevent_attacks) - match ceasefire tab logic
            attack_prevention_effects = ['prevent_attacks:1']
            df['has_ceasefire'] = df['active_effects'].fillna('').astype(str).apply(
                lambda x: any(effect in x for effect in attack_prevention_effects)
            )
            
            # Calculate protected resources for each resource type
            resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'resource_ruby']
            resource_names = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
            
            for col, name in zip(resource_columns, resource_names):
                if col in df.columns:
                    total_amount = df[col].fillna(0).sum()
                    protected_amount = df[df['has_ceasefire']][col].fillna(0).sum()
                    protected_percentage = (protected_amount / total_amount * 100) if total_amount > 0 else 0
                    
                    ceasefire_data[name] = {
                        'total': total_amount,
                        'protected': protected_amount,
                        'protected_percentage': protected_percentage
                    }
        
        realm_data = {
            'date': date,
            'filename': filename,
            'total_players': total_players,
            'total_power': total_power,
            'avg_power_per_player': avg_power_per_player,
            'resources': resources,
            'items': items,
            'buildings_data': buildings_data,
            'troops_data': troops_data,
            'skins_data': skins_data,
            'quests_data': quests_data,
            'ceasefire_data': ceasefire_data,
            'raw_player_data': df  # Store raw data for detailed tabs
        }
        
        return realm_data
        
    except Exception as e:
        # Silently skip parsing errors to avoid sidebar clutter
        return None

def parse_comprehensive_csv(file_path):
    """Parse the new comprehensive_player_data.csv format"""
    try:
        # Extract date from filename - format: comprehensive_player_data_YYYY-MM-DD_HHMMSS.csv
        filename = os.path.basename(file_path)
        
        # Try to extract date from filename
        if "comprehensive_player_data" in filename:
            # Look for date pattern in filename - format: comprehensive_player_data_YYYY-MM-DD_HHMMSS.csv
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{6})', filename)
            if date_match:
                date_part = date_match.group(1)
                time_part = date_match.group(2)
                # Convert HHMMSS to HH:MM:SS format
                if len(time_part) == 6:
                    formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
                    date_str = date_part + "_" + formatted_time
                    date = datetime.strptime(date_str, "%Y-%m-%d_%H:%M:%S")
                else:
                    # Fallback to file modification time
                    date = datetime.fromtimestamp(os.path.getmtime(file_path))
            else:
                # Fallback to file modification time
                date = datetime.fromtimestamp(os.path.getmtime(file_path))
        else:
            return None
        
        # Read the comprehensive CSV
        df = pd.read_csv(file_path)
        
        # Calculate realm summary data
        total_players = len(df)
        
        # Calculate total power (sum of power column if it exists)
        total_power = 0
        if 'power' in df.columns:
            total_power = df['power'].fillna(0).sum()
        
        # Calculate average power per player
        avg_power_per_player = total_power / total_players if total_players > 0 else 0
        
        # Aggregate items data from individual player rows
        items = {}
        # Try items_json format first (new comprehensive format)
        if 'items_json' in df.columns:
            for _, row in df.iterrows():
                try:
                    items_json_str = row['items_json']
                    if pd.notna(items_json_str) and items_json_str:
                        # Handle double-escaped JSON from CSV: "{\"key\": value}"
                        # pandas read_csv should handle the outer quotes, but we need to handle inner escaping
                        items_dict = json.loads(items_json_str)
                        for item_name, count in items_dict.items():
                            items[item_name] = items.get(item_name, 0) + count
                except:
                    continue
        else:
            # Fallback to old format (individual item columns)
            item_columns = [col for col in df.columns if col.startswith('item_')]
            for col in item_columns:
                item_name = col.replace('item_', '')
                total_amount = df[col].fillna(0).sum()
                if total_amount > 0:
                    items[item_name] = total_amount

        # Aggregate resources (comprehensive format uses resource_ prefix)
        resources = {}
        resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'resource_ruby']
        resource_names = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        
        for col, name in zip(resource_columns, resource_names):
            if col in df.columns:
                total_amount = df[col].fillna(0).sum()
                resources[name] = total_amount
        
        # Extract additional data for new tabs
        buildings_data = {}  # Buildings data extraction moved to buildings.py
        
        # Parse troops data from JSON format
        troops_data = {}
        if 'troops_json' in df.columns:
            for _, row in df.iterrows():
                try:
                    troops_json_str = row['troops_json']
                    if pd.notna(troops_json_str) and troops_json_str:
                        troops_dict = json.loads(troops_json_str)
                        for troop_name, count in troops_dict.items():
                            # Skip resource columns (they start with 'resource_')
                            if not troop_name.startswith('resource_'):
                                troops_data[troop_name] = troops_data.get(troop_name, 0) + count
                except:
                    continue
        else:
            # Fallback to old format (individual troop columns)
            troop_columns = [col for col in df.columns if col.startswith('troop_')]
            for col in troop_columns:
                troop_name = col
                total_amount = df[col].fillna(0).sum()
                if total_amount > 0:
                    troops_data[troop_name] = total_amount
        
        # Parse skins data
        skins_data = {}
        if 'equipped_skins' in df.columns:
            df['equipped_skins'].value_counts().to_dict()
        
        # Parse quests and research data
        quests_data = {
            'completed_quests': df['completed_quests_count'].fillna(0).sum(),
            'completed_research': df['completed_research_count'].fillna(0).sum(),
            'in_progress_quests': df['in_progress_quests_count'].fillna(0).sum()
        }
        
        # Calculate ceasefire protection data - always initialize as empty dict
        ceasefire_data = {}
        
        # Only calculate ceasefire data for comprehensive CSV files with required columns
        if 'active_effects' in df.columns and 'resource_gold' in df.columns:
            # Check for ceasefire effects (prevent_attacks) - match ceasefire tab logic
            attack_prevention_effects = ['prevent_attacks:1']
            df['has_ceasefire'] = df['active_effects'].fillna('').astype(str).apply(
                lambda x: any(effect in x for effect in attack_prevention_effects)
            )
            
            # Calculate protected resources for each resource type
            resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'resource_ruby']
            resource_names = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
            
            for col, name in zip(resource_columns, resource_names):
                if col in df.columns:
                    total_amount = df[col].fillna(0).sum()
                    protected_amount = df[df['has_ceasefire']][col].fillna(0).sum()
                    protected_percentage = (protected_amount / total_amount * 100) if total_amount > 0 else 0
                    
                    ceasefire_data[name] = {
                        'total': total_amount,
                        'protected': protected_amount,
                        'protected_percentage': protected_percentage
                    }
        
        realm_data = {
            'date': date,
            'filename': filename,
            'total_players': total_players,
            'total_power': total_power,
            'avg_power_per_player': avg_power_per_player,
            'resources': resources,
            'items': items,
            'buildings_data': buildings_data,
            'troops_data': troops_data,
            'skins_data': skins_data,
            'quests_data': quests_data,
            'ceasefire_data': ceasefire_data,
            'raw_player_data': df  # Store raw data for detailed tabs
        }
        
        return realm_data
        
    except Exception as e:
        # Silently skip parsing errors to avoid sidebar clutter
        return None

def parse_single_file(file_source, filename=None):
    """Parse a single CSV file and return the data. Can accept file path or StringIO object."""
    try:
        # Handle StringIO object vs file path
        if isinstance(file_source, StringIO):
            content = file_source.read()
            if filename is None:
                return None  # Need filename for parsing
            # Check if this is a comprehensive CSV file from GitHub
            if "comprehensive_player_data" in filename:
                return parse_comprehensive_csv_from_string(content, filename)
        else:
            # It's a file path
            if "comprehensive_player_data" in os.path.basename(file_source):
                return parse_comprehensive_csv(file_source)
            
            filename = os.path.basename(file_source)
            with open(file_source, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Extract just the basename if filename includes directory path (from GitHub)
        filename = os.path.basename(filename)
        
        # Remove .gz extension if present for old/new format files
        if filename.endswith('.gz'):
            filename = filename[:-3]
        
        # Extract date from filename (handle both formats)
        parts = filename.split("_")
        
        # Handle old format: realm_Ruby_analytics_2026-03-14_235254.csv
        if len(parts) >= 5 and parts[0] == "realm" and parts[2] == "analytics":
            date_str = parts[3] + "_" + parts[4].replace(".csv", "")
            # Old format has no time separators, parse as HHMMSS
            if ":" not in date_str:
                time_part = date_str.split("_")[1]
                if len(time_part) == 6:  # HHMMSS format
                    formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
                    date_str = date_str.split("_")[0] + "_" + formatted_time
        # Handle new format: Ruby_2026-03-13_15-11-58.csv
        elif len(parts) >= 3:
            date_str = parts[1] + "_" + parts[2].replace(".csv", "")
            # New format uses hyphens, convert to colons
            if "-" in date_str:
                time_part = date_str.split("_")[1]
                formatted_time = time_part.replace("-", ":")
                date_str = date_str.split("_")[0] + "_" + formatted_time
        else:
            return None  # Skip unparseable filename
        
        date = datetime.strptime(date_str, "%Y-%m-%d_%H:%M:%S")
        
        # Parse sections
        sections = content.split('\nSection;')
        
        realm_data = {'date': date, 'filename': filename}
        
        for section in sections:
            if 'Realm Summary' in section:
                lines = section.strip().split('\n')
                for line in lines:
                    if 'Realm Name' in line:
                        realm_data['realm_name'] = line.split(';')[1].strip('"')
                    elif 'Total Players' in line:
                        realm_data['total_players'] = int(line.split(';')[1])
                    elif 'Total Power' in line:
                        realm_data['total_power'] = int(line.split(';')[1])
                    elif 'Average Power per Player' in line:
                        realm_data['avg_power_per_player'] = float(line.split(';')[1])
            
            elif 'Resources' in section:
                lines = section.strip().split('\n')[1:]  # Skip header
                resources = {}
                for line in lines:
                    if line and ';' in line and not line.startswith('resource_type'):
                        parts = line.split(';')
                        if len(parts) >= 2:
                            resource_name = parts[0]
                            total_amount = parts[1]
                            try:
                                resources[resource_name] = float(total_amount)
                            except ValueError:
                                continue
                realm_data['resources'] = resources
            
            elif 'Items' in section:
                lines = section.strip().split('\n')[1:]  # Skip header
                items = {}
                for line in lines:
                    if line and ';' in line and not line.startswith('item_definition_id'):
                        parts = line.split(';')
                        if len(parts) >= 2:
                            item_name = parts[0]
                            total_amount = parts[1]
                            try:
                                items[item_name] = float(total_amount)
                            except ValueError:
                                continue
                realm_data['items'] = items
        
        # Add empty ceasefire_data for old CSV files
        realm_data['ceasefire_data'] = {}
        
        return realm_data
        
    except Exception as e:
        # Silently skip parsing errors to avoid sidebar clutter
        return None

def load_csv_files_from_github():
    """Load CSV files directly from GitHub API (no local files)"""
    try:
        # Get GitHub credentials from centralized auth module
        github_token, csv_repo_url = get_github_credentials()
        
        if not github_token or not csv_repo_url:
            st.error("❌ GitHub credentials not configured. Please add github_token and csv_repo_url to secrets.")
            return pd.DataFrame(), 0
        
        # Extract owner and repo from URL
        if "/tree/" in csv_repo_url:
            repo_parts = csv_repo_url.split("/tree/")
            repo_base = repo_parts[0]
            branch = repo_parts[1] if len(repo_parts) > 1 else "main"
        else:
            repo_base = csv_repo_url
            branch = "main"
        
        # Extract owner and repo name
        url_parts = repo_base.replace("https://github.com/", "").split("/")
        if len(url_parts) < 2:
            st.error("❌ Invalid repository URL format")
            return pd.DataFrame(), 0
        
        owner, repo = url_parts[0], url_parts[1]
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"❌ GitHub API error: {response.status_code}")
            return pd.DataFrame(), 0
        
        files = response.json()
        csv_files = []
        
        # Check root directory for CSV files (backward compatibility)
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                csv_files.append(f)
            elif f.get('type') == 'dir':
                # Check if this looks like a monthly directory (contains digits)
                # Recursively check subdirectories for CSV files
                sub_files = get_csv_files_from_directory(f['name'], owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        if not csv_files:
            st.warning("⚠️ No CSV files found in remote repository")
            return pd.DataFrame(), 0
        
        # Use session state for in-memory cache
        if 'parsed_files_memory_cache' not in st.session_state:
            st.session_state.parsed_files_memory_cache = {}
        
        memory_cache = st.session_state.parsed_files_memory_cache
        new_parsed_count = 0
        all_data = []
        
        # Only cache raw_player_data for the most recent 30 files to save memory
        MAX_RAW_DATA_CACHE = 30
        
        # Track timing for performance analysis
        import time
        start_time = time.time()
        
        # Use st.spinner which automatically disappears when done
        with st.spinner("🏰 Loading Realm Data..."):
            # Overall progress bar
            overall_progress = st.progress(0)
            status_text = st.empty()
            
            # Recent activity display (show last 5 files)
            recent_activity = st.empty()
            
            # Separate cached and uncached files
            files_to_download = []
            for file_info in csv_files:
                filename = file_info['name']
                if filename in memory_cache:
                    all_data.append(memory_cache[filename]['data'])
                else:
                    files_to_download.append(file_info)
            
            if files_to_download:
                # Track total bytes downloaded
                total_bytes_downloaded = 0
                
                def download_and_parse_file(file_info):
                    """Download and parse a single file"""
                    download_url = file_info.get('download_url')
                    if not download_url:
                        return None, file_info['name'], "No download URL"
                    
                    filename = file_info['name']
                    short_name = filename.split('/')[-1]
                    
                    try:
                        download_start = time.time()
                        csv_response = requests.get(download_url, headers=headers)
                        download_time = time.time() - download_start
                        
                        if csv_response.status_code != 200:
                            return None, filename, f"Download failed: {csv_response.status_code}"
                        
                        # Track bytes downloaded
                        nonlocal total_bytes_downloaded
                        bytes_downloaded = len(csv_response.content)
                        total_bytes_downloaded += bytes_downloaded
                        
                        # Track decompression/parsing time
                        parse_start = time.time()
                        
                        # Check if file is compressed
                        if filename.endswith('.gz'):
                            csv_content = StringIO(gzip.decompress(csv_response.content).decode('utf-8'))
                        else:
                            csv_content = StringIO(csv_response.text)
                        
                        parsed_data = parse_single_file(csv_content, filename)
                        parse_time = time.time() - parse_start
                        
                        return parsed_data, filename, None, bytes_downloaded, download_time, parse_time
                    except Exception as e:
                        return None, filename, str(e), 0, 0, 0
                
                def format_bytes(bytes):
                    """Format bytes to human-readable format"""
                    if bytes < 1024 * 1024:
                        return f"{bytes / 1024:.2f} KB"
                    elif bytes < 1024 * 1024 * 1024:
                        return f"{bytes / (1024 * 1024):.2f} MB"
                    else:
                        return f"{bytes / (1024 * 1024 * 1024):.2f} GB"
                
                # Download files in parallel using ThreadPoolExecutor
                completed_count = 0
                recent_files = []
                
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_file = {
                        executor.submit(download_and_parse_file, file_info): file_info 
                        for file_info in files_to_download
                    }
                    
                    for future in as_completed(future_to_file):
                        completed_count += 1
                        progress = completed_count / len(files_to_download)
                        overall_progress.progress(progress)
                        status_text.markdown(f"**Progress: {completed_count}/{len(files_to_download)} files ({progress:.1%}) | Downloaded: {format_bytes(total_bytes_downloaded)}**")
                        
                        parsed_data, filename, error, bytes_downloaded, download_time, parse_time = future.result()
                        short_name = filename.split('/')[-1]
                        
                        if error:
                            recent_files.insert(0, f"❌ {short_name} - {error}")
                        elif parsed_data:
                            memory_cache[filename] = {'data': parsed_data}
                            all_data.append(parsed_data)
                            new_parsed_count += 1
                            recent_files.insert(0, f"✅ {short_name} ({format_bytes(bytes_downloaded)}) - DL: {download_time:.2f}s, Parse: {parse_time:.2f}s")
                        else:
                            recent_files.insert(0, f"⚠️ {short_name} - No data")
                        
                        # Show last 5 recent activities
                        recent_display = recent_files[:5]
                        recent_activity.markdown("**Recent Activity:**\n" + "\n".join(f"• {f}" for f in recent_display))
                
                # Clear all loading indicators before spinner exits
                overall_progress.empty()
                status_text.empty()
                recent_activity.empty()
                
                # Display timing information (temporary toast)
                total_time = time.time() - start_time
                if total_bytes_downloaded > 0:
                    avg_speed = total_bytes_downloaded / total_time / (1024 * 1024)  # MB/s
                    st.toast(f"⏱️ Total time: {total_time:.2f}s | Avg speed: {avg_speed:.2f} MB/s", icon="⏱️")
            else:
                pass
    
    except Exception as e:
        st.error(f"❌ Error loading from GitHub: {e}")
        return pd.DataFrame(), 0
    
    # Sort by date
    all_data.sort(key=lambda x: x['date'])
    
    # Remove raw_player_data from older files to save memory (keep only most recent 30)
    for idx, data in enumerate(all_data):
        if idx >= len(all_data) - MAX_RAW_DATA_CACHE:
            # Keep raw_player_data for recent files
            continue
        # Remove raw_player_data from older files
        if 'raw_player_data' in data:
            data['raw_player_data'] = None
    
    # Create DataFrame with all data but handle complex objects properly
    # Create a simple DataFrame first with only basic data types
    simple_data = []
    for data in all_data:
        row = {}
        for key, value in data.items():
            if key not in ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']:
                row[key] = value
        simple_data.append(row)
    
    df = pd.DataFrame(simple_data)
    
    # Now add complex objects as separate columns with object dtype
    complex_columns = ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']
    
    for col in complex_columns:
        df[col] = None  # Initialize with None
        df[col] = df[col].astype('object')  # Set as object dtype
        
        # Add the complex objects
        col_data = []
        for data in all_data:
            col_data.append(data.get(col, None))
        df[col] = col_data
    
    return df, new_parsed_count

def get_csv_files_from_directory(dir_path, owner, repo, github_token, headers):
    """Recursively get CSV files from a GitHub directory"""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{dir_path}"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        files = response.json()
        csv_files = []
        
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                # Store the full path as a string
                dir_path_str = str(dir_path) if dir_path is not None else ''
                file_path = f"{dir_path_str}/{f['name']}"
                csv_files.append(file_path)
            elif f.get('type') == 'dir':
                # Recursively check subdirectories
                sub_files = get_csv_files_from_directory(f"{dir_path}/{f['name']}", owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        return csv_files
    except Exception as e:
        print(f"Error getting files from directory {dir_path}: {e}")
        return []

def load_csv_files(st, force_reload=False):
    """Load and parse all CSV files from GitHub (no local files)"""
    if force_reload:
        load_csv_files_from_github.clear()
    
    df, new_parsed_count = load_csv_files_from_github()
    
    return df

def load_all_csv_files_without_limits():
    """Load and parse all CSV files from GitHub without any raw data limits"""
    try:
        # Import here to avoid circular imports
        import streamlit as st
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        import gzip
        from io import StringIO
        
        # Get GitHub credentials from centralized auth module
        github_token, csv_repo_url = get_github_credentials()
        
        if not github_token or not csv_repo_url:
            st.error("❌ GitHub credentials not configured")
            return pd.DataFrame(), 0
        
        # Extract owner and repo from URL
        if "/tree/" in csv_repo_url:
            repo_parts = csv_repo_url.split("/tree/")
            repo_base = repo_parts[0]
            branch = repo_parts[1] if len(repo_parts) > 1 else "main"
        else:
            repo_base = csv_repo_url
            branch = "main"
        
        # Extract owner and repo name
        url_parts = repo_base.replace("https://github.com/", "").split("/")
        if len(url_parts) < 2:
            st.error("❌ Invalid repository URL format")
            return pd.DataFrame(), 0
        
        owner, repo = url_parts[0], url_parts[1]
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            st.error(f"❌ GitHub API error: {response.status_code}")
            return pd.DataFrame(), 0
        
        files = response.json()
        csv_files = []
        
        # Get all CSV files
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                csv_files.append(f)
            elif f.get('type') == 'dir':
                sub_files = get_csv_files_from_directory(f['name'], owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        if not csv_files:
            st.warning("⚠️ No CSV files found")
            return pd.DataFrame(), 0
        
        # Load all files without any limits
        all_data = []
        new_parsed_count = 0
        
        def download_and_parse_file(file_info):
            """Download and parse a single file"""
            download_url = file_info.get('download_url')
            if not download_url:
                return None, file_info['name'], "No download URL"
            
            filename = file_info['name']
            
            try:
                csv_response = requests.get(download_url, headers=headers)
                
                if csv_response.status_code != 200:
                    return None, filename, f"Download failed: {csv_response.status_code}"
                
                # Check if file is compressed
                if filename.endswith('.gz'):
                    csv_content = StringIO(gzip.decompress(csv_response.content).decode('utf-8'))
                else:
                    csv_content = StringIO(csv_response.text)
                
                parsed_data = parse_single_file(csv_content, filename)
                
                return parsed_data, filename, None
            except Exception as e:
                return None, filename, str(e)
        
        # Download files in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {
                executor.submit(download_and_parse_file, file_info): file_info 
                for file_info in csv_files
            }
            
            for future in as_completed(future_to_file):
                parsed_data, filename, error = future.result()
                
                if error:
                    print(f"Error loading {filename}: {error}")
                elif parsed_data:
                    all_data.append(parsed_data)
                    new_parsed_count += 1
        
        # Sort by date
        all_data.sort(key=lambda x: x['date'])
        
        # Create DataFrame without removing raw_player_data (NO LIMITS)
        simple_data = []
        for data in all_data:
            row = {}
            for key, value in data.items():
                if key not in ['resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']:
                    row[key] = value
            simple_data.append(row)
        
        df = pd.DataFrame(simple_data)
        
        # Add all complex columns including raw_player_data (no limits)
        complex_columns = ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']
        
        for col in complex_columns:
            df[col] = None
            df[col] = df[col].astype('object')
            
            col_data = []
            for data in all_data:
                col_data.append(data.get(col, None))
            df[col] = col_data
        
        return df, new_parsed_count
        
    except Exception as e:
        st.error(f"❌ Error loading all CSV files: {e}")
        return pd.DataFrame(), 0

# ===== CLEAN THREE-LOADER IMPLEMENTATION =====

def load_csv_files_with_mode(st, database_mode='full', force_reload=False):
    """Load CSV files based on database mode selection"""
    if force_reload:
        # Clear cache if needed
        pass
    
    if database_mode == 'full':
        # Full database - current behavior
        df, new_parsed_count = load_full_database_clean(st)
        return df, new_parsed_count
    
    elif database_mode == 'partial':
        # Partial database - 3 points per day at equal intervals
        df, new_parsed_count = load_partial_database_clean(st)
        return df, new_parsed_count
    
    elif database_mode == 'local':
        # Local database - use cached files with sync
        df, new_parsed_count = load_local_database_clean(st)
        return df, new_parsed_count
    
    else:
        # Default to full mode
        df, new_parsed_count = load_full_database_clean(st)
        return df, new_parsed_count

def load_full_database_clean(st):
    """Load full database with original progress bar"""
    return load_csv_files_from_github()

def load_partial_database_clean(st):
    """Load partial database - 2 points per day with optimized API calls"""
    try:
        import requests
        import re
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Get GitHub credentials
        github_token, csv_repo_url = get_github_credentials()
        
        if not github_token or not csv_repo_url:
            st.error("❌ GitHub credentials not configured")
            return pd.DataFrame(), 0
        
        # Extract owner and repo from URL
        if "/tree/" in csv_repo_url:
            parts = csv_repo_url.split("/tree/")
            base_url = parts[0]
            path = parts[1] if len(parts) > 1 else ""
        else:
            base_url = csv_repo_url
            path = ""
        
        # Parse owner and repo
        url_parts = base_url.replace("https://github.com/", "").split("/")
        owner = url_parts[0]
        repo = url_parts[1]
        
        # GitHub API headers
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get date directories first
        st.sidebar.info("📡 Fetching directory structure...")
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            st.error(f"❌ Failed to access repository: {response.status_code}")
            return pd.DataFrame(), 0
        
        contents = response.json()
        date_dirs = []
        
        for item in contents:
            if item.get('type') == 'dir' and re.match(r'\d{2}\.\d{4}', item.get('name', '')):
                date_dirs.append(item['name'])
        
        st.sidebar.info(f"📅 Found {len(date_dirs)} date directories")
        
        # Get files from each date directory (scan all directories for proper 3-per-day selection)
        all_csv_files = []
        
        for date_dir in sorted(date_dirs):  # Sort all directories chronologically
            st.sidebar.info(f"📁 Scanning {date_dir}...")
            dir_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{date_dir}"
            
            try:
                dir_response = requests.get(dir_url, headers=headers, timeout=15)
                if dir_response.status_code == 200:
                    files = dir_response.json()
                    for f in files:
                        if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                            f_with_path = f.copy()
                            f_with_path['name'] = f"{date_dir}/{f['name']}"
                            f_with_path['download_url'] = f.get('download_url', '')
                            all_csv_files.append(f_with_path)
            except:
                continue
        
        st.sidebar.info(f"📊 Found {len(all_csv_files)} CSV files")
        
        if not all_csv_files:
            st.warning("⚠️ No CSV files found")
            return pd.DataFrame(), 0
        
        # Select 3 files per day
        selected_files = select_partial_files(all_csv_files)
        
        if not selected_files:
            st.warning("⚠️ No files selected for partial mode")
            return pd.DataFrame(), 0
        
        st.sidebar.info(f"🎯 Selected {len(selected_files)} files for partial mode")
        
        # Download selected files with progress bar
        return download_files_with_progress(selected_files, headers, "partial")
        
    except Exception as e:
        st.error(f"❌ Error loading partial database: {str(e)}")
        return pd.DataFrame(), 0

def load_local_database_clean(st):
    """Load local database with sync functionality"""
    import os
    import json
    from pathlib import Path
    
    try:
        # Create local data directory on desktop
        desktop_path = Path.home() / "Desktop" / "RoADashboard_Data"
        desktop_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (desktop_path / "csv_files").mkdir(exist_ok=True)
        (desktop_path / "cache").mkdir(exist_ok=True)
        
                
        # Check if we need to sync from GitHub
        sync_needed = st.session_state.get('sync_needed', False)
        force_sync = st.session_state.get('force_sync', False)
        
        # Check if local files exist - search recursively through all subdirectories
        local_csv_dir = desktop_path / "csv_files"
        
        # Search recursively for all CSV and CSV.GZ files in the entire RoADashboard_Data directory
        local_files = []
        for pattern in ["*.csv", "*.csv.gz"]:
            local_files.extend(desktop_path.rglob(pattern))
        
        # Filter out files that are not in csv_files subdirectory (to avoid system files)
        local_files = [f for f in local_files if "csv_files" in str(f)]
        
        # Create a set of local file paths for comparison
        local_file_paths = set()
        for f in local_files:
            # Convert to relative path from csv_files directory
            relative_path = str(f.relative_to(local_csv_dir))
            local_file_paths.add(relative_path)
        
                
        # Check GitHub for new files if we have local files
        if local_files and not sync_needed and not force_sync:
            # Store message container for cleanup
            github_check_msg = st.info("🔍 Checking GitHub for new files...")
            try:
                # Get GitHub credentials
                github_token, csv_repo_url = get_github_credentials()
                
                if github_token and csv_repo_url:
                    # Extract owner and repo from URL
                    if "/tree/" in csv_repo_url:
                        parts = csv_repo_url.split("/tree/")
                        base_url = parts[0]
                    else:
                        base_url = csv_repo_url
                    
                    url_parts = base_url.replace("https://github.com/", "").split("/")
                    owner, repo = url_parts[0], url_parts[1]
                    
                    # Get remote files
                    remote_files = get_remote_file_list(owner, repo, github_token)
                    remote_file_paths = set(remote_files)
                    
                    # Check for new or missing files
                    missing_files = remote_file_paths - local_file_paths
                    if missing_files:
                        st.info(f"📥 Found {len(missing_files)} new files on GitHub. Syncing...")
                        sync_needed = True
                    else:
                        # Store and clear the up-to-date message
                        up_to_date_msg = st.info("✅ Local database is up to date")
                        # Clear the GitHub check message after a delay
                        import time
                        time.sleep(2)
                        github_check_msg.empty()
                        time.sleep(1)
                        up_to_date_msg.empty()
                else:
                    st.warning("⚠️ GitHub credentials not configured for sync check")
            except Exception as e:
                st.warning(f"⚠️ Failed to check for updates: {e}")
        
        if not local_files or sync_needed or force_sync:
            if not local_files:
                st.info("📥 No local files found. Syncing from GitHub...")
            elif sync_needed:
                st.info("🔄 Sync needed. Updating from GitHub...")
            else:
                st.info("🔄 Force sync requested. Updating from GitHub...")
            
            # Sync files from GitHub
            if sync_needed:
                # Get list of missing files to download
                missing_files = remote_file_paths - local_file_paths
                success = sync_files_from_github(local_csv_dir, st, missing_files)
            else:
                # Full sync for first time or force sync
                success = sync_files_from_github(local_csv_dir, st)
            if not success:
                st.warning("⚠️ Failed to sync from GitHub. Falling back to full mode.")
                return load_full_database_clean(st)
            
            # Clear sync flags
            st.session_state.sync_needed = False
            st.session_state.force_sync = False
        
        # Load local files
        return load_local_files(local_csv_dir, st)
        
    except Exception as e:
        st.error(f"❌ Error in local database mode: {e}")
        st.info("💾 Falling back to full mode...")
        return load_full_database_clean(st)

def get_remote_file_list(owner, repo, github_token):
    """Get list of CSV files from GitHub repository"""
    try:
        import requests
        import re
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        files = response.json()
        csv_files = []
        
        # Check root directory for CSV files
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                csv_files.append(f['name'])
            elif f.get('type') == 'dir':
                # Recursively check subdirectories
                sub_files = get_csv_files_from_directory(f['name'], owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        return csv_files
        
    except Exception as e:
        return []

def get_remote_file_info(owner, repo, github_token):
    """Get file info dictionaries from GitHub repository for sync process"""
    try:
        import requests
        import re
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        files = response.json()
        csv_files = []
        
        # Check root directory for CSV files
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                csv_files.append(f)
            elif f.get('type') == 'dir':
                # Recursively check subdirectories
                sub_files = get_csv_file_info_from_directory(f['name'], owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        return csv_files
        
    except Exception as e:
        return []

def get_csv_file_info_from_directory(dir_path, owner, repo, github_token, headers):
    """Recursively get CSV file info dictionaries from a GitHub directory"""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{dir_path}"
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            return []
        
        files = response.json()
        csv_files = []
        
        for f in files:
            if (f.get('name', '').endswith('.csv') or f.get('name', '').endswith('.csv.gz')) and f.get('type') == 'file':
                # Store the full path in the name for identification
                f_with_path = f.copy()
                dir_path_str = str(dir_path) if dir_path is not None else ''
                f_with_path['name'] = f"{dir_path_str}/{f['name']}"
                f_with_path['download_url'] = f.get('download_url', '')
                csv_files.append(f_with_path)
            elif f.get('type') == 'dir':
                # Recursively check subdirectories
                sub_files = get_csv_file_info_from_directory(f"{dir_path}/{f['name']}", owner, repo, github_token, headers)
                csv_files.extend(sub_files)
        
        return csv_files
    except Exception as e:
        print(f"Error getting files from directory {dir_path}: {e}")
        return []

def sync_files_from_github(local_dir, st, missing_files=None):
    """Sync CSV files from GitHub to local directory
    Args:
        local_dir: Local directory to save files
        st: Streamlit instance
        missing_files: Optional list of specific files to download (for selective sync)
    """
    try:
        import requests
        import gzip
        from io import StringIO
        
        # Get GitHub credentials
        github_token, csv_repo_url = get_github_credentials()
        
        if not github_token or not csv_repo_url:
            st.error("❌ GitHub credentials not configured")
            return False
        
        # Extract owner and repo from URL
        if "/tree/" in csv_repo_url:
            repo_parts = csv_repo_url.split("/tree/")
            repo_base = repo_parts[0]
            branch = repo_parts[1] if len(repo_parts) > 1 else "main"
        else:
            repo_base = csv_repo_url
            branch = "main"
        
        # Extract owner and repo name
        url_parts = repo_base.replace("https://github.com/", "").split("/")
        if len(url_parts) < 2:
            st.error("❌ Invalid repository URL format")
            return False
        
        owner, repo = url_parts[0], url_parts[1]
        
        # GitHub API headers
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        # Get all CSV files from GitHub
        csv_files = get_remote_file_info(owner, repo, github_token)
        
        if not csv_files:
            st.warning("⚠️ No CSV files found in remote repository")
            return False
        
        # Filter files if missing_files is provided (selective sync)
        if missing_files is not None:
            missing_files_set = set(missing_files)
            filtered_files = []
            for file_info in csv_files:
                filename = file_info['name']
                if filename in missing_files_set:
                    filtered_files.append(file_info)
            csv_files = filtered_files
            st.info(f"📥 Downloading {len(csv_files)} new files...")
        
        # Download files concurrently with ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        downloaded_count = 0
        total_files = len(csv_files)
        failed_downloads = []
        
        # Page refresh detection using timestamp
        import time
        if 'download_start_time' not in st.session_state:
            st.session_state.download_start_time = 0
        
        # Set download start time (this will be unique per page load)
        current_start_time = time.time()
        st.session_state.download_start_time = current_start_time
        
        # Create progress bar and status container
        progress_bar = st.progress(0, text=f"📥 Downloading files... 0/{total_files}")
        status_text = st.empty()
        
        # Simple progress tracking (no threading locks)
        completed_count = 0
        should_stop = threading.Event()  # Event to signal thread termination
        
        def update_progress():
            """Update progress bar (simple version)"""
            if should_stop.is_set():
                return
            # Ensure progress never exceeds 1.0
            progress = min(completed_count / total_files, 1.0)
            progress_bar.progress(progress, text=f"📥 Downloading files... {completed_count}/{total_files}")
        
        def download_single_file(file_info):
            """Download a single file"""
            nonlocal completed_count, downloaded_count
            
            # Check if we should stop (page refresh)
            if should_stop.is_set():
                return None
            
            try:
                download_url = file_info.get('download_url')
                if not download_url:
                    return None
                
                filename = file_info['name']
                
                # Check stop signal again before starting download
                if should_stop.is_set():
                    return None
                
                # Handle subdirectories in filename
                if '/' in filename:
                    # Create subdirectory if needed
                    subdir = local_dir / '/'.join(filename.split('/')[:-1])
                    subdir.mkdir(exist_ok=True)
                    local_path = subdir / filename.split('/')[-1]
                else:
                    local_path = local_dir / filename
                
                response = requests.get(download_url, headers=headers, timeout=30)
                
                # Check stop signal after request
                if should_stop.is_set():
                    return None
                
                if response.status_code == 200:
                    if filename.endswith('.gz'):
                        # Check if file is actually gzipped by examining magic number
                        if len(response.content) >= 2 and response.content[:2] == b'\x1f\x8b':
                            # Proper gzip file - decompress it
                            content = gzip.decompress(response.content).decode('utf-8')
                            with open(local_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                        else:
                            # Not actually gzipped - save as plain text
                            content = response.text
                            with open(local_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                    else:
                        with open(local_path, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                    
                    # Thread-safe update - only increment downloaded_count, main thread handles completed_count
                    with download_lock:
                        downloaded_count += 1
                        # Update progress at intervals to avoid overwhelming Streamlit
                        if downloaded_count % progress_update_interval == 0 or downloaded_count == total_files:
                            update_progress()
                    
                    return filename
                else:
                    # Failed download - still count as completed
                    with download_lock:
                        if downloaded_count % progress_update_interval == 0 or downloaded_count == total_files:
                            update_progress()
                    return None
                    
            except Exception as e:
                # Exception - still count as completed
                with download_lock:
                    if downloaded_count % progress_update_interval == 0 or downloaded_count == total_files:
                        update_progress()
                return filename
        
        # No separate progress updater thread - will update from main thread only
        
        # Use simple sequential downloads for reliability with Streamlit
        st.info("🔄 Starting sequential downloads...")
        
        if not csv_files:
            st.warning("⚠️ No files to download!")
            return False
        
        for i, file_info in enumerate(csv_files):
            # Check if we should stop (page refresh detected)
            if should_stop.is_set():
                break
            
            # Check for page refresh using timestamp
            if abs(st.session_state.download_start_time - current_start_time) > 1.0:
                should_stop.set()
                progress_bar.empty()
                st.warning("⏸️ Download stopped due to page refresh")
                break
            
            filename = file_info['name']
            download_url = file_info.get('download_url')
            
            if not download_url:
                failed_downloads.append(filename)
                continue
            
            try:
                # Handle subdirectories
                if '/' in filename:
                    subdir = local_dir / '/'.join(filename.split('/')[:-1])
                    subdir.mkdir(exist_ok=True)
                    local_path = subdir / filename.split('/')[-1]
                else:
                    local_path = local_dir / filename
                
                # Download file with shorter timeout and retry logic
                response = None
                for attempt in range(3):  # 3 attempts
                    try:
                        response = requests.get(download_url, headers=headers, timeout=10)  # Reduced timeout
                        break
                    except requests.exceptions.Timeout:
                        if attempt == 2:  # Last attempt
                            raise
                        continue
                    except Exception as e:
                        if attempt == 2:  # Last attempt
                            raise
                        continue
                
                if response.status_code == 200:
                    if filename.endswith('.gz'):
                        # Check if file is actually gzipped by examining magic number
                        if len(response.content) >= 2 and response.content[:2] == b'\x1f\x8b':
                            # Proper gzip file - decompress it
                            content = gzip.decompress(response.content).decode('utf-8')
                            with open(local_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                        else:
                            # Not actually gzipped - save as plain text
                            content = response.text
                            with open(local_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                    else:
                        with open(local_path, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                    
                    downloaded_count += 1
                else:
                    failed_downloads.append(filename)
                
            except Exception as e:
                failed_downloads.append(filename)
                st.warning(f"⚠️ Failed to download {filename}: {e}")
            
            # Update progress (no lock)
            completed_count = i + 1
            update_progress()
            
            # Show progress every 10 files
            if (i + 1) % 10 == 0:
                st.info(f"📊 Downloaded {i + 1}/{total_files} files")
        
        # Show failed downloads if any
        if failed_downloads:
            with st.expander(f"⚠️ Failed downloads ({len(failed_downloads)} files)"):
                for filename in failed_downloads[:10]:  # Show first 10
                    st.write(f"• {filename}")
                if len(failed_downloads) > 10:
                    st.write(f"... and {len(failed_downloads) - 10} more files")
        
        # Clear progress bar
        progress_bar.empty()
        
        st.success(f"✅ Successfully synced {downloaded_count} files to local directory")
        return True
        
    except Exception as e:
        st.error(f"❌ Error syncing from GitHub: {e}")
        return False

def load_local_files(local_dir, st):
    """Load and parse CSV files from local directory with optimized performance"""
    try:
        import gzip
        from io import StringIO
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        # Get all CSV files using the same recursive logic as main function
        csv_files = []
        for pattern in ["*.csv", "*.csv.gz"]:
            csv_files.extend(local_dir.rglob(pattern))
        
        if not csv_files:
            st.warning("⚠️ No local CSV files found")
            return pd.DataFrame(), 0
        
        # Clear any existing UI elements
        st.empty()
        
        # Optimized parsing with batch processing
        all_data = []
        new_parsed_count = 0
        failed_files = []
        total_files = len(csv_files)
        
        # Create progress tracking
        progress_bar = st.progress(0, text=f"🏰 Parsing files... 0/{total_files}")
        
        # Batch processing for better performance
        batch_size = 50
        for batch_start in range(0, total_files, batch_size):
            batch_end = min(batch_start + batch_size, total_files)
            batch_files = csv_files[batch_start:batch_end]
            
            # Process batch with individual file tracking
            for file_idx, file_path in enumerate(batch_files):
                try:
                    # Optimized file reading
                    if file_path.name.endswith('.gz'):
                        # Check if file is actually gzipped by examining magic number
                        with open(file_path, 'rb') as f:
                            magic_bytes = f.read(2)
                        
                        if len(magic_bytes) >= 2 and magic_bytes == b'\x1f\x8b':
                            # Proper gzip file - decompress it
                            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                                content = f.read()
                        else:
                            # Not actually gzipped - read as plain text
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    
                    # Parse the file
                    parsed_data = parse_single_file(StringIO(content), file_path.name)
                    if parsed_data:
                        all_data.append(parsed_data)
                        new_parsed_count += 1
                        
                except Exception as e:
                    failed_files.append((file_path.name, str(e)))
                
                # Update progress for each file for better user experience
                current_file_count = batch_start + file_idx + 1
                progress = min(current_file_count / total_files, 1.0)
                progress_bar.progress(progress, text=f"🏰 Parsing files... {current_file_count}/{total_files}")
        
        # Clear progress bar
        progress_bar.empty()
        
        # Show failed files if any (but don't stop the process)
        if failed_files and len(failed_files) < 10:  # Only show if few failures
            with st.expander(f"⚠️ Failed to parse {len(failed_files)} files"):
                for filename, error in failed_files:
                    st.write(f"• {filename}: {error}")
        
        if not all_data:
            st.warning("⚠️ No data could be parsed from local files")
            return pd.DataFrame(), 0
        
        # Convert to DataFrame
        df, _ = convert_data_to_dataframe(all_data)
        
        # Store success message for cleanup
        loaded_msg = st.success(f"✅ Loaded {len(all_data)} files from local directory")
        
        # Clear the success message after a delay
        import time
        time.sleep(2)
        loaded_msg.empty()
        
        return df, new_parsed_count
        
    except Exception as e:
        st.error(f"❌ Error loading local files: {e}")
        return pd.DataFrame(), 0

def convert_data_to_dataframe(all_data):
    """Convert parsed data to DataFrame format"""
    try:
        # Create simple data first
        simple_data = []
        for data in all_data:
            if data is None:
                continue
            row = {}
            for key, value in data.items():
                if key not in ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']:
                    row[key] = value
            simple_data.append(row)
        
        df = pd.DataFrame(simple_data)
        
        # Add complex columns
        complex_columns = ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']
        
        for col in complex_columns:
            df[col] = None
            df[col] = df[col].astype('object')
            
            col_data = []
            for data in all_data:
                if data is not None:
                    col_data.append(data.get(col, None))
            df[col] = col_data
        
        return df, len(all_data)
        
    except Exception as e:
        st.error(f"❌ Error converting data to DataFrame: {e}")
        return pd.DataFrame(), 0

def select_partial_files(csv_files):
    """Select files for partial mode - all files from last 24 hours + 2 points per day for older data"""
    import re
    from datetime import datetime, timedelta
    
    # Group files by date
    files_by_date = {}
    files_with_datetime = []
    
    # Get current time for 24-hour comparison
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    for file_info in csv_files:
        filename = file_info['name']
        
        # Extract date from filename - match actual patterns in repository
        date_match = None
        if "comprehensive_player_data" in filename:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{6})', filename)
        elif "realm_Ruby_analytics" in filename:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{6})', filename)
        elif "Ruby_" in filename and ".csv.gz" in filename:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if date_match:
                # Convert HH-MM-SS to HHMMSS format
                time_str = date_match.group(2).replace('-', '')
                date_match = (date_match.group(1), time_str)
        
        if date_match:
            if isinstance(date_match, tuple):
                date_str, time_str = date_match[0], date_match[1]
            else:
                date_str = date_match.group(1)
                time_str = date_match.group(2)
            
            # Parse the full datetime
            try:
                # Parse time based on format
                if len(time_str) == 6:  # HHMMSS format
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])
                else:  # Handle other formats if needed
                    hour, minute, second = 0, 0, 0
                
                file_datetime = datetime.strptime(date_str, "%Y-%m-%d")
                file_datetime = file_datetime.replace(hour=hour, minute=minute, second=second)
                
                files_with_datetime.append({
                    'file_info': file_info,
                    'datetime': file_datetime,
                    'date_str': date_str,
                    'time_str': time_str,
                    'filename': filename
                })
                
                # Group by date for older files selection
                if date_str not in files_by_date:
                    files_by_date[date_str] = []
                
                files_by_date[date_str].append({
                    'file_info': file_info,
                    'time_str': time_str,
                    'filename': filename,
                    'datetime': file_datetime
                })
                
            except ValueError:
                # Skip files with invalid dates
                continue
    
    # Select files
    selected_files = []
    recent_files_selected = set()
    
    # First, select ALL files from the last 24 hours
    for file_data in files_with_datetime:
        if file_data['datetime'] >= twenty_four_hours_ago:
            selected_files.append(file_data['file_info'])
            recent_files_selected.add(file_data['filename'])
    
    # Then, select 2 files per day for older data (older than 24 hours)
    for date_str, files in files_by_date.items():
        # Filter out files already selected (from last 24 hours)
        older_files = [f for f in files if f['filename'] not in recent_files_selected]
        
        if not older_files:
            continue
            
        if len(older_files) <= 2:
            # If 2 or fewer older files, take all of them
            selected_files.extend([f['file_info'] for f in older_files])
        else:
            # Sort older files by time and select 2 at equal intervals
            older_files.sort(key=lambda x: x['time_str'])
            
            # Calculate intervals for 2 points
            interval = len(older_files) // 2
            selected_indices = [0, interval] if interval > 0 else [0, -1]
            
            for idx in selected_indices:
                if idx < len(older_files):
                    selected_files.append(older_files[idx]['file_info'])
    
    return selected_files


def download_files_with_progress(files, headers, mode="full"):
    """Download files with progress bar - match full database style exactly"""
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    def format_bytes(bytes_count):
        """Format bytes to human readable format"""
        if bytes_count == 0:
            return "0.00 KB"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} TB"
    
    def download_and_parse_file(file_info):
        """Download and parse a single file"""
        try:
            download_url = file_info.get('download_url')
            if not download_url:
                return None, file_info['name'], "No download URL", 0, 0, 0
            
            start_time = time.time()
            response = requests.get(download_url, headers=headers, timeout=30)
            download_time = time.time() - start_time
            
            if response.status_code != 200:
                return None, file_info['name'], f"HTTP {response.status_code}", 0, download_time, 0
            
            bytes_downloaded = len(response.content)
            
            # Parse the content
            parse_start = time.time()
            if file_info['name'].endswith('.gz'):
                csv_content = StringIO(gzip.decompress(response.content).decode('utf-8'))
            else:
                csv_content = StringIO(response.text)
            
            # Use the same parsing as full database for consistency
            parsed_data = parse_single_file(csv_content, file_info['name'])
            parse_time = time.time() - parse_start
            
            return parsed_data, file_info['name'], None, bytes_downloaded, download_time, parse_time
            
        except Exception as e:
            return None, file_info['name'], str(e), 0, 0, 0
    
    # Use st.spinner which automatically disappears when done - match full database style
    with st.spinner("🏰 Loading Realm Data..."):
        # Overall progress bar - match full database style
        overall_progress = st.progress(0)
        status_text = st.empty()
        recent_activity = st.empty()
        
        # Download files in parallel - match full database style
        all_data = []
        new_parsed_count = 0
        total_files = len(files)
        total_bytes_downloaded = 0
        recent_files = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(download_and_parse_file, file_info): file_info for file_info in files}
            
            completed_count = 0
            for future in as_completed(future_to_file):
                parsed_data, filename, error, bytes_downloaded, download_time, parse_time = future.result()
                completed_count += 1
                total_bytes_downloaded += bytes_downloaded
                
                # Update progress - match full database style exactly
                progress = completed_count / total_files
                overall_progress.progress(progress)
                status_text.markdown(f"**Progress: {completed_count}/{total_files} files ({progress*100:.1f}%) | Downloaded: {format_bytes(total_bytes_downloaded)}**")
                
                # Update recent activity - match full database style
                short_name = filename.split('/')[-1]
                if error:
                    recent_files.insert(0, f"❌ {short_name} - {error}")
                elif parsed_data:
                    all_data.append(parsed_data)
                    new_parsed_count += 1
                    recent_files.insert(0, f"✅ {short_name} ({format_bytes(bytes_downloaded)}) - DL: {download_time:.2f}s, Parse: {parse_time:.2f}s")
                else:
                    recent_files.insert(0, f"⚠️ {short_name} - No data")
                
                # Keep only last 5 activities and display
                recent_files = recent_files[:5]
                recent_activity.markdown("**Recent Activity:**\n" + " • ".join(recent_files))
        
        # Clear progress indicators
        overall_progress.empty()
        status_text.empty()
        recent_activity.empty()
        
        # Combine all data - handle both DataFrame and dict formats
        if all_data:
            # Check if data is in dictionary format (from parse_comprehensive_csv_from_string)
            if all_data and isinstance(all_data[0], dict):
                # Convert dictionaries to DataFrame format like the original loader
                simple_data = []
                for data in all_data:
                    if data is None:
                        continue
                    row = {}
                    for key, value in data.items():
                        if key not in ['resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']:
                            row[key] = value
                    simple_data.append(row)
                
                df = pd.DataFrame(simple_data)
                
                # Add all complex columns including raw_player_data
                complex_columns = ['raw_player_data', 'resources', 'items', 'buildings_data', 'troops_data', 'skins_data', 'quests_data', 'ceasefire_data']
                
                for col in complex_columns:
                    df[col] = None
                    df[col] = df[col].astype('object')
                    
                    col_data = []
                    for data in all_data:
                        if data is not None:
                            col_data.append(data.get(col, None))
                    df[col] = col_data
                
                combined_df = df
            else:
                # If data is already DataFrame format, concatenate normally
                combined_df = pd.concat(all_data, ignore_index=True)
            
            return combined_df, new_parsed_count
        else:
            st.warning("⚠️ No data loaded")
            return pd.DataFrame(), 0
