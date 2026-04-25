#!/usr/bin/env python3
"""
Simple script to copy wikibuildingsdata to wikibuildingsdata_updated
and selectively update building costs and power rewards from buildings_updated.yaml
"""

import yaml
import re
import shutil

def load_yaml_updates(yaml_file):
    """Load building updates from YAML file."""
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)

def copy_original_file(original_file, output_file):
    """Copy the original file to output location."""
    shutil.copy2(original_file, output_file)
    print(f"Copied {original_file} to {output_file}")

def ensure_location_type(output_file, yaml_updates):
    """Ensure every building has a location type."""
    
    # Read the file line by line
    with open(output_file, 'r') as f:
        lines = f.readlines()
    
    print("Adding location types to buildings...")
    
    current_building = None
    buildings_needing_location = set()
    
    # First pass: identify buildings and check if they have location
    for i, line in enumerate(lines):
        # Track which building we're in (only match lines starting with exactly one tab)
        if line.startswith('\t') and not line.startswith('\t\t'):
            line_stripped = line.strip()
            building_match = re.match(r'(?:(\w+)|\["([^"]+)"\])\s*=', line_stripped)
            if building_match:
                current_building = building_match.group(1) or building_match.group(2)
                buildings_needing_location.add(current_building)
                continue
        
        # Check if current building has location (look for location line)
        if current_building and re.match(r'\t\tlocation\s*=', line.strip()):
            buildings_needing_location.discard(current_building)
    
    print(f"  Found {len(buildings_needing_location)} buildings needing location")
    
    # Second pass: add location to buildings that don't have it
    current_building = None
    lines_to_add = []
    
    for i, line in enumerate(lines):
        # Track which building we're in (only match lines starting with exactly one tab)
        if line.startswith('\t') and not line.startswith('\t\t'):
            line_stripped = line.strip()
            building_match = re.match(r'(?:(\w+)|\["([^"]+)"\])\s*=', line_stripped)
            if building_match:
                current_building = building_match.group(1) or building_match.group(2)
                continue
        
        # Add location after max_level line if building needs location
        if current_building and current_building in buildings_needing_location:
            if 'max_level' in line and '=' in line:
                # Add location after this line
                lines_to_add.append((i + 1, current_building))
                buildings_needing_location.discard(current_building)
    
    # Insert location lines (in reverse order to maintain indices)
    for line_index, building_name in reversed(lines_to_add):
        indent = '\t\t'
        location_line = f'{indent}location = "city",\n'
        lines.insert(line_index, location_line)
        print(f"  Added location to {building_name}")
    
    # Write the updated content back
    with open(output_file, 'w') as f:
        f.writelines(lines)

def ensure_description_field(output_file, yaml_updates):
    """Ensure every building has a description field."""
    
    # Read the file line by line
    with open(output_file, 'r') as f:
        lines = f.readlines()
    
    print("Adding description fields to buildings...")
    
    current_building = None
    buildings_needing_description = set()
    
    # First pass: identify buildings and check if they have description
    for i, line in enumerate(lines):
        # Track which building we're in (only match lines starting with exactly one tab)
        if line.startswith('\t') and not line.startswith('\t\t'):
            line_stripped = line.strip()
            building_match = re.match(r'(?:(\w+)|\["([^"]+)"\])\s*=', line_stripped)
            if building_match:
                current_building = building_match.group(1) or building_match.group(2)
                buildings_needing_description.add(current_building)
                continue
        
        # Check if current building has description (look for description line)
        if current_building and re.match(r'\t\tdescription\s*=', line.strip()):
            buildings_needing_description.discard(current_building)
    
    print(f"  Found {len(buildings_needing_description)} buildings needing description")
    
    # Second pass: add description to buildings that don't have it
    current_building = None
    lines_to_add = []
    
    for i, line in enumerate(lines):
        # Track which building we're in (only match lines starting with exactly one tab)
        if line.startswith('\t') and not line.startswith('\t\t'):
            line_stripped = line.strip()
            building_match = re.match(r'(?:(\w+)|\["([^"]+)"\])\s*=', line_stripped)
            if building_match:
                current_building = building_match.group(1) or building_match.group(2)
                continue
        
        # Add description after location line if building needs description
        if current_building and current_building in buildings_needing_description:
            if 'location' in line and '=' in line:
                # Add description after this line
                lines_to_add.append((i + 1, current_building))
                buildings_needing_description.discard(current_building)
    
    # Insert description lines (in reverse order to maintain indices)
    for line_index, building_name in reversed(lines_to_add):
        indent = '\t\t'
        description_line = f'{indent}description = "Description needs to be added",\n'
        lines.insert(line_index, description_line)
        print(f"  Added description to {building_name}")
    
    # Write updated content back
    with open(output_file, 'w') as f:
        f.writelines(lines)

