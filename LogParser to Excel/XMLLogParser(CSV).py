#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import csv
import json
import re
import html

def clean_xml_content(xml_content):
    """
    Clean XML content by escaping problematic characters in text content
    while preserving XML structure
    """
    # Replace problematic characters in username fields
    # Pattern to find <username>...</username> and escape < > within
    def escape_username_content(match):
        tag_content = match.group(1)
        # Escape < and > characters within the username content
        escaped_content = tag_content.replace('<', '&lt;').replace('>', '&gt;')
        return f'<username>{escaped_content}</username>'
    
    # Apply the replacement
    cleaned_xml = re.sub(r'<username>(.*?)</username>', escape_username_content, xml_content, flags=re.DOTALL)
    
    return cleaned_xml

def parse_xml_to_csv(xml_file_path, csv_output_path):
    """
    Convert XML file to CSV with specified columns:
    1. UUID
    2. Item ID
    3. Username
    4. Date
    5. Timestamp (extracted from data field)
    6. Item (extracted from data field)
    """
    
    # Read and clean the XML content
    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    # Clean problematic characters
    cleaned_xml = clean_xml_content(xml_content)
    
    # Parse the cleaned XML file
    try:
        root = ET.fromstring(cleaned_xml)
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        # Try alternative approach - manually fix common issues
        # Replace any remaining problematic characters
        xml_content_fixed = re.sub(r'<([^<>]*)>([^<>]*[<>][^<>]*)</\1>', 
                                 lambda m: f"<{m.group(1)}>{html.escape(m.group(2))}</{m.group(1)}>", 
                                 xml_content)
        root = ET.fromstring(xml_content_fixed)
    
    # List to store all row data
    data_rows = []
    
    # Iterate through each row element
    for row in root.findall('row'):
        # Extract basic fields
        uuid_elem = row.find('uuid')
        item_id_elem = row.find('item_id')
        username_elem = row.find('username')
        date_elem = row.find('date')
        data_elem = row.find('data')
        
        # Get text content, handle missing elements
        uuid = uuid_elem.text if uuid_elem is not None else ''
        item_id = item_id_elem.text if item_id_elem is not None else ''
        username = username_elem.text if username_elem is not None else ''
        # Unescape HTML entities back to original characters
        username = html.unescape(username)
        date = date_elem.text if date_elem is not None else ''
        
        # Extract timestamp and item type from data field
        timestamp = ''
        item_type = ''
        if data_elem is not None and data_elem.text:
            try:
                # Parse the JSON data
                json_data = json.loads(data_elem.text)
                if isinstance(json_data, list) and len(json_data) > 0:
                    # Extract timestamp from the first entry's time field
                    timestamp = json_data[0].get('time', '')
                    
                    # Extract item type from the first entry's type field
                    type_field = json_data[0].get('type', '')
                    if type_field.startswith('item:'):
                        item_type = type_field[6:]  # Remove 'item:' prefix
            except (json.JSONDecodeError, KeyError, IndexError):
                # Fallback: try to extract using regex if JSON parsing fails
                time_match = re.search(r'"time":"([^"]+)"', data_elem.text)
                if time_match:
                    timestamp = time_match.group(1)
                    
                type_match = re.search(r'"type":"item:([^"]+)"', data_elem.text)
                if type_match:
                    item_type = type_match.group(1)
        
        # Add row to data list
        data_rows.append([uuid, item_id, username, date, timestamp, item_type])
    
    # Write to CSV file
    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['UUID', 'Item ID', 'Username', 'Date', 'Timestamp', 'Item'])
        
        # Write data rows
        writer.writerows(data_rows)
    
    print(f"Successfully converted {len(data_rows)} rows to CSV file: {csv_output_path}")
    
    # Display first few rows as preview
    print("\nPreview of converted data:")
    print("UUID,Item ID,Username,Date,Timestamp,Item")
    for i, row in enumerate(data_rows[:5]):
        print(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}")
    
    return data_rows

if __name__ == "__main__":
    # File paths
    xml_file = "/LogParser to Excel/complete_updated_item_log_testronius_march.xml.xml"
    csv_file = "/LogParser to Excel/item_log_testronius_march.csv"
    
    # Convert XML to CSV
    try:
        data_rows = parse_xml_to_csv(xml_file, csv_file)
        print(f"\nConversion completed successfully!")
        print(f"Total records processed: {len(data_rows)}")
        
        # Get unique items and users
        unique_items = set(row[4] for row in data_rows if row[4])
        unique_users = set(row[2] for row in data_rows if row[2])
        
        print(f"Unique items found: {len(unique_items)}")
        print(f"Items: {sorted(unique_items)}")
        print(f"Unique users: {len(unique_users)}")
        
        print(f"\nCSV file created: {csv_file}")
        print("You can now open this CSV file in Excel or any spreadsheet application.")
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
