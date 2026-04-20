import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from cache_manager import cache_manager

@st.fragment
def render_troops_over_time_chart(filtered_df, latest_data):
    """Fragment for Troops Over Time chart - only reruns when checkboxes change"""
    st.markdown("#### Troops Over Time")
    
    # Get comprehensive data from cache for troops over time chart
    if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
        player_df = latest_data['raw_player_data']
        
        # Get troop columns from JSON or old format
        if 'troops_json' in player_df.columns:
            # Parse troops from JSON format
            all_troop_types = set()
            for _, player_row in player_df.iterrows():
                try:
                    troops_dict = json.loads(player_row['troops_json'])
                    all_troop_types.update(troops_dict.keys())
                except:
                    continue
            troop_columns = [f'troop_{troop_type}' for troop_type in all_troop_types]
        else:
            # Fallback to old format (individual troop columns)
            troop_columns = [col for col in player_df.columns if col.startswith('troop_') and col != 'unique_troop_types']
        
        if troop_columns:
            # Create checkboxes for troop selection
            troop_names = [col.replace('troop_', '').replace('_', ' ').title() for col in troop_columns]
            
            # Filter out Great Dragon and Water Dragon
            troop_names = [t for t in troop_names if t not in ["Great Dragon", "Water Dragon"]]
            
            st.markdown("**Select troop types to display:**")
            
            # Display checkboxes in columns to fill screen width (4 columns)
            cols_per_row = 4
            selected_troops = []
            
            for i, troop in enumerate(troop_names):
                col_idx = i % cols_per_row
                if i % cols_per_row == 0:
                    cols = st.columns(cols_per_row)
                
                with cols[col_idx]:
                    # Only Conscripts selected by default
                    is_selected = st.checkbox(
                        troop,
                        value=(troop == "Conscript"),
                        key=f"troop_checkbox_{troop.replace(' ', '_')}"
                    )
                    if is_selected:
                        selected_troops.append(troop)
            
            if selected_troops:
                # Collect troops data over time
                troops_over_time = []
                
                for _, row in filtered_df.iterrows():
                    if 'troops_data' in row and row['troops_data'] and not isinstance(row['troops_data'], (int, float)):
                        troops_data = row['troops_data']
                        date = row['date']
                        
                        if isinstance(troops_data, dict):
                            troop_entry = {'Date': date}
                            
                            for troop_name, troop_value in troops_data.items():
                                if isinstance(troop_value, str) or troop_name == 'unique_troop_types':
                                    continue
                                
                                # Filter out Great Dragon and Water Dragon
                                if any(dragon in troop_name.lower() for dragon in ['great_dragon', 'water_dragon']):
                                    continue
                                
                                display_name = troop_name.replace('_', ' ').title()
                                
                                if display_name in selected_troops:
                                    if hasattr(troop_value, 'item'):
                                        troop_value = troop_value.item()
                                    troop_entry[display_name] = troop_value
                            
                            troops_over_time.append(troop_entry)
                
                if troops_over_time:
                    troops_over_time_df = pd.DataFrame(troops_over_time)
                    troops_over_time_df = troops_over_time_df.sort_values('Date')
                    
                    # Create line chart
                    fig = go.Figure()
                    
                    for troop in selected_troops:
                        if troop in troops_over_time_df.columns:
                            fig.add_trace(
                                go.Scatter(
                                    x=troops_over_time_df['Date'],
                                    y=troops_over_time_df[troop],
                                    mode='lines+markers',
                                    name=troop
                                )
                            )
                    
                    fig.update_layout(
                        title="Troop Count Over Time",
                        xaxis_title="Date",
                        yaxis_title="Number of Troops",
                        height=400
                    )
                    
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.warning("No troops data available over time")
            else:
                st.info("Please select at least one troop type to display")

def parse_waver_troops(metadata):
    """Parse waver troops from player metadata"""
    if pd.isna(metadata) or not metadata:
        return 0
    
    try:
        metadata_dict = json.loads(str(metadata).replace('""', '"'))
        if 'waver_config' in metadata_dict:
            waver_config = metadata_dict['waver_config']
            if 'lines' in waver_config:
                total_waver_troops = 0
                for line in waver_config['lines']:
                    if 'troops' in line and 'waveAmount' in line:
                        wave_amount = line['waveAmount']
                        for troop in line['troops']:
                            troop_amount = troop.get('amount', 0)
                            total_waver_troops += troop_amount * wave_amount
                return total_waver_troops
        return 0
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0

