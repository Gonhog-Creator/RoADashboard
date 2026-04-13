#!/usr/bin/env python3
"""
Player Data Analyzer (Simple Version)
Unpacks tar file and creates comprehensive CSV with player data including items, troops, and resources.
Uses only standard library modules.
"""

import tarfile
import csv
import os
import json
import shutil
from collections import defaultdict
from datetime import datetime

class PlayerDataAnalyzer:
    def __init__(self, database_path):
        self.database_path = database_path
        # Find all .tar.gz files in the directory
        self.tar_files = sorted([
            os.path.join(database_path, f) 
            for f in os.listdir(database_path) 
            if f.endswith('.tar.gz')
        ])
        
        if not self.tar_files:
            raise FileNotFoundError(f"No .tar.gz files found in {database_path}")
        
        print(f"Found {len(self.tar_files)} .tar.gz file(s) to process")
        
        self.extract_path = os.path.join(database_path, "extracted_data")
        self.item_types_file = os.path.join(database_path, "item_types_registry.json")
        self.troop_types_file = os.path.join(database_path, "troop_types_registry.json")
        
    def extract_tar_file(self, tar_file):
        """Extract the tar file to extract_path"""
        print(f"Extracting {tar_file}...")
        
        if os.path.exists(self.extract_path):
            import shutil
            shutil.rmtree(self.extract_path)
        
        os.makedirs(self.extract_path, exist_ok=True)
        
        with tarfile.open(tar_file, 'r:gz') as tar:
            tar.extractall(path=self.extract_path)
        
        print(f"Extracted to {self.extract_path}")
    
    def read_csv(self, filepath):
        """Read CSV file and return list of dictionaries"""
        data = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            print(f"Loaded {os.path.basename(filepath)}: {len(data)} rows")
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
        return data
    
    def load_csv_data(self):
        """Load all relevant CSV files"""
        data = {}
        
        # List of CSV files we need to process
        csv_files = [
            'player.csv',
            'item.csv', 
            'troop.csv',
            'resource.csv',
            'building.csv',
            'settlement.csv',
            'equipped_skin.csv',
            'unlocked_skin.csv',
            'research.csv',
            'quest.csv',
            'alliance_member.csv',
            'alliance.csv',
            'user.csv',
            'effect.csv'
        ]
        
        for csv_file in csv_files:
            file_path = os.path.join(self.extract_path, csv_file)
            if os.path.exists(file_path):
                data[csv_file.replace('.csv', '')] = self.read_csv(file_path)
            else:
                print(f"File not found: {file_path}")
                data[csv_file.replace('.csv', '')] = []
        
        return data
    
    def load_type_registry(self, registry_file):
        """Load item or troop type registry from JSON file"""
        if os.path.exists(registry_file):
            try:
                with open(registry_file, 'r') as f:
                    registry = json.load(f)
                print(f"Loaded type registry from {registry_file}: {len(registry)} types")
                return registry
            except Exception as e:
                print(f"Error loading registry {registry_file}: {e}")
        
        # Return empty registry if file doesn't exist or error occurs
        return {}
    
    def save_type_registry(self, registry, registry_file):
        """Save item or troop type registry to JSON file"""
        try:
            with open(registry_file, 'w') as f:
                json.dump(registry, f, indent=2)
            print(f"Saved type registry to {registry_file}: {len(registry)} types")
        except Exception as e:
            print(f"Error saving registry {registry_file}: {e}")
    
    def update_type_registry(self, registry, new_types):
        """Update registry with new types"""
        updated = False
        for item_type in new_types:
            if item_type and item_type not in registry:
                registry[item_type] = {
                    'first_seen': datetime.now().isoformat(),
                    'count': 1
                }
                updated = True
            elif item_type and item_type in registry:
                registry[item_type]['count'] += 1
        
        return registry, updated
    
    def cleanup_extracted_files(self):
        """Clean up extracted CSV files"""
        # Clean up the extracted_data subdirectory
        if os.path.exists(self.extract_path):
            try:
                shutil.rmtree(self.extract_path)
                print(f"Cleaned up extracted files from {self.extract_path}")
            except Exception as e:
                print(f"Error cleaning up extracted files: {e}")
        
        # Also clean up any CSV files that might have been extracted to the database path
        # (excluding the comprehensive output files and registry files)
        csv_files_to_remove = [
            'player.csv', 'item.csv', 'troop.csv', 'resource.csv', 'building.csv',
            'settlement.csv', 'equipped_skin.csv', 'unlocked_skin.csv', 'research.csv',
            'quest.csv', 'alliance_member.csv', 'alliance.csv', 'user.csv', 'effect.csv',
            'action.csv', 'battle.csv', 'chat_message.csv', 'challenge.csv',
            'doctrine_migration_versions.csv', 'notification.csv', 'power_history.csv',
            'reinforcement.csv', 'shop_item.csv', 'shop_item_purchase.csv',
            'store_purchase.csv', 'player_pity.csv', 'realm.csv'
        ]
        
        for csv_file in csv_files_to_remove:
            file_path = os.path.join(self.database_path, csv_file)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed {csv_file}")
                except Exception as e:
                    print(f"Error removing {csv_file}: {e}")
    
    def parse_metadata_premium(self, metadata_str):
        """Parse metadata to extract premium status"""
        try:
            if not metadata_str or metadata_str == '':
                return False
            
            # Parse JSON metadata
            metadata = json.loads(metadata_str.replace('""', '"'))
            return metadata.get('has_premium', False)
        except (json.JSONDecodeError, AttributeError):
            return False
    
    def group_by_field(self, data, field):
        """Group data by a specific field"""
        groups = defaultdict(list)
        for item in data:
            if field in item:
                groups[item[field]].append(item)
        return groups
    
    def process_player_data(self, data):
        """Process and consolidate all player data"""
        print("Processing player data...")
        
        if not data.get('player'):
            print("No player data found!")
            return [], [], []
        
        # Load existing registries
        item_registry = self.load_type_registry(self.item_types_file)
        troop_registry = self.load_type_registry(self.troop_types_file)
        
        # Collect all unique item and troop types
        all_item_types = set()
        all_troop_types = set()
        
        for item in data.get('item', []):
            item_type = item.get('definition_id', '')
            if item_type:
                all_item_types.add(item_type)
        
        for troop in data.get('troop', []):
            troop_type = troop.get('definition_id', '')
            if troop_type:
                all_troop_types.add(troop_type)
        
        # Update registries with new types
        item_registry, items_updated = self.update_type_registry(item_registry, all_item_types)
        troop_registry, troops_updated = self.update_type_registry(troop_registry, all_troop_types)
        
        # Save updated registries
        if items_updated:
            self.save_type_registry(item_registry, self.item_types_file)
        if troops_updated:
            self.save_type_registry(troop_registry, self.troop_types_file)
        
        # Create player lookup
        players = {player['uuid']: player for player in data['player']}
        print(f"Total players loaded from player.csv: {len(players)}")
        
        # Process items
        items_by_player = self.group_by_field(data.get('item', []), 'player_id')
        
        # Process troops
        troops_by_player = self.group_by_field(data.get('troop', []), 'player_id')
        
        # Process resources
        resources_by_player = self.group_by_field(data.get('resource', []), 'player_id')
        
        # Process buildings and settlements
        settlements_by_player = self.group_by_field(data.get('settlement', []), 'player_id')
        buildings_by_settlement = self.group_by_field(data.get('building', []), 'settlement_id')
        
        # Process skins
        equipped_skins_by_player = self.group_by_field(data.get('equipped_skin', []), 'player_id')
        unlocked_skins_by_player = self.group_by_field(data.get('unlocked_skin', []), 'player_id')
        
        # Process research and quests
        research_by_player = self.group_by_field(data.get('research', []), 'player_id')
        quests_by_player = self.group_by_field(data.get('quest', []), 'player_id')
        
        # Process user data
        users = {user['uuid']: user for user in data.get('user', [])}
        
        # Process alliance data
        alliance_members = self.group_by_field(data.get('alliance_member', []), 'player_id')
        alliances = {alliance['uuid']: alliance for alliance in data.get('alliance', [])}
        
        # Process effects
        effects_by_player = self.group_by_field(data.get('effect', []), 'player_id')
        
        # Combine all data for each player
        comprehensive_data = []
        processed_count = 0
        
        for player_id, player in players.items():
            processed_count += 1
            # Start with base player data
            player_data = player.copy()
            
            # Add premium status from metadata
            metadata = player.get('metadata', '')
            player_data['has_premium'] = self.parse_metadata_premium(metadata)
            
            # Add user data if available
            account_id = player.get('account_id')
            if account_id and account_id in users:
                user = users[account_id]
                player_data['user_email'] = user.get('email', '')
                player_data['user_created_at'] = user.get('created_at', '')
            else:
                player_data['user_email'] = ''
                player_data['user_created_at'] = ''
            
            # Process items using registry
            items = items_by_player.get(player_id, [])
            total_items = len(items)
            total_item_count = sum(int(item.get('count', 0)) for item in items)
            unique_item_types = list(set(item.get('definition_id', '') for item in items))
            
            player_data['total_items'] = total_items
            player_data['total_item_count'] = total_item_count
            player_data['unique_item_types'] = '|'.join(unique_item_types)
            
            # Count items by type and store as JSON
            item_counts = defaultdict(int)
            for item in items:
                item_type = item.get('definition_id', '')
                count = int(item.get('count', 0))
                item_counts[item_type] += count
            
            # Store items as JSON string instead of individual columns
            player_data['items_json'] = json.dumps(dict(item_counts))
            
            # Process troops using registry
            troops = troops_by_player.get(player_id, [])
            total_troops = len(troops)
            total_troop_amount = sum(int(troop.get('amount', 0)) for troop in troops)
            unique_troop_types = list(set(troop.get('definition_id', '') for troop in troops))
            
            player_data['total_troops'] = total_troops
            player_data['total_troop_amount'] = total_troop_amount
            player_data['unique_troop_types'] = '|'.join(unique_troop_types)
            
            # Count troops by type and store as JSON
            troop_counts = defaultdict(int)
            for troop in troops:
                troop_type = troop.get('definition_id', '')
                amount = int(troop.get('amount', 0))
                troop_counts[troop_type] += amount
            
            # Store troops as JSON string instead of individual columns
            player_data['troops_json'] = json.dumps(dict(troop_counts))
            
            # Process resources
            resources = resources_by_player.get(player_id, [])
            total_resources = sum(int(resource.get('amount', 0)) for resource in resources)
            resource_types = list(set(resource.get('type', '') for resource in resources))
            
            player_data['total_resources'] = total_resources
            player_data['resource_types'] = '|'.join(resource_types)
            
            # Count resources by type
            resource_amounts = defaultdict(int)
            for resource in resources:
                resource_type = resource.get('type', '')
                amount = int(resource.get('amount', 0))
                resource_amounts[resource_type] += amount
            
            # Add resource amounts as columns
            for resource_type, amount in resource_amounts.items():
                player_data[f'resource_{resource_type}'] = amount
            
            # Process buildings and create metadata
            player_buildings = []
            settlements = settlements_by_player.get(player_id, [])
            
            # Track coordinates for primary city and all settlements
            primary_city_coords = None
            all_settlement_coords = []
            
            for settlement in settlements:
                settlement_id = settlement.get('uuid', '')
                settlement_name = settlement.get('name', '')
                settlement_level = settlement.get('level', '')
                settlement_type = settlement.get('type', '')  # 'city' or 'outpost'
                coordinate_x = settlement.get('coordinate_x', '')
                coordinate_y = settlement.get('coordinate_y', '')
                
                # Store coordinates for this settlement
                if coordinate_x and coordinate_y:
                    all_settlement_coords.append(f"{settlement_name}({settlement_type}):({coordinate_x},{coordinate_y})")
                    # Use the first city as primary city coordinates
                    if settlement_type == 'city' and primary_city_coords is None:
                        primary_city_coords = f"{coordinate_x},{coordinate_y}"
                
                buildings = buildings_by_settlement.get(settlement_id, [])
                settlement_buildings = []
                for building in buildings:
                    building_type = building.get('definition_id', '')
                    building_level = building.get('level', '')
                    settlement_buildings.append(f"{building_type}:{building_level}")
                
                if settlement_buildings:
                    # Include settlement type and coordinates in the metadata
                    coord_str = f"({coordinate_x},{coordinate_y})" if coordinate_x and coordinate_y else ''
                    player_buildings.append(f"{settlement_name}({settlement_level})[{settlement_type}]{coord_str}:[{','.join(settlement_buildings)}]")
            
            player_data['buildings_metadata'] = '|'.join(player_buildings) if player_buildings else ''
            player_data['primary_city_coordinates'] = primary_city_coords if primary_city_coords else ''
            player_data['all_settlement_coordinates'] = '|'.join(all_settlement_coords) if all_settlement_coords else ''
            
            # Process skins
            equipped_skins = equipped_skins_by_player.get(player_id, [])
            unlocked_skins = unlocked_skins_by_player.get(player_id, [])
            
            # Create equipped skins metadata
            equipped_skin_data = []
            for skin in equipped_skins:
                skin_type = skin.get('definition_id', '')
                skin_category = skin.get('category', '')
                settlement_id = skin.get('settlement_id', '')
                if settlement_id:  # Building skin
                    equipped_skin_data.append(f"{skin_type}({skin_category})")
                else:  # Avatar skin
                    equipped_skin_data.append(f"{skin_type}({skin_category})")
            
            # Create unlocked skins metadata
            unlocked_skin_data = []
            for skin in unlocked_skins:
                skin_type = skin.get('definition_id', '')
                unlocked_at = skin.get('unlocked_at', '')
                unlocked_skin_data.append(f"{skin_type}@{unlocked_at}")
            
            player_data['equipped_skins'] = '|'.join(equipped_skin_data) if equipped_skin_data else ''
            player_data['unlocked_skins'] = '|'.join(unlocked_skin_data) if unlocked_skin_data else ''
            player_data['total_skins_equipped'] = len(equipped_skins)
            player_data['total_skins_unlocked'] = len(unlocked_skins)
            
            # Process research
            research_items = research_by_player.get(player_id, [])
            research_levels = []
            research_types = set()
            total_research_level = 0
            
            for research in research_items:
                research_type = research.get('definition_id', '')
                research_level = int(research.get('level', 0))
                research_status = research.get('status', '')
                
                research_levels.append(f"{research_type}:{research_level}")
                research_types.add(research_type)
                total_research_level += research_level
            
            player_data['research_metadata'] = '|'.join(research_levels) if research_levels else ''
            player_data['total_research_level'] = total_research_level
            player_data['completed_research_count'] = len(research_items)
            player_data['research_types'] = '|'.join(sorted(research_types)) if research_types else ''
            
            # Process quests
            quest_items = quests_by_player.get(player_id, [])
            completed_quests = []
            in_progress_quests = []
            quest_types = set()
            total_quest_progress = 0.0
            
            for quest in quest_items:
                quest_type = quest.get('definition_id', '')
                quest_status = quest.get('status', '')
                quest_progress = float(quest.get('progress', 0))
                quest_level = quest.get('level', '')
                quest_claimed = quest.get('claimed', '')
                
                quest_types.add(quest_type)
                total_quest_progress += quest_progress
                
                quest_info = f"{quest_type}:{quest_level}:{quest_status}"
                if quest_status == 'completed':
                    completed_quests.append(quest_info)
                elif quest_status == 'in_progress':
                    in_progress_quests.append(quest_info)
            
            player_data['quest_metadata'] = '|'.join(completed_quests + in_progress_quests) if (completed_quests + in_progress_quests) else ''
            player_data['completed_quests_count'] = len(completed_quests)
            player_data['in_progress_quests_count'] = len(in_progress_quests)
            player_data['total_quests_count'] = len(quest_items)
            player_data['quest_types'] = '|'.join(sorted(quest_types)) if quest_types else ''
            
            # Process alliance data
            alliance_memberships = alliance_members.get(player_id, [])
            if alliance_memberships:
                # Get the first alliance membership
                membership = alliance_memberships[0]
                alliance_id = membership.get('alliance_id', '')
                if alliance_id and alliance_id in alliances:
                    alliance = alliances[alliance_id]
                    player_data['alliance_name'] = alliance.get('name', '')
                    player_data['alliance_tag'] = alliance.get('tag', '')
                else:
                    player_data['alliance_name'] = ''
                    player_data['alliance_tag'] = ''
            else:
                player_data['alliance_name'] = ''
                player_data['alliance_tag'] = ''
            
            # Process effects
            effects = effects_by_player.get(player_id, [])
            active_effects = []
            permanent_effects = []
            effect_types = set()
            total_effects = len(effects)
            
            for effect in effects:
                effect_source = effect.get('source', '')
                effect_type = effect.get('type', '')
                effect_level = effect.get('level', '')
                effect_is_permanent = effect.get('is_permanent', '')
                effect_start_at = effect.get('start_at', '')
                effect_duration = effect.get('duration', '')
                
                effect_types.add(effect_type)
                
                effect_info = f"{effect_source}:{effect_type}:{effect_level}"
                if effect_is_permanent == 't':
                    permanent_effects.append(effect_info)
                else:
                    active_effects.append(effect_info)
            
            player_data['total_effects'] = total_effects
            player_data['active_effects'] = '|'.join(active_effects) if active_effects else ''
            player_data['permanent_effects'] = '|'.join(permanent_effects) if permanent_effects else ''
            player_data['effect_types'] = '|'.join(sorted(effect_types)) if effect_types else ''
            player_data['active_effects_count'] = len(active_effects)
            player_data['permanent_effects_count'] = len(permanent_effects)
            
            comprehensive_data.append(player_data)
        
        print(f"Total players processed: {processed_count}")
        print(f"Comprehensive data records created: {len(comprehensive_data)}")
        
        return comprehensive_data, item_registry, troop_registry
    
    def write_csv(self, data, filename):
        """Write data to CSV file"""
        if not data:
            print("No data to write!")
            return
        
        # Get all possible field names
        fieldnames = set()
        for row in data:
            fieldnames.update(row.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"CSV written to {filename} with {len(data)} rows and {len(fieldnames)} columns")
        return fieldnames
    
    def generate_summary(self, data, fieldnames, output_file):
        """Generate summary statistics"""
        summary_file = output_file.replace('.csv', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("=== PLAYER DATA ANALYSIS SUMMARY ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Players: {len(data)}\n")
            f.write(f"Total Columns: {len(fieldnames)}\n\n")
            
            f.write("=== COLUMN LIST ===\n")
            for i, col in enumerate(fieldnames, 1):
                f.write(f"{i:3d}. {col}\n")
            
            f.write("\n=== DATA PREVIEW ===\n")
            # Show first 3 players
            for i, player in enumerate(data[:3]):
                f.write(f"\n--- Player {i+1} ---\n")
                for key, value in list(player.items())[:10]:  # Show first 10 fields
                    f.write(f"{key}: {value}\n")
                if len(player) > 10:
                    f.write(f"... and {len(player)-10} more fields\n")
        
        print(f"Summary saved to {summary_file}")
    
    def get_output_filename(self, tar_file):
        """Generate output filename based on tar file name"""
        tar_filename = os.path.basename(tar_file)
        # Extract date from format: csv-exports_backup_YYYY-MM-DD_HH-MM-SS_csv.tar.gz
        date_match = tar_filename.split('backup_')[1].split('_csv.tar.gz')[0] if 'backup_' in tar_filename else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Convert from YYYY-MM-DD_HH-MM-SS to YYYY-MM-DD_HHMMSS format
        date_parts = date_match.split('_')
        date_part = date_parts[0]
        time_part = date_parts[1].replace('-', '')
        date_formatted = f"{date_part}_{time_part}"
        
        return os.path.join(self.database_path, f"comprehensive_player_data_{date_formatted}.csv")

    def generate_comprehensive_csv(self):
        """Main function to generate the comprehensive CSV for all tar files"""
        print("Starting comprehensive player data analysis...")
        
        for tar_file in self.tar_files:
            print(f"\n{'='*60}")
            print(f"Processing: {os.path.basename(tar_file)}")
            print(f"{'='*60}")
            
            output_file = self.get_output_filename(tar_file)
            
            try:
                # Extract tar file
                self.extract_tar_file(tar_file)
                
                # Load CSV data
                data = self.load_csv_data()
                
                # Process and consolidate data
                comprehensive_data, item_registry, troop_registry = self.process_player_data(data)
                
                if not comprehensive_data:
                    print("No data to process!")
                    continue
                
                # Save to CSV
                fieldnames = self.write_csv(comprehensive_data, output_file)
                
                # Generate summary
                self.generate_summary(comprehensive_data, fieldnames, output_file)
                
                print(f"Analysis complete! Output saved to {output_file}")
                print(f"Total players processed: {len(comprehensive_data)}")
                print(f"Total data points: {len(fieldnames)}")
                print(f"Item types registered: {len(item_registry)}")
                print(f"Troop types registered: {len(troop_registry)}")
                
            finally:
                # Always clean up extracted files
                self.cleanup_extracted_files()
        
        print(f"\n{'='*60}")
        print(f"Processed {len(self.tar_files)} tar file(s)")
        print(f"{'='*60}")

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create analyzer and run
    analyzer = PlayerDataAnalyzer(script_dir)
    analyzer.generate_comprehensive_csv()
