import yaml

def parse_map_cells_to_wiki_format(yaml_file_path, output_file_path):
    """
    Parse MapCellsV2.yaml and convert to wiki data format.
    
    Output format:
    - description: empty for now
    - max_level: highest level found
    - rewards: resources (food, stone, metal, lumber, gold)
    - items: list of item names (no percentages)
    - troops: enemy troops per level
    """
    
    # Load YAML data
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    output_lines = []
    output_lines.append("local map_cells = {")
    
    for cell_type, cell_data in data.items():
        # Skip if not attackable
        if not cell_data.get('attackable', False):
            continue
            
        output_lines.append(f"\t{cell_type} = {{")
        output_lines.append(f"\t\tdescription = \"\",")
        
        # Find max level
        max_level = 0
        if 'troops' in cell_data:
            max_level = max(max_level, max(cell_data['troops'].keys()))
        if 'rewards' in cell_data:
            max_level = max(max_level, max(cell_data['rewards'].keys()))
        
        output_lines.append(f"\t\tmax_level = {max_level},")
        
        # Process loot (resources) and items per level
        output_lines.append(f"\t\tloot = {{")
        
        for level in range(1, max_level + 1):
            # Get resources for this level
            reward_data = cell_data.get('rewards', {}).get(level, {})
            resources = reward_data.get('resources', {})
            
            # Build inline resource string
            resource_items = []
            if resources:
                for resource_name, amount in resources.items():
                    resource_items.append(f"{resource_name} = {amount}")
            
            if resource_items:
                resource_str = ', '.join(resource_items)
                output_lines.append(f"\t\t\t[{level}] = {{ {resource_str} }},")
            else:
                output_lines.append(f"\t\t\t[{level}] = {{}},")
        
        output_lines.append(f"\t\t}},")
        
        # Process items per level
        output_lines.append(f"\t\titems = {{")
        
        for level in range(1, max_level + 1):
            # Get items for this level
            reward_data = cell_data.get('rewards', {}).get(level, {})
            items_data = reward_data.get('items', {})
            
            # Add items data (just list of item names, no percentages)
            if items_data and isinstance(items_data, dict):
                item_names = []
                for item_name, item_info in items_data.items():
                    if item_name not in ['apply_random', '_no_loot']:
                        item_names.append(f'"{item_name}"')
                
                if item_names:
                    items_str = ', '.join(item_names)
                    output_lines.append(f"\t\t\t[{level}] = {{ items = {{{items_str}}} }},")
                else:
                    output_lines.append(f"\t\t\t[{level}] = {{}},")
            else:
                output_lines.append(f"\t\t\t[{level}] = {{}},")
        
        output_lines.append(f"\t\t}},")
        
        # Process troops per level
        output_lines.append(f"\t\ttroops = {{")
        
        for level in range(1, max_level + 1):
            # Get troops for this level
            troops_data = cell_data.get('troops', {}).get(level, {})
            
            # Build inline troop string
            troop_items = []
            if troops_data:
                for troop_name, count in troops_data.items():
                    troop_items.append(f"{troop_name} = {count}")
            
            if troop_items:
                troop_str = ', '.join(troop_items)
                output_lines.append(f"\t\t\t[{level}] = {{ {troop_str} }},")
            else:
                output_lines.append(f"\t\t\t[{level}] = {{}},")
        
        output_lines.append(f"\t\t}},")
        output_lines.append(f"\t}},")
    
    output_lines.append("}")
    output_lines.append("return map_cells")
    
    # Write to output file
    with open(output_file_path, 'w') as file:
        file.write('\n'.join(output_lines))
    
    print(f"GreatDragons format file saved to: {output_file_path}")
    print(f"Processed {len([k for k, v in data.items() if v.get('attackable', False)])} attackable cell types")

if __name__ == '__main__':
    yaml_file = 'Map_CellsV2.yaml'
    output_file = 'map_cells_great_dragons_format.txt'
    
    try:
        parse_map_cells_to_great_dragons_format(yaml_file, output_file)
        print("\nConversion completed successfully!")
    except Exception as e:
        print(f"Error processing file: {e}")
        print("Make sure the YAML file exists and is properly formatted.")
