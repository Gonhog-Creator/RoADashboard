import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import calculate_daily_rate, format_number, format_rate

def create_resources_tab(filtered_df):
    """Create the Resources tab with resource analysis"""
    
    st.subheader("Resource Trends")
    
    if not filtered_df.empty:
        # Get all resource types (already processed in overview)
        all_resources = set()
        for resources in filtered_df['resources']:
            if isinstance(resources, dict):
                all_resources.update(resources.keys())
        
        # Lock to main 6 resources only
        key_resources = ['gold', 'lumber', 'stone', 'metal', 'food', 'ruby']
        selected_resources = [r for r in key_resources if r in all_resources]
        
        if selected_resources:
            # Define colors for each resource
            resource_colors = {
                'Gold': '#FFD700',      # Gold/Yellow
                'Lumber': '#8B4513',    # Brown
                'Stone': '#808080',     # Grey
                'Food': '#F5DEB3',      # Wheat/Beige
                'Metal': '#708090',      # Slate Grey
                'Ruby': '#E0115F',      # Ruby Red
                'Elixir': '#9370DB',     # Medium Purple
                'Soul': '#4B0082',      # Indigo
                'Population': '#FF6347',  # Tomato
                'Blue Energy': '#1E90FF', # Dodger Blue
                'Talisman': '#FF69B4',   # Hot Pink
            }
            
            fig_resources = make_subplots(
                rows=len(selected_resources), 
                cols=2,
                subplot_titles=[f"{r.title()} - Total" if i % 2 == 0 else f"{r.title()} - Daily Rate" for r in selected_resources for i in range(2)],
                vertical_spacing=0.06,  # Reduced spacing
                horizontal_spacing=0.05,
                specs=[[{"secondary_y": False}, {"secondary_y": False}] for _ in selected_resources]
            )
            
            for i, resource in enumerate(selected_resources):
                # Get color for this resource (ensure we have a color)
                color = resource_colors.get(resource.title(), '#333333')
                
                # Overall amount (left column) - Line chart
                values = []
                for resources in filtered_df['resources']:
                    if isinstance(resources, dict) and resource in resources:
                        values.append(resources[resource])
                    else:
                        values.append(0)
                
                fig_resources.add_trace(
                    go.Scatter(
                        x=filtered_df['date'],
                        y=values,
                        mode='lines+markers',
                        name=f"{resource.title()} - Total",
                        line=dict(color=color),
                        marker=dict(color=color),
                        hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Amount: %{y:,.0f}<extra></extra>'
                    ),
                    row=i+1, col=1
                )
                
                # Daily change rate (right column) - Bar chart
                if len(values) >= 2:
                    # Sort data by date to ensure correct chronological order
                    sorted_data = filtered_df.sort_values('date')
                    sorted_values = []
                    sorted_dates = []
                    for _, data_row in sorted_data.iterrows():
                        if isinstance(data_row['resources'], dict) and resource in data_row['resources']:
                            sorted_values.append(data_row['resources'][resource])
                        else:
                            sorted_values.append(0)
                        sorted_dates.append(data_row['date'])
                    
                    # Calculate true daily rates using time differences
                    daily_changes = calculate_daily_rate(sorted_values, sorted_dates)
                    
                    # Aggregate by date to show one bar per day
                    date_df = pd.DataFrame({
                        'date': sorted_dates,
                        'daily_rate': daily_changes
                    })
                    # Group by date and take the mean (or sum) of daily rates for that day
                    daily_agg = date_df.groupby(date_df['date'].dt.date).agg({
                        'daily_rate': 'mean'  # or 'sum' depending on preference
                    }).reset_index()
                    daily_agg['date'] = pd.to_datetime(daily_agg['date'])
                    
                    # Color bars based on positive/negative
                    bar_colors = ['green' if x >= 0 else 'red' for x in daily_agg['daily_rate']]
                    
                    fig_resources.add_trace(
                        go.Bar(
                            x=daily_agg['date'],
                            y=daily_agg['daily_rate'],
                            name=f"{resource.title()} - Daily Rate",
                            marker=dict(color=bar_colors),
                            hovertemplate='<b>%{fullData.name}</b><br>Date: %{x}<br>Daily Change: %{y:,.0f}<extra></extra>'
                        ),
                        row=i+1, col=2
                    )
                
            fig_resources.update_layout(
                height=250 * len(selected_resources),  # Reduced chart height for tighter spacing
                title_text="Resource Analysis - Amount vs Daily Change Rate",
                showlegend=False
            )
            
            # Update x-axes labels
            for i in range(len(selected_resources)):
                fig_resources.update_xaxes(
                    title_text="Date", 
                    row=i+1, col=1,
                    tickformat='%Y-%m-%d'  # Show only date, no time
                )
                fig_resources.update_xaxes(
                    title_text="Date", 
                    row=i+1, col=2,
                    tickformat='%Y-%m-%d'  # Show only date, no time
                )
            
            # Update y-axes labels
            for i in range(len(selected_resources)):
                fig_resources.update_yaxes(title_text="Amount", row=i+1, col=1)
                fig_resources.update_yaxes(title_text="Daily Change (Raw Amount)", row=i+1, col=2)
            
            st.plotly_chart(fig_resources, config={'displayModeBar': False})
            
            # Elite Items Section (Fangtooth Respirators)
            st.markdown("---")
            st.markdown("### Elite Items")
            
            # Look for fangtooth respirators in resources data
            respirator_values = []
            respirator_dates = []
            
            for _, row in filtered_df.iterrows():
                respirator_count = 0
                
                # Check resources dictionary for fangtooth
                if 'resources' in row and isinstance(row['resources'], dict):
                    # Look for resource_fangtooth or similar
                    for resource_name, resource_value in row['resources'].items():
                        if 'fangtooth' in resource_name.lower():
                            respirator_count += resource_value
                
                # Also check raw_player_data for comprehensive format
                if 'raw_player_data' in row and row['raw_player_data'] is not None:
                    player_data = row['raw_player_data']
                    # Look for resource_fangtooth column
                    if 'resource_fangtooth' in player_data.columns:
                        respirator_count += player_data['resource_fangtooth'].fillna(0).sum()
                
                respirator_values.append(respirator_count)
                respirator_dates.append(row['date'])
            
            # Filter out leading zeros, keep only first zero point and actual data
            if sum(respirator_values) > 0:
                # Find first non-zero index
                first_nonzero_idx = next((i for i, v in enumerate(respirator_values) if v > 0), None)
                if first_nonzero_idx is not None and first_nonzero_idx > 0:
                    # Keep only the first zero and everything after first_nonzero_idx
                    respirator_values = [respirator_values[first_nonzero_idx - 1]] + respirator_values[first_nonzero_idx:]
                    respirator_dates = [respirator_dates[first_nonzero_idx - 1]] + respirator_dates[first_nonzero_idx:]
            
            if sum(respirator_values) > 0:
                # Add icon and name inline
                col1, col2 = st.columns([1, 15])
                with col1:
                    image_path = "Images/fangtooth_respirator.webp"
                    try:
                        st.image(image_path, width=50)
                    except:
                        st.write("🦷")
                with col2:
                    st.markdown("### Fangtooth Respirators")
                
                # Calculate daily rate
                if len(respirator_values) >= 2:
                    daily_rates = calculate_daily_rate(respirator_values, respirator_dates)
                    
                    # Aggregate by date
                    date_df = pd.DataFrame({
                        'date': respirator_dates,
                        'daily_rate': daily_rates
                    })
                    daily_agg = date_df.groupby(date_df['date'].dt.date).agg({
                        'daily_rate': 'mean'
                    }).reset_index()
                    daily_agg['date'] = pd.to_datetime(daily_agg['date'])
                    
                    # Color bars based on positive/negative
                    bar_colors = ['green' if x >= 0 else 'red' for x in daily_agg['daily_rate']]
                else:
                    daily_agg = None
                
                # Create combined chart with line and bar
                fig_respirators = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=["Total Quantity", "Daily Rate"],
                    horizontal_spacing=0.1
                )
                
                fig_respirators.add_trace(
                    go.Scatter(
                        x=respirator_dates,
                        y=respirator_values,
                        mode='lines+markers',
                        name='Total',
                        line=dict(color='#FF6B6B', width=2),
                        marker=dict(size=6, color='#FF6B6B'),
                        hovertemplate='<b>Fangtooth Respirators</b><br>Date: %{x}<br>Quantity: %{y:,.0f}<extra></extra>'
                    ),
                    row=1, col=1
                )
                
                if daily_agg is not None:
                    fig_respirators.add_trace(
                        go.Bar(
                            x=daily_agg['date'],
                            y=daily_agg['daily_rate'],
                            name='Daily Rate',
                            marker=dict(color=bar_colors),
                            hovertemplate='<b>Daily Rate</b><br>Date: %{x}<br>Change: %{y:,.0f}<extra></extra>'
                        ),
                        row=1, col=2
                    )
                
                fig_respirators.update_layout(
                    height=350,
                    showlegend=False
                )
                
                fig_respirators.update_xaxes(title_text="Date", row=1, col=1)
                fig_respirators.update_xaxes(title_text="Date", row=1, col=2)
                fig_respirators.update_yaxes(title_text="Quantity", row=1, col=1)
                fig_respirators.update_yaxes(title_text="Daily Change", row=1, col=2)
                
                st.plotly_chart(fig_respirators, config={'displayModeBar': False})
            else:
                st.info("No fangtooth respirators found in the data")
            
            # Combined Resources Line Chart
            st.markdown("---")
            st.markdown("### 📈 All Resources Over Time")

            # Add resource selection toggles
            st.markdown("**Select Resources to Display:**")
            resource_cols = st.columns(len(selected_resources))
            selected_resources_display = []

            for i, resource in enumerate(selected_resources):
                with resource_cols[i]:
                    # Default all resources to selected
                    is_selected = st.checkbox(
                        resource.title(), 
                        value=True,
                        key=f"show_resource_{resource}"
                    )
                    if is_selected:
                        selected_resources_display.append(resource)

            if selected_resources_display:
                # Create a combined line chart for selected resources
                fig_combined = go.Figure()
                
                for resource in selected_resources_display:
                    # Get color for this resource
                    color = resource_colors.get(resource.title(), '#333333')
                    
                    # Get values for this resource
                    values = []
                    for resources in filtered_df['resources']:
                        if isinstance(resources, dict) and resource in resources:
                            values.append(resources[resource])
                        else:
                            values.append(0)
                    
                    fig_combined.add_trace(
                        go.Scatter(
                            x=filtered_df['date'],
                            y=values,
                            mode='lines+markers',
                            name=resource.title(),
                            line=dict(color=color, width=2),
                            marker=dict(size=4),
                            hovertemplate=f'<b>{resource.title()}</b><br>Date: %{{x}}<br>Amount: %{{y:,.0f}}<extra></extra>'
                        )
                    )
                
                fig_combined.update_layout(
                    title="All Resources - Combined Trend",
                    xaxis_title="Date",
                    yaxis_title="Amount",
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    height=500
                )
                
                st.plotly_chart(fig_combined, config={'displayModeBar': False})
            else:
                st.info("Please select at least one resource to display")
    else:
        st.info("No resource data available")
