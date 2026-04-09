import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import glob
import requests
from Tabs.speedups import create_speedups_tab
from Tabs.resources import create_resources_tab
from Tabs.overview import create_overview_tab
from Tabs.power import create_power_tab
from Tabs.items import create_items_tab
from Tabs.troops import create_troops_tab
from Tabs.buildings import create_buildings_tab
from Tabs.skins import create_skins_tab
from Tabs.quests_research import create_quests_research_tab
from Tabs.ceasefire import create_ceasefire_tab

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

def get_realm_name(realm_id):
    """Convert realm ID to realm name"""
    realm_mapping = {
        # Add realm ID to name mappings here
        # Current realm (actual UUID from CSV)
        'ad5fb84b-1cb6-46ec-bc45-58dd610e6d22': 'Ruby',
        # Legacy mappings for compatibility
        '1': 'Ruby',
        'ruby': 'Ruby',
        'Ruby': 'Ruby',
        # Add more realms as needed
        # '2': 'Emerald',
        # '3': 'Diamond',
        # '4': 'Sapphire',
    }
    
    # Handle both numeric and string realm IDs
    if str(realm_id).lower() in realm_mapping:
        return realm_mapping[str(realm_id).lower()]
    else:
        # Return the ID as-is if not mapped
        return str(realm_id)

def process_player_creation_dates(filtered_df):
    """Process player creation dates to generate accurate player count over time"""
    if filtered_df.empty:
        return filtered_df
    
    # Find the latest comprehensive data file (most recent date)
    latest_comprehensive_data = None
    latest_date = None
    
    for _, row in filtered_df.iterrows():
        if 'raw_player_data' in row and row['raw_player_data'] is not None:
            # Check if this is a comprehensive data file
            if hasattr(row, 'filename') and 'comprehensive_player_data' in str(getattr(row, 'filename', '')):
                # Use the most recent comprehensive file
                if latest_date is None or row['date'] > latest_date:
                    latest_date = row['date']
                    latest_comprehensive_data = row['raw_player_data']
            elif latest_comprehensive_data is None:
                # Fallback: use the first comprehensive data found
                latest_comprehensive_data = row['raw_player_data']
                latest_date = row['date']
    
    if latest_comprehensive_data is None:
        return filtered_df  # Return original if no comprehensive data
    
    player_data = latest_comprehensive_data
    
    # Check for creation date columns
    date_column = None
    if 'created_at' in player_data.columns:
        date_column = 'created_at'
    elif 'user_created_at' in player_data.columns:
        date_column = 'user_created_at'
    
    if date_column is None:
        return filtered_df  # Return original if no date columns
    
    # Extract and process creation dates from the latest comprehensive file
    player_dates = pd.to_datetime(player_data[date_column], errors='coerce').dropna()
    
    if player_dates.empty:
        return filtered_df
    
    # Create cumulative player counts over time
    min_date = player_dates.min()
    max_date = player_dates.max()
    
    # Start from one day before the earliest player creation date to show 0 players initially
    start_date = min_date - pd.Timedelta(days=1)
    
    # End at today's date
    today = pd.Timestamp.now().normalize()
    
    # Use the full range from earliest creation to today
    overall_min_date = start_date
    overall_max_date = today
    
    date_range = pd.date_range(start=overall_min_date, end=overall_max_date, freq='D')
    
    cumulative_counts = []
    for date in date_range:
        count = (player_dates <= date).sum()
        cumulative_counts.append(count)
    
    # Create new dataframe with accurate player counts
    player_timeline = pd.DataFrame({
        'date': date_range,
        'total_players': cumulative_counts
    })
    
    # Replace the total_players in filtered_df with accurate data
    updated_df = filtered_df.copy()
    
    # Update each row's total_players based on the closest date in player_timeline
    for idx, row in updated_df.iterrows():
        closest_date_idx = (player_timeline['date'] - row['date']).abs().argmin()
        closest_date = player_timeline.iloc[closest_date_idx]
        updated_df.at[idx, 'total_players'] = closest_date['total_players']
    
    return updated_df

def save_parsed_cache(cache):
    """Save cache of parsed files"""
    cache_file = "parsed_files_cache.json"
    try:
        # Convert datetime objects to strings for JSON serialization
        serializable_cache = {}
        for filename, file_info in cache.items():
            # Create a deep copy and convert datetime objects
            data_copy = {}
            for key, value in file_info['data'].items():
                if isinstance(value, datetime):
                    data_copy[key] = value.isoformat()
                else:
                    data_copy[key] = value
            
            serializable_cache[filename] = {
                'data': data_copy,
                'mtime': file_info['mtime']
            }
        
        with open(cache_file, 'w') as f:
            json.dump(serializable_cache, f)
    except Exception as e:
        st.warning(f"Could not save cache: {e}")

