#!/usr/bin/env python3
"""
YAML to Excel Converter

Extracts all building data from YAML file and creates a comprehensive Excel file
for manual editing of costs, durations, and power rewards.
"""

import pandas as pd
from ruamel.yaml import YAML
import os
from pathlib import Path

def extract_all_building_data(yaml_path):
    """Extract all relevant data from YAML file."""
    yaml = YAML()
    yaml.preserve_quotes = True
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.load(f)
    
    buildings_data = []
    
    for building_id, building_info in yaml_data.items():
        # Basic building info
        base_info = {
            'building_id': building_id,
            'max_level': building_info.get('max_level', 0),
            'max_build_count': building_info.get('max_build_count', 0),
            'destructible': building_info.get('destructible', False),
            'settlement_types': ','.join(building_info.get('settlement_types', [])),
            'for_field': building_info.get('for_field', False)
        }
        
        # Extract requirements for each settlement type and level
        requirements = building_info.get('requirements', {})
        
        if isinstance(requirements, dict):
            # Check if requirements have settlement types or are direct
            has_settlement_types = any(key in ['city', 'outpost'] for key in requirements.keys())
            
            if has_settlement_types:
                # Process settlement-type requirements
                for settlement_type, settlement_data in requirements.items():
                    if isinstance(settlement_data, dict):
                        for level, level_data in settlement_data.items():
                            try:
                                level_int = int(level)
                            except ValueError:
                                continue  # Skip non-numeric levels
                            
                            row = base_info.copy()
                            row.update({
                                'settlement_type': settlement_type,
                                'level': level_int,
                            })
                            
                            # Resource requirements
                            resources = level_data.get('resources', {})
                            row.update({
                                'food_cost': resources.get('food', 0),
                                'lumber_cost': resources.get('lumber', 0),
                                'stone_cost': resources.get('stone', 0),
                                'metal_cost': resources.get('metal', 0),
                                'gold_cost': resources.get('gold', 0),
                                'duration': level_data.get('duration', 0),
                                'population_required': level_data.get('population', 0)
                            })
                            
                            # Building requirements
                            buildings = level_data.get('buildings', {})
                            if buildings:
                                row['required_buildings'] = ','.join([f"{k}:{v}" for k, v in buildings.items()])
                            else:
                                row['required_buildings'] = ''
                            
                            # Item requirements
                            items = level_data.get('items', {})
                            if items:
                                row['required_items'] = ','.join([f"{k}:{v}" for k, v in items.items()])
                            else:
                                row['required_items'] = ''
                            
                            buildings_data.append(row)
            else:
                # Process direct requirements - default to 'city'
                for level, level_data in requirements.items():
                    try:
                        level_int = int(level)
                    except ValueError:
                        continue  # Skip non-numeric levels
                    
                    row = base_info.copy()
                    row.update({
                        'settlement_type': 'city',  # Default to city
                        'level': level_int,
                    })
                    
                    # Resource requirements
                    resources = level_data.get('resources', {})
                    row.update({
                        'food_cost': resources.get('food', 0),
                        'lumber_cost': resources.get('lumber', 0),
                        'stone_cost': resources.get('stone', 0),
                        'metal_cost': resources.get('metal', 0),
                        'gold_cost': resources.get('gold', 0),
                        'duration': level_data.get('duration', 0),
                        'population_required': level_data.get('population', 0)
                    })
                    
                    # Building requirements
                    buildings = level_data.get('buildings', {})
                    if buildings:
                        row['required_buildings'] = ','.join([f"{k}:{v}" for k, v in buildings.items()])
                    else:
                        row['required_buildings'] = ''
                    
                    # Item requirements
                    items = level_data.get('items', {})
                    if items:
                        row['required_items'] = ','.join([f"{k}:{v}" for k, v in items.items()])
                    else:
                        row['required_items'] = ''
                    
                    buildings_data.append(row)
        
        # Extract rewards
        rewards = building_info.get('rewards', {})
        for level, reward_data in rewards.items():
            # Find corresponding building row or create new one
            matching_rows = [r for r in buildings_data 
                           if r['building_id'] == building_id and r['level'] == int(level)]
            
            if matching_rows:
                matching_rows[0]['power_reward'] = reward_data.get('power', 0)
            else:
                # Create reward-only row if no requirements found
                row = base_info.copy()
                row.update({
                    'settlement_type': '',
                    'level': int(level),
                    'power_reward': reward_data.get('power', 0),
                    'food_cost': 0,
                    'lumber_cost': 0,
                    'stone_cost': 0,
                    'metal_cost': 0,
                    'gold_cost': 0,
                    'duration': 0,
                    'population_required': 0,
                    'required_buildings': '',
                    'required_items': ''
                })
                buildings_data.append(row)
        
        # Extract generations
        generations = building_info.get('generations', {})
        for level, gen_data in generations.items():
            matching_rows = [r for r in buildings_data 
                           if r['building_id'] == building_id and r['level'] == int(level)]
            
            if matching_rows:
                row = matching_rows[0]
                # Resource generation
                resources = gen_data.get('resources', {})
                if resources:
                    row['generated_resources'] = ','.join([f"{k}:{v}" for k, v in resources.items()])
                else:
                    row['generated_resources'] = ''
                
                # Population generation
                row['population_generated'] = gen_data.get('population', 0)
                
                # Capacity
                row['capacity'] = gen_data.get('capacity', 0)
                
                # Troops per march
                row['troops_per_march'] = gen_data.get('troops_per_march', 0)
                row['march_count'] = gen_data.get('march_count', 0)
    
    return buildings_data

