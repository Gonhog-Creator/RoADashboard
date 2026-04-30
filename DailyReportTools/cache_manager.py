import streamlit as st
import pandas as pd
import json
from datetime import datetime

class CacheManager:
    """Centralized cache manager for pre-calculating and caching dashboard data"""
    
    def __init__(self):
        self.cache_key = "dashboard_cache_v1"
    
    def initialize_cache(self, filtered_df):
        """Initialize or update cache with current data"""
        # Check if cache exists and is valid
        if self.is_cache_valid(filtered_df):
            return st.session_state[self.cache_key]
        
        # Create new cache
        cache = {
            'cache_date': datetime.now().isoformat(),
            'data_signature': self._generate_data_signature(filtered_df),
            'alliance_stats': self._calculate_alliance_stats(filtered_df),
            'building_stats': self._calculate_building_stats(filtered_df),
            'troops_stats': self._calculate_troops_stats(filtered_df),
            'skin_stats': self._calculate_skin_stats(filtered_df),
            'resource_data': self._calculate_resource_data(filtered_df),
            'player_lookup': self._build_player_lookup(filtered_df),
        }
        
        st.session_state[self.cache_key] = cache
        return cache
    
    def is_cache_valid(self, filtered_df):
        """Check if existing cache is still valid"""
        if self.cache_key not in st.session_state:
            return False
        
        cache = st.session_state[self.cache_key]
        current_signature = self._generate_data_signature(filtered_df)
        
        return cache['data_signature'] == current_signature
    
    def _generate_data_signature(self, filtered_df):
        """Generate unique signature for current data"""
        if filtered_df.empty:
            return "empty"
        
        # Use date and row count as signature
        latest_date = filtered_df['date'].max() if 'date' in filtered_df.columns else 'unknown'
        row_count = len(filtered_df)
        
        return f"{latest_date}_{row_count}"
    
    def _calculate_alliance_stats(self, filtered_df):
        """Pre-calculate alliance statistics"""
        alliance_stats = {}
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return alliance_stats
        
        player_df = latest_data['raw_player_data']
        
        if 'alliance_name' not in player_df.columns:
            return alliance_stats
        
        # Calculate stats for each alliance
        for alliance_name in player_df['alliance_name'].unique():
            if pd.isna(alliance_name):
                continue
                
            alliance_players = player_df[player_df['alliance_name'] == alliance_name]
            
            total_members = len(alliance_players)
            total_power = alliance_players['power'].fillna(0).sum()
            
            # Calculate troops
            total_troops = 0
            if 'troops_json' in alliance_players.columns:
                for _, player in alliance_players.iterrows():
                    if pd.notna(player['troops_json']):
                        try:
                            troops_dict = json.loads(player['troops_json'])
                            for troop_name, count in troops_dict.items():
                                if isinstance(count, str):
                                    continue
                                if hasattr(count, 'item'):
                                    numeric_count = count.item()
                                else:
                                    numeric_count = count
                                if isinstance(numeric_count, (int, float)) and not pd.isna(numeric_count):
                                    total_troops += numeric_count
                        except:
                            continue
            elif 'troops' in alliance_players.columns:
                total_troops = alliance_players['troops'].fillna(0).sum()
            
            # Calculate resources
            resource_columns = ['resource_gold', 'resource_lumber', 'resource_stone', 'resource_metal', 'resource_food']
            total_resources = {}
            for col in resource_columns:
                if col in alliance_players.columns:
                    total_resources[col] = alliance_players[col].fillna(0).sum()
            
            alliance_stats[alliance_name] = {
                'total_members': total_members,
                'total_power': total_power,
                'total_troops': total_troops,
                'total_resources': total_resources,
                'player_ids': alliance_players['account_id'].tolist()
            }
        
        return alliance_stats
    
    def _calculate_building_stats(self, filtered_df):
        """Pre-calculate building statistics"""
        building_stats = {}
        
        # Find latest data with buildings information
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return building_stats
        
        player_df = latest_data['raw_player_data']
        
        if 'buildings_metadata' not in player_df.columns:
            return building_stats
        
        # Parse building metadata
        for _, player in player_df.iterrows():
            buildings_metadata = player.get('buildings_metadata')
            if pd.notna(buildings_metadata) and buildings_metadata:
                # Handle both dict format and string format
                if isinstance(buildings_metadata, str):
                    # Handle format: "CityName(level)[type](x,y):[building1:1,building2:2]"
                    # Or "CityName(level)[type]:[building1:1,building2:2]"
                    # Or "CityName(level)type:[building1:1,building2:2]"
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
                            
                            # Extract settlement type from format "Name(level)type" or "Name(level)[type]" or "Name(level)[type](x,y)"
                            if '[' in settlement_info:
                                bracket_content = settlement_info.split('[')[1].rstrip(']')
                                # Check if there are coordinates after the type
                                if '(' in bracket_content:
                                    # Format: "type(x,y)" - extract type before coordinates
                                    settlement_type = bracket_content.split('(')[0]
                                else:
                                    # Format: "type"
                                    settlement_type = bracket_content
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
                                        if building_name not in building_stats:
                                            building_stats[building_name] = {'players': set(), 'levels': [], 'total_instances': 0}
                                        building_stats[building_name]['players'].add(player['account_id'])  # Track unique player
                                        building_stats[building_name]['total_instances'] += 1  # Count all instances
                                        building_stats[building_name]['levels'].append(level)  # Keep levels for distribution
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
                                    if building_name not in building_stats:
                                        building_stats[building_name] = {'players': set(), 'levels': [], 'total_instances': 0}
                                    building_stats[building_name]['players'].add(player['account_id'])
                                    building_stats[building_name]['total_instances'] += 1
                                    building_stats[building_name]['levels'].append(level)
        
        return building_stats
    
    def _calculate_troops_stats(self, filtered_df):
        """Pre-calculate troops statistics"""
        troops_stats = {}
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return troops_stats
        
        player_df = latest_data['raw_player_data']
        troops_stats = {}
        
        if 'troops_json' in player_df.columns:
            for _, player_row in player_df.iterrows():
                try:
                    troops_json_str = player_row['troops_json']
                    if pd.notna(troops_json_str) and troops_json_str:
                        troops_dict = json.loads(troops_json_str)
                        for troop_name, count in troops_dict.items():
                            troops_stats[troop_name] = troops_stats.get(troop_name, 0) + count
                except:
                    continue
        
        return troops_stats
    
    def _calculate_skin_stats(self, filtered_df):
        """Pre-calculate skin statistics"""
        skin_stats = {}
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return skin_stats
        
        player_df = latest_data['raw_player_data']
        
        if 'equipped_skins' not in player_df.columns:
            return skin_stats
        
        # Parse skins data
        for _, player in player_df.iterrows():
            equipped_skins = player.get('equipped_skins')
            if pd.notna(equipped_skins) and equipped_skins:
                try:
                    if isinstance(equipped_skins, str):
                        combined_entries = equipped_skins.split('|')
                        skins_list = []
                        
                        for entry in combined_entries:
                            entry = entry.strip()
                            if entry.startswith('{') or entry.startswith('['):
                                try:
                                    parsed = json.loads(entry)
                                    if isinstance(parsed, dict):
                                        skins_list.extend(list(parsed.keys()))
                                    else:
                                        skins_list.extend(parsed)
                                except:
                                    skins_list.append(entry)
                            else:
                                if ',' in entry:
                                    skins_list.extend([skin.strip() for skin in entry.split(',')])
                                else:
                                    skins_list.append(entry)
                        
                        for skin in skins_list:
                            if skin and skin.strip():
                                skin_name = skin.strip()
                                skin_stats[skin_name] = skin_stats.get(skin_name, 0) + 1
                except:
                    continue
        
        return skin_stats
    
    def _calculate_resource_data(self, filtered_df):
        """Pre-calculate resource data for ceasefire tab - only unprotected resources"""
        resource_data = {}
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return resource_data
        
        player_df = latest_data['raw_player_data']
        
        # Calculate has_protection column for ceasefire detection
        if 'active_effects' in player_df.columns:
            attack_prevention_effects = ['prevent_attacks:1']
            player_df['has_protection'] = player_df['active_effects'].fillna('').astype(str).apply(
                lambda x: any(effect in x for effect in attack_prevention_effects)
            )
        else:
            player_df['has_protection'] = False
        
        # Resource mapping
        resource_mapping = {
            'Gold': 'resource_gold',
            'Lumber': 'resource_lumber',
            'Stone': 'resource_stone',
            'Metal': 'resource_metal',
            'Food': 'resource_food'
        }
        
        # Calculate vault protected resources
        # Protection values from buildings_updated.yaml
        vault_protection_levels = {
            1: {'food': 5000000, 'lumber': 5000000, 'stone': 5000000, 'metal': 5000000, 'gold': 2000000},
            2: {'food': 11000000, 'lumber': 11000000, 'stone': 11000000, 'metal': 11000000, 'gold': 5000000},
            3: {'food': 17000000, 'lumber': 17000000, 'stone': 17000000, 'metal': 17000000, 'gold': 8000000},
            4: {'food': 23000000, 'lumber': 23000000, 'stone': 23000000, 'metal': 23000000, 'gold': 11000000},
            5: {'food': 29000000, 'lumber': 29000000, 'stone': 29000000, 'metal': 29000000, 'gold': 14000000},
            6: {'food': 35000000, 'lumber': 35000000, 'stone': 35000000, 'metal': 35000000, 'gold': 17000000},
            7: {'food': 41000000, 'lumber': 41000000, 'stone': 41000000, 'metal': 41000000, 'gold': 20000000},
            8: {'food': 47000000, 'lumber': 47000000, 'stone': 47000000, 'metal': 47000000, 'gold': 23000000},
            9: {'food': 53000000, 'lumber': 53000000, 'stone': 53000000, 'metal': 53000000, 'gold': 26000000},
            10: {'food': 59000000, 'lumber': 59000000, 'stone': 59000000, 'metal': 59000000, 'gold': 29000000}
        }
        
        vault_protected_resources = {}
        for resource in ['gold', 'lumber', 'stone', 'metal', 'food']:
            resource_col = f'resource_{resource}'
            if resource_col in player_df.columns:
                vault_protected = 0
                for _, player in player_df.iterrows():
                    if 'storage_vault_level' in player and pd.notna(player['storage_vault_level']):
                        vault_level = player['storage_vault_level']
                        if vault_level > 0 and vault_level in vault_protection_levels:
                            # Use fixed protection amount based on vault level
                            vault_protected += vault_protection_levels[vault_level][resource]
                vault_protected_resources[resource] = vault_protected
        
        # Calculate total protected (ceasefire)
        total_protected = 0
        if 'has_protection' in player_df.columns:
            total_protected = player_df['has_protection'].sum()
        
        total_protected_adjusted = 0
        if total_protected > 0:
            # Adjust for actual protection coverage
            for resource in ['gold', 'lumber', 'stone', 'metal', 'food']:
                resource_col = f'resource_{resource}'
                if resource_col in player_df.columns:
                    total_protected_adjusted += player_df[resource_col].fillna(0).sum()
        
        # Pre-calculate player data for all resources (only unprotected)
        for resource_name, resource_col in resource_mapping.items():
            resource_key = resource_name.lower()
            if resource_col in player_df.columns:
                total_resource = player_df[resource_col].fillna(0).sum()
                protected_resource = vault_protected_resources.get(resource_key, 0)
                
                # Calculate protected from ceasefire
                if total_protected > 0:
                    protected_from_ceasefire = (total_protected_adjusted / total_protected) * (total_resource - protected_resource) if total_resource > 0 else 0
                else:
                    protected_from_ceasefire = 0
                
                total_protected_for_resource = protected_resource + protected_from_ceasefire
                unprotected_amount = max(0, total_resource - total_protected_for_resource)
                
                data_list = []
                for _, player in player_df[player_df[resource_col].fillna(0) > 0].iterrows():
                    player_amount = player[resource_col]
                    if pd.isna(player_amount):
                        player_amount = 0
                    
                    # Calculate player's unprotected amount
                    player_protected = 0
                    if 'storage_vault_level' in player and pd.notna(player['storage_vault_level']):
                        vault_level = player['storage_vault_level']
                        if vault_level > 0:
                            player_protected = player_amount * 0.1 * vault_level
                    
                    if player.get('has_protection', False):
                        player_protected += player_amount * 0.5  # Assume 50% protected by ceasefire
                    
                    player_unprotected = max(0, player_amount - player_protected)
                    
                    # Get defended status
                    defended = False
                    if 'defending_troops' in player and pd.notna(player['defending_troops']) and player['defending_troops'] > 0:
                        defended = True
                    elif 'troops' in player and pd.notna(player['troops']) and player['troops'] > 0:
                        defended = True
                    
                    # Get ceasefire protected status
                    ceasefire_protected = player.get('has_protection', False)
                    
                    # Only include if player has unprotected resources AND is not ceasefire protected
                    if player_unprotected > 0 and not ceasefire_protected:
                        username = player.get('username', 'Unknown')
                        
                        data_list.append({
                            'Player Name': username,
                            f'{resource_name} Amount': int(player_unprotected),
                            'Defended': defended
                        })
                
                # Sort by resource amount descending
                data_list.sort(key=lambda x: x[f'{resource_name} Amount'], reverse=True)
                resource_data[resource_name] = data_list
        
        return resource_data
    
    def _build_player_lookup(self, filtered_df):
        """Build player lookup for fast queries"""
        player_lookup = {}
        
        # Find latest data with comprehensive CSV
        latest_data = None
        for i in range(len(filtered_df) - 1, -1, -1):
            data = filtered_df.iloc[i]
            if 'raw_player_data' in data and data['raw_player_data'] is not None:
                latest_data = data
                break
        
        if latest_data is None:
            return player_lookup
        
        player_df = latest_data['raw_player_data']
        
        if 'account_id' not in player_df.columns:
            return player_lookup
        
        # Build lookup dictionary
        for _, player in player_df.iterrows():
            account_id = player['account_id']
            # Convert to dict and fill NaN values with 0
            player_dict = player.to_dict()
            for key, value in player_dict.items():
                if pd.isna(value):
                    player_dict[key] = 0
            player_lookup[account_id] = player_dict
        
        return player_lookup
    
    def get_alliance_stats(self, alliance_name):
        """Get cached alliance statistics"""
        if self.cache_key not in st.session_state:
            return None
        
        cache = st.session_state[self.cache_key]
        return cache['alliance_stats'].get(alliance_name)
    
    def get_all_alliance_stats(self):
        """Get all cached alliance statistics"""
        if self.cache_key not in st.session_state:
            return {}
        
        cache = st.session_state[self.cache_key]
        return cache['alliance_stats']
    
    def get_all_alliance_names(self):
        """Get all alliance names from cache"""
        if self.cache_key not in st.session_state:
            return []
        
        cache = st.session_state[self.cache_key]
        return list(cache['alliance_stats'].keys())
    
    def get_building_stats(self):
        """Get cached building statistics"""
        if self.cache_key not in st.session_state:
            return {}
        
        cache = st.session_state[self.cache_key]
        return cache['building_stats']
    
    def get_troops_stats(self):
        """Get cached troops statistics"""
        if self.cache_key not in st.session_state:
            return {}
        
        cache = st.session_state[self.cache_key]
        return cache['troops_stats']
    
    def get_skin_stats(self):
        """Get cached skin statistics"""
        if self.cache_key not in st.session_state:
            return {}
        
        cache = st.session_state[self.cache_key]
        return cache['skin_stats']
    
    def get_resource_data(self):
        """Get cached resource data for ceasefire tab"""
        if self.cache_key not in st.session_state:
            return {}
        
        cache = st.session_state[self.cache_key]
        return cache.get('resource_data', {})
    
    def get_player_data(self, account_id):
        """Get cached player data"""
        if self.cache_key not in st.session_state:
            return None
        
        cache = st.session_state[self.cache_key]
        return cache['player_lookup'].get(account_id)
    
    def get_player_data_by_name(self, username):
        """Get cached player data by username"""
        if self.cache_key not in st.session_state:
            return None
        
        cache = st.session_state[self.cache_key]
        for account_id, player_data in cache['player_lookup'].items():
            if player_data.get('username') == username:
                return player_data
        return None
    
    def get_player_historical_data_by_name(self, username, filtered_df):
        """Get all historical data for a specific player by re-parsing CSV files without limits"""
        try:
            from data_loader import load_all_csv_files_without_limits
            import pandas as pd
            
            # Load all CSV files without ANY limits
            all_data_df, _ = load_all_csv_files_without_limits()
            
            if all_data_df.empty:
                return None
            
            # Sort by date
            all_data_df = all_data_df.sort_values('date')
            
            # Collect all historical data for the player
            player_historical_data = []
            
            for _, data_point in all_data_df.iterrows():
                if 'raw_player_data' in data_point and data_point['raw_player_data'] is not None:
                    player_df = data_point['raw_player_data']
                    
                    if isinstance(player_df, pd.DataFrame) and not player_df.empty:
                        # Find the player in this data point
                        player_row = player_df[player_df['username'] == username]
                        
                        if not player_row.empty:
                            player_data = player_row.iloc[0].to_dict()
                            
                            # Handle NaN values
                            for key, value in player_data.items():
                                if pd.isna(value):
                                    player_data[key] = 0
                            
                            # Add date information
                            player_data['data_date'] = data_point['date']
                            player_data['filename'] = data_point.get('filename', 'unknown')
                            
                            player_historical_data.append(player_data)
            
            if not player_historical_data:
                return None
            
            # Return the most recent data point (for compatibility with existing display)
            # but also include historical data count for reference
            latest_data = max(player_historical_data, key=lambda x: x['data_date'])
            latest_data['historical_data_points'] = len(player_historical_data)
            latest_data['all_historical_data'] = player_historical_data
            
            return latest_data
            
        except Exception as e:
            st.error(f"Error loading historical data for {username}: {e}")
            return None
    
    def invalidate_cache(self):
        """Invalidate the cache"""
        if self.cache_key in st.session_state:
            del st.session_state[self.cache_key]


# Global cache manager instance
cache_manager = CacheManager()
