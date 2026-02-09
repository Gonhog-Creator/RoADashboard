# YAML File Parser

This repository contains Python scripts for parsing various YAML configuration files and converting them into different formats for easier analysis and visualization.

## Scripts

### MapCells Parser
**File:** `MapCellsParser.py`

A Python script that parses YAML files containing map cell data and exports the information to a formatted Excel spreadsheet.

**Features:**
- Parses YAML files with terrain/cell type definitions
- Extracts data for multiple levels per terrain type
- Organizes output into structured columns:
  - Column 1: Target Type (capitalized terrain name)
  - Column 2: Target Level
  - Columns 3-6: Resource Gains (Food, Stone, Metal, Lumber)
  - Following columns: Unique items with drop probabilities
  - Final columns: Troop compositions with counts
- Auto-adjusts column widths for better readability
- Handles missing data gracefully (fills with 0)

**Usage:**
```bash
python3 MapCellsParser.py
```

### Buildings Parser
**File:** `BuildingsParser.py`

A Python script that parses YAML files containing building data and exports the information to a formatted Excel spreadsheet.

**Features:**
- Parses YAML files with building type definitions
- Extracts data for multiple levels per building type
- Organizes output into structured columns:
  - Column 1: Building Type (capitalized building name)
  - Column 2: Building Level
  - Columns 3-7: Resource Costs (Food, Lumber, Stone, Metal, Gold)
  - Column 8: Duration
  - Column 9: Population
  - Column 10: Capacity
  - Following columns: Generated Resources (Gen prefix)
  - After resources: Building Requirements (Req prefix)
  - Final columns: Effects (Effect prefix)
- Auto-adjusts column widths for better readability
- Handles missing data gracefully (fills with 0)

**Usage:**
```bash
python3 BuildingsParser.py
```

### Buildings Excel to YAML Converter
**File:** `BuildingsExcelToYamlConverter.py`

A Python script that imports Excel files in the same format as BuildingsParser output and generates updated YAML files while preserving the exact original structure, comments, and formatting.

**Features:**
- Imports Excel files with the exact column structure from BuildingsParser
- Preserves original YAML comments, formatting, and structure
- Maintains effects sections and other metadata from original YAML
- Converts column names back to YAML format (Title Case -> snake_case)
- Handles missing data gracefully
- Preserves building types that weren't modified in the Excel file

**Usage:**
```bash
python3 BuildingsExcelToYamlConverter.py
```

**Workflow:**
1. Use BuildingsParser.py to convert YAML to Excel
2. Edit the Excel file with your changes
3. Use BuildingsExcelToYamlConverter.py to convert back to YAML
4. The output YAML maintains perfect compatibility with the original system

### MapCells Excel to YAML Converter
**File:** `ExcelToYamlMapCells.py`

A Python script that imports Excel files in the same format as MapCellsParser output and generates updated YAML files while preserving the exact original structure, comments, and formatting.

**Features:**
- Imports Excel files with the exact column structure from MapCellsParser
- Preserves original YAML comments, formatting, and structure
- Maintains effects sections and other metadata from original YAML
- Converts column names back to YAML format (Title Case -> snake_case)
- Handles missing data gracefully
- Preserves cell types that weren't modified in the Excel file

**Usage:**
```bash
python3 ExcelToYamlMapCells.py
```

**Workflow:**
1. Use MapCellsParser.py to convert YAML to Excel
2. Edit the Excel file with your changes
3. Use ExcelToYamlMapCells.py to convert back to YAML
4. The output YAML maintains perfect compatibility with the original system
## Requirements

Most scripts in this repository require the following Python packages:
- `yaml` - For parsing YAML files
- `pandas` - For data manipulation and Excel export
- `openpyxl` - For Excel file writing

Install dependencies:
```bash
pip install pyyaml pandas openpyxl
```

## General Output Format

Excel-based parsers typically generate worksheets with the following structure:
- **Target Type**: The category or type being parsed
- **Target Level**: The level or tier within that type
- **Resource columns**: Various resource amounts or gains
- **Item columns**: Item probabilities or amounts
- **Other data columns**: Additional parsed information specific to each script

## Notes

- Scripts automatically discover all unique items and entities across the YAML data
- Missing data is typically filled with 0 values
- Column names are formatted for readability (underscores replaced with spaces, proper capitalization)
- Each script handles its specific YAML structure appropriately