def update_costs_and_power(output_file, yaml_updates):
    """Read the output file and selectively update costs and power values."""
    
    # Read the file line by line
    with open(output_file, 'r') as f:
        lines = f.readlines()
    
    print("Updating building costs and power rewards...")
    
    current_building = None
    in_requirements = False
    in_unlocks = False
    
    for i, line in enumerate(lines):
        # Track which building we're in (only match lines starting with exactly one tab)
        if line.startswith('\t') and not line.startswith('\t\t'):
            line_stripped = line.strip()
            building_match = re.match(r'(?:(\w+)|\["([^"]+)"\])\s*=', line_stripped)
            if building_match:
                current_building = building_match.group(1) or building_match.group(2)
                in_requirements = False
                in_unlocks = False
                print(f"  Processing {current_building}...")
                continue
        
        # Track which section we're in
        if 'requirements' in line:
            in_requirements = True
            in_unlocks = False
            continue
        elif 'unlocks' in line:
            in_requirements = False
            in_unlocks = True
            continue
        
        # Process level lines
        level_match = re.match(r'\t\t\[(\d+)\]\s*=\s*{', line.strip())
        if level_match and current_building:
            level = int(level_match.group(1))
            
            # Get updates for this building
            building_updates = yaml_updates.get(current_building, {})
            
            if in_requirements and 'requirements' in building_updates:
                req_data = building_updates['requirements'].get(level, {})
                if isinstance(req_data, dict) and 'resources' in req_data:
                    # Update requirements line
                    resources = req_data['resources']
                    new_line_parts = []
                    
                    # Keep existing non-resource parts
                    original_content = line.strip()
                    if original_content.endswith('},'):
                        base_part = original_content[:-2] + ', '
                    else:
                        base_part = original_content[:-1] + ', '
                    
                    # Add new resources
                    for resource, value in resources.items():
                        new_line_parts.append(f"{resource} = {value}")
                    
                    # Add build_time if present
                    if 'duration' in req_data:
                        new_line_parts.append(f"build_time = {req_data['duration']}")
                    
                    # Construct new line
                    if new_line_parts:
                        new_line = f"\t\t[{level}] = {{{base_part}{', '.join(new_line_parts)}}},\n"
                        lines[i] = new_line
            
            elif in_unlocks and 'rewards' in building_updates:
                reward_data = building_updates['rewards'].get(level, {})
                if isinstance(reward_data, dict) and 'power' in reward_data:
                    # Update unlocks line
                    power_value = reward_data['power']
                    
                    # Remove existing power and add new one
                    updated_line = line
                    updated_line = re.sub(r',?\s*power\s*=\s*\d+', '', updated_line)
                    
                    # Add new power value
                    if '{' in updated_line and '}' in updated_line:
                        # Insert before closing brace
                        updated_line = updated_line.rstrip().rstrip('}') + f", power = {power_value}}}\n"
                    
                    lines[i] = updated_line
    
    # Write the updated content back
    with open(output_file, 'w') as f:
        f.writelines(lines)
    
    print("Updates completed!")

