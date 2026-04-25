# Building Cost Editor System

This system provides a two-way conversion between YAML building data and Excel format, allowing you to manually edit costs, durations, and rewards while preserving all game logic and formatting.

## How to Use

### Step 1: Convert YAML to Excel
```bash
python yaml_to_excel.py
```
This extracts all building data from `buildings.yaml` and creates `buildings_data.xlsx` with:
- **Building_Data sheet**: Complete breakdown of all buildings, levels, and requirements
- **Summary sheet**: Overview of all buildings and their properties

### Step 2: Edit the Excel File
Open `buildings_data.xlsx` and modify:
- **Cost columns**: `food_cost`, `lumber_cost`, `stone_cost`, `metal_cost`, `gold_cost`
- **Duration**: `duration` (in seconds)
- **Power rewards**: `power_reward`
- **Other data**: Population, building requirements, items, etc.

**Important**: Do not change the structure, only edit the values in the cells.

### Step 3: Convert Excel back to YAML
```bash
python excel_to_yaml.py
```
This rebuilds the `buildings.yaml` file with your updated values while preserving:
- Original YAML formatting and comments
- Special effects and actions
- All game logic and structure

## Files

- `yaml_to_excel.py` - Converts YAML to Excel
- `excel_to_yaml.py` - Converts Excel back to YAML with automatic settlement_types formatting
- `buildings.yaml` - Main building configuration file
- `buildings_data.xlsx` - Excel file for editing (generated)
- `buildings.yaml.backup` - Automatic backup before updates

## Excel Columns Explained

### Basic Info
- `building_id` - Internal building identifier
- `settlement_type` - "city" or "outpost" (buildings with direct requirements default to "city")
- `level` - Building level (1-11)

**Note**: Buildings that have direct requirements (no settlement type specified) are automatically assigned to "city" settlement type in Excel for easier editing.

### Costs & Requirements
- `food_cost`, `lumber_cost`, `stone_cost`, `metal_cost`, `gold_cost` - Resource costs
- `duration` - Build time in seconds
- `population_required` - Population needed to build
- `required_buildings` - Format: "building_id:level,building_id:level"
- `required_items` - Format: "item_name:quantity"

### Rewards & Generation
- `power_reward` - Power points awarded
- `generated_resources` - Format: "resource:hourly_amount"
- `population_generated` - Population provided
- `capacity` - Storage capacity
- `troops_per_march`, `march_count` - Military stats

### Building Properties
- `max_level` - Maximum achievable level
- `max_build_count` - Maximum instances (0 = unlimited)
- `destructible` - Can be destroyed
- `settlement_types` - Where it can be built
- `for_field` - Is this a field building

## Safety Features

- **Automatic backups**: Original YAML is backed up before any changes
- **Data preservation**: Special effects, actions, and formatting are preserved
- **Error handling**: Invalid data is skipped with warnings
- **Validation**: Numeric values are properly converted
- **Automatic formatting**: settlement_types are automatically formatted as `[city, outpost]` or `[city]` to match original YAML structure

## Example Workflow

1. Run `yaml_to_excel.py` to create the Excel file
2. Open `buildings_data.xlsx` and edit costs for specific buildings
3. Save the Excel file
4. Run `excel_to_yaml.py` to update the YAML
5. Test the updated building costs in your game

The system ensures that all your manual cost changes are applied while maintaining the exact YAML structure required by the game engine.
