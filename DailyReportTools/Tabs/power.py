import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

def calculate_daily_rate(sorted_df, value_column):
    """Calculate daily growth rates using time differences"""
    if len(sorted_df) < 2:
        return pd.Series([0] * len(sorted_df))
    
    daily_rates = []
    for i in range(len(sorted_df)):
        if i == 0:
            daily_rates.append(0)
        else:
            current_value = sorted_df.iloc[i][value_column]
            previous_value = sorted_df.iloc[i-1][value_column]
            current_time = sorted_df.iloc[i]['date']
            previous_time = sorted_df.iloc[i-1]['date']
            
            # Calculate time difference in days
            time_diff = (current_time - previous_time).total_seconds() / (24 * 3600)
            
            if time_diff > 0:  # Only calculate rate if time difference is significant
                # Calculate daily rate (change per day)
                change = current_value - previous_value
                daily_rate = change / time_diff
                daily_rates.append(daily_rate)
            else:
                daily_rates.append(0)
    
    return pd.Series(daily_rates)

def create_power_tab(filtered_df):
    """Create the Power tab with power analytics and charts"""
    
    if not filtered_df.empty:
        # Page title and toggle
        st.markdown("### ⚔️ Power Analytics")
        show_full_numbers = st.toggle("Show Full Numbers", key="power_tab_full_numbers")
        
        # Sort data by date
        sorted_df = filtered_df.sort_values('date')
        
        # Get latest power data
        latest_data = sorted_df.iloc[-1]
        total_power = latest_data.get('total_power', 0)
        avg_power_per_player = latest_data.get('avg_power_per_player', 0)
        latest_players = latest_data['total_players']
        
        # Calculate growth rates
        if len(sorted_df) >= 2:
            daily_power_rates = calculate_daily_rate(sorted_df, 'total_power')
            meaningful_changes = daily_power_rates.dropna()
            meaningful_changes = meaningful_changes[meaningful_changes != 0]
            daily_power_change = meaningful_changes.iloc[-1] if len(meaningful_changes) > 0 else 0
            
            daily_avg_power_rates = calculate_daily_rate(sorted_df, 'avg_power_per_player')
            avg_meaningful_changes = daily_avg_power_rates.dropna()
            avg_meaningful_changes = avg_meaningful_changes[avg_meaningful_changes != 0]
            daily_avg_power_change = avg_meaningful_changes.iloc[-1] if len(avg_meaningful_changes) > 0 else 0
        else:
            daily_power_change = 0
            daily_avg_power_change = 0
        
        # Format numbers function
        def format_number(num, show_full=False):
            if pd.isna(num):
                return "0"
            if show_full:
                return f"{int(num):,}"
            else:
                if abs(num) >= 1_000_000_000:
                    return f"{num/1_000_000_000:.1f}B"
                elif abs(num) >= 1_000_000:
                    return f"{num/1_000_000:.1f}M"
                elif abs(num) >= 1_000:
                    return f"{num/1_000:.1f}K"
                else:
                    return f"{int(num)}"
        
        def format_rate(rate, show_full=False):
            if pd.isna(rate):
                return "0/day"
            if show_full:
                return f"{int(rate):+,}/day"
            else:
                if abs(rate) >= 1_000_000_000:
                    return f"{rate/1_000_000_000:.1f}B/day"
                elif abs(rate) >= 1_000_000:
                    return f"{rate/1_000_000:.1f}M/day"
                elif abs(rate) >= 1_000:
                    return f"{rate/1_000:.1f}K/day"
                else:
                    return f"{int(rate):,}/day"
        
        # Key Metrics Section
        st.markdown("#### 📊 Key Power Metrics")
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric(
                "⚔️ Total Power",
                format_number(total_power, show_full_numbers),
                format_rate(daily_power_change, show_full_numbers)
            )
        
        with metric_col2:
            st.metric(
                "👤 Power per Player",
                format_number(avg_power_per_player, show_full_numbers),
                format_rate(daily_avg_power_change, show_full_numbers)
            )
        
        with metric_col3:
            st.metric(
                "👥 Total Players",
                f"{latest_players:,}",
                f"{(latest_players / sorted_df.iloc[0]['total_players'] - 1) * 100:.1f}%" if len(sorted_df) > 1 else "0%"
            )
        
        # Charts Section
        st.markdown("---")
        st.markdown("#### 📈 Power Trends")
        
        # Create subplots for power charts
        fig_power = make_subplots(
            rows=1, cols=2,
            subplot_titles=[
                "Total Power Over Time",
                "Power Changes"
            ],
            vertical_spacing=0.1,
            horizontal_spacing=0.1,
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}]
            ]
        )
        
        # 1. Total Power Over Time (Line Chart)
        fig_power.add_trace(
            go.Scatter(
                x=sorted_df['date'],
                y=sorted_df['total_power'],
                mode='lines+markers',
                name='Total Power',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=6),
                hovertemplate='<b>Total Power</b><br>Date: %{x}<br>Power: %{y:,.0f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 2. Power Changes (Line Chart) - Use actual changes like the data table
        # Calculate actual changes (same logic as data table)
        actual_changes = []
        for i in range(len(sorted_df)):
            if i == 0:
                actual_changes.append(0)  # No change for first day
            else:
                current_power = sorted_df.iloc[i]['total_power']
                previous_power = sorted_df.iloc[i-1]['total_power']
                
                # Skip if either value is NaN
                if pd.isna(current_power) or pd.isna(previous_power):
                    actual_changes.append(0)
                else:
                    # Show the actual change amount
                    change = current_power - previous_power
                    actual_changes.append(change)
        
        fig_power.add_trace(
            go.Scatter(
                x=sorted_df['date'],
                y=actual_changes,
                mode='lines+markers',
                name='Daily Change',
                line=dict(color='#4ECDC4', width=3),
                marker=dict(
                    size=6,
                    color=['#4ECDC4' if change != 0 else '#E0E0E0' for change in actual_changes]
                ),
                hovertemplate='<b>Change</b><br>Date: %{x}<br>Change: %{y:,.0f}<extra></extra>'
            ),
            row=1, col=2
        )
        
        # Update layout
        fig_power.update_layout(
            height=400,
            showlegend=False,
            title_text="Power Analytics Dashboard",
            title_x=0.5
        )
        
        # Update axes labels
        fig_power.update_xaxes(title_text="Date", row=1, col=1)
        fig_power.update_xaxes(title_text="Date", row=1, col=2)
        
        fig_power.update_yaxes(title_text="Total Power", row=1, col=1)
        fig_power.update_yaxes(title_text="Daily Change", row=1, col=2)
        
        st.plotly_chart(fig_power, use_container_width=True)
        
        # Data Table
        st.markdown("---")
        with st.expander("📋 Power Data Table"):
            # Create power-focused dataframe
            power_df = sorted_df[['date', 'total_power', 'avg_power_per_player', 'total_players']].copy()
            
            # Calculate daily changes more accurately - show actual change, not extrapolated daily rate
            daily_changes = []
            for i in range(len(sorted_df)):
                if i == 0:
                    daily_changes.append(0)  # No change for first day
                else:
                    current_power = sorted_df.iloc[i]['total_power']
                    previous_power = sorted_df.iloc[i-1]['total_power']
                    
                    # Skip if either value is NaN
                    if pd.isna(current_power) or pd.isna(previous_power):
                        daily_changes.append(0)
                        continue
                    
                    # Only calculate change if power actually changed
                    if current_power != previous_power:
                        # Show the actual change amount, not extrapolated daily rate
                        change = current_power - previous_power
                        daily_changes.append(change)  # Show actual change, not rate
                    else:
                        daily_changes.append(0)  # No change if power is same
            
            power_df['daily_change'] = daily_changes
            
            # Format columns
            if not show_full_numbers:
                power_df['total_power'] = power_df['total_power'].apply(format_number, args=(False,))
                power_df['avg_power_per_player'] = power_df['avg_power_per_player'].apply(format_number, args=(False,))
                power_df['daily_change'] = power_df['daily_change'].apply(lambda x: format_number(x, False) if pd.notna(x) else "0")
            else:
                power_df['total_power'] = power_df['total_power'].apply(lambda x: f"{int(x):,}")
                power_df['avg_power_per_player'] = power_df['avg_power_per_player'].apply(lambda x: f"{int(x):,}")
                power_df['daily_change'] = power_df['daily_change'].apply(lambda x: f"{int(x):+,}" if pd.notna(x) else "0")
            
            power_df['total_players'] = power_df['total_players'].apply(lambda x: f"{int(x):,}")
            power_df.columns = ['Date', 'Total Power', 'Power per Player', 'Total Players', 'Change']
            
            st.dataframe(power_df, width='stretch')
    
    else:
        st.info("No power data available")
