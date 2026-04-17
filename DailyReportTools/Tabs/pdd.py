import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import base64
from cache_manager import cache_manager

@st.fragment
def render_resources_chart(resource_data, selected_name):
    """Fragment for Resources Over Time chart - only reruns when checkboxes change"""
    if resource_data:
        # Resource selection with checkboxes
        st.markdown("#### Select resources to display:")
        selected_resources = []
        
        # Separate resources into main resources and elite items
        main_resources = ['Gold', 'Lumber', 'Stone', 'Metal', 'Food']
        elite_resources = ['Fangtooth']
        
        # Get available resources
        resource_names = sorted(set(resource_data.keys()))  # Remove duplicates and sort
        
        # Display main resources
        st.markdown("**Resources**")
        cols_main = st.columns(5)
        col_idx = 0
        for resource in main_resources:
            if resource in resource_names:
                with cols_main[col_idx % 5]:
                    default_value = True
                    key = f"resource_{selected_name}_{resource}"
                    if st.checkbox(resource, value=default_value, key=key):
                        selected_resources.append(resource)
                col_idx += 1
        
        # Display elite items
        st.markdown("**Elite Items**")
        cols_elite = st.columns(5)
        col_idx = 0
        for resource in elite_resources:
            if resource in resource_names:
                with cols_elite[col_idx % 5]:
                    default_value = True
                    key = f"resource_{selected_name}_{resource}"
                    if st.checkbox(resource, value=default_value, key=key):
                        selected_resources.append(resource)
                col_idx += 1
        
        if selected_resources:
            fig_resources = go.Figure()
            for resource in selected_resources:
                if resource in resource_data and resource_data[resource]:
                    resource_df = pd.DataFrame(resource_data[resource])
                    if 'Date' in resource_df.columns and 'Amount' in resource_df.columns:
                        fig_resources.add_trace(go.Scatter(
                            x=resource_df['Date'],
                            y=resource_df['Amount'],
                            mode='lines+markers',
                            name=resource
                        ))
            
            fig_resources.update_layout(
                title='Resources Over Time',
                xaxis_title='Date',
                yaxis_title='Amount'
            )
            st.plotly_chart(fig_resources, width='stretch')

@st.fragment
def render_items_chart(items_data, selected_name):
    """Fragment for Items Over Time chart - only reruns when checkboxes change"""
    if items_data:
        # Item selection with checkboxes
        st.markdown("#### Select items to display:")
        selected_items = []
        item_names = sorted(set(items_data.keys()))  # Sort alphabetically
        cols = st.columns(5)
        
        for i, item in enumerate(item_names):
            with cols[i % 5]:
                key = f"item_{selected_name}_{i}_{item}"
                if st.checkbox(item.replace('_', ' ').title(), key=key):
                    selected_items.append(item)
        
        if selected_items:
            fig_items = go.Figure()
            for item in selected_items:
                item_df = pd.DataFrame(items_data[item])
                fig_items.add_trace(go.Scatter(
                    x=item_df['Date'],
                    y=item_df['Count'],
                    mode='lines+markers',
                    name=item.replace('_', ' ').title()
                ))
            
            fig_items.update_layout(
                title='Items Over Time',
                xaxis_title='Date',
                yaxis_title='Count'
            )
            st.plotly_chart(fig_items, width='stretch')

