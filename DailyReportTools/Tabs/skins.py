import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

# Mapping of JSON skin names to common display names
SKIN_NAME_MAPPING = {
    'skin_city_alpha_all(building)': 'City Alpha All',
    'skin_avatar_border_founders(avatar_border)': 'Founders Avatar Border',
    'skin_city_founders(building)': 'City Founders',
    'skin_city_alpha_lvl9(building)': 'City Alpha Level 9',
    'skin_city_top3_challenge_1(building)': 'City Top 3 Challenge 1',
    'skin_water_pack_avatar_border(avatar_border)': 'Water Pack Avatar Border',
    'skin_water_pack_fortress(building)': 'Water Pack Fortress',
    'skin_city_top1_challenge_pvp_1(building)': 'City Top 1 PvP Challenge',
}

def get_common_skin_name(json_name):
    """Convert JSON skin name to common display name"""
    return SKIN_NAME_MAPPING.get(json_name, json_name)

def create_skins_tab(filtered_df):
    """Create the Skins tab showing skin distribution and analytics"""
    
    if not filtered_df.empty:
        st.markdown("### Skins Skin Analytics")
        
        # Find the latest data with skins information (comprehensive CSV)
        latest_skins_data = None
        for i in range(len(filtered_df) - 1, -1, -1):  # Iterate backwards to find latest with skin data
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_skins_data = data
                break
        
        if latest_skins_data is None:
            st.warning("No comprehensive CSV data found. This feature requires comprehensive CSV format.")
            return
        
        latest_data = latest_skins_data
        
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            # Handle case where raw_player_data might be converted to float by pandas
            if player_df is None:
                st.warning("Raw player data is None. This feature requires the comprehensive CSV format.")
            elif isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
                st.warning(f"Player data format error in skins tab: expected DataFrame but got {type(player_df)}. Value: {player_df}")
            else:
                # Check if equipped_skins column exists
                if 'equipped_skins' in player_df.columns:
                    # Process skins data
                    skins_data = {}
                    players_with_skins = 0
                    total_players = len(player_df)
                    
                    for _, player in player_df.iterrows():
                        equipped_skins = player.get('equipped_skins')
                        if pd.notna(equipped_skins) and equipped_skins:
                            players_with_skins += 1
                            
                            # Parse skins (assuming it's a JSON string, comma-separated, or pipe-separated)
                            try:
                                if isinstance(equipped_skins, str):
                                    # First split by | for combined entries
                                    combined_entries = equipped_skins.split('|')
                                    skins_list = []
                                    
                                    for entry in combined_entries:
                                        entry = entry.strip()
                                        # Try to parse as JSON first
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
                                            # Assume comma-separated or single entry
                                            if ',' in entry:
                                                skins_list.extend([skin.strip() for skin in entry.split(',')])
                                            else:
                                                skins_list.append(entry)
                                else:
                                    skins_list = [equipped_skins]
                                
                                for skin in skins_list:
                                    if skin and skin.strip():
                                        skin_name = skin.strip()
                                        common_name = get_common_skin_name(skin_name)
                                        skins_data[common_name] = skins_data.get(common_name, 0) + 1
                            except Exception as e:
                                # If parsing fails, try simple splitting
                                if equipped_skins and str(equipped_skins).strip():
                                    # Try splitting by | first
                                    combined_entries = str(equipped_skins).strip().split('|')
                                    for entry in combined_entries:
                                        entry = entry.strip()
                                        if entry:
                                            common_name = get_common_skin_name(entry)
                                            skins_data[common_name] = skins_data.get(common_name, 0) + 1
                                    players_with_skins += 1
                
                # Display overview metrics
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "Players with Skins",
                            f"{players_with_skins:,} ({(players_with_skins/total_players*100):.1f}%)" if total_players > 0 else f"{players_with_skins:,}"
                        )
                    
                    with col2:
                        st.metric(
                            "Unique Skins",
                            f"{len(skins_data):,}"
                        )
                    
                    if skins_data:
                        # Create skin tiles with images
                        skin_image_map = {
                            'City Alpha All': 'skin_city_alpha_all.webp',
                            'City Alpha Level 9': 'skin_city_alpha_lvl9.webp',
                            'City Founders': 'skin_city_founders.webp',
                            'City Top 1 PvP Challenge': 'skin_city_top1_challenge_pvp_1.webp',
                            'City Top 3 Challenge 1': 'skin_city_top3_challenge_1.webp',
                            'Founders Avatar Border': 'skin_avatar_border_founders_small.webp',
                            'Water Pack Avatar Border': 'skin_water_pack_avatar_border.webp',
                            'Water Pack Fortress': 'skin_water_pack_fortress.webp',
                        }
                        
                        # Sort skins by player count
                        sorted_skins = sorted(skins_data.items(), key=lambda x: x[1], reverse=True)
                        
                        # Display skin tiles in a responsive grid
                        st.markdown("#### Tiles Skin Collection")
                        cols_per_row = 5
                        for i in range(0, len(sorted_skins), cols_per_row):
                            cols = st.columns(min(cols_per_row, len(sorted_skins) - i))
                            for j, (skin_name, player_count) in enumerate(sorted_skins[i:i + cols_per_row]):
                                with cols[j]:
                                    image_file = skin_image_map.get(skin_name, None)
                                    if image_file:
                                        image_path = f"Images/{image_file}"
                                        try:
                                            st.image(image_path, width=70)
                                        except:
                                            st.write("🎨")
                                    else:
                                        st.write("🎨")
                                    
                                    st.markdown(f"**{skin_name}**")
                                    st.metric("Players", player_count)
                        # Create skin distribution dataframe
                        skins_df = pd.DataFrame(list(skins_data.items()), columns=['Skin Name', 'Player Count'])
                        skins_df = skins_df.sort_values('Player Count', ascending=False)
                        
                        # Display skin distribution table
                        st.markdown("#### Table Skin Popularity Rankings")
                        st.dataframe(skins_df, width='stretch')
                        
                        # Create visualizations
                        st.markdown("#### Trends Skin Distribution Charts")
                    
                    # Top 15 skins chart
                        top_skins = skins_df.head(15)
                        
                        fig_top_skins = px.bar(
                            top_skins,
                            x='Skin Name',
                            y='Player Count',
                            title='Top 15 Most Popular Skins'
                        )
                        fig_top_skins.update_layout(
                            xaxis_title="Skin Name",
                            yaxis_title="Number of Players",
                            height=500
                        )
                        st.plotly_chart(fig_top_skins, width='stretch')
                        
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
                            st.plotly_chart(fig_pie, width='stretch')
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
                            st.plotly_chart(fig_pie, width='stretch')
                        
                        # Detailed skin analysis
                        st.markdown("#### Detailed Skin Analysis")
                        
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
                                            # First split by | for combined entries
                                            combined_entries = equipped_skins.split('|')
                                            skins_list = []
                                            
                                            for entry in combined_entries:
                                                # Try to parse as JSON first
                                                if entry.startswith('{') or entry.startswith('['):
                                                    try:
                                                        parsed = json.loads(entry)
                                                        if isinstance(parsed, dict):
                                                            skins_list.extend(list(parsed.keys()))
                                                        else:
                                                            skins_list.extend(parsed)
                                                    except:
                                                        skins_list.append(entry.strip())
                                                else:
                                                    # Assume comma-separated
                                                    skins_list.extend([skin.strip() for skin in entry.split(',')])
                                        else:
                                            skins_list = [equipped_skins]
                                        
                                        # Convert JSON names to common names for comparison
                                        common_skin_names = [get_common_skin_name(s.strip()) for s in skins_list]
                                        if selected_skin in common_skin_names:
                                            skin_players.append({
                                                'Player Name': player.get('username', 'Unknown'),
                                                'Alliance': player.get('alliance_name', 'None'),
                                                'Power': player.get('power', 0),
                                                'Created': player.get('created_at', 'Unknown')
                                            })
                                    except:
                                        continue
                            
                            if skin_players:
                                st.markdown(f"##### Players with {selected_skin}")
                                
                                skin_df = pd.DataFrame(skin_players)
                                skin_df = skin_df.sort_values('Power', ascending=False)
                                
                                # Create display copy with formatted Power
                                display_df = skin_df.copy()
                                display_df['Power'] = display_df['Power'].apply(lambda x: f"{x:,}")
                                st.dataframe(display_df, width='stretch')
                                
                                # Power distribution for this skin (use numeric Power)
                                if 'Power' in skin_df.columns and skin_df['Power'].sum() > 0:
                                    fig_power = px.histogram(
                                        skin_df,
                                        x='Power',
                                        title=f'Power Distribution of Players with {selected_skin}',
                                        nbins=20
                                    )
                                    fig_power.update_layout(height=400)
                                    st.plotly_chart(fig_power, width='stretch')
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
