import streamlit as st
import pandas as pd
import os
import json
from cache_manager import cache_manager

@st.fragment
def create_purchases_tab():
    """Create the Purchases tab"""
    st.markdown("### Purchases")
    
    # Get data from the main dataframe (loaded from GitHub via cache manager)
    df = st.session_state.get('data', pd.DataFrame())
    
    if df.empty:
        st.warning("No data available. Please load data first.")
        return
    
    # Build player names list and mapping from the loaded data
    player_names = []
    player_id_mapping = {}
    
    if 'username' in df.columns and 'account_id' in df.columns:
        for _, player in df.iterrows():
            username = player['username']
            account_id = player['account_id']
            if pd.notna(username) and pd.notna(account_id):
                player_names.append(username)
                player_id_mapping[username] = account_id
    
    # Player search section
    st.markdown("---")
    st.markdown("#### Player Search")
    
    if player_names:
        # Render player search
        render_player_search(player_names, df, player_id_mapping)
    else:
        st.info("No players found in player data.")
    
    # Load shop purchases from comprehensive data
    st.markdown("---")
    st.markdown("#### Shop Purchases")
    
    # Process shop purchases from comprehensive data
    shop_purchases_data = []
    if 'shop_purchases' in df.columns:
        for _, row in df.iterrows():
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
        st.dataframe(item_breakdown, width='stretch', hide_index=True)
    else:
        st.info("No shop purchases found in the data.")
    
    # Load store purchases from comprehensive data
    st.markdown("---")
    st.markdown("#### Store Purchases")
    
    # Process store purchases from comprehensive data
    store_purchases_data = []
    if 'store_purchases' in df.columns:
        for _, row in df.iterrows():
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
                        st.markdown(f"- {product} (x{amount}) on {date}")
        
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
            st.markdown(f"- {product}: {count} purchases")
    else:
        st.info("No store purchases found in the data.")

@st.fragment
def render_player_search(player_names, df, player_id_mapping):
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
            
            # Get player's data from the main dataframe
            player_data = df[df['account_id'] == player_id]
            
            if not player_data.empty:
                player_row = player_data.iloc[-1]  # Get latest data
                
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
                        st.dataframe(shop_df_display, width='stretch', hide_index=True)
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
                        st.dataframe(store_df_display, width='stretch', hide_index=True)
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