def create_excel_file(buildings_data, excel_path):
    """Create comprehensive Excel file with building data."""
    df = pd.DataFrame(buildings_data)
    
    # Reorder columns for better readability
    column_order = [
        'building_id', 'settlement_type', 'level',
        'food_cost', 'lumber_cost', 'stone_cost', 'metal_cost', 'gold_cost',
        'duration', 'population_required', 'required_buildings', 'required_items',
        'power_reward', 'generated_resources', 'population_generated', 'capacity',
        'troops_per_march', 'march_count',
        'max_level', 'max_build_count', 'destructible', 'settlement_types', 'for_field'
    ]
    
    # Ensure all columns exist
    for col in column_order:
        if col not in df.columns:
            df[col] = ''
    
    df = df[column_order]
    
    # Sort by building_id, settlement_type, level
    df = df.sort_values(['building_id', 'settlement_type', 'level'])
    
    # Create Excel writer with multiple sheets
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Main data sheet
        df.to_excel(writer, sheet_name='Building_Data', index=False)
        
        # Summary sheet
        summary_df = df.groupby('building_id').agg({
            'settlement_type': lambda x: ','.join(sorted(set(str(x)))),
            'level': 'max',
            'max_level': 'first',
            'max_build_count': 'first',
            'destructible': 'first',
            'settlement_types': 'first',
            'for_field': 'first'
        }).reset_index()
        summary_df.columns = ['building_id', 'settlement_types_found', 'max_level_found', 
                             'max_level', 'max_build_count', 'destructible', 
                             'settlement_types', 'for_field']
        
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Get column widths for better formatting
        worksheet = writer.sheets['Building_Data']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)

def main():
    """Main conversion function."""
    yaml_path = "buildings.yaml"
    excel_path = "buildings_data.xlsx"
    
    print("Extracting building data from YAML...")
    buildings_data = extract_all_building_data(yaml_path)
    
    print(f"Found {len(buildings_data)} building records")
    
    print("Creating Excel file...")
    create_excel_file(buildings_data, excel_path)
    
    print(f"Excel file created: {excel_path}")
    print("You can now edit the costs, durations, and rewards in Excel.")
    print("Then run 'excel_to_yaml.py' to convert back to YAML format.")

if __name__ == "__main__":
    main()
