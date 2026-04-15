"""Daily Report Tab - Shows daily changes in attacks, resources, troops, etc."""
import streamlit as st
import pandas as pd
import json
from datetime import datetime

def format_number(num):
    """Format numbers with abbreviations"""
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return f"{int(num):,}"

def format_comma(num):
    """Format numbers with commas for readability"""
    return f"{int(num):,}" if pd.notna(num) and num != 0 else '0'

def create_daily_report_tab(filtered_df):
    """Create the Daily Report tab with daily change analysis"""
    
    if not filtered_df.empty:
        # Look for reports with raw_player_data (comprehensive CSV format)
        comprehensive_data_list = []
        for i in range(len(filtered_df)):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                comprehensive_data_list.append(data)
        
        if len(comprehensive_data_list) < 2:
            st.warning("Need at least 2 comprehensive CSV reports to calculate daily changes.")
            return
        
        # Sort by date (most recent first)
        comprehensive_data_list = sorted(comprehensive_data_list, key=lambda x: x['date'], reverse=True)
        
        # Get current and previous reports
        current_data = comprehensive_data_list[0]
        previous_data = comprehensive_data_list[1]
        
        current_df = current_data['raw_player_data']
        previous_df = previous_data['raw_player_data']
        
        # Calculate time difference
        time_diff = (current_data['date'] - previous_data['date']).total_seconds() / (24 * 3600)
        time_diff_str = f"{time_diff:.1f} days" if time_diff >= 1 else f"{time_diff*24:.1f} hours"
        
        # Compact header with time comparison
        st.markdown(f"**📊 Daily Report** • {current_data['date'].strftime('%Y-%m-%d %H:%M')} vs {previous_data['date'].strftime('%Y-%m-%d %H:%M')} ({time_diff_str})")
        
        # Compact metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_autowaver = (current_df['auto_waver_activated'] == 't').sum() if 'auto_waver_activated' in current_df.columns else 0
            previous_autowaver = (previous_df['auto_waver_activated'] == 't').sum() if 'auto_waver_activated' in previous_df.columns else 0
            autowaver_change = current_autowaver - previous_autowaver
            st.metric("Autowaver", format_comma(current_autowaver), delta=f"{autowaver_change:+,}")
        
        with col2:
            total_players = len(current_df)
            st.metric("Players", format_comma(total_players))
        
        with col3:
            merged_df = pd.merge(
                current_df[['username', 'power', 'total_troops']],
                previous_df[['username', 'power', 'total_troops']],
                on='username',
                suffixes=('_current', '_previous'),
                how='outer'
            )
            merged_df['power_change'] = merged_df['power_current'] - merged_df['power_previous']
            merged_df['troop_change'] = merged_df['total_troops_current'] - merged_df['total_troops_previous']
            active_players = merged_df[
                (merged_df['power_change'] != 0) | 
                (merged_df['troop_change'] != 0) |
                (merged_df['power_current'].notna() & merged_df['power_previous'].isna())
            ]
            active_count = len(active_players)
            active_percentage = (active_count / total_players * 100) if total_players > 0 else 0
            st.metric("Active", f"{format_comma(active_count)} ({active_percentage:.1f}%)")
        
        with col4:
            st.metric("Inactive", format_comma(total_players - active_count))
        
        st.markdown("---")
        
        # Resource changes in compact table
        st.markdown("**💰 Resource Changes**")
        resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food']
        resource_names = ['Gold', 'Lumber', 'Stone', 'Metal', 'Food']
        
        resource_changes = []
        for col, name in zip(resource_columns, resource_names):
            if col in current_df.columns and col in previous_df.columns:
                current_total = current_df[col].fillna(0).sum()
                previous_total = previous_df[col].fillna(0).sum()
                change = current_total - previous_total
                resource_changes.append({
                    'Resource': name,
                    'Current': format_comma(current_total),
                    'Change': change
                })
        
        resource_change_df = pd.DataFrame(resource_changes)
        if not resource_change_df.empty:
            resource_change_df = resource_change_df.sort_values('Change', ascending=False)
            resource_change_df['Change'] = resource_change_df['Change'].apply(lambda x: f"+{format_comma(x)}" if x > 0 else format_comma(x))
            st.dataframe(resource_change_df, width='stretch', hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Troop changes in compact table
        st.markdown("**⚔️ Troop Changes**")
        
        current_troops = {}
        previous_troops = {}
        
        if 'troops_json' in current_df.columns:
            for _, row in current_df.iterrows():
                try:
                    troops_json_str = row['troops_json']
                    if pd.notna(troops_json_str) and troops_json_str:
                        troops_dict = json.loads(troops_json_str)
                        for troop_name, count in troops_dict.items():
                            if not troop_name.startswith('resource_'):
                                current_troops[troop_name] = current_troops.get(troop_name, 0) + count
                except:
                    continue
        
        if 'troops_json' in previous_df.columns:
            for _, row in previous_df.iterrows():
                try:
                    troops_json_str = row['troops_json']
                    if pd.notna(troops_json_str) and troops_json_str:
                        troops_dict = json.loads(troops_json_str)
                        for troop_name, count in troops_dict.items():
                            if not troop_name.startswith('resource_'):
                                previous_troops[troop_name] = previous_troops.get(troop_name, 0) + count
                except:
                    continue
        
        troop_changes = []
        total_troops_trained = 0
        all_troop_types = set(current_troops.keys()) | set(previous_troops.keys())
        
        # Normalize troop names
        def normalize_troop_name(name):
            # Convert underscores to spaces and capitalize
            return name.replace('_', ' ').title()
        
        for troop_type in sorted(all_troop_types):
            current_amount = current_troops.get(troop_type, 0)
            previous_amount = previous_troops.get(troop_type, 0)
            change = current_amount - previous_amount
            if change != 0:
                total_troops_trained += abs(change)
                troop_changes.append({
                    'Troop Type': normalize_troop_name(troop_type),
                    'Current': format_comma(current_amount),
                    'Change': change
                })
        
        st.metric("Total Trained", format_comma(total_troops_trained))
        
        if troop_changes:
            troop_change_df = pd.DataFrame(troop_changes)
            troop_change_df = troop_change_df.sort_values('Change', ascending=False)
            troop_change_df['Change'] = troop_change_df['Change'].apply(lambda x: f"+{format_comma(x)}" if x > 0 else format_comma(x))
            st.dataframe(troop_change_df, width='stretch', hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Attack Analysis from comprehensive CSV data
        st.markdown("**⚔️ Attack Analysis**")
        
        # Check if battle statistics columns exist (added after player_data_analyzer update)
        if 'total_attacks' in current_df.columns:
            # Calculate attack statistics from current and previous comprehensive data
            current_total_attacks = current_df['total_attacks'].fillna(0).sum()
            previous_total_attacks = previous_df['total_attacks'].fillna(0).sum()
            attack_change = current_total_attacks - previous_total_attacks
            
            current_autowaver = current_df['autowaver_attacks'].fillna(0).sum()
            previous_autowaver = previous_df['autowaver_attacks'].fillna(0).sum()
            autowaver_change = current_autowaver - previous_autowaver
            
            current_manual = current_df['manual_attacks'].fillna(0).sum()
            previous_manual = previous_df['manual_attacks'].fillna(0).sum()
            manual_change = current_manual - previous_manual
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Attacks", format_comma(current_total_attacks), delta=f"{attack_change:+,}")
            with col2:
                st.metric("Autowaver", format_comma(current_autowaver), delta=f"{autowaver_change:+,}")
            with col3:
                st.metric("Manual", format_comma(current_manual), delta=f"{manual_change:+,}")
            
            # Top attackers
            current_top_attackers = current_df[['username', 'total_attacks', 'autowaver_attacks', 'manual_attacks']].copy()
            current_top_attackers = current_top_attackers.sort_values('total_attacks', ascending=False).head(10)
            if not current_top_attackers.empty:
                current_top_attackers['total_attacks'] = current_top_attackers['total_attacks'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
                current_top_attackers['autowaver_attacks'] = current_top_attackers['autowaver_attacks'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
                current_top_attackers['manual_attacks'] = current_top_attackers['manual_attacks'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
                current_top_attackers.columns = ['Player', 'Total', 'Autowaver', 'Manual']
                st.dataframe(current_top_attackers, width='stretch', hide_index=True, use_container_width=True)
            
            # Target types aggregation
            target_types_current = defaultdict(int)
            for _, row in current_df.iterrows():
                try:
                    target_types = json.loads(row.get('target_types_json', '{}'))
                    for target, count in target_types.items():
                        target_types_current[target] += count
                except:
                    pass
            
            if target_types_current:
                target_df = pd.DataFrame([
                    {'Target': k, 'Attacks': format_comma(v)}
                    for k, v in sorted(target_types_current.items(), key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(target_df, width='stretch', hide_index=True, use_container_width=True)
        else:
            st.info("Battle statistics not available in current CSV files. Run sync tool to regenerate CSV files with battle data.")
        
        st.markdown("---")
        
        # Top power gainers and alliance growth in top row
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏆 Top Power Gainers**")
            merged_df_sorted = merged_df[merged_df['power_change'].notna()].sort_values('power_change', ascending=False)
            top_gainers = merged_df_sorted.head(5)[['username', 'power_previous', 'power_current', 'power_change']].copy()
            
            if not top_gainers.empty:
                top_gainers['power_previous'] = top_gainers['power_previous'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
                top_gainers['power_current'] = top_gainers['power_current'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
                top_gainers['power_change'] = top_gainers['power_change'].apply(lambda x: f"+{format_comma(x)}" if x > 0 else format_comma(x))
                top_gainers.columns = ['Player', 'Prev', 'Curr', 'Change']
                st.dataframe(top_gainers, width='stretch', hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("**🏰 Alliance Growth**")
            if 'alliance_name' in current_df.columns and 'alliance_name' in previous_df.columns:
                current_alliance_power = current_df.groupby('alliance_name')['power'].sum()
                previous_alliance_power = previous_df.groupby('alliance_name')['power'].sum()
                
                alliance_changes = []
                for alliance in current_alliance_power.index:
                    current_power = current_alliance_power[alliance]
                    previous_power = previous_alliance_power.get(alliance, 0)
                    change = current_power - previous_power
                    alliance_changes.append({
                        'Alliance': alliance,
                        'Current': current_power,
                        'Change': change
                    })
                
                alliance_change_df = pd.DataFrame(alliance_changes)
                alliance_change_df = alliance_change_df.sort_values('Change', ascending=False)
                if not alliance_change_df.empty:
                    alliance_change_df['Current'] = alliance_change_df['Current'].apply(lambda x: format_comma(x))
                    alliance_change_df['Change'] = alliance_change_df['Change'].apply(lambda x: f"+{format_comma(x)}" if x > 0 else format_comma(x))
                    st.dataframe(alliance_change_df, width='stretch', hide_index=True, use_container_width=True)
            else:
                st.info("Alliance data not available")
        
        st.markdown("---")
        
        # Top power losers
        st.markdown("**📉 Top Power Losers**")
        merged_df_sorted_losers = merged_df[merged_df['power_change'].notna()].sort_values('power_change', ascending=True)
        top_losers = merged_df_sorted_losers.head(5)[['username', 'power_previous', 'power_current', 'power_change']].copy()
        
        if not top_losers.empty:
            top_losers['power_previous'] = top_losers['power_previous'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
            top_losers['power_current'] = top_losers['power_current'].apply(lambda x: format_comma(x) if pd.notna(x) else '0')
            top_losers['power_change'] = top_losers['power_change'].apply(lambda x: format_comma(x))
            top_losers.columns = ['Player', 'Prev', 'Curr', 'Change']
            st.dataframe(top_losers, width='stretch', hide_index=True, use_container_width=True)
    
    else:
        st.info("No data available for daily report analysis.")
