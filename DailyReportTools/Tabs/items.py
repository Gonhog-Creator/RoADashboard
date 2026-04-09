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
            
            if time_diff > 0.1:  # Only calculate rate if time difference is significant
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return daily_rates

def normalize_item_name(name):
    """Normalize item names for better display"""
    if not name or pd.isna(name):
        return ""
    
    # Convert to lowercase and replace common separators with space
    normalized = str(name).lower().replace('_', ' ').replace('-', ' ')
    
    # Remove extra spaces and strip
    normalized = ' '.join(normalized.split()).strip()
    
    # Capitalize each word (title case)
    normalized = ' '.join(word.capitalize() for word in normalized.split())
    
    return normalized

def categorize_item(item_name):
    """Categorize items based on their names"""
    name_lower = item_name.lower()
    
    # Chests - include all chest-related items and special packs
    if 'chest' in name_lower or ('pack' in name_lower and any(pack_type in name_lower for pack_type in ['supreme', 'welcome'])):
        return "Chests"
    
    # Dragon Armor - include all dragon armor items
    if 'dragon' in name_lower and 'armor' in name_lower:
        return "Dragon Armor"
    
    # Troops - include all troop-related packs (check this BEFORE resource packs)
    troop_names = [
        'armored transport', 'battle dragon', 'conscript', 'fire mirror', 'giant',
        'halberdsman', 'longbowman', 'longbowmen', 'minotaur', 'porter', 'spy', 
        'swift strike dragon', 'silver serpent', 'fangtooth'
    ]
    
    # Also check for underscore versions of troop names
    troop_names_underscore = [
        'armored_transport', 'battle_dragon', 'conscript', 'fire_mirror', 'giant',
        'halberdsman', 'longbow_man', 'longbowmen', 'minotaur', 'porter', 'spy', 
        'swift_strike_dragon', 'silver_serpent', 'fangtooth'
    ]
    
    # Debug: Check if this is a troop pack
    is_pack = 'pack' in name_lower
    found_troop = None
    for troop in troop_names + troop_names_underscore:
        if troop in name_lower:
            found_troop = troop
            break
    
    if is_pack and found_troop:
        return "Troops"
    
    # Resource Packs - include all resource-related items and elixir packs/million elixirs
    if ('pack' in name_lower and any(resource in name_lower for resource in ['lumber', 'gold', 'stone', 'metal', 'food', 'ruby'])) or \
       any(resource in name_lower for resource in ['lumber', 'gold', 'stone', 'metal', 'food', 'ruby', 'wood', 'iron', 'silver', 'copper', 'coal', 'crystal', 'gem']) or \
       ('elixir' in name_lower and ('pack' in name_lower or 'million' in name_lower)) or \
       ('all' in name_lower and 'resource' in name_lower and 'pack' in name_lower) or \
       ('random' in name_lower and 'resource' in name_lower and 'pack' in name_lower):
        return "Resource Packs"
    
    # Speedups - include all speedup items from the speedups tab (but not elixir packs or million elixirs)
    speedup_items = [
        'blink', 'hop', 'skip', 'jump', 'leap', 'bounce', 'bore', 'bolt', 'blitz', 'blast',
        'testronius dust', 'testronius powder', 'testronius infusion'
    ]
    
    # Check for specific speedup items (handle both spaces and underscores)
    for speedup in speedup_items:
        search_key = speedup.replace(' ', '_')
        if search_key in name_lower or speedup in name_lower:
            return "Speedups"
    
    # Check for general speedup keywords and multipliers
    if any(speedup in name_lower for speedup in ['speedup', 'boost', 'acceleration']) or any(x in name_lower for x in ['_x5', '_x10', '_x15']):
        return "Speedups"
    
    # Check for march drops and individual elixirs (not packs, not million elixirs)
    if any(march in name_lower for march in ['march', 'drop']) or \
       (any(enhance in name_lower for enhance in ['enhance', 'boost', 'power', 'strength']) and 
        'pack' not in name_lower and 'million' not in name_lower) or \
       ('elixir' in name_lower and 'pack' not in name_lower and 'million' not in name_lower):
        return "Speedups"
    
    # Default category
    return "ZZZ Other Items"

