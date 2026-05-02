import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from cache_manager import cache_manager
import plotly.express as px
import plotly.graph_objects as go

def normalize_store_name(product_id):
    """Normalize store purchase names to be more readable"""
    name_mapping = {
        'adventurer_pack': 'Adventurer Pack',
        'basic_water_supplies': 'Basic Water Supplies',
        'conqueror_pack': 'Conqueror Pack',
        'hanami_pass': 'Hanami Pass',
        'hero_pack': 'Hero Pack',
        'infinite_water_supplies': 'Infinite Water Supplies',
        'mega_water_supplies': 'Mega Water Supplies',
        'monthly_premium': 'Monthly Premium',
        'ruby_pack_x1250': 'Ruby Pack (1,250)',
        'ruby_pack_x250': 'Ruby Pack (250)',
        'ruby_pack_x3250': 'Ruby Pack (3,250)',
        'ruby_pack_x40': 'Ruby Pack (40)',
        'ruby_pack_x600': 'Ruby Pack (600)',
        'supreme_pack_founders': 'Supreme Pack (Founders)',
        'ultra_water_supplies': 'Ultra Water Supplies'
    }
    
    # Return mapped name or format the original ID
    if product_id in name_mapping:
        return name_mapping[product_id]
    else:
        # Format unknown names: replace underscores with spaces and capitalize
        return product_id.replace('_', ' ').title()

