import yaml
import pandas as pd
import re
from collections import defaultdict

def buildings_excel_to_yaml(excel_file_path, original_yaml_path, output_yaml_path):
    """
    Import Excel file in the same format as BuildingsParser output and generate
    a new YAML file with updated values while preserving exact structure.
    """
    
    # Load the original YAML to preserve structure, comments, and metadata
    with open(original_yaml_path, 'r') as file:
        original_yaml_content = file.read()
    
    # Parse original YAML to get the complete structure
    original_data = yaml.safe_load(original_yaml_content)
    
    # Load the Excel data
    df = pd.read_excel(excel_file_path)
    
    # Parse column names to identify different data types
    resource_columns = ['Food', 'Lumber', 'Stone', 'Metal', 'Gold']
    generated_resource_columns = [col for col in df.columns if col.startswith('Gen ')]
    building_req_columns = [col for col in df.columns if col.startswith('Req ')]
    effect_columns = [col for col in df.columns if col.startswith('Effect ')]
    
    print(f"Found {len(generated_resource_columns)} generation columns: {generated_resource_columns}")
    print(f"Found {len(building_req_columns)} building requirement columns: {building_req_columns}")
    print(f"Found {len(effect_columns)} effect columns: {effect_columns}")
    
    # Convert column names back to YAML format
    def title_to_snake(name):
        return name.lower().replace(' ', '_')
    
    def gen_resource_to_yaml(name):
        return title_to_snake(name.replace('Gen ', ''))
    
    def building_req_to_yaml(name):
        return title_to_snake(name.replace('Req ', ''))
    
    def effect_to_yaml(name):
        return title_to_snake(name.replace('Effect ', ''))
    
    # Create new data structure
    new_data = {}
    
    # Process each row in the Excel file
    for _, row in df.iterrows():
        try:
            building_type = row['Building Type'].lower()  # Convert back to lowercase for YAML keys
            building_level = int(row['Building Level'])
            
            # Initialize the building type if not exists
            if building_type not in new_data:
                # Copy basic structure from original
                if building_type in original_data and isinstance(original_data[building_type], dict):
                    new_data[building_type] = {
                        'id': original_data[building_type].get('id', building_type),
                        'max_level': original_data[building_type].get('max_level', 10),
                        'max_build_count': original_data[building_type].get('max_build_count', 0),
                        'destructible': original_data[building_type].get('destructible', True),
                        'settlement_types': original_data[building_type].get('settlement_types', []),
                        'for_field': original_data[building_type].get('for_field', False),
                        'requirements': {},
                        'generations': {},
                        'effects': {}
                    }
                else:
                    new_data[building_type] = {
                        'id': building_type,
                        'max_level': 10,
                        'max_build_count': 0,
                        'destructible': True,
                        'settlement_types': [],
                        'for_field': False,
                        'requirements': {},
                        'generations': {},
                        'effects': {}
                    }
            
            # Update requirements for this level
            if 'requirements' not in new_data[building_type]:
                new_data[building_type]['requirements'] = {}
            
            # Build resources dict for requirements
            resources = {}
            for resource in resource_columns:
                if pd.notna(row[resource]) and row[resource] != 0:
                    resources[resource.lower()] = int(row[resource])
            
            # Build building requirements dict
            building_reqs = {}
            for building_col in building_req_columns:
                if pd.notna(row[building_col]) and row[building_col] != 0:
                    building_name = building_req_to_yaml(building_col)
                    building_reqs[building_name] = int(row[building_col])
            
            # Build requirement level data
            req_data = {}
            if resources:
                req_data['resources'] = resources
            if building_reqs:
                req_data['buildings'] = building_reqs
            
            # Add duration, population, capacity if present
            if pd.notna(row['Duration']) and row['Duration'] != 0:
                req_data['duration'] = int(row['Duration'])
            if pd.notna(row['Population']) and row['Population'] != 0:
                req_data['population'] = int(row['Population'])
            if pd.notna(row['Capacity']) and row['Capacity'] != 0:
                req_data['capacity'] = int(row['Capacity'])
            
            # Only add requirements level if there's data
            if req_data:
                new_data[building_type]['requirements'][building_level] = req_data
            
            # Update generations for this level
            if 'generations' not in new_data[building_type]:
                new_data[building_type]['generations'] = {}
            
            gen_data = {}
            
            # Handle population generation
            if pd.notna(row.get('Pop Generation')) and row['Pop Generation'] != 0:
                gen_data['population'] = int(row['Pop Generation'])
            
            # Handle capacity generation
            if pd.notna(row.get('Capacity Generation')) and row['Capacity Generation'] != 0:
                gen_data['capacity'] = int(row['Capacity Generation'])
            
            # Handle other generated resources
            for gen_col in generated_resource_columns:
                if pd.notna(row[gen_col]) and row[gen_col] != 0:
                    resource_name = gen_resource_to_yaml(gen_col)
                    gen_data[resource_name] = int(row[gen_col])
            
            if gen_data:
                new_data[building_type]['generations'][building_level] = gen_data
            
            # Update effects for this building
            if 'effects' not in new_data[building_type]:
                new_data[building_type]['effects'] = {}
            
            for effect_col in effect_columns:
                if pd.notna(row[effect_col]) and row[effect_col] != 0:
                    effect_name = effect_to_yaml(effect_col)
                    # Get original effect configuration to preserve scale and units
                    original_effect = original_data.get(building_type, {}).get('effects', {}).get(effect_name, {})
                    if isinstance(original_effect, dict):
                        new_data[building_type]['effects'][effect_name] = {
                            'default': float(row[effect_col]),
                            'default_unit': original_effect.get('default_unit', 'percentage'),
                            'scale': original_effect.get('scale', 0),
                            'scale_unit': original_effect.get('scale_unit', 'percentage')
                        }
                    else:
                        new_data[building_type]['effects'][effect_name] = float(row[effect_col])
        except Exception as e:
            print(f"Error processing row for building {row.get('Building Type', 'unknown')} level {row.get('Building Level', 'unknown')}: {e}")
            continue
    
    # Preserve any building types from original that weren't in Excel
    for building_type, building_data in original_data.items():
        if building_type not in new_data:
            new_data[building_type] = building_data
    
    # Clean up empty sections
    for building_type, building_data in new_data.items():
        try:
            if 'requirements' in building_data and not building_data['requirements']:
                del building_data['requirements']
            if 'generations' in building_data and not building_data['generations']:
                del building_data['generations']
            if 'effects' in building_data and not building_data['effects']:
                del building_data['effects']
        except Exception as e:
            print(f"Error cleaning up {building_type}: {e}")
            continue
    
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
    
    # Fix numeric formatting
    yaml_str = re.sub(r'(\d+\.0+)', lambda m: str(int(float(m.group(1)))), yaml_str)
    
    return yaml_str

if __name__ == '__main__':
    excel_file = 'Buildings_Output.xlsx'
    original_yaml = 'buildings.yaml'
    output_yaml = 'buildings_Updated.yaml'
    
    try:
        new_data = buildings_excel_to_yaml(excel_file, original_yaml, output_yaml)
        print("Excel to YAML conversion completed successfully!")
        
        # Show a sample of what was processed
        sample_type = list(new_data.keys())[0]
        print(f"\nSample processed data for {sample_type}:")
        if 'requirements' in new_data[sample_type]:
            sample_level = list(new_data[sample_type]['requirements'].keys())[0]
            print(f"Level {sample_level} requirements: {new_data[sample_type]['requirements'][sample_level]}")
        if 'generations' in new_data[sample_type]:
            print(f"Generations: {list(new_data[sample_type]['generations'].keys())}")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        print("Make sure the Excel file exists and has the correct format.")
