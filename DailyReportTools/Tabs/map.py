import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import re
import os

def create_map_tab(filtered_df):
    """Create the Map tab with city and outpost locations"""
    
    if not filtered_df.empty:
        st.markdown("### Map Settlement Locations")
        
        # Find the latest comprehensive data
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                if isinstance(data['raw_player_data'], pd.DataFrame):
                    latest_data = data
                    break
        
        if latest_data is None:
            st.warning("No comprehensive data available for map visualization.")
            return
        
        player_df = latest_data['raw_player_data']
        
        # Parse all settlements from buildings_metadata
        settlements = []
        
        for _, row in player_df.iterrows():
            username = row.get('username', '')
            account_id = row.get('account_id', '')
            buildings_metadata = row.get('buildings_metadata', '')
            equipped_skins = row.get('equipped_skins', '')
            
            if pd.isna(buildings_metadata) or not buildings_metadata:
                continue
            
            # Parse settlements from buildings_metadata
            # Format: "CityName(level)[type](x,y):[buildings]|CityName2(level)[type](x,y):[buildings]"
            individual_settlements = buildings_metadata.split('|')
            
            for settlement_metadata in individual_settlements:
                # Extract coordinates and type
                # Pattern: CityName(level)[type](x,y):[buildings]
                match = re.search(r'([^(]+)\((\d+)\)\[([^\]]+)\]\(([^,]+),([^)]+)\)', settlement_metadata)
                
                if match:
                    name = match.group(1).strip()
                    level = int(match.group(2))
                    settlement_type = match.group(3).strip()
                    x = int(match.group(4))
                    y = int(match.group(5))
                    
                    # Determine outpost subtype if applicable
                    outpost_subtype = None
                    if settlement_type.startswith('outpost'):
                        outpost_subtype = settlement_type  # e.g., "outpost", "water_outpost", "fire_outpost"
                        settlement_type = 'outpost'  # Normalize to 'outpost' for categorization
                    
                    # Determine icon based on settlement type and skins
                    if settlement_type == 'city':
                        # Check for city skins
                        icon = 'fortress.webp'
                        if equipped_skins and pd.notna(equipped_skins):
                            try:
                                skins = json.loads(equipped_skins) if isinstance(equipped_skins, str) else equipped_skins
                                if isinstance(skins, dict):
                                    # Check for city skins
                                    city_skins = [s for s in skins.keys() if 'city' in s.lower()]
                                    if city_skins:
                                        # Use the first city skin found
                                        icon = f"skin_{city_skins[0]}.webp"
                            except:
                                pass
                    elif settlement_type == 'outpost':
                        # Determine icon based on outpost subtype
                        if outpost_subtype and outpost_subtype != 'outpost':
                            # Use specific outpost icon if available (e.g., water_outpost.webp)
                            icon = f"{outpost_subtype}.webp"
                        else:
                            icon = 'water_outpost.webp'  # Default outpost icon
                    else:
                        icon = 'fortress.webp'  # Default
                    
                    settlements.append({
                        'name': name,
                        'type': settlement_type,
                        'subtype': outpost_subtype,  # Store the full subtype (e.g., "water_outpost")
                        'level': level,
                        'x': x,
                        'y': y,
                        'username': username,
                        'account_id': account_id,
                        'icon': icon
                    })
        
        if not settlements:
            st.warning("No settlement data found.")
            return
        
        # Player search - render in fragment for instant search updates
        render_settlement_search(settlements)
        cities = [s for s in settlements if s['type'] == 'city']
        outposts = [s for s in settlements if s['type'] == 'outpost']
        
        # Group outposts by subtype for different colors
        outpost_subtypes = {}
        for outpost in outposts:
            subtype = outpost['subtype'] if outpost['subtype'] else 'outpost'
            if subtype not in outpost_subtypes:
                outpost_subtypes[subtype] = []
            outpost_subtypes[subtype].append(outpost)
        
        st.markdown("#### Settlement Statistics")
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cities", len(cities))
        with col2:
            st.metric("Total Outposts", len(outposts))
        with col3:
            st.metric("Total Settlements", len(settlements))
        
        # Show outpost subtype breakdown if there are multiple types
        if len(outpost_subtypes) > 1:
            st.markdown("#### Outpost Types")
            subtype_cols = st.columns(len(outpost_subtypes))
            for i, (subtype, subtype_list) in enumerate(outpost_subtypes.items()):
                with subtype_cols[i]:
                    display_name = subtype.replace('_', ' ').title()
                    st.metric(display_name, len(subtype_list))
        
        st.markdown("---")
        
        # Create scatter plot
        fig = go.Figure()
        
        # Add cities to plot
        if cities:
            city_x = [s['x'] for s in cities]
            city_y = [s['y'] for s in cities]
            city_names = [f"{s['name']}<br>Player: {s['username']}" for s in cities]
            
            fig.add_trace(go.Scatter(
                x=city_x,
                y=city_y,
                mode='markers',
                name='Cities',
                marker=dict(
                    size=15,
                    color='#3498db',
                    symbol='diamond',
                    line=dict(color='white', width=2)
                ),
                text=city_names,
                hovertemplate='<b>%{text}</b><br>Coordinates: (%{x}, %{y})<extra></extra>',
                customdata=city_names
            ))
        
        # Add outposts to plot by subtype
        outpost_colors = {
            'outpost': '#e74c3c',
            'water_outpost': '#3498db',
            'fire_outpost': '#e67e22',
            'stone_outpost': '#95a5a6',
            'wood_outpost': '#27ae60',
        }
        
        for subtype, subtype_outposts in outpost_subtypes.items():
            if subtype_outposts:
                outpost_x = [s['x'] for s in subtype_outposts]
                outpost_y = [s['y'] for s in subtype_outposts]
                outpost_names = [f"{s['name']}<br>Player: {s['username']}" for s in subtype_outposts]
                
                # Use subtype for display name (capitalize and replace underscores)
                display_name = subtype.replace('_', ' ').title()
                
                fig.add_trace(go.Scatter(
                    x=outpost_x,
                    y=outpost_y,
                    mode='markers',
                    name=display_name,
                    marker=dict(
                        size=12,
                        color=outpost_colors.get(subtype, '#e74c3c'),
                        symbol='circle',
                        line=dict(color='white', width=2)
                    ),
                    text=outpost_names,
                    hovertemplate='<b>%{text}</b><br>Coordinates: (%{x}, %{y})<extra></extra>',
                    customdata=outpost_names,
                    showlegend=True
                ))
        
        # Update layout
        fig.update_layout(
            title="Settlement Map (-200 to 200)",
            xaxis_title="X Coordinate",
            yaxis_title="Y Coordinate",
            xaxis=dict(
                range=[-210, 210],
                zeroline=True,
                zerolinecolor='gray',
                zerolinewidth=2,
                gridcolor='lightgray',
                gridwidth=1
            ),
            yaxis=dict(
                range=[-210, 210],
                zeroline=True,
                zerolinecolor='gray',
                zerolinewidth=2,
                gridcolor='lightgray',
                gridwidth=1,
                scaleanchor="x",
                scaleratio=1
            ),
            height=900,
            hovermode='closest',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        # Add center marker (0,0)
        fig.add_trace(go.Scatter(
            x=[0],
            y=[0],
            mode='markers',
            name='Center',
            marker=dict(
                size=8,
                color='gold',
                symbol='star',
                line=dict(color='black', width=1)
            ),
            hovertemplate='Center (0,0)<extra></extra>',
            showlegend=True
        ))
        
        st.plotly_chart(fig, width='stretch')

@st.fragment
def render_settlement_search(settlements):
    """Fragment for settlement search - only reruns when search input changes"""
    # Player search
    st.markdown("#### Player Search")
    search_username = st.text_input("Search by username (partial match)")
    
    if search_username:
        search_results = [s for s in settlements if search_username.lower() in s['username'].lower()]
        if search_results:
            st.markdown(f"Found {len(search_results)} settlement(s) for players matching '{search_username}':")
            for result in search_results:
                st.write(f"- **{result['username']}**: {result['name']} ({result['type'].title()}) at coordinates ({result['x']}, {result['y']})")
        else:
            st.warning(f"No settlements found for username matching '{search_username}'")
        st.markdown("---")
