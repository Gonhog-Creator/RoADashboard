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
