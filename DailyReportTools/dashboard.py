import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import glob
from Tabs.speedups import create_speedups_tab
from Tabs.resources import create_resources_tab
from Tabs.overview import create_overview_tab
from Tabs.power import create_power_tab

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

st.set_page_config(page_title="Realm Analytics Dashboard", layout="wide")

@st.cache_data(ttl=60)  # Add 60-second TTL to prevent stale cache
def load_csv_files():
    """Load and parse all CSV files from Daily Reports folder"""
    csv_files = glob.glob("Daily Reports/*.csv")
    
    # Sort files by modification time (newest first)
    csv_files = sorted(csv_files, key=os.path.getmtime, reverse=True)
    
    all_data = []
    
    for file_path in csv_files:
        try:
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
                continue  # Skip unparseable filename
            
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
            
            all_data.append(realm_data)
            
        except Exception as e:
            # Silently skip parsing errors to avoid sidebar clutter
            pass
    
    return pd.DataFrame(all_data)

# Load data first
df = load_csv_files()

# Create header with title and realm name in top-right
col1, col2 = st.columns([3, 1])

with col1:
    st.title("🏰 Realm Analytics Dashboard")

with col2:
    if not df.empty:
        realm_name = df.iloc[-1]['realm_name']
        st.markdown(f"**Realm:** {realm_name}")

if df.empty:
    st.error("No CSV files found in Daily Reports folder!")
else:
    # Sidebar filters
    st.sidebar.header("Filters")
    
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
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "👥 Player Count", "📈 Resources", "⚔️ Power", "⚡ Speedups"])
    
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
            fig_players = px.line(
                filtered_df, 
                x='date', 
                y='total_players',
                title='Total Players Over Time',
                markers=True
            )
            fig_players.update_layout(
                xaxis_title="Date",
                yaxis_title="Total Players",
                hovermode='x unified'
            )
            st.plotly_chart(fig_players, use_container_width=True)
    
    with tab3:
        create_resources_tab(filtered_df)
    
    with tab4:
        create_power_tab(filtered_df)
    
    with tab5:
        create_speedups_tab(filtered_df)
    
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
        
        # Select columns to display
        display_columns = ['date', 'realm_name', 'total_players', 'TotalPower', 'AvgPowerPerPlayer'] + [f'{resource.title()}Sum' for resource in main_resources]
        
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
    # Clear cache and force reload
    st.cache_data.clear()
    st.success("Database re-synced! Reloading...")
    st.rerun()

if st.sidebar.button("Clear Cache & Reload"):
    st.cache_data.clear()
    st.rerun()