@st.fragment
def render_player_details(selected_name, player_data, latest_data, filtered_df):
    """Fragment for all player-specific content - only reruns when player selection changes"""
    st.markdown("---")
    st.markdown(f"### 📊 {selected_name}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Alliance", player_data.get('alliance_name', 'None'))
    
    with col2:
        st.metric("Power", f"{int(player_data.get('power', 0)):,}")
    
    with col3:
        # Calculate outposts
        has_outpost = False
        if 'buildings_metadata' in player_data and pd.notna(player_data['buildings_metadata']):
            settlements = str(player_data['buildings_metadata']).split('|')
            has_outpost = any('outpost' in s.lower() for s in settlements)
        
        # Display outpost icon with check/X
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", "water_outpost.webp")
        if os.path.exists(icon_path):
            try:
                with open(icon_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                    img_data_url = f"data:image/webp;base64,{img_data}"
                    status_icon = "✓" if has_outpost else "✗"
                    st.markdown(f"<div style='text-align: center;'><div style='font-size: 12px; color: #666; margin-bottom: 5px;'>Outpost</div><div style='position: relative; display: inline-block;'><img src='{img_data_url}' style='width: 50px; height: 50px;'><div style='position: absolute; top: -5px; right: -5px; font-size: 30px; font-weight: bold; color: {'#4CAF50' if has_outpost else '#F44336'};'>{status_icon}</div></div></div>", unsafe_allow_html=True)
            except:
                st.metric("Outpost", "Yes" if has_outpost else "No")
        else:
            st.metric("Outpost", "Yes" if has_outpost else "No")
    
    with col4:
        # Skins - display multiple icons with title
        if 'equipped_skins' in player_data and pd.notna(player_data['equipped_skins']):
            equipped_skins = player_data['equipped_skins']
            if isinstance(equipped_skins, str):
                skins_list = []
                if '|' in equipped_skins:
                    for entry in equipped_skins.split('|'):
                        entry = entry.strip()
                        if entry.startswith('{') or entry.startswith('['):
                            try:
                                parsed = json.loads(entry)
                                if isinstance(parsed, dict):
                                    skins_list.extend(list(parsed.keys()))
                                else:
                                    skins_list.extend(parsed)
                            except:
                                skins_list.append(entry)
                        else:
                            skins_list.append(entry)
                else:
                    skins_list = [equipped_skins]
                
                if skins_list:
                    st.markdown("<div style='font-size: 12px; color: #666; margin-bottom: 5px;'>Skins</div>", unsafe_allow_html=True)
                    # Display all skins in a horizontal row
                    icons_html = "<div style='display: flex; gap: 5px; flex-wrap: wrap;'>"
                    for skin in skins_list:
                        # Clean the skin name - remove all suffixes in parentheses
                        clean_skin = skin.split('(')[0].strip() if '(' in skin else skin
                        # Convert skin name to icon filename
                        # Try multiple filename variations
                        icon_variations = [
                            f"{clean_skin.lower().replace(' ', '_')}.webp",
                            f"{clean_skin.lower().replace(' ', '_')}_small.webp",
                            f"{clean_skin.lower().replace(' ', '_')}_large.webp",
                            f"{clean_skin.lower().replace(' ', '_')}-.webp",
                        ]
                        
                        icon_found = False
                        for icon_filename in icon_variations:
                            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", icon_filename)
                            if os.path.exists(icon_path):
                                try:
                                    with open(icon_path, 'rb') as f:
                                        img_data = base64.b64encode(f.read()).decode('utf-8')
                                        img_data_url = f"data:image/webp;base64,{img_data}"
                                        icons_html += f"<img src='{img_data_url}' style='width: 40px; height: 40px;'>"
                                        icon_found = True
                                        break
                                except:
                                    continue
                        
                        if not icon_found:
                            icons_html += f"<div style='width: 40px; height: 40px; background: #E0E0E0; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #666;'>🎨</div>"
                    icons_html += "</div>"
                    st.markdown(icons_html, unsafe_allow_html=True)
    
    # Active Effects section
    if 'active_effects' in player_data and pd.notna(player_data['active_effects']) and player_data['active_effects']:
        st.markdown("#### Active Effects")
        active_effects_str = player_data['active_effects']
        effects_list = active_effects_str.split('|')
        if effects_list:
            # Display effects in a responsive flexbox grid
            effects_html = "<div style='display: flex; flex-wrap: wrap; gap: 15px; margin: 10px 0;'>"
            
            for effect in effects_list:
                if ':' in effect:
                    # Parse effect format: source:type:level:duration
                    parts = effect.split(':')
                    if len(parts) >= 2:
                        effect_name = parts[0].strip()  # Use source (effect name) instead of type
                        effect_type = parts[1].strip()
                        effect_duration = parts[3].strip() if len(parts) >= 4 else ''
                        
                        # Convert effect name to icon filename (lowercase, replace spaces with underscores)
                        icon_filename = f"{effect_name.lower().replace(' ', '_')}.webp"
                        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", icon_filename)
                        
                        # Convert image to base64
                        img_data_url = ""
                        if os.path.exists(icon_path):
                            try:
                                with open(icon_path, 'rb') as f:
                                    img_data = base64.b64encode(f.read()).decode('utf-8')
                                    img_data_url = f"data:image/webp;base64,{img_data}"
                            except:
                                pass
                        
                        if img_data_url:
                            duration_div = f"<div style='font-size: 12px; color: #666;'>{effect_duration}</div>" if effect_duration else ""
                            effects_html += f"<div style='text-align: center; min-width: 80px; flex: 1;'><img src='{img_data_url}' style='width: 60px; height: 60px;'><div style='font-size: 14px; font-weight: bold; margin-top: 5px;'>{effect_name.replace('_', ' ').title()}</div>{duration_div}</div>"
            
            effects_html += "</div>"
            st.markdown(effects_html, unsafe_allow_html=True)
    
    # Permanent Effects section
    if 'permanent_effects' in player_data and pd.notna(player_data['permanent_effects']) and player_data['permanent_effects']:
        st.markdown("#### 🏆 Permanent Effects")
        permanent_effects_str = player_data['permanent_effects']
        effects_list = permanent_effects_str.split('|')
        if effects_list:
            # Display effects in a responsive flexbox grid
            effects_html = "<div style='display: flex; flex-wrap: wrap; gap: 15px; margin: 10px 0;'>"
            
            for effect in effects_list:
                if ':' in effect:
                    # Parse effect format: source:type:level:duration
                    parts = effect.split(':')
                    if len(parts) >= 2:
                        effect_name = parts[0].strip()  # Use source (effect name) instead of type
                        effect_type = parts[1].strip()
                        effect_level = parts[2].strip() if len(parts) >= 3 else ''
                        effect_duration = parts[3].strip() if len(parts) >= 4 else ''
                        
                        # Convert effect name to icon filename (lowercase, replace spaces with underscores)
                        icon_filename = f"{effect_name.lower().replace(' ', '_')}.webp"
                        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", icon_filename)
                        
                        # Convert image to base64
                        img_data_url = ""
                        if os.path.exists(icon_path):
                            try:
                                with open(icon_path, 'rb') as f:
                                    img_data = base64.b64encode(f.read()).decode('utf-8')
                                    img_data_url = f"data:image/webp;base64,{img_data}"
                            except:
                                pass
                        
                        if img_data_url:
                            level_div = f"<div style='font-size: 12px; color: #666;'>Level {effect_level}</div>" if effect_level else ""
                            duration_div = f"<div style='font-size: 12px; color: #666;'>{effect_duration}</div>" if effect_duration else ""
                            effects_html += f"<div style='text-align: center; min-width: 80px; flex: 1;'><img src='{img_data_url}' style='width: 60px; height: 60px;'><div style='font-size: 14px; font-weight: bold; margin-top: 5px;'>{effect_name.replace('_', ' ').title()}</div>{level_div}{duration_div}</div>"
            
            effects_html += "</div>"
            st.markdown(effects_html, unsafe_allow_html=True)
    
    # Troops section (condensed table - troop types as columns, counts as single row)
    # Use raw_player_data directly to get current data instead of cached
    if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
        player_df = latest_data['raw_player_data']
        player = player_df[player_df['username'] == selected_name]
        if not player.empty and 'troops_json' in player.columns:
            st.markdown("#### Troops")
            try:
                troops_dict = json.loads(player['troops_json'].iloc[0])
                if troops_dict:
                    # Get all possible troop types from the dataset to ensure all columns are present
                    all_troop_types = set()
                    for _, player_row in player_df.iterrows():
                        if pd.notna(player_row['troops_json']):
                            try:
                                row_troops = json.loads(player_row['troops_json'])
                                all_troop_types.update(row_troops.keys())
                            except:
                                continue
                    
                    # Filter out Great Dragon and Water Dragon (exact match, case-insensitive)
                    dragons_to_filter = ['great dragon', 'water dragon', 'great_dragon', 'water_dragon']
                    all_troop_types = [t for t in all_troop_types if t.lower() not in dragons_to_filter]
                    
                    # Build row with all troop types, filling missing with 0
                    troop_row = {}
                    for troop_type in all_troop_types:
                        count = troops_dict.get(troop_type, 0)
                        if pd.isna(count):
                            count = 0
                        troop_row[troop_type] = count
                    
                    # Normalize troop names
                    normalized_troops = {k.replace('_', ' ').title(): v for k, v in troop_row.items()}
                    
                    # Single row with troop types as columns, counts as values
                    troops_df = pd.DataFrame([normalized_troops])
                    troops_df.index = ['Count']
                    # Format counts with commas
                    for col in troops_df.columns:
                        troops_df[col] = troops_df[col].apply(lambda x: f"{int(x):,}")
                    st.dataframe(troops_df, width='stretch')
            except:
                st.info("Troops data unavailable")
    
    # Purchases section
    if 'shop_purchases' in player_data and pd.notna(player_data['shop_purchases']) and player_data['shop_purchases']:
        st.markdown("#### Shop Purchases")
        shop_purchases_str = player_data['shop_purchases']
        shop_purchases_list = shop_purchases_str.split('|')
        
        if shop_purchases_list:
            # Display purchases in a table
            purchases_data = []
            for purchase in shop_purchases_list:
                parts = purchase.split(':')
                if len(parts) >= 3:
                    item_name = parts[0].strip()
                    amount = parts[1].strip()
                    purchased_at = parts[2].strip()
                    purchases_data.append({
                        'Item': item_name,
                        'Amount': amount,
                        'Purchased At': purchased_at
                    })
            
            if purchases_data:
                purchases_df = pd.DataFrame(purchases_data)
                st.dataframe(purchases_df, width='stretch', hide_index=True)
    
    if 'store_purchases' in player_data and pd.notna(player_data['store_purchases']) and player_data['store_purchases']:
        st.markdown("#### Store Purchases")
        store_purchases_str = player_data['store_purchases']
        store_purchases_list = store_purchases_str.split('|')
        
        if store_purchases_list:
            # Display purchases in a table
            purchases_data = []
            for purchase in store_purchases_list:
                parts = purchase.split(':')
                if len(parts) >= 3:
                    product_id = parts[0].strip()
                    amount = parts[1].strip()
                    purchased_at = parts[2].strip()
                    purchases_data.append({
                        'Product': product_id,
                        'Amount': amount,
                        'Purchased At': purchased_at
                    })
            
            if purchases_data:
                purchases_df = pd.DataFrame(purchases_data)
                st.dataframe(purchases_df, width='stretch', hide_index=True)
    
    # Daily attacks section
    st.markdown("#### Daily Attacks (Last 24 Hours)")
    try:
        from datetime import datetime, timedelta
        import csv
        
        # Get battle.csv path
        battle_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'DatabaseParser', 'battle.csv')
        
        if os.path.exists(battle_csv_path):
            # Get selected player's ID
            player_id = player_data.get('uuid', '')
            
            if player_id:
                # Calculate cutoff time (24 hours ago)
                cutoff_time = datetime.now() - timedelta(days=1)
                
                # Read battle.csv and filter for player's attacks in last 24 hours
                daily_attacks = []
                autowaver_count = 0
                manual_count = 0
                target_types = {}
                
                with open(battle_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('attacker_id') == player_id:
                            launched_at = row.get('launched_at', '')
                            if launched_at:
                                try:
                                    battle_time = datetime.strptime(launched_at, '%Y-%m-%d %H:%M:%S')
                                    if battle_time >= cutoff_time:
                                        daily_attacks.append(row)
                                        
                                        # Check if autowaver or manual
                                        metadata = row.get('metadata', '')
                                        if 'from_auto_waver":true' in metadata:
                                            autowaver_count += 1
                                        else:
                                            manual_count += 1
                                        
                                        # Count target types
                                        try:
                                            metadata_dict = json.loads(metadata)
                                            target_name = metadata_dict.get('target_name', 'unknown')
                                            if target_name:
                                                target_types[target_name] = target_types.get(target_name, 0) + 1
                                        except:
                                            pass
                                except:
                                    pass
                
                if daily_attacks:
                    # Display attack statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Daily Attacks", len(daily_attacks))
                    with col2:
                        st.metric("Autowaver", autowaver_count)
                    with col3:
                        st.metric("Manual", manual_count)
                    
                    # Display target types if available
                    if target_types:
                        st.markdown("**Target Types**")
                        target_df = pd.DataFrame([
                            {'Target': k, 'Attacks': v}
                            for k, v in sorted(target_types.items(), key=lambda x: x[1], reverse=True)
                        ])
                        st.dataframe(target_df, width='stretch', hide_index=True)
                else:
                    st.info("No attacks in the last 24 hours")
        else:
            st.info("Battle data not available")
    except Exception as e:
        st.info(f"Unable to load daily attack data: {e}")
    
    # Charts section
    st.markdown("---")
    st.markdown("#### 📈 Charts")
    
    # Power Over Time chart
    st.markdown("##### Power Over Time")
    power_data = []
    for _, row in filtered_df.iterrows():
        if 'raw_player_data' in row and row['raw_player_data'] is not None:
            df = row['raw_player_data']
            if isinstance(df, pd.DataFrame):
                player = df[df['username'] == selected_name]
                if not player.empty:
                    power_data.append({
                        'Date': row['date'],
                        'Power': player['power'].iloc[0]
                    })
    
    if power_data:
        power_df = pd.DataFrame(power_data)
        fig_power = px.line(power_df, x='Date', y='Power', title='Power Over Time')
        st.plotly_chart(fig_power, width='stretch')
    
    # Resources Over Time chart
    st.markdown("##### Resources Over Time")
    # Get resources over time data
    resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food', 'resource_fangtooth']
    resource_data = {}
    
    for _, row in filtered_df.iterrows():
        if 'raw_player_data' in row and row['raw_player_data'] is not None:
            df = row['raw_player_data']
            if isinstance(df, pd.DataFrame):
                player = df[df['username'] == selected_name]
                if not player.empty:
                    for col in resource_columns:
                        if col in player.columns:
                            resource_name = col.replace('resource_', '').title()
                            if resource_name not in resource_data:
                                resource_data[resource_name] = []
                            amount = player[col].iloc[0]
                            if pd.notna(amount):
                                resource_data[resource_name].append({
                                    'Date': row['date'],
                                    'Amount': amount
                                })
    
    # Render resources chart in fragment for instant checkbox updates
    render_resources_chart(resource_data, selected_name)
    
    # Items over time section
    st.markdown("---")
    st.markdown("#### 📦 Items Over Time")
    
    # Get all items data upfront
    items_data = {}
    for _, row in filtered_df.iterrows():
        if 'raw_player_data' in row and row['raw_player_data'] is not None:
            df = row['raw_player_data']
            if isinstance(df, pd.DataFrame):
                player = df[df['username'] == selected_name]
                if not player.empty and 'items_json' in player.columns:
                    try:
                        items_dict = json.loads(player['items_json'].iloc[0])
                        for item, count in items_dict.items():
                            if pd.notna(count) and count > 0:
                                if item not in items_data:
                                    items_data[item] = []
                                items_data[item].append({
                                    'Date': row['date'],
                                    'Count': count
                                })
                    except:
                        pass
    
    # Render items chart in fragment for instant checkbox updates
    render_items_chart(items_data, selected_name)
    
    # Buildings section
    st.markdown("---")
    st.markdown("#### 🏗️ Buildings")
    
    # Get the selected player's data from latest_data
    player_df = latest_data['raw_player_data']
    player_row = player_df[player_df['username'] == selected_name]
    
    if not player_row.empty:
        player_data_row = player_row.iloc[0]
        
        # Parse buildings metadata
        buildings_metadata = player_data_row.get('buildings_metadata')
        
        if pd.notna(buildings_metadata):
            try:
                # Parse all buildings for this player
                player_buildings = []
                
                if isinstance(buildings_metadata, str):
                    # Handle multiple settlements separated by |
                    # Each settlement has format: "CityName(level)[type](coords):[buildings]" or "CityName(level)type:[buildings]"
                    settlements = buildings_metadata.split('|')
                    
                    for settlement in settlements:
                        if ':[' in settlement:
                            city_part, buildings_str = settlement.split(':[')
                            buildings_str = buildings_str.rstrip(']')
                            
                            # Parse city info
                            name_part = city_part
                            settlement_type = 'city'
                            
                            # Check if it has brackets around type: "CityName(level)[type]"
                            if '[' in city_part:
                                name_part = city_part.split('[')[0]
                                # Extract type from brackets
                                bracket_content = city_part.split('[')[1].rstrip(']')
                                # Check if there are coordinates after the type
                                if '(' in bracket_content:
                                    # Format: "type(x,y)" - extract type before coordinates
                                    settlement_type = bracket_content.split('(')[0]
                                else:
                                    # Format: "type"
                                    settlement_type = bracket_content
                            else:
                                # Check for format without brackets: "CityName(level)type:["
                                # Find the last ')' to separate name from type
                                if ')' in city_part and ':' in city_part:
                                    # Extract name and level before the ')'
                                    name_part = city_part.rsplit(')', 1)[0]
                                    # Extract type between ')' and ':'
                                    type_part = city_part.rsplit(')', 1)[1].split(':')[0]
                                    if type_part:
                                        settlement_type = type_part
                            
                            # Parse buildings from the string
                            for building in buildings_str.split(','):
                                if ':' in building:
                                    building_name, level = building.split(':')
                                    building_name = building_name.strip()
                                    try:
                                        level = int(level.strip())
                                        
                                        # Skip fortresses in outposts (they don't have fortresses)
                                        if settlement_type == 'outpost' and building_name == 'fortress':
                                            continue
                                        
                                        player_buildings.append({
                                            'Building': building_name,
                                            'Level': level
                                        })
                                    except ValueError:
                                        # Skip if level is not a valid integer
                                        continue
                    else:
                        # Try splitting by ']:[' for the newer format
                        settlement_parts = buildings_metadata.split(']:[')
                        
                        for i, settlement_part in enumerate(settlement_parts):
                            buildings_str = None
                            name_part = ''
                            settlement_type = 'city'
                            
                            if i == 0:
                                if '[' in settlement_part:
                                    name_part = settlement_part.split('[')[0]
                                    bracket_content = settlement_part.split('[')[1].rstrip(']')
                                    if '(' in bracket_content:
                                        settlement_type = bracket_content.split('(')[0]
                                    else:
                                        settlement_type = bracket_content
                                else:
                                    name_part = settlement_part
                                    settlement_type = 'city'
                                
                                if i + 1 < len(settlement_parts):
                                    buildings_str = settlement_parts[i + 1].rstrip(']')
                            else:
                                buildings_str = settlement_part.rstrip(']')
                                if i + 1 < len(settlement_parts):
                                    next_part = settlement_parts[i + 1]
                                    if '[' in next_part:
                                        name_part = next_part.split('[')[0]
                                        bracket_content = next_part.split('[')[1].rstrip(']')
                                        if '(' in bracket_content:
                                            settlement_type = bracket_content.split('(')[0]
                                        else:
                                            settlement_type = bracket_content
                                    else:
                                        name_part = next_part
                                        settlement_type = 'city'
                            
                            if buildings_str:
                                for building in buildings_str.split(','):
                                    if ':' in building:
                                        building_name, level = building.split(':')
                                        building_name = building_name.strip()
                                        level = int(level.strip())
                                        
                                        if settlement_type == 'outpost' and building_name == 'fortress':
                                            continue
                                        
                                        player_buildings.append({
                                            'Level': level
                                        })
                elif isinstance(buildings_metadata, dict):
                    # Handle dict format
                    for city_name, city_info in buildings_metadata.items():
                        if ':' in city_info:
                            buildings_str = city_info.split(':')[1].strip('[]')
                            for building in buildings_str.split(','):
                                if ':' in building:
                                    building_name, level = building.split(':')
                                    building_name = building_name.strip()
                                    level = int(level.strip())
                                    
                                    player_buildings.append({
                                        'Level': level
                                    })
                
                if player_buildings:
                    # Parse buildings by type and level
                    buildings_by_type = {}
                    for building in player_buildings:
                        btype = building.get('Building', 'unknown')
                        level = building.get('Level', 1)
                        if btype not in buildings_by_type:
                            buildings_by_type[btype] = {}
                        if level not in buildings_by_type[btype]:
                            buildings_by_type[btype][level] = 0
                        buildings_by_type[btype][level] += 1
                    
                    # Display buildings with level distribution visualization
                    st.markdown("##### Building Inventory")
                    
                    # Group buildings in a grid
                    cols = st.columns(5)
                    col_idx = 0
                    
                    for building_type in sorted(buildings_by_type.keys(), key=lambda x: sum(buildings_by_type[x].values()), reverse=True):
                        with cols[col_idx % 5]:
                            # Get building icon - try multiple filename variations
                            icon_variations = [
                                f"{building_type.lower().replace(' ', '_')}.webp",
                                f"{building_type.lower().replace(' ', '_')}-.webp",
                            ]
                            
                            icon_path = None
                            for icon_filename in icon_variations:
                                test_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", icon_filename)
                                if os.path.exists(test_path):
                                    icon_path = test_path
                                    break
                            
                            # Handle specific typo for fountain of life
                            if not icon_path and building_type.lower().replace(' ', '_') == 'fountain_of_life':
                                icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Images", "foutain_of_life.webp")
                            
                            # Convert image to base64
                            img_data_url = ""
                            if os.path.exists(icon_path):
                                try:
                                    with open(icon_path, 'rb') as f:
                                        img_data = base64.b64encode(f.read()).decode('utf-8')
                                        img_data_url = f"data:image/webp;base64,{img_data}"
                                except:
                                    pass
                            
                            # Calculate total count
                            total_count = sum(buildings_by_type[building_type].values())
                            
                            # Filter to only show levels that have buildings
                            active_levels = {level: count for level, count in buildings_by_type[building_type].items() if count > 0}
                            
                            # Create arc HTML - single connected row of 10 boxes (levels 1-10)
                            arc_boxes = ""
                            # Create all 10 level boxes (even if empty)
                            for level in range(1, 11):
                                count = active_levels.get(level, 0)
                                # Create box - highlight if has buildings, gray if empty
                                bg_color = "#4CAF50" if count > 0 else "#E0E0E0"
                                text_color = "white" if count > 0 else "#999"
                                
                                arc_boxes += f"""
                                <div style="flex: 1; height: 50px; background: {bg_color}; border: 2px solid white; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 14px; color: {text_color}; font-weight: bold; margin: 0;">
                                    <span style="font-size: 18px; line-height: 1.2;">{count if count > 0 else "-"}</span>
                                    <span style="font-size: 11px; line-height: 1;">L{level}</span>
                                </div>
                                """
                            
                            # Wrap the connected row in a curved container
                            arc_container = f"""
                            <div style="position: absolute; top: 0; left: 0; width: 100%; height: 70px; display: flex; justify-content: center; align-items: center; transform: translateY(-15px);">
                                <div style="display: flex; width: 95%; height: 100%; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                                    {arc_boxes}
                                </div>
                            </div>
                            """
                            
                            # HTML/CSS for the arc visualization
                            arc_html = f"""
                            <html>
                            <head>
                            <style>
                                body {{ margin: 0; padding: 0; overflow: hidden; }}
                                .building-container {{ text-align: center; padding: 15px; overflow: hidden; }}
                            </style>
                            </head>
                            <body>
                            <div class="building-container">
                                <div style="position: relative; width: 200px; height: 200px; margin: 0 auto;">
                                    {arc_container}
                                    <!-- Building icon -->
                                    <div style="position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); width: 160px; height: 160px;">
                                        {'<img src="' + img_data_url + '" style="width: 100%; height: 100%; object-fit: contain;">' if img_data_url else '<div style="width: 100%; height: 100%; background: #E0E0E0; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #666;">No Icon</div>'}
                                    </div>
                                </div>
                                <div style="margin-top: 10px; font-weight: bold; font-size: 18px; color: white;">{building_type.replace('_', ' ').title()}</div>
                                <div style="font-size: 16px; color: #666;">Total: {total_count}</div>
                            </div>
                            </body>
                            </html>
                            """
                            
                            st.iframe(arc_html, height=340)
                        
                        col_idx += 1
                else:
                    st.warning("No buildings found for this player")
            except Exception as e:
                st.error(f"Error parsing buildings data: {e}")
        else:
            st.warning("No buildings data available for this player")

def create_pdd_tab(filtered_df):
    """Create the Player Deep Dive (PDD) tab"""
    
    if not filtered_df.empty:
        st.markdown("### 🔍 Player Deep Dive")
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            st.warning("No comprehensive CSV data found. This feature requires comprehensive CSV format.")
            return
        
        player_df = latest_data['raw_player_data']
        
        if isinstance(player_df, pd.DataFrame) and not player_df.empty:
            # Player search section
            st.markdown("#### Player Search")
            
            # Create player options with name, alliance, power
            player_options = []
            for _, player in player_df.iterrows():
                player_name = player.get('username', 'Unknown')
                alliance_name = player.get('alliance_name', 'None')
                power = player.get('power', 0)
                player_options.append(f"{player_name} | {alliance_name} | {int(power):,}")
            
            # Render player search in fragment for instant search updates
            render_player_search(player_options, latest_data, filtered_df)

@st.fragment
def render_player_search(player_options, latest_data, filtered_df):
    """Fragment for player search - only reruns when search input changes"""
    # Search box
    search_query = st.text_input("Search for a player:", placeholder="Type player name...")
    
    # Filter player options based on search
    if search_query:
        filtered_options = [opt for opt in player_options if search_query.lower() in opt.lower()]
    else:
        filtered_options = player_options[:100]  # Show first 100 by default
    
    if filtered_options:
        # Default to logged-in user if they're one of the four authorized users
        authorized_users = ['Gonhog', 'Moachi', 'Skenz', 'Higgins']
        default_index = 0
        if 'username' in st.session_state and st.session_state.username in authorized_users:
            logged_in_user = st.session_state.username
            # Find the index of the logged-in user in filtered_options
            for i, option in enumerate(filtered_options):
                if option.startswith(logged_in_user + ' |'):
                    default_index = i
                    break
        
        selected_player_option = st.selectbox("Select a player:", options=filtered_options, index=default_index)
        
        # Parse selected player
        selected_name = selected_player_option.split(' | ')[0]
        
        # Get player data from cache manager
        player_data = cache_manager.get_player_data_by_name(selected_name)
        
        if player_data:
            # Render all player details in fragment for instant widget updates
            render_player_details(selected_name, player_data, latest_data, filtered_df)
    else:
        st.info("No players found matching your search.")
