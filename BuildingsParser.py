import yaml
import pandas as pd
from collections import defaultdict

def parse_buildings_yaml_to_excel(yaml_file_path, output_excel_path):
    """
    Parse YAML file containing building data and export to Excel format.
    
    Columns:
    1: Building Type
    2: Building Level  
    3-7: Resource Costs (food, lumber, stone, metal, gold)
    8: Duration
    9: Population
    10: Capacity
    11+: Generated Resources
    After resources: Building Requirements
    Final: Effects (power)
    """
    
    # Load YAML data
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    # Collect all unique resources, building requirements, and effects
    all_resources = set()
    all_building_requirements = set()
    all_effects = set()
    all_generated_resources = set()
    
    # First pass: collect all unique types
    for building_type, building_data in data.items():
        try:
            if not isinstance(building_data, dict):
                continue
                
            if 'requirements' in building_data and isinstance(building_data['requirements'], dict):
                for level, req_data in building_data['requirements'].items():
                    if isinstance(req_data, dict):
                        if 'resources' in req_data and isinstance(req_data['resources'], dict):
                            for resource in req_data['resources'].keys():
                                all_resources.add(resource)
                        if 'buildings' in req_data and isinstance(req_data['buildings'], dict):
                            for building in req_data['buildings'].keys():
                                all_building_requirements.add(building)
            
            if 'generations' in building_data and isinstance(building_data['generations'], dict):
                for level, gen_data in building_data['generations'].items():
                    if isinstance(gen_data, dict):
                        for key, value in gen_data.items():
                            if key not in ['population', 'capacity']:
                                if isinstance(value, dict):
                                    # Handle nested resource generation
                                    for nested_resource in value.keys():
                                        all_generated_resources.add(f"{key}_{nested_resource}")
                                else:
                                    all_generated_resources.add(key)
            
            if 'effects' in building_data and isinstance(building_data['effects'], dict):
                for effect_name, effect_data in building_data['effects'].items():
                    all_effects.add(effect_name)
        except Exception as e:
            print(f"Error processing {building_type}: {e}")
            continue
    
    # Sort for consistent column order
    all_resources = sorted(list(all_resources))
    all_building_requirements = sorted(list(all_building_requirements))
    all_effects = sorted(list(all_effects))
    all_generated_resources = sorted(list(all_generated_resources))
    
    # Define standard resource types (columns 3-7)
    resource_types = ['food', 'lumber', 'stone', 'metal', 'gold']
    
    # Prepare data for DataFrame
    rows = []
    
    for building_type, building_data in data.items():
        try:
            # Skip non-building entries
            if not isinstance(building_data, dict) or 'id' not in building_data:
                continue
            
            # Determine max level from requirements, generations, or max_level
            max_level = building_data.get('max_level', 1)
            
            # Check if there are levels beyond max_level in requirements or generations
            if 'requirements' in building_data and isinstance(building_data['requirements'], dict):
                max_level = max(max_level, max(building_data['requirements'].keys()))
            if 'generations' in building_data and isinstance(building_data['generations'], dict):
                max_level = max(max_level, max(building_data['generations'].keys()))
            
            for level in range(1, max_level + 1):
                row = {
                    'Building Type': building_type.title(),
                    'Building Level': level
                }
                
                # Add resource costs (columns 3-7)
                req_data = building_data.get('requirements', {}).get(level, {})
                if isinstance(req_data, dict):
                    resources = req_data.get('resources', {})
                    
                    for resource in resource_types:
                        row[f'{resource.capitalize()}'] = resources.get(resource, 0)
                    
                    # Add duration
                    row['Duration'] = req_data.get('duration', 0)
                    
                    # Add population from requirements
                    row['Population'] = req_data.get('population', 0)
                    
                    # Add capacity from requirements
                    row['Capacity'] = req_data.get('capacity', 0)
                else:
                    # Default values if no requirements data
                    for resource in resource_types:
                        row[f'{resource.capitalize()}'] = 0
                    row['Duration'] = 0
                    row['Population'] = 0
                    row['Capacity'] = 0
                
                # Add generated resources
                gen_data = building_data.get('generations', {}).get(level, {})
                if isinstance(gen_data, dict):
                    for gen_resource in all_generated_resources:
                        if '_' in gen_resource:
                            # Handle nested resource generation (format: "category_resource")
                            parts = gen_resource.split('_')
                            category = parts[0]
                            resource = '_'.join(parts[1:])
                            if category in gen_data and isinstance(gen_data[category], dict):
                                row[f'Gen {resource.title()}'] = gen_data[category].get(resource.lower(), 0)
                            else:
                                row[f'Gen {resource.title()}'] = 0
                        else:
                            # Handle simple generation
                            row[f'Gen {gen_resource.title()}'] = gen_data.get(gen_resource, 0)
                    
                    # Handle population generation separately
                    if 'population' in gen_data:
                        row['Pop Generation'] = gen_data['population']
                    else:
                        row['Pop Generation'] = 0
                    
                    # Handle capacity generation separately
                    if 'capacity' in gen_data:
                        row['Capacity Generation'] = gen_data['capacity']
                    else:
                        row['Capacity Generation'] = 0
                
                # Add building requirements
                building_reqs = req_data.get('buildings', {}) if isinstance(req_data, dict) else {}
                for building in all_building_requirements:
                    row[f'Req {building.title()}'] = building_reqs.get(building, 0)
                
                # Add effects
                effects_data = building_data.get('effects', {})
                for effect in all_effects:
                    effect_config = effects_data.get(effect, {})
                    if isinstance(effect_config, dict):
                        row[f'Effect {effect.title()}'] = effect_config.get('default', 0)
                    else:
                        row[f'Effect {effect.title()}'] = 0
                
                rows.append(row)
        except Exception as e:
            print(f"Error processing {building_type} level {level if 'level' in locals() else 'unknown'}: {e}")
            continue
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Save to Excel
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Buildings_Data', index=False)
        
        # Adjust column widths for better readability
        worksheet = writer.sheets['Buildings_Data']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"Excel file saved to: {output_excel_path}")
    print(f"Total rows processed: {len(df)}")
    print(f"Columns: Building Type, Building Level, {', '.join(resource_types)} (costs), Duration, Population, Capacity, Generated Resources, Building Requirements, Effects")
    
    return df

if __name__ == '__main__':
    yaml_file = 'buildings.yaml'
    excel_output = 'Buildings_Output.xlsx'
    
    try:
        df = parse_buildings_yaml_to_excel(yaml_file, excel_output)
        print("\nFirst few rows of the generated data:")
        print(df.head())
    except Exception as e:
        print(f"Error processing file: {e}")
        print("Make sure the YAML file exists and is properly formatted.")
