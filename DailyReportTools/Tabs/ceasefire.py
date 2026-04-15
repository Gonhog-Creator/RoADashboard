import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import json
from cache_manager import cache_manager

def format_number(num):
    """Format numbers with abbreviations"""
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{int(num):,}"

def get_storage_vault_protection(buildings_metadata):
    """Extract storage vault level and calculate protected resources"""
    if pd.isna(buildings_metadata) or not buildings_metadata:
        return None
    
    # Parse buildings_metadata to find storage vault in any settlement
    individual_settlements = buildings_metadata.split('|')
    
    for settlement_metadata in individual_settlements:
        # Extract buildings using the new format parsing logic
        # Try splitting by ']:[' first (new format with brackets)
        if ']:[' in settlement_metadata:
            settlement_parts = settlement_metadata.split(']:[')
        else:
            # Try splitting by ':[' (format without brackets around type)
            settlement_parts = settlement_metadata.split(':[')
        
        if len(settlement_parts) >= 2:
            # Second part has buildings
            buildings_str = settlement_parts[1].rstrip(']')
            
            # Parse buildings from the string
            if buildings_str:
                for building in buildings_str.split(','):
                    # Require colon separator like buildings tab for consistency
                    if ':' in building:
                        building_name, level = building.split(':')
                        building_name_lower = building_name.strip().lower()
                        if 'storage_vault' in building_name_lower:
                            level = int(level.strip())
                            return level
    
    return None

def get_fangtooth_cache_protection(buildings_metadata):
    """Extract fangtooth cache level and calculate protected respirators"""
    if pd.isna(buildings_metadata) or not buildings_metadata:
        return None
    
    # Parse buildings_metadata to find fangtooth cache in any settlement
    individual_settlements = buildings_metadata.split('|')
    
    for idx, settlement_metadata in enumerate(individual_settlements):
        # Extract buildings using the new format parsing logic
        # Try splitting by ']:[' first (new format with brackets)
        if ']:[' in settlement_metadata:
            settlement_parts = settlement_metadata.split(']:[')
        else:
            # Try splitting by ':[' (format without brackets around type)
            settlement_parts = settlement_metadata.split(':[')
        
        if len(settlement_parts) >= 2:
            # Second part has buildings
            buildings_str = settlement_parts[1].rstrip(']')
            
            # Parse buildings from the string
            if buildings_str:
                for building in buildings_str.split(','):
                    # Require colon separator like buildings tab for consistency
                    if ':' in building:
                        building_name, level = building.split(':')
                        building_name_lower = building_name.strip().lower()
                        # Match fangtooth_cache with or without underscore, or fangtoothcache
                        if 'fangtooth' in building_name_lower and 'cache' in building_name_lower:
                            level = int(level.strip())
                            return level
    
    return None

def calculate_vault_protection(level):
    """Calculate protected resources based on vault level"""
    # Values from buildings_updated.yaml
    vault_protection = {
        1: {'food': 5_000_000, 'lumber': 5_000_000, 'stone': 5_000_000, 'metal': 5_000_000, 'gold': 2_000_000},
        2: {'food': 11_000_000, 'lumber': 11_000_000, 'stone': 11_000_000, 'metal': 11_000_000, 'gold': 5_000_000},
        3: {'food': 17_000_000, 'lumber': 17_000_000, 'stone': 17_000_000, 'metal': 17_000_000, 'gold': 8_000_000},
        4: {'food': 23_000_000, 'lumber': 23_000_000, 'stone': 23_000_000, 'metal': 23_000_000, 'gold': 11_000_000},
        5: {'food': 29_000_000, 'lumber': 29_000_000, 'stone': 29_000_000, 'metal': 29_000_000, 'gold': 14_000_000},
        6: {'food': 35_000_000, 'lumber': 35_000_000, 'stone': 35_000_000, 'metal': 35_000_000, 'gold': 17_000_000},
        7: {'food': 41_000_000, 'lumber': 41_000_000, 'stone': 41_000_000, 'metal': 41_000_000, 'gold': 20_000_000},
        8: {'food': 47_000_000, 'lumber': 47_000_000, 'stone': 47_000_000, 'metal': 47_000_000, 'gold': 23_000_000},
        9: {'food': 53_000_000, 'lumber': 53_000_000, 'stone': 53_000_000, 'metal': 53_000_000, 'gold': 26_000_000},
        10: {'food': 59_000_000, 'lumber': 59_000_000, 'stone': 59_000_000, 'metal': 59_000_000, 'gold': 29_000_000},
    }
    return vault_protection.get(level, {'food': 0, 'lumber': 0, 'stone': 0, 'metal': 0, 'gold': 0})

