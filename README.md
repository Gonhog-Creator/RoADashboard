# RoA Dashboard

A comprehensive Streamlit-based analytics dashboard for analyzing game data from CSV reports. The dashboard provides real-time insights into player statistics, resources, buildings, troops, items, and special protection status.

## Features

### Core Analytics
- **Overview Tab**: Resource totals, daily growth rates, per-player averages, and attack protection analysis
- **Player Count**: Population trends and growth analysis
- **Resources**: Detailed resource tracking with historical trends
- **Power**: Player power distribution and rankings
- **Speedups**: Speedup item usage and availability

### Advanced Analytics
- **Items**: Comprehensive item inventory analysis with enhanced tracking
- **Troops**: Troop composition and strength analysis
- **Buildings**: Building levels and construction analysis
- **Skins**: Player cosmetic items tracking
- **Quests & Research**: Quest completion and research progress analysis

### Attack Prevention Analysis
- **Comprehensive Detection**: Identifies all attack prevention effects (ceasefire, truce, armistice, etc.)
- **Resource Control**: Shows which players control protected resources
- **Player Rankings**: Power-sorted list of protected players
- **Resource Distribution**: Pie charts showing resource control among protected players
- **Protection Metrics**: Total protected resources and player percentages

## Installation & Setup

1. **Install Dependencies:**
```bash
pip install streamlit pandas plotly openpyxl
```

2. **Navigate to Daily Report Tools:**
```bash
cd DailyReportTools
```

3. **Run the Dashboard:**
```bash
streamlit run dashboard.py
```

4. **Access the Dashboard:**
   - Open your browser to the provided URL (typically `http://localhost:8501`)
   - The dashboard will automatically load and process available CSV files from GitHub

## Dashboard Tabs Overview

| Tab | Purpose | Key Features |
|-----|---------|--------------|
| **Overview** | Main metrics dashboard | Resource totals, growth rates, attack protection badges |
| **Player Count** | Population analysis | Growth trends, player statistics |
| **Resources** | Resource tracking | Historical trends, resource distribution |
| **Power** | Power analysis | Player rankings, power distribution |
| **Speedups** | Speedup items | Usage patterns, availability |
| **Items** | Item inventory | Comprehensive item tracking |
| **Troops** | Military analysis | Troop composition, strength metrics |
| **Buildings** | Construction analysis | Building levels, progression |
| **Skins** | Cosmetics tracking | Player customization items |
| **Quests & Research** | Progress tracking | Quest completion, research status |
| **Attack Prevention** | Protection analysis | Ceasefire, truce, armistice effects |

## Data Source

The dashboard loads data from the GitHub repository (configured via secrets) containing comprehensive player data CSV files. Data is automatically cached in memory for performance, with selective caching of detailed data for the most recent files to optimize memory usage.

## Recent Updates

### Memory Optimization
- **Selective Caching**: Only retains detailed `raw_player_data` for the most recent 30 files
- **Improved Performance**: Reduced memory footprint while maintaining full functionality

### Loading UI Improvements
- **Clean Disappearance**: Loading UI now completely disappears after data is loaded
- **Performance Metrics**: Shows download speed and timing information during loading
- **Optimized Downloads**: Reduced parallel workers to avoid GitHub API rate limiting

### Attack Prevention Enhancement
- **Expanded Detection**: Captures all attack prevention effects, not just specific types
- **Resource Analysis**: Detailed breakdown of protected resources by player
- **Visual Improvements**: Non-overlapping legends, better chart layouts

## Troubleshooting

### Common Issues
- **No Data Displayed**: Ensure GitHub credentials are configured in secrets
- **Slow Loading**: First load may take time to download all historical data; subsequent loads use cache
- **Chart Overlap**: Refresh the page if legends overlap
- **Loading UI Stuck**: Check GitHub API rate limits and network connectivity

### Data Format
- **Comprehensive Format**: Full player data including `active_effects`, `resource_*`, `power`, `troop_*`, `item_*`, `buildings_metadata`, and more
- **Graceful Handling**: Dashboard handles missing data fields appropriately

## Parser Tools

The repository also includes YAML parser tools for game configuration files (located in root directory):

- **MapCellsParser.py**: Parses map cell data from YAML to Excel
- **BuildingsParser.py**: Parses building data from YAML to Excel
- **BuildingsExcelToYamlConverter.py**: Converts Excel back to YAML format
- **ExcelToYamlMapCells.py**: Converts Excel back to YAML format

These tools are used for game configuration analysis and are separate from the main dashboard functionality.

## Requirements

### Dashboard
- `streamlit` - Web application framework
- `plotly` - Interactive visualizations
- `pandas` - Data processing
- `openpyxl` - Excel file support

### Parser Tools
- `pyyaml` - YAML parsing
- `pandas` - Data manipulation
- `openpyxl` - Excel file writing

### Full Installation
```bash
pip install streamlit plotly pandas openpyxl pyyaml
```
