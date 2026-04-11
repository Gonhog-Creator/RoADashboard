import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def create_troops_tab(filtered_df):
    """Create the Troops tab with troop analytics and top armies"""
    
    if not filtered_df.empty:
        st.markdown("### Troops Troop Analytics")
        
        # Find the latest data with troops information (comprehensive CSV)
        latest_troop_data = None
        for i in range(len(filtered_df) - 1, -1, -1):  # Iterate backwards to find latest with troop data
            data = filtered_df.iloc[i]
            if 'troops_data' in data and data['troops_data'] and not isinstance(data['troops_data'], (int, float)):
                latest_troop_data = data
                break
        
        if latest_troop_data is not None:
            latest_data = latest_troop_data
            troops_data = latest_data['troops_data']
            
                        
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
                
                # Detailed troop breakdown with top 5 players for each troop type
                if 'raw_player_data' in latest_data and len(troops_data) > 1:
                    st.markdown("#### Troop Type Breakdown")
                    
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
                        # Parse troop counts from JSON if available
                        if 'troops_json' in player_df.columns:
                            # Create a dictionary to store troop counts per player
                            player_troop_counts = {}
                            for _, player_row in player_df.iterrows():
                                player_id = player_row['account_id']
                                try:
                                    troops_dict = json.loads(player_row['troops_json'])
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
                            total_amount = troops_data.get(troop_col, 0)
                            
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
                                            troop_count = int(player_data['count'])
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
                                            
                                            troop_count = int(player[troop_col])
                                            tile_content += f"<li style='margin: 5px 0;'>{i}. {player_identifier}: {troop_count:,}</li>"
                                        tile_content += "</ul>"
                                    else:
                                        tile_content += "<p style='margin: 0;'>No players have this troop type</p>"
                                
                                tile_content += "</div>"
                                
                                with cols[col_idx]:
                                    st.markdown(tile_content, unsafe_allow_html=True)
                                
                                col_idx = (col_idx + 1) % 3
            
            # Troops Over Time Chart
            st.markdown("#### Troops Over Time")
            
            # Get all troop types from the latest data
            if 'raw_player_data' in latest_data:
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
                    # Create checkboxes for troop selection (like resource tab)
                    troop_names = [col.replace('troop_', '').replace('_', ' ').title() for col in troop_columns]
                    
                    # Add resource selection toggles
                    st.markdown("**Select Troop Types to Display:**")
                    
                    # Split checkboxes into two rows to prevent name cutoff
                    mid_point = (len(troop_names) + 1) // 2
                    first_row_troops = troop_names[:mid_point]
                    second_row_troops = troop_names[mid_point:]
                    
                    selected_troops_display = []
                    
                    # First row of checkboxes
                    troop_cols_row1 = st.columns(len(first_row_troops))
                    for i, troop in enumerate(first_row_troops):
                        with troop_cols_row1[i]:
                            # Default all individual troops to selected
                            is_selected = st.checkbox(
                                troop, 
                                value=True,
                                key=f"show_troop_{troop}"
                            )
                            if is_selected:
                                selected_troops_display.append(troop)
                    
                    # Second row of checkboxes
                    troop_cols_row2 = st.columns(len(second_row_troops) + 1)  # +1 for Total Troops
                    for i, troop in enumerate(second_row_troops):
                        with troop_cols_row2[i]:
                            # Default all individual troops to selected
                            is_selected = st.checkbox(
                                troop, 
                                value=True,
                                key=f"show_troop_{troop}"
                            )
                            if is_selected:
                                selected_troops_display.append(troop)
                    
                    # Add Total Troops checkbox in second row
                    with troop_cols_row2[len(second_row_troops)]:
                        # Default Total Troops to not selected
                        is_total_selected = st.checkbox(
                            "Total Troops",
                            value=False,
                            key="show_troop_total"
                        )
                        if is_total_selected:
                            selected_troops_display = ["Total Troops"]
                    
                    # Collect troops data over time from all CSV files
                    troops_over_time = []
                    
                    if selected_troops_display:
                        for _, row in filtered_df.iterrows():
                            if 'troops_data' in row and row['troops_data'] and not isinstance(row['troops_data'], (int, float)):
                                troops_data = row['troops_data']
                                date = row['date']
                                
                                if isinstance(troops_data, dict):
                                    troop_entry = {'Date': date}
                                    
                                    # Add individual troop data
                                    for troop_col in troop_columns:
                                        troop_name = troop_col.replace('troop_', '').replace('_', ' ').title()
                                        if troop_name in selected_troops_display:
                                            troop_value = troops_data.get(troop_col, 0)
                                            # Handle numpy types
                                            if hasattr(troop_value, 'item'):
                                                troop_value = troop_value.item()
                                            troop_entry[troop_name] = troop_value
                                    
                                    # Add total troops if selected
                                    if "Total Troops" in selected_troops_display:
                                        total_troops = 0
                                        for key, value in troops_data.items():
                                            try:
                                                if key == 'unique_troop_types' or isinstance(value, str):
                                                    continue
                                                if hasattr(value, 'item'):
                                                    numeric_value = value.item()
                                                else:
                                                    numeric_value = value
                                                
                                                if isinstance(numeric_value, (int, float)) and not pd.isna(numeric_value) and numeric_value > 0:
                                                    total_troops += numeric_value
                                            except:
                                                continue
                                        troop_entry["Total Troops"] = total_troops
                                    
                                    troops_over_time.append(troop_entry)
                        
                        if troops_over_time:
                            troops_over_time_df = pd.DataFrame(troops_over_time)
                            troops_over_time_df = troops_over_time_df.sort_values('Date')
                            
                            # Create line chart
                            fig_troops_over_time = go.Figure()
                            
                            for troop in selected_troops_display:
                                if troop in troops_over_time_df.columns:
                                    fig_troops_over_time.add_trace(
                                        go.Scatter(
                                            x=troops_over_time_df['Date'],
                                            y=troops_over_time_df[troop],
                                            mode='lines+markers',
                                            name=troop,
                                            line=dict(width=2)
                                        )
                                    )
                            
                            fig_troops_over_time.update_layout(
                                title="Troop Count Over Time",
                                xaxis_title="Date",
                                yaxis_title="Number of Troops",
                                height=400,
                                hovermode='x unified'
                            )
                            
                            st.plotly_chart(fig_troops_over_time, use_container_width=True)
                        else:
                            st.warning("No troops data available over time")
                    else:
                        st.info("Please select at least one troop type to display")
            
            # Top 5 Players with Largest Armies
            st.markdown("#### Top 5 Players by Army Size")
            
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
                    
                    # Get top 5 players
                    top_players = player_df.nlargest(5, 'total_troops')
                    
                    if not top_players.empty:
                        # Display top players in a table
                        for i, (_, player) in enumerate(top_players.iterrows(), 1):
                            # Use username if available, otherwise use account ID
                            if 'username' in player and pd.notna(player['username']):
                                player_name = str(player['username'])
                            else:
                                account_id = str(player['account_id'])[:8] + "..." if len(str(player['account_id'])) > 8 else str(player['account_id'])
                                player_name = account_id
                            
                            # Extract scalar value safely
                            total_troops_val = player['total_troops']
                            if isinstance(total_troops_val, (pd.Series, list, tuple)):
                                total_troops = int(total_troops_val.iloc[0] if isinstance(total_troops_val, pd.Series) else total_troops_val[0])
                            else:
                                total_troops = int(total_troops_val)
                            
                            st.markdown(f"**#{i} {player_name}** - {total_troops:,} troops")
                            
                            # Show troop breakdown as simple table
                            troop_breakdown = {}
                            troop_columns = [col for col in player_df.columns if 'troop' in col.lower() and col != 'unique_troop_types' and col != 'total_troop_amount' and col != 'total_troops']
                            
                            for col in troop_columns:
                                col_value = player[col]
                                # Extract scalar value safely
                                if isinstance(col_value, (pd.Series, list, tuple)):
                                    col_value = col_value.iloc[0] if isinstance(col_value, pd.Series) else col_value[0]
                                
                                if pd.notna(col_value) and col_value > 0:
                                    troop_name = col.replace('troop_', '').replace('_', ' ').title()
                                    troop_breakdown[troop_name] = int(col_value)
                            
                            if troop_breakdown:
                                # Create simple table with 3 column pairs for compact display
                                breakdown_df = pd.DataFrame(list(troop_breakdown.items()), columns=['Troop Type', 'Amount'])
                                breakdown_df = breakdown_df.sort_values('Amount', ascending=False)
                                
                                # Split into 3 columns
                                cols = st.columns(3)
                                for j in range(3):
                                    with cols[j]:
                                        # Get subset of data for this column
                                        start_idx = j * (len(breakdown_df) // 3 + 1)
                                        end_idx = start_idx + (len(breakdown_df) // 3 + 1)
                                        subset = breakdown_df.iloc[start_idx:end_idx]
                                        
                                        if not subset.empty:
                                            st.dataframe(subset, use_container_width=True, hide_index=True)
                            else:
                                st.info("No troop data available for this player")
                            
                            st.markdown("---")
                    else:
                        st.warning("No troop data found for players")
            else:
                st.warning("Raw player data not available for detailed analysis")
        
        else:
            # Fallback for old format data or no troops data
            st.info("Warning No detailed troop data available. This feature requires the comprehensive CSV format.")
    
    else:
        st.info("No data available for troop analysis")
