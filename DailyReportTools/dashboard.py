import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from data_loader import load_csv_files, calculate_daily_rate
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
from Tabs.map import create_map_tab
from Tabs.alliance import create_alliance_tab
from Tabs.pdd import create_pdd_tab
from Tabs.daily_report import create_daily_report_tab
from Tabs.purchases import create_purchases_tab
from cache_manager import cache_manager

def get_realm_name(realm_id):
    """Convert realm ID to realm name"""
    return 'Ruby'

def get_latest_commit_version():
    """Get version number from latest git commit message, fallback to commit hash"""
    try:
        import subprocess
        import re
        import os
        
        # Get the git repository root directory
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            git_root = result.stdout.strip()
        else:
            git_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Get the commit message
        result = subprocess.run(['git', 'log', '-1', '--pretty=format:%B'], 
                              capture_output=True, text=True, cwd=git_root)
        if result.returncode == 0:
            commit_message = result.stdout.strip()
            
            # Try to extract version number pattern (e.g., 2.5 or 2.4.4)
            version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', commit_message)
            if version_match:
                return version_match.group(1)
        
        # Fallback to commit hash
        result = subprocess.run(['git', 'log', '-1', '--pretty=format:%h'], 
                              capture_output=True, text=True, cwd=git_root)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None

def get_commit_history():
    """Get all commit messages with version numbers"""
    try:
        import subprocess
        import re
        import os
        
        # Get the git repository root directory
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            git_root = result.stdout.strip()
        else:
            git_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Get all commit messages with full body (limit to last 50 commits)
        # Use format that includes subject and body separated by a delimiter
        result = subprocess.run(['git', 'log', '-50', '--pretty=format:===COMMIT_START===%s%n%b===COMMIT_END==='], 
                              capture_output=True, text=True, cwd=git_root)
        if result.returncode == 0:
            # Split by our custom delimiter
            commits = result.stdout.split('===COMMIT_START===')
            
            # Filter commits with version numbers
            version_commits = []
            for commit in commits:
                if '===COMMIT_END===' in commit:
                    # Remove the end marker
                    message = commit.replace('===COMMIT_END===', '').strip()
                    # Remove TODO and anything after it
                    if 'TODO' in message:
                        message = message.split('TODO')[0].strip()
                    version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', message)
                    if version_match:
                        version = version_match.group(1)
                        version_commits.append({
                            'version': version,
                            'message': message
                        })
            
            return version_commits
        return []
    except Exception:
        return []

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
    
    # Ensure raw_player_data column is preserved (copy() might not preserve complex objects properly)
    if 'raw_player_data' in filtered_df.columns:
        updated_df['raw_player_data'] = filtered_df['raw_player_data'].copy()
    
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

st.set_page_config(page_title="Realm Analytics Dashboard", layout="wide")

# Initialize session state for commit history view
if 'show_commit_history' not in st.session_state:
    st.session_state.show_commit_history = False

# Load data first
df = load_csv_files(st)

# Create header with title and realm name in top-right
col1, col2 = st.columns([3, 1])

with col1:
    version = get_latest_commit_version()
    if version:
        # Display title and version button inline
        title_col, version_col = st.columns([10, 1])
        with title_col:
            st.markdown("### 🏰 Realm Analytics Dashboard")
        with version_col:
            if st.button(f"v{version}", key="version_toggle", help="Click to view version history"):
                st.session_state.show_commit_history = not st.session_state.show_commit_history
    else:
        st.title("🏰 Realm Analytics Dashboard")

with col2:
    if not df.empty:
        latest_row = df.iloc[-1]
        
        # Handle different realm name fields - default to Ruby if nan or missing
        realm_name = 'Ruby'
        if 'realm_name' in latest_row and pd.notna(latest_row['realm_name']):
            realm_name = latest_row['realm_name']
        elif 'realm_id' in latest_row and pd.notna(latest_row['realm_id']):
            realm_name = get_realm_name(latest_row['realm_id'])
        
        st.markdown(f"**Realm:** {realm_name}")

