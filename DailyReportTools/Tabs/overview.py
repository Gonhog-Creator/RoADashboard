import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import base64
from utils import calculate_daily_rate, format_number, format_rate, calculate_percentage


def create_overview_tab(filtered_df):
    """Create the Overview tab with resource and player stats"""
    
    if not filtered_df.empty:
        # Get all resource types from actual resource columns
        all_resources = set()
        for _, row in filtered_df.iterrows():
            if 'raw_player_data' in row and row['raw_player_data'] is not None:
                player_data = row['raw_player_data']
                # Look for resource columns
                resource_cols = [col for col in player_data.columns if col.startswith('resource_')]
                for col in resource_cols:
                    resource_name = col.replace('resource_', '')
                    all_resources.add(resource_name)
        
        # Show main 6 resources only
        key_resources = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        display_resources = [r for r in key_resources if r in all_resources]
        
        if display_resources:
            # Find the latest comprehensive data for accurate calculations
            latest_comprehensive_data = None
            for i in range(len(filtered_df) - 1, -1, -1):  # Iterate backwards to find latest comprehensive data
                data = filtered_df.iloc[i]
                if 'raw_player_data' in data and data['raw_player_data'] is not None:
                    latest_comprehensive_data = data
                    break
            
            if latest_comprehensive_data is None:
                st.warning("No comprehensive CSV data found for accurate resource calculations.")
                return
            
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
                
                # Use comprehensive data for latest resources
                latest_player_data = latest_comprehensive_data.raw_player_data
                
                # Only calculate daily rates if we have multiple data points
                if len(sorted_filtered) >= 2:
                    previous_row = sorted_filtered.iloc[-2]
                    previous_player_data = previous_row['raw_player_data']
                    
                    # Create resource values list for daily rate calculation
                    for resource in display_resources:
                        resource_values = []
                        for _, row in sorted_filtered.iterrows():
                            if 'raw_player_data' in row and row['raw_player_data'] is not None:
                                player_data = row['raw_player_data']
                                resource_col = f'resource_{resource}'
                                if resource_col in player_data.columns:
                                    resource_values.append(player_data[resource_col].sum())
                                else:
                                    resource_values.append(0)
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
                
                # Create 2x3 grid for resource metrics (always show, even with single data point)
                for i in range(0, len(display_resources), 3):
                    # Add spacing between rows (except for the first row)
                    if i > 0:
                        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                    
                    cols = st.columns(3)
                    for j, resource in enumerate(display_resources[i:i+3]):
                        with cols[j]:
                            # Get latest amount from resource columns
                            resource_col = f'resource_{resource}'
                            if resource_col in latest_player_data.columns:
                                latest_amount = latest_player_data[resource_col].sum()
                            else:
                                latest_amount = 0
                            
                        # Get calculated daily rate (per day)
                            if f'{resource}_daily_rate' in sorted_filtered.columns:
                                daily_rate = sorted_filtered.iloc[-1][f'{resource}_daily_rate']
                            else:
                                daily_rate = 0
                            
                            # Calculate per player amount
                            latest_players = len(sorted_filtered.iloc[-1]['raw_player_data']) if 'raw_player_data' in sorted_filtered.iloc[-1] and sorted_filtered.iloc[-1]['raw_player_data'] is not None else 0
                            avg_per_player = latest_amount / latest_players if latest_players > 0 else 0
                            
                            # Use st.metric for consistent styling in both modes
                            st.metric(
                                resource.title(),
                                format_number(latest_amount, show_full_numbers),
                                format_rate(daily_rate, show_full_numbers)
                            )
                            
                            # Calculate unprotected resources (total - protected)
                            unprotected_amount = 0
                            unprotected_percentage = 0
                            
                            # Get ceasefire protection data if available from comprehensive data
                            if hasattr(latest_comprehensive_data, 'ceasefire_data') and isinstance(latest_comprehensive_data.ceasefire_data, dict):
                                ceasefire_info = latest_comprehensive_data.ceasefire_data.get(resource, {})
                                protected_amount = ceasefire_info.get('protected', 0)
                                total_amount = ceasefire_info.get('total', latest_amount)
                                unprotected_amount = total_amount - protected_amount
                                unprotected_percentage = (unprotected_amount / total_amount * 100) if total_amount > 0 else 0
                            else:
                                # If no ceasefire data, unprotected equals total
                                unprotected_amount = latest_amount
                                unprotected_percentage = 100.0
                            
                            # Add per player amount and unprotected resources info below metric
                            # Per player badge
                            st.markdown(f"<div style='text-align: left; margin-top: -10px; margin-bottom: 2px;'><span style='background-color: #666; color: white; padding: 2px 8px; border-radius: 12px; font-size: 14px;'>{format_number(avg_per_player, show_full_numbers)}/player</span></div>", unsafe_allow_html=True)
                            
                            # Unprotected badge below (only if not ruby)
                            if unprotected_amount > 0 and resource != 'ruby':
                                st.markdown(f"<div style='text-align: left; margin-top: 0px;'><span style='background-color: #87CEEB; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px;'>{format_number(unprotected_amount, show_full_numbers)} unprotected ({unprotected_percentage:.1f}%)</span></div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("### 👥 Player Stats")
                
                # Player stats in grid
                latest_players = len(filtered_df.iloc[-1]['raw_player_data']) if 'raw_player_data' in filtered_df.iloc[-1] and filtered_df.iloc[-1]['raw_player_data'] is not None else 0
                
                if len(filtered_df) >= 2:
                    sorted_df = filtered_df.sort_values('date')
                    latest_date = sorted_df.iloc[-1]['date']
                    
                    # Calculate true daily growth rate using time differences
                    player_values = []
                    for _, row in sorted_df.iterrows():
                        if 'raw_player_data' in row and row['raw_player_data'] is not None:
                            player_values.append(len(row['raw_player_data']))
                        else:
                            player_values.append(0)
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
                    prev_day_players = len(sorted_df.iloc[-2]['raw_player_data']) if 'raw_player_data' in sorted_df.iloc[-2] and sorted_df.iloc[-2]['raw_player_data'] is not None else 0
                    if prev_day_players > 0:
                        daily_percent = (daily_growth / prev_day_players) * 100
                    else:
                        daily_percent = 100.0 if daily_growth > 0 else 0.0
                    
                    # Weekly growth (7 days ago)
                    week_ago = latest_date - pd.Timedelta(days=7)
                    week_data = sorted_df[sorted_df['date'] >= week_ago]
                    if len(week_data) >= 2:
                        week_ago_players = len(week_data.iloc[0]['raw_player_data']) if 'raw_player_data' in week_data.iloc[0] and week_data.iloc[0]['raw_player_data'] is not None else 0
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
                        month_ago_players = len(month_data.iloc[0]['raw_player_data']) if 'raw_player_data' in month_data.iloc[0] and month_data.iloc[0]['raw_player_data'] is not None else 0
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
            
            # Power Overview Section
            st.markdown("### ⚔️ Power Overview")
            
            if not filtered_df.empty:
                # Get latest power data
                sorted_df = filtered_df.sort_values('date')
                latest_data = sorted_df.iloc[-1]
                
                # Extract power data from realm summary (handle missing power data)
                total_power = latest_data.get('total_power', 0) if 'total_power' in latest_data else 0
                avg_power_per_player = latest_data.get('avg_power_per_player', 0) if 'avg_power_per_player' in latest_data else 0
                latest_players = len(filtered_df.iloc[-1]['raw_player_data']) if 'raw_player_data' in filtered_df.iloc[-1] and filtered_df.iloc[-1]['raw_player_data'] is not None else 0
                
                # Calculate power growth rates (only if total_power column exists)
                daily_power_change = 0
                daily_avg_power_change = 0
                if len(sorted_df) >= 2 and 'total_power' in sorted_df.columns:
                    daily_power_rates = calculate_daily_rate(sorted_df, 'total_power')
                    
                    # Get the most recent meaningful (non-zero) change
                    meaningful_changes = daily_power_rates.dropna()
                    meaningful_changes = meaningful_changes[meaningful_changes != 0]
                    daily_power_change = meaningful_changes.iloc[-1] if len(meaningful_changes) > 0 else 0
                    
                    # Calculate per player power growth (only if avg_power_per_player column exists)
                    if 'avg_power_per_player' in sorted_df.columns:
                        daily_avg_power_rates = calculate_daily_rate(sorted_df, 'avg_power_per_player')
                        
                        # Get the most recent meaningful (non-zero) change for per player power
                        avg_meaningful_changes = daily_avg_power_rates.dropna()
                        avg_meaningful_changes = avg_meaningful_changes[avg_meaningful_changes != 0]
                        daily_avg_power_change = avg_meaningful_changes.iloc[-1] if len(avg_meaningful_changes) > 0 else 0
                
                # Display power metrics
                power_col1, power_col2, power_col3 = st.columns([1, 1, 2])
                
                with power_col1:
                    st.metric(
                        "⚔️ Total Power",
                        format_number(total_power, False),
                        format_rate(daily_power_change, False)
                    )
                
                with power_col2:
                    st.metric(
                        "👤 Power per Player",
                        format_number(avg_power_per_player, False),
                        format_rate(daily_avg_power_change, False)
                    )
                
                with power_col3:
                    # Top 10 Players by Power
                    st.markdown("**Top 10 Players**")
                    
                    # Get raw player data to find top power players
                    if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
                        player_df = latest_data['raw_player_data']
                        if isinstance(player_df, pd.DataFrame) and not player_df.empty and 'power' in player_df.columns:
                            # Convert power to numeric and get top 10
                            player_df['power'] = pd.to_numeric(player_df['power'], errors='coerce').fillna(0)
                            top_power_players = player_df.nlargest(10, 'power')
                            
                            # Display in 2x5 grid
                            for i in range(0, 10, 5):
                                cols = st.columns(5)
                                for j in range(5):
                                    if i + j < len(top_power_players):
                                        with cols[j]:
                                            player = top_power_players.iloc[i + j]
                                            player_name = player.get('username', str(player['account_id'])[:8] + "...")
                                            power_val = int(player['power'])
                                            st.markdown(f"**#{i + j + 1}**<br>{player_name}<br>{power_val:,}", unsafe_allow_html=True)
            else:
                st.info("No power data available")
            
            st.markdown("---")
            
            # Dragons Section
            st.markdown("### 🐉 Dragons")
            
            # Get dragon data from troops parsing
            dragons_data = {}
            if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
                player_df = latest_data['raw_player_data']
                if isinstance(player_df, pd.DataFrame) and not player_df.empty:
                    # Check if troops_json exists
                    if 'troops_json' in player_df.columns:
                        for _, player in player_df.iterrows():
                            if pd.notna(player['troops_json']):
                                try:
                                    troops_dict = json.loads(player['troops_json'])
                                    # Count players with Great Dragon
                                    if 'great_dragon' in troops_dict and troops_dict['great_dragon'] > 0:
                                        dragons_data['great_dragon'] = dragons_data.get('great_dragon', 0) + 1
                                    # Count players with Water Dragon
                                    if 'water_dragon' in troops_dict and troops_dict['water_dragon'] > 0:
                                        dragons_data['water_dragon'] = dragons_data.get('water_dragon', 0) + 1
                                except:
                                    pass
                    else:
                        # Fallback to individual troop columns
                        if 'troop_great_dragon' in player_df.columns:
                            dragons_data['great_dragon'] = (pd.to_numeric(player_df['troop_great_dragon'], errors='coerce') > 0).sum()
                        if 'troop_water_dragon' in player_df.columns:
                            dragons_data['water_dragon'] = (pd.to_numeric(player_df['troop_water_dragon'], errors='coerce') > 0).sum()
            
            # Dragon image map
            dragon_image_map = {
                'great_dragon': 'great_dragon.webp',
                'water_dragon': 'water_dragon.webp'
            }
            
            dragon_names = ['great_dragon', 'water_dragon']
            
            # Display dragon tiles in a grid
            cols = st.columns(len(dragon_names))
            for i, dragon_name in enumerate(dragon_names):
                with cols[i]:
                    image_file = dragon_image_map.get(dragon_name, 'dragon_keep.webp')
                    image_path = f"Images/{image_file}"
                    
                    try:
                        st.image(image_path, width=70)
                    except:
                        st.write("🐉")
                    
                    display_name = dragon_name.replace('_', ' ').title()
                    player_count = dragons_data.get(dragon_name, 0)
                    st.markdown(f"**{display_name}**")
                    st.metric("Players", player_count)
            
            st.markdown("---")
            st.markdown("### Elite Items")
            
            # Elite Items - Fangtooth Respirators
            # Look for fangtooth respirators in resources data
            respirator_values = []
            respirator_dates = []
            
            for _, row in filtered_df.iterrows():
                respirator_count = 0
                
                # Check resources dictionary for fangtooth
                if 'resources' in row and isinstance(row['resources'], dict):
                    # Look for resource_fangtooth or similar
                    for resource_name, resource_value in row['resources'].items():
                        if 'fangtooth' in resource_name.lower():
                            respirator_count += resource_value
                
                # Also check raw_player_data for comprehensive format
                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                    player_data = row['raw_player_data']
                    # Look for resource_fangtooth column
                    if 'resource_fangtooth' in player_data.columns:
                        respirator_count += player_data['resource_fangtooth'].fillna(0).sum()
                
                respirator_values.append(respirator_count)
                respirator_dates.append(row['date'])
            
            # Filter out leading zeros
            if sum(respirator_values) > 0:
                # Find first non-zero index
                first_nonzero_idx = next((i for i, v in enumerate(respirator_values) if v > 0), None)
                if first_nonzero_idx is not None and first_nonzero_idx > 0:
                    # Keep only the first zero and everything after first_nonzero_idx
                    respirator_values = [respirator_values[first_nonzero_idx - 1]] + respirator_values[first_nonzero_idx:]
                    respirator_dates = [respirator_dates[first_nonzero_idx - 1]] + respirator_dates[first_nonzero_idx:]
            
            if sum(respirator_values) > 0:
                # Calculate daily rate
                if len(respirator_values) >= 2:
                    daily_rates = []
                    for i in range(len(respirator_values)):
                        if i == 0:
                            daily_rates.append(0)
                        else:
                            current_value = respirator_values[i]
                            previous_value = respirator_values[i-1]
                            current_time = respirator_dates[i]
                            previous_time = respirator_dates[i-1]
                            
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
                
                latest_amount = respirator_values[-1]
                
                # Calculate average per player
                latest_players = len(filtered_df.iloc[-1]['raw_player_data']) if 'raw_player_data' in filtered_df.iloc[-1] and filtered_df.iloc[-1]['raw_player_data'] is not None else 0
                avg_per_player = latest_amount / latest_players if latest_players > 0 else 0
                
                # Display elite item tile (compact)
                # For now, single item - will expand to horizontal grid when more items added
                # Currently using single column, but structure is ready for horizontal layout
                elite_cols = st.columns(1)
                with elite_cols[0]:
                    # Read image and convert to base64
                    import base64
                    image_path = "Images/fangtooth_respirator.webp"
                    try:
                        with open(image_path, "rb") as image_file:
                            encoded_image = base64.b64encode(image_file.read()).decode()
                            image_html = f'<img src="data:image/webp;base64,{encoded_image}" width="50" style="border-radius: 4px;">'
                    except:
                        image_html = ""
                    
                    st.markdown(f"""
                    <style>
                    .elite-item-tile {{
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 5px 0;
                        transition: all 0.3s ease;
                        cursor: pointer;
                        max-width: 300px;
                        background-color: #2d2d2d;
                    }}
                    .elite-item-tile:hover {{
                        border-color: #FF6B6B;
                        box-shadow: 0 4px 8px rgba(255, 107, 107, 0.3);
                        transform: translateY(-2px);
                        background-color: rgba(255, 107, 107, 0.05);
                    }}
                    </style>
                    <div class="elite-item-tile">
                        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                            {image_html}
                            <div style="font-size: 14px; font-weight: bold; color: white;">Fangtooth Respirators</div>
                        </div>
                        <div style="font-size: 20px; font-weight: bold; margin: 5px 0; color: white;">{int(latest_amount):,}</div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 14px; color: white; background-color: {'green' if daily_change >= 0 else 'red'}; padding: 2px 8px; border-radius: 12px;">{int(daily_change):,}/day</span>
                            <span style="background-color: #666; color: white; padding: 2px 8px; border-radius: 12px; font-size: 14px;">
                                {int(avg_per_player):,}/player
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
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
                'Testronius Deluxe': '50%',
                'Testronius Infusion': '99%'
            }
            
            # Speedup image map
            speedup_image_map = {
                'Blink': 'Blink.webp',
                'Hop': 'Hop.webp',
                'Skip': 'Skip.webp',
                'Jump': 'Jump.webp',
                'Leap': 'Leap.webp',
                'Bounce': 'Bounce.webp',
                'Bore': 'Bore.webp',
                'Bolt': 'Bolt.webp',
                'Blast': 'Blast.webp',
                'Blitz': 'Blitz.webp',
                'Testronius Dust': 'Testronius_powder.webp',
                'Testronius Powder': 'Testronius_powder.webp',
                'Testronius Deluxe': 'Testronius_deluxe.webp',
                'Testronius Infusion': 'Infusion_testronius.webp'
            }
            
            # Get all item types and find speedup items
            all_items = set()
            for _, row in filtered_df.iterrows():
                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                    player_data = row['raw_player_data']
                    if 'items_json' in player_data.columns:
                        items_json = player_data['items_json']
                        # Process each player's items_json individually
                        for items_str in items_json:
                            if pd.notna(items_str) and items_str:
                                try:
                                    items_dict = json.loads(items_str)
                                    if isinstance(items_dict, dict):
                                        all_items.update(items_dict.keys())
                                except:
                                    continue
            
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
                # Add clear section header
                st.markdown("#### ⚡ Individual Speedup Items")
                st.markdown("*Speedup items across all players*")
                
                # Create grid for speedup tiles (horizontal layout - 5 per row)
                for i in range(0, len(available_speedups), 5):
                    speedup_cols = st.columns(5)
                    for j, speedup_type in enumerate(available_speedups[i:i+5]):
                        with speedup_cols[j]:
                            # Get latest amount (using same logic as speedups tab)
                            sorted_df = filtered_df.sort_values('date')
                            latest_amount = 0
                            for _, row in sorted_df.iterrows():
                                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                                    player_data = row['raw_player_data']
                                    if 'items_json' in player_data.columns:
                                        items_json = player_data['items_json']
                                        # Process each player's items_json individually
                                        count = 0
                                        for items_str in items_json:
                                            if pd.notna(items_str) and items_str:
                                                try:
                                                    items_dict = json.loads(items_str)
                                                    if isinstance(items_dict, dict):
                                                        for item_name, amount in items_dict.items():
                                                            # Handle both spaces and underscores for matching (exclude x5, x10, x15 variants)
                                                            search_key = speedup_type.lower().replace(' ', '_')
                                                            search_name = item_name.lower()
                                                            if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                                count += amount
                                                except:
                                                    pass
                                        latest_amount = count  # This will be the last value
                                else:
                                    latest_amount = 0
                            
                            # Calculate true daily rate
                            if len(sorted_df) >= 2:
                                # Get all values in order
                                values = []
                                for _, row in sorted_df.iterrows():
                                    if 'raw_player_data' in row and row['raw_player_data'] is not None:
                                        player_data = row['raw_player_data']
                                        if 'items_json' in player_data.columns:
                                            items_json = player_data['items_json']
                                            # Process each player's items_json individually
                                            count = 0
                                            for items_str in items_json:
                                                if pd.notna(items_str) and items_str:
                                                    try:
                                                        items_dict = json.loads(items_str)
                                                        if isinstance(items_dict, dict):
                                                            for item_name, amount in items_dict.items():
                                                                # Handle both spaces and underscores for matching (exclude x5, x10, x15 variants)
                                                                search_key = speedup_type.lower().replace(' ', '_')
                                                                search_name = item_name.lower()
                                                                if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                                    count += amount
                                                    except:
                                                        pass
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
                            latest_players = len(sorted_df.iloc[-1]['raw_player_data']) if 'raw_player_data' in sorted_df.iloc[-1] and sorted_df.iloc[-1]['raw_player_data'] is not None else 0
                            avg_per_player = latest_amount / latest_players if latest_players > 0 else 0
                            
                            # Read image and convert to base64
                            image_file = speedup_image_map.get(speedup_type, 'Bolt.webp')
                            image_path = f"Images/{image_file}"
                            try:
                                with open(image_path, "rb") as img_file:
                                    encoded_image = base64.b64encode(img_file.read()).decode()
                                    image_html = f'<img src="data:image/webp;base64,{encoded_image}" width="50" style="border-radius: 4px;">'
                            except:
                                image_html = ""
                            
                            # Create custom metric with average per player (compact tile style)
                            st.markdown(f"""
                            <style>
                            .speedup-tile {{
                                border: 1px solid #ddd;
                                border-radius: 8px;
                                padding: 15px;
                                margin: 5px 0;
                                transition: all 0.3s ease;
                                cursor: pointer;
                                max-width: 300px;
                                background-color: #2d2d2d;
                            }}
                            .speedup-tile:hover {{
                                border-color: #4CAF50;
                                box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
                                transform: translateY(-2px);
                                background-color: rgba(76, 175, 80, 0.05);
                            }}
                            </style>
                            <div class="speedup-tile">
                                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                                    {image_html}
                                    <div style="font-size: 14px; font-weight: bold; color: white;">{speedup_type} ({time_duration})</div>
                                </div>
                                <div style="font-size: 20px; font-weight: bold; margin: 5px 0; color: white;">{int(latest_amount):,}</div>
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
                st.info("No speedup items found in the data")
    else:
        st.info("No data available")

    # Speedup Section - Top 50 Players by Power
    st.markdown("---")
    st.markdown("#### ⚡ Speedup Inventory - Top 50 Players by Power")
    
    if not filtered_df.empty and 'raw_player_data' in filtered_df.iloc[-1]:
        try:
            latest_data = filtered_df.sort_values('date', ascending=False).iloc[0]
            player_df = latest_data['raw_player_data']
            
            if isinstance(player_df, pd.DataFrame) and not player_df.empty:
                # Get top 50 players by power
                top_50_players = player_df.nlargest(50, 'power')
                
                # Define speedup items matching Speedups Overview section (excluding testronius powers)
                speedup_items = {
                    'blink': {'name': 'Blink', 'duration': '1 min'},
                    'hop': {'name': 'Hop', 'duration': '5 min'},
                    'skip': {'name': 'Skip', 'duration': '15 min'},
                    'jump': {'name': 'Jump', 'duration': '30 min'},
                    'leap': {'name': 'Leap', 'duration': '2.5 hours'},
                    'bounce': {'name': 'Bounce', 'duration': '8 hours'},
                    'bore': {'name': 'Bore', 'duration': '15 hours'},
                    'bolt': {'name': 'Bolt', 'duration': '24 hours'},
                    'blast': {'name': 'Blast', 'duration': '2.5 days'},
                    'blitz': {'name': 'Blitz', 'duration': '4 days'},
                }
                
                # Note: Testronius powers (Dust, Powder, Deluxe, Infusion) are excluded as requested
                
                # Calculate totals for each speedup item
                speedup_totals = {}
                total_hourly_amount = 0
                
                for item_key, item_info in speedup_items.items():
                    total_count = 0
                    
                    for _, player in top_50_players.iterrows():
                        if 'items_json' in player and pd.notna(player['items_json']):
                            try:
                                items_data = json.loads(player['items_json'])
                                if item_key in items_data:
                                    total_count += items_data[item_key]
                            except:
                                continue
                    
                    speedup_totals[item_key] = {
                        'total': total_count,
                        'name': item_info['name'],
                        'duration': item_info['duration']
                    }
                    
                    # Calculate hourly contribution
                    duration = item_info['duration']
                    if 'min' in duration:
                        minutes = int(duration.split(' ')[0])
                        hours = minutes / 60
                    elif 'hour' in duration:
                        if 'hours' in duration:
                            hours = float(duration.split(' ')[0])
                        else:
                            hours = 1
                    elif 'day' in duration:
                        if 'days' in duration:
                            days = float(duration.split(' ')[0])
                            hours = days * 24
                        else:
                            hours = 24
                    else:
                        hours = 1
                    
                    total_hourly_amount += total_count * hours
                
                # Display results
                if speedup_totals:
                    # Create two columns for layout
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("**Total Speedup Items (Top 50 Players)**")
                        
                        # Create a table of speedup totals
                        speedup_df_data = []
                        for item_key, data in speedup_totals.items():
                            speedup_df_data.append({
                                'Item': data['name'],
                                'Duration': data['duration'],
                                'Total Count': data['total'],
                                'Per Player': f"{data['total'] / 50:.1f}"
                            })
                        
                        if speedup_df_data:
                            speedup_df = pd.DataFrame(speedup_df_data)
                            speedup_df = speedup_df.sort_values('Total Count', ascending=False)
                            st.dataframe(speedup_df, width='stretch', hide_index=True)
                    
                    with col2:
                        st.markdown("**Combined Hourly Impact**")
                        
                        # Display total hourly amount
                        st.metric(
                            "Total Hours of Speedups",
                            f"{total_hourly_amount:,.0f}",
                            help="Combined speedup hours from all top 50 players"
                        )
                        
                        # Show top 3 items by count
                        if speedup_df_data:
                            top_items = sorted(speedup_df_data, key=lambda x: x['Total Count'], reverse=True)[:3]
                            st.markdown("**Top 3 Items:**")
                            for item in top_items:
                                st.markdown(f"• {item['Item']}: {item['Total Count']:,}")
                
                else:
                    st.info("No speedup items found in top 50 players")
                    
        except Exception as e:
            st.error(f"Error calculating speedup data: {e}")
    else:
        st.info("No player data available for speedup analysis")
