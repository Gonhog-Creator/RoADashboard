import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def create_skins_tab(filtered_df):
    """Create the Skins tab showing skin distribution and analytics"""
    
    if not filtered_df.empty:
        st.markdown("### Skins Skin Analytics")
        
        # Check if we have comprehensive data with skins information
        latest_data = filtered_df.iloc[-1]
        
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            # Handle case where raw_player_data might be converted to float by pandas
            if isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
                st.warning(f"Player data format error in skins tab: expected DataFrame but got {type(player_df)}. Value: {player_df}")
            else:
                # Check if equipped_skins column exists
                if 'equipped_skins' in player_df.columns:
                    st.markdown("#### Stats Skin Distribution Overview")
                
                    # Process skins data
                    skins_data = {}
                    players_with_skins = 0
                    total_players = len(player_df)
                    
                    for _, player in player_df.iterrows():
                        equipped_skins = player.get('equipped_skins')
                        if pd.notna(equipped_skins) and equipped_skins:
                            players_with_skins += 1
                            
                            # Parse skins (assuming it's a JSON string or comma-separated)
                            try:
                                if isinstance(equipped_skins, str):
                                    # Try to parse as JSON first
                                    if equipped_skins.startswith('{') or equipped_skins.startswith('['):
                                        skins_list = json.loads(equipped_skins)
                                        if isinstance(skins_list, dict):
                                            skins_list = list(skins_list.keys())
                                    else:
                                        # Assume comma-separated
                                        skins_list = [skin.strip() for skin in equipped_skins.split(',')]
                                else:
                                    skins_list = [equipped_skins]
                                
                                for skin in skins_list:
                                    if skin and skin.strip():
                                        skin_name = skin.strip()
                                        skins_data[skin_name] = skins_data.get(skin_name, 0) + 1
                            except:
                                # If parsing fails, treat as single skin
                                if equipped_skins and str(equipped_skins).strip():
                                    skin_name = str(equipped_skins).strip()
                                    skins_data[skin_name] = skins_data.get(skin_name, 0) + 1
                                    players_with_skins += 1
                
                # Display overview metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "Skins Total Players",
                            f"{total_players:,}"
                        )
                    
                    with col2:
                        st.metric(
                            "Skins Players with Skins",
                            f"{players_with_skins:,}",
                            f"{(players_with_skins/total_players*100):.1f}%" if total_players > 0 else "0%"
                        )
                    
                    with col3:
                        st.metric(
                            "Skins Unique Skins",
                            f"{len(skins_data):,}"
                        )
                    
                    if skins_data:
                        # Create skin distribution dataframe
                        skins_df = pd.DataFrame(list(skins_data.items()), columns=['Skin Name', 'Player Count'])
                        skins_df = skins_df.sort_values('Player Count', ascending=False)
                        skins_df['Percentage'] = (skins_df['Player Count'] / players_with_skins * 100).round(1) if players_with_skins > 0 else 0
                        
                        # Display skin distribution table
                        st.markdown("#### Table Skin Popularity Rankings")
                        st.dataframe(skins_df, use_container_width=True)
                        
                        # Create visualizations
                        st.markdown("#### Trends Skin Distribution Charts")
                    
                    # Top 15 skins chart
                        top_skins = skins_df.head(15)
                        
                        fig_top_skins = px.bar(
                            top_skins,
                            x='Player Count',
                            y='Skin Name',
                            orientation='h',
                            title='Top 15 Most Popular Skins',
                            color='Player Count',
                            color_continuous_scale='viridis'
                        )
                        fig_top_skins.update_layout(
                            xaxis_title="Number of Players",
                            yaxis_title="Skin Name",
                            height=500
                        )
                        st.plotly_chart(fig_top_skins, use_container_width=True)
                        
                        # Percentage distribution pie chart
                        if len(skins_df) <= 10:  # Only show pie chart if not too many skins
                            fig_pie = px.pie(
                                skins_df,
                                values='Player Count',
                                names='Skin Name',
                                title='Skin Distribution',
                                hole=0.3
                            )
                            fig_pie.update_layout(height=500)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        else:
                            # Show top 10 in pie chart
                            fig_pie = px.pie(
                                skins_df.head(10),
                                values='Player Count',
                                names='Skin Name',
                                title='Top 10 Skins Distribution',
                                hole=0.3
                            )
                            fig_pie.update_layout(height=500)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        
                        # Skin rarity analysis
                        st.markdown("#### Rarity Skin Rarity Analysis")
                    
                    # Define rarity categories based on player count
                        total_with_skins = players_with_skins
                        rarity_data = []
                        
                        for _, row in skins_df.iterrows():
                            player_count = row['Player Count']
                            percentage = (player_count / total_with_skins) * 100 if total_with_skins > 0 else 0
                            
                            if percentage >= 20:
                                rarity = "Common"
                            elif percentage >= 10:
                                rarity = "Uncommon"
                            elif percentage >= 5:
                                rarity = "Rare"
                            elif percentage >= 1:
                                rarity = "Epic"
                            else:
                                rarity = "Legendary"
                            
                            rarity_data.append({
                                'Skin Name': row['Skin Name'],
                                'Player Count': player_count,
                                'Percentage': percentage,
                                'Rarity': rarity
                            })
                        
                        rarity_df = pd.DataFrame(rarity_data)
                        
                        # Rarity distribution
                        rarity_counts = rarity_df['Rarity'].value_counts().reset_index()
                        rarity_counts.columns = ['Rarity', 'Skin Count']
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig_rarity = px.bar(
                                rarity_counts,
                                x='Rarity',
                                y='Skin Count',
                                title='Skin Count by Rarity',
                                color='Rarity',
                                color_discrete_map={
                                    'Common': 'gray',
                                    'Uncommon': 'green',
                                    'Rare': 'blue',
                                    'Epic': 'purple',
                                    'Legendary': 'orange'
                                }
                            )
                            fig_rarity.update_layout(height=400)
                            st.plotly_chart(fig_rarity, use_container_width=True)
                        
                        with col2:
                            # Show rarity table
                            rarity_summary = rarity_df.groupby('Rarity').agg({
                                'Skin Name': 'count',
                                'Player Count': 'sum',
                                'Percentage': 'mean'
                            }).round(1)
                            rarity_summary.columns = ['Number of Skins', 'Total Players', 'Avg Percentage']
                            st.dataframe(rarity_summary, use_container_width=True)
                        
                        # Detailed skin analysis
                        st.markdown("#### \ud83d\udd0d Detailed Skin Analysis")
                        
                        selected_skin = st.selectbox(
                            "Select a skin for detailed analysis:",
                            options=skins_df['Skin Name'].tolist(),
                            index=0
                        )
                        
                        if selected_skin:
                            skin_players = []
                            for _, player in player_df.iterrows():
                                equipped_skins = player.get('equipped_skins')
                                if pd.notna(equipped_skins) and equipped_skins:
                                    try:
                                        if isinstance(equipped_skins, str):
                                            if equipped_skins.startswith('{') or equipped_skins.startswith('['):
                                                skins_list = json.loads(equipped_skins)
                                                if isinstance(skins_list, dict):
                                                    skins_list = list(skins_list.keys())
                                            else:
                                                skins_list = [skin.strip() for skin in equipped_skins.split(',')]
                                        else:
                                            skins_list = [equipped_skins]
                                        
                                        if selected_skin in [s.strip() for s in skins_list]:
                                            skin_players.append({
                                                'Account ID': player['account_id'][:8] + "..." if len(player['account_id']) > 8 else player['account_id'],
                                                'Alliance': player.get('alliance_name', 'None'),
                                                'Power': player.get('power', 0),
                                                'Created': player.get('created_at', 'Unknown')
                                            })
                                    except:
                                        continue
                            
                            if skin_players:
                                st.markdown(f"##### \ud83d\udc65 Players with {selected_skin}")
                                
                                skin_df = pd.DataFrame(skin_players)
                                skin_df = skin_df.sort_values('Power', ascending=False)
                                st.dataframe(skin_df, use_container_width=True)
                                
                                # Power distribution for this skin
                                if 'Power' in skin_df.columns and skin_df['Power'].sum() > 0:
                                    fig_power = px.histogram(
                                        skin_df,
                                        x='Power',
                                        title=f'Power Distribution of Players with {selected_skin}',
                                        nbins=20
                                    )
                                    fig_power.update_layout(height=400)
                                    st.plotly_chart(fig_power, use_container_width=True)
                            else:
                                st.warning(f"No players found with {selected_skin}")
                    
                    else:
                        st.warning("No skin data found in the player records")
                else:
                    st.info("\u26a0\ufe0f No equipped skins data available. This feature requires the comprehensive CSV format with skins information.")
        
        else:
            st.info("\u26a0\ufe0f No detailed player data available. This feature requires the comprehensive CSV format.")
    
    else:
        st.info("No data available for skin analysis")