# Show commit history page if toggled
if st.session_state.show_commit_history:
    st.markdown("---")
    st.markdown("### 📜 ROA Dashboard Update History")
    
    commit_history = get_commit_history()
    
    if commit_history:
        for commit in commit_history:
            st.markdown(f"**Version {commit['version']}**")
            st.markdown(commit['message'])
            st.markdown("---")
    else:
        st.info("No version history found")
    
    if st.button("← Back to Dashboard"):
        st.session_state.show_commit_history = False
        st.rerun()
    
    st.stop()  # Stop execution here to prevent showing the rest of the dashboard

if df.empty:
    st.error("No CSV files found in GitHub repository!")
else:
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Latest report info
    if not df.empty:
        latest_report = df.iloc[-1]
        
        # Database update time from CSV data
        database_date = latest_report['date']
        database_date_str = database_date.strftime("%Y-%m-%d %I:%M %p")
        
        # Dashboard update time - using current time since we load from GitHub
        dashboard_date = datetime.now()
        dashboard_date_str = dashboard_date.strftime("%Y-%m-%d %I:%M %p")
        
        # Handle different realm name fields - default to Ruby if nan or missing
        realm_name = 'Ruby'
        if 'realm_name' in latest_report and pd.notna(latest_report['realm_name']):
            realm_name = latest_report['realm_name']
        elif 'realm_id' in latest_report and pd.notna(latest_report['realm_id']):
            realm_name = get_realm_name(latest_report['realm_id'])
        
        # Get latest commit message
        latest_commit = get_latest_commit_version()
        
        st.sidebar.markdown("### 📊 Latest Report")
        st.sidebar.markdown(f"**Database Update:** {database_date_str}")
        st.sidebar.markdown(f"**Dashboard Update:** {dashboard_date_str}")
        st.sidebar.markdown(f"**Realm:** {realm_name}")
        st.sidebar.markdown(f"**Total Reports:** {len(df)}")
        if latest_commit:
            st.sidebar.markdown(f"**Latest Commit:** {latest_commit}")
    
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
    
    # Initialize cache manager with filtered data
    cache_manager.initialize_cache(filtered_df)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15, tab16 = st.tabs(["Overview", "Daily Report", "Player Count", "Resources", "Power", "Speedups", "Items", "Troops", "Buildings", "Skins", "Quests & Research", "Protected Resources", "Map", "Alliance", "PDD", "Purchases"])
    
    with tab1:
        create_overview_tab(filtered_df)
    
    with tab2:
        create_daily_report_tab(filtered_df)
    
    with tab3:
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
                        
                        # Calculate active players for historical data points
                        active_player_counts = []
                        active_percentages = []
                        
                        # Try to get active player data from historical comprehensive files
                        for chart_date in chart_dates:
                            # Find the closest data point in filtered_df
                            closest_row = None
                            min_diff = float('inf')
                            for _, row in filtered_df.iterrows():
                                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                                    diff = abs(row['date'] - chart_date).total_seconds()
                                    if diff < min_diff:
                                        min_diff = diff
                                        closest_row = row
                            
                            if closest_row is not None and min_diff < 86400:  # Within 1 day
                                # Calculate active players for this data point (7-day window)
                                current_df = closest_row['raw_player_data']
                                if len(filtered_df) > 1:
                                    # Find data point from 7 days ago
                                    target_date = closest_row['date'] - pd.Timedelta(days=7)
                                    prev_row = None
                                    prev_min_diff = float('inf')
                                    for _, row in filtered_df.iterrows():
                                        if 'raw_player_data' in row and row['raw_player_data'] is not None:
                                            if row['date'] < closest_row['date']:
                                                diff = abs(row['date'] - target_date).total_seconds()
                                                if diff < prev_min_diff:
                                                    prev_min_diff = diff
                                                    prev_row = row
                                    
                                    if prev_row is not None:
                                        prev_df = prev_row['raw_player_data']
                                        
                                        # Merge current and 7-day-ago data to find active players
                                        merged_df = pd.merge(
                                            current_df[['username', 'power', 'total_troops']],
                                            prev_df[['username', 'power', 'total_troops']],
                                            on='username',
                                            suffixes=('_current', '_previous'),
                                            how='outer'
                                        )
                                        merged_df['power_change'] = merged_df['power_current'] - merged_df['power_previous']
                                        merged_df['troop_change'] = merged_df['total_troops_current'] - merged_df['total_troops_previous']
                                        
                                        active_players = merged_df[
                                            (merged_df['power_change'] != 0) | 
                                            (merged_df['troop_change'] != 0) |
                                            (merged_df['power_current'].notna() & merged_df['power_previous'].isna())
                                        ]
                                        active_count = len(active_players)
                                        total_count = len(current_df)
                                        active_percentage = (active_count / total_count * 100) if total_count > 0 else 0
                                        active_player_counts.append(active_count)
                                        active_percentages.append(active_percentage)
                                    else:
                                        # No 7-day-ago data, estimate
                                        active_player_counts.append(None)
                                        active_percentages.append(None)
                                else:
                                    active_player_counts.append(None)
                                    active_percentages.append(None)
                            else:
                                active_player_counts.append(None)
                                active_percentages.append(None)
                        
                        # Calculate average active percentage from available data
                        available_percentages = [p for p in active_percentages if p is not None]
                        if available_percentages:
                            avg_active_percentage = sum(available_percentages) / len(available_percentages)
                        else:
                            avg_active_percentage = 30.0  # Default to 30% if no data
                        
                        # Fill in missing active player counts using average percentage
                        for i, (active_count, active_pct, total_count) in enumerate(zip(active_player_counts, active_percentages, chart_counts)):
                            if active_count is None:
                                estimated_active = int(total_count * (avg_active_percentage / 100))
                                active_player_counts[i] = estimated_active
                                active_percentages[i] = avg_active_percentage
                        
                        # Create dataframe for the chart
                        chart_df = pd.DataFrame({
                            'date': chart_dates,
                            'total_players': chart_counts,
                            'active_players': active_player_counts
                        })
                        
                        # Create line chart with both total and active players
                        fig_players = px.line(
                            chart_df, 
                            x='date', 
                            y=['total_players', 'active_players'],
                            title='Player Count Over Time',
                            markers=False,
                            labels={'value': 'Players', 'variable': 'Type'}
                        )
                        fig_players.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Players",
                            hovermode='x unified',
                            legend=dict(
                                yanchor="top",
                                y=0.99,
                                xanchor="left",
                                x=0.01
                            )
                        )
                        fig_players.update_traces(
                            line=dict(width=2),
                            selector=dict(name='total_players')
                        )
                        fig_players.update_traces(
                            line=dict(width=2, dash='dash'),
                            selector=dict(name='active_players')
                        )
                        fig_players.update_yaxes(tickformat=',')
                        st.plotly_chart(fig_players, width='stretch')
                    else:
                        st.warning("No valid player creation dates found in the latest comprehensive data file")
                else:
                    st.warning("No creation date column found in the latest comprehensive data file")
            else:
                st.warning("No comprehensive data file found")
    
    with tab4:
        create_resources_tab(filtered_df)
    
    with tab5:
        create_power_tab(filtered_df)
    
    with tab6:
        create_speedups_tab(filtered_df)
    
    with tab7:
        create_items_tab(filtered_df)
    
    with tab8:
        create_troops_tab(filtered_df)
    
    with tab9:
        create_buildings_tab(filtered_df)
    
    with tab10:
        create_skins_tab(filtered_df)
    
    with tab11:
        create_quests_research_tab(filtered_df)
    
    with tab12:
        create_ceasefire_tab(filtered_df)
    
    with tab13:
        create_map_tab(filtered_df)
    
    with tab14:
        create_alliance_tab(filtered_df)
    
    with tab15:
        create_pdd_tab(filtered_df)
    
    with tab16:
        create_purchases_tab()

# Add cache clear button at bottom
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Sync from GitHub"):
    # Invalidate cache manager cache
    cache_manager.invalidate_cache()
    # Reload data with force_reload=True
    st.cache_data.clear()
    df = load_csv_files(st, force_reload=True)
    st.success("Syncing from GitHub...")
    st.rerun()

if st.sidebar.button("🗑️ Clear Cache"):
    # Manually clear cache
    cache_manager.invalidate_cache()
    st.success("Cache cleared successfully!")
    st.rerun()
