import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_daily_rate(sorted_df, value_column):
    """Calculate true daily rate based on time differences between reports"""
    if len(sorted_df) < 2:
        return pd.Series([0] * len(sorted_df))
    
    daily_rates = []
    for i in range(len(sorted_df)):
        if i == 0:
            daily_rates.append(0)  # First report has no rate
        else:
            current_value = sorted_df.iloc[i][value_column]
            previous_value = sorted_df.iloc[i-1][value_column]
            current_time = sorted_df.iloc[i]['date']
            previous_time = sorted_df.iloc[i-1]['date']
            
            # Calculate time difference in days
            time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
            
            if time_diff > 0.1:  # Only calculate rate if time difference is significant
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return pd.Series(daily_rates)

def format_number(num, show_full=False):
    """Format numbers with optional full display - keeps original styling"""
    if show_full:
        # Full numbers with original st.metric styling
        return f"{int(num):,}"
    else:
        # Abbreviated numbers
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{int(num)}"

def format_rate(rate, show_full=False):
    """Format daily growth rates with optional full display - keeps original styling"""
    if show_full:
        # Full rates with original st.metric styling
        return f"{int(rate):+,}/day"
    else:
        # Abbreviated rates - use largest common number format
        if abs(rate) >= 1_000_000_000:
            return f"{rate/1_000_000_000:.1f}B/day"
        elif abs(rate) >= 1_000_000:
            return f"{rate/1_000_000:.1f}M/day"
        elif abs(rate) >= 1_000:
            return f"{rate/1_000:.1f}K/day"
        else:
            return f"{int(rate):,}/day"