def create_troops_tab(filtered_df):
    """Create the Troops tab with troop analytics and top armies"""
    
    if not filtered_df.empty:
        st.markdown("### Troops Troop Analytics")
        
        # Get cached troops stats from cache manager
        troops_data = cache_manager.get_troops_stats()
        
        if not troops_data:
            st.warning("No troop data found. Please ensure data is loaded.")
            return
        
        latest_data = filtered_df.iloc[-1]  # Use latest row for metadata
        
        # Handle case where troops_data might be converted to float by pandas
        if isinstance(troops_data, (int, float)):
            st.warning(f"Troops data format error: expected dictionary but got {type(troops_data)}. Value: {troops_data}")
            troops_data = {}
        elif not isinstance(troops_data, dict):
            st.warning(f"Troops data format error: expected dictionary but got {type(troops_data)}")
            troops_data = {}
        
        # Total troops overview
        st.markdown("#### Stats Total Troops Overview")
        
        if troops_data:
            # Sum all troop values, excluding string fields
            total_troops = 0
            
            for key, value in troops_data.items():
                try:
                    # Skip string fields like 'unique_troop_types'
                    if key == 'unique_troop_types' or isinstance(value, str):
                        continue
                    # Handle both regular numeric types and numpy types
                    if hasattr(value, 'item'):  # numpy types have .item() method
                        numeric_value = value.item()
                    else:
                        numeric_value = value
                    
                    if isinstance(numeric_value, (int, float)) and not pd.isna(numeric_value) and numeric_value > 0:
                        total_troops += numeric_value
                except:
                    continue
            
            # Add defending troops from raw_player_data
            if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
                player_df = latest_data['raw_player_data']
                if 'defending_troops' in player_df.columns:
                    total_troops += player_df['defending_troops'].fillna(0).sum()
            
            # Add waver troops from metadata (they come back)
            if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
                player_df = latest_data['raw_player_data']
                if 'metadata' in player_df.columns:
                    total_waver_troops = player_df['metadata'].apply(parse_waver_troops).sum()
                    total_troops += total_waver_troops
            
            # Create metrics for total troops
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Troops Total Troops",
                    f"{total_troops:,}",
                    help="Total number of all troops in the realm"
                )
            
            with col2:
                avg_troops_per_player = total_troops / latest_data['total_players'] if latest_data['total_players'] > 0 else 0
                st.metric(
                    "Players Troops per Player",
                    f"{int(avg_troops_per_player):,}",
                    help="Average number of troops per player"
                )
            
            # Detailed troop breakdown
            st.markdown("#### Troop Type Breakdown")
            
            # Get comprehensive data from cache for detailed breakdown
            if 'raw_player_data' in latest_data and latest_data['raw_player_data'] is not None:
                player_df = latest_data['raw_player_data']
                
                # Get all troop columns from player data
                if 'troops_json' in player_df.columns:
                    # Parse troops from JSON format
                    all_troop_types = set()
                    for _, player_row in player_df.iterrows():
                        try:
                            troops_dict = json.loads(player_row['troops_json'])
                            all_troop_types.update(troops_dict.keys())
                        except:
                            continue
                    troop_columns = [f'troop_{troop_type}' for troop_type in all_troop_types]
                else:
                    # Fallback to old format (individual troop columns)
                    troop_columns = [col for col in player_df.columns if col.startswith('troop_') and col != 'unique_troop_types']
                
                if troop_columns:
                    # Filter out Great Dragon and Water Dragon from troop columns
                    troop_columns = [col for col in troop_columns if not any(dragon in col for dragon in ['great_dragon', 'water_dragon'])]
                    
                    # Parse troop counts from JSON if available
                    if 'troops_json' in player_df.columns:
                        # Create a dictionary to store troop counts per player
                        player_troop_counts = {}
                        for _, player_row in player_df.iterrows():
                            player_id = player_row['account_id']
                            try:
                                troops_dict = json.loads(player_row['troops_json'])
                                # Add defending troops to the troop counts
                                if 'defending_troops' in player_row and pd.notna(player_row['defending_troops']):
                                    troops_dict['defending_troops'] = player_row['defending_troops']
                                # Add waver troops to the troop counts (they come back)
                                waver_troops = parse_waver_troops(player_row.get('metadata'))
                                if waver_troops > 0:
                                    troops_dict['waver_troops'] = waver_troops
                                player_troop_counts[player_id] = troops_dict
                            except:
                                player_troop_counts[player_id] = {}
                    else:
                        # Convert troop columns to numeric for old format
                        for col in troop_columns:
                            player_df[col] = pd.to_numeric(player_df[col], errors='coerce').fillna(0)
                        player_troop_counts = None
                    
                    # Display troop types in a 3-column grid of tiles
                    cols = st.columns(3)
                    col_idx = 0
                    
                    for troop_col in troop_columns:
                        # Get total amount from troops_data
                        troop_name = troop_col.replace('troop_', '').replace('_', ' ').title()
                        troop_key = troop_col.replace('troop_', '')  # Remove 'troop_' prefix for lookup
                        total_amount = troops_data.get(troop_key, 0)
                        
                        # Handle numpy types
                        if hasattr(total_amount, 'item'):
                            total_amount = total_amount.item()
                        
                        if total_amount > 0:  # Only show troop types that exist
                            # Get top 5 players for this troop type
                            if player_troop_counts:
                                # Use JSON data
                                troop_type = troop_col.replace('troop_', '')
                                player_troop_list = []
                                for player_id, troops_dict in player_troop_counts.items():
                                    count = troops_dict.get(troop_type, 0)
                                    if count > 0:
                                        player_row = player_df[player_df['account_id'] == player_id].iloc[0]
                                        player_troop_list.append({
                                            'account_id': player_id,
                                            'username': player_row.get('username', ''),
                                            'count': count
                                        })
                                player_troop_list.sort(key=lambda x: x['count'], reverse=True)
                                top_players_list = player_troop_list[:5]
                            else:
                                # Use old column format
                                top_players_list = player_df[player_df[troop_col] > 0].nlargest(5, troop_col)
                            
                            # Create tile content
                            tile_content = f"""
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 5px;">
                                <h4 style="margin: 0 0 10px 0; color: white;">{troop_name}</h4>
                                <p style="margin: 0 0 10px 0; font-size: 1.2em; font-weight: bold; color: #1f77b4;">Total: {int(total_amount):,}</p>
                            """
                            
                            if player_troop_counts:
                                # JSON format - top_players_list is a list of dicts
                                if top_players_list:
                                    tile_content += "<p style='margin: 0 0 5px 0; font-weight: bold;'>Top 5 Players:</p><ul style='margin: 0; padding-left: 20px;'>"
                                    for i, player_data in enumerate(top_players_list, 1):
                                        if player_data.get('username'):
                                            player_identifier = str(player_data['username'])
                                        else:
                                            account_id = str(player_data['account_id'])[:8] + "..." if len(str(player_data['account_id'])) > 8 else str(player_data['account_id'])
                                            player_identifier = account_id
                                        troop_count = int(player_data['count']) if pd.notna(player_data['count']) else 0
                                        tile_content += f"<li style='margin: 5px 0;'>{i}. {player_identifier}: {troop_count:,}</li>"
                                    tile_content += "</ul>"
                                else:
                                    tile_content += "<p style='margin: 0;'>No players have this troop type</p>"
                            else:
                                # Old format - top_players_list is a DataFrame
                                if not top_players_list.empty:
                                    tile_content += "<p style='margin: 0 0 5px 0; font-weight: bold;'>Top 5 Players:</p><ul style='margin: 0; padding-left: 20px;'>"
                                    for i, (_, player) in enumerate(top_players_list.iterrows(), 1):
                                        # Use username if available, otherwise use account ID
                                        if 'username' in player and pd.notna(player['username']):
                                            player_identifier = str(player['username'])
                                        else:
                                            account_id = str(player['account_id'])[:8] + "..." if len(str(player['account_id'])) > 8 else str(player['account_id'])
                                            player_identifier = account_id
                                        
                                        troop_count = int(player[troop_col]) if pd.notna(player[troop_col]) else 0
                                        tile_content += f"<li style='margin: 5px 0;'>{i}. {player_identifier}: {troop_count:,}</li>"
                                    tile_content += "</ul>"
                                else:
                                    tile_content += "<p style='margin: 0;'>No players have this troop type</p>"
                            
                            tile_content += "</div>"
                            
                            with cols[col_idx]:
                                st.markdown(tile_content, unsafe_allow_html=True)
                            
                            col_idx = (col_idx + 1) % 3
    
    # Render troops over time chart in fragment for instant checkbox updates
    render_troops_over_time_chart(filtered_df, latest_data)
    
    # Top 10 Players with Largest Armies
    st.markdown("#### Top 10 Players by Army Size")
    
    if 'raw_player_data' in latest_data:
        player_df = latest_data['raw_player_data']
        
        # Handle case where raw_player_data might be converted to float by pandas
        if isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
            st.warning(f"Player data format error: expected DataFrame but got {type(player_df)}. Value: {player_df}")
        else:
            # Use total_troop_amount if available, otherwise calculate from individual troop columns
            if 'total_troop_amount' in player_df.columns:
                # Convert to numeric and use directly
                player_df['total_troops'] = pd.to_numeric(player_df['total_troop_amount'], errors='coerce').fillna(0)
            else:
                # Fallback: calculate from individual troop columns
                troop_columns = [col for col in player_df.columns if 'troop' in col.lower() and col != 'unique_troop_types']
                
                if troop_columns:
                    # Convert all troop columns to numeric, coercing errors to NaN
                    for col in troop_columns:
                        player_df[col] = pd.to_numeric(player_df[col], errors='coerce')
                    
                    # Fill NaN with 0 and sum
                    player_df['total_troops'] = player_df[troop_columns].fillna(0).sum(axis=1)
                else:
                    st.warning("No troop data available")
                    return
            
            # Get top 10 players
            top_players = player_df.nlargest(10, 'total_troops')
            
            if not top_players.empty:
                # Create a table with players as rows and troops as columns
                troop_data_table = []
                
                for i, (_, player) in enumerate(top_players.iterrows()):
                    # Use username if available, otherwise use account ID
                    if 'username' in player and pd.notna(player['username']):
                        player_name = str(player['username'])
                    else:
                        account_id = str(player['account_id'])[:8] + "..." if len(str(player['account_id'])) > 8 else str(player['account_id'])
                        player_name = account_id
                    
                    row_data = {'Player': player_name}
                    
                    # Check if troops_json exists and parse it
                    if 'troops_json' in player and pd.notna(player['troops_json']):
                        try:
                            troops_dict = json.loads(player['troops_json'])
                            for troop_name, troop_value in troops_dict.items():
                                if isinstance(troop_value, (int, float)) and not isinstance(troop_value, str):
                                    display_name = troop_name.replace('_', ' ').title()
                                    # Filter out Great Dragon and Water Dragon
                                    if not any(dragon in troop_name.lower() for dragon in ['great_dragon', 'water_dragon']):
                                        row_data[display_name] = troop_value
                        except:
                            pass
                    else:
                        # Fallback to individual troop columns
                        troop_columns = [col for col in player_df.columns if 'troop' in col.lower() and col != 'unique_troop_types' and col != 'total_troop_amount' and col != 'total_troops']
                        for col in troop_columns:
                            col_value = player[col]
                            # Extract scalar value safely
                            if isinstance(col_value, (pd.Series, list, tuple)):
                                col_value = col_value.iloc[0] if isinstance(col_value, pd.Series) else col_value[0]
                            
                            # Convert to numeric if it's a string
                            try:
                                col_value = pd.to_numeric(col_value, errors='coerce')
                            except:
                                col_value = 0
                            
                            if pd.notna(col_value) and col_value > 0:
                                troop_name = col.replace('troop_', '').replace('_', ' ').title()
                                # Filter out Great Dragon and Water Dragon
                                if not any(dragon in col.lower() for dragon in ['great_dragon', 'water_dragon']):
                                    row_data[troop_name] = col_value
                    
                    # Add total troops to row
                    total_troops_val = player['total_troops']
                    if pd.isna(total_troops_val):
                        total_troops = 0
                    elif isinstance(total_troops_val, (pd.Series, list, tuple)):
                        total_troops = int(total_troops_val.iloc[0] if isinstance(total_troops_val, pd.Series) else total_troops_val[0])
                    else:
                        total_troops = int(total_troops_val)
                    row_data['Total'] = total_troops
                    
                    troop_data_table.append(row_data)
                
                # Create DataFrame and display
                if troop_data_table:
                    troops_df = pd.DataFrame(troop_data_table)
                    troops_df = troops_df.set_index('Player')
                    
                    # Move Total column to the end
                    if 'Total' in troops_df.columns:
                        total_col = troops_df.pop('Total')
                        troops_df['Total'] = total_col
                    
                    # Format all numeric columns with commas
                    for col in troops_df.columns:
                        troops_df[col] = troops_df[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else "0")
                    
                    st.dataframe(troops_df, width='stretch')
            else:
                st.warning("No troop data found for players")
    else:
        st.warning("Raw player data not available for detailed analysis")