@st.fragment
def create_purchases_tab(filtered_df):
    """Create the Purchases tab"""
    
    # Get the latest comprehensive data to extract purchase information
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
    
    if latest_comprehensive_data is None:
        st.warning("No comprehensive player data found.")
        return
    
    # Get the raw player data
    player_data = latest_comprehensive_data
    
    # Build player names list and mapping from the raw player data
    player_names = []
    player_id_mapping = {}
    
    if 'username' in player_data.columns and 'account_id' in player_data.columns:
        for _, player in player_data.iterrows():
            username = player['username']
            account_id = player['account_id']
            if pd.notna(username) and pd.notna(account_id):
                player_names.append(username)
                player_id_mapping[username] = account_id
    
    # Enhanced Purchases Overview
    st.markdown("---")
    
    # Process all purchase data for analytics
    all_shop_purchases = []
    all_store_purchases = []
    purchase_timeline = []
    
    # Process shop purchases
    if 'shop_purchases' in player_data.columns:
        for _, row in player_data.iterrows():
            if pd.notna(row['shop_purchases']) and row['shop_purchases']:
                username = row['username']
                account_id = row['account_id']
                purchases = row['shop_purchases'].split('|')
                for purchase in purchases:
                    if ':' in purchase:
                        parts = purchase.split(':')
                        if len(parts) >= 3:
                            item_name = parts[0]
                            amount = parts[1]
                            # Handle different formats - timestamp could be split across multiple parts
                            purchased_at = None
                            timestamp_parts = []
                            
                            # Collect timestamp parts (starting from index 2)
                            for part in parts[2:]:
                                if len(part) >= 10 and part[4] == '-' and part[7] == '-':
                                    # This looks like a date part
                                    timestamp_parts.append(part)
                                elif len(part) == 2 and part.isdigit():
                                    # This looks like minutes or seconds
                                    timestamp_parts.append(part)
                                elif len(timestamp_parts) > 0:
                                    # Continue collecting parts after we found a date
                                    timestamp_parts.append(part)
                                else:
                                    # Haven't found date yet, continue
                                    continue
                            
                            # Reconstruct timestamp
                            if timestamp_parts:
                                if len(timestamp_parts) == 1 and len(timestamp_parts[0]) >= 19:
                                    # Full timestamp in one part
                                    purchased_at = timestamp_parts[0][:19]
                                elif len(timestamp_parts) >= 3:
                                    # Split timestamp like ['2026-04-05 15', '17', '02']
                                    purchased_at = f"{timestamp_parts[0]}:{timestamp_parts[1]}:{timestamp_parts[2]}"
                                    if len(purchased_at) > 19:
                                        purchased_at = purchased_at[:19]
                                else:
                                    # Try to join what we have
                                    purchased_at = ':'.join(timestamp_parts)
                                    if len(purchased_at) > 19:
                                        purchased_at = purchased_at[:19]
                            else:
                                purchased_at = parts[2]  # Fallback to third part
                            try:
                                # Handle different timestamp formats
                                if len(purchased_at) == 19:  # Format: YYYY-MM-DD HH:MM:SS
                                    purchase_date = datetime.strptime(purchased_at, "%Y-%m-%d %H:%M:%S")
                                elif len(purchased_at) > 19:  # Format might be longer, truncate
                                    purchase_date = datetime.strptime(purchased_at[:19], "%Y-%m-%d %H:%M:%S")
                                else:
                                    # Try to parse as is, or skip if invalid
                                    purchase_date = datetime.strptime(purchased_at, "%Y-%m-%d %H:%M:%S")
                                
                                all_shop_purchases.append({
                                    'username': username,
                                    'item_name': item_name,
                                    'amount': int(amount) if amount.isdigit() else 0,
                                    'purchased_at': purchase_date,
                                    'type': 'Shop'
                                })
                                purchase_timeline.append({
                                    'date': purchase_date,
                                    'amount': int(amount) if amount.isdigit() else 0,
                                    'type': 'Shop',
                                    'item': item_name
                                })
                            except Exception as e:
                                # Skip invalid timestamps but continue processing
                                continue
    
    # Process store purchases
    if 'store_purchases' in player_data.columns:
        for _, row in player_data.iterrows():
            if pd.notna(row['store_purchases']) and row['store_purchases']:
                username = row['username']
                account_id = row['account_id']
                purchases = row['store_purchases'].split('|')
                for purchase in purchases:
                    if ':' in purchase:
                        parts = purchase.split(':')
                        if len(parts) >= 3:
                            product_id = parts[0]
                            amount = parts[1]
                            # Handle different formats - timestamp could be split across multiple parts
                            purchased_at = None
                            timestamp_parts = []
                            
                            # Collect timestamp parts (starting from index 2)
                            for part in parts[2:]:
                                if len(part) >= 10 and part[4] == '-' and part[7] == '-':
                                    # This looks like a date part
                                    timestamp_parts.append(part)
                                elif len(part) == 2 and part.isdigit():
                                    # This looks like minutes or seconds
                                    timestamp_parts.append(part)
                                elif len(timestamp_parts) > 0:
                                    # Continue collecting parts after we found a date
                                    timestamp_parts.append(part)
                                else:
                                    # Haven't found date yet, continue
                                    continue
                            
                            # Reconstruct timestamp
                            if timestamp_parts:
                                if len(timestamp_parts) == 1 and len(timestamp_parts[0]) >= 19:
                                    # Full timestamp in one part
                                    purchased_at = timestamp_parts[0][:19]
                                elif len(timestamp_parts) >= 3:
                                    # Split timestamp like ['2026-04-05 15', '17', '02']
                                    purchased_at = f"{timestamp_parts[0]}:{timestamp_parts[1]}:{timestamp_parts[2]}"
                                    if len(purchased_at) > 19:
                                        purchased_at = purchased_at[:19]
                                else:
                                    # Try to join what we have
                                    purchased_at = ':'.join(timestamp_parts)
                                    if len(purchased_at) > 19:
                                        purchased_at = purchased_at[:19]
                            else:
                                purchased_at = parts[2]  # Fallback to third part
                            try:
                                # Handle different timestamp formats
                                if len(purchased_at) == 19:  # Format: YYYY-MM-DD HH:MM:SS
                                    purchase_date = datetime.strptime(purchased_at, "%Y-%m-%d %H:%M:%S")
                                elif len(purchased_at) > 19:  # Format might be longer, truncate
                                    purchase_date = datetime.strptime(purchased_at[:19], "%Y-%m-%d %H:%M:%S")
                                else:
                                    # Try to parse as is, or skip if invalid
                                    purchase_date = datetime.strptime(purchased_at, "%Y-%m-%d %H:%M:%S")
                                
                                all_store_purchases.append({
                                    'username': username,
                                    'product_id': product_id,
                                    'amount': int(amount) if amount.isdigit() else 0,
                                    'purchased_at': purchase_date,
                                    'type': 'Store'
                                })
                                purchase_timeline.append({
                                    'date': purchase_date,
                                    'amount': int(amount) if amount.isdigit() else 0,
                                    'type': 'Store',
                                    'item': product_id
                                })
                            except Exception as e:
                                # Skip invalid timestamps but continue processing
                                continue
    
    # Calculate total purchases for header
    total_shop_count = len(all_shop_purchases)
    total_store_count = len(all_store_purchases)
    
    # Update header with total counts
    st.markdown(f"#### 📊 Purchases Overview (Shop: {total_shop_count}, Store: {total_store_count})")
    
    # Create timeline dataframe
    if purchase_timeline:
        timeline_df = pd.DataFrame(purchase_timeline)
        
        # Total Purchases Over Time Chart
        st.markdown("**📈 Total Purchases Over Time**")
        
        # Group by date and type
        daily_purchases = timeline_df.groupby([timeline_df['date'].dt.date, 'type']).agg({
            'amount': 'sum'
        }).reset_index()
        daily_purchases.columns = ['date', 'type', 'total_amount']
        
        # Create line chart
        fig_timeline = px.line(
            daily_purchases, 
            x='date', 
            y='total_amount',
            color='type',
            title='Daily Purchase Volume Over Time',
            markers=True,
            labels={'total_amount': 'Total Purchase Amount', 'date': 'Date', 'type': 'Purchase Type'}
        )
        fig_timeline.update_layout(
            xaxis_title="Date",
            yaxis_title="Total Purchase Amount",
            hovermode='x unified'
        )
        st.plotly_chart(fig_timeline, config={'displayModeBar': False})
        
        # Purchases in Last 24 Hours
        st.markdown("**⏰ Purchases in Last 24 Hours**")
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_purchases = timeline_df[timeline_df['date'] >= last_24h]
        
        if not recent_purchases.empty:
            recent_summary = recent_purchases.groupby('type').agg({
                'amount': 'sum',
                'item': 'count'
            }).reset_index()
            recent_summary.columns = ['type', 'total_amount', 'purchase_count']
            
            # All four metrics on one row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_recent = recent_purchases['amount'].sum()
                st.metric("Total Purchases (24h)", total_recent)
            with col2:
                # Count unique purchases as proxy for unique buyers
                unique_buyers = recent_purchases['item'].nunique()
                st.metric("Unique Items (24h)", unique_buyers)
            
            # Add Shop and Store purchase counts to the same row
            for i, (_, row) in enumerate(recent_summary.iterrows()):
                with [col3, col4][i]:
                    st.metric(f"{row['type']} Purchases", row['purchase_count'])
        else:
            st.info("No purchases in the last 24 hours.")
        
        # Top 10 Things Purchased - One Section Layout
        st.markdown("**🏆 Top 10 Most Purchased Items**")
        
        # Prepare shop and store data
        shop_item_counts = None
        store_item_counts = None
        
        if all_shop_purchases:
            shop_df = pd.DataFrame(all_shop_purchases)
            shop_item_counts = shop_df.groupby('item_name').agg({
                'amount': 'sum',
                'username': 'count'
            }).reset_index()
            shop_item_counts.columns = ['item', 'total_amount', 'purchase_count']
            shop_item_counts = shop_item_counts.sort_values('purchase_count', ascending=False).head(10)
        
        if all_store_purchases:
            store_df = pd.DataFrame(all_store_purchases)
            store_item_counts = store_df.groupby('product_id').agg({
                'amount': 'sum',
                'username': 'count'
            }).reset_index()
            store_item_counts.columns = ['item', 'total_amount', 'purchase_count']
            store_item_counts = store_item_counts.sort_values('purchase_count', ascending=False).head(10)
        
        # Create 4-column layout: shop on left, store on right
        col1, col2, col3, col4 = st.columns(4)
        
        # Shop Purchases (left 2 columns)
        if shop_item_counts is not None:
            with col1:
                st.markdown("**🛒 Shop**")
                for i, (_, row) in enumerate(shop_item_counts.iterrows(), 1):
                    if i <= 5:
                        st.markdown(f"{i}. **{row['item']}**: {row['purchase_count']}")
            
            with col2:
                for i, (_, row) in enumerate(shop_item_counts.iterrows(), 1):
                    if i > 5:
                        st.markdown(f"{i}. **{row['item']}**: {row['purchase_count']}")
        else:
            with col1:
                st.info("No shop data")
            with col2:
                st.empty()
        
        # Store Purchases (right 2 columns)
        if store_item_counts is not None:
            with col3:
                st.markdown("**💳 Store**")
                for i, (_, row) in enumerate(store_item_counts.iterrows(), 1):
                    if i <= 5:
                        normalized_name = normalize_store_name(row['item'])
                        st.markdown(f"{i}. **{normalized_name}**: {row['purchase_count']}")
            
            with col4:
                for i, (_, row) in enumerate(store_item_counts.iterrows(), 1):
                    if i > 5:
                        normalized_name = normalize_store_name(row['item'])
                        st.markdown(f"{i}. **{normalized_name}**: {row['purchase_count']}")
        else:
            with col3:
                st.info("No store data")
            with col4:
                st.empty()
        
        # Combined summary
        if all_shop_purchases and all_store_purchases:
            st.markdown("---")
            st.markdown("**📊 Purchase Summary**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_shop_items = len(all_shop_purchases)
                st.metric("Total Shop Purchases", total_shop_items)
            
            with col2:
                total_store_items = len(all_store_purchases)
                st.metric("Total Store Purchases", total_store_items)
            
            with col3:
                total_ratio = len(all_shop_purchases) / len(all_store_purchases) if len(all_store_purchases) > 0 else 0
                st.metric("Shop/Store Ratio", f"{total_ratio:.1f}:1")
        elif all_shop_purchases or all_store_purchases:
            st.info("Purchase data available for only one category.")
    
    # Player search section
    st.markdown("---")
    st.markdown("#### Player Search")
    
    if player_names:
        # Render player search
        render_player_search(player_names, player_data, player_id_mapping)
    else:
        st.info("No players found in player data.")
    
    # Load shop purchases from comprehensive data
    st.markdown("---")
    st.markdown("#### Shop Purchases")
    
    # Process shop purchases from comprehensive data
    shop_purchases_data = []
    if 'shop_purchases' in player_data.columns:
        for _, row in player_data.iterrows():
            if pd.notna(row['shop_purchases']) and row['shop_purchases']:
                username = row['username']
                account_id = row['account_id']
                # Parse shop purchases: format "item_name:amount:purchased_at|item_name:amount:purchased_at"
                purchases = row['shop_purchases'].split('|')
                for purchase in purchases:
                    if ':' in purchase:
                        parts = purchase.split(':')
                        if len(parts) >= 3:
                            item_name = parts[0]
                            amount = parts[1]
                            purchased_at = parts[2]
                            shop_purchases_data.append({
                                'username': username,
                                'player_id': account_id,
                                'item_name': item_name,
                                'amount': int(amount) if amount.isdigit() else 0,
                                'purchased_at': purchased_at
                            })
    
    if shop_purchases_data:
        shop_df = pd.DataFrame(shop_purchases_data)
        st.info(f"Found {len(shop_df)} shop purchases")
        
        # Group by player
        shop_by_player = shop_df.groupby('player_id').agg({
            'item_name': list,
            'amount': list,
            'purchased_at': list,
            'username': 'first'
        }).reset_index()
        shop_by_player['total_purchases'] = shop_by_player['item_name'].apply(len)
        shop_by_player = shop_by_player.sort_values('total_purchases', ascending=False).head(20)
        
        if not shop_by_player.empty:
            st.markdown("**Top Shop Purchasers**")
            for _, row in shop_by_player.iterrows():
                player_name = row['username']
                with st.expander(f"{player_name} - {row['total_purchases']} purchases"):
                    for i, (item, amount, date) in enumerate(zip(row['item_name'], row['amount'], row['purchased_at'])):
                        st.markdown(f"- {item} (x{amount}) on {date}")
        
        # Purchase statistics
        st.markdown("---")
        st.markdown("#### Purchase Overview")
        st.markdown("**Shop Purchase Statistics**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Shop Purchases", len(shop_df))
        with col2:
            unique_players = shop_df['player_id'].nunique()
            st.metric("Unique Players", unique_players)
        with col3:
            avg_purchases = len(shop_df) / unique_players if unique_players > 0 else 0
            st.metric("Avg Purchases/Player", f"{avg_purchases:.1f}")
        
        # Detailed item breakdown
        item_breakdown = shop_df.groupby('item_name').agg({
            'amount': 'sum',
            'player_id': 'count'
        }).reset_index()
        item_breakdown.columns = ['Item', 'Total Amount', 'Purchase Count']
        item_breakdown = item_breakdown.sort_values('Purchase Count', ascending=False)
        
        st.markdown("**Shop Item Breakdown**")
        st.dataframe(item_breakdown, hide_index=True, width='stretch')
    else:
        st.info("No shop purchases found in the data.")
    
    # Load store purchases from comprehensive data
    st.markdown("---")
    st.markdown("#### Store Purchases")
    
    # Process store purchases from comprehensive data
    store_purchases_data = []
    if 'store_purchases' in player_data.columns:
        for _, row in player_data.iterrows():
            if pd.notna(row['store_purchases']) and row['store_purchases']:
                username = row['username']
                account_id = row['account_id']
                # Parse store purchases: format "product_id:amount:purchased_at|product_id:amount:purchased_at"
                purchases = row['store_purchases'].split('|')
                for purchase in purchases:
                    if ':' in purchase:
                        parts = purchase.split(':')
                        if len(parts) >= 3:
                            product_id = parts[0]
                            amount = parts[1]
                            purchased_at = parts[2]
                            store_purchases_data.append({
                                'username': username,
                                'player_id': account_id,
                                'product_id': product_id,
                                'amount': int(amount) if amount.isdigit() else 0,
                                'purchased_at': purchased_at
                            })
    
    if store_purchases_data:
        store_df = pd.DataFrame(store_purchases_data)
        st.info(f"Found {len(store_df)} store purchases")
        
        # Group by player
        store_by_player = store_df.groupby('player_id').agg({
            'product_id': list,
            'amount': list,
            'purchased_at': list,
            'username': 'first'
        }).reset_index()
        store_by_player['total_purchases'] = store_by_player['product_id'].apply(len)
        store_by_player = store_by_player.sort_values('total_purchases', ascending=False).head(20)
        
        if not store_by_player.empty:
            st.markdown("**Top Store Purchasers**")
            for _, row in store_by_player.iterrows():
                player_name = row['username']
                with st.expander(f"{player_name} - {row['total_purchases']} purchases"):
                    for i, (product, amount, date) in enumerate(zip(row['product_id'], row['amount'], row['purchased_at'])):
                        normalized_name = normalize_store_name(product)
                        st.markdown(f"- {normalized_name} (x{amount}) on {date}")
        
        # Store purchase statistics
        st.markdown("---")
        st.markdown("#### Store Purchase Overview")
        st.markdown("**Store Purchase Statistics**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Store Purchases", len(store_df))
        with col2:
            unique_players = store_df['player_id'].nunique()
            st.metric("Unique Players", unique_players)
        with col3:
            avg_purchases = len(store_df) / unique_players if unique_players > 0 else 0
            st.metric("Avg Purchases/Player", f"{avg_purchases:.1f}")
        
        # Top products
        top_products = store_df['product_id'].value_counts().head(10)
        st.markdown("**Top Store Products**")
        for product, count in top_products.items():
            normalized_name = normalize_store_name(product)
            st.markdown(f"- {normalized_name}: {count} purchases")
    else:
        st.info("No store purchases found in the data.")

@st.fragment
def render_player_search(player_names, player_data, player_id_mapping):
    """Fragment for player search - only reruns when search input changes"""
    # Search box
    search_query = st.text_input("Search for a player:", placeholder="Type player name...", key="purchases_player_search")
    
    # Filter player options based on search
    if search_query:
        filtered_options = [opt for opt in player_names if search_query.lower() in opt.lower()]
    else:
        filtered_options = player_names[:100]  # Show first 100 by default
    
    if filtered_options:
        # Default to logged-in user if they're one of the four authorized users
        authorized_users = ['Gonhog', 'Moachi', 'Skenz', 'Higgins']
        default_index = 0
        if 'username' in st.session_state and st.session_state.username in authorized_users:
            logged_in_user = st.session_state.username
            # Find the index of the logged-in user in filtered_options
            for i, option in enumerate(filtered_options):
                if option == logged_in_user:
                    default_index = i
                    break
        
        selected_player_name = st.selectbox("Select a player:", options=filtered_options, index=default_index, key="purchases_player_select")
        
        # Get player_id from mapping
        player_id = player_id_mapping.get(selected_player_name)
        
        # Load and display player's purchases from comprehensive data
        if player_id:
            st.markdown(f"#### Purchases for {selected_player_name}")
            
            # Get player's data from the player_data dataframe
            player_record = player_data[player_data['account_id'] == player_id]
            
            if not player_record.empty:
                player_row = player_record.iloc[-1]  # Get latest data
                
                # Shop purchases
                st.markdown("**Shop Purchases:**")
                if 'shop_purchases' in player_row and pd.notna(player_row['shop_purchases']) and player_row['shop_purchases']:
                    shop_purchases = player_row['shop_purchases'].split('|')
                    shop_data = []
                    for purchase in shop_purchases:
                        if ':' in purchase:
                            parts = purchase.split(':')
                            if len(parts) >= 3:
                                item_name = parts[0]
                                amount = parts[1]
                                purchased_at = parts[2]
                                shop_data.append({
                                    'Item': item_name,
                                    'Amount': int(amount) if amount.isdigit() else 0,
                                    'Purchased At': purchased_at
                                })
                    
                    if shop_data:
                        shop_df_display = pd.DataFrame(shop_data)
                        shop_df_display = shop_df_display.sort_values('Purchased At', ascending=False)
                        st.dataframe(shop_df_display, hide_index=True, width='stretch')
                    else:
                        st.info("No shop purchases found for this player.")
                else:
                    st.info("No shop purchases found for this player.")
                
                # Store purchases
                st.markdown("**Store Purchases:**")
                if 'store_purchases' in player_row and pd.notna(player_row['store_purchases']) and player_row['store_purchases']:
                    store_purchases = player_row['store_purchases'].split('|')
                    store_data = []
                    for purchase in store_purchases:
                        if ':' in purchase:
                            parts = purchase.split(':')
                            if len(parts) >= 3:
                                product_id = parts[0]
                                amount = parts[1]
                                purchased_at = parts[2]
                                store_data.append({
                                    'Product': product_id,
                                    'Amount': int(amount) if amount.isdigit() else 0,
                                    'Purchased At': purchased_at
                                })
                    
                    if store_data:
                        store_df_display = pd.DataFrame(store_data)
                        store_df_display = store_df_display.sort_values('Purchased At', ascending=False)
                        st.dataframe(store_df_display, hide_index=True, width='stretch')
                    else:
                        st.info("No store purchases found for this player.")
                else:
                    st.info("No store purchases found for this player.")
                
                # Purchase summary
                st.markdown("**Purchase Summary:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_shop = player_row.get('total_shop_purchases', 0)
                    st.metric("Shop Purchases", int(total_shop))
                with col2:
                    total_store = player_row.get('total_store_purchases', 0)
                    st.metric("Store Purchases", int(total_store))
                with col3:
                    total_all = player_row.get('total_purchases', 0)
                    st.metric("Total Purchases", int(total_all))
            else:
                st.warning("Player data not found.")
    else:
        st.info("No players found matching your search.")
