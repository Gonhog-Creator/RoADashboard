import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from cache_manager import cache_manager

def extract_buildings_data(df):
    """Extract buildings data from comprehensive CSV format"""
    buildings_data = {}
    
    if 'buildings_metadata' in df.columns:
        # Parse buildings metadata from comprehensive CSV format
        for _, row in df.iterrows():
            if pd.notna(row['buildings_metadata']):
                try:
                    buildings_metadata = row['buildings_metadata']
                    
                    # Handle both dict format and string format
                    if isinstance(buildings_metadata, str):
                        # Handle format: "CityName(level)city:[building1:1,building2:2]"
                        # Or "CityName(level)[city]:[building1:1,building2:2]"
                        # Multiple settlements separated by '|': "Settlement1...]:[buildings]|Settlement2...]:[buildings]"
                        
                        # First split by '|' to get individual settlements
                        individual_settlements = buildings_metadata.split('|')
                        
                        for settlement_metadata in individual_settlements:
                            # Try splitting by ']:[' first (new format with brackets)
                            if ']:[' in settlement_metadata:
                                settlement_parts = settlement_metadata.split(']:[')
                            else:
                                # Try splitting by ':[' (format without brackets around type)
                                settlement_parts = settlement_metadata.split(':[')
                            
                            if len(settlement_parts) >= 2:
                                # First part has settlement name and type
                                settlement_info = settlement_parts[0]
                                # Second part has buildings
                                buildings_str = settlement_parts[1].rstrip(']')
                                
                                # Extract settlement type from format "Name(level)type" or "Name(level)[type]"
                                if '[' in settlement_info:
                                    settlement_type = settlement_info.split('[')[1].rstrip(']')
                                elif ')' in settlement_info:
                                    # Format: "Name(level)type"
                                    parts = settlement_info.split(')')
                                    if len(parts) >= 2:
                                        settlement_type = parts[1]
                                    else:
                                        settlement_type = 'city'
                                else:
                                    settlement_type = 'city'  # Default to city for old format
                                
                                # Parse buildings from the string
                                if buildings_str:
                                    for building in buildings_str.split(','):
                                        if ':' in building:
                                            building_name, level = building.split(':')
                                            building_name = building_name.strip()
                                            level = int(level.strip())
                                            
                                            # Skip fortresses in outposts (they don't have fortresses)
                                            if settlement_type == 'outpost' and building_name == 'fortress':
                                                continue
                                            
                                            # Track both unique players and total instances
                                            if building_name not in buildings_data:
                                                buildings_data[building_name] = {'players': set(), 'levels': [], 'total_instances': 0}
                                            buildings_data[building_name]['players'].add(row['account_id'])  # Track unique player
                                            buildings_data[building_name]['total_instances'] += 1  # Count all instances
                                            buildings_data[building_name]['levels'].append(level)  # Keep levels for distribution
                    elif isinstance(buildings_metadata, dict):
                        # Handle dict format
                        for city_info in buildings_metadata.values():
                            if ':' in city_info:
                                buildings_list = city_info.split(':')[1].strip('[]')
                                for building in buildings_list.split(','):
                                    if ':' in building:
                                        building_name, level = building.split(':')
                                        building_name = building_name.strip()
                                        level = int(level.strip())
                                        if building_name not in buildings_data:
                                            buildings_data[building_name] = {'players': set(), 'levels': [], 'total_instances': 0}
                                        buildings_data[building_name]['players'].add(row['account_id'])
                                        buildings_data[building_name]['total_instances'] += 1
                                        buildings_data[building_name]['levels'].append(level)
                except Exception as e:
                    continue
    
    return buildings_data

