import yaml
import pandas as pd
from collections import defaultdict

def parse_yaml_to_excel(yaml_file_path, output_excel_path):
    """
    Parse YAML file containing map cell data and export to Excel format.
    
    Columns:
    1: Target Type
    2: Target Level  
    3-6: Resource Gains (food, stone, metal, lumber)
    7+: Unique Items
    After items: Troops
    """
    
    # Load YAML data
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    # Collect all unique items and troops across all cell types and levels
    all_items = set()
    all_troops = set()
    
    # First pass: collect all unique items and troops
    for cell_type, cell_data in data.items():
        if 'rewards' in cell_data:
            for level, reward_data in cell_data['rewards'].items():
                if 'items' in reward_data:
                    for item_name in reward_data['items'].keys():
                        if item_name not in ['apply_random', '_no_loot']:
                            all_items.add(item_name)
        
        if 'troops' in cell_data:
            for level, troop_data in cell_data['troops'].items():
                for troop_name in troop_data.keys():
                    all_troops.add(troop_name)
    
    # Sort for consistent column order
    all_items = sorted(list(all_items))
    all_troops = sorted(list(all_troops))
    
    # Define resource types (columns 3-6)
    resource_types = ['food', 'stone', 'metal', 'lumber']
    
    # Prepare data for DataFrame
    rows = []
    
    for cell_type, cell_data in data.items():
        # Skip if no rewards or troops data
        if 'rewards' not in cell_data and 'troops' not in cell_data:
            continue
            
        # Process each level
        max_level = 0
        if 'rewards' in cell_data:
            max_level = max(max_level, max(cell_data['rewards'].keys()))
        if 'troops' in cell_data:
            max_level = max(max_level, max(cell_data['troops'].keys()))
        
        for level in range(1, max_level + 1):
            row = {
                'Target Type': cell_type.title(),
                'Target Level': level
            }
            
            # Add resource data (columns 3-6)
            reward_data = cell_data.get('rewards', {}).get(level, {})
            resources = reward_data.get('resources', {})
            
            for resource in resource_types:
                row[f'{resource.capitalize()}'] = resources.get(resource, 0)
            
            # Add item data
            items_data = reward_data.get('items', {})
            for item in all_items:
                if item in items_data and isinstance(items_data[item], dict):
                    # Use the weight (chance) instead of amount
                    row[f'{item.replace("_", " ").title()}'] = items_data[item].get('weight', 0)
                else:
                    row[f'{item.replace("_", " ").title()}'] = 0
            
            # Add troop data
            troops_data = cell_data.get('troops', {}).get(level, {})
            for troop in all_troops:
                row[f'{troop.replace("_", " ").title()}'] = troops_data.get(troop, 0)
            
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Save to Excel
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Map_Cells_Data', index=False)
        
        # Adjust column widths for better readability
        worksheet = writer.sheets['Map_Cells_Data']
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
    print(f"Columns: Target Type, Target Level, {', '.join(resource_types)} (resources), {len(all_items)} item columns, {len(all_troops)} troop columns")
    
    return df

if __name__ == '__main__':
    yaml_file = 'Map_CellsV2.yaml'
    excel_output = 'Map_Cells_Output.xlsx'
    
    try:
        df = parse_yaml_to_excel(yaml_file, excel_output)
        print("\nFirst few rows of the generated data:")
        print(df.head())
    except Exception as e:
        print(f"Error processing file: {e}")
        print("Make sure the YAML file exists and is properly formatted.")
