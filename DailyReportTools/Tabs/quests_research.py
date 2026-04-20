import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from collections import Counter

@st.fragment
def display_overview_metrics(stats, previous_stats=None):
    """Display quest and research overview metrics"""
    col1, col2 = st.columns(2)
    
    with col1:
        if 'completed_quests_count' in stats:
            current_total = stats['completed_quests_count']['total']
            # Calculate day-over-day increase
            if previous_stats and 'completed_quests_count' in previous_stats:
                previous_total = previous_stats['completed_quests_count']['total']
                increase = current_total - previous_total
                if increase >= 0:
                    delta = f"+{increase:,}"
                else:
                    delta = f"{increase:,}"
            else:
                delta = "N/A"
            
            st.metric(
                "Completed Quests",
                f"{current_total:,}",
                delta
            )
    
    with col2:
        if 'completed_research_count' in stats:
            current_total = stats['completed_research_count']['total']
            # Calculate day-over-day increase
            if previous_stats and 'completed_research_count' in previous_stats:
                previous_total = previous_stats['completed_research_count']['total']
                increase = current_total - previous_total
                if increase >= 0:
                    delta = f"+{increase:,}"
                else:
                    delta = f"{increase:,}"
            else:
                delta = "N/A"
            
            st.metric(
                "Completed Research",
                f"{current_total:,}",
                delta
            )

@st.fragment
def display_quest_completion(player_df):
    """Display quest completion overview"""
    if 'quest_metadata' in player_df.columns:
        st.markdown("#### Quest Completion Overview")
        
        all_quests = {}
        total_players = len(player_df)
        
        for _, player in player_df.iterrows():
            quest_metadata = player.get('quest_metadata')
            if pd.notna(quest_metadata) and quest_metadata:
                try:
                    if isinstance(quest_metadata, str):
                        quests = quest_metadata.split('|')
                        for quest in quests:
                            if ':' in quest:
                                parts = quest.split(':')
                                if len(parts) >= 3:
                                    quest_name = parts[0].strip().lower().replace('_', ' ')
                                    quest_level = parts[1].strip()
                                    quest_status = parts[2].strip()
                                    
                                    if quest_name not in all_quests:
                                        all_quests[quest_name] = {'total': set(), 'completed': set(), 'in_progress': set()}
                                    
                                    player_id = player.get('account_id', '')
                                    all_quests[quest_name]['total'].add(player_id)
                                    if quest_status == 'completed':
                                        all_quests[quest_name]['completed'].add(player_id)
                                    elif quest_status == 'in_progress':
                                        all_quests[quest_name]['in_progress'].add(player_id)
                except:
                    continue
        
        if all_quests:
            quest_summary = []
            for quest_name, player_sets in sorted(all_quests.items()):
                total_players_with_quest = len(player_sets['total'])
                completed_players = len(player_sets['completed'])
                in_progress_players = len(player_sets['in_progress'])
                completion_rate = (completed_players / total_players_with_quest * 100) if total_players_with_quest > 0 else 0
                
                quest_summary.append({
                    'Quest': quest_name.title(),
                    'Total Players': total_players_with_quest,
                    'Completed': completed_players,
                    'In Progress': in_progress_players,
                    'Completion Rate': f"{completion_rate:.1f}%"
                })
            
            if quest_summary:
                summary_df = pd.DataFrame(quest_summary)
                summary_df = summary_df.sort_values('Completion Rate', ascending=False)
                st.dataframe(summary_df, width='stretch', hide_index=True)
        else:
            st.info("No quest information available in quest_metadata")
    elif 'quest_details' in player_df.columns:
        st.markdown("#### Quest Completion Overview")
        
        all_quests = {}
        total_players = len(player_df)
        
        for _, player in player_df.iterrows():
            quest_details = player.get('quest_details')
            if pd.notna(quest_details) and quest_details:
                try:
                    if isinstance(quest_details, str):
                        quests = quest_details.split('|')
                        for quest in quests:
                            if ':' in quest:
                                parts = quest.split(':')
                                if len(parts) >= 2:
                                    quest_name = parts[0].strip().lower().replace('_', ' ')
                                    status = parts[1].strip()
                                    
                                    if quest_name not in all_quests:
                                        all_quests[quest_name] = {'total': set(), 'completed': set(), 'in_progress': set()}
                                    
                                    player_id = player.get('account_id', '')
                                    all_quests[quest_name]['total'].add(player_id)
                                    if status == 'completed':
                                        all_quests[quest_name]['completed'].add(player_id)
                                    elif status == 'in_progress':
                                        all_quests[quest_name]['in_progress'].add(player_id)
                except:
                    continue
        
        if all_quests:
            quest_summary = []
            for quest_name, player_sets in sorted(all_quests.items()):
                total_players_with_quest = len(player_sets['total'])
                completed_players = len(player_sets['completed'])
                in_progress_players = len(player_sets['in_progress'])
                completion_rate = (completed_players / total_players_with_quest * 100) if total_players_with_quest > 0 else 0
                
                quest_summary.append({
                    'Quest': quest_name.title(),
                    'Total Players': total_players_with_quest,
                    'Completed': completed_players,
                    'In Progress': in_progress_players,
                    'Completion Rate': f"{completion_rate:.1f}%"
                })
            
            summary_df = pd.DataFrame(quest_summary)
            summary_df = summary_df.sort_values('Completion Rate', ascending=False)
            st.dataframe(summary_df, width='stretch', hide_index=True)
        else:
            st.info("No quest information available")

