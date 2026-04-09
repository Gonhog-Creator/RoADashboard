import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

def create_buildings_tab(filtered_df):
    """Create the Buildings tab with interactive building level analysis"""
    
    if not filtered_df.empty:
        st.markdown("### Buildings Building Analytics")
        
        # Check if we have comprehensive data with buildings information
        latest_data = filtered_df.iloc[-1]
        
        if 'buildings_data' in latest_data and latest_data['buildings_data']:
            buildings_data = latest_data['buildings_data']
            
            # Handle case where buildings_data might be converted to float by pandas
            if isinstance(buildings_data, (int, float)):
                st.warning(f"Buildings data format error: expected dictionary but got {type(buildings_data)}. Value: {buildings_data}")
                buildings_data = {}
            elif not isinstance(buildings_data, dict):
                st.warning(f"Buildings data format error: expected dictionary but got {type(buildings_data)}")
                buildings_data = {}
            
            # Building overview
            st.markdown("#### Stats Building Overview")
            
            if buildings_data:
                # Calculate building statistics
                building_stats = {}
                for building_name, levels in buildings_data.items():
                    if levels:
                        building_stats[building_name] = {
                            'total_count': len(levels),
                            'avg_level': sum(levels) / len(levels),
                            'max_level': max(levels),
                            'min_level': min(levels),
                            'level_distribution': {}
                        }
                        
                        # Count buildings by level
                        for level in levels:
                            level_key = f"Level {level}"
                            building_stats[building_name]['level_distribution'][level_key] = \
                                building_stats[building_name]['level_distribution'].get(level_key, 0) + 1
                
                # Create building summary dataframe
                summary_data = []
                for building_name, stats in building_stats.items():
                    summary_data.append({
                        'Building': building_name.replace('_', ' ').title(),
                        'Total Count': stats['total_count'],
                        'Average Level': f"{stats['avg_level']:.1f}",
                        'Max Level': stats['max_level'],
                        'Min Level': stats['min_level']
                    })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    summary_df = summary_df.sort_values('Total Count', ascending=False)
                    
                    st.dataframe(summary_df, use_container_width=True)
                
                # Interactive building selector
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
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Total Count", stats['total_count'])
                        with col2:
                            st.metric("Avg Level", f"{stats['avg_level']:.1f}")
                        with col3:
                            st.metric("Max Level", stats['max_level'])
                        with col4:
                            st.metric("Min Level", stats['min_level'])
                        
                        # Level distribution chart
                        st.markdown(f"##### Trends {selected_building.replace('_', ' ').title()} Level Distribution")
                        
                        level_dist = stats['level_distribution']
                        if level_dist:
                            level_df = pd.DataFrame(list(level_dist.items()), columns=['Level', 'Count'])
                            level_df = level_df.sort_values('Level')
                            
                            fig_level = px.bar(
                                level_df,
                                x='Level',
                                y='Count',
                                title=f"Distribution of {selected_building.replace('_', ' ').title()} Levels",
                                color='Count',
                                color_continuous_scale='blues'
                            )
                            fig_level.update_layout(
                                xaxis_title="Building Level",
                                yaxis_title="Number of Buildings",
                                height=400
                            )
                            st.plotly_chart(fig_level, use_container_width=True)
                            
                            # Level filter
                            st.markdown(f"##### Filter Filter Players by {selected_building.replace('_', ' ').title()} Level")
                            
                            min_level = int(stats['min_level'])
                            max_level = int(stats['max_level'])
                            
                            if min_level != max_level:
                                level_range = st.slider(
                                    f"Select {selected_building.replace('_', ' ').title()} level range:",
                                    min_level,
                                    max_level,
                                    (min_level, max_level)
                                )
                                
                                # Show players with buildings in selected level range
                                if 'raw_player_data' in latest_data:
                                    player_df = latest_data['raw_player_data']
                                    
                                    # Parse buildings for each player and filter
                                    matching_players = []
                                    
                                    for _, player in player_df.iterrows():
                                        if pd.notna(player.get('buildings_metadata')):
                                            try:
                                                buildings_info = eval(player['buildings_metadata'])
                                                for city_info in buildings_info.values():
                                                    if ':' in city_info:
                                                        buildings_list = city_info.split(':')[1].strip('[]')
                                                        for building in buildings_list.split(','):
                                                            if ':' in building:
                                                                building_name, level = building.split(':')
                                                                building_name = building_name.strip()
                                                                level = int(level.strip())
                                                                
                                                                if building_name == selected_building and level_range[0] <= level <= level_range[1]:
                                                                    matching_players.append({
                                                                        'Account ID': player['account_id'][:8] + "...",
                                                                        'Alliance': player.get('alliance_name', 'None'),
                                                                        'Building Level': level,
                                                                        'Created': player.get('created_at', 'Unknown')
                                                                    })
                                                                    break
                                            except:
                                                continue
                                    
                                    if matching_players:
                                        players_df = pd.DataFrame(matching_players)
                                        st.dataframe(players_df, use_container_width=True)
                                        st.info(f"Found {len(matching_players)} players with {selected_building.replace('_', ' ').title()} levels {level_range[0]}-{level_range[1]}")
                                    else:
                                        st.warning(f"No players found with {selected_building.replace('_', ' ').title()} levels {level_range[0]}-{level_range[1]}")
                            else:
                                st.info(f"All {selected_building.replace('_', ' ').title()} buildings are at level {min_level}")
                        
                        # Building comparison
                        st.markdown("##### Stats Building Comparison")
                        
                        if len(building_stats) > 1:
                            # Create comparison chart
                            comparison_data = []
                            for building_name, stats in building_stats.items():
                                comparison_data.append({
                                    'Building': building_name.replace('_', ' ').title(),
                                    'Total Count': stats['total_count'],
                                    'Average Level': stats['avg_level']
                                })
                            
                            comparison_df = pd.DataFrame(comparison_data)
                            
                            # Create subplots for comparison
                            fig_comparison = make_subplots(
                                rows=1, cols=2,
                                subplot_titles=['Total Count by Building', 'Average Level by Building'],
                                specs=[[{"type": "bar"}, {"type": "bar"}]]
                            )
                            
                            # Add total count bars
                            fig_comparison.add_trace(
                                go.Bar(
                                    x=comparison_df['Building'],
                                    y=comparison_df['Total Count'],
                                    name='Total Count',
                                    marker_color='lightblue'
                                ),
                                row=1, col=1
                            )
                            
                            # Add average level bars
                            fig_comparison.add_trace(
                                go.Bar(
                                    x=comparison_df['Building'],
                                    y=comparison_df['Average Level'],
                                    name='Average Level',
                                    marker_color='lightcoral'
                                ),
                                row=1, col=2
                            )
                            
                            fig_comparison.update_layout(
                                height=500,
                                showlegend=False,
                                title_text="Building Comparison Overview"
                            )
                            
                            fig_comparison.update_xaxes(tickangle=45)
                            st.plotly_chart(fig_comparison, use_container_width=True)
            
        else:
            # Fallback for old format data or no buildings data
            st.info("Warning No detailed building data available. This feature requires the comprehensive CSV format.")
            
            # Show basic info if available
            if 'total_players' in latest_data:
                st.metric("Players Total Players", f"{latest_data['total_players']:,}")
    
    else:
        st.info("No data available for building analysis")
