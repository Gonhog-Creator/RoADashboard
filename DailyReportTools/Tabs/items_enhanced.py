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
    """Enhanced categorization for comprehensive item data"""
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
    
    # Special Items - include special game items
    special_items = [
        'fortuna', 'medallion', 'ticket', 'vault', 'warp', 'device', 'seal', 'heart',
        'agreement', 'treaty', 'curse', 'bull', 'light', 'ration', 'dust', 'powder', 'infusion'
    ]
    
    if any(special in name_lower for special in special_items):
        return "Special Items"
    
    # Default category
    return "Other Items"

def create_items_tab(df):
    """Enhanced Items tab with comprehensive data support"""
    if df.empty:
        st.warning("No data available for items analysis")
        return
    
    st.markdown("### Items Enhanced Item Analysis")
    
    # Check if we have comprehensive data
    latest_data = df.iloc[-1]
    
    if 'raw_player_data' in latest_data:
        # Comprehensive CSV format
        player_df = latest_data['raw_player_data']
        
        # Check if player_df is actually a DataFrame
        if not isinstance(player_df, pd.DataFrame) or player_df.empty:
            st.warning("Raw player data is not available or not in expected format")
            return
        
        # Get all item columns
        item_columns = [col for col in player_df.columns if col.startswith('item_')]
        
        if not item_columns:
            st.warning("No item columns found in the comprehensive data")
            return
        
        st.info(f"Found {len(item_columns)} different item types in the comprehensive data")
        
        # Calculate item statistics
        item_stats = {}
        for col in item_columns:
            item_name = col.replace('item_', '')
            total_count = player_df[col].fillna(0).sum()
            players_with_item = (player_df[col] > 0).sum()
            
            if total_count > 0:
                item_stats[item_name] = {
                    'total_count': total_count,
                    'players_with_item': players_with_item,
                    'avg_per_player': total_count / players_with_item if players_with_item > 0 else 0,
                    'max_single_player': player_df[col].max()
                }
        
        # Categorize items
        categorized_items = {}
        for item_name, stats in item_stats.items():
            category = categorize_item(item_name)
            if category not in categorized_items:
                categorized_items[category] = {}
            categorized_items[category][item_name] = stats
        
        # Sort categories and items
        sorted_categories = dict(sorted(categorized_items.items()))
        for category in sorted_categories:
            sorted_categories[category] = dict(sorted(sorted_categories[category].items(), 
                                                    key=lambda x: x[1]['total_count'], reverse=True))
        
        # Category overview
        st.markdown("#### Stats Item Categories Overview")
        
        category_overview = []
        for category, items in sorted_categories.items():
            total_items = sum(stats['total_count'] for stats in items.values())
            unique_items = len(items)
            category_overview.append({
                'Category': category,
                'Total Items': total_items,
                'Unique Types': unique_items,
                'Avg per Type': total_items / unique_items if unique_items > 0 else 0
            })
        
        category_df = pd.DataFrame(category_overview)
        category_df = category_df.sort_values('Total Items', ascending=False)
        
        # Display category metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Items Total Item Types", len(item_stats))
        
        with col2:
            st.metric("Categories Categories", len(sorted_categories))
        
        with col3:
            total_all_items = sum(stats['total_count'] for stats in item_stats.values())
            st.metric("Total Total Items", f"{total_all_items:,}")
        
        with col4:
            st.metric("Players Players with Items", f"{len(player_df):,}")
        
        # Category chart
        fig_categories = px.bar(
            category_df,
            x='Category',
            y='Total Items',
            title='Items by Category',
            color='Total Items',
            color_continuous_scale='viridis'
        )
        fig_categories.update_layout(
            xaxis_title="Category",
            yaxis_title="Total Count",
            height=400
        )
        st.plotly_chart(fig_categories, use_container_width=True)
        
        # Category table
        st.dataframe(category_df, use_container_width=True)
        
        # Item selection by category
        st.markdown("#### Analysis Detailed Item Analysis")
        
        selected_category = st.selectbox(
            "Select a category to analyze:",
            options=list(sorted_categories.keys()),
            index=0
        )
        
        if selected_category:
            category_items = sorted_categories[selected_category]
            
            if category_items:
                # Create item dataframe for this category
                item_data = []
                for item_name, stats in category_items.items():
                    item_data.append({
                        'Item Name': normalize_item_name(item_name),
                        'Total Count': stats['total_count'],
                        'Players with Item': stats['players_with_item'],
                        'Avg per Player': f"{stats['avg_per_player']:.1f}",
                        'Max Single Player': stats['max_single_player']
                    })
                
                item_df = pd.DataFrame(item_data)
                st.dataframe(item_df, use_container_width=True)
                
                # Top items visualization
                top_items = item_df.head(10)
                
                fig_items = px.bar(
                    top_items,
                    x='Total Count',
                    y='Item Name',
                    orientation='h',
                    title=f'Top 10 {selected_category}',
                    color='Total Count',
                    color_continuous_scale='viridis'
                )
                fig_items.update_layout(
                    xaxis_title="Total Count",
                    yaxis_title="Item Name",
                    height=500
                )
                st.plotly_chart(fig_items, use_container_width=True)
                
                # Individual item analysis
                selected_item = st.selectbox(
                    "Select an item for detailed analysis:",
                    options=list(category_items.keys()),
                    format_func=normalize_item_name,
                    index=0
                )
                
                if selected_item:
                    item_col = f'item_{selected_item}'
                    
                    if item_col in player_df.columns:
                        st.markdown(f"##### Players Players with {normalize_item_name(selected_item)}")
                        
                        # Get players with this item
                        item_players = player_df[player_df[item_col] > 0][
                            ['account_id', 'alliance_name', 'power', item_col]
                        ].copy()
                        item_players.columns = ['Account ID', 'Alliance', 'Power', 'Item Count']
                        item_players['Account ID'] = item_players['Account ID'].str[:8] + "..."
                        item_players = item_players.sort_values('Item Count', ascending=False)
                        
                        st.dataframe(item_players.head(20), use_container_width=True)
                        
                        # Item distribution
                        fig_distribution = px.histogram(
                            item_players,
                            x='Item Count',
                            title=f'Distribution of {normalize_item_name(selected_item)}',
                            nbins=20
                        )
                        fig_distribution.update_layout(height=400)
                        st.plotly_chart(fig_distribution, use_container_width=True)
                        
                        # Power correlation
                        if 'Power' in item_players.columns:
                            fig_power = px.scatter(
                                item_players,
                                x='Item Count',
                                y='Power',
                                title=f'{normalize_item_name(selected_item)} vs Power',
                                color='Alliance',
                                hover_data=['Account ID']
                            )
                            fig_power.update_layout(height=400)
                            st.plotly_chart(fig_power, use_container_width=True)
        
        # Time series analysis (if multiple data points available)
        if len(df) > 1:
            st.markdown("#### Trends Item Trends Over Time")
            
            # Select top items for trend analysis
            top_5_items = sorted(item_stats.items(), key=lambda x: x[1]['total_count'], reverse=True)[:5]
            
            if top_5_items:
                # Create time series data
                trend_data = []
                
                for _, row in df.iterrows():
                    date = row['date']
                    if 'raw_player_data' in row:
                        player_data = row['raw_player_data']
                        
                        for item_name, _ in top_5_items:
                            item_col = f'item_{item_name}'
                            if item_col in player_data.columns:
                                count = player_data[item_col].fillna(0).sum()
                                trend_data.append({
                                    'Date': date,
                                    'Item': normalize_item_name(item_name),
                                    'Count': count
                                })
                
                if trend_data:
                    trend_df = pd.DataFrame(trend_data)
                    
                    fig_trend = px.line(
                        trend_df,
                        x='Date',
                        y='Count',
                        color='Item',
                        title='Top 5 Items Trend Over Time',
                        markers=True
                    )
                    fig_trend.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Total Count",
                        height=500
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
    
    else:
        # Fallback to original items tab logic for legacy format
        st.info("Warning Using legacy item analysis. For enhanced features, use the comprehensive CSV format.")
        
        # Call the original items tab logic
        try:
            from Tabs.items import create_items_tab as original_items_tab
            original_items_tab(df)
        except ImportError:
            st.error("Could not load original items tab functionality")