@st.fragment
def display_research_level_distribution(player_df):
    """Display research level distribution"""
    if 'research_metadata' in player_df.columns:
        st.markdown("#### Research Level Distribution")
        
        all_research = {}
        total_players = len(player_df)
        
        for _, player in player_df.iterrows():
            research_metadata = player.get('research_metadata')
            if pd.notna(research_metadata) and research_metadata:
                try:
                    if isinstance(research_metadata, str):
                        research_items = research_metadata.split('|')
                        for research in research_items:
                            if ':' in research:
                                parts = research.split(':')
                                if len(parts) >= 2:
                                    research_name = parts[0].strip().lower().replace('_', ' ')
                                    level = parts[1].strip()
                                    
                                    try:
                                        level = int(level)
                                    except:
                                        level = 0
                                    
                                    if research_name not in all_research:
                                        all_research[research_name] = {}
                                    
                                    if level not in all_research[research_name]:
                                        all_research[research_name][level] = 0
                                    
                                    all_research[research_name][level] += 1
                except:
                    continue
        
        if all_research:
            research_types = sorted(all_research.keys())
            research_display_names = [name.title() for name in research_types]
            
            selected_research = st.radio(
                "Select a research type to view level distribution:",
                options=research_display_names,
                index=0,
                horizontal=True
            )
            
            if selected_research:
                selected_key = selected_research.lower().replace(' ', ' ')
                level_data = all_research[selected_key]
                sorted_levels = sorted(level_data.keys())
                
                fig_research = px.bar(
                    x=sorted_levels,
                    y=[level_data[level] for level in sorted_levels],
                    title=f"{selected_research} Level Distribution",
                    labels={'x': 'Level', 'y': 'Player Count'}
                )
                fig_research.update_layout(
                    xaxis_title="Level",
                    yaxis_title="Player Count",
                    height=400
                )
                st.plotly_chart(fig_research, width='stretch')
                
                st.markdown(f"**Summary for {selected_research}**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Players", sum(level_data.values()))
                with col2:
                    avg_level = sum(level * count for level, count in level_data.items()) / sum(level_data.values()) if level_data else 0
                    st.metric("Average Level", f"{avg_level:.1f}")
        else:
            st.info("No research information available in research_metadata")
    elif 'research_details' in player_df.columns:
        st.markdown("#### Research Level Distribution")
        
        all_research = {}
        total_players = len(player_df)
        
        for _, player in player_df.iterrows():
            research_details = player.get('research_details')
            if pd.notna(research_details) and research_details:
                try:
                    if isinstance(research_details, str):
                        research_items = research_details.split('|')
                        for research in research_items:
                            if ':' in research:
                                parts = research.split(':')
                                if len(parts) >= 2:
                                    research_name = parts[0].strip().lower().replace('_', ' ')
                                    level = parts[1].strip() if len(parts) >= 3 else 0
                                    
                                    try:
                                        level = int(level)
                                    except:
                                        level = 0
                                    
                                    if research_name not in all_research:
                                        all_research[research_name] = {}
                                    
                                    if level not in all_research[research_name]:
                                        all_research[research_name][level] = 0
                                    
                                    all_research[research_name][level] += 1
                except:
                    continue
        
        if all_research:
            research_types = sorted(all_research.keys())
            research_display_names = [name.title() for name in research_types]
            
            selected_research = st.radio(
                "Select a research type to view level distribution:",
                options=research_display_names,
                index=0,
                horizontal=True
            )
            
            if selected_research:
                selected_key = selected_research.lower().replace(' ', ' ')
                level_data = all_research[selected_key]
                sorted_levels = sorted(level_data.keys())
                
                fig_research = px.bar(
                    x=sorted_levels,
                    y=[level_data[level] for level in sorted_levels],
                    title=f"{selected_research} Level Distribution",
                    labels={'x': 'Level', 'y': 'Player Count'}
                )
                fig_research.update_layout(
                    xaxis_title="Level",
                    yaxis_title="Player Count",
                    height=400
                )
                st.plotly_chart(fig_research, width='stretch')
                
                st.markdown(f"**Summary for {selected_research}**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Players", sum(level_data.values()))
                with col2:
                    avg_level = sum(level * count for level, count in level_data.items()) / sum(level_data.values()) if level_data else 0
                    st.metric("Average Level", f"{avg_level:.1f}")
        else:
            st.info("No research information available")

