#!/usr/bin/env python3
"""
Excel to YAML Converter

Reads the edited Excel file and rebuilds the YAML file with updated costs,
durations, and rewards while preserving all other data and formatting.
"""

import pandas as pd
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
import os
import re

def parse_key_value_string(kv_string):
    """Parse 'key:value,key:value' format into dictionary."""
    if not kv_string or pd.isna(kv_string):
        return {}
    
    result = {}
    for pair in str(kv_string).split(','):
        if ':' in pair:
            key, value = pair.split(':', 1)
            try:
                # Try to convert to int, otherwise keep as string
                if value.isdigit():
                    result[key.strip()] = int(value.strip())
                else:
                    result[key.strip()] = value.strip()
            except ValueError:
                result[key.strip()] = value.strip()
    return result

def load_excel_data(excel_path):
    """Load and process data from Excel file."""
    df = pd.read_excel(excel_path, sheet_name='Building_Data')
    
    # Fill NaN values with appropriate defaults
    df = df.fillna({
        'settlement_type': '',
        'food_cost': 0,
        'lumber_cost': 0,
        'stone_cost': 0,
        'metal_cost': 0,
        'gold_cost': 0,
        'duration': 0,
        'population_required': 0,
        'required_buildings': '',
        'required_items': '',
        'power_reward': 0,
        'generated_resources': '',
        'population_generated': 0,
        'capacity': 0,
        'troops_per_march': 0,
        'march_count': 0
    })
    
    return df

def rebuild_yaml_structure(df):
    """Rebuild the complete YAML structure from Excel data."""
    yaml_data = CommentedMap()
    
    # Group by building_id
    for building_id, building_group in df.groupby('building_id'):
        # Get basic building info from first row
        first_row = building_group.iloc[0]
        
        building_data = CommentedMap()
        building_data['id'] = building_id
        building_data['max_level'] = int(first_row['max_level'])
        building_data['max_build_count'] = int(first_row['max_build_count'])
        building_data['destructible'] = bool(first_row['destructible'])
        
        # Parse settlement types
        settlement_types = str(first_row['settlement_types']).split(',')
        building_data['settlement_types'] = [s.strip() for s in settlement_types if s.strip()]
        building_data['for_field'] = bool(first_row['for_field'])
        
        # Build requirements structure
        requirements = CommentedMap()
        
        for _, row in building_group.iterrows():
            settlement_type = str(row['settlement_type']).strip()
            level = int(row['level'])
            
            if settlement_type:  # Only process rows with settlement_type
                if settlement_type not in requirements:
                    requirements[settlement_type] = CommentedMap()
                
                level_data = CommentedMap()
                
                # Add resources if any costs > 0
                resources = CommentedMap()
                if row['food_cost'] > 0:
                    resources['food'] = int(row['food_cost'])
                if row['lumber_cost'] > 0:
                    resources['lumber'] = int(row['lumber_cost'])
                if row['stone_cost'] > 0:
                    resources['stone'] = int(row['stone_cost'])
                if row['metal_cost'] > 0:
                    resources['metal'] = int(row['metal_cost'])
                if row['gold_cost'] > 0:
                    resources['gold'] = int(row['gold_cost'])
                
                if resources:
                    level_data['resources'] = resources
                
                # Add duration
                if row['duration'] > 0:
                    level_data['duration'] = int(row['duration'])
                
                # Add population requirement
                if row['population_required'] > 0:
                    level_data['population'] = int(row['population_required'])
                
                # Add required buildings
                if row['required_buildings']:
                    buildings = parse_key_value_string(row['required_buildings'])
                    if buildings:
                        level_data['buildings'] = CommentedMap(buildings)
                
                # Add required items
                if row['required_items']:
                    items = parse_key_value_string(row['required_items'])
                    if items:
                        level_data['items'] = CommentedMap(items)
                
                # Only add level data if it's not empty
                if level_data:  # This checks if the CommentedMap has any content
                    requirements[settlement_type][level] = level_data
        
        if requirements:
            building_data['requirements'] = requirements
        
        # Build rewards structure
        rewards = CommentedMap()
        reward_rows = building_group[building_group['power_reward'] > 0]
        
        for _, row in reward_rows.iterrows():
            level = int(row['level'])
            rewards[level] = {'power': int(row['power_reward'])}
        
        if rewards:
            building_data['rewards'] = rewards
        
        # Build generations structure
        generations = CommentedMap()
        gen_rows = building_group[
            (building_group['generated_resources'] != '') |
            (building_group['population_generated'] > 0) |
            (building_group['capacity'] > 0) |
            (building_group['troops_per_march'] > 0)
        ]
        
        for _, row in gen_rows.iterrows():
            level = int(row['level'])
            gen_data = CommentedMap()
            
            # Add generated resources
            if row['generated_resources']:
                resources = parse_key_value_string(row['generated_resources'])
                if resources:
                    gen_data['resources'] = CommentedMap(resources)
            
            # Add population generation
            if row['population_generated'] > 0:
                gen_data['population'] = int(row['population_generated'])
            
            # Add capacity
            if row['capacity'] > 0:
                gen_data['capacity'] = int(row['capacity'])
            
            # Add troop march data
            if row['troops_per_march'] > 0:
                gen_data['troops_per_march'] = int(row['troops_per_march'])
            if row['march_count'] > 0:
                gen_data['march_count'] = int(row['march_count'])
            
            if gen_data:
                generations[level] = gen_data
        
        if generations:
            building_data['generations'] = generations
        
        # Add special actions if they existed in original (preserve from backup)
        # This would need to be handled separately or copied from original
        
        yaml_data[building_id] = building_data
    
    return yaml_data

