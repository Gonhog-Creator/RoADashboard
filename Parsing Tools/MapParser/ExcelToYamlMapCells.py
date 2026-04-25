import yaml
import pandas as pd
import re
from collections import defaultdict

def excel_to_yaml(excel_file_path, original_yaml_path, output_yaml_path):
    """
    Import Excel file in the same format as MapCellsParser output and generate
    a new YAML file with updated values while preserving exact structure.
    """
    
    # Load the original YAML to preserve structure, comments, and metadata
    with open(original_yaml_path, 'r') as file:
        original_yaml_content = file.read()
    
    # Parse original YAML to get the complete structure
    original_data = yaml.safe_load(original_yaml_content)
    
    # Load the Excel data
    df = pd.read_excel(excel_file_path)
    
    # Parse column names to identify resources, items, and troops
    resource_columns = ['Food', 'Stone', 'Metal', 'Lumber']
    item_columns = [col for col in df.columns if col not in ['Target Type', 'Target Level'] + resource_columns and not col.startswith('Troop_')]
    troop_columns = [col for col in df.columns if col.startswith('Troop_')]
    
    # Convert item column names back to YAML format (Title Case -> snake_case)
    def title_to_snake(name):
        return name.lower().replace(' ', '_')
    
    # Convert troop column names back to YAML format
    def troop_name_to_yaml(name):
        return name.replace('Troop_', '').lower().replace(' ', '_')
    
    # Create new data structure
    new_data = {}
    
    # Process each row in the Excel file
    for _, row in df.iterrows():
        target_type = row['Target Type'].lower()  # Convert back to lowercase for YAML keys
        target_level = int(row['Target Level'])
        
        # Initialize the cell type if not exists
        if target_type not in new_data:
            # Copy basic structure from original
            if target_type in original_data:
                new_data[target_type] = {
                    'id': original_data[target_type].get('id', target_type),
                    'attackable': original_data[target_type].get('attackable', True),
                    'troops': {},
                    'rewards': {}
                }
                # Preserve effects if they exist in original
                if 'effects' in original_data[target_type]:
                    new_data[target_type]['effects'] = original_data[target_type]['effects']
            else:
                new_data[target_type] = {
                    'id': target_type,
                    'attackable': True,
                    'troops': {},
                    'rewards': {}
                }
        
        # Update resources and items for this level
        if 'rewards' not in new_data[target_type]:
            new_data[target_type]['rewards'] = {}
        
        # Build resources dict
        resources = {}
        for resource in resource_columns:
            if pd.notna(row[resource]) and row[resource] != 0:
                resources[resource.lower()] = int(row[resource])
        
        # Build items dict
        items = {
            'apply_random': True,
            '_no_loot': {'weight': 0.950}  # Default _no_loot weight
        }
        
        for item_col in item_columns:
            if pd.notna(row[item_col]) and row[item_col] != 0:
                item_name = title_to_snake(item_col)
                items[item_name] = {
                    'amount': 1,  # Default amount
                    'weight': float(row[item_col])
                }
        
        # Only add rewards level if there are resources or items
        if resources or items:
            reward_data = {}
            if resources:
                reward_data['resources'] = resources
            if len(items) > 2:  # More than just apply_random and _no_loot
                reward_data['items'] = items
            
            new_data[target_type]['rewards'][target_level] = reward_data
        
        # Update troops for this level
        if 'troops' not in new_data[target_type]:
            new_data[target_type]['troops'] = {}
        
        troops = {}
        for troop_col in troop_columns:
            if pd.notna(row[troop_col]) and row[troop_col] != 0:
                troop_name = troop_name_to_yaml(troop_col)
                troops[troop_name] = int(row[troop_col])
        
        if troops:
            new_data[target_type]['troops'][target_level] = troops
    
    # Preserve any cell types from original that weren't in Excel
    for cell_type, cell_data in original_data.items():
        if cell_type not in new_data:
            new_data[cell_type] = cell_data
    
    # Generate YAML with proper formatting and preserve comments
    yaml_content = generate_yaml_with_comments(new_data, original_yaml_content)
    
    # Write to output file
    with open(output_yaml_path, 'w') as file:
        file.write(yaml_content)
    
    print(f"Updated YAML file saved to: {output_yaml_path}")
    print(f"Processed {len(df)} rows from Excel file")
    
    return new_data

def generate_yaml_with_comments(data, original_content):
    """
    Generate YAML content while preserving original comments and structure
    """
    # Extract header comments from original
    header_lines = []
    lines = original_content.split('\n')
    
    # Capture header (everything before first data entry)
    for line in lines:
        if line.startswith('#') or line.strip() == '':
            header_lines.append(line)
        elif line and not line.startswith('#') and ':' in line and not line.startswith('##'):
            break
    
    header = '\n'.join(header_lines) + '\n\n' if header_lines else ''
    
    # Generate YAML for data
    yaml_data = yaml.dump(data, default_flow_style=False, sort_keys=False, indent=2)
    
    # Fix formatting to match original style
    yaml_data = fix_yaml_formatting(yaml_data)
    
    return header + yaml_data

def fix_yaml_formatting(yaml_str):
    """
    Fix YAML formatting to match the original file style
    """
    # Fix list formatting (effects should use dash notation)
    yaml_str = re.sub(r'(\s+)-\s+name:', r'\1- name:', yaml_str)
    
    # Ensure proper spacing
    yaml_str = re.sub(r':(\S)', r': \1', yaml_str)
    
    # Fix weight formatting to ensure consistent decimal places
    yaml_str = re.sub(r'weight:\s*(\d+\.\d{3})', r'weight: \1', yaml_str)
    yaml_str = re.sub(r'weight:\s*(\d+\.\d{2})', r'weight: \1', yaml_str)
    
    return yaml_str

if __name__ == '__main__':
    excel_file = 'Map_Cells_Output.xlsx'
    original_yaml = 'Map_CellsV2.yaml'
    output_yaml = 'Map_CellsV2_Updated.yaml'
    
    try:
        new_data = excel_to_yaml(excel_file, original_yaml, output_yaml)
        print("Excel to YAML conversion completed successfully!")
        
        # Show a sample of what was processed
        sample_type = list(new_data.keys())[0]
        sample_level = list(new_data[sample_type].get('rewards', {}).keys())[0]
        print(f"\nSample processed data for {sample_type} level {sample_level}:")
        print(f"Resources: {new_data[sample_type]['rewards'][sample_level].get('resources', {})}")
        print(f"Items: {list(new_data[sample_type]['rewards'][sample_level].get('items', {}).keys())}")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        print("Make sure the Excel file exists and has the correct format.")
