import streamlit as st
import pandas as pd
import os
import json

def create_purchases_tab():
    """Create the Purchases tab"""
    st.markdown("### 💳 Purchases")
    
    # Get paths to purchase CSV files
    database_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'DatabaseParser')
    shop_purchase_path = os.path.join(database_path, 'shop_item_purchase.csv')
    store_purchase_path = os.path.join(database_path, 'store_purchase.csv')
    
    # Check if files exist
    if not os.path.exists(shop_purchase_path) and not os.path.exists(store_purchase_path):
        st.warning("Purchase data files not found. Run sync tool to download purchase data.")
        return
    
    # Load shop purchases
    shop_df = None
    if os.path.exists(shop_purchase_path):
        try:
            shop_df = pd.read_csv(shop_purchase_path)
            if not shop_df.empty:
                st.markdown("#### Shop Purchases")
                st.info(f"Found {len(shop_df)} shop purchases")
                
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
                        with st.expander(f"Player ID: {row['player_id']} - {row['total_purchases']} purchases"):
                            for i, (item, amount, date) in enumerate(zip(row['items'], row['amounts'], row['purchase_dates'])):
                                st.markdown(f"- {item} (x{amount}) on {date}")
        except Exception as e:
            st.error(f"Error loading shop purchases: {e}")
    
    # Load store purchases
    store_df = None
    if os.path.exists(store_purchase_path):
        try:
            store_df = pd.read_csv(store_purchase_path)
            if not store_df.empty:
                st.markdown("#### Store Purchases")
                st.info(f"Found {len(store_df)} store purchases")
                
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
                        with st.expander(f"Player ID: {row['player_id']} - {row['total_purchases']} purchases"):
                            for i, (product, amount, date) in enumerate(zip(row['products'], row['amounts'], row['purchase_dates'])):
                                st.markdown(f"- {product} (x{amount}) on {date}")
        except Exception as e:
            st.error(f"Error loading store purchases: {e}")
    
    # Combine all purchases for overview
    if shop_df is not None and not shop_df.empty:
        st.markdown("---")
        st.markdown("#### Purchase Overview")
        
        # Shop purchase statistics
        if shop_df is not None and not shop_df.empty:
            st.markdown("**Shop Purchases**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Shop Purchases", len(shop_df))
            with col2:
                unique_players = shop_df['player_id'].nunique()
                st.metric("Unique Players", unique_players)
            with col3:
                avg_purchases = len(shop_df) / unique_players if unique_players > 0 else 0
                st.metric("Avg Purchases/Player", f"{avg_purchases:.1f}")
            
            # Top items
            top_items = shop_df['item_name'].value_counts().head(10)
            st.markdown("**Top Shop Items**")
            for item, count in top_items.items():
                st.markdown(f"- {item}: {count} purchases")
        
        # Store purchase statistics
        if store_df is not None and not store_df.empty:
            st.markdown("**Store Purchases**")
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
