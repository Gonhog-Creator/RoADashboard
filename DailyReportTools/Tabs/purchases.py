import streamlit as st
import pandas as pd
import os
import json
from cache_manager import cache_manager

@st.fragment
def create_purchases_tab():
    """Create the Purchases tab"""
    st.markdown("### 💳 Purchases")
    
    # Get paths to purchase CSV files
    database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'DatabaseParser')
    shop_purchase_path = os.path.join(database_path, 'shop_item_purchase.csv')
    store_purchase_path = os.path.join(database_path, 'store_purchase.csv')
    
    # Load player data from comprehensive CSV for player names
    comprehensive_csv_path = os.path.join(database_path, 'comprehensive_player_data_*.csv')
    import glob
    csv_files = glob.glob(comprehensive_csv_path)
    
    # Build player names list and mapping
    player_names = []
    player_id_mapping = {}
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getctime)
        try:
            player_df = pd.read_csv(latest_csv)
            if 'account_id' in player_df.columns and 'username' in player_df.columns:
                for _, player in player_df.iterrows():
                    account_id = player['account_id']
                    username = player['username']
                    player_names.append(username)
                    player_id_mapping[username] = account_id
        except:
            pass
    
    # Player search section
    st.markdown("---")
    st.markdown("#### 🔍 Player Search")
    
    if player_names:
        # Render player search
        render_player_search(player_names, shop_purchase_path, store_purchase_path, player_id_mapping)
    else:
        st.info("No players found in player data.")
    
    # Load shop purchases from separate CSV
    st.markdown("---")
    st.markdown("#### Shop Purchases")
    
    shop_df = None
    if os.path.exists(shop_purchase_path):
        try:
            shop_df = pd.read_csv(shop_purchase_path)
            if not shop_df.empty:
                st.info(f"Found {len(shop_df)} shop purchases")
                
                # Add player names from mapping
                if player_id_mapping:
                    shop_df['username'] = shop_df['player_id'].map({v: k for k, v in player_id_mapping.items()})
                
                # Group by player
                shop_by_player = shop_df.groupby('player_id').agg({
                    'item_name': list,
                    'amount': list,
                    'purchased_at': list,
                    'uuid': 'count'
                }).reset_index()
                shop_by_player.columns = ['player_id', 'items', 'amounts', 'purchase_dates', 'total_purchases']
                shop_by_player = shop_by_player.sort_values('total_purchases', ascending=False).head(20)
                
                if not shop_by_player.empty:
                    st.markdown("**Top Shop Purchasers**")
                    for _, row in shop_by_player.iterrows():
                        player_name = player_id_mapping.get(row['player_id'], row['player_id'])
                        with st.expander(f"{player_name} - {row['total_purchases']} purchases"):
                            for i, (item, amount, date) in enumerate(zip(row['items'], row['amounts'], row['purchase_dates'])):
                                st.markdown(f"- {item} (x{amount}) on {date}")
                
                # Detailed item breakdown
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
                    'uuid': 'count'
                }).reset_index()
                item_breakdown.columns = ['Item', 'Total Amount', 'Purchase Count']
                item_breakdown = item_breakdown.sort_values('Purchase Count', ascending=False)
                
                st.markdown("**Shop Item Breakdown**")
                st.dataframe(item_breakdown, width='stretch', hide_index=True)
        except Exception as e:
            st.error(f"Error loading shop purchases: {e}")
    else:
        st.info("Shop purchase file not found.")
    
    # Load store purchases from separate CSV
    st.markdown("---")
    st.markdown("#### Store Purchases")
    
    store_df = None
    if os.path.exists(store_purchase_path):
        try:
            store_df = pd.read_csv(store_purchase_path)
            if not store_df.empty:
                st.info(f"Found {len(store_df)} store purchases")
                
                # Add player names from mapping
                if player_id_mapping:
                    store_df['username'] = store_df['player_id'].map({v: k for k, v in player_id_mapping.items()})
                
                # Group by player
                store_by_player = store_df.groupby('player_id').agg({
                    'product_id': list,
                    'amount': list,
                    'purchased_at': list,
                    'uuid': 'count'
                }).reset_index()
                store_by_player.columns = ['player_id', 'products', 'amounts', 'purchase_dates', 'total_purchases']
                store_by_player = store_by_player.sort_values('total_purchases', ascending=False).head(20)
                
                if not store_by_player.empty:
                    st.markdown("**Top Store Purchasers**")
                    for _, row in store_by_player.iterrows():
                        player_name = player_id_mapping.get(row['player_id'], row['player_id'])
                        with st.expander(f"{player_name} - {row['total_purchases']} purchases"):
                            for i, (product, amount, date) in enumerate(zip(row['products'], row['amounts'], row['purchase_dates'])):
                                st.markdown(f"- {product} (x{amount}) on {date}")
                
                # Store purchase statistics
                st.markdown("---")
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
        except Exception as e:
            st.error(f"Error loading store purchases: {e}")
    else:
        st.info("Store purchase file not found.")

@st.fragment
def render_player_search(player_names, shop_purchase_path, store_purchase_path, player_id_mapping):
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
        
        # Load and display player's purchases from separate CSV files
        if player_id:
            st.markdown(f"#### Purchases for {selected_player_name}")
            
            # Shop purchases
            if os.path.exists(shop_purchase_path):
                try:
                    shop_df = pd.read_csv(shop_purchase_path)
                    player_shop_purchases = shop_df[shop_df['player_id'] == player_id]
                    
                    if not player_shop_purchases.empty:
                        st.markdown("**Shop Purchases**")
                        shop_data = []
                        for _, row in player_shop_purchases.iterrows():
                            shop_data.append({
                                'Item': row.get('item_name', 'Unknown'),
                                'Amount': row.get('amount', 1),
                                'Purchased At': row.get('purchased_at', 'Unknown')
                            })
                        
                        shop_df_display = pd.DataFrame(shop_data)
                        shop_df_display = shop_df_display.sort_values('Purchased At', ascending=False)
                        st.dataframe(shop_df_display, width='stretch', hide_index=True)
                    else:
                        st.info("No shop purchases found for this player.")
                except Exception as e:
                    st.error(f"Error loading shop purchases: {e}")
            else:
                st.info("Shop purchase file not found.")
            
            # Store purchases
            if os.path.exists(store_purchase_path):
                try:
                    store_df = pd.read_csv(store_purchase_path)
                    player_store_purchases = store_df[store_df['player_id'] == player_id]
                    
                    if not player_store_purchases.empty:
                        st.markdown("**Store Purchases**")
                        store_data = []
                        for _, row in player_store_purchases.iterrows():
                            store_data.append({
                                'Product': row.get('product_id', 'Unknown'),
                                'Amount': row.get('amount', 1),
                                'Purchased At': row.get('purchased_at', 'Unknown')
                            })
                        
                        store_df_display = pd.DataFrame(store_data)
                        store_df_display = store_df_display.sort_values('Purchased At', ascending=False)
                        st.dataframe(store_df_display, width='stretch', hide_index=True)
                    else:
                        st.info("No store purchases found for this player.")
                except Exception as e:
                    st.error(f"Error loading store purchases: {e}")
            else:
                st.info("Store purchase file not found.")
    else:
        st.info("No players found matching your search.")
