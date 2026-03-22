import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_daily_rate(values, dates):
    """Calculate true daily rate based on time differences between reports"""
    if len(values) < 2:
        return [0] * len(values)
    
    daily_rates = []
    for i in range(len(values)):
        if i == 0:
            daily_rates.append(0)  # First report has no rate
        else:
            current_value = values[i]
            previous_value = values[i-1]
            current_time = dates[i]
            previous_time = dates[i-1]
            
            # Calculate time difference in days
            time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
            
            if time_diff > 0:
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return daily_rates

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
            
            st.plotly_chart(fig_resources, use_container_width=True)
            
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
                
                st.plotly_chart(fig_combined, use_container_width=True)
            else:
                st.info("Please select at least one resource to display")
    else:
        st.info("No resource data available")