def load_parsed_cache():
    """Load cache of previously parsed files"""
    cache_file = "parsed_files_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Convert datetime strings back to datetime objects
            for filename, file_info in cache_data.items():
                for key, value in file_info['data'].items():
                    if key == 'date' and isinstance(value, str):
                        file_info['data'][key] = datetime.fromisoformat(value)
            
            return cache_data
        except Exception as e:
            st.warning(f"Could not load cache: {e}")
            return {}
    return {}

def parse_comprehensive_csv(file_path):
    """Parse the new comprehensive_player_data.csv format"""
    try:
        # Extract date from filename - assume format: comprehensive_player_data_YYYY-MM-DD_HH-MM-SS.csv
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
        
        # Aggregate items data
        items = {}
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
        buildings_data = {}
        if 'buildings_metadata' in df.columns:
            # Parse buildings metadata JSON
            for _, row in df.iterrows():
                if pd.notna(row['buildings_metadata']):
                    try:
                        buildings_info = eval(row['buildings_metadata'])  # Convert string to dict
                        for city_info in buildings_info.values():
                            if ':' in city_info:
                                buildings_list = city_info.split(':')[1].strip('[]')
                                for building in buildings_list.split(','):
                                    if ':' in building:
                                        building_name, level = building.split(':')
                                        building_name = building_name.strip()
                                        level = int(level.strip())
                                        if building_name not in buildings_data:
                                            buildings_data[building_name] = []
                                        buildings_data[building_name].append(level)
                    except:
                        continue
        
        # Parse troops data (assuming it's in a column)
        troops_data = {}
        troops_columns = [col for col in df.columns if 'troop' in col.lower()]
        for col in troops_columns:
            troops_data[col] = df[col].fillna(0).sum()
        
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
            # Check for ceasefire effects (prevent_attacks)
            ceasefire_effects = ['server:prevent_attacks:1', 'armistice_agreement:prevent_attacks:1']
            df['has_ceasefire'] = df['active_effects'].fillna('').astype(str).apply(
                lambda x: any(effect in x for effect in ceasefire_effects)
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
        st.error(f"Error parsing comprehensive CSV {file_path}: {e}")
        return None

def parse_single_file(file_path):
    """Parse a single CSV file and return the data"""
    try:
        # Check if this is a comprehensive CSV file
        if "comprehensive_player_data" in os.path.basename(file_path):
            return parse_comprehensive_csv(file_path)
        
        # Extract date from filename (handle both formats)
        filename = os.path.basename(file_path)
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
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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

def sync_from_github():
    """Sync CSV files from GitHub repository"""
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
        
        # API URL for repository contents
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Streamlit-Dashboard"
        }
        
        st.write("🔍 Syncing from GitHub repository...")
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            files = response.json()
            csv_files = [f for f in files if f.get('name', '').endswith('.csv')]
            
            if not csv_files:
                st.warning("⚠️ No CSV files found in remote repository")
                return False
            
            # Ensure Daily Reports directory exists
            os.makedirs("Daily Reports", exist_ok=True)
            
            synced_count = 0
            for file_info in csv_files:
                try:
                    download_url = file_info.get('download_url')
                    if not download_url:
                        continue
                    
                    csv_response = requests.get(download_url, headers=headers)
                    
                    if csv_response.status_code == 200:
                        filename = file_info['name']
                        file_path = f"Daily Reports/{filename}"
                        
                        # Write the file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(csv_response.text)
                        
                        synced_count += 1
                        st.success(f"✅ Synced {filename}")
                    else:
                        st.error(f"❌ Failed to download {file_info['name']}")
                        
                except Exception as e:
                    st.error(f"❌ Error processing {file_info.get('name', 'unknown')}: {e}")
            
            if synced_count > 0:
                st.success(f"🎉 Successfully synced {synced_count} CSV files from GitHub!")
                return True
            else:
                st.error("❌ No files were successfully synced")
                return False
                
        else:
            st.error(f"❌ GitHub API error: {response.status_code}")
            return False
            
    except Exception as e:
        st.error(f"❌ Error syncing from GitHub: {e}")
        return False