def preserve_special_data(original_yaml_path, new_yaml_data):
    """Copy special data like effects, special_actions from original YAML."""
    yaml = YAML()
    yaml.preserve_quotes = True
    
    # Always use the backup file that was just created
    backup_path = original_yaml_path + ".backup"
    
    if os.path.exists(backup_path):
        yaml_file_to_read = backup_path
        print(f"Reading special data from backup: {backup_path}")
    else:
        print("Warning: No backup file found, special data may be lost")
        return new_yaml_data
    
    with open(yaml_file_to_read, 'r', encoding='utf-8') as f:
        original_data = yaml.load(f)
    
    # Copy special fields that aren't handled by Excel
    special_fields = ['effects', 'special_actions']
    
    for building_id, building_data in new_yaml_data.items():
        if building_id in original_data:
            original_building = original_data[building_id]
            
            for field in special_fields:
                if field in original_building:
                    building_data[field] = original_building[field]
    
    return new_yaml_data

def main():
    """Main conversion function."""
    # Check for updated file first, then fallback to original
    if os.path.exists("buildings_data_updated.xlsx"):
        excel_path = "buildings_data_updated.xlsx"
        print("Using buildings_data_updated.xlsx")
    else:
        excel_path = "buildings_data.xlsx"
        print("Using buildings_data.xlsx")
    
    yaml_path = "buildings.yaml"
    backup_path = "buildings.yaml.backup"
    
    print("Loading Excel data...")
    df = load_excel_data(excel_path)
    
    print("Rebuilding YAML structure...")
    yaml_data = rebuild_yaml_structure(df)
    
    # Create backup of current YAML BEFORE we preserve special data
    if os.path.exists(yaml_path):
        import shutil
        shutil.copy2(yaml_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    print("Preserving special data from original YAML...")
    yaml_data = preserve_special_data(yaml_path, yaml_data)
    
    # Save with proper formatting
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.default_flow_style = False  # Use block style for most things
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f)
    
    # Fix settlement_types format inline
    print("Fixing settlement_types format...")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the malformed YAML first: settlement_types: [city]\n    - outpost
    content = re.sub(
        r'settlement_types: \[(\w+)\]\s*\n\s*-\s*(\w+)',
        r'settlement_types: [\1, \2]',
        content
    )
    
    # Fix double item lists in proper format
    content = re.sub(
        r'settlement_types:\s*\n\s*-\s*(\w+)\s*\n\s*-\s*(\w+)',
        r'settlement_types: [\1, \2]',
        content
    )
    
    # Fix single item lists
    content = re.sub(
        r'settlement_types:\s*\n\s*-\s*(\w+)',
        r'settlement_types: [\1]',
        content
    )
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Settlement_types format fixed inline")
    
    print(f"YAML file updated: {yaml_path}")
    print("All costs, durations, and rewards have been updated from Excel.")

if __name__ == "__main__":
    main()