def create_items_tab(df):
    """Create Items tab with categorized multi-item selection and time series analysis"""
    if df.empty:
        st.warning("No data available for items analysis")
        return
    
    st.markdown("### 📦 Item Analysis")
    
    # Check if we have comprehensive data format
    latest_data = df.iloc[-1]
    use_comprehensive = 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None
    
    # Extract all unique items from all reports and check if they have any quantity > 0
    all_items = set()
    items_with_history = set()  # Track items that actually have data
    
    if use_comprehensive:
        # Comprehensive CSV format - extract from raw_player_data
        for _, row in df.iterrows():
            if 'raw_player_data' in row and row['raw_player_data'] is not None:
                player_df = row['raw_player_data']
                if isinstance(player_df, pd.DataFrame):
                    item_columns = [col for col in player_df.columns if col.startswith('item_')]
                    for col in item_columns:
                        item_name = col.replace('item_', '')
                        total_count = player_df[col].fillna(0).sum()
                        if total_count > 0:
                            all_items.add(item_name)
                            items_with_history.add(item_name)
    else:
        # Legacy format - extract from items dictionary
        for _, row in df.iterrows():
            if 'items' in row and isinstance(row['items'], dict):
                for item_name, quantity in row['items'].items():
                    if item_name and item_name.strip():
                        all_items.add(item_name)
                        # Only add to items_with_history if quantity > 0
                        if quantity > 0:
                            items_with_history.add(item_name)
    
    # Filter out items that have never had any quantity
    valid_items = items_with_history
    
    if not valid_items:
        st.warning("No items with quantity found in the data")
        return
    
    # Normalize and categorize items
    categorized_items = {}
    for original_name in valid_items:
        normalized = normalize_item_name(original_name)
        category = categorize_item(original_name)
        
        if category not in categorized_items:
            categorized_items[category] = {}
        categorized_items[category][normalized] = original_name
    
    # Sort categories and items within each category
    sorted_categories = dict(sorted(categorized_items.items()))
    for category in sorted_categories:
        sorted_categories[category] = dict(sorted(sorted_categories[category].items()))
    
    # Rename ZZZ Other Items back to just Other Items for display
    if 'ZZZ Other Items' in sorted_categories:
        sorted_categories['Other Items'] = sorted_categories.pop('ZZZ Other Items')
    
    # Multi-select checkboxes with collapsible categories
    st.markdown("#### 🔍 Select Items to Analyze")
    
    selected_items = []
    
    for category, items in sorted_categories.items():
        with st.expander(f"📁 {category} ({len(items)} items)", expanded=False):
            # Create columns for checkbox layout within each category
            num_items = len(items)
            # Prioritize columns first - create as many columns as items (up to 5)
            num_columns = min(5, num_items)  # Columns first approach
            
            if num_columns > 1:
                cols = st.columns(num_columns)
                for i, (normalized_name, original_name) in enumerate(items.items()):
                    col = cols[i % num_columns]
                    if col.checkbox(normalized_name, key=f"item_{original_name}"):
                        selected_items.append((normalized_name, original_name))
            else:
                # Single column if only 1 item
                for normalized_name, original_name in items.items():
                    if st.checkbox(normalized_name, key=f"item_{original_name}"):
                        selected_items.append((normalized_name, original_name))
    
    if selected_items:
        st.markdown(f"#### 📊 Analyzing {len(selected_items)} Selected Items")
        
        # Create subplots for multiple items (2 items per row, 4 columns total)
        num_selected = len(selected_items)
        if num_selected > 0:
            # Calculate rows needed (2 items per row = 4 charts per row)
            num_rows = (num_selected + 1) // 2  # Round up division
            
            # Create figure with subplots (2 charts per item: quantity + daily change)
            fig = make_subplots(
                rows=num_rows,
                cols=4,  # 4 charts per row (2 items * 2 charts each)
                subplot_titles=[f"{selected_items[i//2][0]} - {['Quantity', 'Daily Change'][i%2]}" 
                               for i in range(num_selected * 2)],
                vertical_spacing=0.06,
                horizontal_spacing=0.04,
                specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}] for _ in range(num_rows)]
            )
            
            # Color palette for different items
            colors = px.colors.qualitative.Set3[:num_selected]
            
            for idx, (normalized_name, original_name) in enumerate(selected_items):
                # Create time series data for selected item
                item_data = []
                for _, row in df.iterrows():
                    if use_comprehensive:
                        # Comprehensive CSV format - extract from raw_player_data
                        if 'raw_player_data' in row and row['raw_player_data'] is not None:
                            player_df = row['raw_player_data']
                            if isinstance(player_df, pd.DataFrame):
                                item_col = f'item_{original_name}'
                                if item_col in player_df.columns:
                                    quantity = player_df[item_col].fillna(0).sum()
                                    if quantity > 0:
                                        item_data.append({
                                            'date': row['date'],
                                            'quantity': quantity
                                        })
                    else:
                        # Legacy format - extract from items dictionary
                        if 'items' in row and isinstance(row['items'], dict):
                            quantity = row['items'].get(original_name, 0)
                            if quantity > 0:  # Only include if item exists and has quantity
                                item_data.append({
                                    'date': row['date'],
                                    'quantity': quantity
                                })
                
                if not item_data:
                    continue
                
                item_df = pd.DataFrame(item_data)
                item_df = item_df.sort_values('date')
                
                # Calculate row and column positions
                row = idx // 2 + 1  # 2 items per row
                amount_col = (idx % 2) * 2 + 1  # Amount charts in columns 1, 3
                change_col = (idx % 2) * 2 + 2  # Change charts in columns 2, 4
                
                # Add line chart (left column for this item)
                fig.add_trace(
                    go.Scatter(
                        x=item_df['date'],
                        y=item_df['quantity'],
                        mode='lines+markers',
                        name=normalized_name,
                        line=dict(color=colors[idx]),
                        marker=dict(color=colors[idx]),
                        hovertemplate=f'<b>{normalized_name}</b><br>Date: %{{x}}<br>Quantity: %{{y:,.0f}}<extra></extra>'
                    ),
                    row=int(row), col=int(amount_col)
                )
                
                # Add daily change chart (right column for this item) if we have enough data
                if len(item_df) >= 2:
                    values = item_df['quantity'].tolist()
                    dates = item_df['date'].tolist()
                    
                    # Calculate daily changes
                    daily_changes = calculate_daily_rate(values, dates)
                    
                    # Aggregate by date
                    date_df = pd.DataFrame({
                        'date': dates,
                        'daily_rate': daily_changes
                    })
                    daily_agg = date_df.groupby(date_df['date'].dt.date).agg({
                        'daily_rate': 'mean'
                    }).reset_index()
                    daily_agg['date'] = pd.to_datetime(daily_agg['date'])
                    
                    # Color bars based on positive/negative
                    bar_colors = ['green' if x >= 0 else 'red' for x in daily_agg['daily_rate']]
                    
                    fig.add_trace(
                        go.Bar(
                            x=daily_agg['date'],
                            y=daily_agg['daily_rate'],
                            name=f"{normalized_name} Daily Change",
                            marker=dict(color=bar_colors),
                            hovertemplate=f'<b>{normalized_name}</b><br>Date: %{{x}}<br>Daily Change: %{{y:,.2f}}<extra></extra>'
                        ),
                        row=int(row), col=int(change_col)
                    )
                else:
                    # Add empty bar chart if insufficient data
                    fig.add_trace(
                        go.Bar(
                            x=item_df['date'],
                            y=[0] * len(item_df),
                            name=f"{normalized_name} Daily Change",
                            marker=dict(color='lightgray'),
                            hovertemplate=f'<b>{normalized_name}</b><br>Insufficient data for daily change<extra></extra>'
                        ),
                        row=int(row), col=int(change_col)
                    )
            
            # Update layout
            fig.update_layout(
                height=250 * num_rows,  # Reduced height per row for tighter spacing
                title_text="Multi-Item Analysis - Quantity vs Daily Change",
                showlegend=False
            )
            
            # Update y-axes labels
            for i in range(num_selected):
                fig.update_yaxes(title_text="Quantity", row=(i//2)+1, col=(i%2)*2+1)
                fig.update_yaxes(title_text="Daily Change", row=(i//2)+1, col=(i%2)*2+2)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics for selected items
            st.markdown("#### 📈 Selected Items Summary")
            
            summary_data = []
            for normalized_name, original_name in selected_items:
                # Get latest data for each item
                item_data = []
                for _, row in df.iterrows():
                    if use_comprehensive:
                        # Comprehensive CSV format - extract from raw_player_data
                        if 'raw_player_data' in row and row['raw_player_data'] is not None:
                            player_df = row['raw_player_data']
                            if isinstance(player_df, pd.DataFrame):
                                item_col = f'item_{original_name}'
                                if item_col in player_df.columns:
                                    quantity = player_df[item_col].fillna(0).sum()
                                    if quantity > 0:
                                        item_data.append(quantity)
                    else:
                        # Legacy format - extract from items dictionary
                        if 'items' in row and isinstance(row['items'], dict):
                            quantity = row['items'].get(original_name, 0)
                            if quantity > 0:
                                item_data.append(quantity)
                
                if item_data:
                    summary_data.append({
                        'Item': normalized_name,
                        'Current': item_data[-1],
                        'Average': sum(item_data) / len(item_data),
                        'Peak': max(item_data),
                        'Data Points': len(item_data)
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                # Format for display
                summary_df['Current'] = summary_df['Current'].apply(lambda x: f"{int(x):,}")
                summary_df['Average'] = summary_df['Average'].apply(lambda x: f"{x:.1f}")
                summary_df['Peak'] = summary_df['Peak'].apply(lambda x: f"{int(x):,}")
                
                st.dataframe(summary_df, use_container_width=True)
        
    else:
        st.empty()