def create_overview_tab(filtered_df):
    """Create the Overview tab with resource and player stats"""
    
    if not filtered_df.empty:
        # Get all resource types (keep original case for data access)
        all_resources = set()
        for resources in filtered_df['resources']:
            if isinstance(resources, dict):
                all_resources.update(resources.keys())
        
        # Show main 6 resources only
        key_resources = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        display_resources = [r for r in key_resources if r in all_resources]
        
        if display_resources:
            # Create grid layout
            col1, col2 = st.columns(2)
            
            with col1:
                # Add title and toggle on the same line
                title_col1, title_col2 = st.columns([2, 1])
                with title_col1:
                    st.markdown("### 📈 Resource Overview")
                with title_col2:
                    # Use Streamlit's built-in toggle
                    show_full_numbers = st.toggle("Full Numbers", value=st.session_state.get('resource_full_numbers', False), 
                                                key="resource_full_numbers",
                                                help="Show complete numbers instead of abbreviations")
                
                # Calculate daily increases using true daily rates
                sorted_filtered = filtered_df.sort_values('date')
                if len(sorted_filtered) >= 2:
                    latest_resources = sorted_filtered.iloc[-1]['resources']
                    previous_resources = sorted_filtered.iloc[-2]['resources']
                    
                    # Create resource values list for daily rate calculation
                    for resource in display_resources:
                        resource_values = []
                        for _, row in sorted_filtered.iterrows():
                            if isinstance(row['resources'], dict):
                                resource_values.append(row['resources'].get(resource, 0))
                            else:
                                resource_values.append(0)
                        
                        # Calculate daily rate for this resource
                        daily_rates = []
                        for i in range(len(resource_values)):
                            if i == 0:
                                daily_rates.append(0)
                            else:
                                current_value = resource_values[i]
                                previous_value = resource_values[i-1]
                                current_time = sorted_filtered.iloc[i]['date']
                                previous_time = sorted_filtered.iloc[i-1]['date']
                                
                                # Calculate time difference in days
                                time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
                                
                                if time_diff > 0:
                                    daily_rate = (current_value - previous_value) / time_diff
                                    daily_rates.append(daily_rate)
                                else:
                                    daily_rates.append(0)
                        
                        # Store the latest daily rate for this resource
                        sorted_filtered.loc[:, f'{resource}_daily_rate'] = daily_rates
                    
                    # Create 2x3 grid for resource metrics
                    for i in range(0, len(display_resources), 3):
                        cols = st.columns(3)
                        for j, resource in enumerate(display_resources[i:i+3]):
                            with cols[j]:
                                if isinstance(latest_resources, dict):
                                    latest_amount = latest_resources.get(resource, 0)
                                    
                                    # Get calculated daily rate (per day)
                                    daily_rate = sorted_filtered.iloc[-1][f'{resource}_daily_rate']
                                    
                                    # Calculate per player amount
                                    latest_players = sorted_filtered.iloc[-1]['total_players']
                                    avg_per_player = latest_amount / latest_players if latest_players > 0 else 0
                                    
                                    # Use st.metric for consistent styling in both modes
                                    st.metric(
                                        resource.title(),
                                        format_number(latest_amount, show_full_numbers),
                                        format_rate(daily_rate, show_full_numbers)
                                    )
                                    # Add per player amount below metric in a grey bubble
                                    st.markdown(f"<div style='text-align: left; margin-top: -10px;'><span style='background-color: #666; color: white; padding: 2px 8px; border-radius: 12px; font-size: 14px;'>{format_number(avg_per_player, show_full_numbers)}/player</span></div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("### 👥 Player Stats")
                
                # Player stats in grid
                latest_players = filtered_df.iloc[-1]['total_players']
                
                if len(filtered_df) >= 2:
                    sorted_df = filtered_df.sort_values('date')
                    latest_date = sorted_df.iloc[-1]['date']
                    
                    # Calculate true daily growth rate using time differences
                    player_values = sorted_df['total_players'].tolist()
                    daily_rates = []
                    for i in range(len(player_values)):
                        if i == 0:
                            daily_rates.append(0)
                        else:
                            current_value = player_values[i]
                            previous_value = player_values[i-1]
                            current_time = sorted_df.iloc[i]['date']
                            previous_time = sorted_df.iloc[i-1]['date']
                            
                            # Calculate time difference in days
                            time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
                            
                            if time_diff > 0:
                                daily_rate = (current_value - previous_value) / time_diff
                                daily_rates.append(daily_rate)
                            else:
                                # Same day reports - handle as daily change
                                change = current_value - previous_value
                                daily_rates.append(change)  # Use the actual change as daily rate
                    
                    # Get the latest daily rate
                    daily_growth = daily_rates[-1]
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
            
            # Date range info
            st.markdown("---")
            st.markdown("### 📈 Speedups Overview")
            
            # Define speedup items with their time durations in increasing order
            speedup_items = {
                'Blink': '1 min',
                'Hop': '5 min', 
                'Skip': '15 min',
                'Jump': '30 min',
                'Leap': '2.5 hours',
                'Bounce': '8 hours',
                'Bore': '15 hours',
                'Bolt': '24 hours',
                'Blast': '2.5 days',
                'Blitz': '4 days',
                'Testronius Dust': '15%',
                'Testronius Powder': '30%',
                'Testronius Infusion': '99%'
            }
            
            # Get all item types and find speedup items
            all_items = set()
            for items in filtered_df['items']:
                if isinstance(items, dict):
                    all_items.update(items.keys())
            
            # Find speedup items in data (in order of time)
            available_speedups = []
            for speedup_key in speedup_items.keys():  # Use keys() to maintain order
                for item_name in all_items:
                    # Handle both spaces and underscores for matching
                    search_key = speedup_key.lower().replace(' ', '_')
                    search_name = item_name.lower()
                    if search_key in search_name or speedup_key.lower() in search_name:
                        available_speedups.append(speedup_key)
                        break
            
            if available_speedups:
                # Create grid for speedup tiles (3 per row)
                for i in range(0, len(available_speedups), 3):
                    speedup_cols = st.columns(3)
                    for j, speedup_type in enumerate(available_speedups[i:i+3]):
                        with speedup_cols[j]:
                            # Get latest amount (using same logic as speedups tab)
                            sorted_df = filtered_df.sort_values('date')
                            latest_amount = 0
                            for items in sorted_df['items']:
                                if isinstance(items, dict):
                                    count = 0
                                    for item_name, amount in items.items():
                                        # Handle both spaces and underscores for matching (exclude x5, x10, x15 variants)
                                        search_key = speedup_type.lower().replace(' ', '_')
                                        search_name = item_name.lower()
                                        if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                            count += amount
                                    latest_amount = count  # This will be the last value
                                else:
                                    latest_amount = 0
                            
                            # Calculate true daily rate
                            if len(sorted_df) >= 2:
                                # Get all values in order
                                values = []
                                for items in sorted_df['items']:
                                    if isinstance(items, dict):
                                        count = 0
                                        for item_name, amount in items.items():
                                            # Handle both spaces and underscores for matching (exclude x5, x10, x15 variants)
                                            search_key = speedup_type.lower().replace(' ', '_')
                                            search_name = item_name.lower()
                                            if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                count += amount
                                        values.append(count)
                                    else:
                                        values.append(0)
                                
                                # Calculate daily rate using time differences
                                daily_rates = []
                                for i in range(len(values)):
                                    if i == 0:
                                        daily_rates.append(0)
                                    else:
                                        current_value = values[i]
                                        previous_value = values[i-1]
                                        current_time = sorted_df.iloc[i]['date']
                                        previous_time = sorted_df.iloc[i-1]['date']
                                        
                                        # Calculate time difference in days
                                        time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
                                        
                                        if time_diff > 0:
                                            daily_rate = (current_value - previous_value) / time_diff
                                            daily_rates.append(daily_rate)
                                        else:
                                            daily_rates.append(0)
                                
                                daily_change = daily_rates[-1] if daily_rates else 0
                            else:
                                daily_change = 0
                            
                            # Display speedup tile with time
                            time_duration = speedup_items.get(speedup_type, '')
                            
                            # Calculate average per player
                            latest_players = sorted_df.iloc[-1]['total_players']
                            avg_per_player = latest_amount / latest_players if latest_players > 0 else 0
                            
                            # Create custom metric with average per player
                            st.markdown(f"""
                            <style>
                            .speedup-tile-{speedup_type.lower().replace(' ', '-')} {{
                                border: 1px solid #ddd;
                                border-radius: 8px;
                                padding: 10px;
                                margin: 5px 0;
                                transition: all 0.3s ease;
                                cursor: pointer;
                            }}
                            .speedup-tile-{speedup_type.lower().replace(' ', '-')}:hover {{
                                border-color: #4CAF50;
                                box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
                                transform: translateY(-2px);
                                background-color: rgba(76, 175, 80, 0.05);
                            }}
                            </style>
                            <div class="speedup-tile-{speedup_type.lower().replace(' ', '-')}">
                                <div style="font-size: 14px; font-weight: bold; color: white;">⚡ {speedup_type} ({time_duration})</div>
                                <div style="font-size: 20px; font-weight: bold; margin: 5px 0;">{int(latest_amount):,}</div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span style="font-size: 14px; color: white; background-color: {'green' if daily_change >= 0 else 'red'}; padding: 2px 8px; border-radius: 12px;">{int(daily_change):,}/day</span>
                                    <span style="background-color: #666; color: white; padding: 2px 8px; border-radius: 12px; font-size: 14px;">
                                        {int(avg_per_player):,}/player
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    # No speedup items found - don't show warning since speedups might be displayed elsewhere
                    pass
    else:
        st.info("No data available")