st.set_page_config(page_title="Realm Analytics Dashboard", layout="wide")

def load_csv_files_incremental():
    """Load and parse CSV files - memory only (no file caching for security)"""
    csv_files = glob.glob("Daily Reports/*.csv")
    
    # Sort files by modification time (newest first)
    csv_files = sorted(csv_files, key=os.path.getmtime, reverse=True)
    
    # Use session state for in-memory cache only (no file storage)
    if 'parsed_files_memory_cache' not in st.session_state:
        st.session_state.parsed_files_memory_cache = {}
    
    memory_cache = st.session_state.parsed_files_memory_cache
    new_parsed_count = 0
    all_data = []
    
    for file_path in csv_files:
        file_mtime = os.path.getmtime(file_path)
        filename = os.path.basename(file_path)
        
        # Check if file is in memory cache and hasn't been modified
        if filename in memory_cache and memory_cache[filename]['mtime'] == file_mtime:
            # Use cached data from memory
            all_data.append(memory_cache[filename]['data'])
        else:
            # Need to parse this file
            parsed_data = parse_single_file(file_path)
            if parsed_data:
                # Store in memory cache only (no file storage)
                memory_cache[filename] = {
                    'data': parsed_data,
                    'mtime': file_mtime
                }
                all_data.append(parsed_data)
                new_parsed_count += 1
    
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

# Fallback to original function for compatibility
def load_csv_files():
    """Load and parse all CSV files from Daily Reports folder (legacy function)"""
    df, new_parsed_count = load_csv_files_incremental()
    
    # Show toast for new files (outside of cached function)
    if new_parsed_count > 0:
        st.toast(f"📊 Processed {new_parsed_count} new/updated files", icon="✅")
    
    return df

# Load data first
df = load_csv_files()

# Create header with title and realm name in top-right
col1, col2 = st.columns([3, 1])

with col1:
    st.title("🏰 Realm Analytics Dashboard")

with col2:
    if not df.empty:
        latest_row = df.iloc[-1]
        # Handle different realm name fields
        if 'realm_name' in latest_row:
            realm_name = latest_row['realm_name']
        elif 'realm_id' in latest_row:
            realm_name = get_realm_name(latest_row['realm_id'])
        else:
            realm_name = 'Unknown Realm'
        st.markdown(f"**Realm:** {realm_name}")

if df.empty:
    st.error("No CSV files found in Daily Reports folder!")
