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
    """Enhanced Power tab with buckets, top players, and growth charts"""
    
    if not filtered_df.empty:
        st.markdown("### Enhanced Power Analytics")
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
        st.markdown("#### Key Power Metrics")
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric(
                "Total Power",
                format_number(total_power, show_full_numbers),
                format_rate(daily_power_change, show_full_numbers)
            )
        
        with metric_col2:
            st.metric(
                "Power per Player",
                format_number(avg_power_per_player, show_full_numbers),
                format_rate(daily_avg_power_change, show_full_numbers)
            )
        
        with metric_col3:
            st.metric(
                "Total Players",
                f"{latest_players:,}",
                f"{(latest_players / sorted_df.iloc[0]['total_players'] - 1) * 100:.1f}%" if len(sorted_df) > 1 else "0%"
            )
        
        # Power Buckets Analysis
        st.markdown("#### Power Distribution Buckets")
        
        # Check if we have comprehensive data
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            # Check if player_df is actually a DataFrame
            if isinstance(player_df, pd.DataFrame) and not player_df.empty and 'power' in player_df.columns:
                power_data = player_df['power'].fillna(0)
                
                # Define power buckets
                max_power = power_data.max()
                min_power = power_data.min()
                
                if max_power > min_power:
                    # Create custom buckets
                    bucket_ranges = [
                        (0, 1000, "New Players (0-1K)"),
                        (1000, 10000, "Early Game (1K-10K)"),
                        (10000, 100000, "Mid Game (10K-100K)"),
                        (100000, 1000000, "Late Game (100K-1M)"),
                        (1000000, 10000000, "End Game (1M-10M)"),
                        (10000000, float('inf'), "Whales (10M+)")
                    ]
                    
                    bucket_data = []
                    for min_range, max_range, label in bucket_ranges:
                        count = ((power_data >= min_range) & (power_data < max_range)).sum()
                        if max_range == float('inf'):
                            count = (power_data >= min_range).sum()
                        
                        if count > 0:
                            bucket_data.append({
                                'Power Range': label,
                                'Player Count': count,
                                'Percentage': (count / len(power_data) * 100),
                                'Total Power': power_data[(power_data >= min_range) & (power_data < max_range)].sum() if max_range != float('inf') else power_data[power_data >= min_range].sum()
                            })
                    
                    if bucket_data:
                        bucket_df = pd.DataFrame(bucket_data)
                        
                        # Bucket distribution chart
                        fig_buckets = px.bar(
                            bucket_df,
                            x='Power Range',
                            y='Player Count',
                            title='Player Distribution by Power Buckets',
                            hover_data={'Percentage': ':.1f%', 'Total Power': ':,'}
                        )
                        fig_buckets.update_layout(
                            xaxis_title="Power Range",
                            yaxis_title="Number of Players",
                            height=400
                        )
                        fig_buckets.update_traces(
                            hovertemplate='<b>%{x}</b><br>Players: %{y}<br>Percentage: %{customdata[0]:.1f}%<br>Total Power: %{customdata[1]:,}<extra></extra>'
                        )
                        st.plotly_chart(fig_buckets, use_container_width=True)
                        
                        # Bucket details table
                        bucket_display_df = bucket_df.copy()
                        bucket_display_df['Total Power'] = bucket_display_df['Total Power'].apply(lambda x: f"{int(x):,}")
                        bucket_display_df['Percentage'] = bucket_display_df['Percentage'].apply(lambda x: f"{x:.1f}%")
                        bucket_display_df.columns = ['Power Range', 'Players', '% of Total', 'Total Power']
                        st.dataframe(bucket_display_df, use_container_width=True)
        
        # Top 10 Players by Power
        st.markdown("#### Top 10 Players by Power")
        
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            if isinstance(player_df, pd.DataFrame) and not player_df.empty and 'power' in player_df.columns:
                top_players = player_df.nlargest(10, 'power')[['account_id', 'power', 'alliance_name', 'username']]
                
                if not top_players.empty:
                    # Display in smaller tiles using 2 rows of 5 columns
                    for row in range(2):
                        cols = st.columns(5)
                        
                        for col in range(5):
                            idx = row * 5 + col
                            if idx >= len(top_players):
                                break
                            
                            player = top_players.iloc[idx]
                            
                            # Use username if available, otherwise use account ID
                            if 'username' in player and pd.notna(player['username']):
                                player_name = str(player['username'])
                            else:
                                account_id = str(player['account_id'])[:8] + "..." if len(str(player['account_id'])) > 8 else str(player['account_id'])
                                player_name = account_id
                            
                            power = int(player['power'])
                            alliance = player.get('alliance_name', 'None')
                            
                            # Show power percentage of total
                            power_percentage = (power / total_power * 100) if total_power > 0 else 0
                            
                            with cols[col]:
                                tile_content = f"""
                                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 5px;">
                                    <h4 style="margin: 0 0 8px 0; color: white; font-size: 0.9em;">#{idx+1} {player_name}</h4>
                                    <p style="margin: 0 0 8px 0; font-size: 1.1em; font-weight: bold; color: #1f77b4;">{format_number(power, show_full_numbers)}</p>
                                    <p style="margin: 0 0 4px 0; font-size: 0.85em;">Alliance: {alliance}</p>
                                    <p style="margin: 0; font-size: 0.85em;">% of Realm: {power_percentage:.2f}%</p>
                                </div>
                                """
                                st.markdown(tile_content, unsafe_allow_html=True)
        
        # Enhanced Charts Section
        st.markdown("---")
        st.markdown("#### Enhanced Power Trends")
        
        # Create comprehensive power charts
        fig_power = make_subplots(
            rows=1, cols=2,
            subplot_titles=[
                "Total Power Over Time",
                "Power Changes"
            ],
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
        
        # 2. Power Changes (Line Chart)
        actual_changes = []
        for i in range(len(sorted_df)):
            if i == 0:
                actual_changes.append(0)
            else:
                current_power = sorted_df.iloc[i]['total_power']
                previous_power = sorted_df.iloc[i-1]['total_power']
                
                if pd.isna(current_power) or pd.isna(previous_power):
                    actual_changes.append(0)
                else:
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
            title_text="Comprehensive Power Analytics Dashboard",
            title_x=0.5
        )
        
        # Update axes labels
        fig_power.update_xaxes(title_text="Date", row=1, col=1)
        fig_power.update_xaxes(title_text="Date", row=1, col=2)
        
        fig_power.update_yaxes(title_text="Total Power", row=1, col=1)
        fig_power.update_yaxes(title_text="Daily Change", row=1, col=2)
        
        st.plotly_chart(fig_power, use_container_width=True)
        
        # Player Growth Chart (if comprehensive data available)
        if 'raw_player_data' in latest_data and len(filtered_df) > 1:
            st.markdown("#### Individual Player Power Growth")
            
            # Get top 10 players from latest data
            latest_player_df = latest_data['raw_player_data']
            if isinstance(latest_player_df, pd.DataFrame) and not latest_player_df.empty and 'power' in latest_player_df.columns:
                top_10_players_data = latest_player_df.nlargest(10, 'power')[['account_id', 'username']]
                
                # Create mapping of account_id to player name
                player_name_mapping = {}
                for _, player in top_10_players_data.iterrows():
                    account_id = player['account_id']
                    if 'username' in player and pd.notna(player['username']):
                        player_name_mapping[account_id] = str(player['username'])
                    else:
                        player_name_mapping[account_id] = str(account_id)[:8] + "..."
                
                top_10_players = top_10_players_data['account_id'].tolist()
                
                # Track their power over time
                player_growth_data = []
                
                for _, row in filtered_df.iterrows():
                    if 'raw_player_data' in row:
                        player_data = row['raw_player_data']
                        date = row['date']
                        
                        # Check if player_data is a DataFrame
                        if isinstance(player_data, pd.DataFrame) and not player_data.empty:
                            for player_id in top_10_players:
                                player_row = player_data[player_data['account_id'] == player_id]
                                if not player_row.empty:
                                    power = player_row['power'].iloc[0]
                                    player_growth_data.append({
                                        'Date': date,
                                        'Player': player_name_mapping.get(player_id, str(player_id)[:8] + "..."),
                                        'Power': power
                                    })
                
                if player_growth_data:
                    growth_df = pd.DataFrame(player_growth_data)
                    
                    fig_individual = px.line(
                        growth_df,
                        x='Date',
                        y='Power',
                        color='Player',
                        title='Top 10 Players Power Growth Over Time',
                        markers=True
                    )
                    fig_individual.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Power",
                        height=500
                    )
                    st.plotly_chart(fig_individual, use_container_width=True)
        
        # Data Table
        st.markdown("---")
        with st.expander("Power Data Table"):
            # Create power-focused dataframe
            power_df = sorted_df[['date', 'total_power', 'avg_power_per_player', 'total_players']].copy()
            
            # Calculate daily changes
            daily_changes = []
            for i in range(len(sorted_df)):
                if i == 0:
                    daily_changes.append(0)
                else:
                    current_power = sorted_df.iloc[i]['total_power']
                    previous_power = sorted_df.iloc[i-1]['total_power']
                    
                    if pd.isna(current_power) or pd.isna(previous_power):
                        daily_changes.append(0)
                        continue
                    
                    if current_power != previous_power:
                        change = current_power - previous_power
                        daily_changes.append(change)
                    else:
                        daily_changes.append(0)
            
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