def create_buildings_tab(filtered_df):
    """Create the Buildings tab with interactive building level analysis"""
    
    if not filtered_df.empty:
        st.markdown("### Buildings Building Analytics")
        
        # Get cached building stats from cache manager
        buildings_data = cache_manager.get_building_stats()
        
        if not buildings_data:
            st.warning("No building data found. Please ensure data is loaded.")
            return
        
        latest_data = filtered_df.iloc[-1]  # Use latest row for metadata
        
        if buildings_data:
            
            # Building overview
            st.markdown("#### Stats Building Overview")
            
            if buildings_data:
                # Calculate building statistics
                building_stats = {}
                # Buildings that can have multiple instances per player (count all instances)
                multi_instance_buildings = {'home', 'garrison', 'farm', 'mine', 'quarry', 'lumbermill', 'silo', 'house'}
                
                for building_name, data in buildings_data.items():
                    if data and 'players' in data:
                        # Use total_instances for multi-instance buildings, unique players for single-instance
                        if building_name in multi_instance_buildings:
                            count = data.get('total_instances', 0)
                        else:
                            count = len(data['players'])
                        
                        building_stats[building_name] = {
                            'total_count': count,
                            'level_distribution': {}
                        }
                        
                        # Count buildings by level
                        for level in data['levels']:
                            level_key = f"Level {level}"
                            building_stats[building_name]['level_distribution'][level_key] = \
                                building_stats[building_name]['level_distribution'].get(level_key, 0) + 1
                
                # Create building tiles with images
                building_image_map = {
                    'dragon_keep': 'dragon_keep.webp',
                    'factory': 'factory.webp',
                    'fangtooth_cache': 'fangtooth_cache.webp',
                    'fangtooth_factory': 'fangtooth_factory.webp',
                    'farm': 'farm.webp',
                    'fortress': 'fortress.webp',
                    'fountain_of_life': 'foutain_of_life.webp',
                    'garrison': 'garrison.webp',
                    'home': 'home.webp',
                    'lumbermill': 'lumbermill.webp',
                    'metalsmith': 'metalsmith.webp',
                    'mine': 'mine.webp',
                    'muster_point': 'muster_point.webp',
                    'quarry': 'quarry.webp',
                    'rookery': 'rookery.webp',
                    'science_center': 'science_center.webp',
                    'sentinel': 'sentinel.webp',
                    'storage_vault': 'storage_vault.webp',
                    'theater': 'theater.webp',
                    'wall': 'wall.webp'
                }
                
                if building_stats:
                    # Sort buildings by total count
                    sorted_buildings = sorted(building_stats.items(), key=lambda x: x[1]['total_count'], reverse=True)
                    
                    # Display building tiles in a responsive grid
                    cols_per_row = 6  # Increased from 4 to use more screen width
                    for i in range(0, len(sorted_buildings), cols_per_row):
                        cols = st.columns(min(cols_per_row, len(sorted_buildings) - i))
                        for j, (building_name, stats) in enumerate(sorted_buildings[i:i + cols_per_row]):
                            with cols[j]:
                                image_file = building_image_map.get(building_name, 'home.webp')
                                image_path = f"Images/{image_file}"
                                
                                try:
                                    st.image(image_path, width=70)
                                except:
                                    st.write(f"🏠")
                                
                                st.markdown(f"**{building_name.replace('_', ' ').title()}**")
                                st.metric("Total Count", stats['total_count'])
                
                # Interactive building selector
                # Render in fragment for instant selectbox updates
                render_building_analysis(building_stats)

@st.fragment
def render_building_analysis(building_stats):
    """Fragment for Interactive Building Analysis - only reruns when selectbox changes"""
    st.markdown("#### Interactive Interactive Building Analysis")
    
    if building_stats:
        # Building selection
        building_names = list(building_stats.keys())
        selected_building = st.selectbox(
            "Select a building to analyze:",
            building_names,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        if selected_building:
            stats = building_stats[selected_building]
            
            # Display building statistics
            col1 = st.columns(1)[0]
            
            with col1:
                st.metric("Total Count", stats['total_count'])
            
            # Level distribution chart
            st.markdown(f"##### Trends {selected_building.replace('_', ' ').title()} Level Distribution")
            
            level_dist = stats['level_distribution']
            if level_dist:
                # Extract numeric level for sorting and display
                level_data = []
                for level_key, count in level_dist.items():
                    # Extract numeric part from "Level 1", "Level 2", etc.
                    level_num = int(level_key.replace('Level ', ''))
                    level_data.append({'Level': level_num, 'Count': count})
                
                level_df = pd.DataFrame(level_data)
                level_df = level_df.sort_values('Level')
                
                fig_level = px.bar(
                    level_df,
                    x='Level',
                    y='Count',
                    title=f"Distribution of {selected_building.replace('_', ' ').title()} Levels"
                )
                fig_level.update_layout(
                    xaxis_title="Building Level",
                    yaxis_title="Number of Buildings",
                    height=400
                )
                st.plotly_chart(fig_level, width='stretch')
    
    else:
        st.info("No data available for building analysis")