else:
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Latest report info
    if not df.empty:
        latest_report = df.iloc[-1]
        latest_date = latest_report['date']
        latest_date_str = latest_date.strftime("%Y-%m-%d %H:%M:%S")
        # Handle different realm name fields
        if 'realm_name' in latest_report:
            realm_name = latest_report['realm_name']
        elif 'realm_id' in latest_report:
            realm_name = get_realm_name(latest_report['realm_id'])
        else:
            realm_name = 'Unknown Realm'
        
        st.sidebar.markdown("### 📊 Latest Report")
        st.sidebar.markdown(f"**Date:** {latest_date_str}")
        st.sidebar.markdown(f"**Realm:** {realm_name}")
        st.sidebar.markdown(f"**Total Reports:** {len(df)}")
    
    # Date range filter
    df['date'] = pd.to_datetime(df['date'])
    min_date = df['date'].min().date()
    max_date = df['date'].max().date()
    
    selected_date_range = st.sidebar.date_input(
        "Select Date Range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Filter data by date range
    if len(selected_date_range) == 2:
        start_date = pd.to_datetime(selected_date_range[0])
        # Add 1 day to end_date to include the entire end date
        end_date = pd.to_datetime(selected_date_range[1]) + pd.Timedelta(days=1)
        
        filtered_df = df[(df['date'] >= start_date) & (df['date'] < end_date)]
    else:
        filtered_df = df
    
    # Sort filtered data by date to ensure chronological order in charts
    filtered_df = filtered_df.sort_values('date')
    
    # Process player creation dates for accurate player counts
    filtered_df = process_player_creation_dates(filtered_df)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs(["Overview", "Player Count", "Resources", "Power", "Speedups", "Items", "Troops", "Buildings", "Skins", "Quests & Research", "Ceasefire"])
    
    with tab1:
        create_overview_tab(filtered_df)
    
    with tab2:
        # Weekly and Monthly Growth
        st.markdown("### 📊 Growth Analysis")
        
        # Calculate weekly and monthly growth
        if len(filtered_df) >= 2:
            sorted_df = filtered_df.sort_values('date')
            latest_date = sorted_df.iloc[-1]['date']
            latest_players = sorted_df.iloc[-1]['total_players']
            
            # Calculate true daily growth rate using time differences
            player_values = sorted_df['total_players'].tolist()
            player_dates = sorted_df['date'].tolist()
            daily_rates = calculate_daily_rate(player_values, player_dates)
            
            daily_growth = daily_rates[-1] if daily_rates else 0
            prev_day_players = sorted_df.iloc[-2]['total_players']
            if prev_day_players > 0:
                daily_percent = (daily_growth / prev_day_players) * 100
            else:
                daily_percent = 100.0 if daily_growth > 0 else 0.0
            
            # Weekly growth (7 days ago)
            week_ago = latest_date - pd.Timedelta(days=7)
            week_data = sorted_df[sorted_df['date'] >= week_ago]
            if len(week_data) >= 2:
                week_ago_players = week_data.iloc[0]['total_players']
                if week_ago_players > 0:
                    weekly_growth = latest_players - week_ago_players
                    weekly_percent = (weekly_growth / week_ago_players) * 100
                else:
                    weekly_growth = latest_players
                    weekly_percent = 100.0
            else:
                weekly_growth = 0
                weekly_percent = 0.0
            
            # Monthly growth (30 days ago)
            month_ago = latest_date - pd.Timedelta(days=30)
            month_data = sorted_df[sorted_df['date'] >= month_ago]
            if len(month_data) >= 2:
                month_ago_players = month_data.iloc[0]['total_players']
                if month_ago_players > 0:
                    monthly_growth = latest_players - month_ago_players
                    monthly_percent = (monthly_growth / month_ago_players) * 100
                else:
                    monthly_growth = latest_players
                    monthly_percent = 100.0
            else:
                monthly_growth = 0
                monthly_percent = 0.0
            
            # Display all growth metrics in a single row
            growth_col1, growth_col2, growth_col3, growth_col4 = st.columns(4)
            
            with growth_col1:
                st.metric(
                    "👥 Total Players", 
                    f"{latest_players:,}"
                )
                
            with growth_col2:
                st.metric(
                    "📅 Daily Growth", 
                    f"{int(daily_growth):,}/day",
                    f"{daily_percent:.1f}%"
                )
                
            with growth_col3:
                st.metric(
                    "📆 Weekly Growth", 
                    f"{weekly_growth:,}",
                    f"{weekly_percent:.1f}%"
                )
                
            with growth_col4:
                st.metric(
                    "📅 Monthly Growth", 
                    f"{monthly_growth:,}",
                    f"{monthly_percent:.1f}%"
                )
        else:
            st.info("Not enough data for growth analysis (need at least 2 data points)")
        
        st.markdown("---")
        st.subheader("📈 Player Count Over Time")
        if not filtered_df.empty:
            # Create the entire graph from the latest CSV file
            # Find the latest comprehensive data file
            latest_comprehensive_data = None
            latest_date = None
            
            for _, row in filtered_df.iterrows():
                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                    if hasattr(row, 'filename') and 'comprehensive_player_data' in str(getattr(row, 'filename', '')):
                        if latest_date is None or row['date'] > latest_date:
                            latest_date = row['date']
                            latest_comprehensive_data = row['raw_player_data']
                    elif latest_comprehensive_data is None:
                        latest_comprehensive_data = row['raw_player_data']
                        latest_date = row['date']
            
            if latest_comprehensive_data is not None:
                player_data = latest_comprehensive_data
                
                # Check for creation date columns
                date_column = None
                if 'created_at' in player_data.columns:
                    date_column = 'created_at'
                elif 'user_created_at' in player_data.columns:
                    date_column = 'user_created_at'
                
                if date_column is not None:
                    # Extract and process creation dates from the latest comprehensive file
                    player_dates = pd.to_datetime(player_data[date_column], errors='coerce').dropna()
                    
                    if not player_dates.empty:
                        # Sort player creation dates
                        sorted_dates = player_dates.sort_values()
                        
                        # Create cumulative counts at each player creation point
                        # Start with 0 players at the earliest creation date - 1 day
                        start_date = sorted_dates.min() - pd.Timedelta(days=1)
                        
                        # Create arrays for the chart
                        chart_dates = [start_date]
                        chart_counts = [0]
                        
                        # Add a point for each player creation date
                        for i, date in enumerate(sorted_dates):
                            chart_dates.append(date)
                            chart_counts.append(i + 1)  # i+1 because we want cumulative count
                        
                        # Add today's date with final count to extend the line to present
                        today = pd.Timestamp.now().normalize()
                        if today > sorted_dates.max():
                            chart_dates.append(today)
                            chart_counts.append(len(sorted_dates))
                        
                        # Create dataframe for the chart
                        chart_df = pd.DataFrame({
                            'date': chart_dates,
                            'total_players': chart_counts
                        })
                        
                        # Create smooth line chart without markers for cleaner look
                        fig_players = px.line(
                            chart_df, 
                            x='date', 
                            y='total_players',
                            title='Total Players Over Time',
                            markers=False  # Remove markers for smoother line
                        )
                        fig_players.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Total Players",
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_players, use_container_width=True)
                    else:
                        st.warning("No valid player creation dates found in the latest comprehensive data file")
                else:
                    st.warning("No creation date column found in the latest comprehensive data file")
            else:
                st.warning("No comprehensive data file found")
    
    with tab3:
        create_resources_tab(filtered_df)
    
    with tab4:
        create_power_tab(filtered_df)
    
    with tab5:
        create_speedups_tab(filtered_df)
    
    with tab6:
        create_items_tab(filtered_df)
    
    with tab7:
        create_troops_tab(filtered_df)
    
    with tab8:
        create_buildings_tab(filtered_df)
    
    with tab9:
        create_skins_tab(filtered_df)
    
    with tab10:
        create_quests_research_tab(filtered_df)
    
    with tab11:
        create_ceasefire_tab(filtered_df)
    
    # Data table
    with st.expander("📋 Raw Data"):
        # Create a copy of filtered_df to avoid modifying original
        raw_data_df = filtered_df.copy()
        
        # Add resource columns
        main_resources = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        
        for resource in main_resources:
            raw_data_df[f'{resource.title()}Sum'] = raw_data_df['resources'].apply(
                lambda x: x.get(resource, 0) if isinstance(x, dict) else 0
            )
        
        # Add power columns
        raw_data_df['TotalPower'] = raw_data_df['total_power']
        raw_data_df['AvgPowerPerPlayer'] = raw_data_df['avg_power_per_player']
        
        # Handle realm name/ID and create display column
        if 'realm_name' in raw_data_df.columns:
            raw_data_df['RealmName'] = raw_data_df['realm_name']
        elif 'realm_id' in raw_data_df.columns:
            raw_data_df['RealmName'] = raw_data_df['realm_id'].apply(get_realm_name)
        else:
            raw_data_df['RealmName'] = 'Unknown Realm'
        
        display_columns = ['date', 'RealmName', 'total_players', 'TotalPower', 'AvgPowerPerPlayer'] + [f'{resource.title()}Sum' for resource in main_resources]
        
        # Format the dataframe with commas for numbers
        formatted_df = raw_data_df[display_columns].copy()
        for resource in main_resources:
            formatted_df[f'{resource.title()}Sum'] = formatted_df[f'{resource.title()}Sum'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        
        # Format total_players as well
        formatted_df['total_players'] = formatted_df['total_players'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        
        # Format power columns
        formatted_df['TotalPower'] = formatted_df['TotalPower'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        formatted_df['AvgPowerPerPlayer'] = formatted_df['AvgPowerPerPlayer'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        
        st.dataframe(formatted_df, width='stretch')

# Instructions
st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Setup Instructions")
st.sidebar.markdown("""
1. Place CSV files in the `Daily Reports` folder
2. Run: `streamlit run dashboard.py`
3. Open the provided URL in your browser
""")

# Add cache clear button at bottom
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Re-sync Database"):
    # Clear the memory cache (no file cache for security)
    if 'parsed_files_memory_cache' in st.session_state:
        st.session_state.parsed_files_memory_cache = {}
        st.info("🗑️ Cleared memory cache")
    
    # Remove any existing cache file for security
    cache_file = "parsed_files_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        st.info("🗑️ Removed old cache file")
    
    # Sync from GitHub first
    sync_success = sync_from_github()
    
    if sync_success:
        # Clear Streamlit cache and force reload
        st.cache_data.clear()
        st.success("Database re-synced! Reloading...")
        st.rerun()

if st.sidebar.button("Clear Cache & Reload"):
    st.cache_data.clear()
    st.rerun()
