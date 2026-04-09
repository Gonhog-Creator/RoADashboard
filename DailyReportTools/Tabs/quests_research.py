import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from collections import Counter

def create_quests_research_tab(filtered_df):
    """Create the Quests & Research tab with completion analytics"""
    
    if not filtered_df.empty:
        st.markdown("### Quests Quests & Research Analytics")
        
        # Check if we have comprehensive data
        latest_data = filtered_df.iloc[-1]
        
        if 'raw_player_data' in latest_data:
            player_df = latest_data['raw_player_data']
            
            # Handle case where raw_player_data might be converted to float by pandas
            if isinstance(player_df, (int, float)) or not hasattr(player_df, 'columns'):
                st.warning(f"Player data format error in quests tab: expected DataFrame but got {type(player_df)}. Value: {player_df}")
            else:
                # Check if quests/research columns exist
                quest_columns = ['completed_quests_count', 'completed_research_count', 'in_progress_quests_count']
                available_columns = [col for col in quest_columns if col in player_df.columns]
            
            if available_columns:
                    st.markdown("#### \ud83d\udcca Quest & Research Overview")
                    
                    # Calculate overall statistics
                    total_players = len(player_df)
                    stats = {}
                    
                    for col in available_columns:
                        stats[col] = {
                            'total': player_df[col].fillna(0).sum(),
                            'average': player_df[col].fillna(0).mean(),
                            'max': player_df[col].fillna(0).max(),
                            'players_with_progress': (player_df[col] > 0).sum()
                        }
                
                # Display overview metrics
                    if 'completed_quests_count' in stats:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "\u2705 Completed Quests",
                                f"{stats['completed_quests_count']['total']:,}",
                                f"{stats['completed_quests_count']['average']:.1f} avg"
                            )
                        
                        with col2:
                            completion_rate = (stats['completed_quests_count']['players_with_progress'] / total_players * 100) if total_players > 0 else 0
                            st.metric(
                                "\ud83d\udc65 Players with Quests",
                                f"{stats['completed_quests_count']['players_with_progress']:,}",
                                f"{completion_rate:.1f}%"
                            )
                        
                        with col3:
                            st.metric(
                                "\ud83c\udfc6 Most Quests",
                                f"{stats['completed_quests_count']['max']:,}",
                                "Single player"
                            )
                    
                    if 'completed_research_count' in stats:
                        col4, col5, col6 = st.columns(3)
                        
                        with col4:
                            st.metric(
                                "\ud83d\udd2c Completed Research",
                                f"{stats['completed_research_count']['total']:,}",
                                f"{stats['completed_research_count']['average']:.1f} avg"
                            )
                        
                        with col5:
                            research_rate = (stats['completed_research_count']['players_with_progress'] / total_players * 100) if total_players > 0 else 0
                            st.metric(
                                "\ud83d\udc65 Players with Research",
                                f"{stats['completed_research_count']['players_with_progress']:,}",
                                f"{research_rate:.1f}%"
                            )
                        
                        with col6:
                            st.metric(
                                "\ud83d\udd2c Most Research",
                                f"{stats['completed_research_count']['max']:,}",
                                "Single player"
                            )
                    
                    if 'in_progress_quests_count' in stats:
                        col7, col8 = st.columns(2)
                        
                        with col7:
                            st.metric(
                                "\u23f3 In Progress Quests",
                                f"{stats['in_progress_quests_count']['total']:,}",
                                f"{stats['in_progress_quests_count']['average']:.1f} avg"
                            )
                        
                        with col8:
                            progress_rate = (stats['in_progress_quests_count']['players_with_progress'] / total_players * 100) if total_players > 0 else 0
                            st.metric(
                                "\ud83d\udc65 Active Questers",
                                f"{stats['in_progress_quests_count']['players_with_progress']:,}",
                                f"{progress_rate:.1f}%"
                            )
                    
                    # Distribution charts
                    st.markdown("#### \ud83d\udcc8 Quest & Research Distributions")
                    
                    # Create distribution charts
                    chart_cols = st.columns(len(available_columns))
                    
                    for i, col in enumerate(available_columns):
                        with chart_cols[i]:
                            # Create histogram for this metric
                            fig = px.histogram(
                                player_df,
                                x=col,
                                title=col.replace('_', ' ').title(),
                                nbins=20,
                                color_discrete_sequence=['lightblue']
                            )
                            fig.update_layout(height=300)
                            st.plotly_chart(fig, use_container_width=True)
                
                # Player progress analysis
                    st.markdown("#### \ud83d\udc65 Player Progress Analysis")
                    
                    # Create combined progress dataframe
                    progress_data = []
                    for _, player in player_df.iterrows():
                        row_data = {
                            'Account ID': player['account_id'][:8] + "..." if len(player['account_id']) > 8 else player['account_id'],
                            'Alliance': player.get('alliance_name', 'None'),
                            'Power': player.get('power', 0)
                        }
                        
                        for col in available_columns:
                            row_data[col.replace('_count', '').title()] = player.get(col, 0)
                        
                        progress_data.append(row_data)
                    
                    progress_df = pd.DataFrame(progress_data)
                    
                    if not progress_df.empty:
                        # Sort by total progress
                        if 'completed_quests_count' in available_columns and 'completed_research_count' in available_columns:
                            progress_df['Total Progress'] = progress_df['Completed Quests'] + progress_df['Completed Research']
                            progress_df = progress_df.sort_values('Total Progress', ascending=False)
                        
                        # Display top players
                        st.dataframe(progress_df.head(20), use_container_width=True)
                    
                    # Detailed quest analysis (if quest details are available)
                    if 'quest_details' in player_df.columns:
                        st.markdown("#### \ud83d\udd0d Detailed Quest Analysis")
                        
                        # Process quest details
                        all_quests = []
                        quest_status_counts = {}
                        
                        for _, player in player_df.iterrows():
                            quest_details = player.get('quest_details')
                            if pd.notna(quest_details) and quest_details:
                                try:
                                    # Parse quest details (assuming format: quest_name:status:progress)
                                    if isinstance(quest_details, str):
                                        quests = quest_details.split('|')
                                        for quest in quests:
                                            if ':' in quest:
                                                parts = quest.split(':')
                                                if len(parts) >= 2:
                                                    quest_name = parts[0].strip()
                                                    status = parts[1].strip()
                                                    
                                                    all_quests.append({
                                                        'Account ID': player['account_id'][:8] + "...",
                                                        'Quest': quest_name,
                                                        'Status': status,
                                                        'Alliance': player.get('alliance_name', 'None')
                                                    })
                                                    
                                                    # Count quest statuses
                                                    if quest_name not in quest_status_counts:
                                                        quest_status_counts[quest_name] = {'completed': 0, 'in_progress': 0}
                                                    quest_status_counts[quest_name][status] = quest_status_counts[quest_name].get(status, 0) + 1
                                except:
                                    continue
                            
                        if all_quests:
                            quests_df = pd.DataFrame(all_quests)
                            
                            # Quest status distribution
                            st.markdown("##### \ud83d\udccb Quest Status Overview")
                            
                            # Create quest completion summary
                            quest_summary = []
                            for quest_name, status_counts in quest_status_counts.items():
                                total = sum(status_counts.values())
                                completed = status_counts.get('completed', 0)
                                completion_rate = (completed / total * 100) if total > 0 else 0
                                
                                quest_summary.append({
                                    'Quest': quest_name,
                                    'Total Players': total,
                                    'Completed': completed,
                                    'In Progress': status_counts.get('in_progress', 0),
                                    'Completion Rate': f"{completion_rate:.1f}%"
                                })
                            
                            if quest_summary:
                                summary_df = pd.DataFrame(quest_summary)
                                summary_df = summary_df.sort_values('Completion Rate', ascending=False)
                                st.dataframe(summary_df, use_container_width=True)
                            
                            # Individual quest analysis
                            selected_quest = st.selectbox(
                                "Select a quest for detailed analysis:",
                            options=list(quest_status_counts.keys()),
                                index=0
                            )
                            
                            if selected_quest:
                                quest_players = quests_df[quests_df['Quest'] == selected_quest]
                                
                                st.markdown(f"##### \ud83d\udc65 Players - {selected_quest}")
                                st.dataframe(quest_players, use_container_width=True)
                                
                                # Status distribution for this quest
                                status_counts = quest_status_counts[selected_quest]
                                fig_quest = px.pie(
                                    values=list(status_counts.values()),
                                    names=list(status_counts.keys()),
                                    title=f"{selected_quest} Status Distribution"
                                )
                                st.plotly_chart(fig_quest, use_container_width=True)
                        else:
                            st.info("No detailed quest information available")
                    
                    # Research analysis (if research details are available)
                    if 'research_details' in player_df.columns:
                        st.markdown("#### \ud83d\udd2c Detailed Research Analysis")
                        
                        # Similar processing for research details
                        all_research = []
                        research_status_counts = {}
                        
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
                                                    research_name = parts[0].strip()
                                                    status = parts[1].strip()
                                                    
                                                    all_research.append({
                                                        'Account ID': player['account_id'][:8] + "...",
                                                        'Research': research_name,
                                                        'Status': status,
                                                        'Alliance': player.get('alliance_name', 'None')
                                                    })
                                                    
                                                    if research_name not in research_status_counts:
                                                        research_status_counts[research_name] = {'completed': 0, 'in_progress': 0}
                                                    research_status_counts[research_name][status] = research_status_counts[research_name].get(status, 0) + 1
                                except:
                                    continue
                            
                        if all_research:
                            research_df = pd.DataFrame(all_research)
                            
                            # Research completion summary
                            research_summary = []
                            for research_name, status_counts in research_status_counts.items():
                                total = sum(status_counts.values())
                                completed = status_counts.get('completed', 0)
                                completion_rate = (completed / total * 100) if total > 0 else 0
                                
                                research_summary.append({
                                    'Research': research_name,
                                    'Total Players': total,
                                    'Completed': completed,
                                    'In Progress': status_counts.get('in_progress', 0),
                                    'Completion Rate': f"{completion_rate:.1f}%"
                                })
                            
                            if research_summary:
                                summary_df = pd.DataFrame(research_summary)
                                summary_df = summary_df.sort_values('Completion Rate', ascending=False)
                                st.dataframe(summary_df, use_container_width=True)
                        else:
                            st.info("No detailed research information available")
                    
                    # Progress correlation with power
                    if 'power' in player_df.columns and ('completed_quests_count' in available_columns or 'completed_research_count' in available_columns):
                        st.markdown("#### \ud83d\udcc8 Progress vs Power Correlation")
                        
                        # Create scatter plots
                        if 'completed_quests_count' in available_columns:
                            fig_quests_power = px.scatter(
                                player_df,
                                x='completed_quests_count',
                                y='power',
                                title='Completed Quests vs Power',
                                color='alliance_name' if 'alliance_name' in player_df.columns else None,
                                hover_data=['account_id']
                            )
                            fig_quests_power.update_layout(height=400)
                            st.plotly_chart(fig_quests_power, use_container_width=True)
                        
                        if 'completed_research_count' in available_columns:
                            fig_research_power = px.scatter(
                                player_df,
                                x='completed_research_count',
                                y='power',
                                title='Completed Research vs Power',
                                color='alliance_name' if 'alliance_name' in player_df.columns else None,
                                hover_data=['account_id']
                            )
                            fig_research_power.update_layout(height=400)
                            st.plotly_chart(fig_research_power, use_container_width=True)
                    else:
                        st.info("\u26a0\ufe0f No quests or research data available. This feature requires the comprehensive CSV format with quest and research information.")
            
        else:
            st.info("\u26a0\ufe0f No detailed player data available. This feature requires the comprehensive CSV format.")
    
    else:
        st.info("No data available for quests and research analysis")
