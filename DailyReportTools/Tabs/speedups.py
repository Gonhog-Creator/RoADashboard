import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
            
            if time_diff > 0:
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return daily_rates

def create_speedups_tab(filtered_df):
    """Create speedups analysis tab - exact copy of resources tab structure"""
    
    if not filtered_df.empty:
        # Define speedup items in increasing order of time amount
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
        
        # Check if we have comprehensive data format (same as items tab)
        latest_data = filtered_df.iloc[-1]
        use_comprehensive = 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None
        
        # Get all item types and find speedup items (same logic as items tab)
        all_items = set()
        
        if use_comprehensive:
            # Comprehensive CSV format - extract from raw_player_data (same as items tab)
            for _, row in filtered_df.iterrows():
                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                    player_df = row['raw_player_data']
                    if isinstance(player_df, pd.DataFrame):
                        if 'items_json' in player_df.columns:
                            # Parse items from JSON format
                            for _, player_row in player_df.iterrows():
                                try:
                                    items_dict = json.loads(player_row['items_json'])
                                    all_items.update(items_dict.keys())
                                except:
                                    continue
                        else:
                            # Fallback to old format (individual item columns)
                            item_columns = [col for col in player_df.columns if col.startswith('item_')]
                            for col in item_columns:
                                item_name = col.replace('item_', '')
                                all_items.add(item_name)
        else:
            # Legacy format - extract from items dictionary
            for items in filtered_df['items']:
                if isinstance(items, dict) and items:
                    all_items.update(items.keys())
        
        # Find speedup items in the data (in order of time)
        available_speedups = []
        for speedup_key in speedup_items.keys():  # Use keys() to maintain order
            for item_name in all_items:
                # Handle both spaces and underscores for matching
                search_key = speedup_key.lower().replace(' ', '_')
                search_name = item_name.lower()
                if search_key in search_name or speedup_key.lower() in search_name:
                    available_speedups.append(speedup_key)
                    break
                    break
        
        if available_speedups:
            # Lock to available speedups only (no selector)
            selected_speedup_types = available_speedups
            
            if selected_speedup_types:
                # Define colors for each speedup type (same as resources)
                speedup_colors = {
                    'Blink': '#FFD700',      # Gold/Yellow
                    'Hop': '#F5DEB3',       # Wheat/Beige
                    'Skip': '#808080',      # Grey
                    'Jump': '#708090',      # Slate Grey
                    'Leap': '#E0115F',      # Ruby Red
                    'Bounce': '#9370DB',     # Medium Purple
                    'Bore': '#4B0082',      # Indigo
                    'Bolt': '#FF6347',      # Tomato
                    'Blitz': '#1E90FF',    # Dodger Blue
                    'Blast': '#FF69B4',     # Hot Pink
                    'Testronius Powder': '#FFA500',   # Orange
                    'Testronius Dust': '#9400D3',  # Violet
                    'Testronius Infusion': '#00CED1'   # Dark Turquoise
                }
                
                # Create charts for speedups
                # Calculate rows needed (2 speedups per row = 4 charts per row)
                num_speedups = len(selected_speedup_types)
                num_rows = (num_speedups + 1) // 2  # Round up division
                
                fig_speedups = make_subplots(
                    rows=num_rows, 
                    cols=4,  # 4 charts per row (2 speedups * 2 charts each)
                    subplot_titles=[f"{selected_speedup_types[i//2]} - {['Amount', 'Daily Change'][i%2]}" 
                                 for i in range(num_speedups * 2)],
                    vertical_spacing=0.06,  # Decreased spacing for tighter grid
                    horizontal_spacing=0.04,
                    specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}] for _ in range(num_rows)]
                )
                
                for i, speedup_type in enumerate(selected_speedup_types):
                    # Get color for this speedup
                    color = speedup_colors.get(speedup_type, '#333333')
                    
                    # Calculate row and column positions
                    row = i // 2 + 1  # 2 speedups per row
                    amount_col = (i % 2) * 2 + 1  # Amount charts in columns 1, 3
                    change_col = (i % 2) * 2 + 2  # Change charts in columns 2, 4
                    
                    # Overall amount (left column for this speedup) - Line chart
                    values = []
                    for _, data_row in filtered_df.iterrows():
                        count = 0
                        if use_comprehensive:
                            # Comprehensive CSV format - extract from raw_player_data
                            if 'raw_player_data' in data_row and data_row['raw_player_data'] is not None:
                                player_df = data_row['raw_player_data']
                                if isinstance(player_df, pd.DataFrame):
                                    if 'items_json' in player_df.columns:
                                        # Parse items from JSON format
                                        for _, player_row in player_df.iterrows():
                                            try:
                                                items_dict = json.loads(player_row['items_json'])
                                                for item_name, amount in items_dict.items():
                                                    # Handle both spaces and underscores for matching (exclude x5, x10, x15 variants)
                                                    search_key = speedup_type.lower().replace(' ', '_')
                                                    search_name = item_name.lower()
                                                    if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                        count += amount
                                            except:
                                                continue
                                    else:
                                        # Fallback to old format (individual item columns)
                                        for item_name in all_items:
                                            search_key = speedup_type.lower().replace(' ', '_')
                                            search_name = item_name.lower()
                                            if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                item_col = f'item_{item_name}'
                                                if item_col in player_df.columns:
                                                    count += player_df[item_col].fillna(0).sum()
                        else:
                            # Legacy format - extract from items dictionary
                            if isinstance(data_row['items'], dict) and data_row['items']:
                                for item_name, amount in data_row['items'].items():
                                    search_key = speedup_type.lower().replace(' ', '_')
                                    search_name = item_name.lower()
                                    if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                        count += amount
                        values.append(count)
                    
                    fig_speedups.add_trace(
                        go.Scatter(
                            x=filtered_df['date'],
                            y=values,
                            mode='lines+markers',
                            name=f"{speedup_type}",
                            line=dict(color=color),
                            marker=dict(color=color),
                            hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Amount: %{y:,.0f}<extra></extra>'
                        ),
                        row=int(row), col=int(amount_col)
                    )
                    
                    # Daily change (right column for this speedup) - Bar chart
                    if len(values) >= 2:
                        # Sort data by date to ensure correct chronological order
                        sorted_data = filtered_df.sort_values('date')
                        sorted_values = []
                        sorted_dates = []
                        for _, data_row in sorted_data.iterrows():
                            count = 0
                            if use_comprehensive:
                                # Comprehensive CSV format - extract from raw_player_data
                                if 'raw_player_data' in data_row and data_row['raw_player_data'] is not None:
                                    player_df = data_row['raw_player_data']
                                    if isinstance(player_df, pd.DataFrame):
                                        if 'items_json' in player_df.columns:
                                            # Parse items from JSON format
                                            for _, player_row in player_df.iterrows():
                                                try:
                                                    items_dict = json.loads(player_row['items_json'])
                                                    for item_name, amount in items_dict.items():
                                                        search_key = speedup_type.lower().replace(' ', '_')
                                                        search_name = item_name.lower()
                                                        if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                            count += amount
                                                except:
                                                    continue
                                        else:
                                            # Fallback to old format (individual item columns)
                                            for item_name in all_items:
                                                search_key = speedup_type.lower().replace(' ', '_')
                                                search_name = item_name.lower()
                                                if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                                    item_col = f'item_{item_name}'
                                                    if item_col in player_df.columns:
                                                        count += player_df[item_col].fillna(0).sum()
                            else:
                                # Legacy format - extract from items dictionary
                                if isinstance(data_row['items'], dict) and data_row['items']:
                                    for item_name, amount in data_row['items'].items():
                                        search_key = speedup_type.lower().replace(' ', '_')
                                        search_name = item_name.lower()
                                        if (search_key in search_name or speedup_type.lower() in search_name) and not any(x in search_name for x in ['_x5', '_x10', '_x15']):
                                            count += amount
                            sorted_values.append(count)
                            sorted_dates.append(data_row['date'])
                        
                        # Calculate true daily rates using time differences
                        daily_changes = calculate_daily_rate(sorted_values, sorted_dates)
                        
                        # Aggregate by date to show one bar per day
                        date_df = pd.DataFrame({
                            'date': sorted_dates,
                            'daily_rate': daily_changes
                        })
                        # Group by date and take the mean of daily rates for that day
                        daily_agg = date_df.groupby(date_df['date'].dt.date).agg({
                            'daily_rate': 'mean'
                        }).reset_index()
                        daily_agg['date'] = pd.to_datetime(daily_agg['date'])
                        
                        # Color bars based on positive/negative
                        bar_colors = ['green' if x >= 0 else 'red' for x in daily_agg['daily_rate']]
                        
                        fig_speedups.add_trace(
                            go.Bar(
                                x=daily_agg['date'],
                                y=daily_agg['daily_rate'],
                                name=f"{speedup_type} Daily Change",
                                marker=dict(color=bar_colors),
                                hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Daily Change: %{y:,.0f}<extra></extra>'
                            ),
                            row=int(row), col=int(change_col)
                        )
                
                fig_speedups.update_layout(
                    height=400 * num_rows,  # Height based on number of rows, not speedups
                    title_text="Speedup Analysis - Amount vs Daily Change",
                    showlegend=False
                )
                
                # Update x-axes labels for all charts
                for row in range(1, num_rows + 1):
                    for col in range(1, 5):  # 4 columns
                        fig_speedups.update_xaxes(
                            title_text="Date", 
                            row=row, col=col,
                            tickformat='%Y-%m-%d'  # Show only date, no time
                        )
                        fig_speedups.update_yaxes(
                            title_text="Amount" if col in [1, 3] else "Daily Change", 
                            row=row, col=col
                        )
                
                st.plotly_chart(fig_speedups, use_container_width=True)
        else:
            st.info("No speedup items found in the data.")
