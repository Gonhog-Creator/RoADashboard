"""Data loading module for CSV files from GitHub"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import requests
from io import StringIO

def calculate_daily_rate(values, dates):
    """Calculate true daily rate based on time differences between reports"""
    if len(values) < 2:
        return [0] * len(values)
    
    daily_rates = []
    
    for i in range(len(values)):
        if i == 0:
            daily_rates.append(0)  # First report has no rate
        else:
            current_value = values[i]
            previous_value = values[i-1]
            current_time = dates[i]
            previous_time = dates[i-1]
            
            # Calculate time difference in days
            time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
            
            if time_diff > 0.1:  # Only calculate rate if time difference is significant
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return daily_rates

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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_csv_files_from_github():
    """Load CSV files directly from GitHub API (no local files)"""
    try:
        # Try to get GitHub credentials from secrets
        github_token = None
        csv_repo_url = None
        
        # Check for secrets in multiple possible locations
        if hasattr(st, 'secrets'):
            all_secrets = dict(st.secrets)
            
            # Try root level first
            if "github_token" in all_secrets:
                github_token = st.secrets["github_token"]
            if "csv_repo_url" in all_secrets:
                csv_repo_url = st.secrets["csv_repo_url"]
            
            # Try admin_users level
            if not github_token and "admin_users" in all_secrets:
                admin_users = dict(st.secrets["admin_users"])
                if "github_token" in admin_users:
                    github_token = admin_users["github_token"]
                if "csv_repo_url" in admin_users:
                    csv_repo_url = admin_users["csv_repo_url"]
        
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
            if f.get('name', '').endswith('.csv') and f.get('type') == 'file':
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
        
        # Show progress bar
        progress_bar = st.progress(0, text="Loading CSV files from GitHub...")
        status_text = st.empty()
        
        for idx, file_info in enumerate(csv_files):
            try:
                progress = (idx + 1) / len(csv_files)
                progress_bar.progress(progress, text=f"Loading file {idx + 1} of {len(csv_files)}: {file_info.get('name', 'unknown')}")
                
                download_url = file_info.get('download_url')
                if not download_url:
                    continue
                
                filename = file_info['name']
                
                # Check if file is in memory cache
                if filename in memory_cache:
                    # Use cached data from memory
                    all_data.append(memory_cache[filename]['data'])
                    status_text.text(f"✅ Using cached: {filename}")
                else:
                    # Need to download and parse this file
                    status_text.text(f"⬇️ Downloading: {filename}")
                    csv_response = requests.get(download_url, headers=headers)
                    
                    if csv_response.status_code == 200:
                        status_text.text(f"📊 Parsing: {filename}")
                        # Parse CSV content directly from memory
                        csv_content = StringIO(csv_response.text)
                        parsed_data = parse_single_file(csv_content, filename)
                        
                        if parsed_data:
                            # Store in memory cache
                            memory_cache[filename] = {
                                'data': parsed_data
                            }
                            all_data.append(parsed_data)
                            new_parsed_count += 1
                            status_text.text(f"✅ Loaded: {filename}")
                    else:
                        status_text.text(f"❌ Failed to download: {filename}")
                        
            except Exception as e:
                status_text.text(f"⚠️ Error processing {file_info.get('name', 'unknown')}: {e}")
                continue
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
    
    except Exception as e:
        st.error(f"❌ Error loading from GitHub: {e}")
        return pd.DataFrame(), 0
    
    # Sort by date
    all_data.sort(key=lambda x: x['date'])
    
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
            if f.get('name', '').endswith('.csv') and f.get('type') == 'file':
                # Store the full path in the name for identification
                f_with_path = f.copy()
                # Ensure dir_path is a string
                dir_path_str = str(dir_path) if dir_path is not None else ''
                f_with_path['name'] = f"{dir_path_str}/{f['name']}"
                f_with_path['download_url'] = f.get('download_url', '')
                csv_files.append(f_with_path)
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
