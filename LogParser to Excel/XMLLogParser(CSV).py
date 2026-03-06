#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import csv
import json
import re
import html
import os
import glob

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
    XML Log Parser - Convert XML file to CSV with specified columns:
    1. Username
    2. Date
    3. Timestamp (extracted from data field)
    4. Item (extracted from data field)
    5. Quantity (extracted from message field)
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
        username_elem = row.find('username')
        date_elem = row.find('date')
        data_elem = row.find('data')
        
        # Get text content, handle missing elements
        username = username_elem.text if username_elem is not None else ''
        # Unescape HTML entities back to original characters
        username = html.unescape(username)
        date = date_elem.text if date_elem is not None else ''
        
        # Extract timestamp, item type, and quantity from data field
        timestamp = ''
        item_type = ''
        quantity = ''
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
                    
                    # Extract quantity from the message field
                    message = json_data[0].get('message', '')
                    # Look for pattern like "-3 from" in the message
                    quantity_match = re.search(r'-(\d+)\s+from', message)
                    if quantity_match:
                        quantity = quantity_match.group(1)
            except (json.JSONDecodeError, KeyError, IndexError):
                # Fallback: try to extract using regex if JSON parsing fails
                time_match = re.search(r'"time":"([^"]+)"', data_elem.text)
                if time_match:
                    timestamp = time_match.group(1)
                    
                type_match = re.search(r'"type":"item:([^"]+)"', data_elem.text)
                if type_match:
                    item_type = type_match.group(1)
                    
                # Extract quantity from message using regex
                quantity_match = re.search(r'"message":"[^"]*?-(\d+)\s+from', data_elem.text)
                if quantity_match:
                    quantity = quantity_match.group(1)
        
        # Add row to data list
        data_rows.append([username, date, timestamp, item_type, quantity])
    
    # Sort data rows by username (ascending)
    data_rows.sort(key=lambda x: x[0].lower())
    
    # Write to CSV file
    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Username', 'Date', 'Timestamp', 'Item', 'Quantity'])
        
        # Write data rows
        writer.writerows(data_rows)
    
    print(f"Successfully converted {len(data_rows)} rows to CSV file: {csv_output_path}")
    
    # Display first few rows as preview
    print("\nPreview of converted data:")
    print("Username,Date,Timestamp,Item,Quantity")
    for i, row in enumerate(data_rows[:5]):
        print(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]}")
    
    return data_rows

if __name__ == "__main__":
    # Find XML files in current directory
    xml_files = glob.glob("*.xml") + glob.glob("*.xml.xml")
    
    if not xml_files:
        print("No XML files found in current directory!")
        print("Please place XML files in the same directory as this script.")
        exit(1)
    
    print(f"Found {len(xml_files)} XML file(s):")
    for i, file in enumerate(xml_files, 1):
        print(f"{i}. {file}")
    
    # Process each XML file
    for xml_file in xml_files:
        print(f"\nProcessing: {xml_file}")
        
        # Generate CSV filename
        base_name = os.path.splitext(xml_file)[0]
        csv_file = f"{base_name}.csv"
        
        try:
            # Convert XML to CSV
            data_rows = parse_xml_to_csv(xml_file, csv_file)
            print(f"Conversion completed successfully!")
            print(f"Total records processed: {len(data_rows)}")
            
            # Get unique items and users
            unique_items = set(row[3] for row in data_rows if row[3])
            unique_users = set(row[0] for row in data_rows if row[0])
            
            print(f"Unique items found: {len(unique_items)}")
            print(f"Items: {sorted(unique_items)}")
            print(f"Unique users: {len(unique_users)}")
            
            print(f"CSV file created: {csv_file}")
            
        except Exception as e:
            print(f"Error processing {xml_file}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nAll files processed! You can now open the CSV files in Excel or any spreadsheet application.")