def add_new_buildings(output_file, yaml_updates):
    """Add new buildings from YAML that don't exist in the wiki file."""
    
    # Read existing buildings from the file
    with open(output_file, 'r') as f:
        content = f.read()
    
    print("Adding new buildings from YAML...")
    
    # Find existing buildings
    existing_buildings = set()
    for match in re.finditer(r'\t(?:(\w+)|\["([^"]+)"\])\s*=', content):
        building_name = match.group(1) or match.group(2)
        existing_buildings.add(building_name)
    
    # Find new buildings that need to be added
    new_buildings = []
    for building_name, building_data in yaml_updates.items():
        if building_name not in existing_buildings:
            print(f"  Adding new building: {building_name}")
            new_buildings.append((building_name, building_data))
    
    if not new_buildings:
        print("  No new buildings to add")
        return
    
    # Generate Lua code for new buildings
    new_building_code = []
    for building_name, building_data in new_buildings:
        code = generate_lua_building(building_name, building_data)
        new_building_code.append(code)
    
    # Insert new buildings before the closing brace
    insert_position = content.rfind('}')
    if insert_position != -1:
        new_content = content[:insert_position] + ',\n'.join(new_building_code) + '\n' + content[insert_position:]
        
        # Write back to file
        with open(output_file, 'w') as f:
            f.write(new_content)
        
        print(f"  Added {len(new_buildings)} new buildings")

def generate_lua_building(building_name, building_data):
    """Generate Lua code for a new building."""
    
    # Get building ID (use a simple increment for new buildings)
    building_id = len(re.findall(r'\tid\s*=\s*\d+', open('wikibuildingsdata_updated').read())) + 1
    
    code = f'\t{building_name} = {{\n'
    code += f'\t\tid = {building_id},\n'
    code += f'\t\tfirst_levelup = 1,\n'
    code += f'\t\tmax_level = {building_data.get("max_level", 10)},\n'
    code += f'\t\tlocation = "{building_data.get("settlement_types", ["city"])[0]}",\n'
    code += f'\t\tdescription = "Description needs to be added",\n'
    
    # Add requirements
    code += '\t\trequirements = {\n'
    if 'requirements' in building_data:
        for level, req_data in building_data['requirements'].items():
            if isinstance(req_data, dict) and 'resources' in req_data:
                resources = req_data['resources']
                req_parts = []
                for resource, value in resources.items():
                    req_parts.append(f"{resource} = {value}")
                if 'duration' in req_data:
                    req_parts.append(f"build_time = {req_data['duration']}")
                code += f'\t\t\t[{level}] = {{{", ".join(req_parts)}}},\n'
            else:
                code += f'\t\t\t[{level}] = {{}},\n'
    code += '\t\t},\n'
    
    # Add unlocks
    code += '\t\tunlocks = {\n'
    if 'rewards' in building_data:
        for level, reward_data in building_data['rewards'].items():
            if isinstance(reward_data, dict) and 'power' in reward_data:
                code += f'\t\t\t[{level}] = {{power = {reward_data["power"]}}},\n'
            else:
                code += f'\t\t\t[{level}] = {{}},\n'
    code += '\t\t}\n'
    
    code += '\t}'
    return code

def main():
    # File paths
    original_file = 'wikibuildingsdata'
    yaml_file = 'buildlings_updated.yaml'
    output_file = 'wikibuildingsdata_updated'
    
    try:
        # Load the YAML updates
        print("Loading YAML updates...")
        yaml_updates = load_yaml_updates(yaml_file)
        
        # Remove old output file if it exists
        import os
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Removed existing {output_file}")
        
        # Copy original file
        print("Copying original file...")
        copy_original_file(original_file, output_file)
        
        # Ensure all buildings have location type
        ensure_location_type(output_file, yaml_updates)
        
        # Ensure all buildings have description field
        ensure_description_field(output_file, yaml_updates)
        
        # Update costs and power
        update_costs_and_power(output_file, yaml_updates)
        
        # Add new buildings from YAML
        add_new_buildings(output_file, yaml_updates)
        
        print(f"\nSuccessfully created {output_file} with updated costs, power rewards, location types, description fields, and new buildings!")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure all required files exist in the current directory.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
