import yaml

# Load YAML data
with open('buildings.yaml', 'r') as file:
    data = yaml.safe_load(file)

print("YAML loaded successfully")
print(f"Top-level keys: {list(data.keys())}")

# Test each building type
for building_type, building_data in data.items():
    print(f"\nProcessing {building_type}: {type(building_data)}")
    
    if not isinstance(building_data, dict):
        print(f"  Skipping {building_type} - not a dict")
        continue
        
    if 'id' not in building_data:
        print(f"  Skipping {building_type} - no id")
        continue
    
    print(f"  Building ID: {building_data.get('id')}")
    
    # Test requirements
    if 'requirements' in building_data:
        print(f"  Requirements found: {type(building_data['requirements'])}")
        for level, req_data in building_data['requirements'].items():
            print(f"    Level {level}: {type(req_data)}")
            if isinstance(req_data, dict):
                print(f"      Keys: {list(req_data.keys())}")
                if 'resources' in req_data:
                    print(f"      Resources: {type(req_data['resources'])}")
                if 'buildings' in req_data:
                    print(f"      Buildings: {type(req_data['buildings'])}")
    
    # Test generations
    if 'generations' in building_data:
        print(f"  Generations found: {type(building_data['generations'])}")
        for level, gen_data in building_data['generations'].items():
            print(f"    Level {level}: {type(gen_data)}")
            if isinstance(gen_data, dict):
                print(f"      Keys: {list(gen_data.keys())}")
                for key, value in gen_data.items():
                    print(f"        {key}: {type(value)} = {value}")
    
    # Test effects
    if 'effects' in building_data:
        print(f"  Effects found: {type(building_data['effects'])}")
        for effect_name, effect_data in building_data['effects'].items():
            print(f"    {effect_name}: {type(effect_data)} = {effect_data}")

print("\nDebug completed successfully!")