def calculate_cache_protection(level):
    """Calculate protected fangtooth respirators based on cache level"""
    # 100k per level
    return level * 100_000

def create_ceasefire_tab(filtered_df):
    """Create the Protected Resources tab with player and resource analysis"""
    
    if not filtered_df.empty:
        st.markdown("### Protected Resources Analysis")
        
        # Look for any report with raw_player_data (comprehensive CSV format)
        comprehensive_data = None
        comprehensive_index = -1
        
        for i in range(len(filtered_df) - 1, -1, -1):  # Iterate backwards to find latest with building data
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                comprehensive_data = data
                comprehensive_index = i
                break
        
        if comprehensive_data is None:
            st.warning("No comprehensive CSV data found. This feature requires comprehensive CSV format.")
            return
        
        latest_data = comprehensive_data
        
        player_data = latest_data['raw_player_data']
        
        # Check for active effects column
        if 'active_effects' not in player_data.columns:
            st.warning("Active effects data not available in current report format.")
            return
        
        # Identify players with any attack prevention effects
        attack_prevention_effects = ['prevent_attacks:1']
        player_data['has_protection'] = player_data['active_effects'].fillna('').astype(str).apply(
            lambda x: any(effect in x for effect in attack_prevention_effects)
        )
        
        # Identify players by specific attack prevention type
        player_data['has_ceasefire_treaty'] = player_data['active_effects'].fillna('').astype(str).apply(
            lambda x: 'cease_fire_treaty' in x.lower()
        )
        player_data['has_armistice_agreement'] = player_data['active_effects'].fillna('').astype(str).apply(
            lambda x: 'armistice_agreement' in x.lower()
        )
        player_data['has_truce'] = player_data['active_effects'].fillna('').astype(str).apply(
            lambda x: 'truce' in x.lower()
        )
        player_data['has_server_protection'] = player_data['active_effects'].fillna('').astype(str).apply(
            lambda x: 'server:prevent_attacks' in x.lower()
        )
        
        protected_players = player_data[player_data['has_protection']].copy()
        
        if protected_players.empty:
            st.info("No players currently have attack prevention effects.")
            return
        
        # Summary statistics
        total_players = len(player_data)
        protected_count = len(protected_players)
        protected_percentage = (protected_count / total_players * 100) if total_players > 0 else 0
        
        # Calculate counts for each protection type
        ceasefire_treaty_count = player_data['has_ceasefire_treaty'].sum()
        armistice_agreement_count = player_data['has_armistice_agreement'].sum()
        truce_count = player_data['has_truce'].sum()
        server_protection_count = player_data['has_server_protection'].sum()
        
        # Calculate total protected resources
        resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food']
        total_protected = 0
        for col in resource_columns:
            if col in protected_players.columns:
                total_protected += protected_players[col].fillna(0).sum()
        
        # Calculate total resources across all players
        total_resources = 0
        for col in resource_columns:
            if col in player_data.columns:
                total_resources += player_data[col].fillna(0).sum()
        
        # Calculate storage vault protection
        player_data['storage_vault_level'] = player_data['buildings_metadata'].apply(get_storage_vault_protection)
        player_data['fangtooth_cache_level'] = player_data['buildings_metadata'].apply(get_fangtooth_cache_protection)
        
        # Calculate total protected resources from storage vaults
        vault_protected_resources = {
            'food': 0,
            'lumber': 0,
            'stone': 0,
            'metal': 0,
            'gold': 0
        }
        
        for _, player in player_data.iterrows():
            vault_level = player['storage_vault_level']
            if vault_level:
                protection = calculate_vault_protection(vault_level)
                for resource in vault_protected_resources:
                    vault_protected_resources[resource] += protection[resource]
        
        total_vault_protected = sum(vault_protected_resources.values())
        
        # Calculate fangtooth cache protection
        total_cache_protected = 0
        for _, player in player_data.iterrows():
            cache_level = player['fangtooth_cache_level']
            if cache_level:
                total_cache_protected += calculate_cache_protection(cache_level)
        
        # Subtract vault protection from ceasefire protection (since they overlap)
        total_protected_adjusted = total_protected - total_vault_protected
        protected_resource_percentage_adjusted = (total_protected_adjusted / total_resources * 100) if total_resources > 0 else 0
        
        # Calculate total protected (ceasefire + vault)
        total_protected_combined = total_protected_adjusted + total_vault_protected
        total_protected_percentage = (total_protected_combined / total_resources * 100) if total_resources > 0 else 0
        
        # Calculate percentage of protected resources
        protected_resource_percentage = (total_protected / total_resources * 100) if total_resources > 0 else 0
        
        # Calculate storage vault protected percentage
        vault_protected_percentage = (total_vault_protected / total_resources * 100) if total_resources > 0 else 0
        
        # Display summary metrics (simplified like skins section)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Protected",
                f"{format_number(total_protected_combined)} ({total_protected_percentage:.1f}%)"
            )
        
        with col2:
            st.metric(
                "Ceasefire Protected Resources",
                f"{format_number(total_protected_adjusted)} ({protected_resource_percentage_adjusted:.1f}%)"
            )
        
        with col3:
            st.metric(
                "Storage Vault Protected",
                f"{format_number(total_vault_protected)} ({vault_protected_percentage:.1f}%)"
            )
        
        st.markdown("---")
        
        # Unprotected Resources Section
        st.markdown("#### Unprotected Resources")
        
        # Calculate unprotected resources
        total_unprotected = total_resources - total_protected_combined
        unprotected_percentage = (total_unprotected / total_resources * 100) if total_resources > 0 else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Total Unprotected Resources",
                f"{format_number(total_unprotected)} ({unprotected_percentage:.1f}%)"
            )
        
        with col2:
            st.metric(
                "Total Resources",
                f"{format_number(total_resources)}"
            )
        
        # Calculate unprotected resources by type including fangtooth respirators
        unprotected_by_type = {}
        for resource in ['food', 'lumber', 'stone', 'metal', 'gold']:
            resource_col = f'resource_{resource}'
            if resource_col in player_data.columns:
                total_resource = player_data[resource_col].fillna(0).sum()
                # Calculate protected amount for this resource type
                protected_resource = vault_protected_resources.get(resource, 0)
                # For ceasefire protected, we need to calculate proportionally
                if total_protected_adjusted > 0:
                    # Calculate protected from ceasefire based on proportion
                    protected_from_ceasefire = (total_protected_adjusted / total_protected) * (total_resource - protected_resource) if total_resource > 0 else 0
                else:
                    protected_from_ceasefire = 0
                total_protected_for_resource = protected_resource + protected_from_ceasefire
                unprotected_by_type[resource] = max(0, total_resource - total_protected_for_resource)
            else:
                unprotected_by_type[resource] = 0
        
        # Calculate total fangtooth respirators
        total_fangtooth = 0
        if 'resource_fangtooth' in player_data.columns:
            total_fangtooth = player_data['resource_fangtooth'].fillna(0).sum()
        
        # Fangtooth respirators protected by cache
        protected_fangtooth = total_cache_protected
        unprotected_fangtooth = max(0, total_fangtooth - protected_fangtooth)
        
        # Create unprotected resources table with clickable buttons
        # Render in fragment for instant button updates
        render_unprotected_resources(unprotected_by_type, unprotected_fangtooth, player_data, vault_protected_resources, total_protected_adjusted, total_protected, total_resources, total_players)

        st.markdown("---")
        
        # Player details table (simplified)
        st.markdown("#### Players with Attack Prevention")
        
        # Display players with protection metric and breakdown by type
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Players with Protection",
                f"{protected_count:,} ({protected_percentage:.1f}%)" if total_players > 0 else f"{protected_count:,}"
            )
        
        with col2:
            st.metric(
                "Server Protection",
                f"{server_protection_count:,}"
            )
        
        with col3:
            st.metric(
                "Ceasefire Treaty",
                f"{ceasefire_treaty_count:,}"
            )
        
        with col4:
            st.metric(
                "Armistice Agreement",
                f"{armistice_agreement_count:,}"
            )
        
        with col5:
            st.metric(
                "Truce",
                f"{truce_count:,}"
            )
        
        # Prepare player data for display
        display_columns = ['username', 'power', 'resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'created_at']
        available_columns = [col for col in display_columns if col in protected_players.columns]
        
        if available_columns:
            player_table = protected_players[available_columns].copy()
            
            # Sort by power (descending)
            player_table = player_table.sort_values('power', ascending=False)
            
            # Rename columns for better display
            column_rename_map = {
                'username': 'Player Name',
                'power': 'Power',
                'resource_gold': 'Gold',
                'resource_lumber': 'Lumber',
                'resource_stone': 'Stone',
                'resource_metal': 'Metal',
                'resource_food': 'Food',
                'created_at': 'Creation Date'
            }
            
            player_table = player_table.rename(columns=column_rename_map)
            
            # Format power and resource columns
            if 'Power' in player_table.columns:
                player_table['Power'] = player_table['Power'].apply(lambda x: f"{x:,}" if pd.notna(x) else '0')
            
            # Format creation date
            if 'Creation Date' in player_table.columns:
                player_table['Creation Date'] = pd.to_datetime(player_table['Creation Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            for resource in ['Gold', 'Lumber', 'Stone', 'Metal', 'Food']:
                if resource in player_table.columns:
                    player_table[resource] = player_table[resource].apply(lambda x: f"{int(x):,}" if pd.notna(x) and x != 0 else '0')
            
            st.dataframe(player_table, width='stretch', hide_index=True)
            
            # Add pie charts for each resource
            st.markdown("##### Resource Distribution Among Protected Players")
            
            resources = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food']
            resource_display_names = {'resource_gold': 'Gold', 'resource_lumber': 'Lumber', 'resource_stone': 'Stone', 'resource_metal': 'Metal', 'resource_food': 'Food'}
            cols = st.columns(len(resources))
            
            for i, resource in enumerate(resources):
                if resource in protected_players.columns:
                    with cols[i]:
                        resource_data = protected_players[resource].fillna(0)
                        # Filter out players with 0 of this resource
                        resource_data_filtered = resource_data[resource_data > 0]
                        
                        if not resource_data_filtered.empty:
                            # Get player names for non-zero values
                            player_names = protected_players.loc[resource_data_filtered.index, 'username']
                            
                            # Create pie chart using plotly express for simpler rendering
                            pie_df = pd.DataFrame({
                                'Player': player_names,
                                'Amount': resource_data_filtered.values
                            })
                            
                            # Format the amounts for display
                            pie_df['Formatted Amount'] = pie_df['Amount'].apply(format_number)
                            
                            fig_pie = px.pie(
                                pie_df,
                                values='Amount',
                                names='Player',
                                title=f"{resource_display_names[resource]} Distribution",
                                hole=0.3,
                                height=300
                            )
                            fig_pie.update_layout(
                                margin=dict(l=0, r=0, t=40, b=0),
                                showlegend=False
                            )
                            fig_pie.update_traces(
                                textinfo='label+percent',
                                textposition='inside',
                                textfont_size=10,
                                customdata=pie_df['Formatted Amount'],
                                hovertemplate='<b>%{label}</b><br>Amount: %{customdata}<br>Percent: %{percent}<extra></extra>',
                                text=pie_df['Formatted Amount'].tolist()
                            )
                            st.plotly_chart(fig_pie, width='stretch')
                        else:
                            st.write(f"No {resource_display_names[resource]} data available")
        
        st.markdown("---")
        
        # Storage Vault Section
        st.markdown("#### Storage Vault Protection")
        
        # Calculate players with storage vaults
        players_with_vault = player_data[player_data['storage_vault_level'].notna()].copy()
        players_with_cache = player_data[player_data['fangtooth_cache_level'].notna()].copy()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Players with Storage Vault", len(players_with_vault))
        
        with col2:
            st.metric("Players with Fangtooth Cache", len(players_with_cache))
        
        # Show vault protected resources by type
        if total_vault_protected > 0:
            st.markdown("##### Vault Protected Resources by Type")
            vault_cols = st.columns(5)
            vault_resource_names = ['food', 'lumber', 'stone', 'metal', 'gold']
            for i, resource in enumerate(vault_resource_names):
                with vault_cols[i]:
                    st.metric(
                        resource.title(),
                        format_number(vault_protected_resources[resource])
                    )
        
        # Show fangtooth cache protection
        if total_cache_protected > 0:
            st.markdown("##### Fangtooth Cache Protection")
            st.metric("Protected Fangtooth Respirators", format_number(total_cache_protected))
    
    else:
        st.info("No data available for protected resources analysis.")

@st.fragment
def render_unprotected_resources(unprotected_by_type, unprotected_fangtooth, player_data, vault_protected_resources, total_protected_adjusted, total_protected, total_resources, total_players):
    """Fragment for Unprotected Resources section - only reruns when buttons are clicked"""
    st.markdown("##### Unprotected Resources by Type (Click to view players)")
    
    resource_mapping = {
        'Food': ('resource_food', unprotected_by_type.get('food', 0)),
        'Lumber': ('resource_lumber', unprotected_by_type.get('lumber', 0)),
        'Stone': ('resource_stone', unprotected_by_type.get('stone', 0)),
        'Metal': ('resource_metal', unprotected_by_type.get('metal', 0)),
        'Gold': ('resource_gold', unprotected_by_type.get('gold', 0)),
        'Fangtooth Respirators': ('resource_fangtooth', unprotected_fangtooth)
    }
    
    # Calculate total amounts for each resource type to get percentages
    resource_totals = {}
    for resource_name, (resource_col, _) in resource_mapping.items():
        if resource_col in player_data.columns:
            resource_totals[resource_name] = player_data[resource_col].fillna(0).sum()
        else:
            resource_totals[resource_name] = 0
    
    # Create clickable buttons for each resource
    cols = st.columns(len(resource_mapping))
    for i, (resource_name, (resource_col, unprotected_amount)) in enumerate(resource_mapping.items()):
        with cols[i]:
            button_key = f"unprotected_{resource_name.lower().replace(' ', '_')}"
            # Calculate percentage of total for this resource
            total_amount = resource_totals.get(resource_name, 0)
            percentage = (unprotected_amount / total_amount * 100) if total_amount > 0 else 0
            button_text = f"{resource_name}: {format_number(unprotected_amount)} ({percentage:.1f}%)"
            if st.button(button_text, key=button_key, width='stretch'):
                st.session_state['selected_resource'] = resource_name
                st.session_state['selected_resource_col'] = resource_col
    
    # Get cached resource data from cache manager (pre-calculated at startup)
    cached_resource_data = cache_manager.get_resource_data()
    
    # Show modal if a resource is selected
    if 'selected_resource' in st.session_state and st.session_state['selected_resource']:
        selected_resource = st.session_state['selected_resource']
        
        # Get cached data
        display_data = cached_resource_data.get(selected_resource, [])
        
        # Create expander with player information (modal-like)
        with st.expander(f"📊 Players with Unprotected {selected_resource}", expanded=True):
            if display_data:
                display_df = pd.DataFrame(display_data)
                display_df[f'{selected_resource} Amount'] = display_df[f'{selected_resource} Amount'].apply(lambda x: f"{x:,}")
                display_df['Defended'] = display_df['Defended'].apply(lambda x: 'Yes' if x else 'No')
                st.dataframe(display_df, width='stretch', hide_index=True)
            else:
                st.info(f"No players found with {selected_resource}")
            
            if st.button("Close", key="close_expander"):
                st.session_state.pop('selected_resource', None)
                st.session_state.pop('selected_resource_col', None)
                st.rerun()
