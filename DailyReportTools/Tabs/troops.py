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
            
            # Debug info
            st.info(f"Using troop data from: {latest_data.get('filename', 'Unknown file')} dated {latest_data.get('date', 'Unknown date')}")
            st.info(f"Troops data type: {type(troops_data)}, keys: {list(troops_data.keys()) if isinstance(troops_data, dict) else 'Not a dict'}")
            
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
                # Debug: show what values we're trying to sum
                st.write("Debug - Troops data values:")
                for key, value in troops_data.items():
                    st.write(f"  {key}: {value} (type: {type(value)})")
                
                # Try to sum only numeric values and exclude string fields
                numeric_values = []
                for key, value in troops_data.items():
                    try:
                        # Skip string fields like 'unique_troop_types' and any other string values
                        if key == 'unique_troop_types' or isinstance(value, str):
                            continue
                        if isinstance(value, (int, float)) and not pd.isna(value):
                            numeric_values.append(value)
                    except:
                        continue
                
                if numeric_values:
                    total_troops = sum(numeric_values)
                    st.write(f"Debug - Summed numeric values: {numeric_values}")
                else:
                    total_troops = 0
                    st.warning("No numeric troop values found to sum")
                
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
                        f"{avg_troops_per_player:.1f}",
                        help="Average number of troops per player"
                    )
                
                # Troop distribution chart
                if len(troops_data) > 1:
                    st.markdown("#### Trends Troop Distribution")
                    
                    troop_df = pd.DataFrame(list(troops_data.items()), columns=['Troop Type', 'Count'])
                    troop_df = troop_df.sort_values('Count', ascending=True)
                    
                    fig_troops = px.bar(
                        troop_df.tail(10),  # Show top 10 troop types
                        x='Count',
                        y='Troop Type',
                        orientation='h',
                        title='Top 10 Troop Types',
                        color='Count',
                        color_continuous_scale='viridis'
                    )
                    fig_troops.update_layout(
                        xaxis_title="Total Count",
                        yaxis_title="Troop Type",
                        height=400
                    )
                    st.plotly_chart(fig_troops, use_container_width=True)
            
            # Top 5 Players with Largest Armies
            st.markdown("#### Top Top 5 Players by Army Size")
            
            if 'raw_player_data' in latest_data:
                player_df = latest_data['raw_player_data']
                
                # Handle case where raw_player_data might be converted to float by pandas
                if isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
                    st.warning(f"Player data format error: expected DataFrame but got {type(player_df)}. Value: {player_df}")
                else:
                    # Calculate total troops for each player
                    troop_columns = [col for col in player_df.columns if 'troop' in col.lower()]
                    
                    if troop_columns:
                        player_df['total_troops'] = player_df[troop_columns].fillna(0).sum(axis=1)
                        
                        # Get top 5 players
                        top_players = player_df.nlargest(5, 'total_troops')[['account_id', 'total_troops'] + troop_columns]
                        
                        if not top_players.empty:
                            # Display top players
                            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                                account_id = player['account_id'][:8] + "..." if len(player['account_id']) > 8 else player['account_id']
                                total_troops = int(player['total_troops'])
                                
                                with st.expander(f"#{i} {account_id} - {total_troops:,} troops", expanded=i==1):
                                    # Show troop breakdown
                                    troop_breakdown = {}
                                    for col in troop_columns:
                                        if pd.notna(player[col]) and player[col] > 0:
                                            troop_breakdown[col] = int(player[col])
                                    
                                    if troop_breakdown:
                                        breakdown_df = pd.DataFrame(list(troop_breakdown.items()), columns=['Troop Type', 'Count'])
                                        breakdown_df = breakdown_df.sort_values('Count', ascending=False)
                                        
                                        fig_breakdown = px.bar(
                                            breakdown_df,
                                            x='Count',
                                            y='Troop Type',
                                            orientation='h',
                                            title=f"Army Composition - {account_id}",
                                            color='Count',
                                            color_continuous_scale='reds'
                                        )
                                        fig_breakdown.update_layout(
                                            xaxis_title="Count",
                                            yaxis_title="Troop Type",
                                            height=max(300, len(breakdown_df) * 30)
                                        )
                                        st.plotly_chart(fig_breakdown, use_container_width=True)
                                    else:
                                        st.info("No troop data available for this player")
                        else:
                            st.warning("No troop data found for players")
                    else:
                        st.warning("No troop columns found in player data")
            else:
                st.warning("Raw player data not available for detailed analysis")
        
        else:
            # Fallback for old format data or no troops data
            st.info("Warning No detailed troop data available. This feature requires the comprehensive CSV format.")
            
            # Show basic info if available
            if 'total_players' in latest_data:
                st.metric("Players Total Players", f"{latest_data['total_players']:,}")
    
    else:
        st.info("No data available for troop analysis")