@st.fragment
def display_progress_correlation(player_df, available_columns):
    """Display progress vs power correlation"""
    if 'power' in player_df.columns and ('completed_quests_count' in available_columns or 'completed_research_count' in available_columns):
        st.markdown("#### Progress vs Power Correlation")
        
        # Alliance selection with inverted behavior
        if 'alliance_name' in player_df.columns:
            all_alliances = sorted([x for x in player_df['alliance_name'].unique() if pd.notna(x) and isinstance(x, str)])
            selected_alliance = st.selectbox("Filter by Alliance (select to show only this alliance):", ["All"] + all_alliances)
            
            if selected_alliance != "All":
                # Inverted selection - show only selected alliance
                player_df = player_df[player_df['alliance_name'] == selected_alliance]
        
        # Log scale toggle
        use_log_scale = st.checkbox("Use Log Scale for Y-Axis", value=False)
        
        # Calculate total research levels for each player
        if 'research_metadata' in player_df.columns:
            player_df = player_df.copy()
            total_research_levels = []
            for _, player in player_df.iterrows():
                research_metadata = player.get('research_metadata')
                total_level = 0
                if pd.notna(research_metadata) and research_metadata:
                    try:
                        if isinstance(research_metadata, str):
                            research_items = research_metadata.split('|')
                            for research in research_items:
                                if ':' in research:
                                    parts = research.split(':')
                                    if len(parts) >= 2:
                                        level = parts[1].strip()
                                        try:
                                            total_level += int(level)
                                        except:
                                            pass
                    except:
                        pass
                total_research_levels.append(total_level)
            player_df['total_research_levels'] = total_research_levels
        
        # Format power values to K,M,B,T format
        def format_power(value):
            if pd.isna(value):
                return '0'
            value = float(value)
            if value >= 1e12:
                return f"{value/1e12:.0f}T"
            elif value >= 1e9:
                return f"{value/1e9:.0f}B"
            elif value >= 1e6:
                return f"{value/1e6:.0f}M"
            elif value >= 1e3:
                return f"{value/1e3:.0f}K"
            else:
                return f"{value:.0f}"
        
        player_df = player_df.copy()
        player_df['power_formatted'] = player_df['power'].apply(format_power)
        
        if 'completed_quests_count' in available_columns:
            fig_quests_power = px.scatter(
                player_df,
                x='completed_quests_count',
                y='power',
                title='Completed Quests vs Power',
                color='alliance_name' if 'alliance_name' in player_df.columns else None,
                color_discrete_sequence=px.colors.qualitative.Plotly,
                labels={'alliance_name': 'Alliance', 'completed_quests_count': 'Completed Quests', 'power': 'Power'},
                hover_data=['username', 'power_formatted'] if 'username' in player_df.columns else ['account_id', 'power_formatted'],
                custom_data=['username', 'power_formatted'] if 'username' in player_df.columns else ['account_id', 'power_formatted']
            )
            if 'username' in player_df.columns:
                fig_quests_power.update_traces(
                    hovertemplate='<b>%{customdata[0]}</b><br>Completed Quests: %{x}<br>Power: %{customdata[1]}<extra></extra>'
                )
            else:
                fig_quests_power.update_traces(
                    hovertemplate='<b>Account ID: %{customdata[0]}</b><br>Completed Quests: %{x}<br>Power: %{customdata[1]}<extra></extra>'
                )
            fig_quests_power.update_layout(height=400, yaxis_type='log' if use_log_scale else 'linear')
            st.plotly_chart(fig_quests_power, width='stretch')
        
        if 'completed_research_count' in available_columns:
            # Use total research levels instead of completed_research_count
            if 'total_research_levels' in player_df.columns:
                x_axis = 'total_research_levels'
                x_title = 'Total Research Levels'
            else:
                x_axis = 'completed_research_count'
                x_title = 'Completed Research Count'
            
            fig_research_power = px.scatter(
                player_df,
                x=x_axis,
                y='power',
                title='Completed Research vs Power',
                color='alliance_name' if 'alliance_name' in player_df.columns else None,
                color_discrete_sequence=px.colors.qualitative.Plotly,
                labels={'alliance_name': 'Alliance', x_axis: x_title, 'power': 'Power'},
                hover_data=['username', 'power_formatted'] if 'username' in player_df.columns else ['account_id', 'power_formatted'],
                custom_data=['username', 'power_formatted'] if 'username' in player_df.columns else ['account_id', 'power_formatted']
            )
            if 'username' in player_df.columns:
                fig_research_power.update_traces(
                    hovertemplate='<b>%{customdata[0]}</b><br>' + x_title + ': %{x}<br>Power: %{customdata[1]}<extra></extra>'
                )
            else:
                fig_research_power.update_traces(
                    hovertemplate='<b>Account ID: %{customdata[0]}</b><br>' + x_title + ': %{x}<br>Power: %{customdata[1]}<extra></extra>'
                )
            fig_research_power.update_layout(xaxis_title=x_title, height=400, yaxis_type='log' if use_log_scale else 'linear')
            st.plotly_chart(fig_research_power, width='stretch')
    else:
        st.info("\u26a0\ufe0f No quests or research data available. This feature requires the comprehensive CSV format with quest and research information.")

@st.fragment
def create_quests_research_tab(filtered_df):
    """Create the Quests & Research tab with completion analytics"""
    
    if not filtered_df.empty:
        st.markdown("### Quests Quests & Research Analytics")
        
        latest_quests_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_quests_data = data
                break
        
        if latest_quests_data is None:
            st.warning("No comprehensive CSV data found. This feature requires comprehensive CSV format.")
            return
        
        latest_data = latest_quests_data
        
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            available_columns = []
            if player_df is None:
                st.warning("Raw player data is None. This feature requires the comprehensive CSV format.")
            elif isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
                st.warning(f"Player data format error in quests tab: expected DataFrame but got {type(player_df)}. Value: {player_df}")
            else:
                quest_columns = ['completed_quests_count', 'completed_research_count', 'in_progress_quests_count']
                available_columns = [col for col in quest_columns if col in player_df.columns]
            
            if available_columns:
                st.markdown("#### Quest & Research Overview")
                
                total_players = len(player_df)
                stats = {}
                
                for col in available_columns:
                    stats[col] = {
                        'total': player_df[col].fillna(0).sum(),
                        'average': player_df[col].fillna(0).mean(),
                        'max': player_df[col].fillna(0).max(),
                        'players_with_progress': (player_df[col] > 0).sum()
                    }
                
                # Get previous day's stats for day-over-day comparison
                previous_stats = None
                for i in range(len(filtered_df) - 2, -1, -1):
                    data = filtered_df.iloc[i]
                    if 'raw_player_data' in data and data['raw_player_data'] is not None:
                        prev_player_df = data['raw_player_data']
                        if isinstance(prev_player_df, pd.DataFrame) and not prev_player_df.empty:
                            prev_stats = {}
                            for col in available_columns:
                                if col in prev_player_df.columns:
                                    prev_stats[col] = {
                                        'total': prev_player_df[col].fillna(0).sum()
                                    }
                            if prev_stats:
                                previous_stats = prev_stats
                                break
                
                display_overview_metrics(stats, previous_stats)
                display_quest_completion(player_df)
                display_research_level_distribution(player_df)
                display_progress_correlation(player_df, available_columns)
            
        else:
            st.info("\u26a0\ufe0f No detailed player data available. This feature requires the comprehensive CSV format.")
    
    else:
        st.info("No data available for quests and research analysis")
